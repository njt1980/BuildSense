#!/bin/sh
set -e

echo "Installing git hooks: setting core.hooksPath to .githooks"
git config core.hooksPath .githooks
echo "Done. To revert: git config --unset core.hooksPath" 
