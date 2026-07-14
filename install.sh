#!/bin/sh
# contextkit bootstrap — installs the `contextkit` manager, runtime, guides, and templates.
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
BUNDLE_DIR="$CTX_HOME/bundle"
GUIDES_DIR="$CTX_HOME/guides"
TEMPLATES_DIR="$CTX_HOME/templates"
BUNDLE_FILES="
runtime.md
"
GUIDE_FILES="
bootstrap.md
authoring.md
agent-team.md
global-context.md
memory.md
validation.md
assets.md
routines.md
audit.md
destructive.md
migration.md
hooks.md
capabilities.md
"
TEMPLATE_FILES="
README.md
context/identity/MISSION.md
context/identity/AGENT.md
context/identity/OWNER.md
context/identity/PEOPLE.md
context/guidelines/CONSTITUTION.md
context/guidelines/LIMITATIONS.md
context/guidelines/ASSETS.md
context/architecture/RUNTIME.md
context/architecture/SERVICES.md
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
printf '  fetch    %s/bundle/*.md\n' "$REPO"
printf '  fetch    %s/guides/*.md\n' "$REPO"
printf '  fetch    %s/templates/...\n' "$REPO"
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
curl -fsSL "$REPO/bin/contextkit" -o "$tmp" || err "fetch failed: $REPO/bin/contextkit"

if [ -n "$SHA256" ]; then
    actual="$( (shasum -a 256 "$tmp" 2>/dev/null || sha256sum "$tmp") | cut -d' ' -f1 )"
    [ "$actual" = "$SHA256" ] || err "checksum mismatch: expected $SHA256, got $actual"
fi
head -1 "$tmp" | grep -q "python3" || err "fetched file does not look like the manager script"

mkdir -p "$MANAGER_DIR" "$BIN_DIR" "$BUNDLE_DIR" "$GUIDES_DIR" "$TEMPLATES_DIR"
cp "$tmp" "$MANAGER"
chmod +x "$MANAGER"

for rel in $BUNDLE_FILES; do
    dest="$BUNDLE_DIR/$rel"
    mkdir -p "$(dirname "$dest")"
    curl -fsSL "$REPO/bundle/$rel" -o "$dest" || err "fetch failed: $REPO/bundle/$rel"
done

for rel in $GUIDE_FILES; do
    dest="$GUIDES_DIR/$rel"
    mkdir -p "$(dirname "$dest")"
    curl -fsSL "$REPO/guides/$rel" -o "$dest" || err "fetch failed: $REPO/guides/$rel"
done

for rel in $TEMPLATE_FILES; do
    dest="$TEMPLATES_DIR/$rel"
    mkdir -p "$(dirname "$dest")"
    curl -fsSL "$REPO/templates/$rel" -o "$dest" || err "fetch failed: $REPO/templates/$rel"
done

ln -sf "$MANAGER" "$BIN_DIR/contextkit"

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) printf 'NOTE: %s is not on PATH — add it so `contextkit` resolves by name.\n' "$BIN_DIR" >&2;;
esac

printf 'installed: %s -> %s\n' "$BIN_DIR/contextkit" "$MANAGER"
printf 'next:      contextkit bootstrap · contextkit init --with-layers · contextkit init --with-template\n'
