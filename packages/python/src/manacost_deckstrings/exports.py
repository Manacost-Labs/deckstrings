"""Hearthstone clipboard export parsing and formatting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from .codec import DeckstringError, canonicalize, decode, encode
from .types import CardResolver, ExportMetadata, ParsedExport

MAX_EXPORT_UTF8_LENGTH = 1_500_000
EXPORT_WHITESPACE = (
    "\u0009\u000a\u000b\u000c\u000d\u0020\u0085\u00a0\u1680"
    "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
    "\u2028\u2029\u202f\u205f\u3000"
)


def _trim_export_whitespace(value: str) -> str:
    return value.strip(EXPORT_WHITESPACE)


def _strip_comment(line: str) -> str:
    comment = line[1:]
    return comment[1:] if comment.startswith(" ") else comment


def parse_export(text: str) -> ParsedExport:
    """Parse a complete Hearthstone clipboard export."""

    if not isinstance(text, str) or not text:
        raise DeckstringError("invalid_input", "Export must be a non-empty string.")
    if len(text) > MAX_EXPORT_UTF8_LENGTH:
        raise DeckstringError(
            "limit_exceeded", "Export exceeds the maximum supported size."
        )
    try:
        encoded = text.encode("utf-8")
    except UnicodeEncodeError as error:
        raise DeckstringError(
            "invalid_input", "Export must contain well-formed Unicode."
        ) from error
    if len(encoded) > MAX_EXPORT_UTF8_LENGTH:
        raise DeckstringError(
            "limit_exceeded", "Export exceeds the maximum supported size."
        )

    name: str | None = None
    comments: list[str] = []
    deckstrings: list[str] = []

    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not _trim_export_whitespace(line):
            continue
        if line.startswith("###"):
            if deckstrings:
                raise DeckstringError(
                    "invalid_input", "Deck name must appear before the deckstring."
                )
            if name is None:
                candidate = _trim_export_whitespace(line[3:])
                if not candidate:
                    raise DeckstringError("invalid_input", "Deck name cannot be empty.")
                name = candidate
            else:
                comments.append(_strip_comment(line))
            continue
        if line.startswith("#"):
            comments.append(_strip_comment(line))
            continue
        deckstrings.append(_trim_export_whitespace(line))

    if len(deckstrings) != 1:
        raise DeckstringError(
            "invalid_input", "Export must contain exactly one deckstring."
        )

    deck = decode(deckstrings[0])
    deckstring = encode(deck)
    metadata: ExportMetadata = {"comments": comments}
    if name is not None:
        metadata["name"] = name
    return {"deck": deck, "deckstring": deckstring, "metadata": metadata}


def _metadata_text(value: object, name: str, *, allow_empty: bool) -> str:
    if not isinstance(value, str) or (not value and not allow_empty):
        raise DeckstringError("invalid_input", f"{name} must be a string.")
    if "\n" in value or "\r" in value:
        raise DeckstringError("invalid_input", f"{name} must contain one line.")
    return value


def _resolved_line(
    dbf_id: int,
    count: int,
    resolve_card: CardResolver,
    owner: int | None = None,
) -> str | None:
    resolved = resolve_card(dbf_id)
    if resolved is None:
        return None
    if not isinstance(resolved, Mapping):
        raise DeckstringError(
            "invalid_input", "Card resolver must return an object or None."
        )
    name = _metadata_text(resolved.get("name"), "resolved card name", allow_empty=False)
    cost_value = resolved.get("cost", 0)
    if not _trim_export_whitespace(name):
        raise DeckstringError("invalid_input", "Resolved card name cannot be blank.")
    if type(cost_value) is not int or cost_value < 0 or cost_value > 2_147_483_647:
        raise DeckstringError(
            "invalid_input", "Resolved card cost must be a non-negative integer."
        )
    suffix = "" if owner is None else f" [sideboard:{owner}]"
    return f"{count}x ({cost_value}) {name}{suffix}"


def format_export(
    deck: Mapping[str, object],
    metadata: Mapping[str, object] | None = None,
    resolve_card: CardResolver | None = None,
) -> str:
    """Format a deterministic, locale-neutral Hearthstone clipboard export."""

    canonical = canonicalize(deck)
    metadata = {} if metadata is None else metadata
    if not isinstance(metadata, Mapping):
        raise DeckstringError("invalid_input", "Export metadata must be an object.")

    lines: list[str] = []
    if "name" in metadata:
        name = _trim_export_whitespace(
            _metadata_text(metadata["name"], "deck name", allow_empty=False)
        )
        if not name:
            raise DeckstringError("invalid_input", "Deck name cannot be empty.")
        lines.append(f"### {name}")

    comments_value = metadata.get("comments", [])
    if isinstance(comments_value, (str, bytes, bytearray)) or not isinstance(
        comments_value, Sequence
    ):
        raise DeckstringError("invalid_input", "Export comments must be an array.")
    for index, comment_value in enumerate(cast(Sequence[object], comments_value)):
        comment = _metadata_text(comment_value, f"comments[{index}]", allow_empty=True)
        lines.append("#" if not comment else f"# {comment}")

    if resolve_card is not None:
        for dbf_id, count in canonical["cards"]:
            line = _resolved_line(dbf_id, count, resolve_card)
            if line is not None:
                lines.append(f"# {line}")
        for dbf_id, count, owner in canonical["sideboardCards"]:
            line = _resolved_line(dbf_id, count, resolve_card, owner)
            if line is not None:
                lines.append(f"# {line}")

    deckstring = encode(canonical)
    if not lines:
        return deckstring
    lines.extend(("#", deckstring))
    return "\n".join(lines)
