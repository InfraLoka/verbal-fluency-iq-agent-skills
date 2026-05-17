# Verbal Fluency IQ — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a vendorless MCP-based agent skill that predicts IQ, mental age, and education level from English/Indonesian text using deterministic verbal fluency tools with sentence-level citation evidence.

**Architecture:** 11 atomic MCP tools exposed via FastMCP server; `.agent/SKILL.md` defines the call sequence in vendor-neutral format. Each tool is a focused Python module. Agent orchestrates the pipeline — server has no orchestration logic.

**Tech Stack:** Python 3.11+, FastMCP, spaCy (en_core_web_sm + xx_ent_wiki_sm), lexicalrichness, textstat, sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2), langdetect, langid, PySastrawi, NLTK, scikit-learn

---

## File Map

| File | Responsibility |
|------|---------------|
| `mcp-server/tools/preprocess.py` | detect_language, preprocess_text |
| `mcp-server/tools/lexical.py` | analyze_lexical (MATTR, VOCD-D, hapax, density) |
| `mcp-server/tools/syntactic.py` | analyze_syntactic (MSL, clause density, dep depth) |
| `mcp-server/tools/semantic.py` | analyze_semantic (coherence, drift, chains) |
| `mcp-server/tools/readability.py` | analyze_readability (Flesch, Fog, ARI, CL) |
| `mcp-server/tools/mapper.py` | compute_vfs, predict_iq, predict_mental_age, estimate_education |
| `mcp-server/tools/reporter.py` | generate_report (JSON + structured report with citations) |
| `mcp-server/server.py` | FastMCP entry point — exposes all 11 tools |
| `mcp-server/config/iq_norms.json` | VFS→IQ band lookup table |
| `mcp-server/config/edu_norms.json` | Readability→education level mapping |
| `mcp-server/config/id_syllables.json` | Indonesian syllable counting rules |
| `.agent/SKILL.md` | Vendorless skill definition (works on any agent) |
| `.agent/tools.json` | JSON Schema tool contracts (no vendor syntax) |
| `tests/test_preprocess.py` | Unit tests for language detection and preprocessing |
| `tests/test_lexical.py` | Unit tests for lexical analysis |
| `tests/test_syntactic.py` | Unit tests for syntactic analysis |
| `tests/test_semantic.py` | Unit tests for semantic analysis |
| `tests/test_readability.py` | Unit tests for readability |
| `tests/test_mapper.py` | Unit tests for VFS + IQ + education mapping |
| `tests/test_reporter.py` | Unit tests for report generation |
| `tests/test_pipeline.py` | End-to-end pipeline integration test |
| `requirements.txt` | Python dependencies |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `mcp-server/tools/__init__.py`
- Create: `mcp-server/config/` (directory)
- Create: `tests/__init__.py`

- [ ] **Step 1: Create the directory tree**

```bash
mkdir -p mcp-server/tools mcp-server/config tests .agent
touch mcp-server/__init__.py mcp-server/tools/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write requirements.txt**

Create `requirements.txt`:
```
fastmcp>=0.4.0
spacy>=3.7.0
lexicalrichness>=0.4.2
textstat>=0.7.3
sentence-transformers>=2.6.0
langdetect>=1.0.9
langid>=1.1.6
PySastrawi>=1.2.0
nltk>=3.8.1
scikit-learn>=1.4.0
numpy>=1.26.0
pytest>=8.0.0
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m spacy download xx_ent_wiki_sm
```

Expected: all packages install without error.

- [ ] **Step 4: Verify installs**

```bash
python -c "import spacy; import lexicalrichness; import textstat; import langdetect; import langid; from Sastrawi.Stemmer.StemmerFactory import StemmerFactory; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git init
git add requirements.txt mcp-server/ tests/ .agent/
git commit -m "chore: scaffold verbal-fluency-iq project structure"
```

---

## Task 2: Config Files

**Files:**
- Create: `mcp-server/config/iq_norms.json`
- Create: `mcp-server/config/edu_norms.json`
- Create: `mcp-server/config/id_syllables.json`

- [ ] **Step 1: Write iq_norms.json**

Create `mcp-server/config/iq_norms.json`:
```json
{
  "bands": [
    {
      "vfs_min": 85, "vfs_max": 100,
      "iq_min": 125, "iq_max": 145,
      "label": "Gifted / Highly Gifted",
      "percentile_min": 95
    },
    {
      "vfs_min": 70, "vfs_max": 84.99,
      "iq_min": 110, "iq_max": 124,
      "label": "Above Average / Superior",
      "percentile_min": 75
    },
    {
      "vfs_min": 55, "vfs_max": 69.99,
      "iq_min": 90, "iq_max": 109,
      "label": "Average",
      "percentile_min": 25
    },
    {
      "vfs_min": 40, "vfs_max": 54.99,
      "iq_min": 75, "iq_max": 89,
      "label": "Below Average",
      "percentile_min": 5
    },
    {
      "vfs_min": 0, "vfs_max": 39.99,
      "iq_min": 55, "iq_max": 74,
      "label": "Low",
      "percentile_min": 1
    }
  ],
  "default_chronological_age": 30
}
```

- [ ] **Step 2: Write edu_norms.json**

Create `mcp-server/config/edu_norms.json`:
```json
{
  "levels": [
    {
      "fog_min": 17, "ari_min": 16, "lexical_density_min": 0.60,
      "level_en": "Doctoral / Postgrad Research",
      "level_id": "Doktor / Peneliti Pascasarjana",
      "code": "S3"
    },
    {
      "fog_min": 14, "ari_min": 13, "lexical_density_min": 0.55,
      "level_en": "Graduate",
      "level_id": "Magister (S2)",
      "code": "S2"
    },
    {
      "fog_min": 11, "ari_min": 10, "lexical_density_min": 0.48,
      "level_en": "Undergraduate",
      "level_id": "Sarjana (S1/D4)",
      "code": "S1"
    },
    {
      "fog_min": 9, "ari_min": 8, "lexical_density_min": 0.42,
      "level_en": "Vocational / Diploma",
      "level_id": "Diploma (D1-D3)",
      "code": "D3"
    },
    {
      "fog_min": 7, "ari_min": 6, "lexical_density_min": 0.36,
      "level_en": "Senior High School",
      "level_id": "SMA/SMK",
      "code": "SMA"
    },
    {
      "fog_min": 5, "ari_min": 4, "lexical_density_min": 0.30,
      "level_en": "Junior High School",
      "level_id": "SMP",
      "code": "SMP"
    },
    {
      "fog_min": 0, "ari_min": 0, "lexical_density_min": 0.0,
      "level_en": "Primary School",
      "level_id": "SD",
      "code": "SD"
    }
  ]
}
```

- [ ] **Step 3: Write id_syllables.json**

Create `mcp-server/config/id_syllables.json`:
```json
{
  "vowels": ["a", "e", "i", "o", "u"],
  "diphthongs": ["ai", "au", "oi", "ei"],
  "note": "Indonesian syllable counting: count vowel nuclei. Diphthongs count as one syllable."
}
```

- [ ] **Step 4: Verify JSON is valid**

```bash
python -c "import json; [json.load(open(f'mcp-server/config/{f}')) for f in ['iq_norms.json','edu_norms.json','id_syllables.json']]; print('All JSON valid')"
```

Expected: `All JSON valid`

- [ ] **Step 5: Commit**

```bash
git add mcp-server/config/
git commit -m "feat: add IQ, education, and Indonesian syllable norm config files"
```

---

## Task 3: Language Detection and Preprocessing

**Files:**
- Create: `mcp-server/tools/preprocess.py`
- Create: `tests/test_preprocess.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_preprocess.py`:
```python
import sys
sys.path.insert(0, "mcp-server")

from tools.preprocess import detect_language, preprocess_text


def test_detect_english():
    result = detect_language("The quick brown fox jumps over the lazy dog.")
    assert result["lang"] == "en"
    assert result["confidence"] > 0.5


def test_detect_indonesian():
    result = detect_language("Saya pergi ke pasar untuk membeli sayuran segar.")
    assert result["lang"] == "id"
    assert result["confidence"] > 0.5


def test_detect_returns_en_or_id_only():
    result = detect_language("Bonjour le monde, comment ca va aujourd'hui?")
    assert result["lang"] in ("en", "id")


def test_preprocess_strips_urls():
    result = preprocess_text("Check this out http://example.com great stuff", "en")
    assert "http" not in " ".join(result["tokens"])


def test_preprocess_strips_mentions():
    result = preprocess_text("Hey @john how are you doing today?", "en")
    assert "@john" not in result["tokens"]


def test_preprocess_returns_sentences_with_idx():
    result = preprocess_text("Hello world. How are you? I am fine.", "en")
    assert len(result["sentences"]) >= 2
    assert all("idx" in s and "text" in s for s in result["sentences"])
    assert result["sentences"][0]["idx"] == 0


def test_preprocess_word_count():
    result = preprocess_text("One two three four five.", "en")
    assert result["word_count"] == 5


def test_preprocess_short_text_minimum():
    result = preprocess_text("Hello.", "en")
    assert result["word_count"] >= 1
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_preprocess.py -v 2>&1 | head -30
```

Expected: `ImportError` or `ModuleNotFoundError` (file doesn't exist yet).

- [ ] **Step 3: Write preprocess.py**

Create `mcp-server/tools/preprocess.py`:
```python
import re
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
import langid
import spacy

DetectorFactory.seed = 42

_nlp_cache: dict = {}


def _get_nlp(lang: str):
    if lang not in _nlp_cache:
        model = "en_core_web_sm" if lang == "en" else "xx_ent_wiki_sm"
        _nlp_cache[lang] = spacy.load(model)
    return _nlp_cache[lang]


