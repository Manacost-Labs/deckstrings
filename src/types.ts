import type { FormatType } from "./constants";

export type { FormatType } from "./constants";

/** A card DBF ID and its count. */
export type DeckCard = [dbfId: number, count: number];

/** @deprecated Use {@link DeckCard} instead. */
export type DeckList = DeckCard[];

/** A sideboard card DBF ID, its count, and the owning card DBF ID. */
export type SideboardCard = [
	dbfId: number,
	count: number,
	sideboardOwnerDbfId: number,
];

export interface DeckDefinition {
	cards: DeckCard[];
	sideboardCards?: SideboardCard[];
	heroes: number[];
	format: FormatType;
}

export type DeckstringErrorCode =
	| "invalid_input"
	| "invalid_base64"
	| "unexpected_end"
	| "invalid_reserved"
	| "unsupported_version"
	| "unsupported_format"
	| "invalid_varint"
	| "invalid_id"
	| "invalid_count"
	| "invalid_sideboard"
	| "trailing_data"
	| "limit_exceeded"
	| "invalid_deck";
