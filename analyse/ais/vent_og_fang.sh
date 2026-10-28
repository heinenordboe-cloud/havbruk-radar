#!/bin/bash
# Prøver 5631 hvert minutt i inntil $1 minutter. Første gang porten
# svarer, startes en 60-minutters fangst. Hvert forsøk logges.
set -u
D=$HOME/maling
mkdir -p "$D"
for i in $(seq 1 "$1"); do
  if timeout 10 bash -c 'exec 3<>/dev/tcp/153.44.253.27/5631' 2>/dev/null; then
    echo "$(date -u +%FT%TZ) 5631 svarer" >> "$D/proving-5631.log"
    exec python3 "$HOME/fang.py" 3600 "$D/strom-5631.txt" "$D/hendelser-5631.jsonl" 5631
  fi
  echo "$(date -u +%FT%TZ) 5631 timeout" >> "$D/proving-5631.log"
  sleep 50
done
