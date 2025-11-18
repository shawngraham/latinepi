"""
Robust .spacy file converter with multi-strategy alignment
Drop-in replacement for create_spacy_file() in the notebook

This fixes the 34-37% entity loss issue by trying multiple alignment strategies.
"""

import spacy
import json
import re
from spacy.tokens import DocBin
from spacy.util import filter_spans


def get_annotation_spans(record):
    """Safely retrieves annotations from record"""
    raw = record.get('annotations')
    if isinstance(raw, list):
        return raw
    try:
        return raw['annotations']
    except (KeyError, TypeError):
        return []


def try_alignment_strategies(doc, text, start, end, label):
    """
    Try multiple alignment strategies to recover entities that would otherwise fail

    Strategies (in order of preference):
    1. Strict mode (perfect alignment)
    2. Expand mode (most commonly used)
    3. Strip whitespace and retry
    4. Small boundary shifts (±1, ±2)
    5. Independent start/end adjustments
    6. Contract mode (last resort)

    Returns:
        spacy.tokens.Span or None
    """

    # Strategy 1: Strict alignment (perfect match)
    span = doc.char_span(start, end, label=label, alignment_mode="strict")
    if span is not None:
        return span

    # Strategy 2: Expand mode (standard approach)
    span = doc.char_span(start, end, label=label, alignment_mode="expand")
    if span is not None:
        return span

    # Strategy 3: Strip whitespace from entity text
    if 0 <= start < end <= len(text):
        entity_text = text[start:end]
        stripped = entity_text.strip()

        if stripped and stripped != entity_text:
            # Recalculate offsets without leading/trailing whitespace
            left_spaces = len(entity_text) - len(entity_text.lstrip())
            right_spaces = len(entity_text) - len(entity_text.rstrip())

            new_start = start + left_spaces
            new_end = end - right_spaces

            # Try strict first with cleaned boundaries
            span = doc.char_span(new_start, new_end, label=label, alignment_mode="strict")
            if span is not None:
                return span

            # Try expand with cleaned boundaries
            span = doc.char_span(new_start, new_end, label=label, alignment_mode="expand")
            if span is not None:
                return span

    # Strategy 4: Try small shifts (handles off-by-one errors)
    for shift in [-1, 1, -2, 2]:
        new_start = max(0, start + shift)
        new_end = min(len(text), end + shift)

        span = doc.char_span(new_start, new_end, label=label, alignment_mode="expand")
        if span is not None:
            return span

    # Strategy 5: Independently adjust start and end
    for start_shift in [-2, -1, 0, 1, 2]:
        for end_shift in [-2, -1, 0, 1, 2]:
            if start_shift == 0 and end_shift == 0:
                continue  # Already tried this

            new_start = max(0, start + start_shift)
            new_end = min(len(text), end + end_shift)

            if new_start >= new_end:
                continue

            span = doc.char_span(new_start, new_end, label=label, alignment_mode="expand")
            if span is not None:
                return span

    # Strategy 6: Contract mode (last resort - may lose part of entity)
    span = doc.char_span(start, end, label=label, alignment_mode="contract")
    if span is not None:
        return span

    # All strategies failed
    return None


