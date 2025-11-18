# Using the Annotation Notebook

## Quick Start

The `annotate_inscriptions_with_gemini.ipynb` notebook provides a complete, self-contained workflow for annotating Latin inscriptions with Gemini AI.

## What It Does

1. ✅ Downloads inscription data from EDH (Epigraphic Database Heidelberg)
2. ✅ Cleans Leiden convention markup
3. ✅ Calls Gemini API to annotate entities
4. ✅ Validates annotation quality
5. ✅ Commits and pushes results to git

## Prerequisites

1. **Google AI API Key**
   - Get one at: https://aistudio.google.com/app/apikey
   - Free tier includes generous quota

2. **Python environment**
   - Jupyter notebook support
   - Python 3.8+

## How to Use

### Option 1: Google Colab (Recommended)

1. **Upload the notebook to Google Colab**:
   - Go to https://colab.research.google.com/
   - File → Upload notebook
   - Choose `annotate_inscriptions_with_gemini.ipynb`

2. **Set your API key**:
   ```python
   # In the configuration cell:
   GOOGLE_AI_API_KEY = "your-api-key-here"
   ```

3. **Run all cells** (Runtime → Run all)
   - Downloads 2000 inscriptions from EDH
   - Annotates with Gemini
   - Takes ~40 minutes, costs ~$0.50

4. **Download results**:
   - File → Download → `gemini_annotations.jsonl`

### Option 2: Local Jupyter

1. **Clone the repository**:
   ```bash
   cd latinepi
   ```

2. **Install Jupyter**:
   ```bash
   pip install jupyter
   ```

3. **Set API key** (environment variable):
   ```bash
   export GOOGLE_AI_API_KEY="your-api-key-here"
   ```

4. **Launch notebook**:
   ```bash
   jupyter notebook annotate_inscriptions_with_gemini.ipynb
   ```

5. **Run cells sequentially**:
   - Cell 1: Setup
   - Cell 2-3: Download EDH data
   - Cell 4-8: Configure and test Gemini
   - Cell 9: Run batch annotation
   - Cell 10-11: Validate and review
   - Cell 12: Commit to git

## Configuration Options

### EDH Search Parameters (Cell 3)

```python
SEARCH_PARAMS = {
    "year_from": 1,      # Start year (1 CE)
    "year_to": 100,      # End year (100 CE)
    "limit": 2000,       # Number of inscriptions
}
```

**Examples**:
- 1st century: `year_from=1, year_to=100`
- 2nd century: `year_from=101, year_to=200`
- Republican era: `year_from=-200, year_to=-1`
- All periods: `year_from=-500, year_to=500`

### Gemini Model (Cell 2)

```python
GEMINI_MODEL = "gemini-2.0-flash-exp"  # Fast, cheap ($0.20/1000)
# GEMINI_MODEL = "gemini-1.5-pro"      # More accurate ($2/1000)
```

### Processing Speed (Cell 2)

```python
API_DELAY = 1.0  # Seconds between calls
# API_DELAY = 0.5  # Faster (may hit rate limits)
# API_DELAY = 2.0  # Safer for free tier
```

### Test Mode (Cell 8)

```python
TEST_LIMIT = 10  # Process only 10 inscriptions (for testing)
# TEST_LIMIT = None  # Process all (for production)
```

## Output Files

After running the notebook:

```
assets/
├── gemini_annotations.jsonl        # Main output (annotated inscriptions)
└── gemini_annotations.jsonl.tmp    # Checkpoint (deleted after completion)

edh_downloads/
└── batch_YYYYMMDD_HHMMSS/          # Raw EDH data (JSON files)
    ├── HD000001.json
    ├── HD000002.json
    └── ...
```

## Checkpoint & Resume

The notebook automatically saves progress every 50 inscriptions.

If interrupted:
1. Re-run the annotation cell (Cell 8)
2. It will detect the checkpoint and resume from where it stopped
3. No duplicate work or API charges

To start fresh:
```bash
rm assets/gemini_annotations.jsonl.tmp
```

## Validation Output

After annotation, Cell 9 shows:

```
📊 Entity Type Distribution:
   DEDICATION_TO_THE_GODS     1234
   NOMEN                       987
   COGNOMEN                    856
   ...

🔍 Quality Checks:
   Total entities: 4521
   Overlapping spans: 0        ✅
   Boundary errors: 0          ✅

🎯 Overall Quality: 🌟 EXCELLENT
```

**What to look for**:
- ✅ Overlapping spans: **Should be 0** (critical!)
- ✅ Boundary errors: Should be 0
- ✅ Success rate: >95%
- ✅ Avg entities per inscription: 4-8

## Integration with Training Notebook

After annotation, use the output in your training notebook:

