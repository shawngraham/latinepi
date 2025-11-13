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
    from latinepi.edh_utils import download_edh_inscription, search_edh_inscriptions
except ModuleNotFoundError:
    # Running as script, use relative import
    from parser import read_inscriptions, extract_entities
    from edh_utils import download_edh_inscription, search_edh_inscriptions


def create_parser():
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog='latinepi',
        description='Extract structured personal data from Roman Latin epigraphic inscriptions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process local CSV file to JSON
  latinepi --input inscriptions.csv --output results.json

  # Process with CSV output and higher confidence threshold
  latinepi --input data.json --output results.csv --output-format csv \\
           --confidence-threshold 0.8

  # Include low-confidence entities with ambiguous flag
  latinepi --input data.csv --output results.json --flag-ambiguous

  # Download inscription from EDH by ID
  latinepi --download-edh HD000001 --download-dir ./edh_data/

  # Download and process in one command
  latinepi --download-edh 123 --download-dir ./edh/ \\
           --input ./edh/HD000123.json --output results.csv

For more information, see: https://github.com/yourrepo/latinitas
        """
    )

    # Input/Output group
    io_group = parser.add_argument_group('Input/Output')
    io_group.add_argument(
        '--input',
        metavar='<file>',
        help='Input file containing inscriptions (CSV or JSON format)'
    )

    io_group.add_argument(
        '--output',
        metavar='<file>',
        help='Output file for extracted entities'
    )

    io_group.add_argument(
        '--output-format',
        choices=['json', 'csv'],
        default='json',
        metavar='{json,csv}',
        help='Output format (default: json)'
    )

    # Extraction options group
    extraction_group = parser.add_argument_group('Entity Extraction Options')
    extraction_group.add_argument(
        '--confidence-threshold',
        type=float,
        default=0.5,
        metavar='<0.0-1.0>',
        help='Minimum confidence score for entities (default: 0.5)'
    )

    extraction_group.add_argument(
        '--flag-ambiguous',
        action='store_true',
        help='Include low-confidence entities with "ambiguous" flag'
    )

    # EDH download group
    edh_group = parser.add_argument_group('EDH API Download')
    edh_group.add_argument(
        '--download-edh',
        metavar='<id>',
        help='Download inscription from EDH (e.g., HD000001 or 123)'
    )

    edh_group.add_argument(
        '--download-dir',
        metavar='<directory>',
        help='Directory for downloaded files (required with --download-edh)'
    )

    # EDH search group
    search_group = parser.add_argument_group('EDH Search Options')
    search_group.add_argument(
        '--search-edh',
        action='store_true',
        help='Search and download multiple inscriptions from EDH API'
    )

    search_group.add_argument(
        '--search-province',
        metavar='<province>',
        help='Roman province (e.g., Dalmatia, "Germania Superior")'
    )

    search_group.add_argument(
        '--search-country',
        metavar='<country>',
        help='Modern country name (e.g., Italy, Germany)'
    )

    search_group.add_argument(
        '--search-findspot-modern',
        metavar='<location>',
        help='Modern findspot with wildcards (e.g., rome*, köln*)'
    )

    search_group.add_argument(
        '--search-findspot-ancient',
        metavar='<location>',
        help='Ancient findspot with wildcards (e.g., aquae*, colonia*)'
    )

    search_group.add_argument(
        '--search-bbox',
        metavar='<minLong,minLat,maxLong,maxLat>',
        help='Geographic bounding box (e.g., 11,47,12,48 for Alpine region)'
    )

    search_group.add_argument(
        '--search-year-from',
        type=int,
        metavar='<year>',
        help='Year not before (use negative for BC, e.g., -50 for 50 BC)'
    )

    search_group.add_argument(
        '--search-year-to',
        type=int,
        metavar='<year>',
        help='Year not after (e.g., 200 for 200 AD)'
    )

    search_group.add_argument(
        '--search-limit',
        type=int,
        default=100,
        metavar='<n>',
        help='Maximum inscriptions to download (default: 100)'
    )

    search_group.add_argument(
        '--search-workers',
        type=int,
        default=10,
        metavar='<n>',
        help='Parallel download workers (default: 10, max: 50)'
    )

    search_group.add_argument(
        '--no-resume',
        action='store_true',
        help='Re-download files that already exist (default: skip existing)'
    )

    return parser


def validate_args(args, parser):
    """
    Validate argument combinations and values.

    Args:
        args: Parsed arguments from argparse
        parser: ArgumentParser instance for error messages

    Returns:
        None (exits on validation errors)
    """
    # Validate confidence threshold range
    if not (0.0 <= args.confidence_threshold <= 1.0):
        print("Error: --confidence-threshold must be between 0.0 and 1.0", file=sys.stderr)
        print(f"       Got: {args.confidence_threshold}", file=sys.stderr)
        sys.exit(1)

    # Check for --download-dir without --download-edh or --search-edh
    if args.download_dir and not args.download_edh and not args.search_edh:
        print("Warning: --download-dir specified without --download-edh or --search-edh (will be ignored)", file=sys.stderr)

    # Check for required combinations
    if args.download_edh and not args.download_dir:
        print("Error: --download-dir is required when using --download-edh", file=sys.stderr)
        sys.exit(1)

    if args.search_edh and not args.download_dir:
        print("Error: --download-dir is required when using --search-edh", file=sys.stderr)
        sys.exit(1)

    # Check if at least one action is specified
    if not args.download_edh and not args.search_edh and not args.input:
        parser.print_help(sys.stderr)
        print("\nError: Either --download-edh, --search-edh, or --input must be specified", file=sys.stderr)
        sys.exit(1)

    # Check for output when processing inscriptions
    if args.input and not args.output:
        print("Error: --output is required when processing inscriptions with --input", file=sys.stderr)
        sys.exit(1)

    # Check for extraction options without input
    if not args.input:
        if args.flag_ambiguous:
            print("Warning: --flag-ambiguous specified without --input (will be ignored)", file=sys.stderr)


def main():
    """Main entry point for the CLI."""
    parser = create_parser()

    try:
        args = parser.parse_args()
    except SystemExit as e:
        # argparse calls sys.exit() on error or --help
        # Re-raise to maintain expected behavior
        raise

    # Validate arguments
    validate_args(args, parser)

    # Handle EDH download if requested
    if args.download_edh:
        try:
            print(f"Downloading inscription {args.download_edh} from EDH API...", file=sys.stderr)
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

    # Handle EDH search if requested
    if args.search_edh:
        # Collect search parameters
        search_params = {
            'out_dir': args.download_dir,
            'province': args.search_province,
            'country': args.search_country,
            'fo_modern': args.search_findspot_modern,
            'fo_antik': args.search_findspot_ancient,
            'bbox': args.search_bbox,
            'year_from': args.search_year_from,
            'year_to': args.search_year_to,
            'max_results': args.search_limit,
            'workers': args.search_workers,
            'resume': not args.no_resume
        }

        try:
            downloaded_files = search_edh_inscriptions(**search_params)
            print(f"Successfully downloaded {len(downloaded_files)} inscriptions to {args.download_dir}")

            # If no input file specified, we're done after search
            if not args.input:
                sys.exit(0)

        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: Search failed: {e}", file=sys.stderr)
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
                # Collect all unique fieldnames from all records
                # (different records may have different fields due to threshold filtering)
                all_fieldnames = set()
                for result in results:
                    all_fieldnames.update(result.keys())

                # Sort fieldnames for consistent column ordering
                # inscription_id first, then alphabetically
                fieldnames = sorted(all_fieldnames)
                if 'inscription_id' in fieldnames:
                    fieldnames.remove('inscription_id')
                    fieldnames = ['inscription_id'] + fieldnames

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
