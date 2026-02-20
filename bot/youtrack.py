import logging

import httpx

logger = logging.getLogger(__name__)


class YouTrackClient:
    def __init__(self, url: str, token: str) -> None:
        self._url = url
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_issue(self, project_id: str, summary: str, description: str, assignee: str = "") -> dict:
        body: dict = {
            "project": {"id": project_id},
            "summary": summary,
            "description": description,
        }
        if assignee:
            body["customFields"] = [
                {
                    "$type": "SingleUserIssueCustomField",
                    "name": "Assignee",
                    "value": {"$type": "User", "login": assignee},
                }
            ]
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self._url}/api/issues?fields=id,idReadable,summary",
                json=body,
                headers=self._headers,
                timeout=15,
            )
        if r.status_code not in (200, 201):
            logger.error("YouTrack create_issue error %s: %s", r.status_code, r.text)
            r.raise_for_status()
        return r.json()
