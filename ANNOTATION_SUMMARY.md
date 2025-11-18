# Latin Epigraphy Annotation Setup - Complete

I've created a complete annotation system for your 2000 Latin inscriptions using Gemini Flash 2.5.

## What I've Created

### 1. **Annotation Prompt** (`gemini_annotation_prompt.md`)
A comprehensive, detailed prompt that instructs Gemini Flash 2.5 to:
- Identify 15 entity types specific to Latin epigraphy
- Return character-level annotations (start/end positions)
- Handle abbreviations, Leiden conventions, and formulaic phrases
- Produce output in the exact JSONL format your training pipeline expects

**Key Features:**
- Detailed definitions and examples for each entity type
- Multiple example annotations with explanations
- Edge case handling (damaged text, multiple people, ambiguity)
- Quality checklist to ensure consistency

### 2. **Batch Processing Script** (`batch_annotate_with_gemini.py`)
A production-ready Python script that:
- Processes inscriptions in batches with progress saving
- Handles API rate limiting and retries
- Saves checkpoints every N inscriptions (resumable)
- Works with both CSV and JSON directory inputs
- Provides detailed progress reporting

**Features:**
- ✅ Resume interrupted runs
- ✅ Test with small batches first (`--limit` flag)
- ✅ Automatic checkpoint saving
- ✅ Rate limiting to avoid API errors
- ✅ Detailed statistics on completion

### 3. **Validation Script** (`validate_annotations.py`)
Quality assurance tool that checks:
- JSON structure validity
- Annotation span correctness (indices match text)
- Entity type distribution
- Error detection (overlapping spans, out-of-bounds, etc.)
- Sample visualizations

**Outputs:**
- Overall quality score
- Entity distribution statistics
- Example annotations for each type
- Error and warning reports
- Recommendation for whether to proceed with training

### 4. **Quick Start Guide** (`ANNOTATION_GUIDE.md`)
Step-by-step instructions for:
- Getting your API key
- Testing with small batches
- Running the full annotation
- Validating results
- Cost estimation (~$0.45 for 2000 inscriptions)
- Troubleshooting common issues

---

## Quick Start Commands

### Step 1: Install Dependencies
```bash
pip install google-generativeai pandas
```

### Step 2: Set API Key
```bash
export GOOGLE_AI_API_KEY="your-api-key-here"
```
Get your key at: https://aistudio.google.com/app/apikey

### Step 3: Test with 10 Inscriptions
```bash
python batch_annotate_with_gemini.py \
  --input-csv assets/inscriptions.csv \
  --output assets/test_10.jsonl \
  --limit 10 \
  --delay 2.0
```

### Step 4: Validate Test Results
```bash
python validate_annotations.py assets/test_10.jsonl
```

### Step 5: If Test Looks Good, Run Full Batch
```bash
python batch_annotate_with_gemini.py \
  --input-csv assets/inscriptions.csv \
  --output assets/gemini_annotations_2000.jsonl \
  --save-every 50 \
  --delay 1.0
```

---

## Entity Types Being Annotated

The prompt instructs Gemini to identify these 15 entity types:

| Entity Type | Description | Examples |
|-------------|-------------|----------|
| `DEDICATION_TO_THE_GODS` | Formulaic dedications | D M, DIS MANIBUS |
| `PRAENOMEN` | Personal name | GAIVS, MARCVS, C, M |
| `NOMEN` | Family name | IVLIVS, CORNELIVS |
| `COGNOMEN` | Additional name | FELIX, MAXIMUS |
| `DECEASED_NAME` | Full name (when unclear) | IVLIVS FELIX |
| `FILIATION` | Parentage | M F (son of Marcus) |
| `TRIBE` | Roman voting tribe | FAB, PAL, QVR |
| `MILITARY_UNIT` | Legion/rank/cohort | LEG X, MIL, CENTVRIO |
| `OCCUPATION` | Civilian profession | MEDICUS, NEGOTIATOR |
| `AGE_PREFIX` | Age introduction | VIXIT, VIX, ANNIS |
| `AGE_YEARS` | Age in years | XXX, XL, TRIGINTA |
| `AGE_MONTHS` | Age in months | MENSIBUS VI |
| `AGE_DAYS` | Age in days | DIEBUS XV |
| `DEDICATOR_NAME` | Who erected monument | Name after FECIT |
| `RELATIONSHIP` | Relationship to deceased | CONIVX, FILIVS, MATER |
| `FUNERARY_FORMULA` | Standard phrases | H S E, FECIT, POSVIT |
| `BENE_MERENTI` | "Well-deserving" phrase | BENE MERENTI, B M |

