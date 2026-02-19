import logging
import uuid

import httpx

logger = logging.getLogger(__name__)


class MattermostClient:
    def __init__(self, url: str, token: str) -> None:
        self._url = url
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def post_message(self, channel_id: str, text: str) -> None:
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.post(
                f"{self._url}/api/v4/posts",
                json={"channel_id": channel_id, "message": text},
                headers=self._headers,
                timeout=10,
            )
        if r.status_code not in (200, 201):
            logger.error("Mattermost post_message error %s: %s", r.status_code, r.text)

    async def post_button_message(self, channel_id: str, action_url: str) -> None:
        payload = {
            "channel_id": channel_id,
            "message": "",
            "props": {
                "attachments": [
                    {
                        "text": "Нажмите кнопку чтобы создать заявку в YouTrack",
                        "actions": [
                            {
                                "id": str(uuid.uuid4()),
                                "name": "Создать заявку",
                                "type": "button",
                                "integration": {
                                    "url": action_url,
                                    "context": {"action": "open_dialog"},
                                },
                            }
                        ],
                    }
                ]
            },
        }
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.post(
                f"{self._url}/api/v4/posts",
                json=payload,
                headers=self._headers,
                timeout=10,
            )
        if r.status_code not in (200, 201):
            logger.error("post_button_message error %s: %s", r.status_code, r.text)

    async def open_dialog(self, trigger_id: str, callback_url: str, dialog: dict) -> None:
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.post(
                f"{self._url}/api/v4/actions/dialogs/open",
                json={"trigger_id": trigger_id, "url": callback_url, "dialog": dialog},
                headers=self._headers,
                timeout=10,
            )
        if r.status_code != 200:
            logger.error("open_dialog error %s: %s", r.status_code, r.text)
