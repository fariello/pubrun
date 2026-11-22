"""Pure standard-library PEP 508 requirement parser and marker evaluator.

Uses only the Python standard library and supports Python 3.8 through 3.14.
Unsupported or malformed marker syntax returns an explicit unknown result
(``matched=None`` with an ``error`` reason) rather than guessing or raising.
"""
from dataclasses import dataclass
import os
import platform
import re
import sys
from typing import Any, Dict, FrozenSet, List, Optional, Tuple, Union


# PEP 503 normalization pattern collapsing runs of '-', '_', and '.' to '-'.
_PEP503_RE = re.compile(r"[-_.]+")

# PEP 508 distribution and extra identifier grammar.
_NAME_PREFIX_RE = re.compile(r"^([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)")
_EXTRA_IDENT_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")

# Valid PEP 508 version-specifier start characters (after optional '(').
_VERSION_SPEC_START_RE = re.compile(r"^(?:===|==|!=|<=|>=|~=|<(?!<)|>(?!>))")

# Standard PEP 508 environment variables (excluding `extra`).
_STANDARD_ENV_VARS: FrozenSet[str] = frozenset(
    {
        "os_name",
        "sys_platform",
        "platform_machine",
        "platform_python_implementation",
        "platform_release",
        "platform_system",
        "platform_version",
        "python_version",
        "python_full_version",
        "implementation_name",
        "implementation_version",
    }
)

# Legacy PEP 508 dotted and short aliases mapped to canonical variable names.
_LEGACY_ENV_ALIASES: Dict[str, str] = {
    "os.name": "os_name",
    "sys.platform": "sys_platform",
    "platform.version": "platform_version",
    "platform.machine": "platform_machine",
    "platform.python_implementation": "platform_python_implementation",
    "python_implementation": "platform_python_implementation",
}

# Environment variables compared using PEP 440 version semantics.
_VERSION_VARS: FrozenSet[str] = frozenset(
    {
        "python_version",
        "python_full_version",
        "implementation_version",
    }
)

