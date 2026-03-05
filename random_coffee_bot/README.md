# Random Coffee Bot (aiogram v3 + SQLite)

Production-ready Telegram-бот для еженедельных 1-на-1 встреч коллег внутри офисов.

## Возможности
- Регистрация через `/start` (только личка).
- Обязательный `username` для участия.
- Выбор офиса из настроек.
- Еженедельный раунд с окном готовности (`READY_WINDOW_HOURS`).
- Матчинг внутри офиса с минимизацией повторов за `REPEAT_WINDOW_WEEKS`.
- История пар, пропусков, лог отправок.
- Идемпотентная жеребьёвка, защита от двойного запуска (`round.status + file lock`).
- Бэкап SQLite перед жеребьёвкой.
- Админ-команды управления расписанием и офисами через БД settings.

## Структура
```text
random_coffee_bot/
  pyproject.toml
  .env.example
  README.md
  systemd/random-coffee.service
  src/main.py
  src/bot/
    app.py
    context.py
    keyboards.py
    handlers/
      start.py
      profile.py
      readiness.py
      rules.py
      admin.py
  src/config/
    settings.py
    logging_config.py
  src/db/
    connection.py
    migrations.py
    repositories.py
  src/matching/
    algorithm.py
  src/scheduler/
    cron_utils.py
    jobs.py
  src/services/
    draw_service.py
    calendar.py
  src/texts/
    rules.md
    messages.py
  tests/test_matching.py
```

## Конфиг `.env`
Обязательные/поддерживаемые переменные:
- `BOT_TOKEN` — токен бота.
- `ADMINS` — список Telegram `user_id` через запятую (только этот формат).
- `DB_PATH` — путь к SQLite файлу.
- `BACKUP_DIR` — директория бэкапов.
- `BACKUP_RETENTION` — сколько бэкапов хранить.
- `TIMEZONE` — например `Europe/Moscow`.
- `DRAW_CRON` — либо cron 5 полей, либо упрощённо `DOW HH:MM` (`MON 11:00`).
- `REPEAT_WINDOW_WEEKS` — окно запрета повторов.
- `READY_WINDOW_HOURS` — окно готовности до жеребьёвки.
- `OFFICES` — список офисов через запятую, например `MSK,SPB,KZN`.
- `CALENDAR_SUGGESTION_MODE` — `none` или `default`.
- `LOCK_PATH` — путь к lock-файлу.

См. пример: `.env.example`.

## Команды пользователя
- `/start` — старт, кнопки «Участвовать», «Правила».
- `/menu` — открыть главное меню.
- `/status` — статус регистрации/офиса/готовности.
- `/office` — сменить офис.
- `/leave` — выйти из жеребьёвки (без удаления истории).
- `/join` — вернуться в жеребьёвку.
- `/rules` — показать правила.

## Ready flow
- За `READY_WINDOW_HOURS` до ближайшего draw бот рассылает кнопки:
  - «Я участвую ✅»
  - «Не в этот раз»
- Нажатие кнопок записывает readiness только для ближайшего раунда.
- После завершения раунда readiness этого раунда сбрасывается.

## Матчинг
- Строго внутри офиса.
- Сначала попытка без повторов в окне `REPEAT_WINDOW_WEEKS`.
- Эвристика: «самый ограниченный пользователь первым».
- Если строго невозможно: ослабление с минимизацией повторов (предпочитаются самые старые повторы).
- При нечётном числе: один пользователь в `skipped_history` и личное сообщение.

## Google Calendar
Кнопка «Добавить в Google Calendar» формирует URL шаблона без OAuth.
- Используется HTTPS web-link Google Calendar, который работает на Android и iOS через браузер/приложение.
- `none`: ссылка без предзаполненного времени.
- `default`: предлагается ближайший рабочий день на 12:00 (timezone из `TIMEZONE`), длительность 30 минут, передаётся в UTC для совместимости.

## Админ-команды
- `/admin help`
- `/admin schedule`
- `/admin schedule set <...>`
- `/admin offices`
- `/admin offices set <comma-separated>`
- `/admin users add <user_id> <office>`
- `/admin users remove <user_id>`
- `/admin stats`

