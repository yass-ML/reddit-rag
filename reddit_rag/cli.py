from __future__ import annotations

import argparse
import sys
from dataclasses import asdict

import yaml

from reddit_rag.loaders import load_app_config
from reddit_rag.paths import resolve_config_dir


def _cmd_print_config(_args: argparse.Namespace) -> int:
    config_dir = resolve_config_dir()
    try:
        cfg = load_app_config(config_dir)
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


def main() -> None:
    parser = argparse.ArgumentParser(prog="reddit-rag", description="Local Reddit RAG tooling.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_config = sub.add_parser("print-config", help="Load and print merged YAML configuration.")
    p_config.set_defaults(func=_cmd_print_config)

    args = parser.parse_args()
    code = args.func(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
