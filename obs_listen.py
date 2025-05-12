from __future__ import annotations
import os, asyncio, logging, sys, socket
import obsws_python as obs
from obsws_python.error import OBSSDKError
from views import DynamicUploadView
from datetime import datetime
from config import config

# Add type checking for the bot variable
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from bot import OBSClipper

# Set up sound effects and window title (different libraries depending on OS)
if sys.platform != "win32":
    from AppKit import NSWorkspace
    def get_frontmost_window_title() -> str:
        """
        Retrieves the title of the frontmost window in unix-like systems.

        Returns
        -------
        :class:`str`
            The title of the frontmost window.
        """
        frontmost_app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if frontmost_app:
            return frontmost_app.localizedName()
        return None
    
    # NOTE: I was going to use playsound, but I have never had any success with installing it.
    # NOTE: Simpleaudio is now rendered useless as whenever a sound effect is played, a segmentation fault occurs. Since the project is not being maintained, someone else made a fork of it and fixed the issue. See https://github.com/cexen/py-simple-audio
    import simpleaudio as sa
    def play_sound() -> None:
        """
        Plays a sound effect using simpleaudio.
        """
        wave_obj = sa.WaveObject.from_wave_file("sfx/soundeffectclip.wav")
        play_obj = wave_obj.play()
        play_obj.wait_done()
else:
    from win32gui import GetWindowText, GetForegroundWindow
    def get_frontmost_window_title() -> str:
        """
        Retrieves the title of the frontmost window in Windows.

        Returns
        -------
        :class:`str`
            The title of the frontmost window.
        """
        return GetWindowText(GetForegroundWindow())
    
    import winsound
    def play_sound() -> None:
        """
        Plays a sound effect using winsound.
        """
        winsound.PlaySound("sfx/soundeffectclip.wav", winsound.SND_FILENAME)


log = logging.getLogger("VC_Bot.\u001b[38;5;166;1masnync_obs\u001b[0m")

