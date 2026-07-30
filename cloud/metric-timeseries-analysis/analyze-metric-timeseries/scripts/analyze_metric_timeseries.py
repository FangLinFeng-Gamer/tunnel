#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from metric_timeseries_analysis.analysis.profile_catalog import (
    get_profile_definition,
    list_profile_names,
    profile_definition_to_dict,
)
from metric_timeseries_analysis.service.analysis_service import MetricAnalysisService


def main(argv: list[str] | None = None) -> int:
    verbose_parent = argparse.ArgumentParser(add_help=False)
    verbose_parent.add_argument("--verbose", "-v", action="store_true", help=argparse.SUPPRESS)

    parser = argparse.ArgumentParser(description="Analyze cloud metric time-series data.")
    parser.add_argument("--verbose", "-v", action="store_true", help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser(
        "analyze",
        help="Analyze a metric using a MetricAnalysisSpec.",
        parents=[verbose_parent],
    )
    analyze.add_argument("--args", "-a", required=True, help="MetricAnalysisSpec as a JSON string.")

    subparsers.add_parser(
        "profiles",
        help="List supported analysis profiles.",
        parents=[verbose_parent],
    )

    profile = subparsers.add_parser(
        "profile",
        help="Show parameters for one analysis profile.",
        parents=[verbose_parent],
    )
    profile_subparsers = profile.add_subparsers(dest="profile_name", required=True)
    for profile_name in list_profile_names():
        definition = get_profile_definition(profile_name)
        profile_parser = profile_subparsers.add_parser(
            profile_name,
            help=definition.summary,
            description=f"{definition.summary}\n\n{definition.use_for}",
            formatter_class=argparse.RawTextHelpFormatter,
            parents=[verbose_parent],
        )
        profile_parser.set_defaults(profile_name=profile_name)
        for option in definition.options:
            profile_parser.add_argument(
                f"--{option.name.replace('_', '-')}",
                choices=option.choices or None,
                type=_argparse_type(option.value_type),
                metavar=option.value_type.upper() if not option.choices else None,
                help=_option_help(option),
            )

    args = parser.parse_args(argv)
    if args.command == "analyze":
        try:
            request = json.loads(args.args)
        except json.JSONDecodeError as exc:
            payload = {"success": False, "error": "invalid_request", "message": f"--args must be valid JSON: {exc}"}
        else:
            if not isinstance(request, dict):
                payload = {"success": False, "error": "invalid_request", "message": "--args must decode to a JSON object"}
            else:
                payload = MetricAnalysisService().analyze(request)
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return 0 if payload.get("success") else 1
    if args.command == "profiles":
        payload = {"profiles": list_profile_names()}
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return 0
    if args.command == "profile":
        definition = get_profile_definition(args.profile_name)
        payload = profile_definition_to_dict(definition)
        for option in definition.options:
            value = getattr(args, option.name, None)
            if value is not None:
                payload["example_analysis"][option.name] = value
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return 0
    return 2


def _argparse_type(value_type: str):
    if value_type == "integer":
        return int
    if value_type == "number":
        return float
    if value_type == "boolean":
        return _parse_boolean
    return str


def _parse_boolean(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected a boolean value")


def _option_help(option) -> str:
    parts = ["Required." if option.required else "Optional.", option.description]
    if option.default is not None:
        parts.append(f"Default: {option.default}.")
    if option.choices:
        parts.append("Choices: " + ", ".join(option.choices) + ".")
    return " ".join(parts)


if __name__ == "__main__":
    sys.exit(main())
