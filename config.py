import os

from dotenv import load_dotenv

load_dotenv(override=True)

required_variables = [
    "INST_LOGIN",
    "INST_PASSWORD",
    "TARGET_USERNAME",
    "CHANNEL_ID",
    "TG_ACCESS_TOKEN",
    "ALLOWED_USERS",
    "ADMIN_USER",
    "SCRAPE_INTERVAL",
]


for var_name in required_variables:
    if not os.getenv(var_name):
        raise ValueError(f"Environment variable '{var_name}' is not set or empty")


INST_LOGIN = str(os.getenv("INST_LOGIN"))
INST_PASSWORD = str(os.getenv("INST_PASSWORD"))
TARGET_USERNAME = str(os.getenv("TARGET_USERNAME"))
CHANNEL_ID = str(os.getenv("CHANNEL_ID"))
TG_ACCESS_TOKEN = str(os.getenv("TG_ACCESS_TOKEN"))
ALLOWED_USERS = list(os.getenv("ALLOWED_USERS").split())  # type: ignore
ADMIN_USER = str(os.getenv("ADMIN_USER"))
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL"))  # type: ignore
