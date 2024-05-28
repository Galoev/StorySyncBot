import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List, Union

import aioconsole
import aiofiles
from dotenv import load_dotenv
from instaloader.exceptions import (
    QueryReturnedBadRequestException,
    TwoFactorAuthRequiredException,
)
from instaloader.instaloader import Instaloader
from instaloader.lateststamps import LatestStamps
from instaloader.structures import Profile
from telebot.async_telebot import AsyncTeleBot
from telebot.types import (
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
)

from logger import get_logger

load_dotenv(override=True)

INST_LOGIN = os.getenv("INST_LOGIN")
INST_PASSWORD = os.getenv("INST_PASSWORD")
TARGET_USERNAME = os.getenv("TARGET_USERNAME")
CHANNEL_ID = os.getenv("CHANNEL_ID")
TG_ACCESS_TOKEN = os.getenv("TG_ACCESS_TOKEN")
ALLOWED_USERS = list(os.getenv("ALLOWED_USERS").split())
ADMIN_USER = os.getenv("ADMIN_USER")
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL"))


L = Instaloader(download_video_thumbnails=False)
stampsDB = LatestStamps("configs/stamps.txt")

bot = AsyncTeleBot(TG_ACCESS_TOKEN)
event_inst_rebooted = None
stop_event = None

logger = get_logger(name=__name__)


async def log_and_send(msg, log_level=logging.DEBUG):
    logger.log(level=log_level, msg=msg)
    await bot.send_message(ADMIN_USER, msg)


async def check_global_var(var_name, var):
    if not var:
        logger.log(logging.CRITICAL, f"global variable {var_name} is None")
        save_session()
        await log_and_send(
            "Bot stopped because of CRITICAL error", log_level=logging.CRITICAL
        )
        sys.exit(1)


@bot.message_handler(commands=["reboot"])
async def inst_rebooted(message):
    user_id = message.from_user.id
    if user_id in ALLOWED_USERS:
        msg = "Inst rebooted"
        await check_global_var("event_inst_rebooted", event_inst_rebooted)
        event_inst_rebooted.set()
        logger.info(msg)
        await bot.reply_to(message, msg)


@bot.message_handler(commands=["stop"])
async def stop_bot(message):
    user_id = message.from_user.id
    if user_id in ALLOWED_USERS:
        msg = "Received a command from a TG to stop"
        logger.info(msg)
        await bot.reply_to(message, msg)
        await stop(stop_event)


@bot.message_handler(commands=["status"])
async def status_msg(message):
    user_id = message.from_user.id
    if user_id in ALLOWED_USERS:
        msg = "Received status command from TG"
        logger.info(msg)
        await bot.reply_to(message, msg)


def load_session():
    session_file = Path(f"configs/session-{INST_LOGIN}")
    logger.info(f"Loading session from file: {session_file}")
    if not session_file.exists():
        logger.warning("Session file doesn't exist. Try to login..")
        try:
            L.login(INST_LOGIN, INST_PASSWORD)
        except TwoFactorAuthRequiredException:
            code = input("Enter 2FA code:")
            L.two_factor_login(code)
        logger.info("Login done.")
        save_session()
        return

    L.load_session_from_file(username=INST_LOGIN, filename=session_file)
    logger.info("Loading done.")


def save_session():
    session_file = Path(f"configs/session-{INST_LOGIN}")
    logger.info(f"Saving session from file {session_file}")
    L.save_session_to_file(filename=session_file)
    logger.info("Saving done to file ")


async def sleep_with_interrupt(timeout, event):
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        pass


async def download_stories(profile: Profile):
    try:
        L.download_stories(
            userids=[profile],
            filename_target=profile.userid,
            latest_stamps=stampsDB,
            fast_update=True,
        )
    except QueryReturnedBadRequestException as e:
        msg = f"You need to reboot your Instagram account.\n Error: {e}"
        await log_and_send(msg, logging.ERROR)

        msg = "Waiting for reboot..."
        await log_and_send(msg, logging.ERROR)

        await check_global_var("event_inst_rebooted", event_inst_rebooted)
        await event_inst_rebooted.wait()
        event_inst_rebooted.clear()

        msg = "Continued execution of the bot"
        await log_and_send(msg, logging.ERROR)

    logger.info("Download done")


async def post_stories(folder_path: str, channel_id: str):
    files = os.listdir(folder_path)
    sorted_files = sorted(files)

    for file in sorted_files:
        if not file.endswith((".jpg", ".mp4")):
            continue

        with open(folder_path + "/" + file, "rb") as media:
            if file.endswith(".jpg"):
                await bot.send_photo(chat_id=channel_id, photo=media)
            else:
                await bot.send_video(
                    chat_id=channel_id, video=media, width=1080, height=1920
                )

        logger.info(f"Posted file: {file}")
        await asyncio.sleep(1)


async def post_media_to_channel(folder_path: str, channel_id: str):
    medias = await __collect_media(folder_path)
    if not medias:
        logger.info("Nothing to post")
        return

    n = len(medias)
    max_items_in_media_group = 10
    for start in range(0, n, max_items_in_media_group):
        end = min(start + max_items_in_media_group, n)
        await bot.send_media_group(chat_id=channel_id, media=medias[start:end])

    logger.info("Posted media group")


async def __collect_media(
    folder_path: str,
) -> List[
    Union[
        InputMediaAudio,
        InputMediaDocument,
        InputMediaPhoto,
        InputMediaVideo,
    ]
]:
    files = os.listdir(folder_path)
    sorted_files = sorted(files)
    medias = []
    log_msg = []

    for file in sorted_files:
        if not file.endswith((".jpg", ".mp4")):
            continue

        async with aiofiles.open(folder_path + "/" + file, mode="rb") as media:
            file_content = await media.read()
            if file.endswith(".jpg"):
                medias.append(InputMediaPhoto(file_content))
            else:
                medias.append(InputMediaVideo(file_content, width=1080, height=1920))

        log_msg.append(file)

    logger.info(f"Collected files: {log_msg}")
    return medias


def delete_files_in_directory(directory):
    files = os.listdir(directory)

    for file in files:
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            os.remove(file_path)
            logger.info(f"Deleted file: {file_path}")


async def stop(stop_event: asyncio.Event):
    await log_and_send("Stopping the bot...", logging.INFO)
    bot._polling = False
    await check_global_var("stop_event", stop_event)
    stop_event.set()
    save_session()
    logger.info("Stopping done")


async def cli_interface(stop_event: asyncio.Event):
    while True:
        command = await aioconsole.ainput()
        if command == "stop":
            await stop(stop_event)
            break
        else:
            logger.info("Unknown command. Try again.")
    logger.debug("Exit cli_interface")


async def run(profile: Profile, stop_event: asyncio.Event):
    count = 0
    await check_global_var("stop_event", stop_event)
    while not stop_event.is_set():
        logger.info(f"iter: {count}")
        count += 1
        await download_stories(profile)
        # await post_stories(str(profile.userid), CHANNEL_ID)
        await post_media_to_channel(str(profile.userid), CHANNEL_ID)
        delete_files_in_directory(str(profile.userid))
        await sleep_with_interrupt(SCRAPE_INTERVAL, stop_event)
    logger.info("Stop run loop")


async def main():
    global event_inst_rebooted, stop_event
    event_inst_rebooted = asyncio.Event()
    stop_event = asyncio.Event()

    load_session()
    profile = Profile.from_username(L.context, TARGET_USERNAME)
    tasks = [
        run(profile, stop_event),
        cli_interface(stop_event),
        bot.polling(),
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