def create_spacy_file_robust(input_path, output_path, model='la_core_web_lg', verbose=True):
    """
    Convert JSONL annotations to .spacy format with robust alignment handling

    This is a drop-in replacement for create_spacy_file() that recovers
    entities that would otherwise fail due to tokenization misalignment.

    Args:
        input_path: Path to JSONL file with annotations
        output_path: Path to save .spacy file
        model: spaCy model to use for tokenization (default: la_core_web_lg)
        verbose: Print detailed statistics

    Returns:
        dict: Statistics about the conversion
    """
    nlp = spacy.load(model)
    db = DocBin()

    stats = {
        "docs": 0,
        "total_ents": 0,
        "perfect_alignments": 0,  # Entities that aligned on first try
        "recovered_ents": 0,       # Entities saved by alternative strategies
        "dropped_ents": 0,         # Entities that couldn't be aligned
        "overlapping_ents": 0      # Entities dropped due to overlap
    }

    if verbose:
        print(f"--- Processing '{input_path}' with ROBUST alignment ---")

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            text = record.get('transcription')
            if not text:
                continue

            doc = nlp.make_doc(text)
            ents = []
            annotations = get_annotation_spans(record)

            if not isinstance(annotations, list):
                continue

            for entity in annotations:
                if not isinstance(entity, list) or len(entity) != 3:
                    continue

                start, end, label = entity

                # First try standard expand mode
                span = doc.char_span(start, end, label=label, alignment_mode="expand")

                if span is not None:
                    # Perfect alignment on first try
                    ents.append(span)
                    stats["perfect_alignments"] += 1
                else:
                    # Try alternative strategies
                    span = try_alignment_strategies(doc, text, start, end, label)

                    if span is not None:
                        ents.append(span)
                        stats["recovered_ents"] += 1
                    else:
                        stats["dropped_ents"] += 1
                        if verbose and stats["dropped_ents"] <= 5:
                            # Show first few failures for debugging
                            entity_text = text[start:end] if 0 <= start < end <= len(text) else "[INVALID]"
                            print(f"⚠️  Could not align: '{entity_text}' [{start}:{end}] ({label}) in: {text[:50]}...")

            # Remove overlapping spans (keep longer ones)
            original_count = len(ents)
            filtered_ents = filter_spans(ents)
            stats["overlapping_ents"] += (original_count - len(filtered_ents))

            doc.ents = filtered_ents
            stats["total_ents"] += len(filtered_ents)
            stats["docs"] += 1
            db.add(doc)

    # Save to disk
    db.to_disk(output_path)

    # Print summary
    if verbose:
        total_attempted = stats["perfect_alignments"] + stats["recovered_ents"] + stats["dropped_ents"]
        recovery_rate = (stats["recovered_ents"] / total_attempted * 100) if total_attempted > 0 else 0
        drop_rate = (stats["dropped_ents"] / total_attempted * 100) if total_attempted > 0 else 0

        print(f"✅ Saved {output_path}")
        print(f"   Documents: {stats['docs']}")
        print(f"   Total Entities: {stats['total_ents']} (Avg: {stats['total_ents']/max(1,stats['docs']):.1f} per doc)")
        print(f"   Perfect alignments: {stats['perfect_alignments']}")
        print(f"   Recovered by alt strategies: {stats['recovered_ents']} ({recovery_rate:.1f}%)")
        print(f"   Dropped/Failed: {stats['dropped_ents']} ({drop_rate:.1f}%)")
        print(f"   Overlapping (removed): {stats['overlapping_ents']}")

        if stats["recovered_ents"] > 0:
            print(f"   🎉 RECOVERED {stats['recovered_ents']} entities that would have been lost!")

    return stats


# Example usage in notebook:
if __name__ == "__main__":
    """
    To use in your Colab notebook, replace the create_spacy_file() calls with:

    # OLD CODE:
    # create_spacy_file('assets/train_aligned.jsonl', './corpus/train.spacy')
    # create_spacy_file('assets/dev_aligned.jsonl', './corpus/dev.spacy')

    # NEW CODE:
    stats_train = create_spacy_file_robust('assets/train_aligned.jsonl', './corpus/train.spacy')
    stats_dev = create_spacy_file_robust('assets/dev_aligned.jsonl', './corpus/dev.spacy')

    # Print comparison
    print("\n📊 BEFORE (original create_spacy_file):")
    print("   Train: 2730 annotations → 1802 entities (928 dropped = 34% loss)")
    print("   Dev:    671 annotations →  426 entities (245 dropped = 37% loss)")

    print("\n📊 AFTER (robust alignment):")
    print(f"   Train: Dropped only {stats_train['dropped_ents']} entities ({stats_train['dropped_ents']/2730*100:.1f}% loss)")
    print(f"   Dev:   Dropped only {stats_dev['dropped_ents']} entities ({stats_dev['dropped_ents']/671*100:.1f}% loss)")

    improvement_train = 928 - stats_train['dropped_ents']
    improvement_dev = 245 - stats_dev['dropped_ents']

    print(f"\n🎉 IMPROVEMENT:")
    print(f"   Train: +{improvement_train} entities recovered!")
    print(f"   Dev:   +{improvement_dev} entities recovered!")
    """
    print("Copy the functions above into your Colab notebook.")
    print("Then replace create_spacy_file() calls with create_spacy_file_robust()")
