#!/usr/bin/env python3
"""
Optimized annotation fixer for Latin epigraphic inscriptions - Version 3
Corrects systematic errors in Gemini-generated annotations with efficient logic.
"""

import json
import re
from typing import List, Tuple, Dict, Set
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
        'carissimae', 'carissimo', 'carissimi', 'carissimus',
        'dulcissimo', 'dulcissimae', 'dulcissimi', 'dulcissimus',
        'optimo', 'optimae', 'optimi', 'optimus',
        'sanctissimae', 'sancto', 'sanctae', 'sanctus',
        'fidelissimo', 'fidelissimae',
        'incomparabili', 'incomparabilissimis',
        'clarissimi', 'egregio',
        'benemerenti', 'bene', 'merenti', 'merito', 'meritae',
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


def find_and_merge_formulas(transcription: str) -> List[Tuple[int, int, str]]:
    """
    Find formulaic phrases directly in the transcription text.
    Returns list of (start, end, label) for formulas found.
    """
    text_lower = transcription.lower()
    formulas = []

    # Define patterns with their labels
    patterns = [
        (r'\bdis\s+manibus\s+sacrum\b', 'DEDICATION_TO_THE_GODS'),
        (r'\bdis\s+manibus\b', 'DEDICATION_TO_THE_GODS'),
        (r'\bd\s*m\s*s\b', 'DEDICATION_TO_THE_GODS'),
        (r'\bd\s*m\b', 'DEDICATION_TO_THE_GODS'),
        (r'\bhic\s+situs\s+est\b', 'FUNERARY_FORMULA'),
        (r'\bhic\s+sita\s+est\b', 'FUNERARY_FORMULA'),
        (r'\bh\s*s\s*e\b', 'FUNERARY_FORMULA'),
        (r'\bsit\s+tibi\s+terra\s+levis\b', 'FUNERARY_FORMULA'),
        (r'\bs\s*t\s*t\s*l\b', 'FUNERARY_FORMULA'),
        (r'\bbene\s+merenti\b', 'BENE_MERENTI'),
        (r'\bbene\s+merito\b', 'BENE_MERENTI'),
        (r'\bb\s*m\b', 'BENE_MERENTI'),
        (r'\biovi\s+optimo\s+maximo\b', 'DEDICATION_TO_THE_GODS'),
        (r'\bi\s*o\s*m\b', 'DEDICATION_TO_THE_GODS'),
    ]

    # Find all matches
    for pattern, label in patterns:
        for match in re.finditer(pattern, text_lower):
            formulas.append((match.start(), match.end(), label))

    # Sort by start position and remove overlaps (keep longer spans)
    formulas.sort(key=lambda x: (x[0], -(x[1] - x[0])))

    # Remove overlapping formulas
    non_overlapping = []
    for formula in formulas:
        start, end, label = formula
        # Check if it overlaps with any already added
        overlaps = False
        for existing in non_overlapping:
            if not (end <= existing[0] or start >= existing[1]):
                overlaps = True
                break
        if not overlaps:
            non_overlapping.append(formula)

    return non_overlapping


def fix_single_annotation(transcription: str, annotations: List[List]) -> List[List]:
    """
    Fix annotations for a single inscription.
    Returns corrected annotations list.
    """
    if not annotations:
        return []

    # Find formulaic phrases in the text
    formulas = find_and_merge_formulas(transcription)

    # Create set of formula spans for quick lookup
    formula_spans = set()
    for start, end, label in formulas:
        formula_spans.add((start, end))

    # Pass 1: Filter and fix annotations
    filtered = []
    for start, end, label in annotations:
        # Skip if invalid
        if start >= end or start < 0 or end > len(transcription):
            continue

        entity_text = extract_text(transcription, start, end)
        if not entity_text:
            continue

        entity_lower = normalize_text(entity_text)

        # Skip if should be removed (adjectives/pronouns labeled as names)
        if should_remove_word(entity_text, label):
            continue

        # Skip if this span is part of a formula (will be added later)
        skip_for_formula = False
        for formula_start, formula_end in formula_spans:
            if start >= formula_start and end <= formula_end:
                # This annotation is inside a formula span, skip it
                skip_for_formula = True
                break
        if skip_for_formula:
            continue

        # Check context for measurement phrases (skip if it's a measurement)
        if label in ['AGE_PREFIX', 'AGE_YEARS', 'AGE_MONTHS', 'AGE_DAYS']:
            context_start = max(0, start - 30)
            context_end = min(len(transcription), end + 30)
            context = transcription[context_start:context_end].lower()

            if 'pedes' in context and 'fronte' in context:
                continue
            if 'locus' in context and 'pedum' in context:
                continue

        # Fix label if needed
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

        # Fix RELATIONSHIP words
        relationship_words = {
            'coniugi', 'conivx', 'coniux', 'uxori', 'uxor', 'marito',
            'pater', 'mater', 'patri', 'matri', 'parentes',
            'libertus', 'liberta', 'liberti', 'libertae', 'liberto',
            'patrono', 'patronus', 'patronae',
            'frater', 'fratri', 'soror',
            'filius', 'filia', 'filii', 'filiae', 'filio',
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

        filtered.append([start, end, new_label])

    # Pass 2: Add formula annotations
    for start, end, label in formulas:
        filtered.append([start, end, label])

    # Pass 3: Fix AGE_YEARS - Roman numerals after age prefix
    filtered.sort(key=lambda x: x[0])
    final = []
    for i, (start, end, label) in enumerate(filtered):
        entity_text = extract_text(transcription, start, end)

        # Check if this is a Roman numeral after an age prefix
        if re.match(r'^[IVX]+$', entity_text) and i > 0:
            prev_label = final[-1][2]
            if prev_label == 'AGE_PREFIX':
                label = 'AGE_YEARS'

        final.append([start, end, label])

    return final


def fix_annotations_file(input_path: str, output_path: str):
    """
    Fix all annotations in a JSONL file.
    """
    print(f"Reading from: {input_path}")

    fixed_count = 0
    total_count = 0
    total_removed = 0
    total_added = 0

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
                        new_count = len(fixed_annotations)

                        if original_count != new_count:
                            fixed_count += 1
                            if new_count < original_count:
                                total_removed += (original_count - new_count)
                            else:
                                total_added += (new_count - original_count)

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
    print(f"   Entities removed: {total_removed}")
    print(f"   Entities added: {total_added}")
    print(f"   Net change: {total_added - total_removed:+d}")
    print(f"   Output: {output_path}")


if __name__ == '__main__':
    input_file = 'real_data_w_generated_annotations_to_fix.jsonl'
    output_file = 'real_data_w_generated_annotations_FIXED.jsonl'

    fix_annotations_file(input_file, output_file)
