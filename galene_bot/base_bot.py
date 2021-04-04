# Copyright (C) 2021 Alexandre Iooss
# SPDX-License-Identifier: MIT

"""
Base class to implement a bot for Galène.
"""

import json
import logging
import secrets
import ssl
from datetime import datetime, timedelta

import websockets

log = logging.getLogger(__name__)


class GaleneBot:
    """Galène protocol implementation for bot."""

    def __init__(
        self,
        server: str,
        group: str,
        username: str,
        password="",
        client_id=None,
    ):
        """Create GaleneBot.

        :param server: websocket url to connect to
        :type server: str
        :param group: group to join
        :type group: str
        :param username: group user name
        :type username: str
        :param password: group user password if required
        :type password: str, optional
        :param client_id: client identifier, defaults to random
        :type client_id: str, optional
        """
        if client_id is None:
            # Create random client id
            client_id = secrets.token_bytes(16).hex()

        self.server = server
        self.group = group
        self.username = username
        self.password = password
        self.client_id = client_id
        self.conn = None  # websocket connection

        # Status
        self.joined = False
        self.users = {}  # Map user id to name

    async def send(self, message: dict):
        """Send message to remote.

        :param message: message to send
        :type message: dict
        """
        message = json.dumps(message)
        await self.conn.send(message)

    async def send_chat(self, value="", dest="", kind=""):
        """Send chat message.

        :param value: content of the message, defaults to ""
        :type value: str, optional
        :param dest: destination, defaults to broadcast
        :type dest: str, optional
        :param kind: Kind of message, can be "me" or "", defaults to ""
        :type kind: str, optional
        """
        await self.send(
            {
                "type": "chat",
                "kind": kind,
                "source": self.client_id,
                "username": self.username,
                "dest": dest,
                "value": value,
            }
        )

    @staticmethod
    def is_history(time: datetime, time_frame=5):
        """Check if time is in the past.

        :param time: time of the event
        :type time: datetime
        :param time_frame: time frame in seconds, defaults to 5
        :type time_frame: int, optional
        :return if time is before now (with margin of time frame)
        """
        return time + timedelta(seconds=time_frame) < datetime.now()

    async def _connect(self):
        """Connect to server."""
        # Create WebSocket
        log.info(f"Connecting to {self.server}")
        ssl_ctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        self.conn = await websockets.connect(self.server, ssl=ssl_ctx)

        # Handshake with server
        log.debug("Handshaking")
        msg = {
            "type": "handshake",
            "id": self.client_id,
        }
        await self.send(msg)
        await self.conn.recv()  # wait for handshake

        # Join group
        log.info(f"Joining {self.group} as {self.username}")
        msg = {
            "type": "join",
            "kind": "join",
            "group": self.group,
            "username": self.username,
            "password": self.password,
        }
        await self.send(msg)

    async def loop(self):
        """Client loop."""
        await self._connect()

        async for message in self.conn:
            message = json.loads(message)
            if message["type"] == "ping":
                # Need to answer pong to ping request to keep connection
                await self.send({"type": "pong"})
            elif message["type"] == ["abort", "answer", "ice", "renegotiate"]:
                # Ignore as we do not stream media
                continue
            elif message["type"] == "usermessage":
                # Server is sending us a message
                value = message.get("value")
                if message["kind"] == "error":
                    log.error(f"Server returned error: {value}")
                    break
                else:
                    log.warn(f"Not implemented {message}")
            elif message["type"] == "joined":
                # Response to the group join request
                if message.get("kind") != "join":
                    log.error("Failed to join room")
                    break
                self.joined = True
            elif message["type"] == "user":
                # User joined or left
                user_id = message.get("id")
                username = message.get("username", "(anon)")
                if message["kind"] == "add":
                    self.users[user_id] = username
                    await self.on_user_add(user_id, username)
                elif message["kind"] == "delete":
                    del self.users[user_id]
                    await self.on_user_delete(user_id, username)
                else:
                    log.warn(f"Not implemented {message}")
            elif message["type"] == "chat":
                # New chat message
                kind = message.get("kind")
                source = message.get("source")
                username = message.get("username", "(anon)")
                value = message.get("value", "")
                time = message.get("time", 0)
                if time > 0:
                    time = datetime.fromtimestamp(time / 1000)
                await self.on_chat(kind, source, username, value, time)
            else:
                # Oh no! We receive something not implemented
                log.warn(f"Not implemented {message}")

    async def on_user_add(self, user_id: str, username: str):
        """User joined group event.

        :param user_id: identifier of the new user
        :type user_id: str
        :param username: username of the new user
        :type username: str
        """
        pass

    async def on_user_delete(self, user_id: str, username: str):
        """User left group event.

        :param user_id: identifier of the leaving user
        :type user_id: str
        :param username: username of the leaving user
        :type username: str
        """
        pass

    async def on_chat(
        self, kind: str, source: str, username: str, value: str, time: int
    ):
        """On new chat event.

        :param source: identifier of the sender
        :type source: str
        :param kind: kind of message, None if text message
        :type kind: str
        :param username: username of the new user
        :type username: str
        :param value: text message
        :type value: str
        :param time: time of the message
        :type time: int
        """
        pass
