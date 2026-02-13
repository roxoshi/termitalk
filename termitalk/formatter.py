"""Text formatter: converts spoken phrases to CLI symbols and cleans output."""

import os
import re
import logging
from pathlib import Path
logger = logging.getLogger(__name__)

# CLI term corrections — applied before phrase mapping
# Each entry: (compiled regex pattern, replacement)
CLI_CORRECTIONS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bpseudo\b", re.IGNORECASE), "sudo"),
    (re.compile(r"\bsue do\b", re.IGNORECASE), "sudo"),
    (re.compile(r"\bcube control\b", re.IGNORECASE), "kubectl"),
    (re.compile(r"\bkube control\b", re.IGNORECASE), "kubectl"),
    (re.compile(r"\bengine x\b", re.IGNORECASE), "nginx"),
    (re.compile(r"\bch mod\b", re.IGNORECASE), "chmod"),
    (re.compile(r"\bch own\b", re.IGNORECASE), "chown"),
    (re.compile(r"\blocal host\b", re.IGNORECASE), "localhost"),
    (re.compile(r"\bdev null\b", re.IGNORECASE), "/dev/null"),
    (re.compile(r"\bsystem control\b", re.IGNORECASE), "systemctl"),
    (re.compile(r"\bjournal control\b", re.IGNORECASE), "journalctl"),
    (re.compile(r"\bx args\b", re.IGNORECASE), "xargs"),
    (re.compile(r"\bstandard out\b", re.IGNORECASE), "stdout"),
    (re.compile(r"\bstandard in\b", re.IGNORECASE), "stdin"),
    (re.compile(r"\bstandard error\b", re.IGNORECASE), "stderr"),
    (re.compile(r"\bdot env\b", re.IGNORECASE), ".env"),
    (re.compile(r"\bdot git ignore\b", re.IGNORECASE), ".gitignore"),
    (re.compile(r"\bread me\b", re.IGNORECASE), "README"),
    (re.compile(r"\bmake file\b", re.IGNORECASE), "Makefile"),
    (re.compile(r"\bdocker file\b", re.IGNORECASE), "Dockerfile"),
]

# Digit words for spoken number conversion
_DIGIT_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
}

# Direct phrase-map entries for common port/permission patterns
_NUMBER_PHRASES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\beight zero eight zero\b", re.IGNORECASE), "8080"),
    (re.compile(r"\bthree thousand\b", re.IGNORECASE), "3000"),
    (re.compile(r"\bfour four three\b", re.IGNORECASE), "443"),
    (re.compile(r"\bseven five five\b", re.IGNORECASE), "755"),
    (re.compile(r"\bsix four four\b", re.IGNORECASE), "644"),
]

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


def _convert_spoken_numbers(text: str) -> str:
    """Convert consecutive digit-words to digits.

    Single digit-words are left as English. Two or more consecutive
    digit-words are converted to their numeric form.  "dot"/"period"
    within a digit sequence becomes "." (for IPs/versions).

    Examples:
        "one two seven dot zero dot zero dot one" → "127.0.0.1"
        "port eight zero eight zero" → "port 8080"
        "five" → "five" (single digit-word left as-is)
    """
    # First apply direct number phrase shortcuts
    for pattern, replacement in _NUMBER_PHRASES:
        text = pattern.sub(replacement, text)

    tokens = text.split()
    result: list[str] = []
    i = 0

    while i < len(tokens):
        lower = tokens[i].lower()
        if lower not in _DIGIT_WORDS:
            result.append(tokens[i])
            i += 1
            continue

        # Start accumulating digit-words
        group: list[str] = [_DIGIT_WORDS[lower]]
        j = i + 1
        while j < len(tokens):
            t = tokens[j].lower()
            if t in _DIGIT_WORDS:
                group.append(_DIGIT_WORDS[t])
                j += 1
            elif t in ("dot", "period") and j + 1 < len(tokens) and tokens[j + 1].lower() in _DIGIT_WORDS:
                group.append(".")
                j += 1
            else:
                break

        if len(group) >= 2:
            # Two or more digit-words → emit as digits
            result.append("".join(group))
        else:
            # Single digit-word → leave as English
            result.append(tokens[i])

        i = j

    return " ".join(result)


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

    # Lowercase everything — proper names (README, Makefile) restored via CLI corrections
    text = text.lower()

    # Strip trailing punctuation, wrapping quotes, and Whisper-inserted commas
    text = text.rstrip(".,!?;:")
    text = text.strip("\"'")
    text = text.replace(", ", " ")

    # Remove filler words (case-insensitive, whole words only)
    for filler in FILLERS:
        pattern = r"\b" + re.escape(filler.rstrip(",")) + r",?\b"
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Clean up extra whitespace from filler removal
    text = re.sub(r"\s+", " ", text).strip()

    # Apply CLI term corrections (e.g., "pseudo" → "sudo")
    for pattern, replacement in CLI_CORRECTIONS:
        text = pattern.sub(replacement, text)

    # Convert spoken numbers to digits (e.g., "one two seven" → "127")
    text = _convert_spoken_numbers(text)

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
