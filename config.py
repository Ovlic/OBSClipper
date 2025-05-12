
from typing import Optional


class Config:
    """
    Configuration settings for the bot.
    """
    def __init__(
        self,
        user_id: int,
        guilds: list[int],
        clips_path: str,
        clips_channel: int,
        sound_effect: bool,
        host: str,
        port: int,
        password: str,
        remux: Optional[bool],
        token: str
    ):
        """
        Initialize the configuration with the given data.

        Parameters
        ----------
        user_id: :class:`int`
            The user ID of the bot owner/manager.
        guilds: :class:`list[int]`
            The list of guild IDs the bot is in.
        clips_path: :class:`str`
            The path to the clips folder.
        clips_channel: :class:`int`
            The channel ID where clips are sent.
        sound_effect: :class:`bool`
            Whether to play a sound effect when a clip is captured
        host: :class:`str`
            The host of the OBS WebSocket server (should be "localhost" or an IP address).
        port: :class:`int`
            The port of the OBS WebSocket server.
        password: :class:`str`
            The password for the OBS WebSocket server.
        remux: Optional[:class:`bool`]
            Whether the videos will be remuxed or not. This is used to determine whether to send the mp4 file or the mkv file of a clip. Defaults to ``False``.
        token: :class:`str`
            The token for the bot.
        """
        self._user_id = user_id
        self._guilds = guilds
        self._clips_path = clips_path
        self._clips_channel = clips_channel
        self._sound_effect = sound_effect
        self._OBS_HOST = host
        self._OBS_PORT = port
        self._OBS_PASSWORD = password
        self._REMUX = remux
        self._TOKEN = token

    @property
    def user_id(self) -> int:
        """
        :class:`int`: The user ID of the bot owner.
        """
        return self._user_id
    
    @property
    def guilds(self) -> list[int]:
        """
        :class:`list[int]`: The list of guild IDs the bot is in.
        """
        return self._guilds
    
    @property
    def clips_path(self) -> str:
        """
        :class:`str`: The path to the clips folder.
        """
        return self._clips_path
    
    @property
    def clips_channel(self) -> int:
        """
        :class:`int`: The channel ID where clips are sent.
        """
        return self._clips_channel
    
    @property
    def sound_effect(self) -> bool:
        """
        :class:`bool`: Whether to play a sound effect when a clip is captured
        """
        return self._sound_effect
    
    @property
    def OBS_HOST(self) -> str:
        """
        :class:`str`: The host of the OBS WebSocket server (should be "localhost" or an IP address).
        """
        return self._OBS_HOST
    
    @property
    def OBS_PORT(self) -> int:
        """
        :class:`int`: The port of the OBS WebSocket server.
        """
        return self._OBS_PORT
    
    @property
    def OBS_PASSWORD(self) -> str:
        """
        :class:`str`: The password for the OBS WebSocket server.
        """
        return self._OBS_PASSWORD
    
    @property
    def REMUX(self) -> bool:
        """
        :class:`bool`: Whether the videos will be remuxed or not. This is used to determine whether to send the mp4 file or the mkv file of a clip.
        """
        return self._REMUX
    
    @property
    def TOKEN(self) -> str:
        """
        :class:`str`: The token for the bot.
        """
        return self._TOKEN



config = Config(
    # General settings
    user_id = 0,
    guilds = [0,],
    clips_path = "path/to/clips_folder",
    clips_channel = 0,
    sound_effect=True,
    # OBS settings
    host = "localhost",
    port = 4455,
    password = "password",
    remux = False,
    # Bot token
    token = ""
)