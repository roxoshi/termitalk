"""Text formatter: converts spoken phrases to CLI symbols and cleans output."""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CORRECTIONS_PATH = Path(os.environ.get(
    "TERMITALK_CORRECTIONS",
    Path.home() / ".config" / "termitalk" / "corrections.toml",
))

# Filler words to strip
FILLERS = {"um", "uh", "uh,", "um,", "like,", "you know,", "so,", "well,", "hmm", "er"}

# Multi-word mappings (checked first, order matters — longest phrases first)
PHRASE_MAP = [
    # Common compound symbols
    ("dot dot slash", "../"),
    ("dot slash", "./"),
    ("double dash", "--"),
    ("dot dot", ".."),
    ("dash help", "--help"),
    ("dash dash", "--"),
    ("open paren", "("),
    ("close paren", ")"),
    ("open parenthesis", "("),
    ("close parenthesis", ")"),
    ("open bracket", "["),
    ("close bracket", "]"),
    ("open brace", "{"),
    ("close brace", "}"),
    ("open curly", "{"),
    ("close curly", "}"),
    ("left paren", "("),
    ("right paren", ")"),
    ("left bracket", "["),
    ("right bracket", "]"),
    ("left brace", "{"),
    ("right brace", "}"),
    ("double quote", '"'),
    ("single quote", "'"),
    ("back tick", "`"),
    ("backtick", "`"),
    ("new line", "\n"),
    ("newline", "\n"),
    ("and sign", "&"),
    ("greater than or equal", ">="),
    ("less than or equal", "<="),
    ("not equal", "!="),
    ("double equal", "=="),
    ("greater than", ">"),
    ("less than", "<"),
    ("append to", ">>"),
    ("redirect to", ">"),
]

# Single-word mappings — value is (symbol, join_behavior)
# join_behavior:
#   "prefix"  — attach to next token (no space after): -, $, ~, #, @, +, \
#   "infix"   — attach to both neighbors (no space before or after): ., /, :
#   "keep"    — keep spaces around it: |, >, &
WORD_MAP = {
    "dash": ("-", "prefix"),
    "hyphen": ("-", "prefix"),
    "minus": ("-", "prefix"),
    "dot": (".", "infix"),
    "period": (".", "infix"),
    "slash": ("/", "infix"),
    "backslash": ("\\", "infix"),
    "pipe": ("|", "keep"),
    "tilde": ("~", "prefix"),
    "at": ("@", "infix"),
    "at sign": ("@", "infix"),
    "hash": ("#", "prefix"),
    "hashtag": ("#", "prefix"),
    "pound": ("#", "prefix"),
    "dollar": ("$", "prefix"),
    "dollar sign": ("$", "prefix"),
    "percent": ("%", "infix"),
    "caret": ("^", "prefix"),
    "ampersand": ("&", "keep"),
    "asterisk": ("*", "prefix"),
    "star": ("*", "prefix"),
    "underscore": ("_", "infix"),
    "equals": ("=", "infix"),
    "plus": ("+", "prefix"),
    "colon": (":", "infix"),
    "semicolon": (";", "keep"),
    "comma": (",", "keep"),
    "question mark": ("?", "keep"),
    "exclamation": ("!", "prefix"),
    "bang": ("!", "prefix"),
    "quote": ('"', "keep"),
    "tab": ("\t", "keep"),
    "space": (" ", "keep"),
    "enter": ("\n", "keep"),
}


# Tokens that are pure symbols and should act as prefixes
_SYMBOL_PREFIXES = {"--", "-", "../", "./", "..", "$", "~", "#", "@", "+", "!"}


def _classify_token(token: str) -> str:
    """Classify a non-mapped token's join behavior."""
    if token in _SYMBOL_PREFIXES:
        return "prefix"
    # Tokens that are purely symbols (no letters or digits) — treat as infix
    if token and not any(c.isalnum() for c in token):
        return "infix"
    return "word"


