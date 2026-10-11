# Copyright (c) 2026 InfraLoka. All rights reserved. Proprietary and confidential.
"""Syntactic complexity.

English uses spaCy dependency labels; Indonesian uses a rule-based lexicon and
morphology (xx_ent_wiki_sm has no parser). These are different instruments, so
syntactic scores are NOT comparable across languages (F-023): every result
carries ``comparable_across_languages: False`` and cross-language ranking is
refused by ``tools.policy.assert_same_language``.
"""

import re
from functools import lru_cache

from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

from tools import models
from tools.evidence import rank_evidence
from tools.policy import require_supported_language

SUBORDINATE_DEPS = {"advcl", "relcl", "acl", "csubj", "ccomp", "xcomp"}
CLAUSE_DEPS = SUBORDINATE_DEPS | {"ROOT"}

NON_COMPARABLE_NOTE = (
    "Syntactic scores come from different instruments per language and are not "
    "comparable across languages."
)

# --- Indonesian rule-based resources ---
# Konjungsi subordinatif: always open a subordinate clause.
ID_SUBORDINATORS = {
    "yang",
    "karena",
    "sehingga",
    "ketika",
    "meskipun",
    "walaupun",
    "jika",
    "kalau",
    "agar",
    "supaya",
    "sebab",
    "bahwa",
    "apabila",
    "bilamana",
    "seandainya",
    "andai",
    "tatkala",
    "seraya",
    "sambil",
    "sementara",
    "asalkan",
    "kecuali",
    "biarpun",
    "sekalipun",
    "daripada",
    "seolah",
    "seakan",
}
# Temporal words that are prepositions ("sejak pagi") unless a predicate follows
# ("sejak dia pindah"). Counted as subordinators only in the clausal sense (F-011).
ID_TEMPORAL_JOINERS = {"sejak", "selama", "sampai", "hingga", "sebelum", "setelah"}
# Coordinators that also join nouns and verb phrases ("nasi dan teh", "makan dan
# minum"). Counted as clause joiners only before an overt subject + predicate.
ID_GATED_COORDINATORS = {"dan", "atau", "serta"}
# Coordinators that join clauses in standard usage.
ID_CLAUSE_COORDINATORS = {
    "tetapi",
    "namun",
    "melainkan",
    "sedangkan",
    "lalu",
    "kemudian",
    "padahal",
    "maka",
}
ID_JOINERS = (
    ID_SUBORDINATORS
    | ID_TEMPORAL_JOINERS
    | ID_GATED_COORDINATORS
    | ID_CLAUSE_COORDINATORS
)
# Colloquial / Javanese-influenced connectives -> standard form, applied before
# counting so informal writers are not penalised for register (F-018).
ID_COLLOQUIAL_TO_STANDARD = {
    "kalo": "kalau",
    "biar": "agar",
    "soalnya": "karena",
    "makanya": "maka",
    "pas": "ketika",
    "gara-gara": "karena",
    "nek": "kalau",
    "ben": "agar",
    "trus": "lalu",
    "terus": "lalu",
    "tapi": "tetapi",
}
# di- + one of these roots is a locative/relative written solid ("dimana",
# "diantara", "diatas"), not a passive verb (F-010).
ID_FUNCTION_ROOTS = frozenset(
    {
        "mana",
        "antara",
        "sini",
        "situ",
        "sana",
        "atas",
        "bawah",
        "dalam",
        "luar",
        "depan",
        "belakang",
    }
)
# Place nouns commonly written solid after locative "di" in informal writing.
ID_LOCATIVE_NOUN_ROOTS = frozenset(
    {
        "rumah",
        "kantor",
        "sekolah",
        "kampus",
        "kelas",
        "kamar",
        "dapur",
        "jalan",
        "pasar",
        "toko",
        "kota",
        "desa",
        "kampung",
        "sawah",
        "kebun",
        "pantai",
        "laut",
        "gunung",
        "hutan",
    }
)
# Unaffixed verbs that head a predicate (the affixed ones are found by morphology).
ID_BARE_VERBS = frozenset(
    {
        "makan",
        "minum",
        "pergi",
        "datang",
        "pulang",
        "tidur",
        "duduk",
        "turun",
        "naik",
        "masuk",
        "keluar",
        "tiba",
        "lahir",
        "mati",
        "tinggal",
        "bangun",
        "lari",
        "jatuh",
        "ikut",
        "pindah",
        "mandi",
        "kerja",
        "main",
        "tahu",
        "pakai",
        "beli",
        "jual",
        "bayar",
        "baca",
        "tulis",
        "lihat",
        "dengar",
        "buat",
        "bawa",
        "cari",
        "kirim",
        "tunggu",
        "selesai",
        "mulai",
        "hilang",
        "muncul",
        "menang",
        "kalah",
    }
)
# Adverbs/auxiliaries that open a predicate without a subject ("dan tidak minum").
ID_PREDICATE_MODIFIERS = frozenset(
    {
        "tidak",
        "tak",
        "belum",
        "bukan",
        "sudah",
        "telah",
        "akan",
        "sedang",
        "masih",
        "juga",
        "pun",
        "hanya",
        "bisa",
        "dapat",
        "harus",
        "mau",
        "ingin",
        "boleh",
        "perlu",
        "langsung",
        "segera",
        "pernah",
        "sering",
        "selalu",
    }
)
# Affixed words that are prepositions/determiners, not predicates.
ID_NON_VERB_AFFIXED = frozenset(
    {
        "terhadap",
        "tersebut",
        "terdapat",
        "terutama",
        "termasuk",
        "terakhir",
        "terlalu",
        "tertentu",
        "bersama",
        "berbagai",
        "berdasarkan",
        "beberapa",
        "berupa",
    }
)
_VERB_PREFIX_RE = re.compile(r"^(meng|meny|mem|men|me|ber|be|di|ter)")
_PASSIVE_SUFFIXES = ("kan", "i")
_MIN_ROOT_LEN = 4


