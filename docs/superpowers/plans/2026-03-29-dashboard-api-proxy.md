# Dashboard: API Proxy

**СТАТУС: ВЫПОЛНЕНО 2026-03-29**

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Фронтенд перестаёт ходить в Supabase напрямую. Вместо этого — вызывает Flask-эндпоинты на Render, которые сами идут в Supabase с service_role ключом.

**Почему:** Supabase использует ES256 для подписи JWT. Приватный ключ нам недоступен — Supabase его не отдаёт. Подписать ES256 токен самостоятельно невозможно.

**Архитектура:**
```
login.html → /auth/telegram → JWT подписан APP_SECRET (HS256)
dashboard.js → GET /api/logs?days=90    → Flask проверяет JWT → Supabase (service_role) → JSON
dashboard.js → GET /api/weekly          → Flask проверяет JWT → Supabase (service_role) → JSON
```

**Файлы:**
- Modify: `bot.py`
- Modify: `docs/dashboard.js`
- Modify: `docs/config.js`
- Modify: `docs/index.html`
- Modify: `.env`
- Action: обновить env vars на Render

---

## Task 1: Обновить bot.py

**Files:** `bot.py`

### Step 1: Заменить SUPABASE_JWT_SECRET на APP_SECRET

Найти строку:
```python
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
```
Заменить на:
```python
APP_SECRET = os.getenv("APP_SECRET")
```

### Step 2: Обновить _generate_jwt()

Найти:
```python
    return jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
```
Заменить на:
```python
    return jwt.encode(payload, APP_SECRET, algorithm="HS256")
```

### Step 3: Добавить _verify_jwt() после _generate_jwt()

```python
def _verify_jwt(token: str) -> str | None:
    """Верифицирует JWT и возвращает user_id (sub) или None."""
    try:
        payload = jwt.decode(token, APP_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None
```

### Step 4: Обновить CORS — добавить GET и Authorization header

Найти функцию `_cors`:
```python
def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = DASHBOARD_ORIGIN
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
```
Заменить на:
```python
def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = DASHBOARD_ORIGIN
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response
```

### Step 5: Добавить /api/logs и /api/weekly перед /auth/telegram

```python
@app.route("/api/logs")
def api_logs():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401
    user_id = _verify_jwt(auth[7:])
    if not user_id:
        return jsonify({"error": "Invalid token"}), 401

    days = int(request.args.get("days", 90))
    logs = db.get_health_logs(user_id, days=days)
    return jsonify(logs)


@app.route("/api/weekly")
def api_weekly():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "Unauthorized"}), 401
    user_id = _verify_jwt(auth[7:])
    if not user_id:
        return jsonify({"error": "Invalid token"}), 401

    summary = db.get_weekly_summary(user_id)
    return jsonify(summary or {})
```

### Step 6: Добавить OPTIONS-хендлер для /api/*

```python
@app.route("/api/logs", methods=["OPTIONS"])
@app.route("/api/weekly", methods=["OPTIONS"])
def api_options():
    return "", 204
```

- [ ] Проверить локально: `python3 bot.py` запускается без ошибок

---

## Task 2: Обновить config.js

**Files:** `docs/config.js`

Заменить весь файл на:
```javascript
// URL бэкенда на Render
const RENDER_URL = 'https://oura-v2.onrender.com';
```

`SUPABASE_URL` и `SUPABASE_ANON_KEY` больше не нужны — фронтенд не ходит в Supabase.

---

## Task 3: Обновить index.html — убрать Supabase SDK

**Files:** `docs/index.html`

Найти и удалить строку:
```html
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
```

---

## Task 4: Обновить dashboard.js — заменить Supabase на fetch

**Files:** `docs/dashboard.js`

### Step 1: Заменить блок SUPABASE CLIENT

Найти:
```javascript
// ─────────────────────────────────────────────────────────────
// SUPABASE CLIENT
// ─────────────────────────────────────────────────────────────
const { createClient } = supabase;
const db = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  global: { headers: { Authorization: `Bearer ${jwt}` } },
  auth:   { autoRefreshToken: false, persistSession: false },
});
```
Заменить на:
```javascript
// ─────────────────────────────────────────────────────────────
// API HELPER
// ─────────────────────────────────────────────────────────────
async function apiFetch(path) {
  const res = await fetch(RENDER_URL + path, {
    headers: { Authorization: `Bearer ${jwt}` },
  });
  if (res.status === 401) {
    localStorage.removeItem('oura_jwt');
    localStorage.removeItem('oura_user');
    window.location.replace('login.html');
    return null;
  }
  return res.json();
}
```

### Step 2: Заменить fetchLogs()

Найти весь блок `async function fetchLogs()` и заменить на:
```javascript
async function fetchLogs() {
  const data = await apiFetch('/api/logs?days=90');
  return data || [];
}
```

### Step 3: Заменить fetchRecap()

Найти весь блок `async function fetchRecap()` и заменить на:
```javascript
async function fetchRecap() {
  const data = await apiFetch('/api/weekly');
  if (!data || !data.weekly_data) return null;
  const text = data.weekly_data?.summary || data.weekly_data?.text || null;
  return text ? { text, week_start: data.week_start } : null;
}
```

- [ ] Открыть `http://localhost:8000/index.html` (через `python3 -m http.server 8000 --directory docs`) — убедиться что нет JS-ошибок при загрузке страницы

---

## Task 5: Обновить .env и Render

### .env

Найти и удалить:
```
# если есть SUPABASE_JWT_SECRET — удалить
```
Добавить:
```
APP_SECRET=<сгенерировать случайную строку, например: python3 -c "import secrets; print(secrets.token_hex(32))">
```

### Render environment variables

- [ ] Открыть https://dashboard.render.com → сервис oura-v2 → Environment
- [ ] Добавить: `APP_SECRET` = то же значение что в `.env`
- [ ] Убедиться что `SUPABASE_URL` и `SUPABASE_KEY` (service_role) там есть и актуальны
- [ ] Удалить `SUPABASE_JWT_SECRET` если есть

---

## Task 6: Финальная проверка

- [ ] Задеплоить на Render (push в main → автодеплой или Manual Deploy)
- [ ] Открыть https://demonk03.github.io/Oura-v2/login.html
- [ ] Войти через Telegram
- [ ] Убедиться что дашборд загружает данные без ошибок в консоли
