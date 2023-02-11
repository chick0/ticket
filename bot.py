from os import environ
from sys import stdout
from typing import Optional
from logging import getLogger
from logging import StreamHandler
from logging import Formatter
from logging import INFO

import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
logger = getLogger()
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


async def get_ticket_category(guild: discord.Guild) -> Optional[discord.CategoryChannel]:
    for catrgory in guild.categories:
        if catrgory.name == "티켓":
            return catrgory

    return None


async def get_closed_ticket_category(guild: discord.Guild) -> Optional[discord.CategoryChannel]:
    for catrgory in guild.categories:
        if catrgory.name == "닫힌 티켓":
            return catrgory

    return None


async def get_ticket(category: discord.CategoryChannel, user: discord.User) -> Optional[discord.TextChannel]:
    ticket_name = str(user.id)

    for channel in category.text_channels:
        if channel.name == ticket_name:
            return channel

    return None


async def create_ticket(category: discord.CategoryChannel, user: discord.User) -> discord.TextChannel:
    ticket_name = str(user.id)
    ticket_channel = await category.create_text_channel(ticket_name)

    await ticket_channel.set_permissions(
        target=user,  # type: ignore / user == member
        read_messages=True,
        read_message_history=True,
        send_messages=True,
        add_reactions=True,
        embed_links=True,
        attach_files=True,
        use_application_commands=True
    )

    await ticket_channel.send(
        f"<@{user.id}>님 지원 티켓 채널이 열렸습니다! 해당 채널은 관리자만 확인할 수 있습니다.\n\n"
        "필요한 사항을 남겨주시면 빠르게 도와드리도록 하겠습니다.\n\n"
        "> 다시 티켓을 닫으려면 `/close` 명령어를 사용해주세요."
    )

    return ticket_channel


@tree.command(
    name="ticket",
    description="지원 티켓을 생성합니다.",
    guild=discord.Object(id=int(environ['GUILD']))
)
@app_commands.checks.cooldown(1, 30, key=lambda i: (i.user.id))
async def ticket_open(interaction: discord.Interaction):
    guild: discord.Guild = interaction.guild  # type: ignore
    user: discord.User = interaction.user  # type: ignore

    ticket_catrgory = await get_ticket_category(guild)

    if ticket_catrgory is None:
        await interaction.response.send_message("오류! 해당 서버에 '티켓' 카테고리가 없습니다.")
        return

    ticket_channel = await get_ticket(ticket_catrgory, user)

    if ticket_channel is not None:
        await interaction.response.send_message(
            f"이미 생성한 지원 티켓이 있습니다. <#{ticket_channel.id}>로 이동해주세요.",
            ephemeral=True
        )
        return

    ticket_channel = await create_ticket(ticket_catrgory, user)

    await interaction.response.send_message(
        f"지원 티켓을 생성했습니다. <#{ticket_channel.id}>로 이동해주세요.",
        ephemeral=True
    )


@tree.command(
    name="close",
    description="지원 티켓을 종료합니다.",
    guild=discord.Object(id=int(environ['GUILD']))
)
async def ticket_close(interaction: discord.Interaction):
    async def not_a_ticket():
        await interaction.response.send_message(
            "해당 채널은 지원 티켓이 아닙니다.",
            ephemeral=True
        )

    guild: discord.Guild = interaction.guild  # type: ignore
    user: discord.User = interaction.user  # type: ignore
    channel: discord.TextChannel = interaction.channel  # type: ignore
    category: discord.CategoryChannel = channel.category  # type: ignore

    if category is None or category.name != "티켓":
        return await not_a_ticket()

    closed_ticket_category = await get_closed_ticket_category(guild)

    if closed_ticket_category is None:
        await interaction.response.send_message("오류! 해당 길드에 '닫힌 티켓' 카테고리가 없습니다.")
        return

    await channel.set_permissions(
        target=user,  # type: ignore / user == member
        overwrite=None
    )

    await channel.edit(category=closed_ticket_category)

    await interaction.response.send_message(
        "지원 티켓이 종료되었습니다.",
        ephemeral=True
    )


@tree.error
async def handle_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.errors.CommandOnCooldown):
        retry_after = error.retry_after

        await interaction.response.send_message(
            f"해당 명령어는 {retry_after:.2f}초뒤에 사용할 수 있습니다.",
            ephemeral=True
        )
    else:
        logger.exception(error)


@client.event
async def on_ready():
    user = f"{client.user.name}#{client.user.discriminator}"  # type: ignore
    logger.info(f"Logged in as {user}")

    logger.info("I'm sink!        - Command tree sync start")
    await tree.sync(guild=discord.Object(id=int(environ['GUILD'])))
    logger.info("Now I'm rescued. - Command tree sync finsihed")


def init_logger():
    logger.setLevel(INFO)
    handler = StreamHandler(stdout)
    handler.setFormatter(fmt=Formatter("%(asctime)s [%(levelname)s]: %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(hdlr=handler)


if __name__ == "__main__":
    init_logger()
    client.run(environ['TOKEN'])
