# Concierge Bot

Mattermost-бот для создания заявок в YouTrack через интерактивный диалог.

## Что делает

- Реагирует на slash-команду `/concierge` и упоминание `@concierge`
- Открывает интерактивную форму с вопросами из чеклиста проекта
- Если проектов несколько — сначала предлагает выбрать проект
- Автоматически создаёт тикет в YouTrack с заполненными полями
- Уведомляет в чат со ссылкой на созданный тикет
- `/concierge update` — позволяет добавить комментарий к уже существующему тикету
- Поддержка приватных каналов через WebSocket (outgoing webhook там не работает)

## Стек

- Python 3.12
- FastAPI + Uvicorn
- httpx, websockets
- PyYAML
- Docker Compose

## Структура проекта

```
concierge/
├── bot/
│   ├── main.py          # FastAPI приложение, HTTP endpoints
│   ├── config.py        # Загрузка конфигурации из env и YAML
│   ├── mattermost.py    # Клиент Mattermost API
│   ├── youtrack.py      # Клиент YouTrack API
│   ├── checklist.py     # Парсер чеклистов (.md файлы)
│   └── ws_listener.py   # WebSocket-слушатель для приватных каналов
├── config/
│   ├── config.yaml      # Пути к файлам (не секреты)
│   └── projects.yaml    # Список проектов и маппинг полей
├── checklists/
│   └── *.md             # Чеклисты с вопросами для каждого проекта
├── docker-compose.yml
├── Dockerfile
└── .env                 # Секреты (не коммитить)
```

## Быстрый старт

### 1. Подготовить конфиги

```bash
cp .env.example .env
cp config/config.example.yaml config/config.yaml
cp config/projects.example.yaml config/projects.yaml
cp checklists/helpdesk-general.example.md checklists/helpdesk-general.md
```

### 2. Заполнить `.env`

```env
# Mattermost
MM_URL=https://chat.your-company.com
MM_API_TOKEN=your_bot_personal_access_token
MM_SLASH_TOKEN=token_from_slash_command
MM_WEBHOOK_TOKEN=token_from_outgoing_webhook
MM_LISTEN_CHANNELS=channel_id1,channel_id2   # для WebSocket (приватные каналы)

# YouTrack
YT_URL=https://your-company.youtrack.cloud
YT_TOKEN=perm:your_permanent_token
YT_DEFAULT_PROJECT=HD

# Бот
BOT_PORT=8080
BOT_BASE_URL=http://10.0.0.1:8080   # IP бота, доступный с Mattermost-сервера
CONFIG_PATH=/app/config/config.yaml
```

### 3. Запустить

```bash
docker compose up -d
```

### 4. Проверить

```bash
docker compose logs -f
curl http://localhost:8080/health
# → {"status": "ok"}
```

## Переменные окружения

| Переменная            | Обязательная | Описание |
|-----------------------|:---:|---|
| `MM_URL`              | да  | URL Mattermost-сервера |
| `MM_API_TOKEN`        | да  | Personal Access Token бот-аккаунта |
| `MM_SLASH_TOKEN`      | да  | Токен slash-команды `/concierge` |
| `MM_WEBHOOK_TOKEN`    | нет | Токен outgoing webhook для `@concierge` (публичные каналы) |
| `MM_LISTEN_CHANNELS`  | нет | ID каналов через запятую для WebSocket-режима (приватные каналы) |
| `YT_URL`              | да  | URL YouTrack-инстанса |
| `YT_TOKEN`            | да  | Permanent token YouTrack |
| `YT_DEFAULT_PROJECT`  | нет | Короткое имя проекта по умолчанию (default: `HD`) |
| `BOT_PORT`            | нет | Порт бота (default: `8080`) |
| `BOT_BASE_URL`        | да  | Внешний URL бота (доступный с Mattermost-сервера) |
| `CONFIG_PATH`         | нет | Путь к config.yaml (default: `config/config.yaml`) |

