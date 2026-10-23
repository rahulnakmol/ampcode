#!/usr/bin/env bash
# Idempotent local bootstrap for the distilling-videos runtime.
#
# - Verifies python3 >= 3.9 (the runtime itself uses only the standard library).
# - Creates a private virtualenv (default: ${XDG_CACHE_HOME:-~/.cache}/distilling-videos/venv)
#   and installs "yt-dlp[default]" into it only when missing, or when --upgrade is given. The
#   `default` extra supplies yt-dlp-ejs (the YouTube challenge solver scripts); a venv whose yt-dlp
#   lacks the yt_dlp_ejs module is repaired by installing the extra (--check only reports it).
# - Checks ffmpeg/ffprobe and a Chromium-family browser and prints how to install what is missing.
# - Reports the JavaScript runtime yt-dlp needs for YouTube (deno >= 2.3.0 is yt-dlp's default;
#   node >= 22 or quickjs need `distill.py download --js-runtime NAME`). It never edits yt-dlp config.
#
# It never installs system or global packages, never uses sudo, never reads or writes credentials,
# and never publishes anything. Re-running it is safe and does no network work once yt-dlp and
# yt-dlp-ejs exist in the venv.
#
# Usage: bootstrap.sh [--check] [--upgrade] [--venv DIR]
#   --check    only report; create and install nothing
#   --upgrade  upgrade yt-dlp[default] inside the venv (YouTube extraction changes often)
#   --venv DIR use DIR instead of the default venv (or set DISTILL_VENV)
# Set DISTILL_PYTHON to choose the interpreter used to create the venv (default python3).
#
# Exit codes: 0 ready, 2 usage error, 3 a required tool is missing (matches distill.py).
set -euo pipefail

python=${DISTILL_PYTHON:-python3}
venv=${DISTILL_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/distilling-videos/venv}
check_only=false
upgrade=false

while (($#)); do
	case $1 in
	--check) check_only=true ;;
	--upgrade) upgrade=true ;;
	--venv)
		[[ $# -ge 2 ]] || {
			echo 'error: --venv needs a directory' >&2
			exit 2
		}
		venv=$2
		shift
		;;
	-h | --help)
		sed -n '2,21p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
		exit 0
		;;
	*)
		echo "error: unknown argument: $1" >&2
		exit 2
		;;
	esac
	shift
done

missing=()
say() { printf '%-10s %s\n' "$1" "$2"; }

# Python 3.9+ ---------------------------------------------------------------
if ! command -v "$python" >/dev/null; then
	say missing "$python (Python 3.9 or newer)"
	exit 3
fi
if ! "$python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
	say missing "Python >= 3.9 (found $("$python" -V 2>&1))"
	exit 3
fi
say ok "$("$python" -V 2>&1)"
if ! "$python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
	say warning 'current yt-dlp releases need Python 3.10+; pip will pick an older yt-dlp that may fail on YouTube'
	say '' 'set DISTILL_PYTHON to a newer interpreter and recreate the venv if downloads fail'
fi

# Private venv with yt-dlp[default] -------------------------------------------
# A bare `pip install yt-dlp` has no challenge solver scripts; upstream's PyPI instructions are
# `pip install -U "yt-dlp[default]"`, whose default extra includes yt-dlp-ejs (module yt_dlp_ejs).
pip_install() { "$venv/bin/python" -m pip install --quiet --disable-pip-version-check "$@" 'yt-dlp[default]'; }
has_ejs() { "$venv/bin/python" -c 'import yt_dlp_ejs' >/dev/null 2>&1; }
if [[ -x $venv/bin/yt-dlp ]]; then
	if $upgrade && ! $check_only; then
		pip_install --upgrade
	elif ! $check_only && ! has_ejs; then
		say repair "yt-dlp-ejs is missing from $venv; installing yt-dlp[default]"
		pip_install
	fi
	say ok "yt-dlp $("$venv/bin/yt-dlp" --version) in $venv"
elif $check_only; then
	if command -v yt-dlp >/dev/null; then
		say ok "yt-dlp $(yt-dlp --version) on PATH (no private venv yet)"
		say warning 'cannot check yt-dlp-ejs for a yt-dlp outside the venv; pip installs need yt-dlp[default]'
	else
		say missing "yt-dlp (run bootstrap.sh without --check to install it into $venv)"
		missing+=(yt-dlp)
	fi
else
	[[ -x $venv/bin/python ]] || "$python" -m venv "$venv"
	pip_install
	say ok "yt-dlp $("$venv/bin/yt-dlp" --version) installed in $venv"
