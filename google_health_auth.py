#!/usr/bin/env python3
"""Локальный OAuth-флоу для Google Health API.

Запускается один раз вручную: открывает consent-экран в браузере, принимает
redirect на localhost, обменивает code на refresh token и дописывает его в .env.
"""
import http.server
import json
import os
import secrets
import threading
import urllib.parse
import urllib.request
import webbrowser

PORT = 8765
REDIRECT_URI = f"http://localhost:{PORT}/callback"
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def load_env(path: str = ENV_PATH) -> None:
    """Минимальная замена python-dotenv: KEY=VALUE, без подстановок и кавычек."""
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"\''))


load_env()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

SCOPES = [
    "https://www.googleapis.com/auth/googlehealth.sleep.readonly",
    "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
]

_result = {}
_done = threading.Event()


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        _result.update({k: v[0] for k, v in params.items()})
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        if "code" in _result:
            self.wfile.write("Готово, можно закрывать вкладку.".encode())
        else:
            self.wfile.write(f"Ошибка: {_result.get('error')}".encode())
        _done.set()

    def log_message(self, *args):
        pass


def exchange_code(code: str) -> dict:
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def write_refresh_token(token: str) -> None:
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            lines = [ln for ln in f.read().splitlines()
                     if not ln.startswith("GOOGLE_HEALTH_REFRESH_TOKEN=")]
    lines.append(f"GOOGLE_HEALTH_REFRESH_TOKEN={token}")
    with open(ENV_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise SystemExit("Нет GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET в .env")

    state = secrets.token_urlsafe(16)
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })

    server = http.server.HTTPServer(("localhost", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    print("Открываю браузер. Если не открылся — перейди по ссылке:\n")
    print(auth_url + "\n")
    webbrowser.open(auth_url)

    _done.wait(timeout=300)
    server.shutdown()

    if "code" not in _result:
        raise SystemExit(f"Авторизация не прошла: {_result.get('error', 'таймаут')}")
    if _result.get("state") != state:
        raise SystemExit("state не совпал, флоу прерван")

    tokens = exchange_code(_result["code"])
    if "refresh_token" not in tokens:
        raise SystemExit("Google не вернул refresh_token. Нужен prompt=consent и access_type=offline")

    write_refresh_token(tokens["refresh_token"])
    granted = tokens.get("scope", "").split()
    print("Refresh token записан в .env")
    print(f"Выданные scopes ({len(granted)}):")
    for s in granted:
        print(f"  {s.rsplit('/', 1)[-1]}")


if __name__ == "__main__":
    main()
