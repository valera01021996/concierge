import logging

import httpx

logger = logging.getLogger(__name__)


class MattermostClient:
    def __init__(self, url: str, token: str) -> None:
        self._url = url
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def post_message(self, channel_id: str, text: str, root_id: str = "") -> dict:
        payload: dict = {"channel_id": channel_id, "message": text}
        if root_id:
            payload["root_id"] = root_id
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.post(
                f"{self._url}/api/v4/posts",
                json=payload,
                headers=self._headers,
                timeout=10,
            )
        if r.status_code not in (200, 201):
            logger.error("Mattermost post_message error %s: %s", r.status_code, r.text)
            return {}
        return r.json()

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
                                "name": "Создать заявку",
                                "type": "button",
                                "style": "primary",
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

    async def remove_post_actions(self, post_id: str) -> None:
        """Remove buttons from a post by updating it without actions."""
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.put(
                f"{self._url}/api/v4/posts/{post_id}/patch",
                json={"props": {"attachments": []}},
                headers=self._headers,
                timeout=10,
            )
        if r.status_code not in (200, 201):
            logger.error("remove_post_actions error %s: %s", r.status_code, r.text)
