#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
bin=$(mktemp /tmp/panic-log-test.XXXXXX)
trap 'rm -f "$bin"' EXIT
c++ -std=c++17 -Itest/logging/stubs -Ilib/Logging test/logging/panic_log_test.cpp lib/Logging/Logging.cpp -o "$bin"
for reason in 4 5 6 7 12; do "$bin" "$reason"; done
echo "5 panic reset variants: log preservation and resume passed"
