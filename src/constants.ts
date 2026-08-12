export const DECKSTRING_VERSION = 1;

export type FormatType = 1 | 2 | 3 | 4;

export const FormatType = {
	FT_WILD: 1,
	FT_STANDARD: 2,
	FT_CLASSIC: 3,
	FT_TWIST: 4,
} as const satisfies Record<string, FormatType>;
