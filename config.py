from os import getenv
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.API_ID = 21705136
        self.API_HASH = "78730e89d196e160b0f1992018c6cb19"

        self.BOT_TOKEN = getenv("BOT")
        self.MONGO_URL = "mongodb+srv://Krishna:pss968048@cluster0.4rfuzro.mongodb.net/?retryWrites=true&w=majority"

        self.LOGGER_ID = -1002843633996
        self.OWNER_ID = 8176628365

        self.DURATION_LIMIT = int(getenv("DURATION_LIMIT", 600000000)) * 600000000
        self.QUEUE_LIMIT = int(getenv("QUEUE_LIMIT", 200000000000))
        self.PLAYLIST_LIMIT = int(getenv("PLAYLIST_LIMIT", 200000000000))

        self.SESSION1 = getenv("S", None)
        self.SESSION2 = getenv("SESSION2", None)
        self.SESSION3 = getenv("SESSION3", None)

        self.SUPPORT_CHANNEL = "https://t.me/Toxic_bots"
        self.SUPPORT_CHAT = "https://t.me/Techofy"

        self.AUTO_END: bool = getenv("AUTO_END", True)
        self.AUTO_LEAVE: bool = getenv("AUTO_LEAVE", False)
        self.VIDEO_PLAY: bool = getenv("VIDEO_PLAY", True)
        self.COOKIES_URL = [
            url for url in getenv("COOKIES_URL", "https://batbin.me/hypercriticalness").split(" ")
            if url and "batbin.me" in url
        ]
        self.DEFAULT_THUMB = "https://ar-hosting.pages.dev/1770755014036.jpg"
        self.PING_IMG = "https://ar-hosting.pages.dev/1770755014036.jpg"
        self.START_IMG = "https://ar-hosting.pages.dev/1770755014036.jpg"

    def check(self):
        missing = [
            var
            for var in ["API_ID", "API_HASH", "BOT_TOKEN", "MONGO_URL", "LOGGER_ID", "OWNER_ID", "SESSION1"]
            if not getattr(self, var)
        ]
        if missing:
            raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