def load_user_corrections() -> int:
    """Load custom corrections from ~/.config/termitalk/corrections.toml.

    Merges user-defined phrase and symbol mappings into the formatter.
    Returns the number of corrections loaded.

    File format:
        [phrases]
        "my project" = "myproject"
        "kube control" = "kubectl"

        [symbols]
        "arrow" = "->"
        "fat arrow" = "=>"

        [replacements]
        "kubernetes" = "k8s"
    """
    if not _CORRECTIONS_PATH.exists():
        return 0

    try:
        import tomllib
    except ModuleNotFoundError:
        # Python < 3.11
        try:
            import tomli as tomllib
        except ModuleNotFoundError:
            logger.warning("Cannot load corrections: tomllib not available (Python 3.11+ required)")
            return 0

    try:
        with open(_CORRECTIONS_PATH, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        logger.warning("Failed to load corrections from %s: %s", _CORRECTIONS_PATH, e)
        return 0

    count = 0

    # Phrases: multi-word spoken → text replacement (inserted at the front of PHRASE_MAP)
    for spoken, replacement in data.get("phrases", {}).items():
        PHRASE_MAP.insert(0, (spoken.lower(), replacement))
        count += 1

    # Symbols: single-word spoken → symbol with "prefix" join behavior
    for spoken, symbol in data.get("symbols", {}).items():
        WORD_MAP[spoken.lower()] = (symbol, "prefix")
        count += 1

    # Replacements: simple text substitutions (added as phrase maps)
    for spoken, replacement in data.get("replacements", {}).items():
        PHRASE_MAP.insert(0, (spoken.lower(), replacement))
        count += 1

    if count > 0:
        logger.info("Loaded %d custom corrections from %s", count, _CORRECTIONS_PATH)

    return count


def format_text(text: str) -> str:
    """Convert spoken text to CLI-friendly formatted text.

    Applies phrase mappings, word mappings, and filler removal.
    """
    original = text
    text = text.strip()
    if not text:
        return ""

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove filler words (case-insensitive, whole words only)
    for filler in FILLERS:
        pattern = r"\b" + re.escape(filler.rstrip(",")) + r",?\b"
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Clean up extra whitespace from filler removal
    text = re.sub(r"\s+", " ", text).strip()

    # Apply multi-word phrase mappings first (longest match priority)
    for phrase, symbol in PHRASE_MAP:
        text = re.sub(
            r"\b" + re.escape(phrase) + r"\b",
            symbol,
            text,
            flags=re.IGNORECASE,
        )

    # Apply single-word mappings with join behavior tracking
    # Each output token is (text, join_behavior) where join_behavior indicates
    # how it should connect to the NEXT token
    tokens = text.split()
    mapped: list[tuple[str, str]] = []  # (text, join_behavior)

    for token in tokens:
        lower = token.lower().strip(".,!?;:")
        if lower in WORD_MAP:
            symbol, behavior = WORD_MAP[lower]
            mapped.append((symbol, behavior))
        else:
            # Detect symbol-only tokens from phrase map (e.g., "--", "../", "./")
            behavior = _classify_token(token)
            mapped.append((token, behavior))

    # Join tokens respecting join behaviors
    if not mapped:
        return ""

    parts = [mapped[0][0]]
    for i in range(1, len(mapped)):
        prev_text, prev_behavior = mapped[i - 1]
        curr_text, curr_behavior = mapped[i]

        # Decide whether to insert a space before current token
        if prev_behavior == "prefix":
            # Prefix symbols attach to next: no space
            pass
        elif curr_behavior == "infix":
            # Infix symbols attach to previous: no space
            pass
        elif prev_behavior == "infix":
            # After an infix symbol, attach to next: no space
            pass
        else:
            # Default: insert space
            parts.append(" ")

        parts.append(curr_text)

    text = "".join(parts)

    # Clean up multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    if text != original.strip():
        logger.debug("Formatted: %r → %r", original.strip(), text)

    return text
