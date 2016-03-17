import shlex
import subprocess
import os
import json
import math
import asyncio
import traceback
import logging

import youtube_dl
from googleapiclient.discovery import build

from discord import ClientException, Channel, ChannelType, Member
from discord.voice_client import ProcessPlayer
from discord.opus import load_opus

from NintbotForDiscord.Enums import EventTypes
from NintbotForDiscord.Plugin import BasePlugin
from NintbotForDiscord.Permissions import Permission, create_match_any_permission_group
from NintbotForDiscord.Permissions.Voice import MuteMembers
from NintbotForDiscord.Permissions.Special import Owner

__author__ = 'Riley Flynn (nint8835)'


class VoidLogger:

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

    def info(self, msg):
        pass


# noinspection PyBroadException
def get_stream_info(url):
    import youtube_dl

    opts = {
        'format': 'webm[abr>0]' if 'youtube' in url else 'best',
        'prefer_ffmpeg': True,
        'logger': VoidLogger()
    }

    ydl = youtube_dl.YoutubeDL(opts)
    try:
        info = ydl.extract_info(url, download=False)
        return info
    except:
        return None


class WhitelistedUser(Permission):

    def __init__(self, plugin_instance):
        self.plugin = plugin_instance

    def has_permission(self, member: Member) -> bool:
        return member.id in self.plugin.config["whitelisted_users"]


class InWhitelistedServer(Permission):

    def __init__(self, plugin_instance):
        self.plugin = plugin_instance

    def has_permission(self, member: Member) -> bool:
        return member.server.id in self.plugin.config["whitelisted_servers"]


