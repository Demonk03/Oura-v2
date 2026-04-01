# Bot Onboarding Improvement Implementation Plan

**СТАТУС: ВЫПОЛНЕНО 2026-03-29**

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить `/start` с inline-кнопкой, обновить тексты регистрации и ошибок для улучшения онбординга.

**Architecture:** Все изменения только в `bot.py`. Добавляем `send_message_with_keyboard` (использует `json=` вместо `data=`), хэндлер `/start` с проверкой статуса пользователя, обновляем существующие тексты.

**Tech Stack:** Python, Flask, Telegram Bot API, requests, supabase-py

---

### Task 1: Добавить send_message_with_keyboard

**Files:**
- Modify: `bot.py`

- [ ] **Step 1:** Открыть `bot.py`, найти функцию `send_message` (строка 16)
- [ ] **Step 2:** После функции `send_message` добавить новую функцию:

```python
def send_message_with_keyboard(chat_id: int, text: str, keyboard: dict) -> None:
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text, "reply_markup": keyboard},
        timeout=10,
    )
```

- [ ] **Step 3:** Убедиться, что функция добавлена между `send_message` и `validate_oura_token`

---

### Task 2: Добавить константу OURA_TOKEN_KEYBOARD

**Files:**
- Modify: `bot.py`

- [ ] **Step 1:** После блока импортов и переменных (`TG_TOKEN`, `OURA_BASE_URL`) добавить константу:

```python
OURA_TOKEN_KEYBOARD = {
    "inline_keyboard": [[
        {"text": "Получить токен →", "url": "https://cloud.ouraring.com/personal-access-tokens"}
    ]]
}
```

---

### Task 3: Добавить хэндлер /start

**Files:**
- Modify: `bot.py`

- [ ] **Step 1:** Добавить функцию `handle_start` после `handle_stop`:

```python
def handle_start(chat_id: int) -> None:
    user = db.get_user_by_telegram_id(chat_id)
    if user and user["is_active"]:
        send_message(chat_id, (
            "Привет! Я уже собираю и анализирую твои данные.\n\n"
            "/status — последние показатели\n"
            "/stop — отключиться"
        ))
    else:
        send_message_with_keyboard(chat_id, (
            "Привет! Я Oura Helper — помогаю следить за показателями кольца Oura.\n\n"
            "Анализирую твои данные, присылаю алёрты при отклонениях "
            "от личной нормы и еженедельный дайджест по воскресеньям.\n\n"
            "Для подключения нужен Personal Access Token.\n\n"
            "Когда получишь — отправь: /register <токен>"
        ), OURA_TOKEN_KEYBOARD)
```

- [ ] **Step 2:** В функции `webhook` добавить обработку `/start` перед `/register`:

```python
if text == "/start":
    handle_start(chat_id)

elif text.startswith("/register"):
```

---

### Task 4: Обновить тексты

**Files:**
- Modify: `bot.py`

- [ ] **Step 1:** В `handle_register` заменить текст успешной регистрации (строка ~54):

**Было:**
```python
send_message(chat_id, "Готово! Данные начнут собираться завтра утром. Еженедельный отчёт — по воскресеньям.")
```

**Стало:**
```python
send_message(chat_id, (
    "Отлично, всё готово! Я уже начал собирать твои данные.\n\n"
    "Буду присылать алёрты, если замечу что-то необычное, "
    "и каждое воскресенье — дайджест твоей недели.\n\n"
    "/status — посмотреть последние показатели\n"
    "/stop — отключиться"
))
```

- [ ] **Step 2:** В `handle_register` заменить текст при невалидном токене (строка ~45):

**Было:**
```python
send_message(chat_id, "Токен не работает. Проверь его в приложении Oura: Profile → Personal Access Token.")
```

**Стало:**
```python
send_message(chat_id, (
    "Не получилось подключиться — токен не работает.\n\n"
    "Проверь его на странице: https://cloud.ouraring.com/personal-access-tokens\n"
    "Убедись, что скопировал токен полностью, без лишних пробелов."
))
```

- [ ] **Step 3:** В `webhook` обновить fallback-текст (строка ~110):

**Было:**
```python
send_message(chat_id, "Команды: /register <oura_token> | /status | /stop")
```

**Стало:**
```python
send_message(chat_id, "Команды: /start | /register <oura_token> | /status | /stop")
```

---

### Task 5: Проверка и коммит

- [ ] **Step 1:** Проверить что `bot.py` запускается без ошибок:
```bash
cd "/Users/dkossenkov/Documents/Private files/AI/Oura-v2" && python3 -c "import bot; print('OK')"
```
Ожидаемый вывод: `OK`

- [ ] **Step 2:** Написать боту `/start` и убедиться что пришло приветствие с кнопкой

- [ ] **Step 3:** Закоммитить и запушить:
```bash
cd "/Users/dkossenkov/Documents/Private files/AI/Oura-v2" && git add bot.py && git commit -m "Improve bot onboarding: add /start, inline keyboard, update texts" && git push origin main
```

- [ ] **Step 4:** Дождаться редеплоя на Render, снова написать `/start` — проверить финальный результат