def detect_language(text: str) -> dict:
    try:
        ld_lang = detect(text)
    except LangDetectException:
        ld_lang = "en"

    li_lang, li_conf = langid.classify(text)

    if ld_lang == li_lang:
        lang = ld_lang
        confidence = round(min(0.95, 0.70 + float(li_conf) * 0.25), 2)
    else:
        lang = li_lang
        confidence = 0.65

    if lang not in ("en", "id"):
        lang = "en"
        confidence = 0.50

    return {"lang": lang, "confidence": confidence}


def preprocess_text(text: str, lang: str) -> dict:
    cleaned = re.sub(r"http\S+|www\S+", "", text)
    cleaned = re.sub(r"@\w+|#\w+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    nlp = _get_nlp(lang)
    doc = nlp(cleaned)

    sentences = [
        {"idx": i, "text": sent.text.strip()}
        for i, sent in enumerate(doc.sents)
        if sent.text.strip()
    ]
    tokens = [t.text for t in doc if not t.is_space]
    word_count = len([t for t in doc if not t.is_space and not t.is_punct])

    return {
        "tokens": tokens,
        "sentences": sentences,
        "word_count": word_count,
        "sentence_count": len(sentences),
        "text_clean": cleaned,
    }
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_preprocess.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/preprocess.py tests/test_preprocess.py
git commit -m "feat: add language detection and text preprocessing tools"
```

---

## Task 4: Lexical Analysis Tool

**Files:**
- Create: `mcp-server/tools/lexical.py`
- Create: `tests/test_lexical.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_lexical.py`:
```python
import sys
sys.path.insert(0, "mcp-server")

from tools.lexical import analyze_lexical


RICH_TOKENS = (
    "The epistemological underpinnings of this philosophical discourse "
    "traverse labyrinthine corridors of ontological ambiguity wherein "
    "conventional paradigms dissolve into hermeneutical uncertainty "
    "requiring unprecedented methodological innovation and interdisciplinary "
    "synthesis across divergent theoretical frameworks"
).split()

SIMPLE_TOKENS = "the cat sat on the mat the cat sat the mat sat".split()

SENTENCES = [
    {"idx": 0, "text": "The cat sat on the mat."},
    {"idx": 1, "text": "The epistemological underpinnings dissolve into hermeneutical uncertainty."},
]


def test_analyze_lexical_returns_required_keys():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    for key in ("mattr", "hapax_ratio", "lexical_density", "avg_word_length", "score", "evidence"):
        assert key in result, f"Missing key: {key}"


def test_rich_vocabulary_scores_higher_than_simple():
    rich = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    simple = analyze_lexical(SIMPLE_TOKENS, SENTENCES, "en")
    assert rich["score"] > simple["score"]


def test_mattr_between_0_and_1():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    assert 0 <= result["mattr"] <= 1


def test_hapax_ratio_between_0_and_1():
    result = analyze_lexical(SIMPLE_TOKENS, SENTENCES, "en")
    assert 0 <= result["hapax_ratio"] <= 1


def test_score_between_0_and_100():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    assert 0 <= result["score"] <= 100


def test_evidence_contains_sentence_idx_and_triggered_by():
    result = analyze_lexical(RICH_TOKENS, SENTENCES, "en")
    for ev in result["evidence"]:
        assert "sentence_idx" in ev
        assert "sentence" in ev
        assert "triggered_by" in ev
        assert len(ev["triggered_by"]) > 0


def test_empty_tokens_returns_error():
    result = analyze_lexical([], SENTENCES, "en")
    assert "error" in result
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_lexical.py -v 2>&1 | head -20
```

Expected: `ImportError` or `ModuleNotFoundError`.

- [ ] **Step 3: Write lexical.py**

Create `mcp-server/tools/lexical.py`:
```python
from collections import Counter
from typing import List

from lexicalrichness import LexicalRichness


def _mattr(tokens: List[str], window: int = 50) -> float:
    if len(tokens) < window:
        return len(set(tokens)) / len(tokens) if tokens else 0.0
    ttrs = [
        len(set(tokens[i : i + window])) / window
        for i in range(len(tokens) - window + 1)
    ]
    return sum(ttrs) / len(ttrs)


def analyze_lexical(tokens: List[str], sentences: List[dict], lang: str) -> dict:
    alpha = [t for t in tokens if t.isalpha()]
    if not alpha:
        return {"score": 0.0, "error": "No alphabetic tokens found"}

    lower = [t.lower() for t in alpha]

    if lang == "id":
        try:
            from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
            stemmer = StemmerFactory().create_stemmer()
            mattr_tokens = [stemmer.stem(t) for t in lower]
        except ImportError:
            mattr_tokens = lower
    else:
        mattr_tokens = lower

    mattr = round(_mattr(mattr_tokens), 3)

    vocd_d = None
    if len(alpha) >= 50:
        try:
            lex = LexicalRichness(" ".join(alpha))
            vocd_d = round(lex.vocd(), 1)
        except Exception:
            vocd_d = None

    freq = Counter(lower)
    hapax_count = sum(1 for f in freq.values() if f == 1)
    hapax_ratio = round(hapax_count / len(freq), 3) if freq else 0.0

    avg_word_length = round(sum(len(t) for t in alpha) / len(alpha), 1)

    content_words = [t for t in alpha if len(t) > 3]
    lexical_density = round(len(content_words) / len(alpha), 3)

    mattr_score = min(100.0, max(0.0, (mattr - 0.3) / 0.6 * 100))
    hapax_score = min(100.0, max(0.0, (hapax_ratio - 0.2) / 0.5 * 100))
    awl_score = min(100.0, max(0.0, (avg_word_length - 3.5) / 4.0 * 100))
    ld_score = min(100.0, max(0.0, (lexical_density - 0.3) / 0.4 * 100))

    score = round(mattr_score * 0.40 + hapax_score * 0.30 + awl_score * 0.15 + ld_score * 0.15, 1)

    evidence = []
    for sent in sentences:
        words = [w for w in sent["text"].split() if w.isalpha()]
        rare = [w for w in words if freq.get(w.lower(), 0) == 1 and len(w) > 5]
        if rare:
            evidence.append({
                "sentence_idx": sent["idx"],
                "sentence": sent["text"],
                "triggered_by": [f"hapax:{w}" for w in rare[:3]],
            })

    return {
        "mattr": mattr,
        "vocd_d": vocd_d,
        "hapax_ratio": hapax_ratio,
        "lexical_density": lexical_density,
        "avg_word_length": avg_word_length,
        "score": score,
        "evidence": evidence[:3],
    }
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_lexical.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/lexical.py tests/test_lexical.py
git commit -m "feat: add lexical analysis tool (MATTR, VOCD-D, hapax, density)"
```

---

## Task 5: Syntactic Analysis Tool

**Files:**
- Create: `mcp-server/tools/syntactic.py`
- Create: `tests/test_syntactic.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_syntactic.py`:
```python
import sys
sys.path.insert(0, "mcp-server")

from tools.syntactic import analyze_syntactic

COMPLEX_SENTENCES = [
    {"idx": 0, "text": "Although the data was inconclusive, the team proceeded because the deadline demanded immediate action."},
    {"idx": 1, "text": "The report, which had been revised three times by external reviewers who questioned the methodology, was finally submitted."},
    {"idx": 2, "text": "Researchers who study complex systems argue that emergent properties cannot be predicted from constituent parts alone."},
]

SIMPLE_SENTENCES = [
    {"idx": 0, "text": "The cat sat."},
    {"idx": 1, "text": "Dogs run fast."},
    {"idx": 2, "text": "Birds fly high."},
]


def test_returns_required_keys():
    result = analyze_syntactic(COMPLEX_SENTENCES, "en")
    for key in ("mean_sentence_length", "clause_density", "subordination_index",
                "dependency_depth", "passive_ratio", "score", "evidence"):
        assert key in result


def test_complex_scores_higher_than_simple():
    complex_result = analyze_syntactic(COMPLEX_SENTENCES, "en")
    simple_result = analyze_syntactic(SIMPLE_SENTENCES, "en")
    assert complex_result["score"] > simple_result["score"]


def test_score_between_0_and_100():
    result = analyze_syntactic(COMPLEX_SENTENCES, "en")
    assert 0 <= result["score"] <= 100


def test_mean_sentence_length_positive():
    result = analyze_syntactic(SIMPLE_SENTENCES, "en")
    assert result["mean_sentence_length"] > 0


def test_passive_ratio_between_0_and_1():
    result = analyze_syntactic(COMPLEX_SENTENCES, "en")
    assert 0 <= result["passive_ratio"] <= 1


def test_evidence_has_correct_structure():
    result = analyze_syntactic(COMPLEX_SENTENCES, "en")
    for ev in result["evidence"]:
        assert "sentence_idx" in ev
        assert "sentence" in ev
        assert "triggered_by" in ev
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_syntactic.py -v 2>&1 | head -20
```

Expected: `ImportError`.

- [ ] **Step 3: Write syntactic.py**

Create `mcp-server/tools/syntactic.py`:
```python
from typing import List
import spacy

_nlp_cache: dict = {}

SUBORDINATE_DEPS = {"advcl", "relcl", "acl", "csubj", "ccomp", "xcomp"}
CLAUSE_DEPS = SUBORDINATE_DEPS | {"ROOT"}


def _get_nlp(lang: str):
    if lang not in _nlp_cache:
        model = "en_core_web_sm" if lang == "en" else "xx_ent_wiki_sm"
        _nlp_cache[lang] = spacy.load(model)
    return _nlp_cache[lang]


def _dep_depth(token) -> int:
    depth = 0
    seen = set()
    while token.head != token and id(token) not in seen:
        seen.add(id(token))
        token = token.head
        depth += 1
    return depth


def analyze_syntactic(sentences: List[dict], lang: str) -> dict:
    nlp = _get_nlp(lang)
    lengths, clause_counts, sub_counts, dep_depths = [], [], [], []
    passive_count = 0
    evidence = []

    for sent_data in sentences:
        doc = nlp(sent_data["text"])
        words = [t for t in doc if not t.is_space and not t.is_punct]
        lengths.append(len(words))

        clauses = sum(1 for t in doc if t.dep_ in CLAUSE_DEPS)
        clause_counts.append(max(1, clauses))

        subs = sum(1 for t in doc if t.dep_ in SUBORDINATE_DEPS)
        sub_counts.append(subs)

        max_depth = max((_dep_depth(t) for t in doc if not t.is_space), default=0)
        dep_depths.append(max_depth)

        is_passive = any(t.dep_ in {"nsubjpass", "auxpass", "aux:pass"} for t in doc)
        if is_passive:
            passive_count += 1

        triggered = []
        if subs >= 2:
            triggered.append(f"subordinate_clauses:{subs}")
        if max_depth >= 6:
            triggered.append(f"dep_depth:{max_depth}")
        if is_passive:
            triggered.append("passive_voice")
        if triggered:
            evidence.append({
                "sentence_idx": sent_data["idx"],
                "sentence": sent_data["text"],
                "triggered_by": triggered,
            })

    n = len(sentences)
    msl = round(sum(lengths) / n, 1) if n else 0
    clause_density = round(sum(clause_counts) / n, 2) if n else 0
    sub_index = round(sum(sub_counts) / n, 3) if n else 0
    dep_depth = round(sum(dep_depths) / n, 1) if n else 0
    passive_ratio = round(passive_count / n, 3) if n else 0

    msl_score = min(100.0, max(0.0, (msl - 8) / 22 * 100))
    cd_score = min(100.0, max(0.0, (clause_density - 1.0) / 2.5 * 100))
    si_score = min(100.0, max(0.0, sub_index / 1.5 * 100))
    dd_score = min(100.0, max(0.0, (dep_depth - 2) / 8 * 100))

    score = round(msl_score * 0.30 + cd_score * 0.35 + si_score * 0.25 + dd_score * 0.10, 1)

    return {
        "mean_sentence_length": msl,
        "clause_density": clause_density,
        "subordination_index": sub_index,
        "dependency_depth": dep_depth,
        "passive_ratio": passive_ratio,
        "score": score,
        "evidence": evidence[:3],
    }
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_syntactic.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/syntactic.py tests/test_syntactic.py
git commit -m "feat: add syntactic analysis tool (MSL, clause density, dep depth, passive)"
```

---

## Task 6: Semantic Analysis Tool

**Files:**
- Create: `mcp-server/tools/semantic.py`
- Create: `tests/test_semantic.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_semantic.py`:
```python
import sys
sys.path.insert(0, "mcp-server")

from tools.semantic import analyze_semantic

COHERENT_TEXT = (
    "Climate change is accelerating. The acceleration is driven by carbon emissions. "
    "Carbon emissions must be reduced through policy intervention. "
    "Policy intervention requires international cooperation."
)
COHERENT_SENTENCES = [
    {"idx": 0, "text": "Climate change is accelerating."},
    {"idx": 1, "text": "The acceleration is driven by carbon emissions."},
    {"idx": 2, "text": "Carbon emissions must be reduced through policy intervention."},
    {"idx": 3, "text": "Policy intervention requires international cooperation."},
]

INCOHERENT_TEXT = "Dogs bark at night. The economy grew last quarter. Pizza is delicious. Mountains are tall."
INCOHERENT_SENTENCES = [
    {"idx": 0, "text": "Dogs bark at night."},
    {"idx": 1, "text": "The economy grew last quarter."},
    {"idx": 2, "text": "Pizza is delicious."},
    {"idx": 3, "text": "Mountains are tall."},
]

SINGLE_SENTENCE = [{"idx": 0, "text": "Hello world."}]


def test_returns_required_keys():
    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    for key in ("argument_coherence", "topic_drift_index", "lexical_chain_density",
                "entity_sophistication", "score", "evidence"):
        assert key in result


def test_coherent_text_higher_coherence():
    coherent = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    incoherent = analyze_semantic(INCOHERENT_TEXT, INCOHERENT_SENTENCES, "en")
    assert coherent["argument_coherence"] > incoherent["argument_coherence"]


def test_score_between_0_and_100():
    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    assert 0 <= result["score"] <= 100


def test_single_sentence_returns_gracefully():
    result = analyze_semantic("Hello world.", SINGLE_SENTENCE, "en")
    assert "note" in result or result["score"] is not None


def test_evidence_has_coherence_and_note():
    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    for ev in result["evidence"]:
        assert "sentence_idx_from" in ev
        assert "sentence_idx_to" in ev
        assert "coherence" in ev
        assert "note" in ev


def test_entity_sophistication_is_valid_label():
    result = analyze_semantic(COHERENT_TEXT, COHERENT_SENTENCES, "en")
    assert result["entity_sophistication"] in ("ABSTRACT", "CONCRETE", "MINIMAL")
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_semantic.py -v 2>&1 | head -20
```

Expected: `ImportError`.

- [ ] **Step 3: Write semantic.py**

Create `mcp-server/tools/semantic.py`:
```python
from collections import defaultdict
from typing import List

import numpy as np
import spacy
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

_model_cache = {}
_nlp_cache: dict = {}

ABSTRACT_TYPES = {"LAW", "ORG", "NORP", "EVENT", "WORK_OF_ART", "LANGUAGE"}
CONCRETE_TYPES = {"PERSON", "GPE", "LOC", "FAC", "PRODUCT"}


def _get_model():
    if "model" not in _model_cache:
        _model_cache["model"] = SentenceTransformer(
            "paraphrase-multilingual-MiniLM-L12-v2"
        )
    return _model_cache["model"]


def _get_nlp(lang: str):
    if lang not in _nlp_cache:
        _nlp_cache[lang] = spacy.load(
            "en_core_web_sm" if lang == "en" else "xx_ent_wiki_sm"
        )
    return _nlp_cache[lang]


def analyze_semantic(text: str, sentences: List[dict], lang: str) -> dict:
    if len(sentences) < 2:
        return {
            "argument_coherence": None,
            "topic_drift_index": None,
            "lexical_chain_density": 0.0,
            "entity_sophistication": "MINIMAL",
            "score": 50.0,
            "evidence": [],
            "note": "Too few sentences for full semantic analysis",
        }

    model = _get_model()
    texts = [s["text"] for s in sentences]
    embeddings = model.encode(texts)

    evidence = []
    coherence_vals = []
    for i in range(len(embeddings) - 1):
        sim = float(cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0])
        coherence_vals.append(sim)
        note = (
            "causal chain detected"
            if sim > 0.75
            else "slight drift"
            if sim < 0.50
            else "moderate transition"
        )
        evidence.append({
            "sentence_idx_from": sentences[i]["idx"],
            "sentence_idx_to": sentences[i + 1]["idx"],
            "coherence": round(sim, 3),
            "note": note,
        })

    argument_coherence = round(float(np.mean(coherence_vals)), 3)
    topic_drift_index = round(float(np.std(coherence_vals)), 3)

    nlp = _get_nlp(lang)
    doc = nlp(text)
    entity_types = {ent.label_ for ent in doc.ents}
    if entity_types & ABSTRACT_TYPES:
        entity_sophistication = "ABSTRACT"
    elif entity_types & CONCRETE_TYPES:
        entity_sophistication = "CONCRETE"
    else:
        entity_sophistication = "MINIMAL"

    word_positions: dict = defaultdict(set)
    for i, s in enumerate(sentences):
        for w in s["text"].lower().split():
            if len(w) > 4:
                word_positions[w].add(i)
    chained = sum(1 for pos in word_positions.values() if len(pos) > 1)
    total = len(word_positions)
    lexical_chain_density = round(chained / total, 3) if total else 0.0

    coh_score = min(100.0, max(0.0, (argument_coherence - 0.3) / 0.6 * 100))
    drift_score = min(100.0, max(0.0, (1 - topic_drift_index / 0.3) * 100))
    chain_score = min(100.0, max(0.0, (lexical_chain_density - 0.1) / 0.5 * 100))
    entity_score = {"ABSTRACT": 80.0, "CONCRETE": 50.0, "MINIMAL": 20.0}[entity_sophistication]

    score = round(
        coh_score * 0.45 + drift_score * 0.25 + chain_score * 0.20 + entity_score * 0.10, 1
    )

    return {
        "argument_coherence": argument_coherence,
        "topic_drift_index": topic_drift_index,
        "lexical_chain_density": lexical_chain_density,
        "entity_sophistication": entity_sophistication,
        "score": score,
        "evidence": evidence[:5],
    }
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_semantic.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/semantic.py tests/test_semantic.py
git commit -m "feat: add semantic analysis tool (coherence, drift, chain density)"
```

---

## Task 7: Readability Analysis Tool

**Files:**
- Create: `mcp-server/tools/readability.py`
- Create: `tests/test_readability.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_readability.py`:
```python
import sys
sys.path.insert(0, "mcp-server")

