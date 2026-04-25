from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

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

    args = parser.parse_args()
    code = args.func(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
