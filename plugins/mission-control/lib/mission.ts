import { createHash, randomUUID } from 'node:crypto'
import { closeSync, existsSync, fsyncSync, mkdirSync, openSync, readFileSync, renameSync, statSync, unlinkSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'

// Shared record I/O for contract mission records: bounded UTF-8 reads, the record lock with
// atomic replacement, and small value checks.
export function text(value: unknown): asserts value is string {
	if (typeof value !== 'string' || !value.trim()) throw new Error('Non-empty text required')
}
export function sha(value: unknown): asserts value is string {
	if (typeof value !== 'string' || !/^[a-f0-9]{40}$/.test(value)) throw new Error('Full Git SHA required')
}
export function digest(value: unknown) { return createHash('sha256').update(JSON.stringify(value)).digest('hex') }

export function readRecordBytes(path: string): string | undefined {
	if (!existsSync(path)) return undefined
	if (statSync(path).size > 16 * 1024 * 1024) throw new Error('Mission record exceeds 16 MiB; preserve and investigate')
	const bytes = readFileSync(path)
	if (bytes.length > 16 * 1024 * 1024) throw new Error('Mission record exceeds 16 MiB')
	const raw = bytes.toString('utf8')
	if (!Buffer.from(raw, 'utf8').equals(bytes)) throw new Error('Invalid UTF-8 mission bytes; preserve and investigate')
	return raw
}
// The one lock and atomic-replacement owner for mission records.
// An interrupted lock is never silently stolen. Inspect the writer first.
export function updateRecord(path: string, transform: (raw: string | undefined) => string) {
	mkdirSync(dirname(path), { recursive: true, mode: 0o700 })
	const lock = openSync(path + '.lock', 'wx', 0o600)
	const temporary = path + '.' + randomUUID()
	try {
		const next = transform(readRecordBytes(path))
		if (Buffer.byteLength(next) > 16 * 1024 * 1024) throw new Error('Mission record exceeds 16 MiB')
		const fd = openSync(temporary, 'wx', 0o600)
		try { writeFileSync(fd, next); fsyncSync(fd) } finally { closeSync(fd) }
		renameSync(temporary, path)
		const directory = openSync(dirname(path), 'r')
		try { fsyncSync(directory) } finally { closeSync(directory) }
	} finally {
		if (existsSync(temporary)) unlinkSync(temporary)
		closeSync(lock); unlinkSync(path + '.lock')
	}
}
