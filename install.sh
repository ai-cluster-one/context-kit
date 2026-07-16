#!/bin/sh
# contextkit bootstrap — installs the `contextkit` manager, runtime, guides, and templates.
#
#   curl -fsSL https://raw.githubusercontent.com/ai-cluster-one/context-kit/main/install.sh | sh
#
# Overrides:
#   CONTEXTKIT_REF     fetch a different ref (CONTEXTKIT_TAG is compatible)
#   CONTEXTKIT_RAW_BASE release source base         (default public raw repo)
#   CONTEXTKIT_HOME    manager root             (default ~/.contextkit)
#   CONTEXTKIT_BIN     PATH dir for the symlink (default ~/.local/bin or ~/bin)
#   CONTEXTKIT_SHA256  optionally verify the fetched manager script

set -eu

if [ "${CONTEXTKIT_REF+x}" = x ]; then
    TAG="$CONTEXTKIT_REF"
elif [ "${CONTEXTKIT_TAG+x}" = x ]; then
    TAG="$CONTEXTKIT_TAG"
else
    TAG="main"
fi
SHA256="${CONTEXTKIT_SHA256:-}"
if [ "${CONTEXTKIT_RAW_BASE+x}" = x ]; then
    RAW_BASE="$CONTEXTKIT_RAW_BASE"
else
    RAW_BASE="https://raw.githubusercontent.com/ai-cluster-one/context-kit"
fi
RAW_BASE="${RAW_BASE%/}"

err() { printf '%s\n' "$*" >&2; exit 1; }

command -v curl >/dev/null 2>&1 || err "curl is required"
command -v python3 >/dev/null 2>&1 || err "python3 is required"

if ! RAW_BASE="$(python3 - "$TAG" "$RAW_BASE" <<'PY'
import ipaddress
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

value = sys.argv[1]
valid = bool(value) and value == value.strip() and len(value) <= 200
valid = valid and not value.startswith("/") and not value.endswith("/") and "\\" not in value
valid = valid and not any(ord(char) < 32 for char in value)
for component in value.split("/") if valid else ():
    valid = valid and bool(re.fullmatch(r"[A-Za-z0-9_@+-][A-Za-z0-9._@+-]*", component))
    valid = valid and component not in {".", ".."}
    decoded = component
    for _ in range(3):
        next_value = urllib.parse.unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    valid = valid and decoded not in {".", ".."} and "/" not in decoded and "\\" not in decoded
if not valid:
    raise SystemExit(1)

source = sys.argv[2]
if not source or source != source.strip():
    raise SystemExit(1)
try:
    parsed = urllib.parse.urlsplit(source)
except (TypeError, ValueError):
    raise SystemExit(1)
if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
    raise SystemExit(1)
scheme = parsed.scheme.lower()
if scheme not in {"http", "https", "file"}:
    raise SystemExit(1)
if scheme == "file":
    if parsed.netloc not in {"", "localhost"}:
        raise SystemExit(1)
    try:
        local_path = Path(urllib.request.url2pathname(parsed.path))
    except (OSError, ValueError):
        raise SystemExit(1)
    if not local_path.is_absolute() or local_path == Path(local_path.anchor) or "\\" in parsed.path or any(ord(char) < 32 for char in parsed.path):
        raise SystemExit(1)
    try:
        print(local_path.resolve(strict=False).as_uri().rstrip("/"))
    except (OSError, ValueError):
        raise SystemExit(1)
    raise SystemExit(0)
if not parsed.netloc or parsed.path and not parsed.path.startswith("/"):
    raise SystemExit(1)
try:
    host = parsed.hostname
    port = parsed.port
except ValueError:
    raise SystemExit(1)
if not host or port is not None and not (1 <= port <= 65535):
    raise SystemExit(1)
try:
    if ":" in host:
        canonical_host = f"[{ipaddress.IPv6Address(host).compressed}]"
    else:
        try:
            canonical_host = str(ipaddress.IPv4Address(host))
        except ipaddress.AddressValueError:
            canonical_host = host.encode("idna").decode("ascii").lower()
            labels = canonical_host.split(".")
            if any(not label or len(label) > 63 or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label) for label in labels):
                raise ValueError("invalid host")
