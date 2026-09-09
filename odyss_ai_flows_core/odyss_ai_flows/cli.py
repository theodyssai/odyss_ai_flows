from __future__ import annotations

import argparse
import sys

from importlib import resources
from pathlib import Path


_TEMPLATE_PACKAGE = "odyss_ai_flows._starter_templates"

_STARTER_FILES = {
    "starter_agents.md": Path("AGENTS.md"),
    "starter_main.py.txt": Path("main.py"),
    "global_config.json": Path("global_config.json"),
    "env.example.txt": Path(".env.example"),
    "gitignore.txt": Path(".gitignore"),
    "flow/config.json": Path("flow/config.json"),
    "flow/subject.py.txt": Path("flow/subject.py"),
    "flow/ideas.jinja2": Path("flow/ideas.jinja2"),
    "flow/final.jinja2": Path("flow/final.jinja2"),
}

_RESERVED_PATHS = (
    Path("AGENTS.md"),
    Path("main.py"),
    Path("global_config.json"),
    Path(".env.example"),
    Path(".gitignore"),
    Path("flow"),
)


def _init_project(target: Path) -> int:
    conflicts = [path for path in _RESERVED_PATHS if (target / path).exists()]

    if conflicts:
        print(
            "Cannot initialize: these starter paths already exist:",
            file=sys.stderr,
        )

        for path in conflicts:
            print(f"  {path.as_posix()}", file=sys.stderr)

        return 1

    template_root = resources.files(_TEMPLATE_PACKAGE)

    for resource_name, relative_target in _STARTER_FILES.items():
        source = template_root.joinpath(*Path(resource_name).parts)
        destination = target / relative_target
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    print(f"Initialized Odyss AI Flows project in {target.resolve()}")
    print(
        "Next: copy .env.example to .env.local, set your "
        "OpenRouter API key and model, then run python main.py"
    )

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="odyss",
        description="Odyss AI Flows project tools.",
    )

    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser(
        "init",
        help="Initialize a starter project in the current directory.",
    )

    return parser


def main() -> int:
    args = _build_parser().parse_args()

    if args.command == "init":
        return _init_project(Path.cwd())

    return 2
