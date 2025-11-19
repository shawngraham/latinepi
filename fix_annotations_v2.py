#!/usr/bin/env python3
"""
Comprehensive annotation fixer for Latin epigraphic inscriptions - Version 2
Corrects systematic errors in Gemini-generated annotations with improved logic.
"""

import json
import re
from typing import List, Tuple, Dict
from pathlib import Path


def normalize_text(text: str) -> str:
    """Normalize text for matching"""
    return text.lower().strip()


def extract_text(transcription: str, start: int, end: int) -> str:
    """Extract text for given span"""
    if 0 <= start < end <= len(transcription):
        return transcription[start:end]
    return ""


def should_remove_word(word: str, label: str) -> bool:
    """
    Determine if a word should be removed from annotations.
    These are common adjectives/pronouns that should NOT be annotated as entities.
    """
    word_lower = normalize_text(word)

    # Adjectives and descriptive words that are NOT names
    adjectives = {
        'pia', 'pius', 'piae', 'pii', 'pientissimo', 'pientissimae', 'pientis',
        'carissimae', 'carissimo', 'carissimi', 'carissimus', 'carissimae',
        'dulcissimo', 'dulcissimae', 'dulcissimi', 'dulcissimus',
        'optimo', 'optimae', 'optimi', 'optimus',
        'sanctissimae', 'sancto', 'sanctae', 'sanctus',
        'fidelissimo', 'fidelissimae',
        'incomparabili', 'incomparabilissimis',
        'clarissimi', 'egregio',
    }

    # Pronouns and particles
    particles = {
        'quae', 'qui', 'cum', 'quo', 'qua',
        'sine', 'ulla', 'omnibus',
        'intra', 'neque', 'unquam',
        'et', 'ob', 'de', 'ex', 'in', 'ad',
    }

    # These words should be removed if labeled as COGNOMEN, NOMEN, or RELATIONSHIP
    if label in ['COGNOMEN', 'NOMEN', 'RELATIONSHIP', 'DEDICATOR_NAME']:
        return word_lower in (adjectives | particles)

    return False


def merge_consecutive_spans(annotations: List[List], transcription: str,
                            pattern: str, new_label: str) -> List[List]:
    """
    Merge consecutive annotations that match a pattern into a single annotation.
    E.g., "hic" + "situs" + "est" -> single "hic situs est" FUNERARY_FORMULA
    """
    if not annotations:
        return []

    # Sort by start position
    sorted_anns = sorted(annotations, key=lambda x: x[0])
    result = []
    i = 0

    while i < len(sorted_anns):
        start, end, label = sorted_anns[i]

        # Extract the full phrase starting from this position
        # Look ahead to see if we can find the pattern
        j = i
        phrase_start = start
        phrase_parts = []

        # Collect consecutive tokens
        while j < len(sorted_anns):
            s, e, l = sorted_anns[j]
            text = extract_text(transcription, s, e)
            phrase_parts.append(text)

            # Build current phrase
            phrase = ' '.join(phrase_parts)
            phrase_lower = phrase.lower().strip()

            # Check if it matches the pattern
            if re.search(pattern, phrase_lower):
                # Found a match! Create merged annotation
                phrase_end = e
                result.append([phrase_start, phrase_end, new_label])
                i = j + 1  # Skip past all merged tokens
                break

            # Check if we've gone too far
            if j - i > 10 or s - phrase_start > 100:
                # Too far, break
                break

            j += 1
        else:
            # Didn't find pattern, keep original annotation
            result.append([start, end, label])
            i += 1

    return result


