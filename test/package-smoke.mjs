import { execFileSync } from "node:child_process";
import {
	mkdtempSync,
	mkdirSync,
	readFileSync,
	rmSync,
	writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";

const root = fileURLToPath(new URL("..", import.meta.url));
const temporaryDirectory = mkdtempSync(join(tmpdir(), "deckstrings-package-"));
const packageDirectory = join(temporaryDirectory, "consumer");

try {
	mkdirSync(packageDirectory);
	const packResult = JSON.parse(
		execFileSync(
			"npm",
			[
				"pack",
				"--ignore-scripts",
				"--json",
				"--pack-destination",
				temporaryDirectory,
			],
			{ cwd: root, encoding: "utf8" }
		)
	);
	const packed = packResult[0];
	if (!packed?.filename || !Array.isArray(packed.files)) {
		throw new Error("npm pack did not return package metadata");
	}
	const unexpected = packed.files
		.map(({ path }) => path)
		.filter((path) => path.startsWith("src/") || path.startsWith("test/"));
	if (unexpected.length > 0) {
		throw new Error(
			`package contains source-only files: ${unexpected.join(", ")}`
		);
	}

	writeFileSync(
		join(packageDirectory, "package.json"),
		JSON.stringify({ private: true, type: "module" })
	);
	const tarball = join(temporaryDirectory, packed.filename);
	execFileSync(
		"npm",
		["install", "--ignore-scripts", "--no-audit", "--no-fund", tarball],
		{ cwd: packageDirectory, stdio: "pipe" }
	);

	const esmConsumer = join(packageDirectory, "esm.mjs");
	writeFileSync(
		esmConsumer,
		`import { decode, encode } from "@manacost-labs/deckstrings";
import * as browser from "@manacost-labs/deckstrings/browser";
const value = "AAEBAQcBBAMBAgMAAA==";
if (encode(decode(value)) !== value || browser.encode(browser.decode(value)) !== value) process.exit(1);`
	);
	execFileSync(process.execPath, [esmConsumer], {
		cwd: packageDirectory,
		stdio: "pipe",
	});

	const cjsConsumer = join(packageDirectory, "cjs.cjs");
	writeFileSync(
		cjsConsumer,
		`const { decode, encode } = require("@manacost-labs/deckstrings");
const value = "AAEBAQcBBAMBAgMAAA==";
if (encode(decode(value)) !== value) process.exit(1);`
	);
	execFileSync(process.execPath, [cjsConsumer], {
		cwd: packageDirectory,
		stdio: "pipe",
	});

	const declaration = readFileSync(
		join(
			packageDirectory,
			"node_modules/@manacost-labs/deckstrings/dist/index.d.ts"
		),
		"utf8"
	);
	if (
		!declaration.includes("canonicalize") ||
		!declaration.includes("formatExport")
	) {
		throw new Error("published declarations are incomplete");
	}

	const typeConsumer = join(packageDirectory, "consumer.ts");
	writeFileSync(
		typeConsumer,
		`import { canonicalize, formatExport, FormatType, validate, type CardResolver, type DeckDefinition, type FormatType as FormatTypeValue } from "@manacost-labs/deckstrings";
const format: FormatTypeValue = 1;
const deck: DeckDefinition = { format, heroes: [7], cards: [[1, 1]] };
if (deck.format !== FormatType.FT_WILD) throw new Error("format type/value mismatch");
const resolver: CardResolver = (dbfId) => ({ name: String(dbfId), cost: 1 });
validate(deck);
formatExport(canonicalize(deck), { name: "Typed" }, resolver);`
	);
	writeFileSync(
		join(packageDirectory, "tsconfig.json"),
		JSON.stringify({
			compilerOptions: {
				module: "NodeNext",
				moduleResolution: "NodeNext",
				strict: true,
				noEmit: true,
				types: [],
			},
			include: ["consumer.ts"],
		})
	);
	execFileSync(
		process.execPath,
		[
			join(root, "node_modules/typescript/bin/tsc"),
			"--project",
			join(packageDirectory, "tsconfig.json"),
		],
		{ cwd: packageDirectory, stdio: "pipe" }
	);

	const umdSource = readFileSync(
		join(
			packageDirectory,
			"node_modules/@manacost-labs/deckstrings/dist/browser.umd.js"
		),
		"utf8"
	);
	const browserContext = { atob: globalThis.atob, btoa: globalThis.btoa };
	runInNewContext(umdSource, browserContext);
	const browserGlobal = browserContext.ManacostDeckstrings;
	if (
		!browserGlobal ||
		browserGlobal.encode(browserGlobal.decode("AAEBAQcBBAMBAgMAAA==")) !==
			"AAEBAQcBBAMBAgMAAA=="
	) {
		throw new Error("UMD browser bundle smoke failed");
	}

	console.log(
		"package smoke passed: ESM, CommonJS, browser ESM, UMD, and types"
	);
} finally {
	rmSync(temporaryDirectory, { recursive: true, force: true });
}
