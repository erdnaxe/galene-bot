#!/usr/bin/env python
# Copyright (C) 2021 Alexandre Iooss
# SPDX-License-Identifier: MIT
#
# IRCClient based on PyIRC by Benjamin Graillot, MIT licensed
# <https://gitlab.crans.org/esum/pyirc>

"""
IRC double-puppeting bridge.
"""

import asyncio
import re
import sys

from galene_bot import ArgumentParser, GaleneBot


class IRCClient:
    """Simple IRC client writting to a channel."""

    def __init__(
        self,
        rx_queue,
        tx_queue,
        server: str,
        port=None,
        tls=False,
        nickname="",
        channel="#flood",
    ):
        """Init IRC client.

        :param rx_queue: receive queue
        :type rx_queue: async.Queue
        :param tx_queue: transmit queue
        :type tx_queue: async.Queue
        :param server: server hostname to connect to
        :type server: str
        :param port: port to contact, defaults to 6697 for TLS, or 6667
        :type port: int, optional
        :param tls: enable TLS, defaults to False
        :type tls: bool, optional
        :param nickname: nickname to use, will also be username and realname
        :type nickname: str
        :param channel: channel to join after connection
        :type channel: str
        :raises ValueError: if nickname is empty
        """
        # Default port if none provided
        if port is None:
            port = 6697 if tls else 6667

        # Sanitize parameters
        if not nickname:
            raise ValueError("nickname must not be empty")

        self.rx_queue = rx_queue
        self.tx_queue = tx_queue
        self.server = server
        self.port = port
        self.tls = tls
        self.nickname = nickname
        self.channel = channel
        self.reader, self.writer = None, None
        self.joined = False

    async def _send(self, message: str):
        """Send message to IRC socket.

        :param message: message to send
        :type message: str
        """
        self.writer.write(f"{message}\r\n".encode())
        await self.writer.drain()

    async def _connect(self):
        """Connect to IRC server."""
        # Open socket
        self.reader, self.writer = await asyncio.open_connection(
            host=self.server, port=self.port, ssl=self.tls
        )

        # Log to IRC server
        await self._send(f"NICK {self.nickname}")
        await self._send(f"USER {self.nickname} 0 * :{self.nickname}")

    async def loop(self):
        """Receive from IRC loop."""
        await self._connect()

        while True:
            data = await self.reader.read(4096)
            data = data.decode("utf-8", "ignore").split("\r\n")
            for command in data:
                if command:
                    await self.process_command(command)

    async def loop_transmit(self):
        """Transmit to IRC loop."""
        # Wait for client to be connected
        while not self.joined:
            await asyncio.sleep(1)

        # For each incoming message, send
        while True:
            message = await self.rx_queue.get()
            for m in message.split("\n"):
                await self._send(f"PRIVMSG {self.channel} :{m}")
            self.rx_queue.task_done()

    async def process_command(self, cmd: str):
        """Process IRC command.

        :param cmd: received command
        :type cmd: str
        """
        # Parse IRC command
        match = re.match(
            r"^(?P<tags>@(?:(?:\+?(?:[0-9A-Za-z.-]+/)?[0-9A-Za-z-]+)(?:=[^\x00\r\n; ]+)?)?(?:;(?:\+?(?:[0-9A-Za-z.-]+/)?[0-9A-Za-z-]+)(?:=[^\x00\r\n; ]+)?)*)? *(?::(?P<target>[^ ]*))? *(?P<command>[a-zA-Z]+|[0-9]{3}) *(?:(?P<params>.*?))?$",
            cmd,
        )
        if match is None:
            print("Unknown command:", cmd)
            return
        command = match.group("command")

        # Implement actions
        if command == "PING":
            data = match.group("params")[1:]
            await self._send(f"PONG :{data}")
        elif command == "PRIVMSG":
            nickname = match.group("target").split("!")[0]
            message = match.group("params").split(":", 1)[-1]
            await self.tx_queue.put(f"<{nickname}> {message}")
        elif command == "JOIN":
            # User joined
            nickname = match.group("target").split("!")[0]
            await self.tx_queue.put(f"{nickname} joined")
        elif command == "QUIT":
            # User left
            nickname = match.group("target").split("!")[0]
            await self.tx_queue.put(f"{nickname} left")
        elif command == "001":
            # On welcome, join channel
            await self._send(f"JOIN {self.channel}")
            self.joined = True
        elif command == "433":
            # Nickname is already in use
            self.nickname = self.nickname + "_"
            await self._send(f"NICK {self.nickname}")
        elif command == "353":
            # List of users
            users = match.group("params").split(":", 1)[-1].split(" ")
            for user in users:
                await self.tx_queue.put(f"{user} joined")


