import typescript from "@rollup/plugin-typescript";
import { dts } from "rollup-plugin-dts";

const input = "src/index.ts";

/** @type {import("rollup").RollupOptions[]} */
export default [
	{
		input,
		output: [
			{
				file: "dist/index.js",
				format: "es",
				sourcemap: true,
			},
			{
				file: "dist/index.cjs",
				format: "cjs",
				exports: "named",
				sourcemap: true,
			},
		],
		plugins: [
			typescript({
				tsconfig: "./tsconfig.json",
				noEmit: false,
				declaration: false,
				declarationMap: false,
			}),
		],
	},
	{
		input,
		output: [
			{
				file: "dist/browser.js",
				format: "es",
				sourcemap: true,
			},
			{
				file: "dist/browser.umd.js",
				format: "umd",
				name: "ManacostDeckstrings",
				exports: "named",
				sourcemap: true,
			},
		],
		plugins: [
			typescript({
				tsconfig: "./tsconfig.json",
				noEmit: false,
				declaration: false,
				declarationMap: false,
			}),
		],
	},
	{
		input: "dist/types/index.d.ts",
		output: {
			file: "dist/index.d.ts",
			format: "es",
		},
		plugins: [dts()],
	},
];
