from instaloader import Instaloader
from instaloader import Profile
from instaloader import LatestStamps
from instaloader.exceptions import TwoFactorAuthRequiredException
from instaloader.exceptions import QueryReturnedBadRequestException
# from telebot import TeleBot
from telebot.async_telebot import AsyncTeleBot
from dotenv import load_dotenv
from pathlib import Path
import asyncio
import aioconsole
import random
import os


load_dotenv()

INST_LOGIN=os.getenv("INST_LOGIN")
INST_PASSWORD=os.getenv("INST_PASSWORD")
TARGET_USERNAME=os.getenv("TARGET_USERNAME")
CHANNEL_ID=os.getenv("CHANNEL_ID")
TG_ACCESS_TOKEN=os.getenv("TG_ACCESS_TOKEN")
ALLOWED_USERS=os.getenv("ALLOWED_USERS").split()
ADMIN_USER=os.getenv("ADMIN_USER")

# Initialize Instaloader
L = Instaloader(download_video_thumbnails=False)
# L.login(INST_LOGIN, INST_PASSWORD)
stampsDB = LatestStamps("configs/stamps.txt")

# Initialize Telegram Bot
bot = AsyncTeleBot(TG_ACCESS_TOKEN)
event_inst_rebooted = asyncio.Event()

@bot.message_handler(commands=['reboot'])
async def inst_rebooted(message):
    user_id = message.from_user.id
    if user_id in ALLOWED_USERS:
        msg = "Inst rebooted"
        print(msg)
        event_inst_rebooted.set()
        await bot.reply_to(message, msg)

def load_session():
    session_file = Path(f"configs/session-{INST_LOGIN}")
    print("Loading session...")
    if not session_file.exists():
        print("Session file doesn't exist. Try to login..")
        try:
            L.login(INST_LOGIN, INST_PASSWORD)
        except TwoFactorAuthRequiredException:
            code = input("Enter 2FA code:")
            L.two_factor_login(code)
        print("Login done")
        return

    L.load_session_from_file(username=INST_LOGIN, filename=session_file)
    print("Loading done")

def save_session():
    print("Saving session...")
    L.save_session_to_file(filename=f"configs/session-{INST_LOGIN}")
    print("Saving done")

async def sleep_with_interrupt(timeout, event):
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        pass

async def download_stories(profile: Profile):
    try:
        L.download_stories(userids=[profile], filename_target=profile.userid, latest_stamps=stampsDB, fast_update=True)
    except QueryReturnedBadRequestException as e:
        msg = f"You need to reboot your Instagram account.\n Error: {e}"
        bot.send_message(ADMIN_USER, msg)
        print(msg)

        msg = "Waiting for reboot..."
        bot.send_message(ADMIN_USER, msg)
        print(msg)

        await event_inst_rebooted.wait()

        msg = "Continued execution of the bot"
        event_inst_rebooted.clear()
        bot.send_animation(ADMIN_USER, msg)
        print(msg)

    print("Download done")

async def post_stories(folder_path: str, channel_id: str):
    files = os.listdir(folder_path)
    sorted_files = sorted(files)

    for file in sorted_files:
        if not file.endswith(('.jpg', '.mp4')):
            continue

        with open(folder_path + "/" + file, 'rb') as media:
            if file.endswith('.jpg'):
                await bot.send_photo(chat_id=channel_id, photo=media)
            else:
                await bot.send_video(chat_id=channel_id, video=media, width=1080, height=1920)
        
        await asyncio.sleep(1)

def delete_all_files_in_folder(folder_path):
    command = f"rm -rf {folder_path}/*"
    os.system(command)

async def cli_interface(stop_event: asyncio.Event):
    while True:
        command = await aioconsole.ainput()
        if command == 'close':
            print("Closing the program...")
            bot._polling = False
            stop_event.set()
            save_session()
            print("Closing done")
            break
        else:
            print("Unknown command. Try again.")

async def run(profile: Profile, stop_event: asyncio.Event):
    count = 0
    while not stop_event.is_set():
        print(f"iter: {count}")
        count += 1
        await download_stories(profile)
        await post_stories(str(profile.userid), CHANNEL_ID)
        delete_all_files_in_folder(str(profile.userid))
        # await asyncio.sleep(60 + random.randint(-10, 10))
        await sleep_with_interrupt(60 + random.randint(-10, 10), stop_event)
    print("Stop run loop")

async def main():
    load_session()
    profile = Profile.from_username(L.context, TARGET_USERNAME)
    stop_event = asyncio.Event()
    tasks = [run(profile, stop_event), cli_interface(stop_event), bot.polling()]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
