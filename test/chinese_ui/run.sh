#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
bin=$(mktemp /tmp/chinese-ui-test.XXXXXX)
trap 'rm -f "$bin"' EXIT
c++ -std=c++17 -Ilib/I18n test/chinese_ui/check.cpp lib/I18n/I18n.cpp lib/I18n/I18nStrings.cpp -o "$bin"
"$bin"
