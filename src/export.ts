import { DeckstringError } from "./errors";
import type { DeckDefinition } from "./types";

const MAX_EXPORT_UTF8_LENGTH = 1_500_000;
const EXPORT_WHITESPACE =
	/^[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/g;

export interface ExportMetadata {
	name?: string;
	comments: string[];
}

export interface FormatExportMetadata {
	name?: string;
	comments?: string[];
}

export interface ParsedExport {
	deck: Required<DeckDefinition>;
	deckstring: string;
	metadata: ExportMetadata;
}

export interface ResolvedCard {
	name: string;
	cost?: number;
}

export type CardResolver = (dbfId: number) => ResolvedCard | null | undefined;

export interface ExportCodec {
	decode(deckstring: string): Required<DeckDefinition>;
	encode(deck: DeckDefinition): string;
	canonicalize(deck: DeckDefinition): Required<DeckDefinition>;
}

function invalidInput(message: string): never {
	throw new DeckstringError("invalid_input", message);
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

function trimExportWhitespace(value: string): string {
	return value.replace(EXPORT_WHITESPACE, "");
}

function isWellFormedUnicode(value: string): boolean {
	for (let index = 0; index < value.length; index++) {
		const codeUnit = value.charCodeAt(index);
		if (codeUnit >= 0xd800 && codeUnit <= 0xdbff) {
			if (index + 1 >= value.length) {
				return false;
			}
			const next = value.charCodeAt(index + 1);
			if (next < 0xdc00 || next > 0xdfff) {
				return false;
			}
			index++;
		} else if (codeUnit >= 0xdc00 && codeUnit <= 0xdfff) {
			return false;
		}
	}
	return true;
}

function normalizeSingleLine(value: unknown, name: string): string {
	if (typeof value !== "string") {
		return invalidInput(`${name} must be a string`);
	}
	if (value.includes("\n") || value.includes("\r")) {
		return invalidInput(`${name} must not contain a line break`);
	}
	return value;
}

function resolvedCardLine(
	dbfId: number,
	count: number,
	resolveCard: CardResolver,
	owner?: number
): string | undefined {
	const card = resolveCard(dbfId);
	if (card == null) {
		return undefined;
	}
	if (typeof card !== "object") {
		return invalidInput("card resolver must return an object or null");
	}
	const name = normalizeSingleLine(card.name, "card name");
	if (trimExportWhitespace(name).length === 0) {
		return invalidInput("card name must not be empty");
	}
	const cost = card.cost ?? 0;
	if (!Number.isInteger(cost) || cost < 0 || cost > 0x7fffffff) {
		return invalidInput("card cost must be a non-negative integer");
	}
	const suffix = owner === undefined ? "" : ` [sideboard:${owner}]`;
	return `# ${count}x (${cost}) ${name}${suffix}`;
}

export function parseExportWithCodec(
	text: unknown,
	codec: ExportCodec
): ParsedExport {
	if (typeof text !== "string" || text.length === 0) {
		return invalidInput("export must be a non-empty string");
	}
	if (text.length > MAX_EXPORT_UTF8_LENGTH) {
		throw new DeckstringError(
			"limit_exceeded",
			"export exceeds the maximum supported size"
		);
	}
	if (!isWellFormedUnicode(text)) {
		return invalidInput("export must contain well-formed Unicode");
	}
	if (new TextEncoder().encode(text).length > MAX_EXPORT_UTF8_LENGTH) {
		throw new DeckstringError(
			"limit_exceeded",
			"export exceeds the maximum supported size"
		);
	}
	if (trimExportWhitespace(text).length === 0) {
		return invalidInput("export must be a non-empty string");
	}

	const comments: string[] = [];
	let name: string | undefined;
	let deckstring: string | undefined;

	for (const line of text.replace(/\r\n?/g, "\n").split("\n")) {
		if (trimExportWhitespace(line).length === 0) {
			continue;
		}
		if (line.startsWith("###")) {
			if (deckstring !== undefined) {
				return invalidInput(
					"deck name must appear before the deckstring"
				);
			}
			if (name === undefined) {
				const candidate = trimExportWhitespace(line.slice(3));
				if (candidate.length === 0) {
					return invalidInput("deck name must not be empty");
				}
				name = candidate;
			} else {
				comments.push(line.slice(1).replace(/^ /, ""));
			}
			continue;
		}
		if (line.startsWith("#")) {
			comments.push(line.slice(1).replace(/^ /, ""));
			continue;
		}
		if (deckstring !== undefined) {
			return invalidInput("export must contain exactly one deckstring");
		}
		deckstring = trimExportWhitespace(line);
	}

	if (deckstring === undefined) {
		return invalidInput("export does not contain a deckstring");
	}

	const deck = codec.decode(deckstring);
	const canonicalDeckstring = codec.encode(deck);
	const metadata: ExportMetadata = name ? { name, comments } : { comments };
	return { deck, deckstring: canonicalDeckstring, metadata };
}

export function formatExportWithCodec(
	deck: DeckDefinition,
	codec: ExportCodec,
	metadata: FormatExportMetadata = {},
	resolveCard?: CardResolver
): string {
	if (!isRecord(metadata)) {
		return invalidInput("export metadata must be an object");
	}
	if (resolveCard !== undefined && typeof resolveCard !== "function") {
		return invalidInput("card resolver must be a function");
	}

	const canonicalDeck = codec.canonicalize(deck);
	const deckstring = codec.encode(canonicalDeck);
	const lines: string[] = [];

	if (Object.prototype.hasOwnProperty.call(metadata, "name")) {
		const name = trimExportWhitespace(
			normalizeSingleLine(metadata.name, "deck name")
		);
		if (name.length === 0) {
			return invalidInput("deck name must not be empty");
		}
		lines.push(`### ${name}`);
	}

	const comments = Object.prototype.hasOwnProperty.call(metadata, "comments")
		? metadata.comments
		: [];
	if (!Array.isArray(comments)) {
		return invalidInput("export comments must be an array");
	}
	for (const comment of comments) {
		const normalized = normalizeSingleLine(comment, "comment");
		lines.push(normalized.length === 0 ? "#" : `# ${normalized}`);
	}

	if (resolveCard) {
		for (const [dbfId, count] of canonicalDeck.cards) {
			const line = resolvedCardLine(dbfId, count, resolveCard);
			if (line !== undefined) {
				lines.push(line);
			}
		}
		for (const [dbfId, count, owner] of canonicalDeck.sideboardCards) {
			const line = resolvedCardLine(dbfId, count, resolveCard, owner);
			if (line !== undefined) {
				lines.push(line);
			}
		}
	}

	if (lines.length > 0) {
		lines.push("#");
	}
	lines.push(deckstring);

	return lines.join("\n");
}
