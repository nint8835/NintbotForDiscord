import os
import random

from pymarkovchain import MarkovChain

from NintbotForDiscord.Permissions import Permission
from NintbotForDiscord.Permissions.Special import Owner
from NintbotForDiscord.Plugin import BasePlugin

__author__ = 'Riley Flynn (nint8835)'


class Plugin(BasePlugin):
    def __init__(self, manifest, bot_instance):
        super(Plugin, self).__init__(manifest, bot_instance)
        self.artists = []
        self.songs = []
        self.chain = MarkovChain()
        self.title_chain = MarkovChain()
        self.artist_chain = MarkovChain()

        self.bot.CommandRegistry.register_command("lyricchain",
                                                  "Generates text using markov chains of song lyrics.",
                                                  Permission(),
                                                  self,
                                                  self.command_lyricchain)

        self.bot.CommandRegistry.register_command("reloadlyrics",
                                                  "Reloads the song lyrics.",
                                                  Owner(self.bot),
                                                  self,
                                                  self.command_reloadlyrics)

        self.bot.CommandRegistry.register_command("songlist",
                                                  "Gets a list of all songs the bot is basing it's knowledge off of",
                                                  Owner(self.bot),
                                                  self,
                                                  self.command_songlist)

        self.load_lyrics()

    async def command_lyricchain(self, args):
        await args.channel.send("\"{}\" -{} by {}".format(self.chain.generateString(),
                                                          self.title_chain.generateString(),
                                                          self.artist_chain.generateString()))

    async def command_reloadlyrics(self, args):
        self.load_lyrics()

    async def command_songlist(self, args):
        message = ""
        for song in self.songs:
            if len(message) + 2 + len(song) >= 2000:
                await args.channel.send(message)
                message = song
            elif message == "":
                message = song
            else:
                message += "\n{}".format(song)
        if message != "":
            await args.channel.send(message)

    def load_lyrics(self):
        self.artists = []
        self.songs = []
        lyrics = []
        song_titles = []
        for item in os.listdir(os.path.join(self.manifest["path"], "lyrics")):
            self.songs.append(item)
            with open(os.path.join(self.manifest["path"], "lyrics", item)) as f:
                song_titles.append(item.split("- ")[1])
                artist = item.split(" -")[0]
                if artist not in self.artists:
                    self.artists.append(artist)
                lyrics.append(f.read())
        self.chain.generateDatabase("\n".join(lyrics))
        self.title_chain.generateDatabase("\n".join(song_titles))
        self.artist_chain.generateDatabase("\n".join(self.artists))
