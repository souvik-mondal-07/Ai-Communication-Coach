"""
Request body size limit.

Pydantic bounds every field, but only *after* the whole body has been read and parsed.
This middleware rejects an oversized body up front — by its `Content-Length`, or, for
chunked uploads that don't declare one, as the bytes stream in — so a client can't make
the server buffer megabytes of JSON just to be told "too long".

Audio upload routes are exempt: they enforce their own (larger) limit while streaming
(`VOICE_MAX_AUDIO_BYTES`) and answer with the same 413.
"""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_BODYLESS_METHODS = {"GET", "HEAD", "OPTIONS", "DELETE"}


class _BodyTooLarge(Exception):
    pass


# Same envelope as every other error response (see core.error_handlers).
_REJECTION_BODY = json.dumps(
    {"success": False, "message": "The request is too large.", "error_code": "PAYLOAD_TOO_LARGE"}
).encode()


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_bytes: int, exempt_prefixes: tuple[str, ...] = ()) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.exempt_prefixes = exempt_prefixes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] in _BODYLESS_METHODS
            or scope["path"].startswith(self.exempt_prefixes)
        ):
            await self.app(scope, receive, send)
            return

        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None:
            try:
                too_large = int(declared) > self.max_bytes
            except ValueError:
                too_large = False  # a malformed header is the server's problem, not ours
            if too_large:
                await self._reject(send)
                return

        received = 0
        exceeded = False
        response_started = False
        body_sent = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    exceeded = True
                    raise _BodyTooLarge
            return message

        async def tracking_send(message: Message) -> None:
            # FastAPI catches any exception raised while it reads the body and answers 400.
            # Once the limit has been exceeded, swap whatever the app sends for our 413.
            nonlocal response_started, body_sent
            if exceeded:
                if message["type"] == "http.response.start" and not response_started:
                    response_started = True
                    await send(self._start_message(len(_REJECTION_BODY)))
                elif message["type"] == "http.response.body" and not body_sent:
                    body_sent = True
                    await send({"type": "http.response.body", "body": _REJECTION_BODY})
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _BodyTooLarge:
            if not response_started:
                await self._reject(send)
            elif not body_sent:
                await send({"type": "http.response.body", "body": _REJECTION_BODY})

    @staticmethod
    def _start_message(length: int) -> Message:
        return {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(length).encode()),
                (b"connection", b"close"),
            ],
        }

    @classmethod
    async def _reject(cls, send: Send) -> None:
        await send(cls._start_message(len(_REJECTION_BODY)))
        await send({"type": "http.response.body", "body": _REJECTION_BODY})