class Observer:
    """
    OBS WebSocket client that listens for events and sends messages to Discord.
    """
    def __init__(self, bot, host:str, port:int, password:str) -> None:
        """
        Initialize the OBS WebSocket client and register event callbacks.

        Parameters
        ----------
        bot: :class:`VCBot`
            The bot instance to send messages to Discord.

        host: :class:`str`
            The host of the OBS WebSocket server. Should be "localhost" or an IP address.

        port: :class:`int`
            The port of the OBS WebSocket server.

        password: :class:`str`
            The password for the OBS WebSocket server.
        """
        self.bot: OBSClipper = bot
        self.host = host
        self.port = port
        self.password = password
        self.running = False
        self._client:obs.EventClient = None # obs.EventClient(host=host, port=port, password=password)
        

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._client.disconnect()

    def on_replay_buffer_saved(self, data) -> None:
        """
        Called when the replay buffer is saved.
        
        Parameters
        ----------
        data: :class:`Object`
            The data from the replay buffer saved event. This object has one attribute called `saved_replay_path` (:class:`str`) which gives the path to the saved video.
        """
        #print(data)
        # Print the attributes names and values
        # for attr in data.attrs():
        #     print(f"{attr}: {getattr(data, attr)}")
        filepath = data.saved_replay_path
        # NOTE: Change this if you want to send the mp4 file instead of the mkv file
        if config.REMUX:
            if filepath.endswith(".mkv"):
                filepath = filepath[:-4] + ".mp4"
        
        if config.sound_effect:
            log.debug("Playing sound effect...")
            play_sound()
        active_window = get_frontmost_window_title()
        file_size = round(os.path.getsize(filepath) / (1024 * 1024), 2)
        log.info(f"Replay Buffer Saved: {filepath} (file size: {file_size} MB); Active Window: {active_window})")

        # Get the ending of the file path
        file_name = os.path.basename(filepath)
        # Send message to Discord
        asyncio.run_coroutine_threadsafe(self.notify_discord(file_name, file_size), self.bot.loop)

    async def notify_discord(self, filepath:str, file_size:float) -> None:
        """
        Send a message to Discord when a replay buffer is saved.
        
        Parameters
        ----------
        filepath: :class:`str`
            The path to the saved replay buffer file.
        file_size: :class:`float`
            The size of the saved replay buffer file in MB.
        """
        try:
            active_window = get_frontmost_window_title()
            channel = self.bot.get_channel(self.bot.CLIPS_CHANNEL.id)
            # Get time from the file name 
            # Example: Replay_2025-04-06_18-05-52.mp4
            time_str = filepath.split(".")[0].split("_")[1:4]
            # Convert to datetime object
            time_str = "-".join(time_str).replace("_", "-")
            time_str = datetime.strptime(time_str, "%Y-%m-%d-%H-%M-%S")

            timestamp_str = f"<t:{int(time_str.timestamp())}:f>"

            # Get members from the VC_USERS list
            if self.bot.RECORD_USERS:
                members = [f"<@{user.id}>" for user in self.bot.VC_USERS]
                members_str = ", ".join(members)
                members_str_name = ", ".join([user.name for user in self.bot.VC_USERS])
            else:
                members_str = "No users"
                members_str_name = "No users"
            log.info(f"Members in VC: {members_str_name}")
        except Exception as e:
            log.error(f"Error getting members in VC: {e}")
            return 
        if channel:
            try:
                view = DynamicUploadView(
                    filepath=filepath, 
                    message=f"Replay saved!\nPeople in VC: {members_str}\nActive window: {active_window}\nFile info: `{filepath}` ({file_size} MB)"
                )
                await channel.send(f"Replay saved! ({timestamp_str})\nPeople in VC: {members_str}\nActive window: {active_window}\nFile info: `{filepath}` ({file_size} MB)", view=view)
            except Exception as e:
                log.error(f"Error sending message to Discord: {e}")
                await channel.send(f"Replay saved! People in VC: {members_str}\nFile info: `{filepath}` ({file_size} MB)\nError: {e}")
            log.info(f"Sent message to Discord channel: {channel.name}")
        else:
            log.warning("Could not find Discord channel.")

    def on_input_mute_state_changed(self, data) -> None:
        """
        Called when the mute state of an input changes.
        """
        log.info(f"{data.input_name} mute toggled")

    def on_exit_started(self, _) -> None:
        """
        Called when OBS is closing.
        """
        log.warning("OBS closing, disconnecting...")
        self.disconnect()

    def is_obs_running(self) -> bool:
        """
        Check if OBS is running on the given host and port.

        Parameters
        ----------
        host: :class:`str`
            The host of the OBS WebSocket server. Should be "localhost" or an IP address.
        port: :class:`int`
            The port of the OBS WebSocket server.

        Returns
        -------
        :class:`bool`
            True if OBS is running, False otherwise.
        """
        s = socket.socket()
        s.settimeout(2)
        try:
            s.connect((self.host, self.port))
            return True
        except (ConnectionRefusedError, OSError):
            return False
        finally:
            s.close()

    def connect(self) -> None:
        """
        Connect to the OBS WebSocket server.
        """
        # Check if OBS is running
        if not self.is_obs_running():
            log.error(f"OBS is not running on {self.host}:{self.port}")
            # Raise an exception
            raise ConnectionRefusedError(f"OBS is not running on {self.host}:{self.port} (Is the host and port correct?)")
        
        # Connect to the OBS WebSocket server
        try:
            self._client = obs.EventClient(host=self.host, port=self.port, password=self.password)
        except OBSSDKError as e:
            log.error(f"OBSSDKError: {e}")
            log.debug("Check if the password is correct.")
            # Raise the exception
            raise e
        
        self._client.callback.register(
            [
                self.on_replay_buffer_saved,
                # Testing
                self.on_input_mute_state_changed,
                self.on_exit_started,
            ]
        )
        log.info(f"Registered events: {self._client.callback.get()}")
        self.running = True
        log.info(f"Connected to OBS WebSocket server on {self.host}:{self.port}")

    def disconnect(self) -> None:
        """
        Disconnect from the OBS WebSocket server.
        """
        if self._client:
            self._client.disconnect()
            self.running = False
            log.info("Disconnected from OBS WebSocket server.")
        else:
            log.warning("No OBS WebSocket client to disconnect.")

    async def run(self) -> None:
        """
        Run the observer in an async-friendly way.
        """
        # Connect to the OBS WebSocket server
        if self._client is None:
            self.connect()
        # Start the event loop
        # log.info("Started OBS WebSocket client.")
        while self.running:
            await asyncio.sleep(0.1)

