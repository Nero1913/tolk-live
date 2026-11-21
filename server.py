#!/usr/bin/env python3
"""Tolk Live – Echtzeit-Sprachübersetzung für Gruppen (DE / EN / UK).

Nur Python-Standardbibliothek. Start:  python3 server.py   (Port 8080, änderbar mit PORT=...)
Optional: DEEPL_API_KEY=...  für DeepL statt der kostenlosen Google-Übersetzung.
"""
import json, os, queue, random, shutil, string, subprocess, threading, time, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8080"))
LANGS = ("de", "en", "uk")
HERE = os.path.dirname(os.path.abspath(__file__))
DEEPL_KEY = os.environ.get("DEEPL_API_KEY", "").strip()
if not DEEPL_KEY and os.path.exists(os.path.join(HERE, "deepl_key.txt")):
    with open(os.path.join(HERE, "deepl_key.txt"), encoding="utf-8") as f:
        DEEPL_KEY = f.read().strip()
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) TolkLive/1.0"}

rooms = {}            # code -> Room
rooms_lock = threading.Lock()
tr_cache = {}         # (src, dst, text) -> translation


class Room:
    def __init__(self, code):
        self.code = code
        self.people = {}      # pid -> {"name","lang","q","seen"}
        self.history = []     # last messages
        self.lock = threading.Lock()
        self.touched = time.time()

    def roster(self):
        return [{"pid": p, "name": v["name"], "lang": v["lang"]} for p, v in self.people.items()]

    def broadcast(self, event, data, skip=None):
        payload = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        with self.lock:
            targets = [v["q"] for p, v in self.people.items() if p != skip]
        for q in targets:
            q.put(payload)


def get_room(code, create=False):
    code = (code or "").upper()
    with rooms_lock:
        r = rooms.get(code)
        if r is None and create:
            r = rooms[code] = Room(code)
        if r:
            r.touched = time.time()
        return r


def new_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    while True:
        c = "".join(random.choice(alphabet) for _ in range(5))
        if c not in rooms:
            return c


# ---------- Übersetzung ----------
def _fetch(url, data=None, headers=None):
    """Holt eine URL. Bevorzugt curl (Pythons ältere TLS-Version wird von Google oft mit 429 abgewiesen)."""
    hdrs = {**UA, **(headers or {})}
    if shutil.which("curl"):
        cmd = ["curl", "-sS", "--fail", "-m", "10"]
        for k, v in hdrs.items():
            cmd += ["-H", f"{k}: {v}"]
        if data is not None:
            cmd += ["--data-binary", "@-"]
        res = subprocess.run(cmd + [url], input=data, capture_output=True, timeout=12)
        if res.returncode == 0:
            return res.stdout
        raise RuntimeError(res.stderr.decode("utf-8", "replace").strip())
    req = urllib.request.Request(url, data=data, headers=hdrs)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()


def _http_json(url, data=None, headers=None):
    return json.loads(_fetch(url, data, headers).decode("utf-8"))


def translate(text, src, dst):
    if src == dst or not text.strip():
        return text
    key = (src, dst, text)
    if key in tr_cache:
        return tr_cache[key]
    out = None
    try:
        if DEEPL_KEY:
            host = "api-free.deepl.com" if DEEPL_KEY.endswith(":fx") else "api.deepl.com"
            target = {"en": "EN-GB", "de": "DE", "uk": "UK"}[dst]
            body = urllib.parse.urlencode({"text": text, "source_lang": src.upper(), "target_lang": target}).encode()
            res = _http_json(f"https://{host}/v2/translate", body, {"Authorization": f"DeepL-Auth-Key {DEEPL_KEY}"})
            out = res["translations"][0]["text"]
        else:
            q = urllib.parse.urlencode({"client": "gtx", "sl": src, "tl": dst, "dt": "t", "q": text})
            res = _http_json("https://translate.googleapis.com/translate_a/single?" + q)
            out = "".join(seg[0] for seg in res[0] if seg and seg[0])
    except Exception as e:  # Netzwerkfehler: Originaltext zurückgeben
        print("Übersetzung fehlgeschlagen:", e)
        return None
    if len(tr_cache) > 5000:
        tr_cache.clear()
    tr_cache[key] = out
    return out


