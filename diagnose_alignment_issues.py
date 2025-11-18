#!/usr/bin/env python3
"""
Diagnostic script to identify why entity spans fail alignment during .spacy conversion
Analyzes the alignment issues that cause 34-37% data loss in the training pipeline
"""

import spacy
import json
from pathlib import Path
from collections import Counter, defaultdict
import pandas as pd


def get_annotation_spans(record):
    """Safely navigates the nested dictionary to find the list of annotations."""
    try:
        return record['annotations']['annotations']['annotations']
    except (KeyError, TypeError):
        try:
            return record['annotations']['annotations']
        except (KeyError, TypeError):
            try:
                return record['annotations']
            except (KeyError, TypeError):
                return []


def diagnose_alignment_issues(input_path, output_csv="alignment_failures.csv"):
    """
    Deep dive into why entities fail alignment

    Args:
        input_path: Path to JSONL file with annotations
        output_csv: Where to save the failure analysis
    """

    print("🔍 Loading Latin spaCy model...")
    nlp = spacy.load('la_core_web_lg')

    print(f"📂 Analyzing alignment issues in: {input_path}\n")

    # Statistics tracking
    stats = {
        'total_records': 0,
        'total_entities': 0,
        'perfect_alignments': 0,
        'failed_alignments': 0,
        'expand_mode_fixes': 0,
        'contract_mode_fixes': 0,
        'shift_plus_one_fixes': 0,
        'shift_minus_one_fixes': 0
    }

    # Track failures by entity type
    failures_by_label = Counter()
    successes_by_label = Counter()

    # Detailed failure records
    failures = []

    # Failure reasons
    failure_reasons = Counter()

    with open(input_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            try:
                record = json.loads(line)
                stats['total_records'] += 1
            except json.JSONDecodeError:
                print(f"⚠️  Line {line_num}: Invalid JSON, skipping")
                continue

            text = record.get('transcription', '')
            if not text:
                continue

            annotations = get_annotation_spans(record)
            if not isinstance(annotations, list):
                continue

            doc = nlp.make_doc(text)

            for entity in annotations:
                if not isinstance(entity, list) or len(entity) != 3:
                    continue

                start, end, label = entity
                stats['total_entities'] += 1

                # Extract the expected entity text
                expected_text = text[start:end] if 0 <= start < end <= len(text) else "[OUT OF BOUNDS]"

                # Try different alignment strategies
                span = None
                alignment_method = None

                # Method 1: Original indices with expand mode
                span = doc.char_span(start, end, label=label, alignment_mode="expand")
                if span is not None:
                    alignment_method = "perfect_expand"
                    stats['perfect_alignments'] += 1
                    successes_by_label[label] += 1
                    continue

                # Method 2: Contract mode
                if span is None:
                    span = doc.char_span(start, end, label=label, alignment_mode="contract")
                    if span is not None:
                        alignment_method = "contract"
                        stats['contract_mode_fixes'] += 1
                        successes_by_label[label] += 1
                        continue

                # Method 3: Strict mode
                if span is None:
                    span = doc.char_span(start, end, label=label, alignment_mode="strict")
                    if span is not None:
                        alignment_method = "strict"
                        successes_by_label[label] += 1
                        continue

                # Method 4: +1 shift with expand
                if span is None:
                    span = doc.char_span(start + 1, end + 1, label=label, alignment_mode="expand")
                    if span is not None:
                        alignment_method = "shift_plus_one"
                        stats['shift_plus_one_fixes'] += 1
                        successes_by_label[label] += 1
                        continue

                # Method 5: -1 shift with expand
                if span is None:
                    span = doc.char_span(start - 1, end - 1, label=label, alignment_mode="expand")
                    if span is not None:
                        alignment_method = "shift_minus_one"
                        stats['shift_minus_one_fixes'] += 1
                        successes_by_label[label] += 1
                        continue

                # If we get here, the span failed all alignment methods
                stats['failed_alignments'] += 1
                failures_by_label[label] += 1

                # Diagnose WHY it failed
                failure_reason = diagnose_failure_reason(doc, text, start, end, expected_text)
                failure_reasons[failure_reason] += 1

                # Record detailed failure info
                failures.append({
                    'record_id': record.get('id', f'line_{line_num}'),
                    'full_text': text,
                    'expected_entity': expected_text,
                    'label': label,
                    'start': start,
                    'end': end,
                    'failure_reason': failure_reason,
                    'context': text[max(0, start-20):min(len(text), end+20)],
                    'doc_text': doc.text,
                    'tokens_around': get_tokens_around(doc, start, end)
                })

    # Print statistics
    print("=" * 70)
    print("📊 ALIGNMENT DIAGNOSTIC RESULTS")
    print("=" * 70)
    print()

    print("📈 Overall Statistics:")
    print(f"   Total records processed: {stats['total_records']}")
    print(f"   Total entities analyzed: {stats['total_entities']}")
    print(f"   Perfect alignments: {stats['perfect_alignments']} ({stats['perfect_alignments']/max(1,stats['total_entities'])*100:.1f}%)")
    print(f"   Failed alignments: {stats['failed_alignments']} ({stats['failed_alignments']/max(1,stats['total_entities'])*100:.1f}%)")
    print()

    if stats['contract_mode_fixes'] > 0 or stats['shift_plus_one_fixes'] > 0 or stats['shift_minus_one_fixes'] > 0:
        print("🔧 Alternative Alignment Methods That Worked:")
        if stats['contract_mode_fixes'] > 0:
            print(f"   Contract mode: {stats['contract_mode_fixes']}")
        if stats['shift_plus_one_fixes'] > 0:
            print(f"   Shift +1: {stats['shift_plus_one_fixes']}")
        if stats['shift_minus_one_fixes'] > 0:
            print(f"   Shift -1: {stats['shift_minus_one_fixes']}")
        print()

    print("🏷️  Failure Rate by Entity Type:")
    print(f"   {'Label':<30} {'Failed':>8} {'Success':>8} {'Fail Rate':>10}")
    print("   " + "-" * 60)

    all_labels = set(failures_by_label.keys()) | set(successes_by_label.keys())
    for label in sorted(all_labels):
        failed = failures_by_label[label]
        success = successes_by_label[label]
        total = failed + success
        fail_rate = (failed / total * 100) if total > 0 else 0
        print(f"   {label:<30} {failed:8d} {success:8d} {fail_rate:9.1f}%")
    print()

    print("🔍 Top Failure Reasons:")
    for reason, count in failure_reasons.most_common(10):
        pct = (count / stats['failed_alignments'] * 100) if stats['failed_alignments'] > 0 else 0
        print(f"   {reason:<50} {count:5d} ({pct:5.1f}%)")
    print()

    # Save detailed failures to CSV
    if failures:
        df = pd.DataFrame(failures)
        df.to_csv(output_csv, index=False)
        print(f"💾 Detailed failure analysis saved to: {output_csv}")
        print(f"   Total failures recorded: {len(failures)}")
        print()

        # Show sample failures
        print("📋 Sample Failures (first 5):")
        for i, failure in enumerate(failures[:5], 1):
            print(f"\n   Failure {i}:")
            print(f"   Text: {failure['full_text'][:60]}...")
            print(f"   Expected: '{failure['expected_entity']}' [{failure['start']}:{failure['end']}]")
            print(f"   Label: {failure['label']}")
            print(f"   Reason: {failure['failure_reason']}")
            print(f"   Tokens around: {failure['tokens_around']}")

    print()
    print("=" * 70)

    return stats, failures


def diagnose_failure_reason(doc, text, start, end, expected_text):
    """
    Determine why a span failed to align

    Returns a human-readable reason
    """

    # Check if indices are out of bounds
    if start < 0 or end > len(text) or start >= end:
        return "out_of_bounds"

    # Check if the span lands in whitespace
    if expected_text.strip() == "":
        return "whitespace_only"

    # Check if the span crosses token boundaries awkwardly
    # Find which tokens overlap with the span
    overlapping_tokens = []
    for token in doc:
        token_start = token.idx
        token_end = token.idx + len(token.text)

        # Check if there's any overlap
        if not (end <= token_start or start >= token_end):
            overlapping_tokens.append(token)

    if not overlapping_tokens:
        return "no_overlapping_tokens"

    # Check if span starts/ends in middle of token
    first_token = overlapping_tokens[0]
    last_token = overlapping_tokens[-1]

    first_token_start = first_token.idx
    first_token_end = first_token.idx + len(first_token.text)
    last_token_start = last_token.idx
    last_token_end = last_token.idx + len(last_token.text)

    starts_mid_token = (start > first_token_start and start < first_token_end)
    ends_mid_token = (end > last_token_start and end < last_token_end)

    if starts_mid_token and ends_mid_token:
        return "both_boundaries_mid_token"
    elif starts_mid_token:
        return "start_mid_token"
    elif ends_mid_token:
        return "end_mid_token"

    # Check for whitespace misalignment
    if text[start:start+1].isspace():
        return "starts_with_whitespace"
    if end > 0 and text[end-1:end].isspace():
        return "ends_with_whitespace"

    # Check if tokenization created unexpected splits
    expected_tokens = expected_text.split()
    actual_tokens = [t.text for t in overlapping_tokens]

    if len(actual_tokens) != len(expected_tokens):
        return f"tokenization_mismatch_expected_{len(expected_tokens)}_got_{len(actual_tokens)}"

    return "unknown_reason"


def get_tokens_around(doc, start, end):
    """Get string representation of tokens around the failed span"""
    tokens = []
    for token in doc:
        token_start = token.idx
        token_end = token.idx + len(token.text)

        # Get tokens that overlap or are nearby
        if abs(token_start - start) < 30 or abs(token_end - end) < 30:
            marker = ""
            if token_start <= start < token_end or token_start < end <= token_end:
                marker = " <<<"
            tokens.append(f"{token.text}{marker}")

    return " | ".join(tokens[:10])  # Limit to 10 tokens


def main():
    """Main execution"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python diagnose_alignment_issues.py <input.jsonl> [output.csv]")
        print()
        print("Example:")
        print("  python diagnose_alignment_issues.py assets/train_aligned.jsonl alignment_failures.csv")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "alignment_failures.csv"

    if not Path(input_file).exists():
        print(f"❌ Error: File not found: {input_file}")
        sys.exit(1)

    stats, failures = diagnose_alignment_issues(input_file, output_file)

    # Exit with status based on failure rate
    failure_rate = stats['failed_alignments'] / max(1, stats['total_entities'])
    if failure_rate > 0.10:  # More than 10% failures
        print(f"\n⚠️  WARNING: High failure rate ({failure_rate*100:.1f}%)")
        print("   Review the failure analysis CSV for details")
        sys.exit(1)
    else:
        print(f"\n✅ Acceptable failure rate ({failure_rate*100:.1f}%)")
        sys.exit(0)


if __name__ == "__main__":
    main()
