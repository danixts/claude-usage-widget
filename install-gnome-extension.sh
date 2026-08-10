#!/usr/bin/env bash
set -euo pipefail

uuid='claude-codex-usage@danyjs'
target="$HOME/.local/share/gnome-shell/extensions/$uuid"
autostart_target="$HOME/.config/autostart/claude-usage-widget.desktop"
mkdir -p "$target" "$(dirname "$autostart_target")"
widget_command="$(command -v claude-usage)"
cp gnome-extension/$uuid/{extension.js,metadata.json,stylesheet.css,codex-icon.png} "$target/"

sed "s|^Exec=.*|Exec=$widget_command --detach|" autostart/claude-usage-widget.desktop > "$autostart_target"

python3 - "$uuid" <<'PYTHON'
import ast
import subprocess
import sys

uuid = sys.argv[1]
current = ast.literal_eval(
    subprocess.check_output(
        ["gsettings", "get", "org.gnome.shell", "enabled-extensions"], text=True
    ).strip()
)
if uuid not in current:
    current.append(uuid)
subprocess.run(
    ["gsettings", "set", "org.gnome.shell", "enabled-extensions", repr(current)],
    check=True,
)
PYTHON

printf 'Enabled %s and installed the widget login autostart entry. Log out and back in to load a newly installed extension.\n' "$uuid"
