#!/usr/bin/env bash
# Render (ve CI) derleme adımı: bağımlılıklar + sabitlenmiş OpenFootball verisi (CC0, git ile; yerelle aynı commit).
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "${KUR_PIP:-1}" = "1" ]; then
  python3 -m pip install --no-cache-dir -r requirements.txt
fi
OF_SHA="e6744429ee395bc86f247348c6184bb08d4eb361"
OF_DIZIN="output/kaynak_veri/openfootball-football.json"
if [ ! -d "$OF_DIZIN/.git" ] || [ "$(git -C "$OF_DIZIN" rev-parse HEAD 2>/dev/null)" != "$OF_SHA" ]; then
  mkdir -p "$OF_DIZIN"
  git -C "$OF_DIZIN" init -q
  git -C "$OF_DIZIN" remote add origin https://github.com/openfootball/football.json.git 2>/dev/null || true
  git -C "$OF_DIZIN" fetch -q --depth 1 origin "$OF_SHA"
  git -C "$OF_DIZIN" checkout -q FETCH_HEAD
fi
test "$(git -C "$OF_DIZIN" rev-parse HEAD)" = "$OF_SHA"
PYTHONPATH=lib python3 -c "from fi.kaynaklar import openfootball as O; m = O.lig_oku('en.2', sezonlar=['2025-26'])[0]; print('OpenFootball en.2 2025-26:', len(m), 'maç')"
echo "kurulum tamam"
