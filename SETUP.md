# Latin BERT Model Setup Guide

This guide explains how to set up the latin-bert model for production use with the latinepi tool.

## Quick Start (Stub Mode)

By default, latinepi uses a fast pattern-based stub that doesn't require any model downloads:

```bash
pip install -r requirements.txt
latinepi --input inscriptions.csv --output results.json
```

This stub mode is useful for development, testing, and quick analyses, but has limited accuracy.

## Full Setup (Latin BERT Model)

For production use with higher accuracy, follow these steps to download and configure the actual latin-bert model.

### 1. Install Dependencies

Uncomment the model dependencies in `requirements.txt` and install:

```bash
pip install torch>=2.0.0 transformers>=4.30.0
```

Note: These packages are large (~2GB) and require significant disk space and memory.

### 2. Download Latin BERT Model

The latin-bert model is hosted on Google Drive and must be downloaded manually:

```bash
# Clone the latin-bert repository
git clone https://github.com/dbmdz/latin-bert
cd latin-bert

# Run the download script (downloads ~400MB model from Google Drive)
bash download.sh
```

The script downloads `latin_bert.tar`, extracts it to `models/latin_bert/`, and cleans up the archive.

**Manual Download Alternative:**

If the script fails, you can download manually from the Google Drive link in the repository and extract to `models/latin_bert/`.

### 3. Configure Environment Variables

Set the path to your downloaded model:

```bash
# Point to the extracted model directory
export LATIN_BERT_PATH=/path/to/latin-bert/models/latin_bert

# Disable stub mode to use the real model
export LATINEPI_USE_STUB=false
```

Add these to your `.bashrc`, `.zshrc`, or `.env` file for persistence.

### 4. Verify Setup

Test that the model loads correctly:

```bash
# This should print a warning if LATIN_BERT_PATH is not set
latinepi --input test_data.json --output test_output.json
```

Look for this message in stderr:
- ✅ "Loading latin-bert model from /path/to/latin-bert/models/latin_bert..."
- ⚠️ "Warning: LATIN_BERT_PATH not set. Using generic multilingual model."

## Alternative: CLTK for Tokenization

The Classical Language Toolkit (CLTK) provides Latin-specific NLP tools including tokenizers:

```bash
# Install CLTK
pip install cltk>=1.0.0

# Download Latin models
python3 -c "from cltk.data.fetch import FetchCorpus; \
corpus_downloader = FetchCorpus(language='lat'); \
corpus_downloader.import_corpus('lat_models_cltk')"
```

**Note:** CLTK integration is currently not implemented but is documented for future enhancement.

## Model Behavior

### With LATIN_BERT_PATH Set
- Loads local latin-bert model optimized for Latin text
- Higher accuracy for Latin epigraphic inscriptions
- Extracts entities with confidence scores from the model

### Without LATIN_BERT_PATH (Fallback)
- Uses `dbmdz/bert-base-historic-multilingual-cased` from HuggingFace
- Generic multilingual model, lower accuracy for Latin
- Still functional but not optimized for Latin epigraphy

### Stub Mode (Default)
- Pattern-based entity extraction using regex
- Very fast, no model loading overhead
- Limited accuracy but useful for development/testing

## Troubleshooting

### Model Download Issues

If `download.sh` fails with Google Drive errors:
1. The download link may have expired - check the latin-bert repo for updates
2. Try downloading manually from the Google Drive link in the repo
3. Ensure you have ~500MB free disk space

### Import Errors

```
ModuleNotFoundError: No module named 'transformers'
```
Solution: Install model dependencies: `pip install torch transformers`

### Model Loading Failures

```
Warning: Could not load NER model: ...
```
Solution: Check that LATIN_BERT_PATH points to a valid model directory containing:
- `config.json`
- `pytorch_model.bin`
- `vocab.txt`

### Memory Issues

The model requires ~2GB RAM to load. If you encounter OOM errors:
1. Use stub mode instead: `export LATINEPI_USE_STUB=true`
2. Close other applications to free memory
3. Consider using a machine with more RAM

## Performance Considerations

- **Model loading**: Takes 5-30 seconds on first use (cached afterward)
- **Inference**: ~100-500ms per inscription depending on length
- **Memory**: ~2GB RAM when model is loaded
- **Disk**: ~400MB for model files

For batch processing large datasets, the model overhead is amortized across all inscriptions in a single run.
