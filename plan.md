# 1. High-level Step-by-Step Blueprint

Examples/prior art:

https://github.com/dbamman/latin-bert

https://github.com/sdam-au/EDH_ETL

## Phase 1: Core Fundamentals

A. Project Scaffold
B. Establishing CLI Basics
C. Building Input/Output Framework
D. Foundation for Testing

## Phase 2: Integrate Key Features Iteratively

E. Basic NER Model Integration
F. Parsing Pipeline (Single Record, then Batch)
G. Entity Extraction & Confidence Scores
H. Ambiguity Handling & Threshold Logic
I. Output Formatting & Writing
J. Download Utility for EDH Data

## Phase 3: Final Touches

K. CLI Enhancement (flags, input validation)
L. Comprehensive Tests (CLI & Parser)
M. Documentation & User Guidance
N. Integration (“wiring up”)

# 2. Chunking into Iterative Milestones

Milestone 1: Project Skeleton, Unit Test Scaffold

Milestone 2: CLI Parsing (args, help), Simple File I/O

Milestone 3: Single-record NER Extraction (stub/mock)

Milestone 4: Batch Processing Loop (no NER yet)

Milestone 5: Connect Real BERT Model

Milestone 6: Add Confidence & Threshold Logic (with Tests)

Milestone 7: Output Formatting (JSON/CSV)

Milestone 8: Implement & Test EDH Download Utility

Milestone 9: Integrate CLI Flags, Error Handling, Help

Milestone 10: End-to-End Tests & Documentation

Milestone 11: Final Wiring Up & CLI Integration Testing

# 3. Review for Step-size

Each chunk is (a) testable, (b) incremental, (c) leaves no orphan code, (d) avoids big leaps. None will jump from “nothing” to “everything” (e.g., no full NER/CLI pipeline before all components are unit tested and stubbed in).

## For Each Milestone

    + Subdivide into atomic steps (e.g., for NER: load model, run on sample, extract results, etc.)
    + Ensure each step can be run and tested in isolation.
    + Each prompt: Always requests both implementation and appropriate tests.
    + Steps build naturally from previous.

# 4. Code Generation Prompts (Final Series)

## Prompt 1: Project Scaffold and First Test. Complete: [x]
```
You are to implement the initial scaffold for a Python project called `latinepi` for extracting structured data from Latin inscriptions. 

**Requirements:**
- Create a directory structure:  
  - `latinepi/cli.py` (main CLI entry point, prints "Hello World" for now)
  - `latinepi/parser.py` (empty)
  - `latinepi/edh_utils.py` (empty)
  - `latinepi/test/test_cli.py` (unit test for cli)
  - `latinepi/test/test_parser.py` (empty test file for parser)
  - `latinepi/__init__.py`

**Task:**
- Implement `cli.py` so that if called as a main program, it prints "Hello World".
- Implement a test in `test/test_cli.py` that runs `cli.py` as a script and asserts "Hello World" is in stdout.
```

## Prompt 2: CLI Argument Parsing and Help. Complete: [x]
```
Extend `latinepi/cli.py` to parse command-line arguments using `argparse`:

**Requirements:**
- Required: `--input <input_file>`, `--output <output_file>`
- Optional: `--output-format {json,csv}`, default is `json`
- Optional: `--help`
- When run with no args or `--help`, should print help/usage with descriptions for each arg.
- If any required arg is missing, print error message and usage to `stderr`.

**Testing:**
- Update `test/test_cli.py` to:
  - Test that running with `--help` prints a usage/help message.
  - Test that missing a required argument prints an error to `stderr`.
```

## Prompt 3: Basic File Reading and Writing. Complete: [x]

```
Expand `latinepi/cli.py` to open the input file specified by `--input` and write a given string to the path in `--output`:

**Requirements:**
- If input file doesn't exist, print an error and exit (to stderr).
- Regardless of file contents, write the string `"latinepi: output placeholder\n"` to the output file.
- Print a confirmation message to stdout after writing.
- Properly handle file errors.

**Testing:**
- In `test/test_cli.py`, test:
  - Supplying a non-existent input file returns the correct error.
  - Providing good input and output args results in the output file containing the placeholder string and a confirmation in stdout.
```

