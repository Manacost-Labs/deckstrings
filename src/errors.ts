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
	public readonly code: DeckstringErrorCode;

	constructor(code: DeckstringErrorCode, message: string) {
		super(message);
		this.name = "DeckstringError";
		this.code = code;
		const objectConstructor = Object as any;
		if (objectConstructor.setPrototypeOf) {
			objectConstructor.setPrototypeOf(this, DeckstringError.prototype);
		} else {
			(this as any).__proto__ = DeckstringError.prototype;
		}
	}
}
