import { createHash } from 'node:crypto'
import { closeSync, existsSync, fsyncSync, openSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { parseMission, updateRecord, type Mission } from './mission'
import { advanceV2, createMissionV2, legacyManifest, type MissionV2 } from './mission-v2'

export function sourceDigest(raw: string) { return createHash('sha256').update(raw).digest('hex') }
export function previewMigration(previous: Mission, repository?: string): MissionV2 {
	return advanceV2(createMissionV2(previous.thread, legacyManifest(previous, repository)), { type: 'import-v1', record: previous })
}
export function migrateMission(path: string, thread: string, expectedDigest: string, repository?: string): MissionV2 {
	let migrated: MissionV2 | undefined
	updateRecord(path, raw => {
		if (raw === undefined || sourceDigest(raw) !== expectedDigest) throw new Error('Migration source changed; preview again')
		migrated = previewMigration(parseMission(JSON.parse(raw), thread), repository)
		const backup = path + '.v1-' + expectedDigest + '.json'
		if (existsSync(backup)) {
			if (readFileSync(backup, 'utf8') !== raw) throw new Error('Existing migration backup differs; preserve and investigate')
		} else {
			const fd = openSync(backup, 'wx', 0o400)
			try { writeFileSync(fd, raw); fsyncSync(fd) } finally { closeSync(fd) }
		}
		// Persist the backup directory entry before replacing the only live v1 copy.
		const directory = openSync(dirname(path), 'r')
		try { fsyncSync(directory) } finally { closeSync(directory) }
		return JSON.stringify(migrated, null, 2) + '\n'
	})
	return migrated!
}