## Prompt 4: Parsing CSV/JSON Input With Unit Tests. Complete: [ ]

```
In `latinepi/parser.py`, implement functions to read a CSV or JSON file containing inscriptions.

**Requirements:**
- Function `read_inscriptions(path)` that returns a list of dicts.
  - If CSV: each row as a dict.
  - If JSON: parse as list of dicts (or dict), depending on file.
- Raise a descriptive error on file format/parse errors.
- Add tests in `test/test_parser.py` that:
  - Supply sample CSV and JSON files as temp fixtures and verify correct parsing.
  - Test with malformed CSV/JSON and confirm errors are raised.
```

## Prompt 5: Single Record Parsing/NER Extraction Stub. Complete: [ ]

```
In `parser.py`, add a function `extract_entities(text)` which takes inscription text and returns a hardcoded dict simulating entities (e.g., {'nomen': {'value': 'Iulius', 'confidence': 0.95}}):

**Requirements:**
- `extract_entities(text)` outputs a sample set of fake entity results, meant to mock real NER.
- Expand the CLI to apply `extract_entities` to each record’s relevant text field, and collect results.
- Aggregate entity results (as a list of dicts) and write as JSON (or CSV) via CLI.
- Input files should have at least one 'text' field for extraction.
- Print a progress message to stdout as each record is processed.

**Testing:**
- Write tests in `test_parser.py` for `extract_entities` (verifying output format).
- Write CLI test to check entire process: input file → entity extraction → correct output structure.
```

## Prompt 6: Batch Processing Logic With Real File I/O. Complete: [ ]

```
Update CLI and `parser.py` to:
- Efficiently read all records from the input file (using `read_inscriptions`).
- For each record, run `extract_entities` and store results.
- Write all processed entity dicts to output in a flat (per-record) format.

**Testing:**
- Test parsing >1 inscription in sequence, ensure unique results per input line.
- Test with both JSON and CSV inputs, and varied record counts.
```

## Prompt 7: Integrate latin-bert Model, Minimal NER. Complete: [ ]

```
Switch `extract_entities` in `parser.py` from hardcoded results to integrating the real pretrained `latin-bert` model using HuggingFace Transformers:

**Requirements:**
- Load and initialize `latin-bert` (from https://github.com/dbamman/latin-bert).
- Given text, run model and map NER labels (e.g., "NOMEN", "COGNOMEN") to output fields.
- Extract entity values and confidence scores from model output.
- Handle missing entities gracefully.
- Update previous tests to still work using mocked outputs, and add integration test with real model and a Latin text example.

**Note:** Performance/memory to be kept in mind; avoid loading model more than once.
```

## Prompt 8: Confidence/Threshold Logic. Complete: [ ]

```
Add confidence threshold logic to `extract_entities` and wire it up to CLI arguments:

**Requirements:**
- If an entity’s confidence score is below `--confidence-threshold`, either:
  - Omit the entity from results (default), or
  - If `--flag-ambiguous` is set, include with `"ambiguous": true`.
- Ensure threshold defaults to 0.5 and is user-settable.
- Handle situations where no entities meet threshold.

**Testing:**
- Test with artificial entity outputs for thresholding (bypass the model for controlled test).
- CLI integration test: run with and without `--flag-ambiguous` and different thresholds, verify output.
```

## Prompt 9: Output Formatting, JSON/CSV Choice. Complete: [ ]

```
Expand the CLI to write output as either flat JSON or CSV according to the `--output-format` flag.

**Requirements:**
- Output files must contain all extracted fields per record, plus confidences and ambiguous flags as needed.
- All fields flat at top level for CSV, “field_confidence”, “field_ambiguous” columns included.
- Write individual test cases to ensure correct format and content for both output types.

**Testing:**
- Given controlled input and entity extraction, produce JSON and CSV and check structure and values.
```

