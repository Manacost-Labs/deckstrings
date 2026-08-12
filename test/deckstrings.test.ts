import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
	DeckstringError,
	FormatType,
	canonicalize,
	decode,
	encode,
	formatExport,
	parseExport,
	validate,
} from "../src/index";
import type {
	DeckDefinition,
	DeckstringErrorCode,
	ExportMetadata,
} from "../src/index";

interface DeckstringFixtures {
	valid: Array<{
		name: string;
		deckstring: string;
		canonicalDeckstring?: string;
		deck: Required<DeckDefinition>;
	}>;
	invalid: Array<{
		name: string;
		deckstring: string;
		errorCode: DeckstringErrorCode;
	}>;
}

interface ApiFixtures {
	canonicalize: Array<{
		name: string;
		deck: DeckDefinition;
		expectedDeck?: Required<DeckDefinition>;
		errorCode?: DeckstringErrorCode;
	}>;
	validate: Array<{
		name: string;
		deck: unknown;
		valid: boolean;
		errors: Array<{ code: DeckstringErrorCode; path: string }>;
	}>;
}

interface ExportFixtures {
	valid: Array<{
		name: string;
		text: string;
		parsed: {
			deck: Required<DeckDefinition>;
			deckstring: string;
			metadata: ExportMetadata;
		};
		formatted: string;
	}>;
	invalid: Array<{
		name: string;
		text: string;
		errorCode: DeckstringErrorCode;
	}>;
	resolver: {
		valid: Array<{
			name: string;
			deck: DeckDefinition;
			metadata: ExportMetadata;
			cards: Record<string, { name: string; cost?: number } | null>;
			formatted: string;
		}>;
		invalid: Array<{
			name: string;
			deck: DeckDefinition;
			cards: Record<string, { name: string; cost?: number } | null>;
			errorCode: DeckstringErrorCode;
		}>;
	};
}

function readFixture<T>(relativePath: string): T {
	return JSON.parse(
		readFileSync(new URL(relativePath, import.meta.url), "utf8")
	) as T;
}

const deckstringFixtures = readFixture<DeckstringFixtures>(
	"../fixtures/deckstrings.json"
);
const apiFixtures = readFixture<ApiFixtures>("../fixtures/api.json");
const exportFixtures = readFixture<ExportFixtures>("../fixtures/exports.json");

describe("deckstring codec", () => {
	for (const fixture of deckstringFixtures.valid) {
		it(`decodes ${fixture.name}`, () => {
			expect(decode(fixture.deckstring)).toEqual(fixture.deck);
		});

		it(`canonically encodes ${fixture.name}`, () => {
			const expected = fixture.canonicalDeckstring ?? fixture.deckstring;
			expect(encode(fixture.deck)).toBe(expected);
			expect(encode(decode(fixture.deckstring))).toBe(expected);
		});
	}

	for (const fixture of deckstringFixtures.invalid) {
		it(`returns ${fixture.errorCode} for ${fixture.name}`, () => {
			try {
				decode(fixture.deckstring);
				expect.fail("expected decode to throw");
			} catch (error) {
				expect(error).toBeInstanceOf(DeckstringError);
				expect((error as DeckstringError).code).toBe(fixture.errorCode);
			}
		});
	}

	it("preserves the public format constants", () => {
		expect(FormatType).toEqual({
			FT_WILD: 1,
			FT_STANDARD: 2,
			FT_CLASSIC: 3,
			FT_TWIST: 4,
		});
	});

	it("rejects a decoded payload larger than one mebibyte", () => {
		const oversized = Buffer.alloc(1024 * 1024 + 1).toString("base64");
		expect(() => decode(oversized)).toThrowError(
			expect.objectContaining({ code: "limit_exceeded" })
		);
	});
});

describe("canonicalize", () => {
	for (const fixture of apiFixtures.canonicalize) {
		it(fixture.name, () => {
			if (fixture.errorCode) {
				try {
					canonicalize(fixture.deck);
					expect.fail("expected canonicalize to throw");
				} catch (error) {
					expect(error).toBeInstanceOf(DeckstringError);
					expect((error as DeckstringError).code).toBe(
						fixture.errorCode
					);
				}
				return;
			}
			expect(canonicalize(fixture.deck)).toEqual(fixture.expectedDeck);
		});
	}

	it("does not mutate caller-owned arrays", () => {
		const deck: DeckDefinition = {
			format: 1,
			heroes: [10, 2],
			cards: [
				[4, 1],
				[3, 2],
			],
			sideboardCards: [[7, 1, 10]],
		};
		const snapshot = structuredClone(deck);
		canonicalize(deck);
		expect(deck).toEqual(snapshot);
	});
});

