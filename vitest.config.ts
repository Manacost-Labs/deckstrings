import { playwright } from "@vitest/browser-playwright";
import { defineConfig } from "vitest/config";

export default defineConfig({
	test: {
		coverage: {
			provider: "v8",
			include: ["src/**/*.ts"],
			reporter: ["text", "json-summary", "html"],
			thresholds: {
				statements: 90,
				branches: 80,
				functions: 100,
				lines: 90,
			},
		},
		projects: [
			{
				test: {
					name: "unit",
					environment: "node",
					include: ["test/**/*.test.ts", "test/**/*.unit.test.ts"],
					exclude: ["test/**/*.browser.test.ts"],
				},
			},
			{
				test: {
					name: "browser",
					include: ["test/**/*.browser.test.ts"],
					browser: {
						enabled: true,
						headless: true,
						provider: playwright(),
						instances: [{ browser: "chromium" }],
					},
				},
			},
		],
	},
});