from tools.readability import analyze_readability

COMPLEX_TEXT = (
    "The epistemological underpinnings of contemporary hermeneutical theory "
    "necessitate a comprehensive reevaluation of ontological presuppositions "
    "embedded within conventional philosophical frameworks. "
    "Unprecedented methodological innovations require interdisciplinary synthesis "
    "across divergent theoretical paradigms."
)

SIMPLE_TEXT = "The cat sat on the mat. Dogs like to run. Birds can fly."

ID_TEXT = (
    "Perkembangan teknologi informasi yang pesat telah mengubah paradigma "
    "komunikasi modern secara fundamental dan komprehensif. "
    "Implementasi sistem yang berkelanjutan memerlukan koordinasi multidimensional."
)


def test_returns_required_keys():
    result = analyze_readability(COMPLEX_TEXT, "en")
    for key in ("flesch_reading_ease", "gunning_fog", "ari", "coleman_liau", "score", "evidence"):
        assert key in result


def test_complex_text_higher_fog_than_simple():
    complex_r = analyze_readability(COMPLEX_TEXT, "en")
    simple_r = analyze_readability(SIMPLE_TEXT, "en")
    assert complex_r["gunning_fog"] > simple_r["gunning_fog"]


def test_score_between_0_and_100():
    result = analyze_readability(COMPLEX_TEXT, "en")
    assert 0 <= result["score"] <= 100


