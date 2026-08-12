import { FormatType } from "./constants";
import { DeckstringError } from "./errors";
import type {
	DeckCard,
	DeckDefinition,
	DeckstringErrorCode,
	SideboardCard,
} from "./types";

const MAX_ITEMS_PER_GROUP = 10_000;
const MAX_ITEMS_PER_DECK = 30_000;
const MAX_TOP_LEVEL_PROPERTIES = 16;
const MAX_INTEGER = 0x7fffffff;

export interface ValidationError {
	code: DeckstringErrorCode;
	path: string;
	message: string;
}

export interface ValidationResult {
	valid: boolean;
	errors: ValidationError[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isPositiveInteger(value: unknown): value is number {
	return (
		typeof value === "number" &&
		Number.isInteger(value) &&
		value > 0 &&
		value <= MAX_INTEGER
	);
}

function validateDeck(
	deck: unknown,
	allowZeroCounts: boolean
): ValidationError[] {
	const errors: ValidationError[] = [];
	const add = (
		code: DeckstringErrorCode,
		path: string,
		message: string
	): void => {
		errors.push({ code, path, message });
	};

	if (!isRecord(deck)) {
		add("invalid_deck", "", "deck must be an object");
		return errors;
	}

	let propertyCount = 0;
	for (const key in deck) {
		if (!Object.prototype.hasOwnProperty.call(deck, key)) {
			continue;
		}
		propertyCount += 1;
		if (propertyCount > MAX_TOP_LEVEL_PROPERTIES) {
			add("limit_exceeded", "", "deck contains too many properties");
			return errors;
		}
	}

	const heroesLength = Array.isArray(deck.heroes) ? deck.heroes.length : 0;
	const cardsLength = Array.isArray(deck.cards) ? deck.cards.length : 0;
	const sideboardsLength = Array.isArray(deck.sideboardCards)
		? deck.sideboardCards.length
		: 0;
	if (heroesLength + cardsLength + sideboardsLength > MAX_ITEMS_PER_DECK) {
		add("limit_exceeded", "", "deck contains too many items");
		return errors;
	}

	for (const key of Object.keys(deck)) {
		if (!["format", "heroes", "cards", "sideboardCards"].includes(key)) {
			add("invalid_deck", key, "deck contains an unknown property");
		}
	}

	if (!Object.values(FormatType).includes(deck.format as never)) {
		add(
			"unsupported_format",
			"format",
			"format must be Wild, Standard, Classic, or Twist"
		);
	}

	if (!Array.isArray(deck.heroes)) {
		add("invalid_deck", "heroes", "heroes must be an array");
	} else {
		if (deck.heroes.length === 0) {
			add(
				"invalid_count",
				"heroes",
				"deck must contain at least one hero"
			);
		}
		if (deck.heroes.length > MAX_ITEMS_PER_GROUP) {
			add("limit_exceeded", "heroes", "hero group is too large");
		}
		const seen = new Set<number>();
		for (let index = 0; index < deck.heroes.length; index++) {
			const hero = deck.heroes[index];
			if (!isPositiveInteger(hero)) {
				add(
					"invalid_id",
					`heroes[${index}]`,
					"hero DBF ID must be a positive integer"
				);
			} else if (seen.has(hero)) {
				add(
					"invalid_deck",
					`heroes[${index}]`,
					"hero DBF ID is duplicated"
				);
			} else {
				seen.add(hero);
			}
		}
	}

	validateCardGroup(deck.cards, "cards", false, allowZeroCounts, add);
	if (deck.sideboardCards !== undefined) {
		validateCardGroup(
			deck.sideboardCards,
			"sideboardCards",
			true,
			allowZeroCounts,
			add
		);
	}

	return errors;
}

function validateCardGroup(
	value: unknown,
	path: "cards" | "sideboardCards",
	sideboard: boolean,
	allowZeroCounts: boolean,
	add: (code: DeckstringErrorCode, path: string, message: string) => void
): void {
	if (!Array.isArray(value)) {
		add("invalid_deck", path, `${path} must be an array`);
		return;
	}
	const seen = new Set<string>();
	const groupCounts = [0, 0, 0];
	for (let index = 0; index < value.length; index++) {
		const entry = value[index];
		const entryPath = `${path}[${index}]`;
		const expectedLength = sideboard ? 3 : 2;
		if (!Array.isArray(entry) || entry.length !== expectedLength) {
			add(
				"invalid_deck",
				entryPath,
				`${entryPath} must be a ${sideboard ? "triplet" : "pair"}`
			);
			continue;
		}

		const [dbfId, count, owner] = entry;
		if (!isPositiveInteger(dbfId)) {
			add(
				"invalid_id",
				`${entryPath}[0]`,
				"card DBF ID must be a positive integer"
			);
		}
		const validCount =
			typeof count === "number" &&
			Number.isInteger(count) &&
			count <= MAX_INTEGER &&
			(count > 0 || (allowZeroCounts && count === 0));
		if (!validCount) {
			add(
				"invalid_count",
				`${entryPath}[1]`,
				"card count must be a positive integer"
			);
		}

		if (sideboard && !isPositiveInteger(owner)) {
			add(
				"invalid_id",
				`${entryPath}[2]`,
				"sideboard owner DBF ID must be a positive integer"
			);
		}

		if (validCount && count === 0 && allowZeroCounts) {
			continue;
		}

		if (
			isPositiveInteger(dbfId) &&
			(!sideboard || isPositiveInteger(owner))
		) {
			const key = sideboard ? `${owner}:${dbfId}` : String(dbfId);
			if (seen.has(key)) {
				add(
					"invalid_deck",
					sideboard ? entryPath : `${entryPath}[0]`,
					"card is duplicated"
				);
			} else {
				seen.add(key);
			}
		}

		if (validCount && count > 0) {
			const group = count === 1 ? 0 : count === 2 ? 1 : 2;
			groupCounts[group]! += 1;
		}
	}

	if (groupCounts.some((count) => count > MAX_ITEMS_PER_GROUP)) {
		add("limit_exceeded", path, `${path} item group is too large`);
	}
}

export function validate(deck: unknown): ValidationResult {
	const errors = validateDeck(deck, false);
	return { valid: errors.length === 0, errors };
}

export function canonicalize(deck: DeckDefinition): Required<DeckDefinition> {
	const errors = validateDeck(deck, true);
	if (errors.length > 0) {
		const first = errors[0]!;
		throw new DeckstringError(
			first.code,
			`${first.path}: ${first.message}`
		);
	}

	const source = deck as Required<DeckDefinition>;
	const cards = source.cards
		.filter(([, count]) => count !== 0)
		.map(([dbfId, count]): DeckCard => [dbfId, count])
		.sort(([left], [right]) => left - right);
	const sideboardCards = (source.sideboardCards ?? [])
		.filter(([, count]) => count !== 0)
		.map(([dbfId, count, owner]): SideboardCard => [dbfId, count, owner])
		.sort(
			([leftId, , leftOwner], [rightId, , rightOwner]) =>
				leftOwner - rightOwner || leftId - rightId
		);

	return {
		format: source.format,
		heroes: [...source.heroes].sort((left, right) => left - right),
		cards,
		sideboardCards,
	};
}
