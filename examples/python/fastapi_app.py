"""Illustrative FastAPI adapter: `fastapi dev fastapi_app.py`."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from manacost_deckstrings import DeckstringError, decode, encode, parse_export

app = FastAPI(title="Deckstrings API")


class DecodeRequest(BaseModel):
    deckstring: str = Field(min_length=1, max_length=1_398_104)


class ExportRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1_500_000)


def invalid_deckstring(error: DeckstringError) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={"code": error.code, "message": "The deck input is invalid."},
    )


@app.post("/deckstrings/decode")
def decode_deck(request: DecodeRequest) -> dict[str, object]:
    try:
        deck = decode(request.deckstring)
        return {"deck": deck, "deckstring": encode(deck)}
    except DeckstringError as error:
        raise invalid_deckstring(error) from error


@app.post("/deckstrings/parse-export")
def parse_deck_export(request: ExportRequest) -> dict[str, object]:
    try:
        return dict(parse_export(request.text))
    except DeckstringError as error:
        raise invalid_deckstring(error) from error
