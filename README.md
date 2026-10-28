# Telegram Giveaway Bot

Telegram-бот для розыгрышей в канале: публикация поста с кнопкой участия, проверка подписки, хранение участников в SQLite, выбор победителей вручную или по дедлайну, экспорт участников в CSV.

## Требования

- Python 3.12
- Telegram-бот, созданный через @BotFather
- Бот добавлен в канал с правами на публикацию сообщений

## Установка (Windows)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
call .venv\Scripts\activate.bat
pip install -r requirements.txt
Copy-Item .env.example .env
```

Откройте `.env` и заполните `BOT_TOKEN`, `CHANNEL_ID`, `CHANNEL_USERNAME` и `INITIAL_ADMIN_IDS`.

## Запуск

```powershell
python -m app.main
```

## Команды администратора

- `/newgiveaway Название приза [минуты]` — создать и опубликовать розыгрыш; минуты необязательны.
- `/participants [id]` — список участников активного розыгрыша или указанного ID.
- `/pickwinner [id]` — выбрать и объявить победителя(ей).
- `/cancelgiveaway [id]` — отменить розыгрыш.
- `/deletegiveaway ID` — удалить розыгрыш.
- `/exportparticipants [id]` — выгрузить участников в CSV.

ID администраторов указываются через запятую в `INITIAL_ADMIN_IDS`. Дедлайн проверяется с интервалом `DEADLINE_CHECK_INTERVAL` секунд.

## Тесты

```powershell
pytest
```

Не публикуйте файл `.env`: он содержит токен бота.
