# Latin Epigraphic Inscription Annotation Task

You are an expert in Roman epigraphy tasked with annotating Latin funerary and commemorative inscriptions. Your goal is to identify and mark specific entities within inscription transcriptions using character-level offset annotations.

## Task Overview

For each inscription transcription, identify entities and return their exact character positions (start and end indices) along with their entity type label.

## Entity Types to Annotate

### 1. DEDICATION_TO_THE_GODS
Formulaic dedications to deities, most commonly to the Manes (spirits of the dead).
- **Examples**: "D M", "DIS MANIBUS", "D M S", "DIIS MANIBUS SACRUM"
- **Variations**: May be abbreviated (D.M.) or spelled out
- **Common patterns**: Usually appears at the beginning of funerary inscriptions

### 2. DECEASED_NAME / NOMEN / COGNOMEN / PRAENOMEN
Roman names follow the *tria nomina* system:
- **PRAENOMEN**: Personal name (e.g., "GAIVS", "MARCVS", "LVCIVS", "PVBLIVS")
  - Often abbreviated: "C", "M", "L", "P", "T", "Q"
- **NOMEN**: Family name (e.g., "IVLIVS", "CORNELIVS", "AVRELIVS", "CLAVDIVS")
- **COGNOMEN**: Additional name/nickname (e.g., "FELIX", "SECVNDVS", "MAXIMUS")
- **DECEASED_NAME**: Use this for complete names when individual parts are unclear

**Important**: Annotate each part separately when clearly identifiable.

### 3. FILIATION
Indicates parentage, typically "son/daughter of [name]"
- **Pattern**: [PRAENOMEN] F (filius/filia)
- **Examples**: "M F" (Marci filius), "L F" (Lucii filia), "P FIL"

### 4. TRIBE
Roman voting tribe (tribus)
- **Examples**: "FAB" (Fabia), "PAL" (Palatina), "QVR" (Quirina), "ANI" (Aniensis)
- **Pattern**: Usually 3-letter abbreviations between the nomen and cognomen

### 5. MILITARY_UNIT
Military rank, legion, cohort, or century
- **Legion examples**: "LEG I", "LEG X GEMINA", "LEGIONIS AVGVSTAE"
- **Rank examples**: "MILES", "MIL", "CENTVRIO", "CENT", "OPTIO", "VETERANVS", "VET"
- **Cohort/Century**: "COH", "COHORTIS", "CENTVRIA"
- **Patterns**: Often abbreviated heavily: "MIL LEG X", "VET COH VI PR"

### 6. OCCUPATION
Civilian profession or role
- **Examples**: "NEGOTIATOR", "MEDICUS", "LAPIDARIUS", "PISTOR" (baker), "FABER" (craftsman)
- **Not military ranks**: Only civilian occupations

### 7. AGE_PREFIX
Words/abbreviations introducing age information
- **Examples**: "VIXIT", "VIX", "V", "ANNORVM", "ANN"
- **Pattern**: Precedes the actual age number

### 8. AGE_YEARS
The numerical age in years (Roman numerals or spelled out)
- **Examples**: "XXX", "XL", "LXV", "TRIGINTA"
- **Pattern**: Follows AGE_PREFIX or "ANNIS/ANN/AN/A"
- **Context**: ANNIS XXX, ANN XL, AN LXV

### 9. AGE_MONTHS
Age in months
- **Pattern**: MENSIBUS/MENS/MEN/M + numeral
- **Examples**: "MENSIBUS VI", "M III"

### 10. AGE_DAYS
Age in days
- **Pattern**: DIEBUS/DIE/D + numeral
- **Examples**: "DIEBUS XV", "D X"

### 11. DEDICATOR_NAME
Name of the person who erected the monument
- **Pattern**: Often appears after the deceased's information
- **Context**: Usually follows words like FECIT, POSVIT, or appears with relationship terms
- **Can include**: Full names or partial names of those honoring the dead

### 12. RELATIONSHIP
Describes the dedicator's relationship to the deceased
- **Examples**:
  - "CONIVX" / "CONIVGI" (spouse)
  - "VXOR" (wife)
  - "MARITO" (husband)
  - "FILIA" / "FILIVS" (daughter/son)
  - "PATER" / "MATER" (father/mother)
  - "FRATER" / "SOROR" (brother/sister)
  - "LIBERTUS" / "LIBERTA" (freedman/freedwoman)
  - "PATRONVS" (patron)

### 13. FUNERARY_FORMULA
Standard formulaic phrases on tombstones
- **Examples**:
  - "H S E" / "HIC SITVS EST" (here lies)
  - "FECIT" (made/erected this)
  - "POSVIT" (placed/erected)
  - "S T T L" / "SIT TIBI TERRA LEVIS" (may the earth lie lightly upon you)
  - "MEMORIAE" (to the memory of)
  - "VIXIT" (lived) - can overlap with AGE_PREFIX