@lru_cache(maxsize=1)
def _sastrawi():
    """(root dictionary, stemmer) from PySastrawi's bundled kata-dasar list."""
    factory = StemmerFactory()
    roots = frozenset(w for w in factory.get_words_from_file() if w)
    return roots, factory.create_stemmer()


def normalise_colloquial(words: list[str]) -> tuple[list[str], int]:
    """Map colloquial connectives to standard forms; return (words, n_changed)."""
    out, changed = [], 0
    for w in words:
        standard = ID_COLLOQUIAL_TO_STANDARD.get(w)
        if standard is None:
            out.append(w)
        else:
            out.append(standard)
            changed += 1
    return out, changed


def is_di_passive(word: str) -> bool:
    """di- + a dictionary root (optionally + -kan/-i), excluding function roots.

    A bare di- + place noun ("dirumah", "dikantor") is the locative preposition
    written solid, so it is not passive; with a suffix ("dirumahkan",
    "dijalankan") it is. ter- is deliberately NOT treated as passive: most ter-
    words are adjectives, superlatives or stative forms (terjadi, terkait,
    terbaik).
    """
    if not word.startswith("di") or len(word) < 2 + _MIN_ROOT_LEN:
        return False
    roots, _ = _sastrawi()
    rest = word[2:]
    if rest in ID_FUNCTION_ROOTS or rest in ID_LOCATIVE_NOUN_ROOTS:
        return False
    candidates = [rest] + [
        rest[: -len(s)] for s in _PASSIVE_SUFFIXES if rest.endswith(s)
    ]
    return any(
        len(c) >= _MIN_ROOT_LEN and c in roots and c not in ID_FUNCTION_ROOTS
        for c in candidates
    )


@lru_cache(maxsize=65536)
def is_verb_like(word: str) -> bool:
    """Bare verb from ID_BARE_VERBS, or me-/ber-/di-/ter- on a dictionary root."""
    if word in ID_BARE_VERBS:
        return True
    if word in ID_JOINERS or word in ID_NON_VERB_AFFIXED:
        return False
    if not _VERB_PREFIX_RE.match(word):
        return False
    if word.startswith("di"):
        return is_di_passive(word)
    roots, stemmer = _sastrawi()
    root = stemmer.stem(word)
    return (
        root != word
        and len(root) >= 3
        and root in roots
        and root not in ID_FUNCTION_ROOTS
    )


def _segment_after(words: list[str], i: int) -> list[str]:
    segment = []
    for w in words[i + 1 :]:
        if w in ID_JOINERS:
            break
        segment.append(w)
    return segment


def _opens_clause(segment: list[str], require_subject: bool) -> bool:
    if not segment:
        return False
    if not require_subject:
        return any(is_verb_like(w) for w in segment)
    head = segment[0]
    if is_verb_like(head) or head in ID_PREDICATE_MODIFIERS:
        return False  # shared subject: predicate coordination inside one clause
    return any(is_verb_like(w) for w in segment[1:])


def count_id_clause_joiners(words: list[str]) -> tuple[int, int]:
    """Return (subordinators, coordinators) that actually join clauses."""
    subs = coords = 0
    for i, w in enumerate(words):
        if w in ID_SUBORDINATORS:
            subs += 1
        elif w in ID_CLAUSE_COORDINATORS:
            coords += 1
        elif w in ID_TEMPORAL_JOINERS:
            subs += _opens_clause(_segment_after(words, i), require_subject=False)
        elif w in ID_GATED_COORDINATORS:
            coords += _opens_clause(_segment_after(words, i), require_subject=True)
    return subs, coords


