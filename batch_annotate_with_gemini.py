#!/usr/bin/env python3
"""
Batch annotation script for Latin inscriptions using Gemini Flash 2.5
Processes inscriptions and generates spaCy-compatible training annotations
"""

import json
import time
import os
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd

# You'll need to install: pip install google-generativeai
try:
    import google.generativeai as genai
except ImportError:
    print("❌ Please install google-generativeai: pip install google-generativeai")
    exit(1)


class GeminiAnnotator:
    """Handles batch annotation of inscriptions using Gemini API"""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize the annotator

        Args:
            api_key: Your Google AI API key
            model_name: Gemini model to use (flash-2.5 recommended for speed/cost)
        """
        genai.configure(api_key=api_key)

        # Configure the model
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": 0.1,  # Low temperature for more deterministic output
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
        )

        # Load the system prompt
        prompt_path = Path(__file__).parent / "gemini_annotation_prompt.md"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()

        print(f"✅ Initialized with model: {model_name}")

    def annotate_single(self, inscription: Dict) -> Optional[Dict]:
        """
        Annotate a single inscription

        Args:
            inscription: Dict with keys: id, text, transcription

        Returns:
            Dict with annotations added, or None if failed
        """
        # Prepare the input
        input_json = json.dumps({
            "id": inscription.get("id", ""),
            "text": inscription.get("text", ""),
            "transcription": inscription.get("transcription", "")
        }, ensure_ascii=False, indent=2)

        # Construct the full prompt
        full_prompt = f"""{self.system_prompt}

---

Please annotate the following inscription:

{input_json}