def fix_single_annotation(transcription: str, annotations: List[List]) -> List[List]:
    """
    Fix annotations for a single inscription.
    Returns corrected annotations list.
    """
    if not annotations:
        return []

    # First pass: Remove words that shouldn't be annotated
    filtered = []
    for start, end, label in annotations:
        entity_text = extract_text(transcription, start, end)

        # Skip if should be removed
        if should_remove_word(entity_text, label):
            continue

        # Skip if empty or invalid
        if not entity_text or start >= end:
            continue

        filtered.append([start, end, label])

    # Second pass: Merge formulaic phrases
    # Define patterns to merge
    merge_patterns = [
        (r'\bdis\s+manibus\s+sacrum\b', 'DEDICATION_TO_THE_GODS'),
        (r'\bdis\s+manibus\b', 'DEDICATION_TO_THE_GODS'),
        (r'\bhic\s+situs\s+est\b', 'FUNERARY_FORMULA'),
        (r'\bhic\s+sita\s+est\b', 'FUNERARY_FORMULA'),
        (r'\bsit\s+tibi\s+terra\s+levis\b', 'FUNERARY_FORMULA'),
        (r'\bbene\s+merenti\b', 'BENE_MERENTI'),
        (r'\bbene\s+merito\b', 'BENE_MERENTI'),
        (r'\biovi\s+optimo\s+maximo\b', 'DEDICATION_TO_THE_GODS'),
    ]

    result = filtered
    for pattern, label in merge_patterns:
        result = merge_consecutive_spans(result, transcription, pattern, label)

    # Third pass: Fix labels for specific word types
    final = []
    for start, end, label in result:
        entity_text = extract_text(transcription, start, end)
        entity_lower = normalize_text(entity_text)

        new_label = label

        # Fix AGE_PREFIX words
        age_prefix_words = {
            'vixit', 'vix', 'vivus',
            'annos', 'annorum', 'annis', 'anno', 'annum',
            'mensibus', 'menses',
            'diebus', 'dies',
        }
        if entity_lower in age_prefix_words:
            new_label = 'AGE_PREFIX'

        # Fix Roman numerals after age prefix
        if re.match(r'^[IVX]+$', entity_text) and final:
            prev_label = final[-1][2]
            if prev_label == 'AGE_PREFIX':
                new_label = 'AGE_YEARS'

        # Fix RELATIONSHIP words
        relationship_words = {
            'coniugi', 'conivx', 'coniux', 'uxori', 'uxor', 'marito',
            'pater', 'mater', 'patri', 'matri', 'parentes',
            'libertus', 'liberta', 'liberti', 'libertae', 'liberto',
            'patrono', 'patronus', 'patronae',
            'frater', 'fratri', 'soror',
            'filius', 'filia', 'filii', 'filiae', 'filio', 'filiae',
            'conservae',
        }
        if entity_lower in relationship_words:
            new_label = 'RELATIONSHIP'

        # Fix FUNERARY_FORMULA words
        funerary_words = {
            'fecit', 'fecerunt', 'posuit', 'posuerunt',
            'curavit', 'curaverunt', 'faciendum',
        }
        if entity_lower in funerary_words:
            new_label = 'FUNERARY_FORMULA'

        final.append([start, end, new_label])

    # Fourth pass: Remove annotations that are part of measurement phrases
    # Check context for measurement words
    cleaned = []
    for start, end, label in final:
        entity_text = extract_text(transcription, start, end)
        entity_lower = normalize_text(entity_text)

        # Check if this is part of a measurement phrase
        context_start = max(0, start - 30)
        context_end = min(len(transcription), end + 30)
        context = transcription[context_start:context_end].lower()

        # Skip if it's a measurement
        if 'pedes' in context and 'fronte' in context:
            # This is likely "in fronte pedes XVI" - not an age
            if label in ['AGE_PREFIX', 'AGE_YEARS', 'AGE_DAYS']:
                continue

        if 'locus' in context and 'pedum' in context:
            # This is "locus pedum" - not an age
            if label in ['AGE_PREFIX', 'AGE_YEARS']:
                continue

        cleaned.append([start, end, label])

    return cleaned


def fix_annotations_file(input_path: str, output_path: str):
    """
    Fix all annotations in a JSONL file.
    """
    print(f"Reading from: {input_path}")

    fixed_count = 0
    total_count = 0
    total_removed = 0

    with open(input_path, 'r', encoding='utf-8') as f_in:
        with open(output_path, 'w', encoding='utf-8') as f_out:
            for line_num, line in enumerate(f_in, 1):
                try:
                    record = json.loads(line)
                    total_count += 1

                    original_annotations = record.get('annotations', [])
                    original_count = len(original_annotations)

                    if original_annotations:
                        fixed_annotations = fix_single_annotation(
                            record['transcription'],
                            original_annotations
                        )

                        record['annotations'] = fixed_annotations
                        removed = original_count - len(fixed_annotations)
                        total_removed += removed

                        if removed > 0:
                            fixed_count += 1

                    f_out.write(json.dumps(record, ensure_ascii=False) + '\n')

                    if line_num % 100 == 0:
                        print(f"Processed {line_num} records...")

                except Exception as e:
                    print(f"Error on line {line_num} ({record.get('id', '?')}): {e}")
                    # Write original line if error
                    f_out.write(line)

    print(f"\n✅ Processing complete!")
    print(f"   Total records: {total_count}")
    print(f"   Records modified: {fixed_count}")
    print(f"   Total entities removed: {total_removed}")
    print(f"   Output: {output_path}")


if __name__ == '__main__':
    input_file = 'real_data_w_generated_annotations_to_fix.jsonl'
    output_file = 'real_data_w_generated_annotations_FIXED.jsonl'

    fix_annotations_file(input_file, output_file)
