---
title: Tolk Live
emoji: 🗣️
colorFrom: blue
colorTo: yellow
sdk: gradio
sdk_version: 5.9.1
app_file: app.py
python_version: "3.12"
pinned: false
short_description: Live-Übersetzung DE/EN/UK für Gruppen
---

# Tolk Live

**Online:** https://nero1913.github.io/tolk-live/ – Link öffnen, Raum starten, Einladung teilen. Kein Konto, keine Installation.

Echtzeit-Sprachübersetzung für Gruppen: Deutsch, Englisch und Ukrainisch.
Jede Person spricht in ihrer eigenen Sprache. Alle anderen sehen den Text sofort übersetzt und hören ihn vorgelesen.

## Starten

```bash
./start.sh
```

Dann im Browser `http://localhost:8080` öffnen, Namen und Sprache wählen und auf **Neuen Raum starten** tippen.
Das Einladungsfenster öffnet sich direkt, mit QR-Code, Link und Buttons für WhatsApp, Telegram und E-Mail.

## Einladen übers Internet

Damit das Mikrofon auf fremden Handys funktioniert, braucht es einen **https**-Link.
`start.sh` erstellt ihn automatisch, wenn `cloudflared` vorhanden ist (kostenlos, kein Konto nötig):

```bash
mkdir -p bin && curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz | tar -xz -C bin
```

(Bei einem Intel-Mac `cloudflared-darwin-amd64.tgz` verwenden.)

Blockiert dein Netzwerk Cloudflare (Fehler 1033), wechselt `start.sh` nach 20 Sekunden automatisch zu **localhost.run** (über SSH, ebenfalls ohne Konto). Die Adresse sieht dann so aus: `https://….lhr.life`. Direkt localhost.run nutzen: `TUNNEL=ssh ./start.sh`.

Danach zeigt `./start.sh` die öffentliche Adresse an. Öffne **diese** Adresse und erstelle dort den Raum. Dann enthalten Link und QR-Code die öffentliche Adresse.
Der Link funktioniert, solange der Mac läuft und `start.sh` offen ist. Bei jedem Start gibt es eine neue Adresse.

## Gut zu wissen

- **Browser:** Chrome, Edge oder Safari (auch auf iPhone und Android). Firefox kann keine Sprache erkennen, dort kann man nur tippen.
- **Echo:** Während eine Übersetzung vorgelesen wird, pausiert das Mikrofon automatisch. Mit Kopfhörern läuft es am flüssigsten.
- **Gleiche Sprache:** Was jemand in deiner eigenen Sprache sagt, wird nicht vorgelesen.
- **Übersetzung:** Standardmäßig über Google (kostenlos, ohne Schlüssel). Mit einem DeepL-Schlüssel wird es meist genauer:
  `DEEPL_API_KEY=dein-schlüssel ./start.sh`
- **Datenschutz:** Gesprochenes wird im Browser in Text umgewandelt (bei Chrome über Google-Server) und zum Übersetzen an Google bzw. DeepL geschickt. Räume und Verlauf liegen nur im Arbeitsspeicher und verschwinden beim Beenden.
