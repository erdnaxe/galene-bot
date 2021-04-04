#!/usr/bin/env python
# Copyright (C) 2021 Alexandre Iooss
# SPDX-License-Identifier: MIT

"""
Smile bot.
"""

import asyncio
import sys

from galene_bot.base_bot import GaleneBot
from galene_bot.base_argparse import ArgumentParser


class SmileBot(GaleneBot):
    """A bot that smiles back to sad users."""

    async def on_chat(self, kind: str, source: str, username: str, value: str, time: int):
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
        if ":(" in value:
            await self.send_chat(":)")


def main():
    """Entrypoint."""
    # Arguments parser
    parser = ArgumentParser(
        prog="smilebot",
        description="A bot that smiles.",
    )
    opt = parser.parse_args()

    # Run
    client = SmileBot(opt.server, opt.group, opt.username, opt.password)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.loop())
    except KeyboardInterrupt:
        sys.exit(1)


if __name__ == "__main__":
    main()
