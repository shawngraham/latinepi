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
    from latinepi.edh_utils import download_edh_inscription
except ModuleNotFoundError:
    # Running as script, use relative import
    from parser import read_inscriptions, extract_entities
    from edh_utils import download_edh_inscription


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

    # Input/output arguments
    parser.add_argument(
        '--input',
        metavar='<input_file>',
        help='Path to input file (CSV or JSON)'
    )

    parser.add_argument(
        '--output',
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

    parser.add_argument(
        '--confidence-threshold',
        type=float,
        default=0.5,
        metavar='<threshold>',
        help='Minimum confidence score for entity extraction (0.0-1.0, default: 0.5)'
    )

    parser.add_argument(
        '--flag-ambiguous',
        action='store_true',
        help='Include low-confidence entities with ambiguous flag instead of omitting them'
    )

    # EDH download arguments
    parser.add_argument(
        '--download-edh',
        metavar='<inscription_id>',
        help='Download inscription from EDH API by ID (e.g., HD000001 or 123)'
    )

    parser.add_argument(
        '--download-dir',
        metavar='<directory>',
        help='Directory to save downloaded EDH inscriptions (required with --download-edh)'
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

    # Handle EDH download if requested
    if args.download_edh:
        if not args.download_dir:
            print("Error: --download-dir is required when using --download-edh", file=sys.stderr)
            sys.exit(1)

        try:
            output_file = download_edh_inscription(args.download_edh, args.download_dir)
            print(f"Successfully downloaded inscription {args.download_edh} to {output_file}")

            # If no input file specified, we're done after download
            if not args.input:
                sys.exit(0)

        except (ValueError, OSError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: Failed to download inscription: {e}", file=sys.stderr)
            sys.exit(1)

    # Validate required arguments for processing mode
    if not args.input:
        print("Error: --input is required (unless using --download-edh alone)", file=sys.stderr)
        sys.exit(1)

    if not args.output:
        print("Error: --output is required when processing inscriptions", file=sys.stderr)
        sys.exit(1)

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

        # Apply confidence threshold filtering and flatten the entity structure for output
        for entity_name, entity_data in entities.items():
            confidence = entity_data['confidence']

            # Check if entity meets confidence threshold
            if confidence < args.confidence_threshold:
                if args.flag_ambiguous:
                    # Include entity with ambiguous flag
                    result[entity_name] = entity_data['value']
                    result[f"{entity_name}_confidence"] = confidence
                    result[f"{entity_name}_ambiguous"] = True
                else:
                    # Omit entity from results (skip to next entity)
                    continue
            else:
                # Entity meets threshold, include it
                result[entity_name] = entity_data['value']
                result[f"{entity_name}_confidence"] = confidence

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
