import assert from "node:assert/strict";
import {
	DeckstringError,
	FormatType,
	canonicalize,
	decode,
	encode,
	formatExport,
	parseExport,
	validate,
} from "@manacost-labs/deckstrings";

const input = {
	format: FormatType.FT_WILD,
	heroes: [7],
	cards: [
		[4, 1],
		[1, 2],
	],
	sideboardCards: [[5, 1, 90749]],
};

const canonical = canonicalize(input);
assert.deepEqual(canonical.cards, [
	[1, 2],
	[4, 1],
]);
assert.equal(validate(canonical).valid, true);

const deckstring = encode(canonical);
assert.deepEqual(decode(deckstring), canonical);

const parsed = parseExport(`### API example\n# Format: Wild\n#\n${deckstring}`);
assert.equal(parsed.metadata.name, "API example");
assert.equal(parsed.deckstring, deckstring);

const cards = new Map([
	[1, { name: "First Card", cost: 1 }],
	[4, { name: "Fourth Card", cost: 4 }],
	[5, { name: "Sideboard Card" }],
]);
const formatted = formatExport(
	parsed.deck,
	{ name: "API example", comments: ["Format: Wild"] },
	(dbfId) => cards.get(dbfId)
);
assert.match(formatted, /# 2x \(1\) First Card/);
assert.match(formatted, /# 1x \(0\) Sideboard Card \[sideboard:90749\]/);

try {
	decode("not-base64!");
	assert.fail("invalid input should throw");
} catch (error) {
	assert.ok(error instanceof DeckstringError);
	assert.equal(error.code, "invalid_base64");
}

console.log(formatted);
