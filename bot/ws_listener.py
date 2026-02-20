import asyncio
import json
import logging
import ssl
from typing import Awaitable, Callable

import websockets

logger = logging.getLogger(__name__)


async def listen(
    mm_url: str,
    token: str,
    listen_channels: list[str],
    on_mention: Callable[[str], Awaitable[None]],
) -> None:
    ws_url = mm_url.replace("https://", "wss://").replace("http://", "ws://") + "/api/v4/websocket"

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    while True:
        try:
            logger.info("ws: connecting to %s", ws_url)
            async with websockets.connect(ws_url, ssl=ssl_ctx) as ws:
                await ws.send(json.dumps({
                    "seq": 1,
                    "action": "authentication_challenge",
                    "data": {"token": token},
                }))
                logger.info("ws: connected and authenticated")

                async for raw in ws:
                    try:
                        event = json.loads(raw)
                    except Exception:
                        continue

                    if event.get("event") != "posted":
                        continue

                    data = event.get("data", {})
                    try:
                        post = json.loads(data.get("post", "{}"))
                    except Exception:
                        continue

                    channel_id = post.get("channel_id", "")
                    text = post.get("message", "")

                    if listen_channels and channel_id not in listen_channels:
                        continue

                    if "@concierge" in text.lower():
                        logger.info("ws: @concierge mention in channel %s", channel_id)
                        await on_mention(channel_id)

        except asyncio.CancelledError:
            logger.info("ws: listener stopped")
            break
        except Exception as e:
            logger.error("ws: error %s, reconnect in 5s", e)
            await asyncio.sleep(5)
