import { atob, btoa } from "./base64";
import { DeckstringError } from "./errors";

const MAX_BASE64_LENGTH = 1398104;
const MAX_DECODED_LENGTH = 1048576;
const MAX_VARINT = 0x7fffffff;

/** @internal */
export class Iterator {
	index: number;

	constructor() {
		this.index = 0;
	}

	public next(repeat = 1): void {
		this.index += repeat;
	}
}

/** @internal */
export class BufferWriter extends Iterator {
	buffer: number[];

	constructor() {
		super();
		this.buffer = [];
	}

	public null(): void {
		this.buffer[this.index] = 0;
		this.next();
	}

	public varint(value: number): void {
		let remaining = value;
		do {
			let byte = remaining % 128;
			remaining = Math.floor(remaining / 128);
			if (remaining > 0) {
				byte |= 0x80;
			}
			this.buffer[this.index] = byte;
			this.next();
		} while (remaining > 0);
	}

	public override toString(): string {
		const chunks: string[] = [];
		const chunkSize = 0x8000;
		for (let index = 0; index < this.buffer.length; index += chunkSize) {
			chunks.push(
				String.fromCharCode(
					...this.buffer.slice(index, index + chunkSize)
				)
			);
		}
		const binary = chunks.join("");
		return btoa(binary);
	}
}

/** @internal */
export class BufferReader extends Iterator {
	buffer: Uint8Array;

	constructor(string: unknown) {
		super();
		if (typeof string !== "string" || string.length === 0) {
			throw new DeckstringError(
				"invalid_input",
				"Deckstring must be a non-empty string."
			);
		}
		if (string.length > MAX_BASE64_LENGTH) {
			throw new DeckstringError(
				"limit_exceeded",
				"Deckstring exceeds the maximum supported size."
			);
		}
		if (string.length % 4 !== 0 || !/^[A-Za-z0-9+/]*={0,2}$/.test(string)) {
			throw new DeckstringError(
				"invalid_base64",
				"Deckstring is not valid Base64."
			);
		}

		let binary: string;
		try {
			binary = atob(string);
		} catch {
			throw new DeckstringError(
				"invalid_base64",
				"Deckstring is not valid Base64."
			);
		}
		if (binary.length > MAX_DECODED_LENGTH) {
			throw new DeckstringError(
				"limit_exceeded",
				"Deckstring exceeds the maximum supported size."
			);
		}
		const buffer = new Uint8Array(binary.length);
		for (let i = 0; i < binary.length; i++) {
			buffer[i] = binary.charCodeAt(i);
		}
		this.buffer = buffer;
	}

	public get atEnd(): boolean {
		return this.index >= this.buffer.length;
	}

	public nextByte(): number {
		if (this.atEnd) {
			throw new DeckstringError(
				"unexpected_end",
				"Unexpected end of deckstring."
			);
		}
		const value = this.buffer[this.index]!;
		this.next();
		return value;
	}

	public nextVarint(): number {
		let value = 0;
		let multiplier = 1;

		for (let byteIndex = 0; byteIndex < 5; byteIndex++) {
			let current: number;
			try {
				current = this.nextByte();
			} catch (error) {
				if (byteIndex > 0) {
					throw new DeckstringError(
						"invalid_varint",
						"Deckstring contains a truncated varint."
					);
				}
				throw error;
			}

			value += (current & 0x7f) * multiplier;
			if ((current & 0x80) === 0) {
				if (value > MAX_VARINT) {
					throw new DeckstringError(
						"invalid_varint",
						"Deckstring varint is too large."
					);
				}
				return value;
			}
			multiplier *= 128;
		}

		throw new DeckstringError(
			"invalid_varint",
			"Deckstring varint is too large."
		);
	}
}