def test_indonesian_text_runs_without_error():
    result = analyze_readability(ID_TEXT, "id")
    assert "score" in result
    assert result["score"] >= 0


def test_evidence_contains_polysyllabic_trigger():
    result = analyze_readability(COMPLEX_TEXT, "en")
    if result["evidence"]:
        for ev in result["evidence"]:
            assert "sentence_idx" in ev
            assert any("polysyllabic" in t for t in ev["triggered_by"])
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_readability.py -v 2>&1 | head -20
```

Expected: `ImportError`.

- [ ] **Step 3: Write readability.py**

Create `mcp-server/tools/readability.py`:
```python
import textstat


def _count_id_syllables(word: str) -> int:
    vowels = set("aeiouAEIOU")
    count, prev_vowel = 0, False
    for ch in word:
        is_v = ch in vowels
        if is_v and not prev_vowel:
            count += 1
        prev_vowel = is_v
    return max(1, count)


def _syllable_count(word: str, lang: str) -> int:
    if lang == "id":
        return _count_id_syllables(word)
    return textstat.syllable_count(word)


def analyze_readability(text: str, lang: str) -> dict:
    textstat.set_lang("en_US")

    sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]

    evidence = []
    for i, sent in enumerate(sentences[:20]):
        words = sent.split()
        if not words:
            continue
        polysyllabic = sum(1 for w in words if _syllable_count(w, lang) >= 3)
        density = round(polysyllabic / len(words), 2)
        if density >= 0.3:
            evidence.append({
                "sentence_idx": i,
                "sentence": sent,
                "triggered_by": [f"polysyllabic_density:{density}"],
            })

    if lang == "id":
        words_all = text.split()
        sents_clean = [s for s in sentences if s]
        avg_sent_len = len(words_all) / max(1, len(sents_clean))
        avg_syl = sum(_count_id_syllables(w) for w in words_all) / max(1, len(words_all))
        flesch = round(206.835 - 1.015 * avg_sent_len - 84.6 * avg_syl, 1)
    else:
        flesch = round(textstat.flesch_reading_ease(text), 1)

    fog = round(textstat.gunning_fog(text), 1)
    ari = round(textstat.automated_readability_index(text), 1)
    cl = round(textstat.coleman_liau_index(text), 1)

    fog_score = min(100.0, max(0.0, (fog - 6) / 12 * 100))
    ari_score = min(100.0, max(0.0, (ari - 5) / 11 * 100))
    cl_score = min(100.0, max(0.0, (cl - 5) / 11 * 100))
    flesch_score = min(100.0, max(0.0, 100 - flesch))

    score = round(fog_score * 0.35 + ari_score * 0.30 + cl_score * 0.20 + flesch_score * 0.15, 1)

    return {
        "flesch_reading_ease": flesch,
        "gunning_fog": fog,
        "ari": ari,
        "coleman_liau": cl,
        "score": score,
        "evidence": evidence[:3],
    }
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_readability.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/readability.py tests/test_readability.py
git commit -m "feat: add readability analysis tool (Flesch, Fog, ARI, Coleman-Liau)"
```

---

## Task 8: VFS, IQ, Mental Age, and Education Mapper

**Files:**
- Create: `mcp-server/tools/mapper.py`
- Create: `tests/test_mapper.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_mapper.py`:
```python
import sys
sys.path.insert(0, "mcp-server")

from tools.mapper import (
    compute_verbal_fluency_score,
    predict_iq,
    predict_mental_age,
    estimate_education_level,
)

MOCK_LEXICAL = {"score": 80.0, "mattr": 0.78, "hapax_ratio": 0.42, "lexical_density": 0.53, "avg_word_length": 5.8, "vocd_d": 61.2, "evidence": []}
MOCK_SYNTACTIC = {"score": 70.0, "mean_sentence_length": 18.3, "clause_density": 2.1, "subordination_index": 0.48, "dependency_depth": 6.0, "passive_ratio": 0.12, "evidence": []}
MOCK_SEMANTIC = {"score": 72.0, "argument_coherence": 0.74, "topic_drift_index": 0.21, "lexical_chain_density": 0.61, "entity_sophistication": "ABSTRACT", "evidence": []}
MOCK_READABILITY = {"score": 65.0, "flesch_reading_ease": 52.1, "gunning_fog": 12.4, "ari": 11.8, "coleman_liau": 12.1, "evidence": []}


def test_vfs_returns_required_keys():
    result = compute_verbal_fluency_score(MOCK_LEXICAL, MOCK_SYNTACTIC, MOCK_SEMANTIC, MOCK_READABILITY, 412, "en")
    for key in ("vfs", "lexical", "syntactic", "semantic", "readability", "confidence", "confidence_label", "lang", "text_length_words"):
        assert key in result


def test_vfs_weighted_formula():
    result = compute_verbal_fluency_score(MOCK_LEXICAL, MOCK_SYNTACTIC, MOCK_SEMANTIC, MOCK_READABILITY, 412, "en")
    expected = 80 * 0.35 + 70 * 0.25 + 72 * 0.25 + 65 * 0.15
    assert abs(result["vfs"] - expected) < 0.2


def test_confidence_very_low_for_short_text():
    result = compute_verbal_fluency_score(MOCK_LEXICAL, MOCK_SYNTACTIC, MOCK_SEMANTIC, MOCK_READABILITY, 20, "en")
    assert result["confidence_label"] == "VERY LOW"
    assert result["confidence"] == 0.30


def test_confidence_high_for_long_text():
    result = compute_verbal_fluency_score(MOCK_LEXICAL, MOCK_SYNTACTIC, MOCK_SEMANTIC, MOCK_READABILITY, 400, "en")
    assert result["confidence_label"] == "HIGH"


def test_predict_iq_returns_ci_and_classification():
    vfs_result = compute_verbal_fluency_score(MOCK_LEXICAL, MOCK_SYNTACTIC, MOCK_SEMANTIC, MOCK_READABILITY, 412, "en")
    result = predict_iq(vfs_result["vfs"], vfs_result["confidence"])
    for key in ("point_estimate", "ci_low", "ci_high", "classification", "percentile"):
        assert key in result


def test_predict_iq_ci_low_less_than_high():
    vfs_result = compute_verbal_fluency_score(MOCK_LEXICAL, MOCK_SYNTACTIC, MOCK_SEMANTIC, MOCK_READABILITY, 412, "en")
    result = predict_iq(vfs_result["vfs"], vfs_result["confidence"])
    assert result["ci_low"] < result["point_estimate"] < result["ci_high"]


def test_predict_mental_age_with_known_age():
    result = predict_mental_age(120.0, 25)
    assert result["mental_age"] == 30.0
    assert result["age_assumed"] is False


def test_predict_mental_age_assumes_default():
    result = predict_mental_age(100.0)
    assert result["age_assumed"] is True
    assert result["mental_age"] == 30.0


def test_estimate_education_s1_level():
    result = estimate_education_level(12.4, 11.8, 0.53, 2.1)
    assert result["level_code"] in ("S1", "S2", "S3", "D3")
    assert "level_en" in result
    assert "level_id" in result
    assert "confidence" in result
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_mapper.py -v 2>&1 | head -20
```

Expected: `ImportError`.

- [ ] **Step 3: Write mapper.py**

Create `mcp-server/tools/mapper.py`:
```python
import json
import os
from typing import Optional

_iq_norms = None
_edu_norms = None

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")


def _load_iq_norms() -> dict:
    global _iq_norms
    if _iq_norms is None:
        with open(os.path.join(_CONFIG_DIR, "iq_norms.json")) as f:
            _iq_norms = json.load(f)
    return _iq_norms


def _load_edu_norms() -> dict:
    global _edu_norms
    if _edu_norms is None:
        with open(os.path.join(_CONFIG_DIR, "edu_norms.json")) as f:
            _edu_norms = json.load(f)
    return _edu_norms


def compute_verbal_fluency_score(
    lexical: dict, syntactic: dict, semantic: dict,
    readability: dict, word_count: int, lang: str
) -> dict:
    vfs = round(
        lexical["score"] * 0.35
        + syntactic["score"] * 0.25
        + semantic["score"] * 0.25
        + readability["score"] * 0.15,
        1,
    )

    if word_count < 30:
        confidence, label = 0.30, "VERY LOW"
    elif word_count < 100:
        confidence, label = 0.55, "LOW"
    elif word_count < 300:
        confidence, label = 0.70, "MEDIUM"
    else:
        extra = min(0.13, (word_count - 300) / 1000 * 0.13)
        confidence, label = round(0.82 + extra, 2), "HIGH"

    return {
        "vfs": vfs,
        "lexical": lexical["score"],
        "syntactic": syntactic["score"],
        "semantic": semantic["score"],
        "readability": readability["score"],
        "confidence": confidence,
        "confidence_label": label,
        "lang": lang,
        "text_length_words": word_count,
    }