def tts_audio(text, lang):
    q = urllib.parse.urlencode({"ie": "UTF-8", "tl": lang, "client": "tw-ob", "q": text[:200]})
    return _fetch("https://translate.google.com/translate_tts?" + q)


# ---------- HTTP ----------
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 20000:
            return {}
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        qs = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
        if url.path == "/" or url.path.startswith("/r/"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if url.path == "/api/events":
            return self.events(qs)
        if url.path == "/api/tts":
            lang = qs.get("lang", "en")
            if lang not in LANGS or not qs.get("q"):
                return self._send(400, {"error": "bad request"})
            try:
                return self._send(200, tts_audio(qs["q"], lang), "audio/mpeg")
            except Exception as e:
                return self._send(502, {"error": str(e)})
        if url.path == "/api/room":
            r = get_room(qs.get("code"))
            return self._send(200, {"exists": bool(r)})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        data = self._json_body()
        if url.path == "/api/room":
            code = new_code()
            get_room(code, create=True)
            return self._send(200, {"code": code})
        room = get_room(data.get("room"))
        pid = data.get("pid")
        if not room or pid not in room.people:
            return self._send(404, {"error": "room or participant unknown"})
        me = room.people[pid]

        if url.path == "/api/say":
            text = str(data.get("text", "")).strip()[:1000]
            if not text:
                return self._send(400, {"error": "empty"})
            src = me["lang"]
            msg = {"id": f"{int(time.time()*1000)}-{random.randint(0, 9999)}", "pid": pid,
                   "name": me["name"], "lang": src, "text": text, "ts": time.time(), "tr": {}}
            needed = {v["lang"] for v in room.people.values()} | set(LANGS)
            threads, results = [], {}
            for dst in needed:
                def job(d=dst):
                    results[d] = translate(text, src, d)
                t = threading.Thread(target=job); t.start(); threads.append(t)
            for t in threads:
                t.join(12)
            msg["tr"] = {d: (results.get(d) or (text if d == src else None)) for d in LANGS}
            with room.lock:
                room.history = (room.history + [msg])[-150:]
            room.broadcast("message", msg)
            return self._send(200, {"ok": True})

        if url.path == "/api/interim":
            room.broadcast("interim", {"pid": pid, "name": me["name"], "lang": me["lang"],
                                       "text": str(data.get("text", ""))[:500]}, skip=pid)
            return self._send(200, {"ok": True})

        if url.path == "/api/profile":
            if data.get("lang") in LANGS:
                me["lang"] = data["lang"]
            if data.get("name"):
                me["name"] = str(data["name"])[:40]
            room.broadcast("roster", room.roster())
            return self._send(200, {"ok": True})

        self._send(404, {"error": "not found"})

    def events(self, qs):
        room = get_room(qs.get("room"), create=bool(qs.get("room")))
        if not room:
            return self._send(404, {"error": "no room"})
        pid = qs.get("pid") or "".join(random.choice(string.ascii_lowercase) for _ in range(10))
        lang = qs.get("lang") if qs.get("lang") in LANGS else "en"
        name = (qs.get("name") or "Gast")[:40]
        q = queue.Queue()
        with room.lock:
            room.people[pid] = {"name": name, "lang": lang, "q": q}
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        hello = {"pid": pid, "room": room.code, "history": room.history}
        q.put(f"event: hello\ndata: {json.dumps(hello, ensure_ascii=False)}\n\n")
        room.broadcast("roster", room.roster())
        try:
            while True:
                try:
                    chunk = q.get(timeout=15)
                except queue.Empty:
                    chunk = ": ping\n\n"
                self.wfile.write(chunk.encode("utf-8"))
                self.wfile.flush()
        except Exception:
            pass
        finally:
            with room.lock:
                if room.people.get(pid, {}).get("q") is q:
                    del room.people[pid]
            room.broadcast("roster", room.roster())


def cleanup():
    while True:
        time.sleep(600)
        with rooms_lock:
            for code in [c for c, r in rooms.items() if not r.people and time.time() - r.touched > 6 * 3600]:
                del rooms[code]


if __name__ == "__main__":
    threading.Thread(target=cleanup, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    srv.daemon_threads = True
    print(f"Tolk Live läuft: http://localhost:{PORT}")
    print("Übersetzung:", "DeepL" if DEEPL_KEY else "Google (kostenlos)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
