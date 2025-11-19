#!/usr/bin/env python3
"""
Comprehensive annotation fixer for Latin epigraphic inscriptions.
Corrects systematic errors in Gemini-generated annotations.
"""

import json
import re
from typing import List, Tuple, Dict
from pathlib import Path


# Common Latin adjectives/descriptors that are NOT names
COMMON_ADJECTIVES = {
    'pia', 'pius', 'piae', 'pii', 'pientissimo', 'pientissimae',
    'carissimae', 'carissimo', 'carissimi', 'carissimus',
    'dulcissimo', 'dulcissimae', 'dulcissimi',
    'optimo', 'optimae', 'optimi',
    'sanctissimae', 'sancto', 'sanctae',
    'fidelissimo', 'fidelissimae',
    'incomparabili', 'incomparabilissimis',
    'bene', 'merenti', 'merito',
    'libens', 'libentes',
    'quae', 'qui', 'cum', 'quo', 'qua',
    'sine', 'ulla', 'omnibus',
    'intra', 'neque', 'unquam',
    'animo',
}

# Common funerary formulas that should be single spans
FUNERARY_FORMULAS = [
    r'\bhic\s+situs\s+est\b',
    r'\bhic\s+sita\s+est\b',
    r'\bsit\s+tibi\s+terra\s+levis\b',
    r'\bh\s+s\s+e\b',
    r'\bs\s+t\s+t\s+l\b',
    r'\bd\s*m\s*s\b',
]

# Dedication formulas
DEDICATION_FORMULAS = [
    r'\bdis\s+manibus\b',
    r'\bd\s*m\b',
    r'\biovi\s+optimo\s+maximo\b',
    r'\bapollin[io]\s+augusto\b',
]

def normalize_text(text: str) -> str:
    """Normalize text for matching"""
    return text.lower().strip()


def is_adjective(word: str) -> bool:
    """Check if a word is a common Latin adjective"""
    return normalize_text(word) in COMMON_ADJECTIVES


def is_measurement_phrase(text: str) -> bool:
    """Check if text is a measurement (e.g., 'pedes XVI', 'in fronte')"""
    measurement_patterns = [
        r'in\s+fronte\s+pedes',
        r'in\s+agro\s+pedes',
        r'pedes\s+[IVX]+',
        r'locus\s+pedum',
    ]
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in measurement_patterns)


def is_age_component(word: str) -> bool:
    """Check if word is part of age expression"""
    age_words = {
        'annorum', 'annos', 'annis', 'ann', 'anno', 'annum',
        'mensibus', 'menses', 'mens', 'men',
        'diebus', 'dies', 'die',
        'vixit', 'vix', 'vivus',
    }
    return normalize_text(word) in age_words


def extract_text(transcription: str, start: int, end: int) -> str:
    """Extract text for given span"""
    if 0 <= start < end <= len(transcription):
        return transcription[start:end]
    return ""


