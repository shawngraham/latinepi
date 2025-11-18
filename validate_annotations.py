#!/usr/bin/env python3
"""
Validation script for Gemini-annotated Latin inscriptions
Checks annotation quality and identifies potential issues
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Tuple


class AnnotationValidator:
    """Validates annotation quality and finds issues"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.stats = defaultdict(int)
        self.entity_counts = Counter()
        self.entity_examples = defaultdict(list)

    def validate_file(self, jsonl_path: str) -> Dict:
        """
        Validate an entire JSONL file of annotations

        Args:
            jsonl_path: Path to the JSONL file

        Returns:
            Dict with validation results and statistics
        """
        print(f"🔍 Validating annotations in: {jsonl_path}")
        print()

        records = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                try:
                    record = json.loads(line)
                    records.append(record)
                    self._validate_record(record, line_num)
                except json.JSONDecodeError as e:
                    self.errors.append(f"Line {line_num}: Invalid JSON - {e}")

        # Compute statistics
        self._compute_statistics(records)

        # Print report
        self._print_report(records)

        return {
            'total_records': len(records),
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'entity_counts': dict(self.entity_counts),
            'errors': self.errors,
            'warnings': self.warnings
        }

    def _validate_record(self, record: Dict, line_num: int):
        """Validate a single annotation record"""

        # Check required fields
        if 'id' not in record:
            self.warnings.append(f"Line {line_num}: Missing 'id' field")

        if 'transcription' not in record:
            self.errors.append(f"Line {line_num}: Missing 'transcription' field")
            return

        if 'annotations' not in record:
            self.errors.append(f"Line {line_num}: Missing 'annotations' field")
            return

        text = record['transcription']
        annotations = record['annotations']

        # Validate annotations structure
        if not isinstance(annotations, list):
            self.errors.append(
                f"Line {line_num}: 'annotations' must be a list, got {type(annotations)}"
            )
            return

        # Check each annotation
        for i, ann in enumerate(annotations):
            self._validate_annotation(ann, text, line_num, i, record['id'])

    def _validate_annotation(
        self,
        annotation: List,
        text: str,
        line_num: int,
        ann_index: int,
        record_id: str
    ):
        """Validate a single annotation span"""

        # Check structure
        if not isinstance(annotation, list) or len(annotation) != 3:
            self.errors.append(
                f"Line {line_num}, ann {ann_index}: Invalid format. "
                f"Expected [start, end, label], got {annotation}"
            )
            return

        start, end, label = annotation

        # Check types
        if not isinstance(start, int) or not isinstance(end, int):
            self.errors.append(
                f"Line {line_num}, ann {ann_index}: "
                f"start and end must be integers, got {type(start)}, {type(end)}"
            )
            return

        if not isinstance(label, str):
            self.errors.append(
                f"Line {line_num}, ann {ann_index}: "
                f"label must be string, got {type(label)}"
            )
            return

        # Check bounds
        if start < 0:
            self.errors.append(
                f"Line {line_num}, ann {ann_index}: "
                f"start index {start} is negative"
            )

        if end > len(text):
            self.errors.append(
                f"Line {line_num}, ann {ann_index}: "
                f"end index {end} exceeds text length {len(text)}"
            )

        if start >= end:
            self.errors.append(
                f"Line {line_num}, ann {ann_index}: "
                f"start {start} >= end {end}"
            )

        # Validate span extraction
        if 0 <= start < end <= len(text):
            span_text = text[start:end]

            # Check for empty spans
            if not span_text.strip():
                self.warnings.append(
                    f"Line {line_num}, ann {ann_index}: "
                    f"Empty or whitespace-only span at [{start}:{end}]"
                )

            # Track entity
            self.entity_counts[label] += 1

            # Store examples (limit to 5 per type)
            if len(self.entity_examples[label]) < 5:
                self.entity_examples[label].append({
                    'text': span_text,
                    'context': text,
                    'id': record_id
                })

    def _compute_statistics(self, records: List[Dict]):
        """Compute overall statistics"""
        self.stats['total_records'] = len(records)
        self.stats['total_entities'] = sum(self.entity_counts.values())

        # Count records with annotations
        self.stats['annotated_records'] = sum(
            1 for r in records if r.get('annotations')
        )

        # Count empty annotation records
        self.stats['empty_records'] = sum(
            1 for r in records if not r.get('annotations')
        )

        # Average entities per record
        if self.stats['annotated_records'] > 0:
            self.stats['avg_entities'] = (
                self.stats['total_entities'] / self.stats['annotated_records']
            )
        else:
            self.stats['avg_entities'] = 0

        # Count unique entity types
        self.stats['unique_entity_types'] = len(self.entity_counts)

    def _print_report(self, records: List[Dict]):
        """Print a detailed validation report"""

        print("=" * 70)
        print("📊 VALIDATION REPORT")
        print("=" * 70)
        print()

        # Overall Statistics
        print("📈 Overall Statistics:")
        print(f"   Total records: {self.stats['total_records']}")
        print(f"   Records with annotations: {self.stats['annotated_records']}")
        print(f"   Records without annotations: {self.stats['empty_records']}")
        print(f"   Total entities annotated: {self.stats['total_entities']}")
        print(f"   Unique entity types: {self.stats['unique_entity_types']}")
        print(f"   Avg entities per record: {self.stats['avg_entities']:.2f}")
        print()

        # Entity Type Distribution
        print("📋 Entity Type Distribution:")
        print(f"   {'Entity Type':<30} {'Count':>8} {'%':>6}")
        print("   " + "-" * 50)
        total = sum(self.entity_counts.values())
        for label, count in self.entity_counts.most_common():
            pct = (count / total * 100) if total > 0 else 0
            print(f"   {label:<30} {count:8d} {pct:5.1f}%")
        print()

        # Examples for each entity type
        print("📝 Example Annotations (up to 5 per type):")
        for label in sorted(self.entity_examples.keys()):
            examples = self.entity_examples[label]
            print(f"\n   {label}:")
            for ex in examples[:5]:
                # Truncate context if too long
                context = ex['context']
                if len(context) > 60:
                    context = context[:60] + "..."
                print(f"      • '{ex['text']}' in: {context}")
        print()

        # Errors
        if self.errors:
            print("❌ ERRORS FOUND:")
            for error in self.errors[:20]:  # Limit to first 20
                print(f"   {error}")
            if len(self.errors) > 20:
                print(f"   ... and {len(self.errors) - 20} more errors")
            print()
        else:
            print("✅ No errors found!")
            print()

        # Warnings
        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in self.warnings[:20]:  # Limit to first 20
                print(f"   {warning}")
            if len(self.warnings) > 20:
                print(f"   ... and {len(self.warnings) - 20} more warnings")
            print()
        else:
            print("✅ No warnings!")
            print()

        # Quality Assessment
        print("🎯 Quality Assessment:")
        error_rate = len(self.errors) / max(1, self.stats['total_records'])
        warning_rate = len(self.warnings) / max(1, self.stats['total_entities'])

        if error_rate == 0 and warning_rate < 0.01:
            quality = "🌟 EXCELLENT"
        elif error_rate < 0.01 and warning_rate < 0.05:
            quality = "✅ GOOD"
        elif error_rate < 0.05 and warning_rate < 0.10:
            quality = "⚠️  FAIR"
        else:
            quality = "❌ NEEDS REVIEW"

        print(f"   Overall Quality: {quality}")
        print(f"   Error rate: {error_rate:.2%}")
        print(f"   Warning rate: {warning_rate:.2%}")
        print()

        # Sample annotated texts
        print("📖 Sample Annotated Texts:")
        samples = [r for r in records if r.get('annotations')][:3]
        for i, record in enumerate(samples, 1):
            print(f"\n   Sample {i}:")
            print(f"   ID: {record.get('id', 'N/A')}")
            print(f"   Text: {record['transcription'][:80]}...")
            print(f"   Entities ({len(record['annotations'])}):")
            for start, end, label in record['annotations'][:10]:  # Max 10 entities
                entity_text = record['transcription'][start:end]
                print(f"      [{start:3d}:{end:3d}] {label:25s} = '{entity_text}'")
            if len(record['annotations']) > 10:
                print(f"      ... and {len(record['annotations']) - 10} more")

        print()
        print("=" * 70)

        # Final recommendation
        if self.errors:
            print("⚠️  RECOMMENDATION: Review and fix errors before training")
        elif warning_rate > 0.10:
            print("⚠️  RECOMMENDATION: Review warnings, but may be acceptable for training")
        else:
            print("✅ RECOMMENDATION: Annotations look good! Ready for training.")

        print("=" * 70)


def main():
    """Main execution"""
    if len(sys.argv) != 2:
        print("Usage: python validate_annotations.py <annotations.jsonl>")
        print()
        print("Example:")
        print("  python validate_annotations.py assets/gemini_annotations.jsonl")
        sys.exit(1)

    jsonl_path = sys.argv[1]

    if not Path(jsonl_path).exists():
        print(f"❌ Error: File not found: {jsonl_path}")
        sys.exit(1)

    validator = AnnotationValidator()
    results = validator.validate_file(jsonl_path)

    # Exit with error code if serious issues found
    if results['total_errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