```python
# In training_spacy_model_for_latin_epigraphy.ipynb:

# OLD:
# INPUT_FILE = "assets/synthethic-training.jsonl"

# NEW:
INPUT_FILE = "assets/gemini_annotations.jsonl"

# Then continue with existing pipeline:
partition_data(INPUT_FILE, CLEAN_OUTPUT_FILE, FIX_OUTPUT_FILE)
split_data(CLEAN_OUTPUT_FILE, TRAIN_SPLIT_FILE, DEV_SPLIT_FILE)
align_annotations('assets/train_split.jsonl', 'assets/train_aligned.jsonl')
create_spacy_file_robust('assets/train_aligned.jsonl', './corpus/train.spacy')
```

## Troubleshooting

### "API key invalid"
- Check your key at https://aistudio.google.com/app/apikey
- Make sure it's set in Cell 2 or environment

### "Rate limit exceeded"
- Increase `API_DELAY` to 2.0 or 3.0
- Wait a few minutes and resume

### "Out of memory" (Colab)
- Process in smaller batches (set `SEARCH_PARAMS["limit"] = 500`)
- Run multiple times with different year ranges
- Combine JSONL files afterward

### "No inscriptions downloaded"
- Check EDH website is accessible
- Try different search parameters
- EDH may have no data for that time/region

### "Many overlapping spans found"
- The Gemini model didn't follow the prompt correctly
- Try `GEMINI_MODEL = "gemini-1.5-pro"` (more reliable)
- Or manually fix overlaps in post-processing

## Cost Estimation

**Gemini Flash 2.5** (recommended):
- Input: $0.075 per 1M tokens
- Output: $0.30 per 1M tokens
- **2000 inscriptions ≈ $0.40-0.60**

**Gemini Pro 1.5** (higher quality):
- Input: $1.25 per 1M tokens
- Output: $5.00 per 1M tokens
- **2000 inscriptions ≈ $8-12**

Time: ~20-40 minutes for 2000 inscriptions (with 1s delay)

## Expected Results

For 2000 inscriptions (1st century CE):

- ✅ ~4000-5000 total entities annotated
- ✅ ~2-5 entities per inscription (avg)
- ✅ <1% overlap rate (vs 34% with synthetic data)
- ✅ Success rate >95%

Entity distribution (approximate):
- DEDICATION_TO_THE_GODS: 1200-1500
- NOMEN: 800-1000
- COGNOMEN: 600-800
- PRAENOMEN: 400-600
- MILITARY_UNIT: 200-300
- AGE_YEARS: 150-250
- RELATIONSHIP: 100-200
- Others: 500-1000

## Next Steps After Annotation

1. **Validate quality** (Cell 9)
   - Check for 0 overlaps
   - Review entity distribution
   - Inspect sample annotations

2. **Compare with synthetic data**:
   - Train model A: 463 synthetic only
   - Train model B: 2000 real only
   - Train model C: Combined (463 + 2000)
   - Evaluate on held-out real inscriptions

3. **Scale up** if quality is good:
   - Annotate 2nd century (101-200 CE)
   - Annotate 3rd century (201-300 CE)
   - Aim for 5000-10000 total inscriptions

4. **Iterate on quality**:
   - Review failed cases
   - Adjust prompt if needed
   - Re-run on small batches to test

## Git Integration

Cell 11 automatically:
1. Stages annotation files
2. Creates descriptive commit message
3. Commits to current branch
4. Pushes to remote

**Commit message includes**:
- Timestamp
- Number of inscriptions
- Success rate
- Entity counts
- Search parameters

Example:
```
Add Gemini-annotated inscriptions (2025-01-15 14:30)

Annotated 2000 inscriptions using gemini-2.0-flash-exp
- Total entities: 4521
- Avg entities per inscription: 2.3
- Success rate: 97.5%
- Search params: 1-100 CE

Files:
- assets/gemini_annotations.jsonl
- edh_downloads/batch_20250115_143021/
```

## Tips for Best Results

1. **Start small**: Test with 10-50 inscriptions first
2. **Validate thoroughly**: Check overlap rate is 0%
3. **Use Flash model**: Unless quality is poor
4. **Save checkpoints**: Don't skip this safety feature
5. **Review samples**: Look at Cell 10 output
6. **Compare models**: Train with and without this data
7. **Iterate**: Improve prompt if needed and re-run

## Support

If you encounter issues:
- Check the validation output (Cell 9)
- Review sample annotations (Cell 10)
- Inspect failed cases manually
- Adjust configuration and retry

The notebook is designed to be self-documenting and error-resistant. Each cell includes explanations and error handling.

---

**Ready to start?** Open the notebook and run Cell 1! 🚀
