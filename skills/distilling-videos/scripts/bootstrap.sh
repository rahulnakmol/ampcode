#!/usr/bin/env bash
# Idempotent local bootstrap for the distilling-videos runtime.
#
# - Verifies python3 >= 3.9 (the runtime itself uses only the standard library).
# - Creates a private virtualenv (default: ${XDG_CACHE_HOME:-~/.cache}/distilling-videos/venv)
#   and installs yt-dlp into it only when missing, or when --upgrade is given.
# - Checks ffmpeg/ffprobe and a Chromium-family browser and prints how to install what is missing.
#
# It never installs system or global packages, never uses sudo, never reads or writes credentials,
# and never publishes anything. Re-running it is safe and does no network work once yt-dlp exists.
#
# Usage: bootstrap.sh [--check] [--upgrade] [--venv DIR]
#   --check    only report; create and install nothing
#   --upgrade  upgrade yt-dlp inside the venv (YouTube extraction changes often)
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
		sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
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

# Private venv with yt-dlp ----------------------------------------------------
if [[ -x $venv/bin/yt-dlp ]]; then
	if $upgrade && ! $check_only; then
		"$venv/bin/python" -m pip install --quiet --disable-pip-version-check --upgrade yt-dlp
	fi
	say ok "yt-dlp $("$venv/bin/yt-dlp" --version) in $venv"
elif $check_only; then
	if command -v yt-dlp >/dev/null; then
		say ok "yt-dlp $(yt-dlp --version) on PATH (no private venv yet)"
	else
		say missing "yt-dlp (run bootstrap.sh without --check to install it into $venv)"
		missing+=(yt-dlp)
	fi
else
	[[ -x $venv/bin/python ]] || "$python" -m venv "$venv"
	"$venv/bin/python" -m pip install --quiet --disable-pip-version-check yt-dlp
	say ok "yt-dlp $("$venv/bin/yt-dlp" --version) installed in $venv"
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
	echo "Install the missing tools yourself, then rerun this script:"
	echo '  macOS:            brew install ffmpeg'
	echo '  Debian/orb setup: sudo apt-get install -y ffmpeg'
	exit 3
fi

if [[ -x $venv/bin/yt-dlp ]]; then
	echo
	echo "Ready. Put yt-dlp on PATH for this shell before running distill.py:"
	printf '  export PATH=%q:"$PATH"\n' "$venv/bin"
fi