class Plugin(BasePlugin):

    def __init__(self, bot_instance, plugin_data, folder):
        super(Plugin, self).__init__(bot_instance, plugin_data, folder)
        with open(os.path.join(folder, "config.json")) as f:
            self.config = json.load(f)
        self.admin = create_match_any_permission_group([Owner(self.bot), MuteMembers()])
        self.bot.register_handler(EventTypes.CommandSent, self.on_command, self)

        self.bot.CommandRegistry.register_command("play",
                                                  "Adds a song to the song queue.",
                                                  InWhitelistedServer(self),
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("joinvoice",
                                                  "Makes the bot connect to a voice channel.",
                                                  WhitelistedUser(self),
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("leavevoice",
                                                  "Makes the bot disconnect from a voice channel",
                                                  WhitelistedUser(self),
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("skip",
                                                  "Votes to skip the current song.",
                                                  InWhitelistedServer(self),
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("haroo",
                                                  "Requests the greatest song in the world. HAROO HAROO HAROO!",
                                                  InWhitelistedServer(self),
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("youtube",
                                                  "Searches your request on Youtube and adds the first result to the queue.",
                                                  InWhitelistedServer(self),
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("queue",
                                                  "Gets the current length of the queue.",
                                                  InWhitelistedServer(self),
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("volume",
                                                  "Changes the playback volume for the remaining songs in the queue.",
                                                  self.admin,
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("rate",
                                                  "Changes the sample rate of the remaining songs in the queue.",
                                                  self.admin,
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("voteskip",
                                                  "Toggles the ability to voteskip songs.",
                                                  self.admin,
                                                  plugin_data)
        self.bot.CommandRegistry.register_command("ffmpegopts",
                                                  "Changes the FFMPEG filter options.",
                                                  self.admin,
                                                  plugin_data)

        load_opus(os.path.join(folder, "libopus"))
        self.queue = asyncio.Queue()
        # self.text_channel = Channel()
        logging.getLogger("googleapiclient.discovery").setLevel(logging.ERROR)
        self._youtube = build("youtube", "v3", developerKey = self.config["youtube_api_key"])
        self.joined_voice = False
        self.skips = []
        self.song = {}
        self.next_song_event = asyncio.Event()
        self.bot.EventManager.loop.create_task(self.song_queue())

    def toggle_next_song(self):
        self.bot.loop.call_soon_threadsafe(self.next_song_event.set)

    def custom_ffmpeg_player(self, filename, volume, playback_rate, *, use_avconv = False, pipe = False, options = None, after = None):
        command = 'ffmpeg' if not use_avconv else 'avconv'
        input_name = '-' if pipe else shlex.quote(filename)
        cmd = command + ' -i {} -f s16le -ar {} -ac {} {} -loglevel warning pipe:1'
        cmd = cmd.format(input_name, self.bot.voice.encoder.sampling_rate, self.bot.voice.encoder.channels, "-af \"volume={}{}{}\"".format(volume, playback_rate, self.config["ffmpeg_options"]))
        if isinstance(options, str):
            cmd = cmd + ' ' + options

        stdin = None if not pipe else filename
        args = shlex.split(cmd)
        try:
            p = subprocess.Popen(args, stdin = stdin, stdout = subprocess.PIPE)
            return ProcessPlayer(p, self.bot.voice, after)
        except subprocess.SubprocessError as e:
            raise ClientException('Popen failed: {0.__name__} {1}'.format(type(e), str(e)))

    def custom_ytdl_player(self, url, *, options = None, use_avconv = False, after = None):

        opts = {
            'format': 'webm[abr>0]' if 'youtube' in url else 'best',
            'prefer_ffmpeg': not use_avconv,
            'logger': VoidLogger()
        }
        if options is not None and isinstance(options, dict):
            opts.update(options)

        ydl = youtube_dl.YoutubeDL(opts)
        info = ydl.extract_info(url, download = False)

        if self.config["playback_rate"] == 0:
            rate = ""
        else:
            rate = ",asetrate=r={}".format(self.config["playback_rate"])

        return self.custom_ffmpeg_player(info['url'], volume = self.config["playback_volume"], playback_rate = rate, use_avconv = use_avconv, after = after)

    # noinspection PyBroadException
    async def song_queue(self):
        while not self.bot.is_closed:
            self.next_song_event.clear()
            self.skips = []
            self.song = await self.queue.get()
            waiting_to_join = True
            while waiting_to_join:
                try:
                    waiting_to_join = not self.bot.voice.is_connected()
                except:
                    waiting_to_join = True
                if waiting_to_join:
                    await asyncio.sleep(5)
            self.player = self.custom_ytdl_player(self.song["url"],
                                                  after=self.toggle_next_song)
            self.player.start()
            await self.bot.send_message(self.text_channel, ":speaker: Now playing {}, requested by {}.".format(self.song["info"]["title"], self.song["requester"].name))
            if self.song["info"]["title"] == "Dropkick Murphys - Johnny I hardly knew ya":
                await self.bot.send_message(self.text_channel, "HAROO HAROO HAROO HAROO HAROO HAROO HAROO HAROO HAROO HAROO HAROO HAROO HAROO HAROO")
            await self.next_song_event.wait()

    # noinspection PyBroadException
    async def on_command(self, args):
        if (not args["message"].channel.is_private) and args["command_args"][0] in ["skip", "joinvoice", "play", "leavevoice", "volume", "rate", "voteskip", "queue", "haroo", "youtube", "ffmpegopts"]:
            try:
                if InWhitelistedServer(self).has_permission(args["author"]):
                    self.text_channel = args["message"].channel
                    if args["command_args"][0] == "play" and len(args["command_args"]) >= 2:
                        for item in args["command_args"][1:]:
                            try:
                                domain = ".".join(item.split("://")[1].split("/")[0].split(".")[-2:])
                                if domain in self.config["whitelisted_domains"]:
                                    stream_info_getter = self.bot.EventManager.loop.run_in_executor(None, get_stream_info, item)
                                    stream_info = await stream_info_getter
                                    if stream_info is not None:
                                        info = {"url": item, "info": stream_info, "requester": args["author"]}
                                        await self.queue.put(info)
                                        await self.bot.send_message(args["message"].channel,
                                                                         ":ballot_box_with_check: Song {} added to queue.".format(info["info"]["title"]))
                                    else:
                                        await self.bot.send_message(args["message"].channel,
                                                                    ":no_entry_sign: Song from {} failed to be added to queue. Please use a different upload of the song.".format(item))
                            except:
                                pass

                    if args["command_args"][0] == "joinvoice" and WhitelistedUser(self).has_permission(args["author"]):
                        try:
                            await self.bot.voice.disconnect()
                        except:
                            pass
                        if len(args["command_args"]) == 1:
                            for channel in [i for i in args["message"].server.channels if i.type == ChannelType.voice]:
                                if args["author"] in channel.voice_members:
                                    await self.bot.join_voice_channel(channel)
                                    await self.bot.send_message(args["message"].channel,
                                                                     ":ballot_box_with_check: Joined voice channel \"{}\"".format(channel.name))
                        if len(args["command_args"]) > 1:
                            joined = False
                            for channel in [i for i in args["message"].server.channels if i.type == ChannelType.voice]:
                                if channel.name == args["command_args"][1]:
                                    await self.bot.join_voice_channel(channel)
                                    await self.bot.send_message(args["message"].channel,
                                                                     ":ballot_box_with_check: Joined voice channel \"{}\"".format(channel.name))
                                    joined = True
                                    break

                            if not joined:
                                await self.bot.send_message(args["channel"], ":no_entry_sign: Channel not found.")

                    if args["command_args"][0] == "leavevoice" and WhitelistedUser(self).has_permission(args["author"]):
                        try:
                            await self.bot.voice.disconnect()
                            await self.bot.send_message(self.text_channel, ":ballot_box_with_check: Disconnected from voice.")
                        except:
                            await self.bot.send_message(args["channel"], ":no_entry_sign: The bot is not in a voice channel.")

                    if args["command_args"][0] == "skip":
                        if self.admin.has_permission(args["author"]):
                            await self.bot.send_message(self.text_channel, ":ballot_box_with_check: Admin skipped song.")
                            self.player.stop()
                            self.toggle_next_song()

                        elif args["author"] in self.bot.voice.channel.voice_members and args["author"] not in self.skips and self.config["voteskip_enabled"]:
                            self.skips.append(args["author"])
                            await self.bot.send_message(self.text_channel, ":question: {} of the required {} users have voted to skip.".format(len(self.skips), int(math.ceil((len(self.bot.voice.channel.voice_members)-1)/2))))
                            if len(self.skips) >= int(math.ceil((len(self.bot.voice.channel.voice_members)-1)/2)):
                                await self.bot.send_message(self.text_channel, ":ballot_box_with_check: Vote passed.")
                                self.player.stop()
                                self.toggle_next_song()

                    if args["command_args"][0] == "haroo":
                        item = "https://www.youtube.com/watch?v=Yg_rf2d894k"
                        stream_info_getter = self.bot.EventManager.loop.run_in_executor(None, get_stream_info, item)
                        stream_info = await stream_info_getter
                        if stream_info is not None:
                            info = {"url": item, "info": stream_info, "requester": args["author"]}
                            await self.queue.put(info)
                            await self.bot.send_message(args["message"].channel,
                                                        ":ballot_box_with_check: Song {} added to queue.".format(info["info"]["title"]))
                        else:
                            await self.bot.send_message(args["message"].channel,
                                                        ":no_entry_sign: Song from {} failed to be added to queue. Please use a different upload of the song.".format(item))

                    if args["command_args"][0] == "youtube" and len(args["command_args"])>=2:
                        try:
                            query = " ".join(args["command_args"][1:])
                            results = self._youtube.search().list(
                                q=query,
                                part="id",
                                maxResults = 10
                            ).execute().get("items", [])
                            for result in results:
                                if result["id"]["kind"] == "youtube#video":
                                    item = "https://www.youtube.com/watch?v={}".format(result["id"]["videoId"])
                                    break
                                else:
                                    item = ""

                            if item != "":
                                stream_info_getter = self.bot.EventManager.loop.run_in_executor(None, get_stream_info, item)
                                stream_info = await stream_info_getter
                                if stream_info is not None:
                                    info = {"url": item, "info": stream_info, "requester": args["author"]}
                                    await self.queue.put(info)
                                    await self.bot.send_message(args["message"].channel,
                                                                ":ballot_box_with_check: Song {} added to queue.".format(info["info"]["title"]))
                                else:
                                    await self.bot.send_message(args["message"].channel,
                                                                ":no_entry_sign: Song from {} failed to be added to queue. Please use a different upload of the song.".format(item))
                        except:
                            traceback.print_exc(5)

                    if args["command_args"][0] == "queue":
                        await self.bot.send_message(self.text_channel, ":information_source: There are {} songs currently in the queue.".format(self.queue.qsize()))

                    if args["command_args"][0] == "volume" and len(args["command_args"])==2 and self.admin.has_permission(args["author"]):
                        self.config["playback_volume"] = args["command_args"][1]
                        await self.bot.send_message(self.text_channel, ":ballot_box_with_check: Playback volume set to {}%.".format(float(self.config["playback_volume"]) * 100))

                    if args["command_args"][0] == "rate" and len(args["command_args"])==2 and self.admin.has_permission(args["author"]):
                        self.config["playback_rate"] = int(args["command_args"][1])
                        if args["command_args"][1] == "0":
                            await self.bot.send_message(self.text_channel, ":ballot_box_with_check: Playback rate set to content default.".format(self.config["playback_rate"]))
                        else:
                            await self.bot.send_message(self.text_channel, ":ballot_box_with_check: Playback rate set to {}Hz.".format(self.config["playback_rate"]))

                    if args["command_args"][0] == "voteskip" and self.admin.has_permission(args["author"]):
                        self.config["voteskip_enabled"] = not self.config["voteskip_enabled"]
                        await self.bot.send_message(args["channel"], ":ballot_box_with_check: Voteskip enabled status set to {}.".format(self.config["voteskip_enabled"]))

                    if args["command_args"][0] == "ffmpegopts" and len(args["command_args"])>=2 and self.admin.has_permission(args["author"]):
                        if args["command_args"][1] == "NONE":
                            self.config["ffmpeg_options"] = ""
                        else:
                            self.config["ffmpeg_options"] = " ".join(args["command_args"][1:])
                        await self.bot.send_message(self.text_channel, ":ballot_box_with_check: FFMPEG options updated")


                else:
                    await self.bot.send_message(args["channel"], ":no_entry_sign: This server is not whitelisted in the config.")

            except:
                #await self.bot.send_message(args["channel"], "```{}```".format(traceback.format_exc(2)))
                pass