describe("validate", () => {
	for (const fixture of apiFixtures.validate) {
		it(fixture.name, () => {
			const result = validate(fixture.deck);
			expect(result.valid).toBe(fixture.valid);
			expect(
				result.errors.map(({ code, path }) => ({ code, path }))
			).toEqual(fixture.errors);
			for (const error of result.errors) {
				expect(error.message.length).toBeGreaterThan(0);
			}
		});
	}

	it("returns a result instead of throwing for arbitrary input", () => {
		expect(validate(null).valid).toBe(false);
		expect(validate("not a deck").valid).toBe(false);
	});

	it("rejects unknown deck properties", () => {
		const deck = {
			...deckstringFixtures.valid[0]!.deck,
			unexpected: true,
		};
		expect(validate(deck)).toEqual({
			valid: false,
			errors: [
				{
					code: "invalid_deck",
					path: "unexpected",
					message: "deck contains an unknown property",
				},
			],
		});
	});

	it("bounds validation errors for excessive top-level properties", () => {
		const deck = Object.fromEntries(
			Array.from({ length: 17 }, (_, index) => [`field${index}`, index])
		);
		expect(validate(deck)).toEqual({
			valid: false,
			errors: [
				{
					code: "limit_exceeded",
					path: "",
					message: "deck contains too many properties",
				},
			],
		});
	});

	it("rejects sparse deck arrays instead of skipping holes", () => {
		const cards = Array<DeckDefinition["cards"][number]>(1);
		const heroes = Array<number>(1);
		expect(
			validate({ format: 1, heroes: [7], cards, sideboardCards: [] })
				.errors[0]
		).toMatchObject({ code: "invalid_deck", path: "cards[0]" });
		expect(
			validate({ format: 1, heroes, cards: [], sideboardCards: [] })
				.errors[0]
		).toMatchObject({ code: "invalid_id", path: "heroes[0]" });
		expect(() =>
			canonicalize({
				format: 1,
				heroes: [7],
				cards,
				sideboardCards: [],
			})
		).toThrowError(expect.objectContaining({ code: "invalid_deck" }));
	});

	it("applies the item limit to each encoded count group", () => {
		const cards: DeckDefinition["cards"] = [];
		for (let index = 1; index <= 6_000; index++) {
			cards.push([index, 1], [index + 6_000, 2]);
		}
		expect(
			validate({ format: 1, heroes: [7], cards, sideboardCards: [] })
		).toEqual({ valid: true, errors: [] });

		cards.push(
			...[...Array(4_001)].map(
				(_, index): DeckDefinition["cards"][number] => [
					12_001 + index,
					1,
				]
			)
		);
		expect(
			validate({ format: 1, heroes: [7], cards, sideboardCards: [] })
				.errors
		).toContainEqual(
			expect.objectContaining({ code: "limit_exceeded", path: "cards" })
		);
	});
});

describe("clipboard exports", () => {
	for (const fixture of exportFixtures.valid) {
		it(`parses ${fixture.name}`, () => {
			expect(parseExport(fixture.text)).toEqual(fixture.parsed);
		});

		it(`formats ${fixture.name}`, () => {
			expect(
				formatExport(fixture.parsed.deck, fixture.parsed.metadata)
			).toBe(fixture.formatted);
		});
	}

	for (const fixture of exportFixtures.invalid) {
		it(`rejects ${fixture.name}`, () => {
			try {
				parseExport(fixture.text);
				expect.fail("expected parseExport to throw");
			} catch (error) {
				expect(error).toBeInstanceOf(DeckstringError);
				expect((error as DeckstringError).code).toBe(fixture.errorCode);
			}
		});
	}

	for (const fixture of exportFixtures.resolver.valid) {
		it(`formats shared resolver case ${fixture.name}`, () => {
			expect(
				formatExport(
					fixture.deck,
					fixture.metadata,
					(dbfId) => fixture.cards[String(dbfId)]
				)
			).toBe(fixture.formatted);
		});
	}

	for (const fixture of exportFixtures.resolver.invalid) {
		it(`rejects shared resolver case ${fixture.name}`, () => {
			expect(() =>
				formatExport(
					fixture.deck,
					{},
					(dbfId) => fixture.cards[String(dbfId)]
				)
			).toThrowError(
				expect.objectContaining({ code: fixture.errorCode })
			);
		});
	}

	it("rejects clipboard exports larger than the UTF-8 limit", () => {
		expect(() => parseExport("a".repeat(1_500_001))).toThrowError(
			expect.objectContaining({ code: "limit_exceeded" })
		);
		expect(() => parseExport("🔥".repeat(375_001))).toThrowError(
			expect.objectContaining({ code: "limit_exceeded" })
		);
		expect(() => parseExport(" ".repeat(1_500_001))).toThrowError(
			expect.objectContaining({ code: "limit_exceeded" })
		);
	});

	it("rejects malformed Unicode with a stable code", () => {
		expect(() => parseExport("\uD800")).toThrowError(
			expect.objectContaining({ code: "invalid_input" })
		);
	});

	it("adds resolved main and sideboard card lines", () => {
		const deck: DeckDefinition = {
			format: 1,
			heroes: [7],
			cards: [[4, 1]],
			sideboardCards: [[8, 2, 4]],
		};
		const names = new Map([
			[4, { name: "Main Card", cost: 3 }],
			[8, { name: "Side Card" }],
		]);
		const output = formatExport(
			deck,
			{ name: "Resolver Test", comments: ["Format: Wild"] },
			(dbfId) => names.get(dbfId)
		);
		expect(output).toContain("# 1x (3) Main Card");
		expect(output).toContain("# 2x (0) Side Card [sideboard:4]");
	});

	it("rejects invalid card resolver output", () => {
		const deck = deckstringFixtures.valid[0]!.deck;
		expect(() =>
			formatExport(deck, {}, () => ({ name: "Card", cost: -1 }))
		).toThrowError(expect.objectContaining({ code: "invalid_input" }));
		expect(() =>
			formatExport(deck, {}, () => ({ name: "", cost: 0 }))
		).toThrowError(expect.objectContaining({ code: "invalid_input" }));
		expect(() =>
			formatExport(deck, {}, () => ({ name: "   ", cost: 0 }))
		).toThrowError(expect.objectContaining({ code: "invalid_input" }));
	});

	it("rejects malformed export metadata with a stable code", () => {
		const deck = deckstringFixtures.valid[0]!.deck;
		for (const metadata of [
			null,
			{ name: 1 },
			{ comments: 1 },
			{ comments: null },
			{ comments: "ab" },
		]) {
			expect(() => formatExport(deck, metadata as never)).toThrowError(
				expect.objectContaining({ code: "invalid_input" })
			);
		}
	});
});
