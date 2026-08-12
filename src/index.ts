import { BufferReader, BufferWriter } from "./buffer";
import type { DeckCard, DeckDefinition, SideboardCard } from "./types";
import { DECKSTRING_VERSION, FormatType } from "./constants";
import { DeckstringError } from "./errors";
import { canonicalize, validate } from "./api";
import { formatExportWithCodec, parseExportWithCodec } from "./export";
import type {
	CardResolver,
	FormatExportMetadata,
	ParsedExport,
} from "./export";

type BaseCard = [number, number, ...unknown[]];
const MAX_ITEMS_PER_GROUP = 10000;

function verifyDbfId(id: unknown, name?: string): void {
	name = name ? name : "dbf id";
	if (!isPositiveNaturalNumber(id)) {
		throw new DeckstringError(
			"invalid_id",
			`Invalid ${name} ${id} (expected valid dbf id)`
		);
	}
}

function isPositiveNaturalNumber(n: unknown): boolean {
	if (typeof n !== "number" || !Number.isFinite(n)) {
		return false;
	}
	if (!Number.isInteger(n)) {
		return false;
	}
	return n > 0 && n <= 0x7fffffff;
}

function sort_cards<T extends BaseCard>(
	cards: T[],
	sideboard: boolean = false
): T[] {
	if (sideboard) {
		return cards.sort((a, b) => Number(a[2]) - Number(b[2]) || a[0] - b[0]);
	}
	return cards.sort((a, b) => a[0] - b[0]);
}

function trisort_cards<T extends BaseCard>(cards: T[]): [T[], T[], T[]] {
	const single: T[] = [],
		double: T[] = [],
		n: T[] = [];
	for (const tuple of cards) {
		const [card, count] = tuple;
		if (count === 0) {
			continue;
		}
		if (count === 1) {
			single.push(tuple);
		} else if (count === 2) {
			double.push(tuple);
		} else if (isPositiveNaturalNumber(count)) {
			n.push(tuple);
		} else {
			throw new DeckstringError(
				"invalid_count",
				`Invalid count ${count} (expected positive natural number)`
			);
		}
	}
	return [single, double, n];
}

export function encode(deck: DeckDefinition): string {
	const canonicalDeck = canonicalize(deck);
	const writer = new BufferWriter();

	const format = canonicalDeck.format;
	const heroes = canonicalDeck.heroes;
	const cards = canonicalDeck.cards;
	const sideboard = canonicalDeck.sideboardCards;

	writer.null();
	writer.varint(DECKSTRING_VERSION);
	writer.varint(format);
	writer.varint(heroes.length);
	for (const hero of heroes) {
		verifyDbfId(hero, "hero");
		writer.varint(hero);
	}

	for (const list of trisort_cards(cards)) {
		writer.varint(list.length);
		for (const tuple of list) {
			const [card, count] = tuple;
			verifyDbfId(card, "card");
			writer.varint(card);
			if (count !== 1 && count !== 2) {
				writer.varint(count);
			}
		}
	}

	if (sideboard.length) {
		writer.varint(1);
		for (const list of trisort_cards(sideboard)) {
			writer.varint(list.length);
			for (const tuple of list) {
				const [card, count, owner] = tuple;
				verifyDbfId(card, "sideboard card");
				verifyDbfId(owner, "sideboard card owner");
				writer.varint(card);
				if (count !== 1 && count !== 2) {
					writer.varint(count);
				}
				writer.varint(owner);
			}
		}
	} else {
		writer.varint(0);
	}

	return writer.toString();
}

export function decode(deckstring: string): Required<DeckDefinition> {
	const reader = new BufferReader(deckstring);

	if (reader.nextByte() !== 0) {
		throw new DeckstringError("invalid_reserved", "Invalid reserved byte.");
	}

	const version = reader.nextVarint();
	if (version !== DECKSTRING_VERSION) {
		throw new DeckstringError(
			"unsupported_version",
			`Unsupported deckstring version ${version}`
		);
	}

	const format = reader.nextVarint();
	if (
		format !== FormatType.FT_WILD &&
		format !== FormatType.FT_STANDARD &&
		format !== FormatType.FT_CLASSIC &&
		format !== FormatType.FT_TWIST
	) {
		throw new DeckstringError(
			"unsupported_format",
			`Unsupported format ${format} in deckstring`
		);
	}

	const heroCount = readGroupCount(reader);
	if (heroCount === 0) {
		throw new DeckstringError(
			"invalid_count",
			"Deckstring must contain at least one hero."
		);
	}
	const heroes = new Array(heroCount);
	for (let i = 0; i < heroes.length; i++) {
		heroes[i] = readPositiveVarint(reader, "hero DBF ID");
	}
	heroes.sort((a, b) => a - b);

	const cards: DeckCard[] = [];
	for (let i = 1; i <= 3; i++) {
		for (let j = 0, c = readGroupCount(reader); j < c; j++) {
			cards.push([
				readPositiveVarint(reader, "card DBF ID"),
				i === 1 || i === 2
					? i
					: readPositiveVarint(reader, "card count", "invalid_count"),
			]);
		}
	}
	sort_cards(cards);

	const sideboardCards: SideboardCard[] = [];
	const hasSideboard = reader.atEnd ? 0 : reader.nextVarint();
	if (hasSideboard !== 0 && hasSideboard !== 1) {
		throw new DeckstringError(
			"invalid_sideboard",
			"Invalid sideboard marker."
		);
	}
	if (hasSideboard == 1) {
		for (let i = 1; i <= 3; i++) {
			for (let j = 0, c = readGroupCount(reader); j < c; j++) {
				sideboardCards.push([
					readPositiveVarint(reader, "sideboard DBF ID"),
					i === 1 || i === 2
						? i
						: readPositiveVarint(
								reader,
								"sideboard count",
								"invalid_count"
							),
					readPositiveVarint(reader, "sideboard owner DBF ID"),
				]);
			}
		}
		sort_cards(sideboardCards, true);
	}
	if (!reader.atEnd) {
		throw new DeckstringError(
			"trailing_data",
			"Deckstring contains trailing data."
		);
	}

	return canonicalize({
		cards,
		sideboardCards,
		heroes,
		format,
	});
}

export function parseExport(text: unknown): ParsedExport {
	return parseExportWithCodec(text, { decode, encode, canonicalize });
}

export function formatExport(
	deck: DeckDefinition,
	metadata: FormatExportMetadata = {},
	resolveCard?: CardResolver
): string {
	return formatExportWithCodec(
		deck,
		{ decode, encode, canonicalize },
		metadata,
		resolveCard
	);
}

function readPositiveVarint(
	reader: BufferReader,
	name: string,
	errorCode: "invalid_id" | "invalid_count" = "invalid_id"
): number {
	const value = reader.nextVarint();
	if (value <= 0) {
		throw new DeckstringError(errorCode, `${name} must be positive.`);
	}
	return value;
}

function readGroupCount(reader: BufferReader): number {
	const count = reader.nextVarint();
	if (count > MAX_ITEMS_PER_GROUP) {
		throw new DeckstringError(
			"limit_exceeded",
			"Deckstring item group is too large."
		);
	}
	return count;
}

export { canonicalize, DeckstringError, FormatType, validate };
export type {
	DeckCard,
	DeckDefinition,
	DeckList,
	DeckstringErrorCode,
	SideboardCard,
} from "./types";
export type { ValidationError, ValidationResult } from "./api";
export type {
	CardResolver,
	ExportMetadata,
	FormatExportMetadata,
	ParsedExport,
	ResolvedCard,
} from "./export";
