#!/usr/bin/env bash
set -euo pipefail

uuid='claude-codex-usage@danyjs'
target="$HOME/.local/share/gnome-shell/extensions/$uuid"
mkdir -p "$target"
cp gnome-extension/$uuid/{extension.js,metadata.json,stylesheet.css,codex-icon.png} "$target/"

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

printf 'Enabled %s. Log out and back in to load a newly installed extension.\n' "$uuid"
