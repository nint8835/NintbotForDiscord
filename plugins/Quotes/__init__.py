import random
import traceback
import os
import datetime

from pymarkovchain import MarkovChain

from NintbotForDiscord.Permissions.Special import Owner
from NintbotForDiscord.Permissions.Text import ManageMessages
from NintbotForDiscord.Plugin import BasePlugin
from NintbotForDiscord.Permissions import Permission, create_match_any_permission_group

from libraries.JSONDB import JSONDatabase, SelectionMode
__author__ = 'Riley Flynn (nint8835)'


class Plugin(BasePlugin):

    def __init__(self, bot_instance, plugin_data, folder):
        super(Plugin, self).__init__(bot_instance, plugin_data, folder)
        self.admin = create_match_any_permission_group([Owner(self.bot), ManageMessages()])
        self.bot.CommandRegistry.register_command("quote",
                                                  "View and manage quotes.",
                                                  Permission(),
                                                  plugin_data,
                                                  self.on_command)
        self.quotes = JSONDatabase(os.path.join(self.folder, "quotes.json"))
        self.markov = MarkovChain()
        self.generate_chain()

    def generate_chain(self):
        self.markov.generateDatabase("\n".join([i["msg"] for i in self.quotes.data]))

    async def on_command(self, args):
        if len(args["command_args"])>=4:
            if args["command_args"][1] == "add" and self.admin.has_permission(args["author"]):
                try:
                    quote_msg = args["command_args"][2]
                    quote_author = " ".join(args["command_args"][3:])
                    quote_addtime = datetime.datetime.now().strftime("%x %X")
                    self.quotes.insert({"msg": quote_msg,
                                        "author": quote_author,
                                        "added_at": quote_addtime})
                    await self.bot.send_message(args["channel"], ":ballot_box_with_check: New quote added to database.")
                    self.generate_chain()
                except:
                    traceback.print_exc(5)
        elif len(args["command_args"]) == 2:
            if args["command_args"][1] == "markov":
                await self.bot.send_message(args["channel"], "\"{}\" {}".format(self.markov.generateString(),
                                                                                random.choice(self.quotes.data)["author"]))
            elif args["command_args"][1] == "tts":
                await self.bot.send_message(args["channel"], "\n".join([random.choice(self.quotes.data)["msg"] for i in range(5)]), tts=True)
            else:
                quotes = [quote["msg"] for quote in self.quotes.data if quote["author"].count(args["command_args"][1]) >= 1]
                message = ""
                for quote in quotes:
                    if len(message) + 2 + len(quote) >= 2000:
                        await self.bot.send_message(args["channel"], message)
                        message = quote
                    elif message == "":
                        message = quote
                    else:
                        message += "\n{}".format(quote)
                if message != "":
                    await self.bot.send_message(args["channel"], message)

        elif len(args["command_args"]) == 1:
            quote = random.choice(self.quotes.select(SelectionMode.ALL).rows)
            await self.bot.send_message(args["channel"], "\"{}\" {}".format(quote["msg"], quote["author"]))
