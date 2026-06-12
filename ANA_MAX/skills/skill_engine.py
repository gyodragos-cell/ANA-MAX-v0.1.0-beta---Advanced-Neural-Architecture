"""ANA MAX skill engine compatibility entrypoint.

This module is intentionally non-mutating. It exists so audit/validation flows
can invoke skill routing commands without changing stable OS-20 runtime logic.
"""

from __future__ import annotations

import argparse
from typing import Any

from ANA_MAX.self_optimization.os3_common import print_raw_json


def run_skill(*, skill: str | None, dry_run: bool) -> dict[str, Any]:
    return {
        "schema": "ana.skills.skill_engine.placeholder.v1",
        "engine": "skill_engine",
        "skill": skill or "unspecified",
        "dry_run": dry_run,
        "status": "noop",
        "mutations": [],
        "overall_success": True,
        "note": "Compatibility placeholder; no runtime skill execution performed.",
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ANA MAX Skill Engine")
    parser.add_argument("--skill", default=None, help="Skill name to validate or route.")
    parser.add_argument("--dry-run", action="store_true", help="Do not mutate runtime state.")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    print_raw_json(run_skill(skill=args.skill, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
