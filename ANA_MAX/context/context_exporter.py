#!/usr/bin/env python3
"""Compatibility wrapper for ANA MAX context export."""

from __future__ import annotations

from ANA_MAX.context.context_injector import (
    build_context_bundle,
    build_export,
    build_arg_parser,
    export_agent_bootstrap_prompt,
    main,
)

__all__ = [
    "build_context_bundle",
    "build_export",
    "build_arg_parser",
    "export_agent_bootstrap_prompt",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
