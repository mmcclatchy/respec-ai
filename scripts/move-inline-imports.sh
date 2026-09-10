#!/bin/bash
# pre-commit already fails a hook when it modifies files, and it compares only the
# files it passed in. The previous `git diff --exit-code` here inspected the whole
# working tree instead, so any unrelated dirty file failed the hook regardless of
# whether autoimport changed anything.
set -euo pipefail
autoimport "$@"
