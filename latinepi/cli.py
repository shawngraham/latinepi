#!/usr/bin/env python3
"""
Main CLI entry point for latinepi tool.
"""
import argparse
import sys
from pathlib import Path


def create_parser():
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog='latinepi',
        description='Extract structured personal data from Roman Latin epigraphic inscriptions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  latinepi --input inscriptions.csv --output structured_data.json
  latinepi --input batch.json --output results.csv --output-format csv
        """
    )

    # Required arguments
    parser.add_argument(
        '--input',
        required=True,
        metavar='<input_file>',
        help='Path to input file (CSV or JSON)'
    )

    parser.add_argument(
        '--output',
        required=True,
        metavar='<output_file>',
        help='Path to output file'
    )

    # Optional arguments
    parser.add_argument(
        '--output-format',
        choices=['json', 'csv'],
        default='json',
        metavar='{json,csv}',
        help='Output format (default: json)'
    )

    return parser


def main():
    """Main entry point for the CLI."""
    parser = create_parser()

    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse calls sys.exit() on error or --help
        # Re-raise to maintain expected behavior
        raise

    # Check if input file exists
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{args.input}' does not exist", file=sys.stderr)
        sys.exit(1)

    # Try to read the input file to ensure it's accessible
    try:
        with open(input_path, 'r') as f:
            # Just verify we can read it; we'll process contents later
            f.read()
    except Exception as e:
        print(f"Error: Could not read input file '{args.input}': {e}", file=sys.stderr)
        sys.exit(1)

    # Write placeholder string to output file
    output_path = Path(args.output)
    try:
        with open(output_path, 'w') as f:
            f.write("latinepi: output placeholder\n")
    except Exception as e:
        print(f"Error: Could not write to output file '{args.output}': {e}", file=sys.stderr)
        sys.exit(1)

    # Print confirmation to stdout
    print(f"Successfully processed '{args.input}' -> '{args.output}'")


if __name__ == "__main__":
    main()
