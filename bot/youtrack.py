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

    async def get_reporter_issues(self, project_names: list[str] | None = None, max_count: int = 50) -> list[dict]:
        query = "reporter: me"
        if project_names:
            projects_filter = " ".join(f"project: {{{n}}}" for n in project_names)
            query = f"reporter: me {projects_filter}"
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self._url}/api/issues",
                params={"query": query, "fields": "id,idReadable,summary", "$top": max_count},
                headers=self._headers,
                timeout=15,
            )
        if r.status_code != 200:
            logger.error("YouTrack get_reporter_issues error %s: %s", r.status_code, r.text)
            return []
        return r.json()

    async def add_comment(self, issue_id: str, text: str) -> None:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self._url}/api/issues/{issue_id}/comments",
                json={"text": text},
                headers=self._headers,
                timeout=15,
            )
        if r.status_code not in (200, 201):
            logger.error("YouTrack add_comment error %s: %s", r.status_code, r.text)
            r.raise_for_status()
