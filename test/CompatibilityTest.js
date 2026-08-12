/*#if _PLATFORM === "browser"
// Cross-language fixtures exercise backend packages and run in Node.js.
//#else */
const fs = require("fs");
const path = require("path");
const { expect } = require("chai");
const { DeckstringError, decode, encode } = require("../dist/index");

const fixtures = JSON.parse(
	fs.readFileSync(
		path.join(__dirname, "../fixtures/deckstrings.json"),
		"utf8"
	)
);

describe("cross-language compatibility fixtures", () => {
	for (const fixture of fixtures.valid) {
		it(`${fixture.name} decodes to the canonical definition`, () => {
			expect(decode(fixture.deckstring)).to.deep.equal(fixture.deck);
		});

		it(`${fixture.name} encodes to the canonical deckstring`, () => {
			const expected = fixture.canonicalDeckstring || fixture.deckstring;
			expect(encode(fixture.deck)).to.equal(expected);
			expect(encode(decode(fixture.deckstring))).to.equal(expected);
		});
	}

	for (const fixture of fixtures.invalid) {
		it(`${fixture.name} returns ${fixture.errorCode}`, () => {
			try {
				decode(fixture.deckstring);
				expect.fail("Expected decode to throw");
			} catch (error) {
				expect(error).to.be.instanceOf(DeckstringError);
				expect(error.code).to.equal(fixture.errorCode);
			}
		});
	}
});
//#endif
