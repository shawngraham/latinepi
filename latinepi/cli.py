#!/usr/bin/env python3
"""
Main CLI entry point for latinepi tool.
"""
import argparse
import sys


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
        # For now, just print confirmation that args were parsed
        print(f"Input: {args.input}")
        print(f"Output: {args.output}")
        print(f"Format: {args.output_format}")
    except SystemExit as e:
        # argparse calls sys.exit() on error or --help
        # Re-raise to maintain expected behavior
        raise


if __name__ == "__main__":
    main()
