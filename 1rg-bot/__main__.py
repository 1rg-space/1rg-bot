from typing import List, Union
import discord
import os
import traceback
from dotenv import load_dotenv

from .bluesky import BlueskyPoster

load_dotenv()

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

# Map confirmation Message to server Message
waiting_dms: dict[discord.Message, discord.Message] = {}

# Keep track of msgs (their IDs) that are too long to prevent double notifying
too_long_msgs: List[int] = []


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

    if reaction.message in waiting_dms:
        # A user has reacted to the DM request to post

        if user != waiting_dms[reaction.message].author:
            # The user who clicked the check is not the author of the post
            return

        if str(reaction.emoji) == YES_EMOJI:
            # They consented to post the msg
            try:
                url = await bsky.post(waiting_dms[reaction.message])
                edit_text = f"\nEdit: [posted]({url})"
            except Exception as e:
                print(traceback.format_exc())
                try:
                    edit_text = f"\nEdit: `{e.response.content.message}` 🙁"  # type: ignore
                except AttributeError:
                    edit_text = f"\nEdit: `{e}` 🙁"

            await reaction.message.edit(
                content=reaction.message.content + edit_text,
                suppress=True,
            )
            # Mark message as posted so it won't be double posted
            await waiting_dms[reaction.message].add_reaction(TARGET_EMOJI)
            # No longer track it
            del waiting_dms[reaction.message]
            return

        # User reacted with some other emoji, just ignore this
        # And still keep the DM as waiting
        return

    # Validate random user msg
    if str(reaction.emoji) != TARGET_EMOJI:
        return
    if reaction.count < TARGET_COUNT:
        return

    if reaction.message in waiting_dms.values():
        # A user added the target emoji to a msg that the bot has already sent
        # a confirmation msg for. So just ignore it
        # This prevents repeated confirmation msgs
        return

    if client.user in [user async for user in reaction.users()]:
        # The bot has already posted this
        # It reacting to the post is a marker of this
        # So stop processing to prevent double-posting
        return

    if len(reaction.message.content) > MAX_LENGTH:
        if reaction.message.id not in too_long_msgs:
            await reaction.message.reply(
                "❌ This message is too long to post on Bluesky.",
                suppress_embeds=True,
            )
            too_long_msgs.append(reaction.message.id)
        return

    # DM user to confirm they want it posted
    dm_content = (
        f"{reaction.message.author.mention}"
        + " are you okay with your msg being posted publicly to a"
        + " [1RG account](https://bsky.app/profile/overheard.1rg.space)?"
        + " Click the check if so."
    )
    # SIKE: it's a reply, not a DM
    dm_msg = await reaction.message.reply(dm_content, suppress_embeds=True)
    # Track it for when the user reacts
    waiting_dms[dm_msg] = reaction.message

    # Add reactions for the user to click
    await dm_msg.add_reaction(YES_EMOJI)

    # Once the user reacts, this function will be triggered again


client.run(os.environ["DISCORD_TOKEN"])
