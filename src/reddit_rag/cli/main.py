from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from reddit_rag import __version__
from reddit_rag.config import load_app_config
from reddit_rag.env import (
    load_dotenv_from_project,
    load_reddit_source_settings_from_env,
    missing_reddit_env,
    reddit_source_mode,
)
from reddit_rag.ingestion.raw_ingestion import fetch_thread_to_raw, ingest_subreddit_raw
from reddit_rag.ingestion.reddit_source import JsonRedditSource, RedditJsonResponse, RedditSourceError
from reddit_rag.paths import resolve_processed_dir
from reddit_rag.processing.chunk import chunk_records, chunk_to_dict
from reddit_rag.processing.chunks_io import (
    default_chunks_jsonl_path,
    load_records_from_jsonl,
    merge_chunk_records_jsonl,
)
from reddit_rag.processing.comments import (
    comment_record_to_dict,
    default_comments_jsonl_path,
    merge_comment_records_jsonl,
    normalize_comments_from_subreddit,
    normalize_comments_from_thread_file,
)
from reddit_rag.processing.normalize import NormalizedComment, NormalizedPost
from reddit_rag.processing.posts import (
    default_posts_jsonl_path,
    merge_post_records_jsonl,
    normalize_posts_from_subreddit,
    normalize_posts_from_thread_file,
    post_record_to_dict,
)


