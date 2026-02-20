# Concierge Bot

Mattermost-бот для создания заявок в YouTrack через интерактивный диалог.

## Что делает

- Реагирует на slash-команду `/concierge` и упоминание `@concierge`
- Открывает форму с вопросами из чеклиста проекта
- Автоматически создаёт тикет в YouTrack с заполненными полями
- Уведомляет в чат со ссылкой на созданный тикет

## Стек

- Python 3.12
- FastAPI + Uvicorn
- httpx
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
│   └── session.py       # Менеджер сессий
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

### 1. Клонировать и подготовить конфиги

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
MM_WEBHOOK_TOKEN=token_from_outgoing_webhook   # только для @concierge

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
```

## Переменные окружения

| Переменная          | Обязательная | Описание |
|---------------------|:---:|---|
| `MM_URL`            | да  | URL Mattermost-сервера |
| `MM_API_TOKEN`      | да  | Personal Access Token бот-аккаунта |
| `MM_SLASH_TOKEN`    | да  | Токен slash-команды `/concierge` |
| `MM_WEBHOOK_TOKEN`  | нет | Токен outgoing webhook для `@concierge` |
| `YT_URL`            | да  | URL YouTrack-инстанса |
| `YT_TOKEN`          | да  | Permanent token YouTrack |
| `YT_DEFAULT_PROJECT`| нет | Короткое имя проекта по умолчанию (default: `HD`) |
| `BOT_PORT`          | нет | Порт бота (default: `8080`) |
| `BOT_BASE_URL`      | да  | Внешний URL бота (доступный с Mattermost-сервера) |
| `CONFIG_PATH`       | нет | Путь к config.yaml (default: `/app/config/config.yaml`) |

## Конфигурация проектов

`config/projects.yaml` — список проектов, каждый с:

```yaml
projects:
  - id: "helpdesk-general"
    name: "Общий HelpDesk"
    checklist_file: "helpdesk-general.md"
    youtrack:
      project_id: "0-0"          # ID проекта из YouTrack URL
      assignee: "ivan.petrov"    # Login исполнителя (необязательно)
      field_mapping:
        summary: "summary"       # ключ_чеклиста: поле_YouTrack
        description: "description"
        priority: "Priority"
```

`project_id` можно найти в YouTrack: Settings → Projects → выбрать проект → ID в URL.

## Формат чеклиста

Файл `.md` в папке `checklists/`:

```markdown
# Название чеклиста

## question_id
Текст вопроса — отображается как placeholder в форме

## another_question
Ещё один вопрос
```

- `# heading` — название (используется в уведомлении об успехе)
- `## id` — идентификатор поля, маппится в `field_mapping`

## Настройка Mattermost

### Slash-команда `/concierge`
1. Main Menu → Integrations → Slash Commands → Add Slash Command
2. **Command Trigger Word:** `concierge`
3. **Request URL:** `http://<BOT_BASE_URL>/slash`
4. **Request Method:** POST
5. Скопировать токен → вставить в `MM_SLASH_TOKEN`

### Outgoing Webhook для `@concierge` (опционально)
1. Main Menu → Integrations → Outgoing Webhooks → Add Outgoing Webhook
2. **Trigger Words:** `@concierge`
3. **Callback URLs:** `http://<BOT_BASE_URL>/webhook`
4. **Content Type:** `application/x-www-form-urlencoded`
5. Скопировать токен → вставить в `MM_WEBHOOK_TOKEN`
6. System Console → Environment → Developer → **Allow untrusted internal connections to:** добавить IP бота

### Бот-аккаунт
1. System Console → Integrations → Bot Accounts → Enable Bot Account Creation
2. Integrations → Bot Accounts → Add Bot Account
3. Создать Personal Access Token → вставить в `MM_API_TOKEN`
