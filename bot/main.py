import asyncio
import logging
import os
from contextlib import asynccontextmanager

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from bot import ws_listener
from bot.checklist import Checklist, load_checklist
from bot.config import load_config
from bot.mattermost import MattermostClient
from bot.youtrack import YouTrackClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Startup: load config and projects
# ---------------------------------------------------------------------------

CONFIG_PATH = os.environ.get("CONFIG_PATH", "config/config.yaml")
cfg = load_config(CONFIG_PATH)

with open(cfg.paths.projects_config, encoding="utf-8") as _f:
    PROJECTS: list[dict] = yaml.safe_load(_f).get("projects", [])

CHECKLISTS: dict[str, Checklist] = {}
for _p in PROJECTS:
    _path = os.path.join(cfg.paths.checklists_dir, _p["checklist_file"])
    CHECKLISTS[_p["id"]] = load_checklist(_path)

mm = MattermostClient(cfg.mattermost.url, cfg.mattermost.api_token)
yt = YouTrackClient(cfg.youtrack.url, cfg.youtrack.token)


async def _on_ws_mention(channel_id: str) -> None:
    await mm.post_button_message(channel_id, ACTION_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if cfg.mattermost.listen_channels is not None:
        task = asyncio.create_task(
            ws_listener.listen(
                cfg.mattermost.url,
                cfg.mattermost.api_token,
                cfg.mattermost.listen_channels,
                _on_ws_mention,
            )
        )
        logger.info("ws: listener started for channels: %s", cfg.mattermost.listen_channels)
    yield
    if task:
        task.cancel()


app = FastAPI(lifespan=lifespan)

# ---------------------------------------------------------------------------
# Dialog builders
# ---------------------------------------------------------------------------

DIALOG_URL = f"{cfg.base_url}/dialog"
ACTION_URL = f"{cfg.base_url}/action"


def _project_select_dialog() -> dict:
    return {
        "callback_id": "project_select",
        "title": "Concierge — выбор проекта",
        "submit_label": "Далее",
        "elements": [
            {
                "display_name": "Проект",
                "name": "project_id",
                "type": "select",
                "options": [{"text": p["name"], "value": p["id"]} for p in PROJECTS],
            }
        ],
    }


def _update_dialog(issues: list[dict]) -> dict:
    options = [
        {
            "text": f"{i.get('idReadable', i.get('id'))} — {i.get('summary', '')[:60]}",
            "value": i.get("idReadable") or i.get("id"),
        }
        for i in issues
    ]
    return {
        "callback_id": "update",
        "title": "Обновить тикет",
        "submit_label": "Добавить комментарий",
        "elements": [
            {
                "display_name": "Тикет",
                "name": "issue_id",
                "type": "select",
                "optional": False,
                "options": options,
            },
            {
                "display_name": "Комментарий",
                "name": "comment",
                "type": "textarea",
                "placeholder": "Введите комментарий к тикету",
                "optional": False,
            },
        ],
    }


def _checklist_dialog(project: dict) -> dict:
    checklist = CHECKLISTS[project["id"]]
    elements = [
        {
            "display_name": q.id.replace("_", " ").title(),
            "name": q.id,
            "type": "textarea",
            "placeholder": q.text,
            "optional": False,
        }
        for q in checklist.questions
    ]
    return {
        "callback_id": f"checklist:{project['id']}",
        "title": project["name"],
        "submit_label": "Создать тикет",
        "elements": elements,
    }


# ---------------------------------------------------------------------------
# Ticket creation
# ---------------------------------------------------------------------------


async def _create_ticket(project: dict, answers: dict, channel_id: str) -> None:
    fm: dict = project.get("youtrack", {}).get("field_mapping", {})

    summary_key = next((k for k, v in fm.items() if v == "summary"), None)
    desc_key = next((k for k, v in fm.items() if v == "description"), None)

    summary = answers.get(summary_key) or "Новая заявка"

    desc_parts: list[str] = []
    if desc_key and answers.get(desc_key):
        desc_parts.append(answers[desc_key])

    extra = {
        k: v
        for k, v in answers.items()
        if k not in (summary_key, desc_key) and v
    }
    if extra:
        if desc_parts:
            desc_parts.append("\n---")
        for k, v in extra.items():
            yt_name = fm.get(k, k)
            label = yt_name if yt_name not in ("summary", "description") else k.replace("_", " ").title()
            desc_parts.append(f"**{label}:** {v}")

    description = "\n".join(desc_parts)
    project_id = project.get("youtrack", {}).get("project_id", cfg.youtrack.default_project)

    try:
        assignee = project.get("youtrack", {}).get("assignee", "")
        issue = await yt.create_issue(project_id, summary, description, assignee)
        issue_id = issue.get("idReadable") or issue.get("id", "?")
        url = f"{cfg.youtrack.url}/issue/{issue_id}"
        first_question_id = CHECKLISTS[project["id"]].questions[0].id
        first_answer = answers.get(first_question_id, "")
        heading = f"### {first_answer}\n" if first_answer else ""
        await mm.post_message(channel_id, f"{heading}Тикет создан: **{issue_id}**\n{url}")
    except Exception as e:
        logger.error("Failed to create YouTrack issue: %s", e)
        await mm.post_message(channel_id, "Не удалось создать тикет в YouTrack. Обратитесь к администратору.")


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/slash")
async def slash_command(request: Request):
    """Handles /concierge slash command — opens an interactive dialog."""
    form = await request.form()

    if form.get("token") != cfg.mattermost.slash_token:
        return JSONResponse({"text": "Unauthorized"}, status_code=401)

    trigger_id = str(form.get("trigger_id", ""))
    subcommand = str(form.get("text", "")).strip().lower()

    if subcommand == "update":
        project_names = [p.get("youtrack", {}).get("project_short_name", "") for p in PROJECTS if p.get("youtrack", {}).get("project_short_name")]
        issues = await yt.get_reporter_issues(project_names=project_names)
        if not issues:
            return JSONResponse({"text": "Нет доступных тикетов для обновления."})
        await mm.open_dialog(trigger_id, DIALOG_URL, _update_dialog(issues))
    else:
        if len(PROJECTS) == 1:
            dialog = _checklist_dialog(PROJECTS[0])
        else:
            dialog = _project_select_dialog()
        await mm.open_dialog(trigger_id, DIALOG_URL, dialog)

    return JSONResponse({})


@app.post("/webhook")
async def outgoing_webhook(request: Request):
    """Handles @concierge mention — posts a button message."""
    form = await request.form()
    received_token = str(form.get("token", ""))

    if received_token != cfg.mattermost.webhook_token:
        logger.warning("webhook: token mismatch received=%r expected=%r", received_token, cfg.mattermost.webhook_token)
        return JSONResponse({})

    channel_id = str(form.get("channel_id", ""))
    logger.info("webhook: channel_id=%r action_url=%s", channel_id, ACTION_URL)
    await mm.post_button_message(channel_id, ACTION_URL)
    return JSONResponse({})


@app.post("/action")
async def button_action(request: Request):
    """Handles button click — opens the dialog."""
    import json as _json
    body_bytes = await request.body()
    logger.info("action: content-type=%s body=%r", request.headers.get("content-type"), body_bytes[:300])
    try:
        body = _json.loads(body_bytes)
    except Exception:
        body = {}
    trigger_id = str(body.get("trigger_id", ""))
    post_id = str(body.get("post_id", ""))
    logger.info("action: trigger_id=%r post_id=%r", trigger_id, post_id)

    if not trigger_id:
        logger.warning("action: no trigger_id received, cannot open dialog")
        return JSONResponse({})

    if len(PROJECTS) == 1:
        dialog = _checklist_dialog(PROJECTS[0])
    else:
        dialog = _project_select_dialog()

    await mm.open_dialog(trigger_id, DIALOG_URL, dialog)

    if post_id:
        await mm.remove_post_actions(post_id)

    return JSONResponse({})


@app.post("/dialog")
async def dialog_submit(request: Request):
    """Handles interactive dialog submissions from Mattermost."""
    body = await request.json()

    if body.get("cancelled"):
        return JSONResponse({})

    callback_id: str = body.get("callback_id", "")
    channel_id: str = body.get("channel_id", "")
    trigger_id: str = body.get("trigger_id", "")
    submission: dict = body.get("submission", {})

    if callback_id == "project_select":
        project_id = submission.get("project_id", "")
        project = next((p for p in PROJECTS if p["id"] == project_id), None)
        if not project:
            return JSONResponse({"error": "Проект не найден"})
        await mm.open_dialog(trigger_id, DIALOG_URL, _checklist_dialog(project))
        return JSONResponse({})

    if callback_id.startswith("checklist:"):
        project_id = callback_id.split(":", 1)[1]
        project = next((p for p in PROJECTS if p["id"] == project_id), None)
        if project:
            await _create_ticket(project, submission, channel_id)
        return JSONResponse({})

    if callback_id == "update":
        issue_id = submission.get("issue_id", "")
        comment = submission.get("comment", "")
        if issue_id and comment:
            try:
                await yt.add_comment(issue_id, comment)
                url = f"{cfg.youtrack.url}/issue/{issue_id}"
                await mm.post_message(channel_id, f"Комментарий добавлен к тикету **{issue_id}**\n{url}")
            except Exception as e:
                logger.error("Failed to add comment to %s: %s", issue_id, e)
                await mm.post_message(channel_id, "Не удалось добавить комментарий. Обратитесь к администратору.")
        return JSONResponse({})

    return JSONResponse({})