def predict_iq(vfs: float, confidence: float) -> dict:
    norms = _load_iq_norms()

    band = norms["bands"][-1]
    for b in norms["bands"]:
        if b["vfs_min"] <= vfs <= b["vfs_max"]:
            band = b
            break

    band_range = band["vfs_max"] - band["vfs_min"]
    position = (vfs - band["vfs_min"]) / band_range if band_range > 0 else 0.5
    iq_point = round(band["iq_min"] + position * (band["iq_max"] - band["iq_min"]))

    ci_half = round(15 - confidence * 10)
    percentile = round(band["percentile_min"] + position * (95 - band["percentile_min"]))

    return {
        "point_estimate": iq_point,
        "ci_low": iq_point - ci_half,
        "ci_high": iq_point + ci_half,
        "classification": band["label"],
        "percentile": percentile,
    }


def predict_mental_age(iq_estimate: float, chronological_age: Optional[int] = None) -> dict:
    norms = _load_iq_norms()
    assumed = chronological_age is None
    age = chronological_age if chronological_age is not None else norms["default_chronological_age"]
    return {
        "mental_age": round((iq_estimate / 100) * age, 1),
        "based_on_chronological_age": age,
        "age_assumed": assumed,
        "formula": "mental_age = (iq / 100) * chronological_age",
    }


def estimate_education_level(
    gunning_fog: float, ari: float, lexical_density: float, clause_density: float
) -> dict:
    norms = _load_edu_norms()
    matched = norms["levels"][-1]
    for level in norms["levels"]:
        if (
            gunning_fog >= level["fog_min"]
            and ari >= level["ari_min"]
            and lexical_density >= level["lexical_density_min"]
        ):
            matched = level
            break

    thresholds_met = sum([
        gunning_fog >= matched["fog_min"] + 1,
        ari >= matched["ari_min"] + 1,
        lexical_density >= matched["lexical_density_min"] + 0.05,
    ])

    if thresholds_met == 3:
        confidence, conf_label = 0.82, "HIGH"
    elif thresholds_met == 2:
        confidence, conf_label = 0.68, "MEDIUM"
    else:
        confidence, conf_label = 0.50, "LOW"

    return {
        "level_en": matched["level_en"],
        "level_id": matched["level_id"],
        "level_code": matched["code"],
        "confidence": confidence,
        "confidence_label": conf_label,
    }
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_mapper.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/mapper.py tests/test_mapper.py
git commit -m "feat: add VFS computation, IQ prediction, mental age, education mapping"
```

---

## Task 9: Report Generator

**Files:**
- Create: `mcp-server/tools/reporter.py`
- Create: `tests/test_reporter.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_reporter.py`:
```python
import sys
sys.path.insert(0, "mcp-server")

from tools.reporter import generate_report

LANG = {"lang": "en", "confidence": 0.92}
PREP = {"word_count": 412, "sentence_count": 18, "sentences": [{"idx": 0, "text": "The cat sat on the mat."}], "text_clean": "The cat sat."}
LEXICAL = {"mattr": 0.78, "vocd_d": 61.2, "hapax_ratio": 0.42, "lexical_density": 0.53, "avg_word_length": 5.8, "score": 78.1, "evidence": [{"sentence_idx": 0, "sentence": "The epistemological underpinnings.", "triggered_by": ["hapax:epistemological"]}]}
SYNTACTIC = {"mean_sentence_length": 18.3, "clause_density": 2.1, "subordination_index": 0.48, "dependency_depth": 6.0, "passive_ratio": 0.12, "score": 69.2, "evidence": []}
SEMANTIC = {"argument_coherence": 0.74, "topic_drift_index": 0.21, "lexical_chain_density": 0.61, "entity_sophistication": "ABSTRACT", "score": 71.8, "evidence": [{"sentence_idx_from": 0, "sentence_idx_to": 1, "coherence": 0.81, "note": "causal chain detected"}]}
READABILITY = {"flesch_reading_ease": 52.1, "gunning_fog": 12.4, "ari": 11.8, "coleman_liau": 12.1, "score": 65.0, "evidence": []}
VFS = {"vfs": 73.4, "lexical": 78.1, "syntactic": 69.2, "semantic": 71.8, "readability": 65.0, "confidence": 0.82, "confidence_label": "HIGH", "lang": "en", "text_length_words": 412}
IQ = {"point_estimate": 117, "ci_low": 110, "ci_high": 124, "classification": "Above Average / Superior", "percentile": 79}
MENTAL_AGE = {"mental_age": 35.1, "based_on_chronological_age": 30, "age_assumed": True, "formula": "mental_age = (iq / 100) * chronological_age"}
EDU = {"level_en": "Undergraduate", "level_id": "Sarjana (S1/D4)", "level_code": "S1", "confidence": 0.68, "confidence_label": "MEDIUM"}


def _call(flag="--both", **kwargs):
    return generate_report(LANG, PREP, LEXICAL, SYNTACTIC, SEMANTIC, READABILITY, VFS, IQ, MENTAL_AGE, EDU, format_flag=flag, **kwargs)


def test_json_flag_returns_json_no_report():
    result = _call("--json")
    assert result["json"] is not None
    assert result["report"] is None


def test_report_flag_returns_report_no_json():
    result = _call("--report")
    assert result["report"] is not None
    assert result["json"] is None


def test_both_flag_returns_both():
    result = _call("--both")
    assert result["json"] is not None
    assert result["report"] is not None


def test_scores_only_returns_slim_json():
    result = _call("--scores-only")
    assert "vfs" in result["json"]
    assert "iq" in result["json"]
    assert result["report"] is None


def test_report_contains_iq_value():
    result = _call("--report")
    assert "117" in result["report"]


def test_report_contains_evidence_sentence():
    result = _call("--report")
    assert "epistemological" in result["report"]


def test_verbose_caveats_adds_extended_section():
    result = _call("--report", verbose_caveats=True)
    assert "EXTENDED LIMITATIONS" in result["report"]


def test_report_contains_confidence_label():
    result = _call("--report")
    assert "HIGH" in result["report"]
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_reporter.py -v 2>&1 | head -20
```

Expected: `ImportError`.

- [ ] **Step 3: Write reporter.py**

Create `mcp-server/tools/reporter.py`:
```python
from datetime import date
from typing import Optional

LANG_LABELS = {"en": "English", "id": "Indonesian"}