def _cmd_validate_config(args: argparse.Namespace) -> int:
    config_dir = Path(args.config_dir).expanduser().resolve() if args.config_dir else None
    try:
        cfg = load_app_config(config_dir=config_dir)
    except (FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1

    print(
        "Config valid: "
        f"{len(cfg.subreddits.subreddits)} subreddit(s), "
        f"embedding model {cfg.models.embedding_model}, "
        f"chat model {cfg.models.chat_model}",
        file=sys.stdout,
    )
    return 0


def _cmd_print_config(args: argparse.Namespace) -> int:
    config_dir = Path(args.config_dir).expanduser().resolve() if args.config_dir else None
    try:
        cfg = load_app_config(config_dir=config_dir)
    except (FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1

    payload = {
        "subreddits": [asdict(e) for e in cfg.subreddits.subreddits],
        "models": asdict(cfg.models),
    }
    text = yaml.dump(
        payload,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    sys.stdout.buffer.write(text.encode("utf-8"))
    return 0


def _cmd_check_env(_args: argparse.Namespace) -> int:
    load_dotenv_from_project()
    try:
        missing = missing_reddit_env()
        settings = None if missing else load_reddit_source_settings_from_env()
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    if missing:
        print(
            "Missing required Reddit source environment variables. "
            "Set them in the environment or in a .env file at the project root:",
            file=sys.stderr,
        )
        for name in missing:
            print(f"  {name}", file=sys.stderr)
        return 1
    print(
        "Reddit source environment is valid: "
        f"mode={reddit_source_mode()}, "
        f"user_agent={settings.user_agent if settings else ''}",
        file=sys.stdout,
    )
    return 0


def _cmd_json_smoke_test(args: argparse.Namespace) -> int:
    load_dotenv_from_project()
    try:
        settings = load_reddit_source_settings_from_env()
        source = JsonRedditSource(settings)
        response = source.fetch_subreddit_listing(args.subreddit, limit=1)
        post_id = _first_listing_post_id(response)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    except RedditSourceError as e:
        print(f"Reddit JSON smoke test failed: {e}", file=sys.stderr)
        return 1

    print(
        "Reddit JSON smoke test passed: "
        f"subreddit={args.subreddit}, "
        f"post_id={post_id or 'none'}, "
        f"{_format_rate_limit(response)}",
        file=sys.stdout,
    )
    return 0


def _cmd_fetch_thread(args: argparse.Namespace) -> int:
    load_dotenv_from_project()
    raw_dir = Path(args.raw_dir).expanduser().resolve() if args.raw_dir else None
    try:
        settings = load_reddit_source_settings_from_env()
        source = JsonRedditSource(settings)
        saved = fetch_thread_to_raw(source, args.permalink, raw_dir=raw_dir)
    except (ValueError, RedditSourceError) as e:
        print(str(e), file=sys.stderr)
        return 1

    print(f"Fetched thread JSON: {saved.path}", file=sys.stdout)
    return 0


def _format_comment_pretty(comment: NormalizedComment) -> str:
    lines = [
        f"subreddit: {comment.subreddit}",
        f"permalink: {comment.permalink}",
        f"id: {comment.id} (reddit_id={comment.reddit_id})",
        f"post_reddit_id: {comment.post_reddit_id}  parent_reddit_id: {comment.parent_reddit_id}",
        f"score: {comment.score}",
    ]
    if comment.author:
        lines.append(f"author: {comment.author}")
    if comment.created_utc is not None:
        lines.append(f"created_utc: {comment.created_utc}")
    lines.append(f"raw_path: {comment.raw_path}")
    lines.append("")
    body = comment.body if comment.body.strip() else "[empty body]"
    lines.append(body)
    lines.append("-" * 72)
    return "\n".join(lines)


def _format_post_pretty(post: NormalizedPost) -> str:
    lines = [
        f"title: {post.title}",
        f"subreddit: {post.subreddit}",
        f"permalink: {post.permalink}",
        f"id: {post.id} (reddit_id={post.reddit_id})",
        f"score: {post.score}  comments: {post.num_comments}",
    ]
    if post.url:
        lines.append(f"url: {post.url}")
    if post.author:
        lines.append(f"author: {post.author}")
    if post.created_utc is not None:
        lines.append(f"created_utc: {post.created_utc}")
    lines.append(f"raw_path: {post.raw_path}")
    lines.append("")
    body = post.body if post.body.strip() else "[empty body]"
    lines.append(body)
    lines.append("-" * 72)
    return "\n".join(lines)


def _cmd_normalize_posts(args: argparse.Namespace) -> int:
    raw_dir = Path(args.raw_dir).expanduser().resolve() if args.raw_dir else None
    try:
        if args.thread:
            path = Path(args.thread).expanduser().resolve()
            posts = normalize_posts_from_thread_file(path)
        elif args.subreddit:
            posts = normalize_posts_from_subreddit(args.subreddit, raw_dir=raw_dir)
        else:
            print("Specify --thread PATH or --subreddit NAME.", file=sys.stderr)
            return 1
    except (ValueError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 1

    records = [post_record_to_dict(p) for p in posts]

    processed_root = (
        Path(args.processed_dir).expanduser().resolve() if args.processed_dir else resolve_processed_dir()
    )

    if not args.pretty:
        if not records:
            print("No posts normalized (empty input).", file=sys.stdout)
        else:
            if args.output:
                out_path = Path(args.output).expanduser().resolve()
                result = merge_post_records_jsonl(out_path, records)
                print(
                    "Merged JSONL: "
                    f"path={result.path} "
                    f"existing={result.existing_count} "
                    f"appended={result.appended} "
                    f"skipped_duplicates={result.skipped_duplicates} "
                    f"total={result.total_after}",
                    file=sys.stdout,
                )
            else:
                by_sub: defaultdict[str, list] = defaultdict(list)
                for post in posts:
                    by_sub[post.subreddit].append(post_record_to_dict(post))
                for subreddit in sorted(by_sub.keys()):
                    out_path = default_posts_jsonl_path(processed_root, subreddit)
                    result = merge_post_records_jsonl(out_path, by_sub[subreddit])
                    print(
                        "Merged JSONL: "
                        f"path={result.path} "
                        f"existing={result.existing_count} "
                        f"appended={result.appended} "
                        f"skipped_duplicates={result.skipped_duplicates} "
                        f"total={result.total_after}",
                        file=sys.stdout,
                    )

    if args.pretty:
        for post in posts:
            print(_format_post_pretty(post), file=sys.stdout)

    return 0


def _cmd_normalize_comments(args: argparse.Namespace) -> int:
    raw_dir = Path(args.raw_dir).expanduser().resolve() if args.raw_dir else None
    try:
        if args.thread:
            path = Path(args.thread).expanduser().resolve()
            comments = normalize_comments_from_thread_file(path)
        elif args.subreddit:
            comments = normalize_comments_from_subreddit(args.subreddit, raw_dir=raw_dir)
        else:
            print("Specify --thread PATH or --subreddit NAME.", file=sys.stderr)
            return 1
    except (ValueError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 1

    records = [comment_record_to_dict(c) for c in comments]

    processed_root = (
        Path(args.processed_dir).expanduser().resolve() if args.processed_dir else resolve_processed_dir()
    )

    if not args.pretty:
        if not records:
            print("No comments normalized (empty input).", file=sys.stdout)
        else:
            if args.output:
                out_path = Path(args.output).expanduser().resolve()
                result = merge_comment_records_jsonl(out_path, records)
                print(
                    "Merged JSONL: "
                    f"path={result.path} "
                    f"existing={result.existing_count} "
                    f"appended={result.appended} "
                    f"skipped_duplicates={result.skipped_duplicates} "
                    f"total={result.total_after}",
                    file=sys.stdout,
                )
            else:
                by_sub: defaultdict[str, list] = defaultdict(list)
                for comment in comments:
                    by_sub[comment.subreddit].append(comment_record_to_dict(comment))
                for subreddit in sorted(by_sub.keys()):
                    out_path = default_comments_jsonl_path(processed_root, subreddit)
                    result = merge_comment_records_jsonl(out_path, by_sub[subreddit])
                    print(
                        "Merged JSONL: "
                        f"path={result.path} "
                        f"existing={result.existing_count} "
                        f"appended={result.appended} "
                        f"skipped_duplicates={result.skipped_duplicates} "
                        f"total={result.total_after}",
                        file=sys.stdout,
                    )

    if args.pretty:
        for comment in comments:
            print(_format_comment_pretty(comment), file=sys.stdout)

    return 0


def _cmd_ingest_raw(args: argparse.Namespace) -> int:
    load_dotenv_from_project()
    config_dir = Path(args.config_dir).expanduser().resolve() if args.config_dir else None
    raw_dir = Path(args.raw_dir).expanduser().resolve() if args.raw_dir else None
    try:
        cfg = load_app_config(config_dir=config_dir)
        settings = load_reddit_source_settings_from_env()
        source = JsonRedditSource(settings)
    except (FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1

    entries = cfg.subreddits.subreddits
    if args.subreddit:
        entries = [entry for entry in entries if entry.name.lower() == args.subreddit.lower()]
        if not entries:
            print(f"Subreddit not found in config: {args.subreddit}", file=sys.stderr)
            return 1

    for entry in entries:
        max_posts = args.max_posts if args.max_posts is not None else entry.max_posts
        max_comments = args.max_comments if args.max_comments is not None else entry.max_comments
        try:
            result = ingest_subreddit_raw(
                source,
                entry.name,
                max_posts=max_posts,
                max_comments=max_comments,
                raw_dir=raw_dir,
                reset_checkpoint=args.reset_checkpoint,
            )
        except (ValueError, RedditSourceError) as e:
            print(f"Ingestion failed for {entry.name}: {e}", file=sys.stderr)
            return 1
        print(
            "Raw ingestion complete: "
            f"subreddit={result.subreddit}, "
            f"listing_pages={result.listing_pages}, "
            f"posts_seen={result.posts_seen}, "
            f"threads_fetched={result.threads_fetched}, "
            f"comments_seen={result.comments_seen}, "
            f"checkpoint={result.checkpoint_path}",
            file=sys.stdout,
        )
    return 0


def _cmd_chunk(args: argparse.Namespace) -> int:
    processed_root = (
        Path(args.processed_dir).expanduser().resolve() if args.processed_dir else resolve_processed_dir()
    )
    posts_path: Path | None = None
    comments_path: Path | None = None
    out_path: Path

    if args.subreddit:
        sub = args.subreddit.strip()
        posts_path = default_posts_jsonl_path(processed_root, sub)
        comments_path = default_comments_jsonl_path(processed_root, sub)
        out_path = (
            Path(args.output).expanduser().resolve()
            if args.output
            else default_chunks_jsonl_path(processed_root, sub)
        )
    else:
        if not args.posts and not args.comments:
            print("Specify --subreddit NAME or at least one of --posts PATH / --comments PATH.", file=sys.stderr)
            return 1
        if not args.output:
            print("When omitting --subreddit, --output PATH is required.", file=sys.stderr)
            return 1
        posts_path = Path(args.posts).expanduser().resolve() if args.posts else None
        comments_path = Path(args.comments).expanduser().resolve() if args.comments else None
        out_path = Path(args.output).expanduser().resolve()

    if args.chunk_overlap >= args.chunk_size:
        print("chunk_overlap must be strictly less than chunk_size.", file=sys.stderr)
        return 1

    records: list[dict[str, Any]] = []
    try:
        if posts_path is not None:
            records.extend(load_records_from_jsonl(posts_path))
        if comments_path is not None:
            records.extend(load_records_from_jsonl(comments_path))
        chunks = chunk_records(records, args.chunk_size, args.chunk_overlap)
    except (ValueError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 1

    if args.pretty:
        for ch in chunks:
            print(json.dumps(chunk_to_dict(ch), ensure_ascii=False, indent=2), file=sys.stdout)
        print(
            f"Chunk preview: built={len(chunks)} from input_records={len(records)}",
            file=sys.stdout,
        )
        return 0

    row_dicts = [chunk_to_dict(c) for c in chunks]
    try:
        result = merge_chunk_records_jsonl(out_path, row_dicts)
    except (ValueError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 1

    print(
        "Chunks: "
        f"input_records={len(records)} "
        f"chunks_built={len(chunks)} "
        f"merged_jsonl path={result.path} "
        f"existing={result.existing_count} "
        f"appended={result.appended} "
        f"skipped_duplicates={result.skipped_duplicates} "
        f"total={result.total_after}",
        file=sys.stdout,
    )
    return 0


def _first_listing_post_id(response: RedditJsonResponse) -> str | None:
    if not isinstance(response.payload, dict):
        return None
    data = response.payload.get("data")
    if not isinstance(data, dict):
        return None
    children = data.get("children")
    if not isinstance(children, list) or not children:
        return None
    first = children[0]
    if not isinstance(first, dict):
        return None
    first_data = first.get("data")
    if not isinstance(first_data, dict):
        return None
    post_id = first_data.get("id")
    return str(post_id) if post_id else None


def _format_rate_limit(response: RedditJsonResponse) -> str:
    rate = response.rate_limit
    return (
        "rate_limit="
        f"used:{rate.used if rate.used is not None else 'unknown'},"
        f"remaining:{rate.remaining if rate.remaining is not None else 'unknown'},"
        f"reset_seconds:{rate.reset_seconds if rate.reset_seconds is not None else 'unknown'}"
    )


def _non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError("value must be an integer") from e
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return parsed


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError("value must be an integer") from e
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be > 0")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(prog="reddit-rag", description="Local Reddit RAG tooling.")
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate-config", help="Validate subreddits and models config files.")
    p_validate.add_argument(
        "--config-dir",
        help="Optional config directory containing subreddits.yaml and models.yaml.",
    )
    p_validate.set_defaults(func=_cmd_validate_config)

    p_config = sub.add_parser("print-config", help="Load and print merged YAML configuration.")
    p_config.add_argument(
        "--config-dir",
        help="Optional config directory containing subreddits.yaml and models.yaml.",
    )
    p_config.set_defaults(func=_cmd_print_config)

    p_env = sub.add_parser("check-env", help="Verify required Reddit source settings are set.")
    p_env.set_defaults(func=_cmd_check_env)

    p_smoke = sub.add_parser("reddit-smoke-test", help="Run a read-only Reddit JSON smoke test.")
    p_smoke.add_argument(
        "--subreddit",
        default="redditdev",
        help="Public subreddit name used for the smoke test (default: redditdev).",
    )
    p_smoke.set_defaults(func=_cmd_json_smoke_test)

    p_json_smoke = sub.add_parser("json-smoke-test", help="Run a read-only Reddit JSON smoke test.")
    p_json_smoke.add_argument(
        "--subreddit",
        default="redditdev",
        help="Public subreddit name used for the smoke test (default: redditdev).",
    )
    p_json_smoke.set_defaults(func=_cmd_json_smoke_test)

    p_thread = sub.add_parser("fetch-thread", help="Fetch one Reddit thread JSON payload into raw storage.")
    p_thread.add_argument("permalink", help="Reddit thread permalink or URL.")
    p_thread.add_argument("--raw-dir", help="Optional raw data directory override.")
    p_thread.set_defaults(func=_cmd_fetch_thread)

    p_ingest = sub.add_parser("ingest-raw", help="Fetch configured subreddit listings and threads into raw storage.")
    p_ingest.add_argument(
        "--config-dir",
        help="Optional config directory containing subreddits.yaml and models.yaml.",
    )
    p_ingest.add_argument("--subreddit", help="Optional single subreddit name from config to ingest.")
    p_ingest.add_argument("--max-posts", type=_non_negative_int, help="Override max posts for this run.")
    p_ingest.add_argument("--max-comments", type=_non_negative_int, help="Override max comments for this run.")
    p_ingest.add_argument("--raw-dir", help="Optional raw data directory override.")
    p_ingest.add_argument(
        "--reset-checkpoint",
        action="store_true",
        help="Ignore and replace any existing raw ingestion checkpoint.",
    )
    p_ingest.set_defaults(func=_cmd_ingest_raw)

    p_norm = sub.add_parser(
        "normalize-posts",
        help="Normalize saved raw thread JSON into NormalizedPost records (JSONL and/or readable output).",
    )
    p_norm.add_argument(
        "--thread",
        help="Path to one saved raw thread JSON file (under .../threads/<id>.json).",
    )
    p_norm.add_argument(
        "--subreddit",
        help="Subreddit name; reads all JSON files from <raw-dir>/<name>/threads/.",
    )
    p_norm.add_argument(
        "--raw-dir",
        help="Override raw data root (default: REDDIT_RAG_RAW_DIR or <project>/data/raw).",
    )
    p_norm.add_argument(
        "--processed-dir",
        help="Override processed data root for default JSONL paths (default: REDDIT_RAG_PROCESSED_DIR or <project>/data/processed).",
    )
    p_norm.add_argument(
        "--output",
        help=(
            "JSONL output path (one NormalizedPost per line). Merges with existing file by reddit_id. "
            "Default when omitted: <processed>/<subreddit>/posts.jsonl (one file per subreddit)."
        ),
    )
    p_norm.add_argument(
        "--pretty",
        action="store_true",
        help="Print human-readable post content to stdout.",
    )
    p_norm.set_defaults(func=_cmd_normalize_posts)

    p_norm_comments = sub.add_parser(
        "normalize-comments",
        help="Normalize saved raw thread JSON into NormalizedComment records (JSONL and/or readable output).",
    )
    p_norm_comments.add_argument(
        "--thread",
        help="Path to one saved raw thread JSON file (under .../threads/<id>.json).",
    )
    p_norm_comments.add_argument(
        "--subreddit",
        help="Subreddit name; reads all JSON files from <raw-dir>/<name>/threads/.",
    )
    p_norm_comments.add_argument(
        "--raw-dir",
        help="Override raw data root (default: REDDIT_RAG_RAW_DIR or <project>/data/raw).",
    )
    p_norm_comments.add_argument(
        "--processed-dir",
        help="Override processed data root for default JSONL paths (default: REDDIT_RAG_PROCESSED_DIR or <project>/data/processed).",
    )
    p_norm_comments.add_argument(
        "--output",
        help=(
            "JSONL output path (one NormalizedComment per line). Merges with existing file by reddit_id. "
            "Default when omitted: <processed>/<subreddit>/comments.jsonl (one file per subreddit)."
        ),
    )
    p_norm_comments.add_argument(
        "--pretty",
        action="store_true",
        help="Print human-readable comment content to stdout.",
    )
    p_norm_comments.set_defaults(func=_cmd_normalize_comments)

    p_chunk = sub.add_parser(
        "create-chunks",
        help="Build chunk records from normalized posts/comments JSONL and merge into chunks.jsonl.",
    )
    p_chunk.add_argument(
        "--subreddit",
        help="Subreddit name; reads <processed>/<name>/posts.jsonl and comments.jsonl.",
    )
    p_chunk.add_argument("--posts", help="Explicit path to posts.jsonl (use with --comments and/or --output).")
    p_chunk.add_argument("--comments", help="Explicit path to comments.jsonl.")
    p_chunk.add_argument(
        "--processed-dir",
        help="Processed data root for default paths (default: REDDIT_RAG_PROCESSED_DIR or <project>/data/processed).",
    )
    p_chunk.add_argument(
        "--output",
        help=(
            "JSONL output path. Required when using only --posts/--comments without --subreddit. "
            "With --subreddit, defaults to <processed>/<subreddit>/chunks.jsonl."
        ),
    )
    p_chunk.add_argument(
        "--chunk-size",
        type=_positive_int,
        default=1500,
        help="Maximum characters per chunk (default: 1500).",
    )
    p_chunk.add_argument(
        "--chunk-overlap",
        type=_non_negative_int,
        default=200,
        help="Character overlap between consecutive chunks (default: 200; must be < chunk-size).",
    )
    p_chunk.add_argument(
        "--pretty",
        action="store_true",
        help="Print chunk JSON to stdout instead of writing JSONL.",
    )
    p_chunk.set_defaults(func=_cmd_chunk)

    args = parser.parse_args()
    code = args.func(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
