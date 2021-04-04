# Copyright (C) 2021 Alexandre Iooss
# SPDX-License-Identifier: MIT

"""
Implement an argument parser for a bot.
"""

import argparse
import asyncio
import logging
import sys


class ArgumentParser(argparse.ArgumentParser):
    """Argument parser for a bot that also configures logging."""

    def __init__(self, *args, **kwargs):
        """Override argparse init to add arguments."""
        super().__init__(*args, **kwargs)

        # Add common arguments
        self.add_argument(
            "--debug",
            action="store_true",
            default=False,
            help="debug mode: show debug messages",
        )
        self.add_argument(
            "-s",
            "--server",
            required=True,
            help='Galène server to connect to, e.g. "wss://galene.example.com/ws"',
        )
        self.add_argument(
            "-g",
            "--group",
            required=True,
            help="Join this group",
        )
        self.add_argument(
            "-u",
            "--username",
            required=True,
            help="Group username",
        )
        self.add_argument(
            "-p",
            "--password",
            help="Group password",
        )

    def parse_args(self, *args, **kwargs):
        """Override argparse parse_args to configure logging."""
        options = super().parse_args(*args, **kwargs)

        # Configure logging
        level = logging.DEBUG if options.debug else logging.INFO
        logging.addLevelName(logging.INFO, "\033[1;36mINFO\033[1;0m")
        logging.addLevelName(logging.WARNING, "\033[1;33mWARNING\033[1;0m")
        logging.addLevelName(logging.ERROR, "\033[1;91mERROR\033[1;0m")
        logging.addLevelName(logging.DEBUG, "\033[1;30mDEBUG")
        logging.basicConfig(
            level=level,
            format="\033[90m%(asctime)s\033[1;0m [%(name)s] %(levelname)s %(message)s\033[1;0m",
        )
        return options

    def run(self, BotClass, *args, **kwargs):
        """Run bot.

        :param BotClass: Bot class.
        :type BotClass: GaleneBot
        """
        opt = self.parse_args()
        client = BotClass(
            opt.server, opt.group, opt.username, opt.password, *args, **kwargs
        )
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(client.loop())
        except KeyboardInterrupt:
            sys.exit(1)
