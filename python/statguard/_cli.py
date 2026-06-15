"""
statguard CLI — validate data files against contracts from the terminal.

Usage:
    statguard validate --contract contract.sg --file data.parquet [--reference ref.parquet]
    statguard check   --contract contract.sg                       # syntax-check DSL only
"""

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="statguard",
        description="StatGuard data quality engine",
    )
    sub = parser.add_subparsers(dest="command")

    # statguard validate
    validate = sub.add_parser("validate", help="Validate a data file against a contract")
    validate.add_argument("--contract", required=True, help="Path to .sg DSL file")
    validate.add_argument("--file",     required=True, help="Path to data file (parquet/csv/json/ipc)")
    validate.add_argument("--reference", default=None, help="Optional reference data file for drift")
    validate.add_argument("--format",   choices=["summary", "json", "prometheus"], default="summary")
    validate.add_argument("--fail-on-warning", action="store_true")

    # statguard check
    check = sub.add_parser("check", help="Syntax-check a DSL file only")
    check.add_argument("--contract", required=True)

    args = parser.parse_args()

    if args.command == "check":
        _cmd_check(args)
    elif args.command == "validate":
        _cmd_validate(args)
    else:
        parser.print_help()
        sys.exit(1)


def _cmd_check(args) -> None:
    from statguard import validate_dsl
    try:
        dsl = open(args.contract).read()
        name = validate_dsl(dsl)
        print(f"✓ DSL valid — dataset: {name}")
    except Exception as e:
        print(f"✗ DSL error: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_validate(args) -> None:
    from statguard import DataContract, execute_file
    try:
        contract = DataContract.from_file(args.contract)
        report   = execute_file(contract, args.file, args.reference)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(2)

    if args.format == "json":
        print(report.to_json_pretty())
    elif args.format == "prometheus":
        print(report.to_prometheus())
    else:
        print(report.summary())

    fail = not report.passed
    if args.fail_on_warning:
        fail = fail or report.violation_count > 0

    sys.exit(1 if fail else 0)
