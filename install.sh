#!/bin/sh
# contextkit bootstrap — installs the `contextkit` manager and its global doctrine.
#
#   curl -fsSL https://raw.githubusercontent.com/ai-cluster-one/context-kit/main/install.sh | sh
#
# Overrides:
#   CONTEXTKIT_TAG     fetch a different ref
#   CONTEXTKIT_HOME    manager root             (default ~/.contextkit)
#   CONTEXTKIT_BIN     PATH dir for the symlink (default ~/.local/bin or ~/bin)
#   CONTEXTKIT_SHA256  optionally verify the fetched manager script

set -eu

TAG="${CONTEXTKIT_TAG:-main}"
SHA256="${CONTEXTKIT_SHA256:-}"
REPO="https://raw.githubusercontent.com/ai-cluster-one/context-kit/$TAG"
CTX_HOME="${CONTEXTKIT_HOME:-$HOME/.contextkit}"
MANAGER_DIR="$CTX_HOME/.manager"
MANAGER="$MANAGER_DIR/contextkit"
DOCTRINE_DIR="$CTX_HOME/doctrine"
DOCTRINE_FILES="
runtime.md
guides/bootstrap.md
guides/authoring.md
guides/validation.md
guides/assets.md
guides/routines.md
guides/audit.md
guides/destructive.md
guides/migration.md
guides/hooks.md
guides/capabilities.md
"

err() { printf '%s\n' "$*" >&2; exit 1; }

command -v curl >/dev/null 2>&1 || err "curl is required"
command -v python3 >/dev/null 2>&1 || err "python3 is required"

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
printf '  fetch    %s/doctrine/*.md\n' "$REPO"
if [ -n "$SHA256" ]; then printf '  verify   sha256 %s\n' "$SHA256"; else printf '  verify   (no checksum pinned for ref %s)\n' "$TAG"; fi
printf '  place    %s\n' "$MANAGER"
printf '  doctrine %s\n' "$DOCTRINE_DIR"
printf '  symlink  %s/contextkit\n' "$BIN_DIR"

if (exec < /dev/tty) 2>/dev/null; then
    printf 'Proceed? [Y/n] '
    read -r answer < /dev/tty || answer=""
    case "$answer" in n*|N*) err "aborted";; esac
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
curl -fsSL "$REPO/bin/contextkit" -o "$tmp" || err "fetch failed: $REPO/bin/contextkit"

if [ -n "$SHA256" ]; then
    actual="$( (shasum -a 256 "$tmp" 2>/dev/null || sha256sum "$tmp") | cut -d' ' -f1 )"
    [ "$actual" = "$SHA256" ] || err "checksum mismatch: expected $SHA256, got $actual"
fi
head -1 "$tmp" | grep -q "python3" || err "fetched file does not look like the manager script"

mkdir -p "$MANAGER_DIR" "$BIN_DIR" "$DOCTRINE_DIR"
cp "$tmp" "$MANAGER"
chmod +x "$MANAGER"

for rel in $DOCTRINE_FILES; do
    dest="$DOCTRINE_DIR/$rel"
    mkdir -p "$(dirname "$dest")"
    curl -fsSL "$REPO/doctrine/$rel" -o "$dest" || err "fetch failed: $REPO/doctrine/$rel"
done

ln -sf "$MANAGER" "$BIN_DIR/contextkit"

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) printf 'NOTE: %s is not on PATH — add it so `contextkit` resolves by name.\n' "$BIN_DIR" >&2;;
esac

printf 'installed: %s -> %s\n' "$BIN_DIR/contextkit" "$MANAGER"
printf 'next:      contextkit init · contextkit build --target codex · contextkit doctor\n'