def _dep_depth(token) -> int:
    depth = 0
    seen = set()
    while token.head != token and id(token) not in seen:
        seen.add(id(token))
        token = token.head
        depth += 1
    return depth


def _analyze_syntactic_id(sentences: list[dict]) -> dict:
    """Parser-free Indonesian syntactic analysis.

    Dependency depth is not measurable without a parser, so it is reported as
    None (not 0) and excluded from the weighted score, with the remaining
    weights renormalised.
    """
    lengths, clause_counts, sub_counts = [], [], []
    passive_count = 0
    colloquial_total = 0
    evidence = []

    for sent_data in sentences:
        words = [w for w in sent_data["text"].split() if any(c.isalpha() for c in w)]
        lengths.append(len(words))
        lower = [re.sub(r"[^a-z\-]", "", w.lower()) for w in words]
        lower, n_colloquial = normalise_colloquial(lower)
        colloquial_total += n_colloquial

        subs, coords = count_id_clause_joiners(lower)
        sub_counts.append(subs)
        clause_counts.append(1 + subs + coords)

        passives = [w for w in lower if is_di_passive(w)]
        is_passive = bool(passives)
        if is_passive:
            passive_count += 1

        triggered = [f"clauses:{1 + subs + coords}"]
        if subs >= 1:
            triggered.append(f"subordinators:{subs}")
        if is_passive:
            triggered.append(f"passive:{passives[0]}")
        evidence.append(
            {
                "sentence_idx": sent_data["idx"],
                "sentence": sent_data["text"],
                "triggered_by": triggered,
                "contribution": float(1 + subs + coords),
            }
        )

    n = len(sentences) or 1
    msl = round(sum(lengths) / n, 1)
    clause_density = round(sum(clause_counts) / n, 2)
    sub_index = round(sum(sub_counts) / n, 3)
    passive_ratio = round(passive_count / n, 3)

    msl_score = min(100.0, max(0.0, (msl - 8) / 22 * 100))
    cd_score = min(100.0, max(0.0, (clause_density - 1.0) / 2.5 * 100))
    si_score = min(100.0, max(0.0, sub_index / 1.5 * 100))
    # Dependency depth (10% weight) is unmeasurable for id -> drop it and
    # renormalise the remaining 0.30/0.35/0.25 weights (sum 0.90) to 1.0.
    score = round(
        msl_score * (0.30 / 0.90) + cd_score * (0.35 / 0.90) + si_score * (0.25 / 0.90),
        1,
    )

    return {
        "mean_sentence_length": msl,
        "clause_density": clause_density,
        "subordination_index": sub_index,
        "dependency_depth": None,  # honest: not measurable without a parser
        "passive_ratio": passive_ratio,
        "colloquial_forms_normalised": colloquial_total,
        "comparable_across_languages": False,
        "score": score,
        "evidence": rank_evidence(evidence),
        "note": (
            "Indonesian syntactic metrics computed via rule-based morphology; "
            "dependency depth not measured (no parser for id). " + NON_COMPARABLE_NOTE
        ),
    }


def analyze_syntactic(sentences: list[dict], lang: str) -> dict:
    require_supported_language(lang)
    if lang == "id":
        return _analyze_syntactic_id(sentences)

    nlp = models.get_spacy(lang)
    lengths, clause_counts, sub_counts, dep_depths = [], [], [], []
    passive_count = 0
    evidence = []

    # One batched pass over all sentences instead of one nlp() call each (G-027).
    docs = nlp.pipe([s["text"] for s in sentences], batch_size=64)
    for sent_data, doc in zip(sentences, docs, strict=True):
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

        triggered = [f"clauses:{max(1, clauses)}"]
        if subs >= 1:
            triggered.append(f"subordinate_clauses:{subs}")
        if max_depth >= 6:
            triggered.append(f"dep_depth:{max_depth}")
        if is_passive:
            triggered.append("passive_voice")
        evidence.append(
            {
                "sentence_idx": sent_data["idx"],
                "sentence": sent_data["text"],
                "triggered_by": triggered,
                # Clauses first, depth as the tie-breaker.
                "contribution": float(max(1, clauses)) + max_depth / 100,
            }
        )

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

    score = round(
        msl_score * 0.30 + cd_score * 0.35 + si_score * 0.25 + dd_score * 0.10, 1
    )

    return {
        "mean_sentence_length": msl,
        "clause_density": clause_density,
        "subordination_index": sub_index,
        "dependency_depth": dep_depth,
        "passive_ratio": passive_ratio,
        "comparable_across_languages": False,
        "score": score,
        "evidence": rank_evidence(evidence),
        "note": NON_COMPARABLE_NOTE,
    }
