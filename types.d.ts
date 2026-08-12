export type FormatType = 1 | 2 | 3 | 4;

export type DeckCard = [number, number]; // [dbfId, count]
export type DeckList = DeckCard[]; // keep type for backwards compatibility

export type SideboardCard = [number, number, number]; // [dbfId, count, sideboardOwnerDbfId]

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

export class DeckstringError extends Error {
	readonly code: DeckstringErrorCode;
}

export function encode(deck: DeckDefinition): string;

export function decode(deckstring: string): Required<DeckDefinition>;
