# Gemini Annotation Quick Start Guide

This guide will help you annotate your 2000 Latin inscriptions using Gemini Flash 2.5.

## Prerequisites

1. **Get a Google AI API Key**
   - Visit: https://aistudio.google.com/app/apikey
   - Create a new API key
   - Save it securely

2. **Install Required Package**
   ```bash
   pip install google-generativeai
   ```

## Step 1: Set Your API Key

Option A - Environment Variable (Recommended):
```bash
export GOOGLE_AI_API_KEY="your-api-key-here"
```

Option B - Pass directly to script:
```bash
# Use --api-key flag (shown in examples below)
```

## Step 2: Test with a Small Batch First

**IMPORTANT**: Always test with a small sample before running the full 2000!

### If your data is in CSV format:
```bash
python batch_annotate_with_gemini.py \
  --input-csv assets/inscriptions.csv \
  --output assets/test_annotations.jsonl \
  --limit 10 \
  --delay 2.0
```

### If your data is in JSON directory (EDH format):
```bash
python batch_annotate_with_gemini.py \
  --input-json-dir edh_downloads/first_century \
  --output assets/test_annotations.jsonl \
  --limit 10 \
  --delay 2.0
```

### Inspect the Results
```bash
# Look at the first few annotations
head -n 3 assets/test_annotations.jsonl | python -m json.tool
```

## Step 3: Validate the Test Batch

Run the validation script to check annotation quality:

```bash
python validate_annotations.py assets/test_annotations.jsonl
```

This will show:
- Entity type distribution
- Any errors in span alignment
- Sample annotated texts
- Statistics on annotation quality

## Step 4: Run the Full Batch

Once satisfied with the test results:

```bash
python batch_annotate_with_gemini.py \
  --input-csv assets/inscriptions.csv \
  --output assets/gemini_annotations_full.jsonl \
  --save-every 50 \
  --delay 1.0
```

### Parameters Explained:
- `--save-every 50`: Saves progress every 50 inscriptions (in case of interruption)
- `--delay 1.0`: Wait 1 second between API calls (rate limiting)
- `--model`: Defaults to `gemini-2.0-flash-exp` (fast and cheap)

### For 2000 inscriptions:
- **Estimated time**: ~35-40 minutes (with 1s delay)
- **Estimated cost**: ~$0.20-0.40 USD (Flash 2.5 pricing)
- **Progress**: Saves checkpoints every 50, so you can resume if interrupted

## Step 5: Resume if Interrupted

If the script stops (network issue, etc.), resume from where you left off:

```bash
python batch_annotate_with_gemini.py \
  --input-csv assets/inscriptions.csv \
  --output assets/gemini_annotations_full.jsonl \
  --resume-from 850 \
  --save-every 50 \
  --delay 1.0
```

Replace `850` with the last successfully processed index shown in the output.

## Step 6: Convert to Training Format

The output is already in the correct JSONL format for your training pipeline!

You can now use it directly with the notebook's data preparation steps:

```python
# In your notebook:
INPUT_FILE = "assets/gemini_annotations_full.jsonl"
CLEAN_OUTPUT_FILE = "assets/train_clean.jsonl"
FIX_OUTPUT_FILE = "assets/train_needs_fixing.jsonl"

partition_data(INPUT_FILE, CLEAN_OUTPUT_FILE, FIX_OUTPUT_FILE)
```

## Troubleshooting

### API Rate Limits
If you get rate limit errors, increase the delay:
```bash
--delay 2.0  # or even 3.0
```

### JSON Parse Errors
If you see occasional JSON parse errors:
- The script automatically handles these
- Failed annotations are marked and saved
- Check the summary at the end for failure count

### Out of Memory
Processing 2000 at once shouldn't cause issues, but if it does:
- Process in batches of 500
- Combine the JSONL files afterward:
```bash
cat batch1.jsonl batch2.jsonl batch3.jsonl batch4.jsonl > all_annotations.jsonl
```

### Cost Estimation
Gemini Flash 2.5 pricing (as of 2025):
- Input: $0.075 per 1M tokens
- Output: $0.30 per 1M tokens

For 2000 inscriptions (~200 chars each + prompt):
- Input: ~2M tokens = $0.15
- Output: ~1M tokens = $0.30
- **Total: ~$0.45 USD**

(This is approximate - actual cost may vary)

## Quality Checks After Annotation

### 1. Check Entity Distribution
```bash
python -c "
import json
from collections import Counter

with open('assets/gemini_annotations_full.jsonl') as f:
    all_labels = []
    for line in f:
        data = json.loads(line)
        for ann in data.get('annotations', []):
            all_labels.append(ann[2])

for label, count in Counter(all_labels).most_common():
    print(f'{label:30s} {count:5d}')
"
```

### 2. Inspect Random Samples
```bash
# Show 5 random annotated inscriptions
python -c "
import json
import random

with open('assets/gemini_annotations_full.jsonl') as f:
    data = [json.loads(line) for line in f]

for item in random.sample(data, 5):
    print('='*60)
    print(f\"ID: {item['id']}\")
    print(f\"Text: {item['transcription']}\")
    print(f\"Entities: {len(item.get('annotations', []))}\")
    for start, end, label in item.get('annotations', []):
        entity_text = item['transcription'][start:end]
        print(f\"  [{label}] {entity_text}\")
    print()
"
```

## Advanced: Custom Models

If you have access to other Gemini models:

```bash
# Use Gemini Pro (more accurate but slower/expensive)
python batch_annotate_with_gemini.py \
  --model gemini-1.5-pro \
  --input-csv assets/inscriptions.csv \
  --output assets/annotations_pro.jsonl

# Use experimental models
python batch_annotate_with_gemini.py \
  --model gemini-2.0-flash-thinking-exp-01-21 \
  --input-csv assets/inscriptions.csv \
  --output assets/annotations_thinking.jsonl
```

## Next Steps

After successful annotation:

1. ✅ Run partition_data() to separate clean vs problematic annotations
2. ✅ Run split_data() to create train/dev splits
3. ✅ Run align_annotations() if needed
4. ✅ Convert to .spacy format with create_spacy_file()
5. ✅ Train your model!

---

**Questions or Issues?**

Check the validation script output or inspect the .jsonl files directly with:
```bash
cat assets/gemini_annotations_full.jsonl | jq '.' | less
```
