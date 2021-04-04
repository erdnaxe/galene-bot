#!/usr/bin/env python
# Copyright (C) 2021 Alexandre Iooss
# SPDX-License-Identifier: MIT

"""
Smile bot.
"""

import asyncio
import sys
from datetime import datetime, timedelta

from galene_bot import ArgumentParser, GaleneBot


class SmileBot(GaleneBot):
    """A bot that smiles back to sad users."""

    smiles = {
        ":(": ":)",
        "D:": ":D",
        ":-(": ":-)",
        "🙁": "🙂",
    }

    async def on_chat(self, _, __, ___, value: str, time: int):
        """On new chat event.

        :param value: text message
        :type value: str
        :param time: time of the message
        :type time: int
        """
        # Get only new messages
        if self.is_history(time):
            return

        # Make user happy
        for sad_smile, happy_smile in self.smiles.items():
            if sad_smile in value:
                if len(sad_smile) + 1 < len(value) and f" {sad_smile} " not in f" {value} ":
                    return  # This is not really a sad message

                await self.send_chat(happy_smile)
                return


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