# PEP 440 version grammar (standard public versions without local segments).
_PEP440_VERSION_RE = re.compile(
    r"""
    ^\s*
    v?
    (?:(?P<epoch>[0-9]+)!)?
    (?P<release>[0-9]+(?:\.[0-9]+)*)
    (?P<pre>
        [-_.]?
        (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
        [-_.]?
        (?P<pre_n>[0-9]+)?
    )?
    (?P<post>
        (?:-(?P<post_n1>[0-9]+))
        |
        (?:[-_.]?(?P<post_l>post|rev|r)[-_. ]?(?P<post_n2>[0-9]+)?)
    )?
    (?P<dev>
        [-_.]?
        (?P<dev_l>dev)
        [-_.]?
        (?P<dev_n>[0-9]+)?
    )?
    \s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)

# PEP 440 prefix wildcard grammar (e.g. "3.11.*", "1!2.3.*").
_PEP440_PREFIX_RE = re.compile(
    r"^\s*v?(?:(?P<epoch>[0-9]+)!)?(?P<release>[0-9]+(?:\.[0-9]+)*)\.\*\s*$",
    re.IGNORECASE,
)

_PRE_TAG_MAP: Dict[str, int] = {
    "a": 0,
    "alpha": 0,
    "b": 1,
    "beta": 1,
    "c": 2,
    "rc": 2,
    "pre": 2,
    "preview": 2,
}

_MAX_PAREN_DEPTH = 64


class _NegInfType:
    """Sentinel sorting before every comparable value."""

    def __lt__(self, other: Any) -> bool:
        return not isinstance(other, _NegInfType)

    def __le__(self, other: Any) -> bool:
        return True

    def __gt__(self, other: Any) -> bool:
        return False

    def __ge__(self, other: Any) -> bool:
        return isinstance(other, _NegInfType)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, _NegInfType)


class _PosInfType:
    """Sentinel sorting after every comparable value."""

    def __lt__(self, other: Any) -> bool:
        return False

    def __le__(self, other: Any) -> bool:
        return isinstance(other, _PosInfType)

    def __gt__(self, other: Any) -> bool:
        return not isinstance(other, _PosInfType)

    def __ge__(self, other: Any) -> bool:
        return True

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, _PosInfType)


_NEG_INF = _NegInfType()
_POS_INF = _PosInfType()


@dataclass(frozen=True)
class ParsedRequirement:
    """Structured fields parsed from a PEP 508 requirement string."""

    name: str
    normalized_name: str
    extras: Tuple[str, ...]
    marker: Optional[str]
    raw: str


@dataclass(frozen=True)
class MarkerEvalResult:
    """Tri-state result of evaluating a PEP 508 environment marker.

    ``matched`` is ``True`` or ``False`` for valid markers, and ``None`` with a
    concise ``error`` string when syntax, variable names, or version literals
    are unsupported or malformed.
    """

    matched: Optional[bool]
    error: Optional[str] = None


@dataclass(frozen=True)
class _Pep440Version:
    """Parsed PEP 440 public version with release tuple and comparison key."""

    epoch: int
    release: Tuple[int, ...]
    cmp_key: Tuple[Any, ...]


def _normalize_name(name: str) -> str:
    """Return the PEP 503 normalized form of a distribution or extra name."""
    return _PEP503_RE.sub("-", name).lower()


def _format_full_version(info: Any) -> str:
    """Format ``sys.implementation.version`` per PEP 508."""
    version = f"{info.major}.{info.minor}.{info.micro}"
    kind = info.releaselevel
    if kind != "final":
        version += kind[0] + str(info.serial)
    return version


def default_marker_environment() -> Dict[str, str]:
    """Compute the active PEP 508 marker evaluation environment."""
    if hasattr(sys, "implementation"):
        impl_version = _format_full_version(sys.implementation.version)
        impl_name = sys.implementation.name
    else:
        impl_version = "0"
        impl_name = ""

    py_full = platform.python_version().split("+", 1)[0]
    py_short = ".".join(platform.python_version_tuple()[:2])

    return {
        "os_name": os.name,
        "sys_platform": sys.platform,
        "platform_machine": platform.machine(),
        "platform_python_implementation": platform.python_implementation(),
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "python_version": py_short,
        "python_full_version": py_full,
        "implementation_name": impl_name,
        "implementation_version": impl_version,
    }


def _find_unquoted_semicolon(text: str) -> int:
    """Return index of first unquoted ``;`` in ``text``, or -1 if absent."""
    quote_char: Optional[str] = None
    escaped = False
    for idx, ch in enumerate(text):
        if quote_char is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote_char:
                quote_char = None
        else:
            if ch in ("'", '"'):
                quote_char = ch
            elif ch == ";":
                return idx
    return -1


def _validate_version_spec_fragment(spec_part: str) -> bool:
    """Return True if a non-empty version specifier fragment is structurally sane."""
    inner = spec_part.strip()
    if not inner:
        return True

    if inner.startswith("("):
        depth = 0
        for idx, ch in enumerate(inner):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth < 0:
                    return False
                if depth == 0 and idx != len(inner) - 1:
                    return False
        if depth != 0:
            return False
        inner = inner[1:-1].strip()
        if not inner:
            return True

    # Must start with a valid PEP 440 specifier operator.
    return bool(_VERSION_SPEC_START_RE.match(inner))


def parse_requirement(req_str: str) -> Optional[ParsedRequirement]:
    """Parse a PEP 508 requirement string into name, normalized extras, and marker.

    Returns ``None`` for empty strings and for malformed requirement syntax
    (such as unclosed extras brackets, missing direct URLs, or empty trailing
    semicolons).
    """
    if not isinstance(req_str, str):
        return None
    text = req_str.strip()
    if not text:
        return None

    name_match = _NAME_PREFIX_RE.match(text)
    if not name_match:
        return None
    name = name_match.group(1)
    pos = name_match.end()

    # Reject dangling name characters (e.g. "foo-" or "foo$bar").
    if pos < len(text) and not text[pos].isspace() and text[pos] not in "[(@;!=<>~":
        return None

    while pos < len(text) and text[pos].isspace():
        pos += 1

    # Optional bracketed extras list: [extra1, extra2].
    extras_list: List[str] = []
    if pos < len(text) and text[pos] == "[":
        close_idx = text.find("]", pos + 1)
        if close_idx == -1:
            return None
        raw_extras = text[pos + 1 : close_idx].strip()
        if raw_extras:
            for item in raw_extras.split(","):
                part = item.strip()
                if not part or not _EXTRA_IDENT_RE.match(part):
                    return None
                norm_extra = _normalize_name(part)
                if norm_extra not in extras_list:
                    extras_list.append(norm_extra)
        pos = close_idx + 1
        while pos < len(text) and text[pos].isspace():
            pos += 1

    marker: Optional[str] = None
    if pos < len(text) and text[pos] == "@":
        # Direct URL requirement: @ <non-whitespace-URI> [ ; <marker> ]
        pos += 1
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text):
            return None
        url_start = pos
        while pos < len(text) and not text[pos].isspace():
            pos += 1
        url_token = text[url_start:pos]
        if not url_token or url_token.startswith(";"):
            return None
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos < len(text):
            if text[pos] != ";":
                return None
            marker_text = text[pos + 1 :].strip()
            if not marker_text:
                return None
            marker = marker_text
    elif pos < len(text):
        remainder = text[pos:]
        semi_idx = _find_unquoted_semicolon(remainder)
        if semi_idx != -1:
            spec_part = remainder[:semi_idx].strip()
            marker_text = remainder[semi_idx + 1 :].strip()
            if not marker_text:
                return None
            if spec_part and not _validate_version_spec_fragment(spec_part):
                return None
            marker = marker_text
        else:
            spec_part = remainder.strip()
            if spec_part and not _validate_version_spec_fragment(spec_part):
                return None

    return ParsedRequirement(
        name=name,
        normalized_name=_normalize_name(name),
        extras=tuple(extras_list),
        marker=marker,
        raw=req_str,
    )


def _parse_pep440_version(raw: str) -> Optional[_Pep440Version]:
    """Parse a standard PEP 440 version string into a comparable representation."""
    match = _PEP440_VERSION_RE.match(raw)
    if not match:
        return None

    epoch = int(match.group("epoch")) if match.group("epoch") is not None else 0
    release = tuple(int(part) for part in match.group("release").split("."))

    # Normalize trailing release zeros (e.g. 3.10.0 == 3.10).
    norm_list = list(release)
    while len(norm_list) > 1 and norm_list[-1] == 0:
        norm_list.pop()
    norm_release = tuple(norm_list)

    pre: Optional[Tuple[int, int]] = None
    if match.group("pre_l") is not None:
        pre_tag = _PRE_TAG_MAP[match.group("pre_l").lower()]
        pre_num = int(match.group("pre_n")) if match.group("pre_n") is not None else 0
        pre = (pre_tag, pre_num)

    post: Optional[int] = None
    if match.group("post_n1") is not None:
        post = int(match.group("post_n1"))
    elif match.group("post_l") is not None:
        post = int(match.group("post_n2")) if match.group("post_n2") is not None else 0

    dev: Optional[int] = None
    if match.group("dev_l") is not None:
        dev = int(match.group("dev_n")) if match.group("dev_n") is not None else 0

    if pre is None and post is None and dev is not None:
        pre_key: Any = _NEG_INF
    elif pre is None:
        pre_key = _POS_INF
    else:
        pre_key = pre

    post_key: Any = _NEG_INF if post is None else post
    dev_key: Any = _POS_INF if dev is None else dev

    return _Pep440Version(
        epoch=epoch,
        release=release,
        cmp_key=(epoch, norm_release, pre_key, post_key, dev_key),
    )


def _parse_pep440_prefix(raw: str) -> Optional[Tuple[int, Tuple[int, ...]]]:
    """Parse a PEP 440 ``.*`` prefix pattern into ``(epoch, prefix_release)``."""
    match = _PEP440_PREFIX_RE.match(raw)
    if not match:
        return None
    epoch = int(match.group("epoch")) if match.group("epoch") is not None else 0
    prefix = tuple(int(part) for part in match.group("release").split("."))
    return epoch, prefix


def _compare_versions(lhs: str, op: str, rhs: str) -> MarkerEvalResult:
    """Compare two version operands under PEP 508 / PEP 440 rules."""
    if op == "in":
        return MarkerEvalResult(matched=(lhs in rhs))
    if op == "not in":
        return MarkerEvalResult(matched=(lhs not in rhs))
    if op == "===":
        return MarkerEvalResult(matched=(lhs.lower() == rhs.lower()))

    lhs_stripped = lhs.strip()
    rhs_stripped = rhs.strip()
    lhs_is_prefix = lhs_stripped.endswith(".*")
    rhs_is_prefix = rhs_stripped.endswith(".*")

    if lhs_is_prefix or rhs_is_prefix:
        if op not in ("==", "!="):
            return MarkerEvalResult(
                matched=None,
                error=f"wildcard '.*' is not allowed with operator '{op}'",
            )
        if lhs_is_prefix and rhs_is_prefix:
            return MarkerEvalResult(
                matched=None,
                error="cannot compare two '.*' wildcard version literals",
            )
        prefix_raw, ver_raw = (
            (lhs_stripped, rhs_stripped) if lhs_is_prefix else (rhs_stripped, lhs_stripped)
        )
        prefix_parsed = _parse_pep440_prefix(prefix_raw)
        ver_parsed = _parse_pep440_version(ver_raw)
        if prefix_parsed is None or ver_parsed is None:
            return MarkerEvalResult(
                matched=None,
                error=f"unparseable version comparison: {lhs!r} {op} {rhs!r}",
            )
        p_epoch, p_release = prefix_parsed
        padded = ver_parsed.release + (0,) * max(0, len(p_release) - len(ver_parsed.release))
        is_match = ver_parsed.epoch == p_epoch and padded[: len(p_release)] == p_release
        return MarkerEvalResult(matched=is_match if op == "==" else (not is_match))

    v_lhs = _parse_pep440_version(lhs_stripped)
    v_rhs = _parse_pep440_version(rhs_stripped)
    if v_lhs is None or v_rhs is None:
        return MarkerEvalResult(
            matched=None,
            error=f"unparseable PEP 440 version in {lhs!r} {op} {rhs!r}",
        )

    if op == "==":
        return MarkerEvalResult(matched=(v_lhs.cmp_key == v_rhs.cmp_key))
    if op == "!=":
        return MarkerEvalResult(matched=(v_lhs.cmp_key != v_rhs.cmp_key))
    if op == "<":
        return MarkerEvalResult(matched=(v_lhs.cmp_key < v_rhs.cmp_key))
    if op == "<=":
        return MarkerEvalResult(matched=(v_lhs.cmp_key <= v_rhs.cmp_key))
    if op == ">":
        return MarkerEvalResult(matched=(v_lhs.cmp_key > v_rhs.cmp_key))
    if op == ">=":
        return MarkerEvalResult(matched=(v_lhs.cmp_key >= v_rhs.cmp_key))
    if op == "~=":
        if len(v_rhs.release) < 2:
            return MarkerEvalResult(
                matched=None,
                error=f"compatible release '~=' requires at least two segments: {rhs!r}",
            )
        prefix_len = len(v_rhs.release) - 1
        lhs_padded = v_lhs.release + (0,) * max(0, prefix_len - len(v_lhs.release))
        matched = (
            v_lhs.epoch == v_rhs.epoch
            and v_lhs.cmp_key >= v_rhs.cmp_key
            and lhs_padded[:prefix_len] == v_rhs.release[:prefix_len]
        )
        return MarkerEvalResult(matched=matched)

    return MarkerEvalResult(matched=None, error=f"unsupported operator {op!r}")


# ---------------------------------------------------------------------------
# Marker tokenizer and AST
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Token:
    kind: str  # "LPAREN", "RPAREN", "AND", "OR", "OP", "STRING", "IDENT"
    value: str


@dataclass(frozen=True)
class _ValueNode:
    is_var: bool
    value: str  # canonical var name if is_var else literal string


@dataclass(frozen=True)
class _CompareNode:
    lhs: _ValueNode
    op: str
    rhs: _ValueNode


@dataclass(frozen=True)
class _BoolOpNode:
    op: str  # "and" or "or"
    children: Tuple[Any, ...]


_ExprNode = Union[_CompareNode, _BoolOpNode]


def _tokenize_marker(marker_str: str) -> Tuple[Optional[List[_Token]], Optional[str]]:
    """Tokenize a PEP 508 marker expression without raising."""
    tokens: List[_Token] = []
    pos = 0
    length = len(marker_str)

    while pos < length:
        ch = marker_str[pos]
        if ch.isspace():
            pos += 1
            continue

        if ch == "(":
            tokens.append(_Token("LPAREN", "("))
            pos += 1
            continue

        if ch == ")":
            tokens.append(_Token("RPAREN", ")"))
            pos += 1
            continue

        if ch in ("'", '"'):
            quote = ch
            pos += 1
            chars: List[str] = []
            closed = False
            while pos < length:
                c = marker_str[pos]
                if c == "\\" and pos + 1 < length and marker_str[pos + 1] in (quote, "\\"):
                    chars.append(marker_str[pos + 1])
                    pos += 2
                    continue
                if c == quote:
                    closed = True
                    pos += 1
                    break
                chars.append(c)
                pos += 1
            if not closed:
                return None, "unterminated string literal in marker"
            tokens.append(_Token("STRING", "".join(chars)))
            continue

        # Multi-character and single-character comparison operators.
        three = marker_str[pos : pos + 3]
        if three == "===":
            tokens.append(_Token("OP", "==="))
            pos += 3
            continue

        two = marker_str[pos : pos + 2]
        if two in ("==", "!=", "<=", ">=", "~="):
            tokens.append(_Token("OP", two))
            pos += 2
            continue

        if ch in ("<", ">"):
            tokens.append(_Token("OP", ch))
            pos += 1
            continue

        if ch.isalpha() or ch == "_":
            start = pos
            pos += 1
            while pos < length and (marker_str[pos].isalnum() or marker_str[pos] in ("_", ".")):
                pos += 1
            ident = marker_str[start:pos]
            if ident == "and":
                tokens.append(_Token("AND", "and"))
            elif ident == "or":
                tokens.append(_Token("OR", "or"))
            elif ident == "in":
                tokens.append(_Token("OP", "in"))
            elif ident == "not":
                # Peek ahead past whitespace for "in" to emit a single "not in" token.
                look = pos
                while look < length and marker_str[look].isspace():
                    look += 1
                if (
                    marker_str[look : look + 2] == "in"
                    and (
                        look + 2 == length
                        or not (marker_str[look + 2].isalnum() or marker_str[look + 2] in ("_", "."))
                    )
                ):
                    tokens.append(_Token("OP", "not in"))
                    pos = look + 2
                else:
                    return None, "unexpected token 'not' (expected 'not in')"
            else:
                tokens.append(_Token("IDENT", ident))
            continue

        return None, f"unexpected character {ch!r} in marker"

    return tokens, None


class _MarkerParser:
    """Recursive-descent parser for PEP 508 marker expressions."""

    def __init__(self, tokens: List[_Token]) -> None:
        self._tokens = tokens
        self._pos = 0
        self._depth = 0

    def _peek(self) -> Optional[_Token]:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _consume(self) -> _Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def parse(self) -> Tuple[Optional[_ExprNode], Optional[str]]:
        if not self._tokens:
            return None, "empty marker expression"
        node, err = self._parse_or()
        if err is not None:
            return None, err
        trailing = self._peek()
        if trailing is not None:
            return None, f"unexpected trailing token {trailing.value!r}"
        return node, None

    def _parse_or(self) -> Tuple[Optional[_ExprNode], Optional[str]]:
        left, err = self._parse_and()
        if err is not None or left is None:
            return None, err
        items: List[_ExprNode] = [left]
        while True:
            tok = self._peek()
            if tok is not None and tok.kind == "OR":
                self._consume()
                right, err = self._parse_and()
                if err is not None or right is None:
                    return None, err
                items.append(right)
            else:
                break
        if len(items) == 1:
            return items[0], None
        return _BoolOpNode("or", tuple(items)), None

    def _parse_and(self) -> Tuple[Optional[_ExprNode], Optional[str]]:
        left, err = self._parse_atom()
        if err is not None or left is None:
            return None, err
        items: List[_ExprNode] = [left]
        while True:
            tok = self._peek()
            if tok is not None and tok.kind == "AND":
                self._consume()
                right, err = self._parse_atom()
                if err is not None or right is None:
                    return None, err
                items.append(right)
            else:
                break
        if len(items) == 1:
            return items[0], None
        return _BoolOpNode("and", tuple(items)), None

    def _parse_atom(self) -> Tuple[Optional[_ExprNode], Optional[str]]:
        tok = self._peek()
        if tok is None:
            return None, "unexpected end of marker expression"

        if tok.kind == "LPAREN":
            self._depth += 1
            if self._depth > _MAX_PAREN_DEPTH:
                return None, "marker parentheses nesting exceeds limit"
            self._consume()
            inner, err = self._parse_or()
            if err is not None or inner is None:
                return None, err
            closing = self._peek()
            if closing is None or closing.kind != "RPAREN":
                return None, "unmatched '(' in marker expression"
            self._consume()
            self._depth -= 1
            return inner, None

        lhs, err = self._parse_value()
        if err is not None or lhs is None:
            return None, err

        op_tok = self._peek()
        if op_tok is None or op_tok.kind != "OP":
            got = op_tok.value if op_tok is not None else "end of expression"
            return None, f"expected comparison operator, got {got!r}"
        self._consume()

        rhs, err = self._parse_value()
        if err is not None or rhs is None:
            return None, err

        return _CompareNode(lhs=lhs, op=op_tok.value, rhs=rhs), None

    def _parse_value(self) -> Tuple[Optional[_ValueNode], Optional[str]]:
        tok = self._peek()
        if tok is None:
            return None, "expected marker variable or string literal"
        if tok.kind == "STRING":
            self._consume()
            return _ValueNode(is_var=False, value=tok.value), None
        if tok.kind == "IDENT":
            self._consume()
            name = tok.value
            if name == "extra":
                return _ValueNode(is_var=True, value="extra"), None
            canonical = _LEGACY_ENV_ALIASES.get(name, name)
            if canonical in _STANDARD_ENV_VARS:
                return _ValueNode(is_var=True, value=canonical), None
            return None, f"unknown marker variable {name!r}"
        return None, f"unexpected token {tok.value!r} where value was expected"


def _eval_compare(
    node: _CompareNode,
    env: Dict[str, str],
    normalized_extra: str,
) -> MarkerEvalResult:
    """Evaluate a single ``value op value`` node."""
    lhs_var = node.lhs.value if node.lhs.is_var else None
    rhs_var = node.rhs.value if node.rhs.is_var else None

    if lhs_var == "extra":
        lhs_val = normalized_extra
    elif lhs_var is not None:
        lhs_val = env.get(lhs_var, "")
    else:
        lhs_val = node.lhs.value

    if rhs_var == "extra":
        rhs_val = normalized_extra
    elif rhs_var is not None:
        rhs_val = env.get(rhs_var, "")
    else:
        rhs_val = node.rhs.value

    op = node.op

    # PEP 503 normalize both sides when comparing against `extra`.
    if lhs_var == "extra" or rhs_var == "extra":
        lhs_norm = _normalize_name(lhs_val) if lhs_val else ""
        rhs_norm = _normalize_name(rhs_val) if rhs_val else ""
        if op == "==":
            return MarkerEvalResult(matched=(lhs_norm == rhs_norm))
        if op == "!=":
            return MarkerEvalResult(matched=(lhs_norm != rhs_norm))
        if op == "===":
            return MarkerEvalResult(matched=(lhs_norm == rhs_norm))
        if op == "in":
            if lhs_var == "extra" and lhs_norm == "" and rhs_norm != "":
                return MarkerEvalResult(matched=False)
            return MarkerEvalResult(matched=(lhs_norm in rhs_norm))
        if op == "not in":
            if lhs_var == "extra" and lhs_norm == "" and rhs_norm != "":
                return MarkerEvalResult(matched=True)
            return MarkerEvalResult(matched=(lhs_norm not in rhs_norm))
        if op == "<":
            return MarkerEvalResult(matched=(lhs_norm < rhs_norm))
        if op == "<=":
            return MarkerEvalResult(matched=(lhs_norm <= rhs_norm))
        if op == ">":
            return MarkerEvalResult(matched=(lhs_norm > rhs_norm))
        if op == ">=":
            return MarkerEvalResult(matched=(lhs_norm >= rhs_norm))
        return MarkerEvalResult(
            matched=None,
            error=f"operator {op!r} is not supported for 'extra' comparisons",
        )

    # PEP 440 version comparisons for version environment variables.
    if lhs_var in _VERSION_VARS or rhs_var in _VERSION_VARS:
        return _compare_versions(lhs_val, op, rhs_val)

    # Standard string comparisons for non-version environment variables.
    if op == "==":
        return MarkerEvalResult(matched=(lhs_val == rhs_val))
    if op == "!=":
        return MarkerEvalResult(matched=(lhs_val != rhs_val))
    if op == "===":
        return MarkerEvalResult(matched=(lhs_val.lower() == rhs_val.lower()))
    if op == "<":
        return MarkerEvalResult(matched=(lhs_val < rhs_val))
    if op == "<=":
        return MarkerEvalResult(matched=(lhs_val <= rhs_val))
    if op == ">":
        return MarkerEvalResult(matched=(lhs_val > rhs_val))
    if op == ">=":
        return MarkerEvalResult(matched=(lhs_val >= rhs_val))
    if op == "in":
        return MarkerEvalResult(matched=(lhs_val in rhs_val))
    if op == "not in":
        return MarkerEvalResult(matched=(lhs_val not in rhs_val))

    return MarkerEvalResult(
        matched=None,
        error=f"operator {op!r} is only supported for version comparisons",
    )


def _eval_ast(
    node: _ExprNode,
    env: Dict[str, str],
    normalized_extra: str,
) -> MarkerEvalResult:
    """Evaluate a parsed marker AST against ``env`` and ``normalized_extra``."""
    if isinstance(node, _CompareNode):
        return _eval_compare(node, env, normalized_extra)

    if node.op == "and":
        result_val = True
        for child in node.children:
            res = _eval_ast(child, env, normalized_extra)
            if res.matched is None:
                return res
            if not res.matched:
                result_val = False
        return MarkerEvalResult(matched=result_val)

    if node.op == "or":
        result_val = False
        for child in node.children:
            res = _eval_ast(child, env, normalized_extra)
            if res.matched is None:
                return res
            if res.matched:
                result_val = True
        return MarkerEvalResult(matched=result_val)

    return MarkerEvalResult(matched=None, error=f"unsupported boolean op {node.op!r}")


def _resolve_env(env: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Merge optional caller-provided marker variables with runtime defaults."""
    resolved = default_marker_environment()
    if env:
        for key, value in env.items():
            canonical = _LEGACY_ENV_ALIASES.get(key, key)
            resolved[canonical] = str(value)
    return resolved


def evaluate_marker(
    marker_str: str,
    *,
    active_extra: str = "",
    active_extras: Optional[FrozenSet[str]] = None,
    env: Optional[Dict[str, str]] = None,
) -> MarkerEvalResult:
    """Evaluate a PEP 508 environment marker string.

    Returns ``MarkerEvalResult(matched=True|False)`` for valid markers, or
    ``MarkerEvalResult(matched=None, error=...)`` for unsupported, unknown, or
    malformed syntax without raising exceptions.
    """
    if not isinstance(marker_str, str) or not marker_str.strip():
        return MarkerEvalResult(matched=None, error="empty marker expression")

    tokens, tok_err = _tokenize_marker(marker_str)
    if tok_err is not None or tokens is None:
        return MarkerEvalResult(matched=None, error=tok_err or "marker tokenization error")

    try:
        ast_node, parse_err = _MarkerParser(tokens).parse()
    except RecursionError:
        return MarkerEvalResult(matched=None, error="marker nesting too deep")

    if parse_err is not None or ast_node is None:
        return MarkerEvalResult(matched=None, error=parse_err or "marker parse error")

    resolved_env = _resolve_env(env)

    if active_extras is not None and len(active_extras) > 0:
        normalized_set = sorted(
            {_normalize_name(e) if e else "" for e in active_extras}
        )
        first_error: Optional[str] = None
        for norm_extra in normalized_set:
            res = _eval_ast(ast_node, resolved_env, norm_extra)
            if res.matched is True:
                return MarkerEvalResult(matched=True)
            if res.matched is None and first_error is None:
                first_error = res.error or "marker evaluation error"
        if first_error is not None:
            return MarkerEvalResult(matched=None, error=first_error)
        return MarkerEvalResult(matched=False)

    norm_single = _normalize_name(active_extra) if active_extra else ""
    return _eval_ast(ast_node, resolved_env, norm_single)
