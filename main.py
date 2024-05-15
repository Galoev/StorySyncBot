from instaloader import Instaloader
from instaloader import Profile
from instaloader import LatestStamps
from telebot import TeleBot
from dotenv import load_dotenv
import asyncio
import os


load_dotenv()

INST_LOGIN=os.getenv("INST_LOGIN")
INST_PASSWORD=os.getenv("INST_PASSWORD")
TARGET_USERNAME=os.getenv("TARGET_USERNAME")
CHANNEL_ID=os.getenv("CHANNEL_ID")
TG_ACCESS_TOKEN=os.getenv("TG_ACCESS_TOKEN")

# Initialize Instaloader
L = Instaloader(download_video_thumbnails=False)
L.login(INST_LOGIN, INST_PASSWORD)
stampsDB = LatestStamps("configs/stamps.txt")

# Initialize Telegram Bot
bot = TeleBot(TG_ACCESS_TOKEN)


def download_stories(profile: Profile):
    L.download_stories(userids=[profile], filename_target=profile.userid, latest_stamps=stampsDB, fast_update=True)
    print("Download: DONE")

async def post_stories(folder_path: str, channel_id: str):
    files = os.listdir(folder_path)
    sorted_files = sorted(files)

    for file in sorted_files:
        if not file.endswith(('.jpg', '.mp4')):
            continue

        with open(folder_path + "/" + file, 'rb') as media:
            if file.endswith('.jpg'):
                bot.send_photo(chat_id=channel_id, photo=media)
            else:
                bot.send_video(chat_id=channel_id, video=media, width=1080, height=1920)
        
        await asyncio.sleep(1)

def delete_all_files_in_folder(folder_path):
    command = f"rm -rf {folder_path}/*"
    os.system(command)

def save_session():
    print("Saving session...")
    L.save_session_to_file(filename=f"config/session-{INST_LOGIN}")
    print("Saving done")

async def cli_interface(stop_event: asyncio.Event):
    while True:
        command = input("> ")
        if command == 'close':
            stop_event.set()
            break
        else:
            print("Unknown command. Try again.")
    print("Closing the program...")

async def run(profile: Profile, stop_event: asyncio.Event):
    while not stop_event.is_set():
        download_stories(profile)
        await post_stories(str(profile.userid), CHANNEL_ID)
        delete_all_files_in_folder(str(profile.userid))
        await asyncio.sleep(30)
    save_session()

async def main():
    profile = Profile.from_username(L.context, TARGET_USERNAME)
    stop_event = asyncio.Event()
    tasks = [run(profile, stop_event), cli_interface(stop_event)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
