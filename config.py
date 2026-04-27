from os import getenv
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.API_ID = 21705136
        self.API_HASH = "78730e89d196e160b0f1992018c6cb19"

        self.BOT_TOKEN = "8677717845:AAGt3sfCM30DhTa6Pjs1GllVaNUyzRaKFR8"
        self.MONGO_URL = ""

        self.LOGGER_ID = -1003763475049
        self.OWNER_ID = 6944519938

        self.DURATION_LIMIT = int(getenv("DURATION_LIMIT", 600000000)) * 600000000
        self.QUEUE_LIMIT = int(getenv("QUEUE_LIMIT", 200000000000))
        self.PLAYLIST_LIMIT = int(getenv("PLAYLIST_LIMIT", 200000000000))

        self.SESSION1 = "BAFLMbAAGH7JAbEAjnpcf3sZ8fAbEfMrwqMNkGIfx0oQ1Y4ysQTQ6LRjHl4-zloy6xxju5vgXUBInMcBMNVbHw6w47yKP16KWp2pQpZvrx5rI35AfV1vQxbWLEYxrF9CKzKRgDObOmoX_TDPuhKW25rSYnzkfiGQ4Ti0iNkkrGSyQSfFX41lObcHtXi60E7QGQIQkMfHBELOJvdpGzfQHZV3XqvXIpi1q-Xw4oXp7xVWgxhzjaDkowNmybaeZSfba4X8H6GSnR7-Ab8Sy6z4ZQdVfM1EXrCEZRIDJGAR7vv-15jP6EyPz0wO2hnq1C26lR4BLNdiz-YX_VglYG1MZCB1lKsSNgAAAAF0Y2d0AA"
        self.SESSION2 = getenv("SESSION2", None)
        self.SESSION3 = getenv("SESSION3", None)

        self.SUPPORT_CHANNEL = "https://t.me/Toxic_bots"
        self.SUPPORT_CHAT = "https://t.me/toxiic_chats"

        self.AUTO_END: bool = getenv("AUTO_END", True)
        self.AUTO_LEAVE: bool = getenv("AUTO_LEAVE", False)
        self.VIDEO_PLAY: bool = getenv("VIDEO_PLAY", True)
        self.COOKIES_URL = [
            url for url in getenv("COOKIES_URL", "https://batbin.me/captors").split(" ")
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