def fix_single_annotation(transcription: str, annotations: List[List]) -> List[List]:
    """
    Fix annotations for a single inscription.
    Returns corrected annotations list.
    """
    if not annotations:
        return []

    fixed_annotations = []
    text_lower = transcription.lower()

    # Sort annotations by start position
    sorted_anns = sorted(annotations, key=lambda x: x[0])

    i = 0
    while i < len(sorted_anns):
        start, end, label = sorted_anns[i]
        entity_text = extract_text(transcription, start, end)
        entity_lower = normalize_text(entity_text)

        skip = False

        # Skip if empty or invalid
        if not entity_text or start >= end:
            i += 1
            continue

        # Fix: Remove adjectives misidentified as names/cognomens
        if label in ['COGNOMEN', 'NOMEN', 'RELATIONSHIP'] and is_adjective(entity_text):
            # Skip this annotation - it's an adjective, not a name
            i += 1
            continue

        # Fix: Combine "hic situs est" into single FUNERARY_FORMULA
        if entity_lower == 'hic' and i + 2 < len(sorted_anns):
            next1 = sorted_anns[i + 1]
            next2 = sorted_anns[i + 2]
            text1 = extract_text(transcription, next1[0], next1[1]).lower()
            text2 = extract_text(transcription, next2[0], next2[1]).lower()

            if text1 in ['situs', 'sita'] and text2 == 'est':
                # Combine into single formula
                combined_end = next2[1]
                fixed_annotations.append([start, combined_end, 'FUNERARY_FORMULA'])
                i += 3  # Skip next two
                continue

        # Fix: Combine "sit tibi terra levis" into single FUNERARY_FORMULA
        if entity_lower == 'sit' and i + 3 < len(sorted_anns):
            next1 = sorted_anns[i + 1]
            next2 = sorted_anns[i + 2]
            next3 = sorted_anns[i + 3]
            text1 = extract_text(transcription, next1[0], next1[1]).lower()
            text2 = extract_text(transcription, next2[0], next2[1]).lower()
            text3 = extract_text(transcription, next3[0], next3[1]).lower()

            if text1 == 'tibi' and text2 == 'terra' and text3 == 'levis':
                # Combine into single formula
                combined_end = next3[1]
                fixed_annotations.append([start, combined_end, 'FUNERARY_FORMULA'])
                i += 4  # Skip next three
                continue

        # Fix: "Dis Manibus" should be single DEDICATION_TO_THE_GODS
        if entity_lower == 'dis' and i + 1 < len(sorted_anns):
            next1 = sorted_anns[i + 1]
            text1 = extract_text(transcription, next1[0], next1[1]).lower()

            if text1 == 'manibus':
                combined_end = next1[1]
                fixed_annotations.append([start, combined_end, 'DEDICATION_TO_THE_GODS'])
                i += 2
                continue

        # Fix: "Dis Manibus sacrum" should be single DEDICATION_TO_THE_GODS
        if entity_lower == 'dis' and i + 2 < len(sorted_anns):
            next1 = sorted_anns[i + 1]
            next2 = sorted_anns[i + 2]
            text1 = extract_text(transcription, next1[0], next1[1]).lower()
            text2 = extract_text(transcription, next2[0], next2[1]).lower()

            if text1 == 'manibus' and text2 == 'sacrum':
                combined_end = next2[1]
                fixed_annotations.append([start, combined_end, 'DEDICATION_TO_THE_GODS'])
                i += 3
                continue

        # Fix: Remove measurements labeled as ages
        if label in ['AGE_PREFIX', 'AGE_YEARS', 'AGE_MONTHS', 'AGE_DAYS']:
            # Check if it's actually a measurement
            context_start = max(0, start - 20)
            context_end = min(len(transcription), end + 20)
            context = transcription[context_start:context_end]

            if is_measurement_phrase(context):
                # Skip this - it's a measurement, not an age
                i += 1
                continue

        # Fix: "bene merenti" should be single BENE_MERENTI
        if entity_lower == 'bene' and i + 1 < len(sorted_anns):
            next1 = sorted_anns[i + 1]
            text1 = extract_text(transcription, next1[0], next1[1]).lower()

            if text1 in ['merenti', 'merito', 'meritae']:
                combined_end = next1[1]
                fixed_annotations.append([start, combined_end, 'BENE_MERENTI'])
                i += 2
                continue

        # Fix: "vixit annos" pattern - "vixit" is AGE_PREFIX, "annos" is also AGE_PREFIX
        if entity_lower in ['vixit', 'vix'] and label != 'AGE_PREFIX':
            fixed_annotations.append([start, end, 'AGE_PREFIX'])
            i += 1
            continue

        if entity_lower in ['annos', 'annorum', 'annis', 'anno', 'annum'] and label != 'AGE_PREFIX':
            fixed_annotations.append([start, end, 'AGE_PREFIX'])
            i += 1
            continue

        # Fix: Roman numerals after age words should be AGE_YEARS
        if re.match(r'^[IVX]+$', entity_text) and i > 0:
            prev_ann = fixed_annotations[-1] if fixed_annotations else None
            if prev_ann and prev_ann[2] == 'AGE_PREFIX':
                # This is likely an age number
                if label != 'AGE_YEARS':
                    fixed_annotations.append([start, end, 'AGE_YEARS'])
                    i += 1
                    continue

        # Fix: "fili[au]s" / "filia" after a name should be FILIATION or RELATIONSHIP
        if entity_lower in ['filius', 'filia', 'filii', 'filiae', 'filio']:
            if label not in ['FILIATION', 'RELATIONSHIP']:
                fixed_annotations.append([start, end, 'RELATIONSHIP'])
                i += 1
                continue

        # Fix: Common relationships
        relationship_words = {
            'coniugi', 'conivx', 'coniux', 'uxori', 'uxor', 'marito',
            'pater', 'mater', 'patri', 'matri',
            'libertus', 'liberta', 'liberti', 'libertae', 'liberto',
            'patrono', 'patronus', 'patronae',
            'frater', 'fratri', 'soror',
            'conservae',
        }
        if entity_lower in relationship_words and label not in ['RELATIONSHIP', 'FILIATION']:
            fixed_annotations.append([start, end, 'RELATIONSHIP'])
            i += 1
            continue

        # Fix: Common funerary formula words
        funerary_words = {
            'fecit', 'fecerunt', 'posuit', 'posuerunt', 'curavit', 'curaverunt',
            'faciendum', 'depositus',
        }
        if entity_lower in funerary_words and label != 'FUNERARY_FORMULA':
            fixed_annotations.append([start, end, 'FUNERARY_FORMULA'])
            i += 1
            continue

        # If we get here, keep the annotation as-is
        fixed_annotations.append([start, end, label])
        i += 1

    return fixed_annotations


def fix_annotations_file(input_path: str, output_path: str):
    """
    Fix all annotations in a JSONL file.
    """
    print(f"Reading from: {input_path}")

    fixed_count = 0
    total_count = 0
    entity_changes = 0

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
                        entity_changes += (original_count - len(fixed_annotations))

                        if original_count != len(fixed_annotations):
                            fixed_count += 1

                    f_out.write(json.dumps(record, ensure_ascii=False) + '\n')

                    if line_num % 100 == 0:
                        print(f"Processed {line_num} records...")

                except Exception as e:
                    print(f"Error on line {line_num}: {e}")
                    # Write original line if error
                    f_out.write(line)

    print(f"\n✅ Processing complete!")
    print(f"   Total records: {total_count}")
    print(f"   Records modified: {fixed_count}")
    print(f"   Net entity change: {entity_changes} removed")
    print(f"   Output: {output_path}")


if __name__ == '__main__':
    input_file = 'real_data_w_generated_annotations_to_fix.jsonl'
    output_file = 'real_data_w_generated_annotations_FIXED.jsonl'

    fix_annotations_file(input_file, output_file)
