import os
import threading
import time
from bs4 import BeautifulSoup
from flask import Flask
import requests

app = Flask(__name__)


@app.route("/")
def home():
  threading.Thread(target=check_manoramamax_updates).start()
  return "ManoramaMAX Bot is Running Live & Checked for Updates!"


def run_web_server():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

TARGET_SHOWS = [
    "https://www.manoramamax.com/programs/detail/20000068/ghm9gfw",
    "https://www.manoramamax.com/programs/detail/122743/marimayam",
    "https://www.manoramamax.com/programs/detail/167656/super-kanmani",
    "https://www.manoramamax.com/programs/detail/179938/othiri-othiri-swapnangal",
    "https://www.manoramamax.com/programs/detail/182211/oru-chiri-iru-chiri-bumper-chiri-3",
    "https://www.manoramamax.com/programs/detail/176743/ottashikharam",
]

SENT_LINKS_FILE = "sent_manoramamax_episodes.txt"
LAST_OFFSET = None


def get_sent_links():
  try:
    with open(SENT_LINKS_FILE, "r") as f:
      return set(f.read().splitlines())
  except FileNotFoundError:
    return set()


def save_sent_link(link):
  with open(SENT_LINKS_FILE, "a") as f:
    f.write(link + "\n")


def get_episode_details(episode_url, headers):
  """എപ്പിസോഡിന്റെ തംബ്‌നെയിൽ ഫോട്ടോ ലിങ്കും ടൈറ്റിലും എടുക്കുന്നു"""
  try:
    res = requests.get(episode_url, headers=headers, timeout=10)
    if res.status_code == 200:
      soup = BeautifulSoup(res.text, "html.parser")

      # 1. Thumbnail Photo
      img_tag = soup.find("meta", property="og:image")
      image_url = img_tag["content"] if img_tag else None

      # 2. Title
      title_tag = soup.find("meta", property="og:title") or soup.find("title")
      title = (
          title_tag["content"]
          if title_tag and "content" in title_tag.attrs
          else title_tag.text if title_tag else "New Episode Released"
      )

      return image_url, title
  except Exception as e:
    print(f"Error fetching details: {e}")
  return None, "New Episode Released"


def send_telegram_post(photo_url, caption):
  """ഫോട്ടോ അപ്‌ലോഡ് ചെയ്ത് അതിന് താഴെ ക്യാപ്ഷനായി ഡീറ്റെയിൽസും ലിങ്കും നൽകുന്നു"""
  if not BOT_TOKEN or not CHANNEL_ID:
    return

  if photo_url:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHANNEL_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "Markdown",
    }
  else:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": caption,
        "parse_mode": "Markdown",
    }

  requests.post(url, data=payload)


def check_manoramamax_updates():
  sent_links = get_sent_links()
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      ),
      "Accept-Language": "en-US,en;q=0.9",
  }

  for show_url in TARGET_SHOWS:
    try:
      response = requests.get(show_url, headers=headers, timeout=10)
      if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=True)

        for a in links:
          href = a["href"]
          if "/detail/" in href or "/shows/" in href or "/episode" in href:
            full_url = (
                href
                if href.startswith("http")
                else f"https://www.manoramamax.com{href}"
            )

            if full_url not in sent_links and full_url not in TARGET_SHOWS:
              photo_url, title = get_episode_details(full_url, headers)

              url_parts = show_url.rstrip("/").split("/")
              show_name = (
                  url_parts[-1].replace("-", " ").title()
                  if len(url_parts) > 0
                  else "ManoramaMAX Show"
              )

              caption = f"""⎔ New Episode Released

│ Show: {show_name}
├─────────────────
├ Title: {title}
├ Platform: ManoramaMAX
└ Status: Latest Episode Available

➤ Watch Link:
{full_url}

│ 🌟─────────────────🌟"""

              send_telegram_post(photo_url, caption)
              save_sent_link(full_url)
              time.sleep(1)
    except Exception as e:
      print(f"Error checking show {show_url}: {e}")


def check_start():
  global LAST_OFFSET
  try:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 1}
    if LAST_OFFSET:
      params["offset"] = LAST_OFFSET

    res = requests.get(url, params=params).json()
    updates = res.get("result", [])

    for u in updates:
      LAST_OFFSET = u.get("update_id") + 1
      msg = u.get("message", {})
      if msg.get("text") == "/start":
        chat_id = msg.get("chat", {}).get("id")
        reply = "Hi, I am ManoramaMAX Notification Bot. I am active!"
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": reply},
        )
  except Exception as e:
    print(f"Start command error: {e}")


def bot_loop():
  while True:
    check_start()
    check_manoramamax_updates()
    time.sleep(300)


if __name__ == "__main__":
  t = threading.Thread(target=bot_loop)
  t.start()
  run_web_server()
                       
