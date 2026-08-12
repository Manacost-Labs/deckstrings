import { describe, expect, it } from "vitest";
import { decode, encode } from "../src/index";

const DECKSTRING = "AAEBAQcBBAMBAgMAAA==";

describe("browser codec", () => {
	it("round-trips using browser Base64 globals", () => {
		const decoded = decode(DECKSTRING);
		expect(decoded.heroes).toEqual([7]);
		expect(encode(decoded)).toBe(DECKSTRING);
	});
});
