from typing import Union
import discord
import os

TARGET_EMOJI = "📤"
TARGET_COUNT = 1  # TODO
YES_EMOJI = "✅"
NO_EMOJI = "❌"

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

client = discord.Client(intents=intents)


waiting_dms = []


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_reaction_add(
    reaction: discord.Reaction, user: Union[discord.Member, discord.User]
):
    print(reaction, user)

    # Ignore reactions from the bot itself
    if user == client.user:
        return

    if reaction.message.id in waiting_dms:
        # A user has reacted to the DM request to post
        if str(reaction.emoji) == NO_EMOJI:
            await user.send("Ok.")
            waiting_dms.remove(reaction.message.id)
            return
        if str(reaction.emoji) == YES_EMOJI:
            # TODO: make the post
            await user.send("Thanks!")
            waiting_dms.remove(reaction.message.id)
            return

        # User reacted with some other emoji, just ignore this
        # And still keep the DM as waiting
        return

    # Validate random user msg
    if str(reaction.emoji) != TARGET_EMOJI:
        return
    if reaction.count < TARGET_COUNT:
        return

    # DM user to confirm they want it posted
    dm_content = "Are you okay with your msg being posted publicly to a 1RG account? Click an emoji reaction.\n"
    dm_content += f"Message: {reaction.message.jump_url}"
    dm_msg = await reaction.message.author.send(dm_content)
    waiting_dms.append(dm_msg.id)  # Track it for when the user reacts

    # Add reactions for the user to click
    await dm_msg.add_reaction(YES_EMOJI)
    await dm_msg.add_reaction(NO_EMOJI)

    # Once the user reacts, this function will be triggered again


client.run(os.environ["DISCORD_TOKEN"])
