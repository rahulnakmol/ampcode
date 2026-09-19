#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
thread_id='T-00000000-0000-0000-0000-000000000000'

command -v amp >/dev/null || {
	echo 'error: amp CLI is required' >&2
	exit 1
}

while IFS= read -r -d '' plugin; do
	echo "Checking plugin: ${plugin#"$root"/}"
	amp plugins exec "$plugin" session.start \
		--data "{\"thread\":{\"id\":\"$thread_id\"}}"
done < <(find "$root/plugins" -maxdepth 2 -type f \( -name '*.ts' -o -name '*.js' \) -print0)

while IFS= read -r -d '' skill; do
	directory=$(basename "$(dirname "$skill")")
	name=$(awk '
		/^---$/ { frontmatter++; next }
		frontmatter == 1 && /^name:[[:space:]]*/ {
			sub(/^name:[[:space:]]*/, "")
			print
			exit
		}
	' "$skill")
	description=$(awk '
		/^---$/ { frontmatter++; next }
		frontmatter == 1 && /^description:[[:space:]]*/ {
			sub(/^description:[[:space:]]*/, "")
			print
			exit
		}
	' "$skill")

	if [[ ! $name =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
		echo "error: $skill has an invalid skill name: $name" >&2
		exit 1
	fi
	if [[ $name != "$directory" ]]; then
		echo "error: $skill name '$name' does not match directory '$directory'" >&2
		exit 1
	fi
	if [[ -z $description ]]; then
		echo "error: $skill is missing a description" >&2
		exit 1
	fi
	done < <(find "$root/skills" -mindepth 2 -maxdepth 2 -type f -name SKILL.md -print0)

bun test "$root/tests"

git -C "$root" diff --check
echo 'All checks passed.'
