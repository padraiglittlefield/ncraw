#!/usr/bin/env bash
# install.sh — installs ncraw and its man page

set -euo pipefail

BIN_DIR="/usr/local/bin"
MAN_DIR="/usr/local/share/man/man1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─── Helpers ──────────────────────────────────────────────────────────────────

ok()  { echo "  ok: $*"; }
err() { echo "  error: $*" >&2; exit 1; }
msg() { echo "$*"; }

# ─── Checks ───────────────────────────────────────────────────────────────────

msg ""
msg "NiteCrawler Focuser — installer"
msg ""

# Must be run as root
if [[ "$EUID" -ne 0 ]]; then
    err "This installer must be run with sudo.

  Try:  sudo bash install.sh"
fi

# Required files must be present alongside this script
[[ -f "$SCRIPT_DIR/ncraw" ]]      || err "ncraw not found in $SCRIPT_DIR — make sure ncraw and install.sh are in the same folder."
[[ -f "$SCRIPT_DIR/ncraw.1" ]]    || err "ncraw.1 not found in $SCRIPT_DIR — make sure ncraw.1 and install.sh are in the same folder."

# ─── Install ──────────────────────────────────────────────────────────────────

msg "Installing..."
msg ""

# Install the command
install -m 755 "$SCRIPT_DIR/ncraw" "$BIN_DIR/ncraw"
ok "ncraw installed to $BIN_DIR/ncraw"

# Install the man page
mkdir -p "$MAN_DIR"
install -m 644 "$SCRIPT_DIR/ncraw.1" "$MAN_DIR/ncraw.1"
ok "man page installed to $MAN_DIR/ncraw.1"

# Rebuild the man page index so 'man ncraw' works immediately
if command -v mandb &>/dev/null; then
    mandb -q
    ok "man page index updated"
fi

# Offer to add the user to the dialout group if not already a member
REAL_USER="${SUDO_USER:-}"
if [[ -n "$REAL_USER" ]]; then
    if ! id -nG "$REAL_USER" | grep -qw dialout; then
        msg ""
        msg "  Your user ($REAL_USER) is not in the 'dialout' group."
        msg "  Without this, ncraw cannot open the USB serial port."
        msg ""
        read -r -p "  Add $REAL_USER to dialout now? [Y/n] " answer
        answer="${answer:-Y}"
        answer=$(printf '%s' "$answer" | tr '[:lower:]' '[:upper:]')
        if [[ "$answer" == "Y" ]]; then
            usermod -aG dialout "$REAL_USER"
            ok "$REAL_USER added to dialout"
            msg ""
            msg "  IMPORTANT: You must log out and back in for this to take effect."
        else
            msg ""
            msg "  Skipped. You can do this later with:"
            msg "    sudo usermod -aG dialout $REAL_USER"
        fi
    else
        ok "$REAL_USER already in dialout group"
    fi
fi

# ─── Done ─────────────────────────────────────────────────────────────────────

msg ""
msg "Done. Try it:"
msg ""
msg "  ncraw where"
msg "  ncraw help"
msg ""