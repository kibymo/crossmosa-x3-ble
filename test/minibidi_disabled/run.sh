#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
c++ -std=c++17 -DCROSSMOSA_DISABLE_BIDI=1 -I"$root/lib/MiniBidi" "$root/test/minibidi_disabled/no_bidi_test.cpp" "$root/lib/MiniBidi/BidiUtils.cpp" -o "$work/test"
"$work/test"
if nm -C "$work/test" | rg 'sharedBidiLine|bidiMutex|::shaped|do_bidi|do_shape'; then
  echo 'unexpected bidi storage or processing linked' >&2
  exit 1
fi
echo '6 text cases, null input, direction/mark fallback and word-order reset passed; no bidi buffers or shaping linked'
