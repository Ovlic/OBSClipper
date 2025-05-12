
import discord
from bot import OBSClipper
from discord.errors import NotFound
from discord.app_commands.errors import CommandNotFound as AppCommandNotFound, CommandInvokeError, CheckFailure
from utils import setupLogger
from config import config


# Setup logger
logger = setupLogger()

client: OBSClipper = OBSClipper()

@client.tree.error
async def on_app_command_error(interaction: discord.Interaction, error:Exception) -> None: 
    print(f"main: {type(error)}")
    # If the command is not found or someone failed a check, ignore it
    if isinstance(error, AppCommandNotFound): return
    if isinstance(error, NotFound): return
    if isinstance(error, CheckFailure): return
    if interaction.user.id == client.MY_ID.id: # To print the debug info
        err_str = f"`{getattr(error, '__module__')}:  {error.args[0]}`"
        try:
            await interaction.response.send_message(err_str)
        except discord.errors.InteractionResponded:
            # Already responded, so we can't send a message
            pass

    if isinstance(error, CommandInvokeError):
        # logger.exception(error.__cause__)
        return

    logger.exception(error)


@client.tree.command(description="Test upload")
async def upload_file(interaction: discord.Interaction):
    # Upload a file called test.mp4
    await interaction.response.defer()
    print("Uploading file...")
    await interaction.followup.send("File", file=discord.File("examples/testing.mp4"))
    print("File uploaded!")
    

@client.tree.command(description="Test get people")
async def get_vc_users(interaction: discord.Interaction):
    if not client.RECORD_USERS:
        await interaction.response.send_message("Not recording users")
        return
    if not client.RECORD_USERS_CHANNEL:
        await interaction.response.send_message("Not recording users channel")
        return
    if not client.VC_USERS:
        await interaction.response.send_message("No users in VC")
        return
    await interaction.response.send_message(", ".join([str(user.name) for user in client.VC_USERS]))
    logger.info(f"Current VC users: {', '.join([str(user.name) for user in client.VC_USERS])}")

@client.tree.command()
async def search_for_user(interaction:discord.Interaction):
    ch = await client.check_for_user()
    if ch:
        await interaction.response.send_message(f"Found user {ch.name}")
    else:
        await interaction.response.send_message("No user found")


@client.tree.command()
async def kill_obs(interaction:discord.Interaction):
    await interaction.response.defer()
    client.obs_client.disconnect()
    await interaction.followup.send("Killed OBS")
    logger.info("Killed OBS")
    client.res.add_done_callback(lambda x: print("Done"))
    logger.info(client.res.running())


client.run(config.TOKEN)