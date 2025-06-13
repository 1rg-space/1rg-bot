from typing import Union
import discord
import os

from .bluesky import BlueskyPoster

TARGET_EMOJI = "📤"
TARGET_COUNT = 1  # TODO: increase eventually
YES_EMOJI = "✅"
MAX_LENGTH = 300  # Bluesky limit

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

client = discord.Client(intents=intents)

bsky = BlueskyPoster()

waiting_dms = {}  # Map DM ids to server Message


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_reaction_add(
    reaction: discord.Reaction, user: Union[discord.Member, discord.User]
):
    # Ignore reactions from the bot itself
    if user == client.user:
        return

    if reaction.message.id in waiting_dms:
        # A user has reacted to the DM request to post
        if str(reaction.emoji) == YES_EMOJI:
            bsky.post(waiting_dms[reaction.message.id])
            # await user.send("Thanks!")
            del waiting_dms[reaction.message.id]
            return

        # User reacted with some other emoji, just ignore this
        # And still keep the DM as waiting
        return

    # Validate random user msg
    if str(reaction.emoji) != TARGET_EMOJI:
        return
    if reaction.count < TARGET_COUNT:
        return
    if len(reaction.message.content) > MAX_LENGTH:
        return

    # DM user to confirm they want it posted
    dm_content = "Are you okay with your msg being posted publicly to a [1RG account](https://bsky.app/profile/overheard.1rg.space)?"
    dm_content += " Click the check if so."
    # SIKE: it's a reply, not a DM
    dm_msg = await reaction.message.reply(dm_content, suppress_embeds=True)
    # Track it for when the user reacts
    waiting_dms[dm_msg.id] = reaction.message

    # Add reactions for the user to click
    await dm_msg.add_reaction(YES_EMOJI)

    # Once the user reacts, this function will be triggered again


client.run(os.environ["DISCORD_TOKEN"])