## Prompt 10: EDH Download Utility (Basic Fetch and Save). Complete: [ ]
```
Implement the EDH download utility in `latinepi/edh_utils.py`.

**Requirements:**
- Function `download_edh_inscription(inscription_id: str, out_dir: str)`:
    - Fetch details for `inscription_id` from the EDH API (fetch JSON and all available metadata fields, but not images).
    - Save the raw result as a JSON file in `out_dir`, using the ID as filename.
    - Ensure output format matches what the rest of the pipeline can use.
    - Properly create `out_dir` if it does not exist.
    - Handle HTTP errors and invalid IDs cleanly and report them.

- Wire a corresponding CLI flag (`--download-edh <id> --download-dir <path>`) in `cli.py` that calls this utility and prints status.

**Testing:**
- In `test/test_cli.py` and/or `test_edh_utils.py`:
    - Mock the EDH API endpoint.
    - Test downloading an inscription, saving to correct location, and correct error handling.
    - Test CLI invocation with EDH flags, and output file.
```

## Prompt 11: CLI Argument Validation, User Guidance, and Error Handling. Complete: [ ]

```
Enhance CLI UX and robustness in `cli.py`:

**Requirements:**
- Ensure all argument combinations are validated:
    - Require `--download-dir` with `--download-edh`.
    - Prevent unknown argument combinations.
    - Meaningful error messages for misuse, missing arguments, or logic errors.
- Print informative user messages on start, error, and successful completion to either stdout or stderr as appropriate.
- When `--input` and `--output` are missing for a given run, error out with usage message.
- Group arguments in `--help` by logical sections (Input/Output, Download, Extraction).
- Ensure exit codes: 0 on success; nonzero on all error conditions.

**Testing:**
- Expand and test error conditions (missing args, invalid combos, etc) and correct messages/codes.
```

## Prompt 12: End-to-End Integration and Full CLI Test Suite. Complete: [ ]

```
Write an integration test suite covering full workflow scenarios:

**Requirements:**
- In `test/test_cli.py` (or a new `test_integration.py`):
    - Full test: Given a real or mocked input file, end-to-end run of CLI that reads, extracts, and writes output in both formats.
    - EDH path: Use the download feature to fetch a (mocked) inscription, then parse it, then write output.
    - Test handling of all flag combinations (`--flag-ambiguous`, `--confidence-threshold`, formats, etc).
    - Validate error handling and outputs in all major CLI paths.
- Ensure tests clean up temp files created during runs.

**Tip:** All CLI paths exercised, ensuring no orphan code or broken behavior.
```

## Prompt 13: Project Documentation and Usage Examples. Complete: [ ]

```
Write a `README.md` for the project and include documentation in the CLI help text:

**Requirements:**
- Usage overview, example commands, explanation for each CLI argument, and EDH download guidance.
- List all major dependencies and Python version requirements.
- Step-by-step instructions for installing requirements and running tests.
- Add several realistic CLI command-line examples and sample expected outputs.
- Ensure all documented CLI commands match the actual implementation.

**Testing:**
- (Manual) Confirm that all documented commands function as described in test or dev environment.
```

## Prompt 14: Final Wiring and Cleanup. Complete: [ ]

```
Review and wire up all modules:

**Requirements:**
- Ensure `cli.py` imports and calls functions from `parser.py` and `edh_utils.py` as needed.
- Refactor any duplicated code or inconsistent interface.
- Ensure all functions are documented with docstrings.
- Clean up unused imports or variables.
- Re-run all tests to ensure they pass.
```

## Prompt 15: Continuous Integration Scaffold. Complete: [ ]

```
Add a basic configuration for automated testing (optional):

**Requirements:**
- Add a minimal `.github/workflows/python-app.yml` for GitHub Actions, or `.gitlab-ci.yml` for GitLab.
- Workflow should install dependencies and run all tests in the `test/` directory.
- Ensure status badge and info are included in README.md.

**Testing:**
- Confirm workflow is green with test repository (manual step).
```
