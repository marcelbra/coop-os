#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default split: vertical (side by side). Pass -h for horizontal (top/bottom).
SPLIT="vertically"
while getopts "vh" opt; do
    case $opt in
        h) SPLIT="horizontally" ;;
        v) SPLIT="vertically" ;;
    esac
done

# Disable inactive pane dimming
defaults write com.googlecode.iterm2 DimInactiveSplitPanes -bool false

# Write Dynamic Profiles.
"$DIR/.venv/bin/python" "$DIR/scripts/write_iterm_profiles.py"

# Read agent command from config.yml
AGENT_CMD=$(awk -F': ' '/^agent_harness_command:/{gsub(/"/, "", $2); print $2; exit}' "$DIR/config.yml")
AGENT_CMD="${AGENT_CMD:-claude}"

# If not already inside iTerm, launch it and wait for it to be ready.
if [ "${TERM_PROGRAM}" != "iTerm.app" ]; then
    if ! pgrep -xq iTerm2; then
        open -a iTerm
        until pgrep -xq iTerm2; do sleep 0.3; done
        sleep 2
    fi
fi

# Create window, split panes, write startup commands, and maximize.
osascript \
  -e 'tell application "Finder" to set screenBounds to bounds of window of desktop' \
  -e 'tell application "iTerm2"' \
  -e "  set w to (create window with profile \"coop-os-tui\")" \
  -e '  tell w' \
  -e '    set topPane to current session of current tab' \
  -e '    tell topPane' \
  -e "      set bottomPane to (split $SPLIT with profile \"coop-os-agent\")" \
  -e "      write text \"cd '$DIR' && make run\"" \
  -e '    end tell' \
  -e '    tell bottomPane' \
  -e "      write text \"cd '$DIR' && $AGENT_CMD\"" \
  -e '    end tell' \
  -e '  end tell' \
  -e '  set bounds of w to screenBounds' \
  -e 'end tell'

# If launched from outside iTerm, bring it to the front now.
if [ "${TERM_PROGRAM}" != "iTerm.app" ]; then
    open -a iTerm
fi
