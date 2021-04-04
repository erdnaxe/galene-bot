#!/usr/bin/env python
# Copyright (C) 2021 Alexandre Iooss
# SPDX-License-Identifier: MIT

"""
Welcome new users.
"""

from datetime import datetime
import random

from galene_bot import ArgumentParser, GaleneBot


class WelcomeBot(GaleneBot):
    """A bot that welcomes new users."""

    welcome_msg = [
        "Hello {username} o/",
        "Welcome {username}",
        "Hi {username}!",
        "Greetings {username}!",
        "Hurrah, {username} joined!",
        "{username} joined the group :)",
        "{username} enterred the room.",
    ]

    leave_msg = [
        "See you {username}!",
        "I hope you had a nice time {username}!",
        "Oh! {username} disappeared.",
        "{username} exited the group.",
    ]

    # Let's give a fantasy nickname to anonymous users.
    # Please note that the join/leave name will not match and that's a feature.
    anonymous_usernames = [
        "Batman",
        "Robin",
        "anonymous user",
        "hidden person",
        "shadow",
        "[insert nick]",
        "Zorro",
        "???",
    ]

    def __init__(self, *args, **kwargs):
        """Override init to get time."""
        super().__init__(*args, **kwargs)
        self.init_time = datetime.now()

    async def on_user_add(self, user_id: str, username: str):
        """User joined group event.

        :param user_id: identifier of the new user
        :type user_id: str
        :param username: username of the new user
        :type username: str
        """
        # Skip first 5s events to ignore old users
        if not self.is_history(self.init_time):
            return

        # Invent a name for anonymous users
        if username == "(anon)":
            username = random.choice(self.anonymous_usernames)

        msg = random.choice(self.welcome_msg).format(username=username)
        await self.send_chat(msg)

    async def on_user_delete(self, user_id: str, username: str):
        """User left group event.

        :param user_id: identifier of the leaving user
        :type user_id: str
        :param username: username of the leaving user
        :type username: str
        """
        # Skip first 5s events to ignore old users
        if not self.is_history(self.init_time):
            return

        # Invent a name for anonymous users
        if username == "(anon)":
            username = random.choice(self.anonymous_usernames)

        msg = random.choice(self.leave_msg).format(username=username)
        await self.send_chat(msg)


def main():
    """Entrypoint."""
    parser = ArgumentParser(
        prog="welcomebit",
        description="A bot that welcomes new users.",
    )
    parser.run(WelcomeBot)


if __name__ == "__main__":
    main()
