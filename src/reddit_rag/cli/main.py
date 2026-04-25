from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

import yaml

from reddit_rag import __version__
from reddit_rag.config import load_app_config
from reddit_rag.env import load_dotenv_from_project, missing_reddit_env


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
    missing = missing_reddit_env()
    if missing:
        print(
            "Missing required environment variables. Set them in the environment or in a .env file at the project root:",
            file=sys.stderr,
        )
        for name in missing:
            print(f"  {name}", file=sys.stderr)
        return 1
    print("All required Reddit API environment variables are set.", file=sys.stdout)
    return 0


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

    p_env = sub.add_parser("check-env", help="Verify required Reddit API credentials are set.")
    p_env.set_defaults(func=_cmd_check_env)

    args = parser.parse_args()
    code = args.func(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