Return ONLY the JSON object with annotations added. No other text.
"""

        try:
            # Call the API
            response = self.model.generate_content(full_prompt)

            # Extract JSON from response
            response_text = response.text.strip()

            # Clean up common issues
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # Parse the JSON
            result = json.loads(response_text)

            # Validate the structure
            if "annotations" not in result:
                print(f"⚠️  Missing 'annotations' field for {inscription.get('id')}")
                return None

            if not isinstance(result["annotations"], list):
                print(f"⚠️  Invalid annotations format for {inscription.get('id')}")
                return None

            return result

        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error for {inscription.get('id')}: {e}")
            print(f"   Response: {response_text[:200]}...")
            return None
        except Exception as e:
            print(f"❌ API error for {inscription.get('id')}: {e}")
            return None

    def annotate_batch(
        self,
        inscriptions: List[Dict],
        output_path: str,
        resume_from: int = 0,
        save_every: int = 10,
        delay: float = 1.0
    ):
        """
        Annotate a batch of inscriptions with progress saving

        Args:
            inscriptions: List of inscription dicts
            output_path: Where to save the JSONL output
            resume_from: Index to resume from (for interrupted runs)
            save_every: Save progress every N inscriptions
            delay: Delay between API calls in seconds (rate limiting)
        """
        output_file = Path(output_path)
        temp_file = output_file.with_suffix('.jsonl.tmp')

        # Load existing results if resuming
        completed = []
        if resume_from > 0 and temp_file.exists():
            print(f"📂 Resuming from index {resume_from}")
            with open(temp_file, 'r', encoding='utf-8') as f:
                completed = [json.loads(line) for line in f]

        total = len(inscriptions)

        print(f"🚀 Starting annotation of {total} inscriptions")
        print(f"   Saving to: {output_path}")
        print(f"   Checkpoint every {save_every} inscriptions")
        print()

        for i, inscription in enumerate(inscriptions[resume_from:], start=resume_from):
            print(f"[{i+1}/{total}] Processing {inscription.get('id', 'unknown')}...", end=" ")

            result = self.annotate_single(inscription)

            if result:
                completed.append(result)
                num_entities = len(result.get('annotations', []))
                print(f"✓ ({num_entities} entities)")
            else:
                # Save the original without annotations as a fallback
                completed.append({
                    **inscription,
                    "annotations": [],
                    "_error": True
                })
                print("✗ (failed)")

            # Save checkpoint
            if (i + 1) % save_every == 0:
                self._save_checkpoint(completed, temp_file)
                print(f"   💾 Checkpoint saved ({len(completed)} completed)")

            # Rate limiting
            if i < total - 1:  # Don't delay after last item
                time.sleep(delay)

        # Final save
        self._save_final(completed, output_file, temp_file)

        # Statistics
        successful = sum(1 for r in completed if "_error" not in r)
        failed = len(completed) - successful
        total_entities = sum(len(r.get('annotations', [])) for r in completed)

        print()
        print("="*60)
        print("✅ ANNOTATION COMPLETE")
        print(f"   Total inscriptions: {len(completed)}")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        print(f"   Total entities: {total_entities}")
        print(f"   Avg entities per inscription: {total_entities/successful:.1f}")
        print(f"   Output saved to: {output_file}")
        print("="*60)

    def _save_checkpoint(self, results: List[Dict], temp_file: Path):
        """Save intermediate results"""
        with open(temp_file, 'w', encoding='utf-8') as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')

    def _save_final(self, results: List[Dict], output_file: Path, temp_file: Path):
        """Save final results and clean up temp file"""
        with open(output_file, 'w', encoding='utf-8') as f:
            for result in results:
                # Remove error markers from final output
                if "_error" in result:
                    result = {k: v for k, v in result.items() if k != "_error"}
                f.write(json.dumps(result, ensure_ascii=False) + '\n')

        # Clean up temp file
        if temp_file.exists():
            temp_file.unlink()


def load_inscriptions_from_csv(csv_path: str, text_column: str = "transcription") -> List[Dict]:
    """
    Load inscriptions from a CSV file

    Args:
        csv_path: Path to CSV file with columns: id, text, transcription
        text_column: Which column to use for transcription

    Returns:
        List of inscription dicts
    """
    df = pd.read_csv(csv_path)

    inscriptions = []
    for _, row in df.iterrows():
        inscriptions.append({
            "id": str(row.get('id', '')),
            "text": str(row.get('text', '')) if pd.notna(row.get('text')) else '',
            "transcription": str(row.get(text_column, '')) if pd.notna(row.get(text_column)) else ''
        })

    # Filter out empty transcriptions
    inscriptions = [i for i in inscriptions if i['transcription'].strip()]

    print(f"📚 Loaded {len(inscriptions)} inscriptions from {csv_path}")
    return inscriptions


def load_inscriptions_from_json_dir(json_dir: str) -> List[Dict]:
    """
    Load inscriptions from a directory of JSON files (EDH format)

    Args:
        json_dir: Directory containing .json files

    Returns:
        List of inscription dicts
    """
    json_path = Path(json_dir)
    json_files = list(json_path.glob("*.json"))

    inscriptions = []
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            inscriptions.append({
                "id": data.get("id", ""),
                "text": data.get("diplomatic_text", ""),
                "transcription": data.get("transcription", "")
            })

    # Filter out empty transcriptions
    inscriptions = [i for i in inscriptions if i['transcription'].strip()]

    print(f"📚 Loaded {len(inscriptions)} inscriptions from {json_dir}")
    return inscriptions


def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Batch annotate Latin inscriptions using Gemini API"
    )
    parser.add_argument(
        "--input-csv",
        help="Input CSV file with inscriptions"
    )
    parser.add_argument(
        "--input-json-dir",
        help="Input directory containing JSON files (EDH format)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSONL file path"
    )
    parser.add_argument(
        "--api-key",
        help="Google AI API key (or set GOOGLE_AI_API_KEY env var)"
    )
    parser.add_argument(
        "--model",
        default="gemini-2.0-flash-exp",
        help="Gemini model to use (default: gemini-2.0-flash-exp)"
    )
    parser.add_argument(
        "--resume-from",
        type=int,
        default=0,
        help="Resume from this index (for interrupted runs)"
    )
    parser.add_argument(
        "--save-every",
        type=int,
        default=10,
        help="Save checkpoint every N inscriptions (default: 10)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between API calls in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Only process first N inscriptions (for testing)"
    )

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.environ.get("GOOGLE_AI_API_KEY")
    if not api_key:
        print("❌ Error: No API key provided")
        print("   Set --api-key or GOOGLE_AI_API_KEY environment variable")
        print("   Get your key at: https://aistudio.google.com/app/apikey")
        exit(1)

    # Load inscriptions
    if args.input_csv:
        inscriptions = load_inscriptions_from_csv(args.input_csv)
    elif args.input_json_dir:
        inscriptions = load_inscriptions_from_json_dir(args.input_json_dir)
    else:
        print("❌ Error: Must provide either --input-csv or --input-json-dir")
        exit(1)

    # Apply limit if specified
    if args.limit:
        inscriptions = inscriptions[:args.limit]
        print(f"⚠️  Limited to first {args.limit} inscriptions")

    # Create annotator and run
    annotator = GeminiAnnotator(api_key=api_key, model_name=args.model)

    annotator.annotate_batch(
        inscriptions=inscriptions,
        output_path=args.output,
        resume_from=args.resume_from,
        save_every=args.save_every,
        delay=args.delay
    )


if __name__ == "__main__":
    main()
