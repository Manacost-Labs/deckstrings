import type { DeckstringErrorCode } from "./types";

export class DeckstringError extends Error {
	public readonly code: DeckstringErrorCode;

	constructor(code: DeckstringErrorCode, message: string) {
		super(message);
		this.name = "DeckstringError";
		this.code = code;
		Object.setPrototypeOf(this, new.target.prototype);
	}
}
