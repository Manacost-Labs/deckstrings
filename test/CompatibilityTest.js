const fs = require("fs");
const path = require("path");
const { expect } = require("chai");
const { decode, encode } = require("../dist/index");

const fixtures = JSON.parse(
	fs.readFileSync(
		path.join(__dirname, "../fixtures/deckstrings.json"),
		"utf8"
	)
).valid;

describe("cross-language compatibility fixtures", () => {
	for (const fixture of fixtures) {
		it(`${fixture.name} decodes to the canonical definition`, () => {
			expect(decode(fixture.deckstring)).to.deep.equal(fixture.deck);
		});

		it(`${fixture.name} encodes to the canonical deckstring`, () => {
			const expected = fixture.canonicalDeckstring || fixture.deckstring;
			expect(encode(fixture.deck)).to.equal(expected);
			expect(encode(decode(fixture.deckstring))).to.equal(expected);
		});
	}
});
