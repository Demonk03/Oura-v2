# Fix: Oura Alert Check (v2) GitHub Actions failure

**СТАТУС: ВЫПОЛНЕНО 2026-03-29**

**Goal:** Починить падение workflow `alert_check.yml` в GitHub Actions.

**Root cause (гипотеза):** `update.yml` (success) использует только `SUPABASE_URL` + `SUPABASE_KEY`. `alert_check.yml` (failure) дополнительно требует `OPENAI_API_KEY` + `TG_TOKEN` — скорее всего, они не добавлены в Secrets репозитория `Demonk03/Oura-v2`. Также `alert_checker.py` не имеет обработки ошибок в `main()` — любое исключение (HTTP ошибка GPT, Telegram timeout) роняет весь job.

---

## Task 1: Проверить и добавить GitHub Secrets

**Files:** нет (действие в GitHub UI)

- [ ] Открыть https://github.com/Demonk03/Oura-v2/settings/secrets/actions
- [ ] Убедиться что есть все 4 секрета: `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_API_KEY`, `TG_TOKEN`
- [ ] Если `OPENAI_API_KEY` или `TG_TOKEN` отсутствуют — добавить (значения из `.env`)
- [ ] Запустить workflow вручную: Actions → Oura Alert Check (v2) → Run workflow
- [ ] Проверить что job прошёл успешно

---

## Task 2: Добавить обработку ошибок в alert_checker.py

**Files:**
- Modify: `alert_checker.py`

Сейчас `main()` не перехватывает исключения. Если GPT вернул 401/500, `raise_for_status()` бросает исключение → весь job падает. Нужно обернуть `process_user()` в try/except, чтобы ошибка одного пользователя не роняла остальных и job в целом.

- [ ] В `main()` обернуть `process_user(user)` в try/except:

```python
def main():
    users = db.get_active_users()
    print(f"Активных пользователей: {len(users)}")
    for user in users:
        try:
            process_user(user)
        except Exception as e:
            print(f"[user {user.get('telegram_id')}] Ошибка: {e}")
```

- [ ] Убедиться что скрипт запускается локально без ошибок
- [ ] Коммит: `Fix: wrap process_user in try/except to prevent job failure on single user error`