except (UnicodeError, ValueError, ipaddress.AddressValueError):
    raise SystemExit(1)
if "\\" in parsed.path or any(ord(char) < 32 for char in parsed.path):
    raise SystemExit(1)
netloc = canonical_host + (f":{port}" if port is not None else "")
print(urllib.parse.urlunsplit((scheme, netloc, parsed.path.rstrip("/"), "", "")))
PY
)"; then
    err "CONTEXTKIT_RAW_BASE or CONTEXTKIT_REF is invalid"
fi

REPO="$RAW_BASE/$TAG"
CTX_HOME="${CONTEXTKIT_HOME:-$HOME/.contextkit}"
MANAGER_DIR="$CTX_HOME/.manager"
MANAGER="$MANAGER_DIR/contextkit"
BUNDLE_DIR="$CTX_HOME/bundle"
GUIDES_DIR="$CTX_HOME/guides"
TEMPLATES_DIR="$CTX_HOME/templates"

if [ -n "${CONTEXTKIT_BIN:-}" ]; then
    BIN_DIR="$CONTEXTKIT_BIN"
else
    BIN_DIR="$HOME/.local/bin"
    for cand in "$HOME/.local/bin" "$HOME/bin"; do
        [ -d "$cand" ] || continue
        case ":$PATH:" in *":$cand:"*) BIN_DIR="$cand"; break;; esac
    done
fi

printf 'contextkit bootstrap — the plan:\n'
printf '  fetch    %s/bin/contextkit\n' "$REPO"
printf '  verify   %s/release.json and every shipped file\n' "$REPO"
if [ -n "$SHA256" ]; then printf '  verify   sha256 %s\n' "$SHA256"; else printf '  verify   (no checksum pinned for ref %s)\n' "$TAG"; fi
printf '  place    %s\n' "$MANAGER"
printf '  bundle   %s\n' "$BUNDLE_DIR"
printf '  guides   %s\n' "$GUIDES_DIR"
printf '  templates %s\n' "$TEMPLATES_DIR"
printf '  symlink  %s/contextkit\n' "$BIN_DIR"

if (exec < /dev/tty) 2>/dev/null; then
    printf 'Proceed? [Y/n] '
    read -r answer < /dev/tty || answer=""
    case "$answer" in n*|N*) err "aborted";; esac
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

max_attempts=3
attempt=0
while [ "$attempt" -lt "$max_attempts" ]; do
    attempt=$((attempt + 1))
    if curl -fsSL "$REPO/bin/contextkit" -o "$tmp"; then
        break
    fi
    if [ "$attempt" -lt "$max_attempts" ]; then
        case "$attempt" in
            1) sleep 0.5 ;;
            2) sleep 1 ;;
        esac
    else
        err "fetch failed after $max_attempts attempts: $REPO/bin/contextkit"
    fi
done

if [ -n "$SHA256" ]; then
    actual="$( (shasum -a 256 "$tmp" 2>/dev/null || sha256sum "$tmp") | cut -d' ' -f1 )"
    [ "$actual" = "$SHA256" ] || err "checksum mismatch: expected $SHA256, got $actual"
fi
head -1 "$tmp" | grep -q "python3" || err "fetched file does not look like the manager script"

CONTEXTKIT_HOME="$CTX_HOME" \
CONTEXTKIT_BIN="$BIN_DIR" \
CONTEXTKIT_RAW_BASE="$RAW_BASE" \
CONTEXTKIT_REF="$TAG" \
python3 "$tmp" update --apply --yes >/dev/null || err "ContextKit release installation failed"

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) printf 'NOTE: %s is not on PATH — add it so `contextkit` resolves by name.\n' "$BIN_DIR" >&2;;
esac

printf 'installed: %s -> %s\n' "$BIN_DIR/contextkit" "$MANAGER"
printf 'next:      contextkit bootstrap · contextkit init --with-layers · contextkit init --with-template\n'
