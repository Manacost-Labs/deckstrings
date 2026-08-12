/** @internal */
function atobBinary(encoded: string): string {
	return globalThis.atob(encoded);
}

/** @internal */
function btoaBinary(decoded: string): string {
	return globalThis.btoa(decoded);
}

export { atobBinary as atob, btoaBinary as btoa };
