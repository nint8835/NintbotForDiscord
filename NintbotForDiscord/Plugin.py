import logging

from NintbotForDiscord.Enums import EventTypes
from NintbotForDiscord.Permissions import Permission
from jigsaw import JigsawPlugin

__author__ = 'Riley Flynn (nint8835)'


class BasePlugin(JigsawPlugin):

    def __init__(self, manifest, bot_instance):
        super(BasePlugin, self).__init__(manifest)

        self.bot = bot_instance  # type: Bot.Bot

        self.plugin_info = {
            "plugin_name": self.manifest.get("name", "Unnamed Plugin"),
            "plugin_developer": self.manifest.get("developer", "Unspecified Developer"),
            "plugin_version": self.manifest.get("version", "0.0.0"),
            "module_name": self.manifest.get("module_name", self.manifest.get("name", "Unnamed Plugin")),
            "main_file": self.manifest.get("main_path", "__init__.py")
        }

        self._registered_commands = []
        self._registered_handlers = []

        self.logger = logging.getLogger(self.plugin_info["plugin_name"])

    def register_command(self, name: str, description: str, method: classmethod, permission: Permission = Permission()) -> None:
        """
        Adds a command to the internal command registry to be auto-registered/unregistered on enable/disable
        :param name: The command name
        :param description: The command description
        :param method: The method that will handle the command
        :param permission: The permission required to use the command
        """
        self._registered_commands.append({
            "command": name,
            "description": description,
            "required_perm": permission,
            "plugin_info": self.plugin_info,
            "command_handler": method
        })

    def register_handler(self, event_type: EventTypes, event_handler: classmethod) -> None:
        """
        Adds a handler to the internal handler registry to be auto-registered/unregistered on enable/disable
        :param event_type: The type of event this handler will handle
        :param event_handler: The method that will handle the event
        """
        self._registered_handlers.append({
            "event_type": event_type,
            "event_handler": event_handler,
            "plugin": self
        })
