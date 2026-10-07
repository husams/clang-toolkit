#!/usr/bin/env bash
set -euo pipefail
# Supply the official ANTLR 4.13.2 complete jar; Java is needed only to regenerate.
: "${CTK_ANTLR_JAR:?Set CTK_ANTLR_JAR to antlr-4.13.2-complete.jar}"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root/server/src/script/grammar"
java -jar "$CTK_ANTLR_JAR" -Dlanguage=Cpp -no-listener -visitor \
  -package 'ctk::script::grammar' -Xexact-output-dir \
  -o ../generated CtkScript.g4
