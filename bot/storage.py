import json
import logging
import os

logger = logging.getLogger(__name__)

_STORAGE_PATH = os.environ.get("STORAGE_PATH", "data/issues.json")


def _load() -> dict:
    if not os.path.exists(_STORAGE_PATH):
        return {}
    try:
        with open(_STORAGE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("storage: failed to load %s: %s", _STORAGE_PATH, e)
        return {}


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(_STORAGE_PATH)), exist_ok=True)
    with open(_STORAGE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_issue(issue_id: str, post_id: str, channel_id: str) -> None:
    data = _load()
    data[issue_id] = {"post_id": post_id, "channel_id": channel_id}
    _save(data)
    logger.info("storage: saved %s → post_id=%s", issue_id, post_id)


def get_issue(issue_id: str) -> dict | None:
    return _load().get(issue_id)
