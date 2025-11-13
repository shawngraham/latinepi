#!/usr/bin/env python3
"""
Main CLI entry point for latinepi tool.
"""
import argparse
import json
import sys
from pathlib import Path

# Support both running as script and as module
try:
    from latinepi.parser import read_inscriptions, extract_entities
except ModuleNotFoundError:
    # Running as script, use relative import
    from parser import read_inscriptions, extract_entities


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

    # Read inscriptions from input file
    try:
        inscriptions = read_inscriptions(args.input)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Could not read input file '{args.input}': {e}", file=sys.stderr)
        sys.exit(1)

    # Process each inscription and extract entities
    results = []
    total = len(inscriptions)

    print(f"Processing {total} inscription(s)...")

    for i, inscription in enumerate(inscriptions, start=1):
        # Get the text field from the inscription
        text = inscription.get('text', inscription.get('Text', ''))

        if not text:
            print(f"Warning: Inscription {i} has no 'text' field, skipping", file=sys.stderr)
            continue

        # Extract entities from the text
        entities = extract_entities(text)

        # Create result record with original ID if available and extracted entities
        result = {}
        if 'id' in inscription:
            result['inscription_id'] = inscription['id']
        elif 'Id' in inscription:
            result['inscription_id'] = inscription['Id']

        # Flatten the entity structure for output
        for entity_name, entity_data in entities.items():
            result[entity_name] = entity_data['value']
            result[f"{entity_name}_confidence"] = entity_data['confidence']

        results.append(result)

        # Print progress
        print(f"Processed inscription {i}/{total}")

    # Write results to output file
    output_path = Path(args.output)
    try:
        if args.output_format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        else:  # csv
            import csv
            if results:
                fieldnames = results[0].keys()
                with open(output_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(results)

    except Exception as e:
        print(f"Error: Could not write to output file '{args.output}': {e}", file=sys.stderr)
        sys.exit(1)

    # Print confirmation to stdout
    print(f"Successfully processed {len(results)} inscription(s) -> '{args.output}'")


if __name__ == "__main__":
    main()