## Конфигурация проектов

`config/projects.yaml`:

```yaml
projects:
  - id: "helpdesk-general"
    name: "Общий HelpDesk"
    checklist_file: "helpdesk-general.md"
    youtrack:
      project_id: "0-0"              # ID проекта из YouTrack (Settings → Projects → ID в URL)
      project_short_name: "HD"       # Короткое имя для фильтра в /concierge update
      assignee: "ivan.petrov"        # YouTrack login исполнителя (необязательно)
      field_mapping:
        summary: "summary"           # ключ_чеклиста: поле_YouTrack
        description: "description"
        priority: "Priority"
```

- `project_id` — числовой ID (например `0-0`), находится в URL YouTrack при открытии проекта
- `project_short_name` — используется для фильтрации тикетов в `/concierge update`
- `assignee` — если указан, тикет сразу назначается на этого пользователя
- `field_mapping` — маппинг вопросов чеклиста на поля YouTrack; `summary` → заголовок тикета, `description` → описание, остальные → добавляются в конец описания

## Формат чеклиста

Файл `.md` в папке `checklists/`:

```markdown
# Название чеклиста

## question_id
Текст вопроса — отображается как placeholder в форме

## another_question
Ещё один вопрос
```

- `## id` — идентификатор поля, маппится в `field_mapping` проекта
- Первый вопрос чеклиста используется как заголовок уведомления при создании тикета

## HTTP endpoints

| Метод | Путь       | Описание |
|-------|------------|---|
| GET   | `/health`  | Health check |
| POST  | `/slash`   | Slash-команда `/concierge` и `/concierge update` |
| POST  | `/webhook` | Outgoing webhook для `@concierge` (публичные каналы) |
| POST  | `/action`  | Обработка нажатия кнопки |
| POST  | `/dialog`  | Обработка отправки диалогов |

## Настройка Mattermost

### Бот-аккаунт

1. System Console → Integrations → Bot Accounts → Enable Bot Account Creation
2. Integrations → Bot Accounts → Add Bot Account
3. Создать Personal Access Token → вставить в `MM_API_TOKEN`
4. Добавить бота в нужные каналы через Add Members

### Slash-команда `/concierge`

1. Main Menu → Integrations → Slash Commands → Add Slash Command
2. **Command Trigger Word:** `concierge`
3. **Request URL:** `http://<BOT_BASE_URL>/slash`
4. **Request Method:** POST
5. Скопировать токен → вставить в `MM_SLASH_TOKEN`

### Outgoing Webhook для `@concierge` (только публичные каналы)

1. Main Menu → Integrations → Outgoing Webhooks → Add Outgoing Webhook
2. **Trigger Words:** `@concierge`
3. **Callback URLs:** `http://<BOT_BASE_URL>/webhook`
4. Скопировать токен → вставить в `MM_WEBHOOK_TOKEN`
5. System Console → Environment → Developer → **Allow untrusted internal connections to:** добавить IP бота

### WebSocket для приватных каналов

Outgoing Webhooks не работают в приватных каналах. Для поддержки `@concierge` в приватных каналах используется WebSocket-подключение:

1. Добавить бота в нужный приватный канал (Add Members)
2. Узнать ID канала: открыть канал → Channel Info, или из URL
3. Добавить в `.env`:
   ```
   MM_LISTEN_CHANNELS=channel_id_here
   ```
4. Перезапустить бот:
   ```bash
   docker compose restart concierge
   ```

Можно указать несколько каналов через запятую. Если `MM_LISTEN_CHANNELS` не задан — WebSocket-слушатель не запускается.

## Использование

### Создать тикет

```
/concierge
```
или написать `@concierge` в канале — бот покажет кнопку **Создать заявку**.

Если проектов несколько — сначала откроется диалог выбора проекта, затем форма с вопросами чеклиста.

### Добавить комментарий к тикету

```
/concierge update
```

Откроется форма со списком ваших тикетов и полем для комментария.