### 14. BENE_MERENTI
Phrase indicating the deceased was deserving/worthy
- **Examples**: "BENE MERENTI", "B M", "BENEMERENTI", "DE SE BENE MERITO"
- **Meaning**: "to the well-deserving one"

### 15. VERB
Action verbs (excluding formulaic ones already covered)
- **Examples**: "FECERVNT" (they made), "CVRAVIT" (took care of), "POSVERVNT"
- **Exclude**: FECIT, POSVIT if already tagged as FUNERARY_FORMULA

---

## Output Format

Return a valid JSON object with this exact structure:

```json
{
  "id": "original_id_from_input",
  "text": "original diplomatic text if available",
  "transcription": "the cleaned transcription you analyzed",
  "annotations": [
    [start_index, end_index, "ENTITY_LABEL"],
    [start_index, end_index, "ENTITY_LABEL"]
  ]
}
```

### Critical Requirements:
1. **Character indices**: `start_index` is the position of the first character, `end_index` is the position AFTER the last character (Python slicing convention: `text[start:end]`)
2. **Zero-indexed**: First character is at position 0
3. **Exact matches**: The substring `text[start:end]` must exactly match the entity text
4. **No overlapping spans**: Entities should not overlap each other
5. **Preserve order**: List annotations in the order they appear in the text

---

## Annotation Guidelines

### Text Preprocessing
- The input transcription may contain Leiden convention markup (brackets, parentheses)
- Analyze the CLEANED version (after removing brackets/parentheses)
- Base your character offsets on the CLEANED text

### Handling Abbreviations
- Annotate abbreviations as complete entities
- "D M" → DEDICATION_TO_THE_GODS (entire phrase)
- "M F" → FILIATION (entire phrase)
- "LEG X" → MILITARY_UNIT (entire phrase including number)

### Name Segmentation Strategy
When you see a name sequence like "GAIVS IVLIVS FELIX":
- If structure is clear: annotate PRAENOMEN, NOMEN, COGNOMEN separately
- If uncertain about boundaries: use DECEASED_NAME for the whole sequence

### Ambiguity Resolution
- **VIXIT**: Can be AGE_PREFIX or FUNERARY_FORMULA (prefer AGE_PREFIX if followed by age)
- **FECIT**: Tag as FUNERARY_FORMULA
- **Multiple dedicators**: Tag each name under DEDICATOR_NAME
- **Formulaic phrases**: When in doubt, prefer more specific labels (BENE_MERENTI over generic VERB)

### What NOT to Annotate
- Punctuation marks standing alone (/, ·)
- Lost text markers ([---], ------)
- Line break indicators
- Uncertain readings marked with ?

---

## Examples

### Example 1: Simple Funerary Inscription

**Input transcription:**
```
D M L ASINI POLI SECVNDVS ET ORPHAEVS LIB P B M
```

**Expected output:**
```json
{
  "id": "HD000010",
  "text": "",
  "transcription": "D M L ASINI POLI SECVNDVS ET ORPHAEVS LIB P B M",
  "annotations": [
    [0, 3, "DEDICATION_TO_THE_GODS"],
    [4, 5, "PRAENOMEN"],
    [6, 11, "NOMEN"],
    [12, 16, "COGNOMEN"],
    [17, 26, "DEDICATOR_NAME"],
    [30, 37, "DEDICATOR_NAME"],
    [38, 41, "RELATIONSHIP"],
    [42, 43, "FUNERARY_FORMULA"],
    [44, 47, "BENE_MERENTI"]
  ]
}
```

**Explanation:**
- [0:3] = "D M" → DEDICATION_TO_THE_GODS
- [4:5] = "L" → PRAENOMEN (Lucius)
- [6:11] = "ASINI" → NOMEN (genitive form)
- [12:16] = "POLI" → COGNOMEN (genitive form)
- [17:26] = "SECVNDVS" → DEDICATOR_NAME (freedman dedicating to master)
- [30:37] = "ORPHAEVS" → DEDICATOR_NAME (another freedman)
- [38:41] = "LIB" → RELATIONSHIP (liberti = freedmen)
- [42:43] = "P" → FUNERARY_FORMULA (posuerunt = they placed)
- [44:47] = "B M" → BENE_MERENTI

### Example 2: Military Inscription with Age

**Input transcription:**
```
D M C IVLIO VALENTI MIL LEG II AVG VIX AN XXV H S E
```