class GaleneMainClient(GaleneBot):
    """Galène bot to observe room."""

    def __init__(self, rx_queue, tx_queue, *args, **kwargs):
        """Override init to get receive and transmit event queues.

        :param rx_queue: receive queue
        :type rx_queue: async.Queue
        :param tx_queue: transmit queue
        :type tx_queue: async.Queue
        """
        super().__init__(*args, **kwargs)
        self.rx_queue = rx_queue
        self.tx_queue = tx_queue

    async def loop_transmit(self):
        """Transmit to Galène loop."""
        # Wait for client to be connected
        while not self.joined:
            await asyncio.sleep(1)

        # For each incoming message, send
        while True:
            m = await self.rx_queue.get()
            await self.send_chat(m)
            self.rx_queue.task_done()

    async def on_chat(self, kind, _, username: str, value: str, time: int):
        """On new chat event.

        :param kind: kind of message, None if text message
        :type kind: str
        :param source: identifier of the sender
        :type source: str
        :param username: username of the sender
        :type username: str
        :param value: text message
        :type value: str
        :param time: time of the message
        :type time: int
        """
        # Get only new messages
        if self.is_history(time):
            return

        if kind == "me":
            # Action message
            await self.tx_queue.put(f"{username} {value}")
        else:
            # Standard message
            await self.tx_queue.put(f"<{username}> {value}")

    async def on_user_add(self, _, username: str):
        """User joined group event.

        :param username: username of the new user
        :type username: str
        """
        await self.tx_queue.put(f"{username} joined")

    async def on_user_delete(self, _, username: str):
        """User left group event.

        :param username: username of the leaving user
        :type username: str
        """
        await self.tx_queue.put(f"{username} left")


def main():
    """Entrypoint."""
    parser = ArgumentParser(
        prog="ircbridge",
        description="IRC-Galène bridge.",
    )
    parser.add_argument(
        "--irc_server",
        required=True,
        help="IRC server hostname",
    )
    parser.add_argument(
        "--irc_port",
        help="IRC port, defaults to 6697 for TLS, or 6667",
    )
    parser.add_argument(
        "--irc_tls",
        action="store_true",
        default=False,
        help="Use TLS for IRC, default to false",
    )
    parser.add_argument(
        "--irc_nickname",
        default="galenebridge",
        help="IRC nickname, default to galenebridge",
    )
    parser.add_argument(
        "--irc_channel",
        default="#flood",
        help="IRC channel, default to #flood",
    )
    opt = parser.parse_args()

    # Message queues for corroutine communication
    queue_galene_to_irc = asyncio.Queue()
    queue_irc_to_galene = asyncio.Queue()

    # Main client read messages and list users
    # Puppets only write messages
    # FIXME: implement puppeting
    main_irc_client = IRCClient(
        queue_galene_to_irc,
        queue_irc_to_galene,
        opt.irc_server,
        opt.irc_port,
        opt.irc_tls,
        opt.irc_nickname,
        opt.irc_channel,
    )
    main_galene_client = GaleneMainClient(
        queue_irc_to_galene,
        queue_galene_to_irc,
        opt.server,
        opt.group,
        opt.username,
        opt.password,
    )
    # puppet_irc_client = []
    # puppet_galene_client = []

    # Start main loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(
            asyncio.gather(
                main_irc_client.loop(),
                main_irc_client.loop_transmit(),
                main_galene_client.loop(),
                main_galene_client.loop_transmit(),
            )
        )
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    main()
