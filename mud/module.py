"""
MODULE
"""
import logging
from mud.injector import Injector


class Module(Injector):
    """An extension of the Game."""
    def handle_event(self, event):
        return event

    def log(self, *args):
        logging.info(args)