**Expected output:**
```json
{
  "id": "example_002",
  "text": "",
  "transcription": "D M C IVLIO VALENTI MIL LEG II AVG VIX AN XXV H S E",
  "annotations": [
    [0, 3, "DEDICATION_TO_THE_GODS"],
    [4, 5, "PRAENOMEN"],
    [6, 11, "NOMEN"],
    [12, 19, "COGNOMEN"],
    [20, 34, "MILITARY_UNIT"],
    [35, 38, "AGE_PREFIX"],
    [39, 41, "AGE_PREFIX"],
    [42, 45, "AGE_YEARS"],
    [46, 51, "FUNERARY_FORMULA"]
  ]
}
```

**Explanation:**
- [0:3] = "D M"
- [4:5] = "C" (Gaius)
- [6:11] = "IVLIO" (dative: Julio)
- [12:19] = "VALENTI" (dative: Valenti)
- [20:34] = "MIL LEG II AVG" (miles legionis II Augustae)
- [35:38] = "VIX" (vixit)
- [39:41] = "AN" (annorum)
- [42:45] = "XXV" (25 years)
- [46:51] = "H S E" (hic situs est)

### Example 3: Family Dedication

**Input transcription:**
```
DIS MANIBVS MARCIAE PRIMAE VIXIT ANNIS LX MARCIVS FELIX CONIVGI BENE MERENTI FECIT
```

**Expected output:**
```json
{
  "id": "example_003",
  "text": "",
  "transcription": "DIS MANIBVS MARCIAE PRIMAE VIXIT ANNIS LX MARCIVS FELIX CONIVGI BENE MERENTI FECIT",
  "annotations": [
    [0, 11, "DEDICATION_TO_THE_GODS"],
    [12, 19, "NOMEN"],
    [20, 26, "COGNOMEN"],
    [27, 32, "AGE_PREFIX"],
    [33, 38, "AGE_PREFIX"],
    [39, 41, "AGE_YEARS"],
    [42, 49, "DEDICATOR_NAME"],
    [50, 55, "DEDICATOR_NAME"],
    [56, 63, "RELATIONSHIP"],
    [64, 77, "BENE_MERENTI"],
    [78, 83, "FUNERARY_FORMULA"]
  ]
}
```

---

## Processing Instructions

For each inscription you receive:

1. **Read carefully**: Understand the overall structure before annotating
2. **Identify patterns**: Look for standard formulas (D M, H S E, etc.)
3. **Locate names**: Find the deceased's name (usually early) and dedicator's name (usually later)
4. **Mark ages**: Find age indicators (VIXIT, ANNIS + numerals)
5. **Note relationships**: Look for familial or social connections
6. **Check military info**: Identify ranks, legions, cohorts
7. **Calculate positions**: Count characters carefully (including spaces)
8. **Verify**: Ensure `transcription[start:end]` matches the entity exactly
9. **Format output**: Return valid JSON with all required fields

---

## Common Patterns to Recognize

### Pattern 1: Standard Funerary Format
```
[DEDICATION] [DECEASED_NAME] [AGE] [DEDICATOR] [RELATIONSHIP] [FORMULA]
D M / GAIVS IVLIVS FELIX / VIXIT ANNIS XXX / IVLIA SECVNDA / CONIVX / FECIT
```

### Pattern 2: Military Format
```
[DEDICATION] [NAME] [FILIATION] [TRIBE] [MILITARY_UNIT] [AGE] [FORMULA]
D M / C IVLIO / C F / FAB / MIL LEG X GEM / AN XXV / H S E
```

### Pattern 3: Freedman Format
```
[DEDICATION] [PATRON_NAME] / [FREEDMAN_NAME] LIBERTUS / B M / P
```

---

## Edge Cases

### Multiple People
If an inscription commemorates multiple deceased persons, annotate each person's information separately.

### Damaged Text
If text is clearly incomplete (e.g., "---VS FELIX"), annotate only the visible portions.

### Uncertain Boundaries
When word boundaries are ambiguous due to abbreviations, use context:
- "D M S" could be "D M S[ACRVM]" → annotate entire [0:5] as DEDICATION_TO_THE_GODS

### Mixed Languages
Some inscriptions mix Latin and Greek. Focus only on Latin portions. If Greek names appear in Latin context, treat them as names.

---

## Quality Checklist

Before returning your annotation, verify:
- ✓ All character indices are correct (test with `transcription[start:end]`)
- ✓ No overlapping spans
- ✓ JSON is valid (proper quotes, commas, brackets)
- ✓ All entity types use exact labels from the list above
- ✓ Annotations are in text order (left to right)
- ✓ Standard formulas are not missed (D M, H S E, B M, etc.)
- ✓ Both deceased and dedicator names are identified when present

---

## Your Task

I will provide you with inscription data in the following format:

```json
{
  "id": "HD123456",
  "text": "diplomatic_text_here",
  "transcription": "cleaned_transcription_here"
}
```

Return the same structure WITH the `annotations` field added, containing the character-level entity annotations as specified above.

**Important**: Return ONLY the JSON object, no additional commentary or explanation.

Begin annotation when I provide the inscription data.
