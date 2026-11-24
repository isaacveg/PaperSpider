# Copyright 2026 Isaacveg
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0

"""Turn LaTeX fragments found in paper titles into readable plain text."""

from __future__ import annotations

import re
import unicodedata

_GREEK = {
    name: chr(code)
    for name, code in (
        ("alpha", 0x3B1), ("beta", 0x3B2), ("gamma", 0x3B3), ("delta", 0x3B4),
        ("epsilon", 0x3B5), ("varepsilon", 0x3B5), ("zeta", 0x3B6), ("eta", 0x3B7),
        ("theta", 0x3B8), ("vartheta", 0x3D1), ("iota", 0x3B9), ("kappa", 0x3BA),
        ("lambda", 0x3BB), ("mu", 0x3BC), ("nu", 0x3BD), ("xi", 0x3BE),
        ("pi", 0x3C0), ("rho", 0x3C1), ("sigma", 0x3C3), ("tau", 0x3C4),
        ("upsilon", 0x3C5), ("phi", 0x3C6), ("varphi", 0x3C6), ("chi", 0x3C7),
        ("psi", 0x3C8), ("omega", 0x3C9), ("Gamma", 0x393), ("Delta", 0x394),
        ("Theta", 0x398), ("Lambda", 0x39B), ("Xi", 0x39E), ("Pi", 0x3A0),
        ("Sigma", 0x3A3), ("Phi", 0x3A6), ("Psi", 0x3A8), ("Omega", 0x3A9),
    )
}
_SYMBOLS = {
    "nabla": "∇", "infty": "∞", "times": "×", "cdot": "·", "pm": "±",
    "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "neq": "≠", "approx": "≈",
    "sim": "∼", "rightarrow": "→", "to": "→", "leftarrow": "←", "ell": "ℓ",
    "partial": "∂", "sum": "Σ", "prod": "∏", "sqrt": "√", "star": "⋆",
    "circ": "∘", "in": "∈", "forall": "∀", "exists": "∃", "dagger": "†",
    "ldots": "…", "dots": "…", "cdots": "⋯", "prime": "′", "LaTeX": "LaTeX",
    "natural": "♮", "sharp": "♯", "flat": "♭", "log": "log", "exp": "exp",
}
_STYLE_COMMANDS = (
    "textit", "textbf", "texttt", "textsc", "textrm", "textsf", "text", "emph",
    "mathbf", "mathrm", "mathit", "mathsf", "mathtt", "mathcal", "mathbb",
    "mathfrak", "boldsymbol", "bm", "operatorname", "mbox", "hat", "tilde",
    "bar", "vec", "widehat", "widetilde", "overline", "underline",
)
_ACCENTS = {
    '"': "\u0308", "'": "\u0301", "`": "\u0300", "^": "\u0302",
    "~": "\u0303", "c": "\u0327", "v": "\u030c", "=": "\u0304", ".": "\u0307",
}
_SUPERSCRIPT = str.maketrans(
    "0123456789+-=()abcdefghijklmnoprstuvwxyzABDEGHIJKLMNOPRTUVW∘",
    "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵀᵁⱽᵂ°",
)
_SUBSCRIPT = str.maketrans("0123456789+-=()aeoxhklmnpst", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜ")

_ACCENT_RE = re.compile(r"\\([\"'`^~=.])\s*\{?([A-Za-z])\}?|\\([cv])\{([A-Za-z])\}")
_STYLE_RE = re.compile(r"\\(?:%s)\s*\{([^{}]*)\}" % "|".join(_STYLE_COMMANDS))
_STYLE_NAME_RE = re.compile(r"\\(?:%s)(?![A-Za-z])\s*" % "|".join(_STYLE_COMMANDS))
_BRACED = r"\{((?:[^{}]|\{[^{}]*\})*)\}"
_FRAC_RE = re.compile(r"\\[dt]?frac\s*" + _BRACED + r"\s*" + _BRACED)
_SQRT_RE = re.compile(r"√\{([^{}]*)\}")
_MATH_RE = re.compile(r"\$([^$]+)\$")
_SCRIPT_RE = re.compile(r"([\^_])(\{[^{}]*\}|[^\s{}$^_])")
_REPLACEMENTS = {**_GREEK, **_SYMBOLS}
_KNOWN_RE = re.compile(
    r"\\(%s)(?![A-Za-z])" % "|".join(sorted(_REPLACEMENTS, key=len, reverse=True))
)
_COMMAND_RE = re.compile(r"\\([A-Za-z]+)")
_ESCAPE_RE = re.compile(r"\\([%&_#$])")


def _accent(match: re.Match) -> str:
    mark, letter = (match.group(1), match.group(2)) if match.group(1) else (
        match.group(3),
        match.group(4),
    )
    return unicodedata.normalize("NFC", letter + _ACCENTS[mark])


def _script(match: re.Match) -> str:
    content = match.group(2).strip("{}")
    table = _SUPERSCRIPT if match.group(1) == "^" else _SUBSCRIPT
    if content and all(ord(ch) in table for ch in content):
        return content.translate(table)
    if match.group(1) == "_":
        return content
    return f"^{content}" if len(content) == 1 else f"^({content})"


def display_title(text: str) -> str:
    """Return ``text`` with common LaTeX markup rendered as plain Unicode."""

    if not text or ("\\" not in text and "$" not in text):
        return text or ""
    result = text.replace("\\\\", " ").replace("\\(", "$").replace("\\)", "$")
    result = _ACCENT_RE.sub(_accent, result)
    result = _KNOWN_RE.sub(lambda m: _REPLACEMENTS[m.group(1)], result)
    previous = None
    while previous != result:
        previous = result
        result = _STYLE_RE.sub(r"\1", result)
        result = _FRAC_RE.sub(r"\1/\2", result)
        result = _SQRT_RE.sub(r"√\1", result)
    result = _STYLE_NAME_RE.sub("", result).replace("{}", "")
    result = _MATH_RE.sub(lambda m: _SCRIPT_RE.sub(_script, m.group(1)), result)
    result = _ESCAPE_RE.sub(r"\1", result)
    result = _COMMAND_RE.sub(r"\1", result)
    result = result.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", result).strip()
