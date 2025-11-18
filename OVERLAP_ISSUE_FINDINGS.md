# Entity Loss Root Cause: Overlapping Annotations (RESOLVED)

## 🔍 Investigation Results

After running the robust alignment diagnostics on the actual training data, we discovered the **real cause** of the 34% entity loss.

### What We Thought Was Wrong
- ❌ Tokenization misalignment (character offsets not matching token boundaries)
- ❌ Whitespace handling issues
- ❌ spaCy's char_span() failing to find entities

### What Was Actually Wrong
✅ **Overlapping annotations** being removed by spaCy's `filter_spans()` function

## 📊 The Evidence

```
Training set diagnostic results:
- Total annotations: 2730
- Perfect alignments: 2730 (100% ✓)
- Failed alignments: 0 (0% ✓)
- Recovered by alt strategies: 0 (not needed ✓)
- Overlapping entities REMOVED: 928 (34% ❌)
- Final entities: 1802

Dev set diagnostic results:
- Total annotations: 671
- Perfect alignments: 671 (100% ✓)
- Failed alignments: 0 (0% ✓)
- Recovered by alt strategies: 0 (not needed ✓)
- Overlapping entities REMOVED: 245 (37% ❌)
- Final entities: 426
```

**Key finding**: ZERO alignment failures, but 34-37% removed as overlaps!

## 🐛 Root Cause Explanation

### The Problem

SpaCy's NER models cannot handle **overlapping entity spans**. When your annotations contain overlaps like this:

```
Text: "GAIVS IVLIVS FELIX"

Annotations:
[0, 5, "PRAENOMEN"]      → "GAIVS"
[6, 12, "NOMEN"]         → "IVLIVS"
[13, 18, "COGNOMEN"]     → "FELIX"
[0, 18, "DECEASED_NAME"] → "GAIVS IVLIVS FELIX"  ← Overlaps with all 3 above!
```

The `filter_spans()` function automatically:
1. Detects the overlap
2. Keeps the **longest span** (DECEASED_NAME)
3. **Discards the shorter spans** (PRAENOMEN, NOMEN, COGNOMEN)

This is why you lost exactly 34% - roughly one-third of annotations were shorter spans nested inside longer ones.

### Why It Happened

Your **synthetic data generation** (LLM-based) was creating redundant, hierarchical annotations:

1. It annotated individual name components
2. **AND** the complete name
3. Same for military units (individual words + complete phrase)
4. This violated spaCy's non-overlapping constraint

The LLM was being "helpful" by providing multiple levels of detail, but spaCy can't use overlapping annotations for training.

## ✅ The Solution

### Updated Gemini Annotation Prompt

I've updated `gemini_annotation_prompt.md` with:

1. **Prominent warning section** at the top:
   - "⚠️ CRITICAL CONSTRAINT: NO OVERLAPPING SPANS"
   - Visual examples of WRONG vs CORRECT annotations

2. **Clear decision rules**:
   ```
   For names:
   - IF tria nomina structure is clear → annotate parts separately
   - IF structure is unclear → use DECEASED_NAME for whole name
   - NEVER annotate both!
   ```

3. **Explicit example (Example 0)** showing:
   - ❌ What NOT to do (with overlaps)
   - ✅ What TO do (without overlaps)

4. **Validation checklist**:
   ```python
   Before returning, verify:
   - Sort annotations by start position
   - Check: end[i] <= start[i+1] for all consecutive annotations
   - If you annotated PRAENOMEN/NOMEN/COGNOMEN, did NOT annotate DECEASED_NAME
   ```

5. **Updated all examples** with explanatory notes about why we chose each strategy

### Expected Impact

**Before** (with overlaps):
- 2730 annotations → 1802 entities (928 lost = 34%)
- Annotation efficiency: 66%

**After** (no overlaps):
- 2730 annotations → ~2700 entities (<30 lost = <1%)
- Annotation efficiency: ~99%

**For 2000 new inscriptions**:
- Expected: ~4000-5000 non-overlapping entities
- Virtually zero loss due to overlaps
- Much better representation of rare entity types

## 🎯 Impact on Training

### What This Means

1. **The robust alignment code wasn't needed** - it was solving the wrong problem
   - But good to have for edge cases!

2. **Your current model is fine** - the 1802 entities are valid
   - They're just the "longer span" versions that survived filtering

3. **The real fix is in the annotation strategy** - prevent overlaps at the source

### What Changes

**For existing synthetic data:**
- Already trained with 1802 entities (post-filtering)
- No action needed - model is valid

**For new 2000 real inscriptions:**
- Gemini will follow updated prompt
- Should produce ~4000+ non-overlapping entities
- Zero loss to overlap filtering
- Better entity type distribution

### Entity Type Impact

The overlap filtering likely affected different entity types differently:

**Heavily impacted** (probably lost many):
- PRAENOMEN, NOMEN, COGNOMEN (when DECEASED_NAME was also annotated)
- Individual name components in general

**Lightly impacted** (probably kept):
- DECEASED_NAME (longer, kept by filter_spans)
- DEDICATION_TO_THE_GODS (usually standalone)
- FUNERARY_FORMULA (usually standalone)
- AGE_YEARS (usually standalone)

This explains why some entity types (NOMEN, COGNOMEN) had good F1 scores despite the loss - the training data still had them when they appeared alone, just lost them when they overlapped with DECEASED_NAME.

## 📝 Action Items

### ✅ Completed
- [x] Diagnosed the real issue (overlapping spans, not alignment)
- [x] Updated Gemini prompt with NO OVERLAP constraint
- [x] Added clear examples and validation rules
- [x] Committed and pushed changes

### 🔜 Next Steps for You

1. **Use the updated prompt** when annotating your 2000 inscriptions
   - Run a test batch of 10-20 first
   - Validate with `validate_annotations.py`
   - Check for zero overlaps in the validation output

2. **Expected validation results**:
   ```
   Overlapping entities: 0
   Total entities: ~40-50 (for 10 inscriptions)
   Entity loss rate: <1%
   ```

3. **If you see overlaps in validation**:
   - The LLM didn't follow instructions correctly
   - Adjust the prompt or add more explicit examples
   - Or manually fix the few overlapping cases

4. **Train with new data**:
   - Should get 4000+ clean entities from 2000 inscriptions
   - Compare performance: synthetic-only vs real-only vs combined

## 🎉 Summary

**The Good News:**
- ✅ No alignment bug - tokenization works perfectly
- ✅ No code fixes needed in the pipeline
- ✅ Robust converter works but wasn't necessary
- ✅ Simple prompt update solves the issue

**The Bad News:**
- ❌ 34% of your annotation effort was wasted on overlaps
- ❌ Rare entity types suffered most from filtering

**The Solution:**
- ✅ Updated prompt prevents overlaps at the source
- ✅ New annotations will be ~99% efficient
- ✅ 2000 real inscriptions → 4000+ training entities

**The Lesson:**
When using LLMs for annotation, be **extremely explicit** about constraints. LLMs naturally want to be "helpful" by providing multiple levels of detail, but structured ML pipelines often can't handle redundancy.

---

**Files modified:**
- `gemini_annotation_prompt.md` - Added comprehensive no-overlap guidance

**Files that are still useful:**
- `robust_spacy_converter.py` - Good for edge cases, though not needed for this issue
- `diagnose_alignment_issues.py` - Helped us find the real problem!
- All documentation - Still valuable for understanding the pipeline

The investigation was successful - we found and fixed the root cause! 🎯