fi
if [[ -x $venv/bin/yt-dlp ]]; then
	if has_ejs; then
		say ok "yt-dlp-ejs in $venv"
	elif $check_only; then
		say missing "yt-dlp-ejs (run bootstrap.sh without --check to install yt-dlp[default] into $venv)"
		missing+=(yt-dlp-ejs)
	else
		say missing "yt-dlp-ejs (pip install 'yt-dlp[default]' did not provide yt_dlp_ejs in $venv)"
		missing+=(yt-dlp-ejs)
	fi
fi

# JavaScript runtime for YouTube challenges (yt-dlp EJS) ------------------------
# Upstream: https://github.com/yt-dlp/yt-dlp/wiki/EJS. The solver scripts come from yt-dlp-ejs
# (above); a runtime executes them. Only deno is enabled by default in yt-dlp;
# distill.py runs yt-dlp with --ignore-config, so choose another runtime with --js-runtime, not a config file.
version_at_least() {
	"$python" -c 'import re, sys
have = [int(x) for x in re.findall(r"\d+", sys.argv[1])[:3]]
need = [int(x) for x in sys.argv[2].split(".")]
sys.exit(0 if have and have >= need else 1)' "$1" "$2"
}
js_runtime=''
for spec in deno:deno:2.3.0 node:node:22.0.0; do
	IFS=: read -r name exe minimum <<<"$spec"
	command -v "$exe" >/dev/null || continue
	version=$("$exe" --version 2>/dev/null </dev/null | awk 'NR == 1 { print ($1 == "deno" ? $2 : $1) }')
	if version_at_least "$version" "$minimum"; then
		if [[ $name == deno ]]; then
			say ok "js-runtime deno $version (yt-dlp default; no flag needed)"
		else
			say ok "js-runtime node $version: pass --js-runtime node to distill.py download"
		fi
		js_runtime=$name
		break
	fi
	say warning "js-runtime $name $version is too old (yt-dlp needs $minimum or newer)"
done
if [[ -z $js_runtime ]] && command -v qjs >/dev/null; then
	say ok 'js-runtime quickjs (qjs): pass --js-runtime quickjs to distill.py download'
	js_runtime=quickjs
fi
if [[ -z $js_runtime ]]; then
	say warning 'no supported JavaScript runtime for yt-dlp: YouTube downloads may fail (for example HTTP 403)'
	say '' 'install deno 2.3+ (recommended) or node 22+; see https://github.com/yt-dlp/yt-dlp/wiki/EJS'
fi

# FFmpeg (system tool; never installed here) ---------------------------------
for tool in ffmpeg ffprobe; do
	if command -v "$tool" >/dev/null; then
		say ok "$tool $("$tool" -version 2>/dev/null | awk 'NR == 1 { print $3 }')"
	else
		say missing "$tool"
		missing+=("$tool")
	fi
done

# Chromium-family browser for `distill.py pdf` (optional) ---------------------
browser=${DISTILL_BROWSER:-}
if [[ -z $browser ]]; then
	for name in chromium chromium-browser google-chrome google-chrome-stable microsoft-edge msedge brave-browser; do
		if command -v "$name" >/dev/null; then
			browser=$(command -v "$name")
			break
		fi
	done
fi
if [[ -z $browser ]]; then
	for app in '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
		'/Applications/Chromium.app/Contents/MacOS/Chromium' \
		'/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge' \
		'/Applications/Brave Browser.app/Contents/MacOS/Brave Browser' \
		'/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary'; do
		if [[ -x $app ]]; then
			browser=$app
			break
		fi
	done
fi
if [[ -n $browser ]]; then
	say ok "browser $browser"
else
	say optional 'no Chromium-family browser: `distill.py pdf` will exit 3 (package needs --allow-missing-pdf)'
fi

if ((${#missing[@]})); then
	echo
	echo "Install the missing tools, then rerun this script:"
	if [[ " ${missing[*]} " == *' ff'* ]]; then
		echo '  macOS:            brew install ffmpeg'
		echo '  Debian/orb setup: sudo apt-get install -y ffmpeg'
	fi
	if [[ " ${missing[*]} " == *' yt-dlp'* ]]; then
		echo "  yt-dlp:           bootstrap.sh (without --check) installs yt-dlp[default] into $venv"
	fi
	exit 3
fi

if [[ -x $venv/bin/yt-dlp ]]; then
	echo
	echo "Ready. Put yt-dlp on PATH for this shell before running distill.py:"
	printf '  export PATH=%q:"$PATH"\n' "$venv/bin"
fi
