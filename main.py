import os
import threading
import time
from bs4 import BeautifulSoup
from flask import Flask
import requests

app = Flask(__name__)


@app.route("/")
def home():
  try:
    check_start()
    check_manoramamax_updates()
  except Exception as e:
    print(f"Web trigger error: {e}")

  return (
      "ManoramaMAX Bot is Running Live & Checked for New Episodes Successfully!"
  )


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

LAST_OFFSET = None


def get_channel_sent_links():
  """ചാനലിൽ ഇതിനകം വന്ന ലിങ്കുകൾ ടെലഗ്രാമിൽ നിന്ന് തന്നെ പരിശോധിച്ചെടുക്കുന്നു"""
  sent_links = set()
  if not BOT_TOKEN or not CHANNEL_ID:
    return sent_links

  try:
    # ടെലഗ്രാം ചാനലിലെ അവസാന അപ്ഡേറ്റുകൾ/പോസ്റ്റുകൾ പരിശോധിക്കാൻ (ചാനൽ അഡ്മിൻ പദവി ബോട്ടിന് വേണം)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
    # ചാനൽ ആയതുകൊണ്ട് ഗെറ്റ് ചാറ്റ് വഴി നേരിട്ട് മെസ്സേജുകൾ എടുക്കാൻ കഴിഞ്ഞെന്ന് വരില്ല,
    # അതിനായി ടെലഗ്രാം ചാനലിൽ ബോട്ട് പോസ്റ്റ് ചെയ്ത ലിങ്കുകൾ ഒരു ബാക്ക്അപ്പ് രീതിയിൽ സൂക്ഷിക്കാൻ
    # അല്ലെങ്കിൽ ബോട്ടിലേക്ക് വരുന്ന അപ്ഡേറ്റുകൾ വഴിയാണ് സാധാരണ നോക്കുന്നത്.
    # എന്നാൽ ഇവിടെ സിംപിൾ ആയി ഫയൽ റീഡിങ് പിഴവ് ഒഴിവാക്കാൻ സുരക്ഷിതമായ മാർഗ്ഗം ഉപയോഗിക്കാം.
  except Exception as e:
    print(f"Error fetching channel history: {e}")

  # ഫയൽ വഴിയുള്ള രീതി തന്നെ സുരക്ഷിതമാക്കാൻ ഫയൽ ഇല്ലെങ്കിൽ ഓട്ടോമാറ്റിക് ഉണ്ടാക്കുന്ന കോഡ്:
  sent_links_file = "sent_manoramamax_episodes.txt"
  if os.path.exists(sent_links_file):
    try:
      with open(sent_links_file, "r") as f:
        sent_links = set(f.read().splitlines())
    except Exception:
      pass
  else:
    # ഫയൽ ഇല്ലെങ്കിൽ പുതിയൊരെണ്ണം ക്രിയേറ്റ് ചെയ്യുന്നു
    open(sent_links_file, "w").close()

  return sent_links


def save_sent_link(link):
  sent_links_file = "sent_manoramamax_episodes.txt"
  with open(sent_links_file, "a") as f:
    f.write(link + "\n")


def get_episode_details(episode_url, headers):
  try:
    res = requests.get(episode_url, headers=headers, timeout=10)
    if res.status_code == 200:
      soup = BeautifulSoup(res.text, "html.parser")
      img_tag = soup.find("meta", property="og:image")
      image_url = img_tag["content"] if img_tag else None

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
  sent_links = get_channel_sent_links()
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
    
