
import discord, logging, os, re
from config import config

log = logging.getLogger("VC_Bot.\u001b[38;5;226;1mviews\u001b[0m")



class DynamicUploadButton(
    discord.ui.DynamicItem[discord.ui.Button], 
    template=r"Replay_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.(mp4|mkv)"
    ):
    """
    A button that uploads a file when clicked.
    This button is created dynamically based on the file path and message provided.
    """

    def __init__(self, filepath: str, message: str, user_id: int):
        """
        Initialize the button with the given filepath and message.
        
        Parameters
        ----------
        filepath: :class:`str`
            The path to the file to be uploaded.
        message: :class:`str`
            The message to be sent with the file.
        user_id: :class:`int`
            The ID of the user who triggered the interaction (for permission check).
        """
        # Create the actual button
        super().__init__(
            discord.ui.Button(
                label="Upload Clip",
                style=discord.ButtonStyle.primary,
                custom_id=os.path.basename(filepath),  # Use the base filepath as the custom_id
            )
        )
        self.filepath = filepath
        self.message = message
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
   
    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        log.info(f"Uploading clip {self.filepath}")
        if os.path.exists(self.filepath):
            with open(self.filepath, "rb") as file:
                # Send the file to the user
                file = discord.File(file, filename=os.path.basename(self.filepath))
                try:
                    await interaction.followup.send(self.message, file=file)
                    log.info(f"Uploaded clip {self.filepath}")
                except discord.HTTPException as e:
                    # Handle the case where the file is too large to send
                    if e.status == 413 and "File is too large" in str(e):
                        await interaction.followup.send("File is too large to send!", ephemeral=True)
                        # Log name and size of the file
                        log.error(f"File too large: {self.filepath} ({round(os.path.getsize(self.filepath) / (1024 * 1024), 2)} MB)")
                    else:
                        await interaction.followup.send("An error occurred while sending the file.", ephemeral=True)
                        log.error(f"Error sending file: {e}")
                        raise e  # Re-raise the exception for logging
        else:
            await interaction.followup.send("File not found!", ephemeral=True)
            log.warning(f"File not found: {self.filepath}")

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str], /):
        message = interaction.message.content
        print(f"Orig response: {message}")
        filepath = os.path.join(config.clips_path, match.group(0))
        user_id = interaction.user.id
        return cls(filepath=filepath, message=message, user_id=user_id)
        

class DynamicUploadView(discord.ui.View):
    def __init__(self, filepath: str, message: str, user_id: int = config.user_id):
        """
        Initialize the view with a button that uploads a file when clicked.

        Parameters
        ----------
        filepath: :class:`str`
            The path to the file to be uploaded.
        message: :class:`str`
            The message to be sent with the file.
        user_id: :class:`int`
            The ID of the user who triggered the interaction (for permission check).
        """
        
        super().__init__(timeout=None)  # Set timeout to None for no expiration
        self.add_item(DynamicUploadButton(filepath, message, user_id))
   