`/admin schedule set` и `/admin offices set` пишут значения в таблицу `settings` и перекрывают `.env` в рантайме.

## Запуск локально
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
python3 src/main.py
```

## Тесты
```bash
pytest
```

## Деплой на Debian (systemd)
```bash
sudo mkdir -p /opt/random_coffee
sudo chown -R $USER:$USER /opt/random_coffee
cp -R . /opt/random_coffee
cd /opt/random_coffee
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# отредактировать .env
sudo cp systemd/random-coffee.service /etc/systemd/system/random-coffee.service
sudo systemctl daemon-reload
sudo systemctl enable random-coffee
sudo systemctl start random-coffee
sudo systemctl status random-coffee
```

Логи:
```bash
journalctl -u random-coffee -f
```

## Установка, настройка и запуск на сервере
1. Подготовь сервер (Debian 12+):
```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip git
```
2. Создай рабочие директории:
```bash
sudo mkdir -p /opt/random_coffee /opt/random_coffee/data /opt/random_coffee/backups
sudo chown -R $USER:$USER /opt/random_coffee
```
3. Разверни код:
```bash
cd /opt/random_coffee
git clone <REPO_URL> .
```
4. Создай виртуальное окружение и установи зависимости:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```
5. Настрой переменные окружения:
```bash
cp .env.example .env
```
Заполни `.env` обязательно:
- `BOT_TOKEN`
- `ADMINS` (только `user_id`, через запятую)
- `DB_PATH=/opt/random_coffee/data/random_coffee.sqlite`
- `BACKUP_DIR=/opt/random_coffee/backups`
- `TIMEZONE`, `DRAW_CRON`, `OFFICES`

6. Проверь запуск вручную:
```bash
source .venv/bin/activate
python3 src/main.py
```
7. Установи systemd unit и запусти сервис:
```bash
sudo cp systemd/random-coffee.service /etc/systemd/system/random-coffee.service
sudo systemctl daemon-reload
sudo systemctl enable random-coffee
sudo systemctl start random-coffee
sudo systemctl status random-coffee
```
8. Операционные команды:
```bash
sudo systemctl restart random-coffee
sudo systemctl stop random-coffee
sudo systemctl status random-coffee
journalctl -u random-coffee -f
```

## Пользовательские сценарии
1. Первое подключение сотрудника:
- Пользователь пишет `/start`.
- Нажимает «Участвовать».
- Если нет `@username`, бот просит его включить.
- Пользователь выбирает офис.
- Профиль активирован, пользователь участвует в следующих раундах.

2. Проверка статуса:
- Пользователь отправляет `/status`.
- Бот показывает регистрацию, офис, активность и готовность к ближайшему раунду.

3. Смена офиса:
- Пользователь отправляет `/office`.
- Выбирает новый офис из кнопок.
- Следующие жеребьёвки идут уже по новому офису.

4. Временный выход и возвращение:
- `/leave` отключает участие, история остаётся.
- `/join` возвращает участие.
- Если офис не задан, бот попросит выбрать офис.

5. Подтверждение участия в раунде:
- За `READY_WINDOW_HOURS` до жеребьёвки приходит сообщение с кнопками «Я участвую ✅» и «Не в этот раз».
- «Я участвую ✅» фиксирует участие в ближайшем раунде.
- «Не в этот раз» фиксирует пропуск раунда и отправляет ответ «Хорошо, ждём тебя в следующий раз!».

6. Получение пары:
- После жеребьёвки пользователь получает личное сообщение с `@username` пары.
- В сообщении есть кнопка «Добавить в Google Calendar».
- Если пары не нашлось, приходит тихое уведомление о пропуске раунда.

8. Главное меню:
- После ключевых действий (чтение правил, ответ на напоминание, смена офиса, join/leave) есть кнопка «В меню».
- В меню доступны: «Мой статус», «Мой офис», «Правила», «Поставить на паузу/Возобновить участие».

7. Работа админа:
- `/admin schedule` смотрит текущее расписание.
- `/admin schedule set ...` обновляет расписание без правки `.env`.
- `/admin offices set ...` меняет список офисов.
- `/admin stats` показывает агрегированную статистику.

## Миграции
При старте вызывается `schema_version`-механизм из `src/db/migrations.py`.
