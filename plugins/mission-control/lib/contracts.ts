import { createHash } from 'node:crypto'

export function object(value: unknown, required: string[], optional: string[] = []): asserts value is Record<string, any> {
	if (!value || typeof value !== 'object' || Array.isArray(value) || ![Object.prototype, null].includes(Object.getPrototypeOf(value))) throw new Error('Object required')
	if (required.some(k => !Object.hasOwn(value, k)) || Object.keys(value).some(k => !required.includes(k) && !optional.includes(k))) throw new Error('Missing or unknown fields')
}
export function prose(value: unknown): asserts value is string {
	if (typeof value !== 'string' || !value.trim() || Buffer.byteLength(value) > 16 * 1024) throw new Error('Non-empty text up to 16 KiB required')
}
export function identity(value: unknown): asserts value is string {
	if (typeof value !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(value)) throw new Error('Invalid identity')
}
export function list(value: unknown, empty = false): asserts value is any[] {
	if (!Array.isArray(value) || (!empty && !value.length) || value.length > 1000) throw new Error('Bounded list required')
}
export function strings(value: unknown, empty = false): asserts value is string[] {
	list(value, empty); value.forEach(prose)
	if (new Set(value).size !== value.length) throw new Error('Duplicate values')
}
export function canonical(value: unknown, depth = 0): string {
	if (depth > 32) throw new Error('JSON nesting exceeds limit')
	if (value === null || typeof value === 'boolean' || typeof value === 'string') return JSON.stringify(value)
	if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value)
	if (Array.isArray(value)) return '[' + Array.from(value, item => canonical(item, depth + 1)).join(',') + ']'
	if (value && typeof value === 'object' && [Object.prototype, null].includes(Object.getPrototypeOf(value))) {
		return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical((value as any)[key], depth + 1)).join(',') + '}'
	}
	throw new Error('Only finite JSON values are supported')
}
export function intentDigest(value: unknown) { return createHash('sha256').update(canonical(value)).digest('hex') }
