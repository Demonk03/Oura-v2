# Dashboard Auth Debug — Session Log 2026-03-28

**СТАТУС: РЕШЕНО 2026-03-29** — см. план `2026-03-29-dashboard-api-proxy.md`

## Что сделано

1. **GitHub Pages** — файлы из `dashboard/` перемещены в `docs/`, включён GitHub Pages на ветке `main` / папке `/docs`. Dashboard доступен по `https://demonk03.github.io/Oura-v2/login.html`.

2. **Telegram Widget** — заработал после прописки домена `demonk03.github.io` в BotFather → Bot Settings → Domain.

3. **Логин** — работает: Telegram Widget отправляет данные на `oura-v2.onrender.com/auth/telegram`, бот проверяет подпись и возвращает JWT. Токен сохраняется в localStorage.

4. **Редирект после логина** — работает (после исправления SUPABASE_JWT_SECRET на Render).

---

## Текущая проблема

**Дашборд не загружает данные.** Supabase возвращает ошибку:

```
code: "PGRST301"
message: "No suitable key or wrong key type"
details: "None of the keys was able to decode the JWT"
```

### Причина

Supabase-проект использует **ES256 (P-256, асимметричные ключи)** — это подтверждено через:
`https://ehvprasmfkamqlyawthi.supabase.co/auth/v1/.well-known/jwks.json`

Bot.py генерирует JWT с алгоритмом **HS256** (симметричный, с секретом). Supabase PostgREST проверяет токены через JWKS endpoint и не принимает HS256 токены.

### Что пробовали

- Сверяли SUPABASE_JWT_SECRET на Render и в Supabase → совпадают
- Пробовали legacy (старый) ключ из Supabase → не помогло
- JWT корректно верифицируется на jwt.io с правильным секретом — но Supabase всё равно отклоняет

### JWT payload (корректный)

```json
{
  "sub": "843f18ad-c8b8-4b68-b094-66d722e5bdbc",
  "role": "authenticated",
  "iss": "supabase",
  "iat": 1774734123,
  "exp": 1775338923
}
```

---

## Что нужно сделать в следующей сессии

Переписать генерацию JWT в `bot.py` — вместо самостоятельной подписи использовать Supabase Admin API для получения валидного токена.

### Вариант решения

Использовать `supabase-py` admin-клиент в bot.py:
1. При регистрации пользователя через Telegram → создавать Supabase Auth user (`auth.admin.create_user`) с `user_metadata: {telegram_id: ...}`
2. При логине через Telegram Widget → бот вызывает `auth.admin.create_user` (если не существует) или получает существующего пользователя → генерирует ссылку/токен через admin API
3. Возвращает Supabase-native JWT на фронтенд

Либо более простой вариант: `auth.admin.sign_in_with_id` или аналог без email/password.

### Ключевые файлы

- `bot.py` — функция `_generate_jwt()` и эндпоинт `/auth/telegram` (строки 60–206)
- RLS-политики в Supabase — `user_id = auth.uid()` — менять не нужно
