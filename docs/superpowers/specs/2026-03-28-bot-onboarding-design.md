# Bot Onboarding Improvement Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Улучшить онбординг Telegram-бота для технически грамотной аудитории — снизить трение при регистрации и установить правильные ожидания.

**Audience:** Друзья/знакомые с Oura Ring, технически грамотные.

**Approach:** Добавить `/start`, inline-кнопку для получения токена, человечные тексты с чёткими ожиданиями.

---

## Сценарии

### /start — новый пользователь

```
Привет! Я Oura Helper — помогаю следить за показателями кольца Oura.

Анализирую твои данные, присылаю алёрты при отклонениях
от личной нормы и еженедельный дайджест по воскресеньям.

Для подключения нужен Personal Access Token.

[Получить токен →]

Когда получишь — отправь: /register <токен>
```

Кнопка `[Получить токен →]` — inline keyboard с URL `https://cloud.ouraring.com/personal-access-tokens`.

### После успешного /register

```
Отлично, всё готово! Я уже начал собирать твои данные.

Буду присылать алёрты, если замечу что-то необычное,
и каждое воскресенье — дайджест твоей недели.

/status — посмотреть последние показатели
/stop — отключиться
```

### /start — уже зарегистрированный пользователь (is_active=True)

```
Привет! Я уже собираю и анализирую твои данные.

/status — последние показатели
/stop — отключиться
```

### /start — деактивированный пользователь (is_active=False)

Показывать как новому пользователю — то же приветствие с кнопкой и инструкцией по `/register`.

### /register с невалидным токеном

```
Не получилось подключиться — токен не работает.

Проверь его на странице: https://cloud.ouraring.com/personal-access-tokens
Убедись, что скопировал токен полностью, без лишних пробелов.
```

---

## Технические изменения

**Файл:** `bot.py`

1. Добавить хэндлер `/start`:
   - Проверить через `db.get_user_by_telegram_id`
   - Если `is_active=True` — отправить короткий статус
   - Если нет записи или `is_active=False` — отправить приветствие с inline-кнопкой

2. Добавить `send_message_with_keyboard(chat_id, text, keyboard)` — отдельная функция, использует `json=` (не `data=`) в `requests.post`, иначе вложенный `reply_markup` не передаётся корректно:
   ```python
   requests.post(
       f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
       json={"chat_id": chat_id, "text": text, "reply_markup": keyboard},
       timeout=10,
   )
   ```

3. Inline keyboard для кнопки токена:
   ```json
   {
     "inline_keyboard": [[
       {"text": "Получить токен →", "url": "https://cloud.ouraring.com/personal-access-tokens"}
     ]]
   }
   ```

4. Обновить текст после успешного `/register`.

5. Обновить текст при невалидном токене.

6. Обновить fallback-текст (неизвестная команда) — добавить `/start` в список:
   `Команды: /start | /register <oura_token> | /status | /stop`

---

## Что не меняем

- Логику регистрации, валидации токена, базу данных
- Команды `/status`, `/stop`
- GitHub Actions, Supabase, Render
