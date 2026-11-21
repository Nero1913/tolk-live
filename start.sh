#!/bin/bash
# Startet Tolk Live und erstellt einen öffentlichen https-Link.
# Reihenfolge: Cloudflare (falls installiert und erreichbar), sonst localhost.run über SSH.
# Erzwingen:  TUNNEL=ssh ./start.sh   |   TUNNEL=cloudflare ./start.sh   |   TUNNEL=none ./start.sh
cd "$(dirname "$0")"
PORT="${PORT:-8080}"
TUNNEL="${TUNNEL:-auto}"
LOG="$(mktemp -t tolklive)"

# DeepL-Schlüssel einmalig abfragen und in deepl_key.txt speichern
if [ -z "$DEEPL_API_KEY" ] && [ ! -s deepl_key.txt ] && [ ! -e .kein_deepl ]; then
  echo "DeepL-Schlüssel einfügen und Enter drücken."
  echo "(Nur Enter = kostenlose Google-Übersetzung. Löschen von deepl_key.txt fragt erneut.)"
  read -r -s -p "> " KEY; echo
  KEY="$(echo "$KEY" | tr -d '[:space:]')"
  if [ -n "$KEY" ]; then
    (umask 077; printf '%s' "$KEY" > deepl_key.txt)
    echo "Gespeichert. Ab jetzt wird mit DeepL übersetzt."
  else
    touch .kein_deepl
  fi
fi

PORT=$PORT python3 server.py 2>/dev/null &
SERVER=$!
TPID=""
trap 'kill $SERVER $TPID 2>/dev/null; rm -f "$LOG"' EXIT
sleep 1

show() {
  echo
  echo "  ==============================================================="
  echo "   Öffentlicher Link (diesen öffnen und Raum dort erstellen):"
  echo "   $1"
  echo "  ==============================================================="
  echo "  Fenster offen lassen. Beenden mit Ctrl-C."
  echo
}

CF=""
[ -x ./bin/cloudflared ] && CF=./bin/cloudflared
[ -z "$CF" ] && command -v cloudflared >/dev/null && CF=cloudflared

if [ "$TUNNEL" = "none" ]; then
  echo "Nur lokal: http://localhost:$PORT"; wait $SERVER; exit
fi

if [ -n "$CF" ] && [ "$TUNNEL" != "ssh" ]; then
  echo "Versuche Cloudflare …"
  "$CF" tunnel --no-autoupdate --protocol http2 --url "http://localhost:$PORT" >"$LOG" 2>&1 &
  TPID=$!
  for i in $(seq 1 40); do grep -q "Registered tunnel connection" "$LOG" && break; sleep 0.5; done
  if grep -q "Registered tunnel connection" "$LOG"; then
    show "$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -1)"
    wait $TPID; exit
  fi
  echo "Cloudflare ist aus diesem Netzwerk nicht erreichbar, wechsle zu localhost.run …"
  kill $TPID 2>/dev/null; TPID=""
fi

# localhost.run trennt kostenlose Tunnel gelegentlich – dann automatisch neu verbinden.
while kill -0 $SERVER 2>/dev/null; do
  echo "Verbinde mit localhost.run …"
  : >"$LOG"
  ssh -T -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=20 -o ServerAliveCountMax=3 \
      -o ExitOnForwardFailure=yes -R 80:localhost:$PORT nokey@localhost.run -- --output json >"$LOG" 2>&1 &
  TPID=$!
  for i in $(seq 1 60); do grep -qE 'https://[a-z0-9.-]+\.lhr\.life' "$LOG" && break; kill -0 $TPID 2>/dev/null || break; sleep 0.5; done
  URL=$(grep -oE 'https://[a-z0-9.-]+\.lhr\.life' "$LOG" | head -1)
  if [ -n "$URL" ]; then
    echo "$URL" > link.txt
    show "$URL"
    wait $TPID
    echo
    echo "!! Tunnel getrennt ($(date +%H:%M)). Neuer Link folgt – alle bitte neu einladen."
  else
    echo "Verbindung fehlgeschlagen, neuer Versuch in 10 Sekunden …"; tail -3 "$LOG"
  fi
  rm -f link.txt
  sleep 3
  [ -z "$URL" ] && sleep 7
done
