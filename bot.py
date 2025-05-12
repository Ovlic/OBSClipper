
import os
import discord
import logging
import asyncio
from discord.ext.commands import Bot, CommandNotFound
from discord.app_commands.errors import CommandNotFound as AppCommandNotFound, CommandInvokeError
from obs_listen import Observer
from views import DynamicUploadButton
from config import Config, config

log = logging.getLogger("VC_Bot.\u001b[38;5;82;1mBot\u001b[0m")



class OBSClipper(Bot):
    def __init__(self):
        super().__init__(
            intents=discord.Intents.all(),
            command_prefix="!"
        )

        self.MY_ID: discord.Object = discord.Object(id=config.user_id)
        self.MY_GUILDS = [discord.Object(id=guild_id) for guild_id in config.guilds]
        self.CLIPS_CHANNEL = discord.Object(id=config.clips_channel)  # Channel ID for clips
        
        self.RECORD_USERS = False
        self.RECORD_USERS_CHANNEL = None
        self.VC_USERS = []
        self.CLIP_MESSAGES = []
        self.pending_removals = {}
        self.res = None

    def setup(self):
        # Setup OBS
        log.info("Setting up OBS...")
        self.observer = Observer(self, host=config.OBS_HOST, port=config.OBS_PORT, password=config.OBS_PASSWORD)
        self.observer.connect()
        log.info("OBS setup complete.")

        
    def run(self, *args, **kwargs):
        """
        Run the bot with the given arguments.
        This is a wrapper around the run method to handle exceptions.
        """
        # Setup obs
        self.setup()
        # Run the bot
        Bot.run(self, *args, **kwargs)


    async def on_ready(self):
        self.add_dynamic_items(DynamicUploadButton)
        # Start the OBS observer
        # Connect to OBS (to make sure the connection is valid before starting the bot)
        try:
            t = asyncio.create_task(self.observer.run())  # Runs the observer in the background
        except Exception as e:
            # Stop the event loop and raise an error
            log.error("Failed to connect to OBS WebSocket server. Please check your settings.")
            self.loop.stop()
            raise e
        log.info("Observer started.")
        log.info("VC bot is ready!")
        await self.change_presence(activity=discord.Game(name="Recording people"))
        # Check if the main user is already in a voice channel
        # await self.check_for_user() # Doesnt work and not really needed in the long run (ratelimits if the bot is in a lot of servers and the servers have many voice channels)
        log.info("------ Bot setup complete ------\n")


    # Check if a user is in vc when bot is started
    async def check_for_user(self):
        log.info("Checking for main user in VC...")
        async for guild in self.fetch_guilds():
            log.info(f"Checking guild: {guild.name}")
            # Get all channels in the guild
            channels = await guild.fetch_channels()
            for channel in channels:
                if channel.type != discord.ChannelType.voice:
                    continue # Skip non-voice channels
                log.info(f"Checking channel: {channel.name} ({guild.name})")
                log.info(f"Members in channel: {[member.name for member in channel.members]}")
                if self.MY_ID.id in [member.id for member in channel.members]:
                    log.info(f"Main user is in {channel.name} ({guild.name})")
                    self.RECORD_USERS = True
                    self.RECORD_USERS_CHANNEL = channel
                    self.VC_USERS = [user for user in channel.members]
                    log.info(f"VC_USERS updated: {[user.name for user in self.VC_USERS]}")
                    return True
        log.info("Main user not found in any VC.")
        return False

    async def on_command_error(self, ctx, ex):
        print(f"main.on_command_error: {type(ex)}")
        if isinstance(ex, CommandNotFound): return
        if ctx.author.id == self.MY_ID.id: 
            err_str = f"`{getattr(ex, '__module__')}:  {ex.args[0]}`"
            await ctx.reply(err_str)
        if isinstance(ex, CommandInvokeError):
            log.exception(ex.__cause__)
            log.info(f"CommandInvokeError: {ex.__cause__}")
            raise ex.__cause__
        else:
            log.exception(ex)
            raise ex.__cause__
        
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel is None and after.channel is not None:
            # User joined a voice channel
            if member.id == self.MY_ID.id: # Main user joined a voice channel
                if member.name in self.pending_removals:
                    # Cancel pending removal if they rejoin within 30 seconds
                    self.pending_removals[member.name].cancel()
                    del self.pending_removals[member.name]
                    log.info(f"Cancelled removal of {member.name} (Main user) from VC_USERS")
                
                log.info(f"Main user joined {after.channel.name}, START RECORDING PEOPLE!")
                self.RECORD_USERS = True
                self.RECORD_USERS_CHANNEL = after.channel
                self.VC_USERS = [user for user in after.channel.members]
                log.info(f"VC_USERS updated: {[user.name for user in self.VC_USERS]}")
            else: # User joined a voice channel
                if self.RECORD_USERS and self.RECORD_USERS_CHANNEL == after.channel:
                    log.info(f"{member.name} joined {after.channel.name}")
                    if member.name in self.pending_removals:
                        # Cancel pending removal if they rejoin within 30 seconds
                        self.pending_removals[member.name].cancel()
                        del self.pending_removals[member.name]
                        log.info(f"Cancelled removal of {member.name} from VC_USERS")
                    if member not in self.VC_USERS:
                        log.info(f"Added {member.name} to VC_USERS")
                        self.VC_USERS.append(member)

        elif before.channel is not None and after.channel is None:
            # User left a voice channel
            if member.id == self.MY_ID.id:
                log.info(f"Ovlic left {before.channel.name}, starting delay...")
                task = asyncio.create_task(self.delayed_main_user_leave(member))
                self.pending_removals[member.name] = task
                # self.RECORD_USERS = False
                # self.RECORD_USERS_CHANNEL = None
                # self.VC_USERS = []
            else:
                if self.RECORD_USERS and self.RECORD_USERS_CHANNEL == before.channel:
                    log.info(f"{member.name} left {before.channel.name}, scheduling removal in 30 seconds.")
                    if member in self.VC_USERS:
                        task = asyncio.create_task(self.delayed_removal(member))
                        self.pending_removals[member.name] = task

    async def delayed_removal(self, member):
        """
        Wait for 30 seconds before removing the user from VC_USERS.
        This is to prevent removing users who rejoin within 30 seconds.
        
        Parameters
        ----------
        member: :class:`discord.Member`
            The member to remove.
        """
        await asyncio.sleep(30)
        if member in self.VC_USERS:
            self.VC_USERS.remove(member)
            log.info(f"Removed {member.name} from VC_USERS after delay.")
        self.pending_removals.pop(member, None)

    async def delayed_main_user_leave(self, member):
        """
        Wait for 30 seconds before stopping recording.
        This is to prevent stopping recording if the main user rejoin within 30 seconds.
        
        Parameters
        ----------
        member: :class:`discord.Member`
            The main user to check.
        """
        await asyncio.sleep(30)
        if member in self.VC_USERS:
            log.info(f"Ovlic has left the channel, stopping recording.")
            # Stop recording
            self.RECORD_USERS = False
            self.RECORD_USERS_CHANNEL = None
            self.VC_USERS = []
            log.info(f"Stopped recording, VC_USERS cleared.")
            ac = await self.attach_clips()
            if ac == -1:
                print("Failed to attach clips.")
        else:
            log.warning("Main user not in VC_USERS, not stopping recording. (Was already in VC when bot started?)")


    # Function that recieves a message (non-couroutine function) and sends it to send_clip_message
    def send_message(self, text, filepath, channel):
        """Send a message with the clip file."""
        log.debug(f"Sending clip message: text='{text}', filepath='{filepath}'")
        if not os.path.exists(filepath):
            log.warning(f"File not found: {filepath}")
            return

        channel = self.get_channel(self.CLIPS_CHANNEL.id)
        if channel:
            log.debug("Running send_clip_message in event loop")
            # Run in the bot's event loop
            loop = self.loop
            # Run the coroutine in the event loop
            
            res = asyncio.run_coroutine_threadsafe(self.send_clip_message(text, filepath, channel), loop)
            log.debug("send_clip_message scheduled")
            log.debug("send_clip_message")
            log.info(res._state)
            self.res = res
        else:
            log.error("Clips channel not found!")
    
    async def send_clip_message(self, text, filepath, channel):
        """Send a message with the clip file."""
        log.debug(f"Sending clip message: text='{text}', filepath='{filepath}'")
        if not os.path.exists(filepath):
            log.warning(f"File not found: {filepath}")
            return
        await channel.send("Sending clip message...")
        file = discord.File(filepath, filename=os.path.basename(filepath))
        msg = await channel.send("Hi", file=file)
        # self.CLIP_MESSAGES.append((msg.id, filepath))
        log.info(f"Sent clip message: {msg.id} with file: {filepath}")


    async def attach_clips(self):
        """Attach captured replay files to their original messages."""
        log.info("Attaching clips to messages...")
        if not self.clip_messages:
            log.info("No clips to attach.")
            return

        channel = self.get_channel(self.CLIPS_CHANNEL.id)
        if not channel:
            log.error("Clips channel not found!")
            return -1

        log.info(f"Amount of clips to attach: {len(self.clip_messages)}")
        to_remove = []  # Store successful message IDs for removal

        for message_id, filepath in self.clip_messages[:]:  # Iterate over a copy
            log.debug(f"Attaching clip to message {message_id}: {filepath}")
            if os.path.exists(filepath):
                try:
                    msg = await channel.fetch_message(message_id)
                    file = discord.File(filepath, filename=os.path.basename(filepath))

                    # Preserve existing attachments
                    new_attachments = msg.attachments + [file]

                    await msg.edit(content=msg.content + "\n[Clip attached]", attachments=new_attachments)
                    log.info(f"Edited message {message_id} with clip: {filepath}")

                    to_remove.append((message_id, filepath))  # Mark for removal
                except Exception as e:
                    log.error(f"Failed to edit message {message_id}: {e}")
            else:
                log.warning(f"File not found: {filepath}")

        # Remove processed messages after iteration
        for item in to_remove:
            self.clip_messages.remove(item)

        log.info("Finished attaching clips.")


    async def setup_hook(self):
        for guild in self.MY_GUILDS:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
