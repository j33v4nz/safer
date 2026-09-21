from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

from .client import GuardBlocked, inspect, require_allowed


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="safer", description="Check a prompt with the local Safer service.")
    commands = root.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="inspect text and print the policy decision")
    check.add_argument("text", nargs="?", help="prompt text; reads stdin when omitted")
    execute = commands.add_parser("exec", help="check explicit prompt text before running a command")
    execute.add_argument("--prompt", required=True, help="exact prompt text sent by the child command")
    execute.add_argument("program", nargs=argparse.REMAINDER, help="command after --")
    pipe = commands.add_parser("pipe", help="check stdin, then forward the untouched stdin to a command")
    pipe.add_argument("program", nargs=argparse.REMAINDER, help="command after --")
    antigravity = commands.add_parser("antigravity", aliases=["agy"], help="check a prompt, then send it to the Antigravity CLI")
    antigravity.add_argument("prompt", nargs="+", help="prompt text passed to agy")
    return root


def _command(program: list[str]) -> list[str]:
    if program[:1] == ["--"]:
        program = program[1:]
    if not program:
        raise SystemExit("a command is required after --")
    return program


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "check":
            text = args.text if args.text is not None else sys.stdin.read()
            result = inspect(text)
            print(json.dumps(result.payload, indent=2))
            return 0 if result.allowed else 3
        if args.command == "exec":
            require_allowed(args.prompt, source="cli-exec")
            return subprocess.run(_command(args.program), check=False).returncode
        if args.command == "pipe":
            text = sys.stdin.read()
            require_allowed(text, source="cli-stdin")
            return subprocess.run(_command(args.program), input=text, text=True, check=False).returncode
        if args.command in {"antigravity", "agy"}:
            prompt = " ".join(args.prompt)
            require_allowed(prompt, source="antigravity-cli")
            binary = os.environ.get("SAFER_ANTIGRAVITY_BIN", "agy")
            resolved = shutil.which(binary)
            if not resolved:
                raise RuntimeError(f"Antigravity binary not found: {binary}")
            return subprocess.run([resolved, prompt], check=False).returncode
    except GuardBlocked as exc:
        print(f"safer: {exc}", file=sys.stderr)
        return 3
    except RuntimeError as exc:
        print(f"safer: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
