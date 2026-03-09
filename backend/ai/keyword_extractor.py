"""
keyword_extractor.py – Extract meaningful keywords from text using spaCy.

Falls back to a simple regex-based extractor if spaCy or its model
is not available (e.g. during first-time setup).

Returns a deduplicated list of lowercase keyword strings.
"""

import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  Lazy-load spaCy model
# ──────────────────────────────────────────────
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            from backend.config import settings
            _nlp = spacy.load(settings.spacy_model)
            logger.info(f"spaCy model '{settings.spacy_model}' loaded.")
        except Exception as exc:
            logger.warning(f"Could not load spaCy model ({exc}). Using regex fallback.")
            _nlp = False  # sentinel: fallback mode
    return _nlp


# ──────────────────────────────────────────────
#  Stop words (supplement spaCy's built-in list)
# ──────────────────────────────────────────────
EXTRA_STOP_WORDS = {
    "like", "just", "also", "get", "got", "let", "make", "made",
    "say", "said", "way", "go", "going", "know", "think", "really",
    "even", "back", "right", "ve", "ll", "re", "don", "didn",
    "isn", "wasn", "aren", "haven", "wouldn", "couldn", "shouldn",
}


def _regex_extract(text: str, top_n: int = 8) -> List[str]:
    """
    Simple regex-based keyword extractor.

    Keeps nouns/long words, removes common short stop-words.
    """
    # Tokenise: keep only alphabetic tokens ≥ 4 chars
    tokens = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for tok in tokens:
        if tok not in seen and tok not in EXTRA_STOP_WORDS:
            seen.add(tok)
            unique.append(tok)

    # Return top N by original order (first-seen heuristic)
    return unique[:top_n]


def extract_keywords(text: str, top_n: int = 8) -> List[str]:
    """
    Extract the most relevant keywords from a transcript segment.

    Parameters
    ----------
    text : str
        Raw transcript text.
    top_n : int
        Maximum number of keywords to return.

    Returns
    -------
    List of lowercase keyword strings.
    """
    if not text.strip():
        return []

    nlp = _get_nlp()

    if not nlp:
        # spaCy unavailable – use regex fallback
        return _regex_extract(text, top_n)

    doc = nlp(text)

    keywords = []
    for token in doc:
        if (
            not token.is_stop
            and not token.is_punct
            and not token.is_space
            and token.is_alpha
            and len(token.text) >= 3
            # Keep nouns, proper nouns, adjectives, verbs (content words)
            and token.pos_ in {"NOUN", "PROPN", "ADJ", "VERB"}
            and token.lemma_.lower() not in EXTRA_STOP_WORDS
        ):
            keywords.append(token.lemma_.lower())

    # Also extract named entities (people, orgs, places, etc.)
    for ent in doc.ents:
        ent_text = ent.text.lower().strip()
        if ent_text not in keywords and len(ent_text) >= 3:
            keywords.append(ent_text)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)

    return unique[:top_n]