---

## Example Output Format

The script produces JSONL (JSON Lines) format, ready for your training pipeline:

```json
{
  "id": "HD000123",
  "text": "D(is) M(anibus) / C(aio) Iulio Felici...",
  "transcription": "D M C IVLIO FELICI MIL LEG X VIX AN XXX H S E",
  "annotations": [
    [0, 3, "DEDICATION_TO_THE_GODS"],
    [4, 5, "PRAENOMEN"],
    [6, 11, "NOMEN"],
    [12, 18, "COGNOMEN"],
    [19, 28, "MILITARY_UNIT"],
    [29, 32, "AGE_PREFIX"],
    [33, 35, "AGE_PREFIX"],
    [36, 39, "AGE_YEARS"],
    [40, 45, "FUNERARY_FORMULA"]
  ]
}
```

Each line is a complete JSON object that your notebook can load directly.

---

## Cost and Time Estimates

For 2000 inscriptions using Gemini Flash 2.5:

- **Estimated cost**: $0.40 - $0.60 USD
- **Estimated time**: 35-40 minutes (with 1s delay between calls)
- **Token usage**: ~3M tokens total (input + output)

The script saves progress every 50 inscriptions, so if interrupted you can resume without losing work.

---

## Integration with Your Training Pipeline

The output JSONL file can be used directly in your notebook:

```python
# Replace the synthetic data line in your notebook:
# OLD:
INPUT_FILE = "assets/synthethic-training.jsonl"

# NEW:
INPUT_FILE = "assets/gemini_annotations_2000.jsonl"

# Then continue with your existing pipeline:
partition_data(INPUT_FILE, CLEAN_OUTPUT_FILE, FIX_OUTPUT_FILE)
split_data(CLEAN_OUTPUT_FILE, TRAIN_SPLIT_FILE, DEV_SPLIT_FILE)
# ... etc
```

---

## Troubleshooting

### "Rate limit exceeded"
- Increase delay: `--delay 2.0` or `--delay 3.0`

### "Invalid API key"
- Check your API key at: https://aistudio.google.com/app/apikey
- Ensure it's set correctly: `echo $GOOGLE_AI_API_KEY`

### "JSON decode error"
- The script automatically handles these
- Check validation output for frequency
- If >5% of annotations fail, consider adjusting the prompt

### Script interrupted
- Use `--resume-from N` where N is the last completed index
- The script automatically saves to `.jsonl.tmp` files during processing

---

## Next Steps After Annotation

1. ✅ Validate annotations: `python validate_annotations.py output.jsonl`
2. ✅ Review quality metrics (aim for <1% error rate)
3. ✅ Check entity distribution (ensure all types are represented)
4. ✅ Manually inspect a few random samples
5. ✅ Feed into your training pipeline
6. ✅ Compare model performance (synthetic vs. real data)

---

## Advanced Options

### Use a Different Model
```bash
# Gemini Pro (more accurate, more expensive)
--model gemini-1.5-pro

# Gemini Flash Thinking (experimental reasoning)
--model gemini-2.0-flash-thinking-exp-01-21
```

### Process Multiple Batches in Parallel
```bash
# Split your data into chunks and run multiple scripts:
python batch_annotate_with_gemini.py --input-csv chunk1.csv --output batch1.jsonl &
python batch_annotate_with_gemini.py --input-csv chunk2.csv --output batch2.jsonl &
wait

# Combine results:
cat batch1.jsonl batch2.jsonl > combined.jsonl
```

### Adjust Prompt for Your Specific Needs
Edit `gemini_annotation_prompt.md` to:
- Add new entity types
- Modify examples
- Change annotation guidelines
- Adjust to your specific corpus characteristics

---

## Files Created

```
/home/user/latinepi/
├── gemini_annotation_prompt.md      # The detailed annotation prompt
├── batch_annotate_with_gemini.py    # Main annotation script
├── validate_annotations.py          # Quality validation script
├── ANNOTATION_GUIDE.md              # Step-by-step user guide
└── ANNOTATION_SUMMARY.md            # This file
```

---

## Support

If you encounter issues:

1. Check the validation script output
2. Review the ANNOTATION_GUIDE.md troubleshooting section
3. Inspect failed annotations in the output file
4. Test with a smaller batch first to diagnose problems

---

**Ready to annotate!** Start with the test batch (10 inscriptions) to verify everything works, then scale up to your full 2000.

Good luck! 🏛️
