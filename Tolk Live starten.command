#!/bin/bash
# Doppelklick startet Tolk Live im Mac-Terminal.
# caffeinate verhindert, dass der Mac einschläft, solange das Fenster offen ist.
cd "$(dirname "$0")"
TUNNEL=ssh caffeinate -i ./start.sh
