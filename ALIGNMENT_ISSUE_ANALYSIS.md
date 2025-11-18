# Alignment Issue Analysis and Solutions

## The Problem

Your notebook shows a **34-37% entity loss** during the conversion to .spacy format:

```
Training set:
- Input: 2730 perfect annotations
- Output: 1802 entities in .spacy format
- LOSS: 928 entities (34%)

Dev set:
- Input: 671 perfect annotations
- Output: 426 entities in .spacy format
- LOSS: 245 entities (37%)
```

This is happening in the `create_spacy_file()` function at this step:

```python
span = doc.char_span(start, end, label=label, alignment_mode="expand")
if span is not None:
    ents.append(span)
else:
    stats["dropped_ents"] += 1  # ← 34-37% of entities end up here
```

---

## Root Causes

### 1. **Tokenization Misalignment**

SpaCy tokenizes text based on whitespace and punctuation. Your annotations use **character positions** from the original text, which may not align with token boundaries.

**Example:**
```
Text: "D M C IVLIO VALENTI"
Annotation: [4, 5, "PRAENOMEN"]  # Trying to capture "C"

Tokens: ["D", "M", "C", "IVLIO", "VALENTI"]
Token positions: [0-1], [2-3], [4-5], [6-11], [12-19]
```

If your annotation is `[4, 5]`, it aligns perfectly with the token "C" at position [4-5]. ✅

But if your annotation is `[3, 5]` (including the space), it tries to span from mid-token "M" to end of "C". ❌

### 2. **Whitespace Handling**

Latin inscriptions often have irregular spacing:
- `"D M"` vs `"D  M"` (double space)
- `" D M"` (leading space)
- `"D M "` (trailing space)

If annotations include/exclude spaces inconsistently, alignment fails.

### 3. **Abbreviation Expansion in Annotations**

If your synthetic data annotated the **expanded** form but the text has **abbreviated** form:

```
Text: "D M"
Annotation tries to find: "DIS MANIBUS" ← Wrong!
```

### 4. **Unicode and Case Issues**

Latin inscriptions use various Unicode characters:
- `IVLIVS` vs `JVLIVS`
- `V` vs `U`
- Combining diacritics

---

## Diagnostic Steps

### Step 1: Run the Diagnostic Script

```bash
python diagnose_alignment_issues.py assets/train_aligned.jsonl failures_train.csv
python diagnose_alignment_issues.py assets/dev_aligned.jsonl failures_dev.csv
```

This will produce:
- **Summary statistics** by entity type
- **Failure reasons** categorized
- **CSV file** with every failed span for manual inspection

### Step 2: Examine the CSV Output

The CSV will show:

| record_id | expected_entity | label | start | end | failure_reason | context | tokens_around |
|-----------|-----------------|-------|-------|-----|----------------|---------|---------------|
| HD001 | " C" | PRAENOMEN | 3 | 5 | starts_with_whitespace | ...D M C IV... | D \| M \| C <<< |

### Step 3: Identify Patterns

Look for the most common `failure_reason` values:
- `starts_with_whitespace` → Annotations include leading spaces
- `ends_with_whitespace` → Annotations include trailing spaces
- `start_mid_token` → Annotation starts in middle of a token
- `end_mid_token` → Annotation ends in middle of a token
- `tokenization_mismatch` → SpaCy split tokens differently than expected

---

## Solutions

### Solution 1: **Fix Annotations at the Source** (Best)

Update your annotation generation (whether LLM or manual) to ensure:

1. **No leading/trailing whitespace in entity spans**
   ```python
   # Before annotating, strip whitespace and adjust offsets
   entity_text = text[start:end]
   stripped = entity_text.strip()

   # Adjust start to skip leading whitespace
   start_offset = len(entity_text) - len(entity_text.lstrip())
   new_start = start + start_offset

   # Adjust end to skip trailing whitespace
   end_offset = len(entity_text) - len(entity_text.rstrip())
   new_end = end - end_offset

   annotation = [new_start, new_end, label]
   ```

2. **Verify annotations align with token boundaries**
   ```python
   doc = nlp.make_doc(text)
   span = doc.char_span(start, end, alignment_mode="strict")

   if span is None:
       # Try expand mode as fallback
       span = doc.char_span(start, end, alignment_mode="expand")
       if span is not None:
           # Update annotation to use span's actual boundaries
           new_annotation = [span.start_char, span.end_char, label]
   ```

### Solution 2: **Auto-Fix During Data Prep** (Good)

Modify your `create_spacy_file()` function to try multiple alignment strategies:

```python
def create_spacy_file_robust(input_path, output_path):
    nlp = spacy.load('la_core_web_lg')
    db = DocBin()

    stats = {
        "docs": 0,
        "total_ents": 0,
        "dropped_ents": 0,
        "auto_fixed": 0
    }

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            record = json.loads(line)
            text = record.get('transcription')
            if not text:
                continue

            doc = nlp.make_doc(text)
            ents = []
            annotations = get_annotation_spans(record)

            for entity in annotations:
                if len(entity) != 3:
                    continue
                start, end, label = entity

                # Try multiple strategies in order of preference
                span = try_alignment_strategies(doc, text, start, end, label)

                if span is not None:
                    ents.append(span)
                    if span.start_char != start or span.end_char != end:
                        stats["auto_fixed"] += 1
                else:
                    stats["dropped_ents"] += 1

            doc.ents = filter_spans(ents)
            stats["total_ents"] += len(doc.ents)
            stats["docs"] += 1
            db.add(doc)

    db.to_disk(output_path)
    print(f"✅ Saved {output_path}")
    print(f"   Documents: {stats['docs']}")
    print(f"   Total Entities: {stats['total_ents']}")
    print(f"   Auto-fixed: {stats['auto_fixed']}")
    print(f"   Dropped: {stats['dropped_ents']}")

def try_alignment_strategies(doc, text, start, end, label):
    """Try multiple alignment strategies in order of preference"""

    # Strategy 1: Strict (perfect alignment)
    span = doc.char_span(start, end, label=label, alignment_mode="strict")
    if span:
        return span

    # Strategy 2: Expand (most permissive)
    span = doc.char_span(start, end, label=label, alignment_mode="expand")
    if span:
        return span

    # Strategy 3: Strip whitespace and retry
    entity_text = text[start:end]
    stripped = entity_text.strip()

    if stripped != entity_text:
        # Recalculate offsets without whitespace
        new_start = start + (len(entity_text) - len(entity_text.lstrip()))
        new_end = end - (len(entity_text) - len(entity_text.rstrip()))

        span = doc.char_span(new_start, new_end, label=label, alignment_mode="expand")
        if span:
            return span

    # Strategy 4: Try shifting boundaries by ±1
    for shift in [-1, 1, -2, 2]:
        span = doc.char_span(start + shift, end + shift, label=label, alignment_mode="expand")
        if span:
            return span

    # Strategy 5: Try adjusting just start or just end
    for start_shift in [-1, 0, 1]:
        for end_shift in [-1, 0, 1]:
            if start_shift == 0 and end_shift == 0:
                continue
            span = doc.char_span(start + start_shift, end + end_shift, label=label, alignment_mode="expand")
            if span:
                return span

    # All strategies failed
    return None
```

### Solution 3: **Pre-normalize Text** (Preventive)

Normalize the transcription text BEFORE annotation:

```python
def normalize_transcription(text):
    """Normalize text to ensure consistent tokenization"""

    # 1. Standardize whitespace
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces → single space
    text = text.strip()  # Remove leading/trailing

    # 2. Remove double spaces after abbreviation dots
    text = re.sub(r'\.\s+', '. ', text)  # "D.  M." → "D. M."

    # 3. Standardize Unicode
    text = text.upper()  # Ensure uppercase
    text = text.replace('J', 'I')  # J → I for classical Latin

    return text
```

Then ensure annotations are created on the **normalized** text.

### Solution 4: **Use Contract Mode** (Aggressive)

If entities often span slightly beyond token boundaries:

```python
# Instead of:
span = doc.char_span(start, end, label=label, alignment_mode="expand")

# Try:
span = doc.char_span(start, end, label=label, alignment_mode="contract")
```

**Contract mode** shrinks the span to fit within token boundaries.

**Warning**: This may exclude parts of entities, reducing precision.

---

## Recommended Action Plan

### Immediate Fix (for existing data):

1. **Add the robust alignment function** to your notebook:
   ```python
   # Replace create_spacy_file with create_spacy_file_robust
   ```

2. **Re-run the data preparation**:
   ```python
   create_spacy_file_robust('assets/train_aligned.jsonl', './corpus/train.spacy')
   create_spacy_file_robust('assets/dev_aligned.jsonl', './corpus/dev.spacy')
   ```

3. **Check improvement**:
   - Before: 34% loss (928 dropped)
   - After: Should be <5% loss

### Long-term Fix (for new annotations):

1. **Update Gemini prompt** to include:
   ```
   CRITICAL: Annotations must align with token boundaries.
   - Do NOT include leading or trailing whitespace in entity spans
   - Verify: text[start:end].strip() == text[start:end]
   - Start and end positions must be at word boundaries
   ```

2. **Add validation in annotation script**:
   ```python
   def validate_annotation(text, start, end, label):
       entity_text = text[start:end]

       # Check 1: No whitespace padding
       if entity_text != entity_text.strip():
           # Fix it
           stripped = entity_text.strip()
           new_start = text.find(stripped, start)
           new_end = new_start + len(stripped)
           return new_start, new_end, label

       return start, end, label
   ```

---

## Testing the Fix

After implementing the robust alignment:

```python
# Run this in your notebook:
stats_before = {
    "train_annotations": 2730,
    "train_entities": 1802,
    "train_loss": 928
}

# Re-run with new function
create_spacy_file_robust('assets/train_aligned.jsonl', './corpus/train_fixed.spacy')

# Compare
print(f"Before: {stats_before['train_loss']} dropped (34%)")
print(f"After: {new_stats['dropped_ents']} dropped ({new_stats['dropped_ents']/2730*100:.1f}%)")
print(f"Improvement: {stats_before['train_loss'] - new_stats['dropped_ents']} entities recovered")
```

**Expected result**: Reduce from 34% loss to <5% loss, recovering ~800+ entities for training.

---

## Why This Matters

Getting from 1802 entities → 2500+ entities means:
- **38% more training data** without annotating anything new
- Better model performance on rare entity types
- Reduced overfitting (more diverse examples)

This could be the difference between your current F1 scores and significantly better results, especially for:
- RELATIONSHIP (currently F1=0.20)
- BENE_MERENTI (currently F1=0.37)
- MILITARY_UNIT (currently F1=0.57)

---

## Next Steps

1. ✅ Implement `try_alignment_strategies()` function
2. ✅ Replace `create_spacy_file()` with robust version
3. ✅ Re-run data preparation pipeline
4. ✅ Compare before/after statistics
5. ✅ Retrain model with recovered entities
6. ✅ Evaluate performance improvement

Would you like me to create a notebook cell with the fixed code ready to run?