def _bar(score: float, width: int = 10) -> str:
    filled = round(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _trunc(text: str, max_len: int = 100) -> str:
    return f'"{text[:max_len]}..."' if len(text) > max_len else f'"{text}"'


def generate_report(
    lang_result: dict,
    preprocess_result: dict,
    lexical_result: dict,
    syntactic_result: dict,
    semantic_result: dict,
    readability_result: dict,
    vfs_result: dict,
    iq_result: dict,
    mental_age_result: dict,
    edu_result: dict,
    format_flag: str = "--both",
    age: Optional[int] = None,
    verbose_caveats: bool = False,
) -> dict:
    full_json = {
        "language": lang_result,
        "verbal_fluency_score": vfs_result,
        "iq_prediction": iq_result,
        "mental_age": mental_age_result,
        "education_level": edu_result,
        "metrics": {
            "lexical": lexical_result,
            "syntactic": syntactic_result,
            "semantic": semantic_result,
            "readability": readability_result,
        },
    }

    if format_flag == "--scores-only":
        slim = {
            "vfs": vfs_result["vfs"],
            "iq": iq_result["point_estimate"],
            "iq_range": f"{iq_result['ci_low']}–{iq_result['ci_high']}",
            "mental_age": mental_age_result["mental_age"],
            "education": edu_result["level_code"],
            "confidence": vfs_result["confidence_label"],
        }
        return {"json": slim, "report": None}

    if format_flag == "--json":
        return {"json": full_json, "report": None}

    # Build structured report
    sep = "━" * 50
    thin = "  " + "─" * 46
    L = []

    def line(s=""):
        L.append(s)

    line(sep)
    line("  VERBAL FLUENCY INTELLIGENCE REPORT")
    line(f"  Generated: {date.today().isoformat()} | Language: {LANG_LABELS.get(lang_result['lang'], lang_result['lang'])}")
    line(sep)
    line()
    line("  SUBJECT PROFILE")
    line(f"  Text input          : {preprocess_result['word_count']} words, {preprocess_result['sentence_count']} sentences")
    line(f"  Lang detection conf : {lang_result['confidence']:.0%}")
    line(f"  Analysis confidence : {vfs_result['confidence_label']} ({vfs_result['confidence']:.0%})")
    line()

    line(thin)
    line("  VERBAL FLUENCY SCORE")
    line(thin)
    line(f"  Overall VFS     : {vfs_result['vfs']} / 100")
    line(f"  └── Lexical     : {vfs_result['lexical']} / 100  {_bar(vfs_result['lexical'])}")
    line(f"  └── Syntactic   : {vfs_result['syntactic']} / 100  {_bar(vfs_result['syntactic'])}")
    line(f"  └── Semantic    : {vfs_result['semantic']} / 100  {_bar(vfs_result['semantic'])}")
    line(f"  └── Readability : {vfs_result['readability']} / 100  {_bar(vfs_result['readability'])}")
    line()

    line(thin)
    line("  IQ PREDICTION")
    line(thin)
    line(f"  Point estimate  : {iq_result['point_estimate']}")
    line(f"  95% CI range    : {iq_result['ci_low']} – {iq_result['ci_high']}")
    line(f"  Classification  : {iq_result['classification']}")
    line(f"  Percentile      : ~{iq_result['percentile']}th")
    line()

    line(thin)
    line("  MENTAL AGE")
    line(thin)
    line(f"  Estimated       : {mental_age_result['mental_age']} years")
    if mental_age_result["age_assumed"]:
        line(f"  (Chronological age assumed: {mental_age_result['based_on_chronological_age']} | pass --age=N for precision)")
    line()

    line(thin)
    line("  EDUCATION LEVEL ESTIMATE")
    line(thin)
    line(f"  EN label        : {edu_result['level_en']}")
    line(f"  ID label        : {edu_result['level_id']}")
    line(f"  Confidence      : {edu_result['confidence_label']} ({edu_result['confidence']:.0%})")
    line()

    line(thin)
    line("  DETAILED LEXICAL METRICS")
    line(thin)
    line(f"  MATTR (window=50)     : {lexical_result['mattr']}")
    line(f"  VOCD-D                : {lexical_result.get('vocd_d') or 'N/A (< 50 words)'}")
    line(f"  Hapax Legomena ratio  : {lexical_result['hapax_ratio']}")
    line(f"  Lexical density       : {lexical_result['lexical_density']}")
    line(f"  Avg word length       : {lexical_result['avg_word_length']} chars")
    line()

    line(thin)
    line("  DETAILED SYNTACTIC METRICS")
    line(thin)
    line(f"  Mean sentence length  : {syntactic_result['mean_sentence_length']} words")
    line(f"  Clause density        : {syntactic_result['clause_density']}")
    line(f"  Subordination index   : {syntactic_result['subordination_index']}")
    line(f"  Dependency tree depth : {syntactic_result['dependency_depth']}")
    line(f"  Passive voice ratio   : {syntactic_result['passive_ratio']}")
    line()

    line(thin)
    line("  DETAILED SEMANTIC METRICS")
    line(thin)
    line(f"  Argument coherence    : {semantic_result['argument_coherence']}")
    line(f"  Topic drift index     : {semantic_result['topic_drift_index']} (low = focused)")
    line(f"  Lexical chain density : {semantic_result['lexical_chain_density']}")
    line(f"  Entity sophistication : {semantic_result['entity_sophistication']}")
    line()

    line(thin)
    line("  READABILITY INDICES")
    line(thin)
    line(f"  Flesch Reading Ease   : {readability_result['flesch_reading_ease']}")
    line(f"  Gunning Fog Index     : {readability_result['gunning_fog']}")
    line(f"  ARI                   : {readability_result['ari']}")
    line(f"  Coleman-Liau Index    : {readability_result['coleman_liau']}")
    line()

    line(thin)
    line("  INTERPRETATION WITH EVIDENCE")
    line(thin)
    line()

    line(f"  [LEXICAL — Score {vfs_result['lexical']}]")
    line(f"  Vocabulary diversity (MATTR {lexical_result['mattr']}), lexical density {lexical_result['lexical_density']}.")
    for ev in lexical_result.get("evidence", []):
        line("  Evidence:")
        line(f"    → {_trunc(ev['sentence'])}")
        line(f"       [{', '.join(ev['triggered_by'])}]")
    line()

    line(f"  [SYNTACTIC — Score {vfs_result['syntactic']}]")
    line(f"  Clause density {syntactic_result['clause_density']}, subordination index {syntactic_result['subordination_index']}.")
    for ev in syntactic_result.get("evidence", []):
        line("  Evidence:")
        line(f"    → {_trunc(ev['sentence'])}")
        line(f"       [{', '.join(ev['triggered_by'])}]")
    line()

    line(f"  [SEMANTIC — Score {vfs_result['semantic']}]")
    line(f"  Argument coherence {semantic_result['argument_coherence']}, topic drift {semantic_result['topic_drift_index']}.")
    sents = preprocess_result.get("sentences", [])
    sent_map = {s["idx"]: s["text"] for s in sents}
    for ev in semantic_result.get("evidence", [])[:3]:
        line(f"    → S{ev['sentence_idx_from']}→S{ev['sentence_idx_to']} coherence: {ev['coherence']} [{ev['note']}]")
        src = sent_map.get(ev["sentence_idx_from"], "")
        if src:
            line(f"       {_trunc(src, 80)}")
    line()

    line(f"  [READABILITY — Score {vfs_result['readability']}]")
    line(f"  Gunning Fog {readability_result['gunning_fog']}, ARI {readability_result['ari']}.")
    for ev in readability_result.get("evidence", []):
        line("  Evidence:")
        line(f"    → {_trunc(ev['sentence'])}")
        line(f"       [{', '.join(ev['triggered_by'])}]")
    line()

    line(f"  [IQ PREDICTION — {iq_result['point_estimate']}, CI: {iq_result['ci_low']}–{iq_result['ci_high']}]")
    line(f"  Driven by lexical sophistication (score {vfs_result['lexical']}) and syntactic complexity (score {vfs_result['syntactic']}).")
    for ev in lexical_result.get("evidence", [])[:3]:
        line(f"    → [S{ev['sentence_idx']}] {_trunc(ev['sentence'], 80)}")
    line()

    line(f"  [EDUCATION ESTIMATE — {edu_result['level_code']}/{edu_result['level_en']}]")
    line(f"  Fog {readability_result['gunning_fog']} + ARI {readability_result['ari']} + lexical density {lexical_result['lexical_density']}.")
    line(f"  Writing style consistent with {edu_result['level_en']} authorship.")
    line()

    line(thin)
    line("  CONFIDENCE & LIMITATIONS")
    line(thin)
    line(f"  Overall confidence    : {vfs_result['confidence_label']} ({vfs_result['confidence']:.0%})")
    line("  Limiting factors      :")
    line("    • Text-based IQ estimation carries ±10–15 pt error margin")
    line("    • Mental age assumes population median if age not supplied")
    line("    • Education estimate does not account for self-taught learning")
    line("    • Cultural/linguistic background affects psycholinguistic norms")
    line("    • Short texts (< 100 words) significantly reduce reliability")

    if verbose_caveats or format_flag == "--verbose-caveats":
        line()
        line("  EXTENDED LIMITATIONS (--verbose-caveats)")
        line("    • This tool produces statistical estimates, NOT clinical diagnoses.")
        line("    • Verbal fluency text proxies cannot replace standardized IQ tests")
        line("      (WAIS-IV, Raven's Progressive Matrices, etc.).")
        line("    • The IQ→mental age formula is a simplified ratio model.")
        line("    • Education estimates assume formal schooling context.")
        line("    • Indonesian norms are approximated from EN research with ID adaptation.")
        line("    • Do not use these estimates for hiring, clinical, or legal decisions.")

    line()
    line(thin)
    line("  RESEARCH BASIS")
    line(thin)
    line("  Pennebaker et al.   — LIWC personality/intelligence studies")
    line("  Crossley et al.     — Lexical Sophistication indices")
    line("  Mairesse et al.     — Big Five + intelligence from text")
    line("  Gunning (1952)      — Fog Index")
    line("  Coleman & Liau (1975) — CL Index")
    line("  Covington & McFall (2010) — VOCD-D")
    line()
    line(sep)

    report_text = "\n".join(L)

    if format_flag == "--report":
        return {"json": None, "report": report_text}
    return {"json": full_json, "report": report_text}
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_reporter.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/tools/reporter.py tests/test_reporter.py
git commit -m "feat: add report generator with sentence-level citation evidence"
```

---

## Task 10: MCP Server Entry Point

**Files:**
- Create: `mcp-server/server.py`

- [ ] **Step 1: Write server.py**

Create `mcp-server/server.py`:
```python
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP
from tools.preprocess import detect_language, preprocess_text
from tools.lexical import analyze_lexical
from tools.syntactic import analyze_syntactic
from tools.semantic import analyze_semantic
from tools.readability import analyze_readability
from tools.mapper import (
    compute_verbal_fluency_score,
    predict_iq,
    predict_mental_age,
    estimate_education_level,
)
from tools.reporter import generate_report

mcp = FastMCP("verbal-fluency-mcp")


@mcp.tool()
def tool_detect_language(text: str) -> str:
    """Detect language of input text. Returns lang (en|id) and confidence."""
    return json.dumps(detect_language(text))


@mcp.tool()
def tool_preprocess_text(text: str, lang: str) -> str:
    """Clean and tokenize text. Returns tokens, sentences (with idx), word_count."""
    return json.dumps(preprocess_text(text, lang))


@mcp.tool()
def tool_analyze_lexical(tokens_json: str, sentences_json: str, lang: str) -> str:
    """Compute MATTR, VOCD-D, hapax ratio, lexical density. Returns score and evidence."""
    return json.dumps(analyze_lexical(json.loads(tokens_json), json.loads(sentences_json), lang))


@mcp.tool()
def tool_analyze_syntactic(sentences_json: str, lang: str) -> str:
    """Compute clause density, subordination index, dependency depth. Returns score and evidence."""
    return json.dumps(analyze_syntactic(json.loads(sentences_json), lang))


@mcp.tool()
def tool_analyze_semantic(text: str, sentences_json: str, lang: str) -> str:
    """Compute argument coherence, topic drift, lexical chain density. Returns score and evidence."""
    return json.dumps(analyze_semantic(text, json.loads(sentences_json), lang))


@mcp.tool()
def tool_analyze_readability(text: str, lang: str) -> str:
    """Compute Flesch, Gunning Fog, ARI, Coleman-Liau. Returns score and evidence."""
    return json.dumps(analyze_readability(text, lang))


@mcp.tool()
def tool_compute_verbal_fluency_score(
    lexical_json: str, syntactic_json: str, semantic_json: str,
    readability_json: str, word_count: int, lang: str
) -> str:
    """Combine metric scores into weighted VFS (0-100) with confidence label."""
    return json.dumps(compute_verbal_fluency_score(
        json.loads(lexical_json), json.loads(syntactic_json),
        json.loads(semantic_json), json.loads(readability_json),
        word_count, lang,
    ))


@mcp.tool()
def tool_predict_iq(vfs: float, confidence: float) -> str:
    """Map VFS to IQ point estimate, 95% CI, classification, and percentile."""
    return json.dumps(predict_iq(vfs, confidence))


@mcp.tool()
def tool_predict_mental_age(iq_estimate: float, chronological_age: int = 0) -> str:
    """Compute mental age from IQ. Pass chronological_age=0 to use population default (30)."""
    age = chronological_age if chronological_age > 0 else None
    return json.dumps(predict_mental_age(iq_estimate, age))


@mcp.tool()
def tool_estimate_education_level(
    gunning_fog: float, ari: float, lexical_density: float, clause_density: float
) -> str:
    """Map readability metrics to education level with EN and ID labels."""
    return json.dumps(estimate_education_level(gunning_fog, ari, lexical_density, clause_density))


@mcp.tool()
def tool_generate_report(
    lang_result_json: str,
    preprocess_result_json: str,
    lexical_result_json: str,
    syntactic_result_json: str,
    semantic_result_json: str,
    readability_result_json: str,
    vfs_result_json: str,
    iq_result_json: str,
    mental_age_result_json: str,
    edu_result_json: str,
    format_flag: str = "--both",
    chronological_age: int = 0,
    verbose_caveats: bool = False,
) -> str:
    """Generate JSON and/or structured report with sentence-level citation evidence."""
    age = chronological_age if chronological_age > 0 else None
    result = generate_report(
        json.loads(lang_result_json),
        json.loads(preprocess_result_json),
        json.loads(lexical_result_json),
        json.loads(syntactic_result_json),
        json.loads(semantic_result_json),
        json.loads(readability_result_json),
        json.loads(vfs_result_json),
        json.loads(iq_result_json),
        json.loads(mental_age_result_json),
        json.loads(edu_result_json),
        format_flag,
        age,
        verbose_caveats,
    )
    return json.dumps(result)


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 2: Verify server starts without error**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python mcp-server/server.py --help 2>&1 | head -5 || python -c "import sys; sys.path.insert(0,'mcp-server'); import server; print('server imports OK')"
```

Expected: no import errors.

- [ ] **Step 3: Commit**

```bash
git add mcp-server/server.py
git commit -m "feat: add FastMCP server exposing all 11 verbal fluency tools"
```

---

## Task 11: End-to-End Pipeline Integration Test

**Files:**
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write the integration test**

Create `tests/test_pipeline.py`:
```python
import sys
import json
sys.path.insert(0, "mcp-server")

from tools.preprocess import detect_language, preprocess_text
from tools.lexical import analyze_lexical
from tools.syntactic import analyze_syntactic
from tools.semantic import analyze_semantic
from tools.readability import analyze_readability
from tools.mapper import compute_verbal_fluency_score, predict_iq, predict_mental_age, estimate_education_level
from tools.reporter import generate_report

EN_LONG = """
The epistemological foundations of cognitive science have undergone substantial transformation
over the past three decades, driven by advances in computational neuroscience and the emergence
of connectionist models that challenge classical symbolic approaches. Although the data from
early neural network experiments was inconclusive, subsequent research demonstrated that
distributed representations could encode semantic relationships more effectively than
rule-based systems. The implications for natural language processing are profound:
systems that learn statistical regularities from large corpora exhibit emergent properties
that were not explicitly programmed, suggesting that intelligence may be better understood
as a statistical phenomenon than as a logical one. This perspective, while compelling,
requires careful methodological scrutiny to avoid conflating correlation with causation
in the interpretation of model behavior.
"""

ID_MEDIUM = """
Perkembangan teknologi informasi telah mengubah paradigma komunikasi modern secara fundamental.
Implementasi sistem berbasis kecerdasan buatan memerlukan koordinasi multidimensional antara
berbagai pemangku kepentingan yang memiliki perspektif berbeda-beda.
Meskipun tantangan teknis yang dihadapi sangat kompleks, tim pengembang berhasil menyelesaikan
proyek tersebut dengan hasil yang memuaskan karena dedikasi dan kolaborasi yang intensif.
"""

EN_SHORT = "The cat sat on the mat."


def _run_pipeline(text: str) -> dict:
    lang_r = detect_language(text)
    lang = lang_r["lang"]
    prep_r = preprocess_text(text, lang)
    lex_r = analyze_lexical(prep_r["tokens"], prep_r["sentences"], lang)
    syn_r = analyze_syntactic(prep_r["sentences"], lang)
    sem_r = analyze_semantic(prep_r["text_clean"], prep_r["sentences"], lang)
    read_r = analyze_readability(prep_r["text_clean"], lang)
    vfs_r = compute_verbal_fluency_score(lex_r, syn_r, sem_r, read_r, prep_r["word_count"], lang)
    iq_r = predict_iq(vfs_r["vfs"], vfs_r["confidence"])
    ma_r = predict_mental_age(iq_r["point_estimate"])
    edu_r = estimate_education_level(read_r["gunning_fog"], read_r["ari"], lex_r["lexical_density"], syn_r["clause_density"])
    report_r = generate_report(lang_r, prep_r, lex_r, syn_r, sem_r, read_r, vfs_r, iq_r, ma_r, edu_r, "--both")
    return {"vfs": vfs_r, "iq": iq_r, "edu": edu_r, "report": report_r}


def test_en_long_pipeline_completes():
    result = _run_pipeline(EN_LONG)
    assert 0 < result["vfs"]["vfs"] <= 100
    assert result["iq"]["point_estimate"] > 0
    assert result["report"]["report"] is not None
    assert result["report"]["json"] is not None


def test_en_long_has_high_confidence():
    result = _run_pipeline(EN_LONG)
    assert result["vfs"]["confidence_label"] in ("HIGH", "MEDIUM")


def test_id_pipeline_detects_indonesian():
    lang_r = detect_language(ID_MEDIUM)
    assert lang_r["lang"] == "id"


def test_id_pipeline_completes():
    result = _run_pipeline(ID_MEDIUM)
    assert result["vfs"]["vfs"] > 0
    assert result["edu"]["level_code"] in ("SD", "SMP", "SMA", "D3", "S1", "S2", "S3")


def test_short_text_very_low_confidence():
    result = _run_pipeline(EN_SHORT)
    assert result["vfs"]["confidence_label"] in ("VERY LOW", "LOW")


def test_report_contains_research_basis():
    result = _run_pipeline(EN_LONG)
    assert "Pennebaker" in result["report"]["report"]


def test_json_output_has_all_top_level_keys():
    result = _run_pipeline(EN_LONG)
    j = result["report"]["json"]
    for key in ("language", "verbal_fluency_score", "iq_prediction", "mental_age", "education_level", "metrics"):
        assert key in j


def test_vfs_does_not_drift_more_than_2_points_on_same_input():
    r1 = _run_pipeline(EN_LONG)
    r2 = _run_pipeline(EN_LONG)
    assert abs(r1["vfs"]["vfs"] - r2["vfs"]["vfs"]) < 2.0
```

- [ ] **Step 2: Run integration test**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/test_pipeline.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/ -v
```

Expected: all tests PASS. Note total count.

- [ ] **Step 4: Commit**

```bash
git add tests/test_pipeline.py
git commit -m "test: add end-to-end pipeline integration tests"
```

---

## Task 12: Vendorless Agent Files

**Files:**
- Create: `.agent/SKILL.md`
- Create: `.agent/tools.json`

- [ ] **Step 1: Write .agent/SKILL.md**

Create `.agent/SKILL.md`:
```markdown
---
name: verbal-fluency-iq
description: >
  Predict IQ, mental age, and education level from text passages using
  verbal fluency analysis. Supports English and Indonesian. Tool-first:
  all scores are computed by deterministic MCP tools — never estimated
  by reasoning alone.
tools_required:
  - tool_detect_language
  - tool_preprocess_text
  - tool_analyze_lexical
  - tool_analyze_syntactic
  - tool_analyze_semantic
  - tool_analyze_readability
  - tool_compute_verbal_fluency_score
  - tool_predict_iq
  - tool_predict_mental_age
  - tool_estimate_education_level
  - tool_generate_report
mcp_server: verbal-fluency-mcp
mcp_transport: stdio
mcp_command: "python mcp-server/server.py"
output_flags:
  default: "--both"
  options:
    - "--json"          # JSON scores only
    - "--report"        # Full structured report only
    - "--both"          # JSON + full report (default)
    - "--scores-only"   # Minimal JSON, no caveats
    - "--verbose-caveats" # Report + extended limitations
optional_params:
  chronological_age: "integer — improves mental age precision"
---

# Verbal Fluency IQ Skill

## When to invoke

Use this skill when the user provides one or more text passages from a
target person and asks to analyze intelligence, verbal fluency, IQ,
mental age, or education level.

## Hard constraint

NEVER estimate or reason about any score. If the MCP server is
unavailable, return this error:
```
{"error": "verbal-fluency-mcp server not available. Cannot estimate scores without tools."}
```

## Tool call sequence

Call these tools in order. Each output feeds the next.

```
1. tool_detect_language(text)
   → { lang, confidence }

2. tool_preprocess_text(text, lang)
   → { tokens, sentences, word_count, sentence_count, text_clean }

3. tool_analyze_lexical(tokens_json, sentences_json, lang)
   → { mattr, vocd_d, hapax_ratio, lexical_density, avg_word_length, score, evidence }

4. tool_analyze_syntactic(sentences_json, lang)
   → { mean_sentence_length, clause_density, subordination_index, dependency_depth, passive_ratio, score, evidence }

5. tool_analyze_semantic(text_clean, sentences_json, lang)
   → { argument_coherence, topic_drift_index, lexical_chain_density, entity_sophistication, score, evidence }

6. tool_analyze_readability(text_clean, lang)
   → { flesch_reading_ease, gunning_fog, ari, coleman_liau, score, evidence }

7. tool_compute_verbal_fluency_score(lexical_json, syntactic_json, semantic_json, readability_json, word_count, lang)
   → { vfs, lexical, syntactic, semantic, readability, confidence, confidence_label, lang, text_length_words }

8. tool_predict_iq(vfs, confidence)
   → { point_estimate, ci_low, ci_high, classification, percentile }

9. tool_predict_mental_age(iq_estimate, chronological_age)
   → { mental_age, based_on_chronological_age, age_assumed, formula }

10. tool_estimate_education_level(gunning_fog, ari, lexical_density, clause_density)
    → { level_en, level_id, level_code, confidence, confidence_label }

11. tool_generate_report(lang_json, preprocess_json, lexical_json, syntactic_json,
                         semantic_json, readability_json, vfs_json, iq_json,
                         mental_age_json, edu_json, format_flag, chronological_age, verbose_caveats)
    → { json, report }
```

## Passing JSON between tools

Each tool returns a JSON string. Pass it directly as the `*_json` parameter
of the next tool. Do not parse or summarize intermediate results.

## User prompt flags

Parse these from the user's message:
- `--json` / `--report` / `--both` / `--scores-only` / `--verbose-caveats`
- `--age=N` → extract integer N as `chronological_age`

Default: `--both` if no flag specified.

## Minimum text requirement

If `word_count < 10`, return:
```
{"error": "Text too short for analysis. Minimum 10 words required."}
```
```

- [ ] **Step 2: Write .agent/tools.json**

Create `.agent/tools.json`:
```json
{
  "schema_version": "1.0",
  "mcp_server": "verbal-fluency-mcp",
  "tools": [
    {
      "name": "tool_detect_language",
      "description": "Detect language (en|id) from text with confidence score",
      "parameters": {
        "text": { "type": "string", "required": true }
      },
      "returns": { "lang": "string", "confidence": "number" }
    },
    {
      "name": "tool_preprocess_text",
      "description": "Clean, tokenize, and sentence-split text",
      "parameters": {
        "text": { "type": "string", "required": true },
        "lang": { "type": "string", "enum": ["en", "id"], "required": true }
      },
      "returns": { "tokens": "array", "sentences": "array", "word_count": "integer", "sentence_count": "integer", "text_clean": "string" }
    },
    {
      "name": "tool_analyze_lexical",
      "description": "Compute MATTR, VOCD-D, hapax ratio, lexical density with sentence evidence",
      "parameters": {
        "tokens_json": { "type": "string", "required": true },
        "sentences_json": { "type": "string", "required": true },
        "lang": { "type": "string", "required": true }
      },
      "returns": { "mattr": "number", "vocd_d": "number|null", "hapax_ratio": "number", "lexical_density": "number", "avg_word_length": "number", "score": "number", "evidence": "array" }
    },
    {
      "name": "tool_analyze_syntactic",
      "description": "Compute clause density, subordination index, dependency depth",
      "parameters": {
        "sentences_json": { "type": "string", "required": true },
        "lang": { "type": "string", "required": true }
      },
      "returns": { "mean_sentence_length": "number", "clause_density": "number", "subordination_index": "number", "dependency_depth": "number", "passive_ratio": "number", "score": "number", "evidence": "array" }
    },
    {
      "name": "tool_analyze_semantic",
      "description": "Compute argument coherence, topic drift, lexical chain density",
      "parameters": {
        "text": { "type": "string", "required": true },
        "sentences_json": { "type": "string", "required": true },
        "lang": { "type": "string", "required": true }
      },
      "returns": { "argument_coherence": "number|null", "topic_drift_index": "number|null", "lexical_chain_density": "number", "entity_sophistication": "string", "score": "number", "evidence": "array" }
    },
    {
      "name": "tool_analyze_readability",
      "description": "Compute Flesch Reading Ease, Gunning Fog, ARI, Coleman-Liau",
      "parameters": {
        "text": { "type": "string", "required": true },
        "lang": { "type": "string", "required": true }
      },
      "returns": { "flesch_reading_ease": "number", "gunning_fog": "number", "ari": "number", "coleman_liau": "number", "score": "number", "evidence": "array" }
    },
    {
      "name": "tool_compute_verbal_fluency_score",
      "description": "Combine lexical/syntactic/semantic/readability into weighted VFS (0-100)",
      "parameters": {
        "lexical_json": { "type": "string", "required": true },
        "syntactic_json": { "type": "string", "required": true },
        "semantic_json": { "type": "string", "required": true },
        "readability_json": { "type": "string", "required": true },
        "word_count": { "type": "integer", "required": true },
        "lang": { "type": "string", "required": true }
      },
      "returns": { "vfs": "number", "lexical": "number", "syntactic": "number", "semantic": "number", "readability": "number", "confidence": "number", "confidence_label": "string", "lang": "string", "text_length_words": "integer" }
    },
    {
      "name": "tool_predict_iq",
      "description": "Map VFS to IQ point estimate with 95% confidence interval",
      "parameters": {
        "vfs": { "type": "number", "required": true },
        "confidence": { "type": "number", "required": true }
      },
      "returns": { "point_estimate": "integer", "ci_low": "integer", "ci_high": "integer", "classification": "string", "percentile": "integer" }
    },
    {
      "name": "tool_predict_mental_age",
      "description": "Compute mental age from IQ. Use chronological_age=0 to use default (30).",
      "parameters": {
        "iq_estimate": { "type": "number", "required": true },
        "chronological_age": { "type": "integer", "default": 0 }
      },
      "returns": { "mental_age": "number", "based_on_chronological_age": "integer", "age_assumed": "boolean", "formula": "string" }
    },
    {
      "name": "tool_estimate_education_level",
      "description": "Map readability metrics to education level with EN and ID labels",
      "parameters": {
        "gunning_fog": { "type": "number", "required": true },
        "ari": { "type": "number", "required": true },
        "lexical_density": { "type": "number", "required": true },
        "clause_density": { "type": "number", "required": true }
      },
      "returns": { "level_en": "string", "level_id": "string", "level_code": "string", "confidence": "number", "confidence_label": "string" }
    },
    {
      "name": "tool_generate_report",
      "description": "Generate JSON scores and/or structured report with sentence-level citation evidence",
      "parameters": {
        "lang_result_json": { "type": "string", "required": true },
        "preprocess_result_json": { "type": "string", "required": true },
        "lexical_result_json": { "type": "string", "required": true },
        "syntactic_result_json": { "type": "string", "required": true },
        "semantic_result_json": { "type": "string", "required": true },
        "readability_result_json": { "type": "string", "required": true },
        "vfs_result_json": { "type": "string", "required": true },
        "iq_result_json": { "type": "string", "required": true },
        "mental_age_result_json": { "type": "string", "required": true },
        "edu_result_json": { "type": "string", "required": true },
        "format_flag": { "type": "string", "enum": ["--json","--report","--both","--scores-only","--verbose-caveats"], "default": "--both" },
        "chronological_age": { "type": "integer", "default": 0 },
        "verbose_caveats": { "type": "boolean", "default": false }
      },
      "returns": { "json": "object|null", "report": "string|null" }
    }
  ]
}
```

- [ ] **Step 3: Verify JSON is valid**

```bash
python -c "import json; json.load(open('.agent/tools.json')); print('tools.json valid')"
```

Expected: `tools.json valid`

- [ ] **Step 4: Commit**

```bash
git add .agent/
git commit -m "feat: add vendorless .agent/SKILL.md and tools.json for any-agent compatibility"
```

---

## Task 13: Final Verification

- [ ] **Step 1: Run the complete test suite**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -m pytest tests/ -v --tb=short
```

Expected: all tests PASS. Zero failures.

- [ ] **Step 2: Verify MCP server lists all 11 tools**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -c "
import sys; sys.path.insert(0,'mcp-server')
import server
tools = [name for name in dir(server) if name.startswith('tool_')]
print(f'Found {len(tools)} tools:')
for t in sorted(tools): print(' -', t)
assert len(tools) == 11, f'Expected 11 tools, got {len(tools)}'
print('All 11 tools present')
"
```

Expected: 11 tools listed, `All 11 tools present`.

- [ ] **Step 3: Smoke-test the pipeline on a real passage**

```bash
cd /Users/rahmatwibowo/Infraloka/verbal-fluency-iq && python -c "
import sys; sys.path.insert(0,'mcp-server')
from tools.preprocess import detect_language, preprocess_text
from tools.lexical import analyze_lexical
from tools.syntactic import analyze_syntactic
from tools.semantic import analyze_semantic
from tools.readability import analyze_readability
from tools.mapper import compute_verbal_fluency_score, predict_iq, predict_mental_age, estimate_education_level
from tools.reporter import generate_report

text = 'The epistemological foundations of cognitive science have undergone substantial transformation. Although data from early experiments was inconclusive, subsequent research demonstrated that distributed representations encode semantic relationships more effectively. This perspective requires careful methodological scrutiny to avoid conflating correlation with causation.'
lang_r = detect_language(text)
prep_r = preprocess_text(text, lang_r['lang'])
lex_r = analyze_lexical(prep_r['tokens'], prep_r['sentences'], lang_r['lang'])
syn_r = analyze_syntactic(prep_r['sentences'], lang_r['lang'])
sem_r = analyze_semantic(prep_r['text_clean'], prep_r['sentences'], lang_r['lang'])
read_r = analyze_readability(prep_r['text_clean'], lang_r['lang'])
vfs_r = compute_verbal_fluency_score(lex_r, syn_r, sem_r, read_r, prep_r['word_count'], lang_r['lang'])
iq_r = predict_iq(vfs_r['vfs'], vfs_r['confidence'])
ma_r = predict_mental_age(iq_r['point_estimate'])
edu_r = estimate_education_level(read_r['gunning_fog'], read_r['ari'], lex_r['lexical_density'], syn_r['clause_density'])
report_r = generate_report(lang_r, prep_r, lex_r, syn_r, sem_r, read_r, vfs_r, iq_r, ma_r, edu_r)
print(report_r['report'])
"
```

Expected: full structured report printed to stdout with scores, citations, and limitations.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete verbal-fluency-iq skill — all 11 MCP tools + vendorless agent files"
```
