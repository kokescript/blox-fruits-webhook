import os
import time
import requests
import cloudscraper
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Cloudflareのbot対策を回避するスクレイパー（requestsの代わりに使う）
scraper = cloudscraper.create_scraper(
    browser={
        "browser": "chrome",
        "platform": "android",
        "mobile": True,
    }
)


def get_stock(max_retries=3, retry_delay=5):
    url = "https://m.blox-fruits.fandom.com/wiki/Blox_Fruits_Wiki"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = scraper.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            fruits = []
            fruit_names = [
                "Rocket", "Spin", "Chop", "Spring", "Bomb", "Smoke", "Spike", "Flame",
                "Falcon", "Ice", "Sand", "Dark", "Diamond", "Light", "Rubber", "Ghost",
                "Magma", "Quake", "Buddha", "Love", "Spider", "Sound", "Phoenix", "Portal",
                "Rumble", "Pain", "Blizzard", "Gravity", "Mammoth", "T-Rex", "Dough",
                "Shadow", "Venom", "Control", "Spirit", "Dragon", "Leopard", "Kitsune"
            ]
            page_text = soup.get_text()
            for fruit in fruit_names:
                if fruit in page_text:
                    fruits.append(fruit)

            return fruits

        except (requests.exceptions.SSLError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            last_error = e
            print(f"試行 {attempt}/{max_retries} 失敗（接続エラー）: {e}")
            if attempt < max_retries:
                wait = retry_delay * attempt  # 5秒, 10秒, 15秒...と間隔を広げる
                print(f"{wait}秒待って再試行します...")
                time.sleep(wait)

        except Exception as e:
            last_error = e
            print(f"試行 {attempt}/{max_retries} 失敗（その他のエラー）: {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)

    print(f"全{max_retries}回の試行に失敗しました。最後のエラー: {last_error}")
    return []


def send_discord(stock_list):
    if not WEBHOOK_URL:
        print("警告: DISCORD_WEBHOOK_URL が設定されていません。GitHubのSecretsを確認してください。")
        return
    if not stock_list:
        print("在庫取得失敗、または在庫が空です")
        return

    payload = {
        "username": "ブロフル入荷Bot",
        "embeds": [{
            "title": "🏪 フルーツディーラー在庫",
            "description": "\n".join(
                [f"• {fruit}" for fruit in stock_list]
            ),
            "color": 16753920
        }]
    }
    res = requests.post(WEBHOOK_URL, json=payload)
    print(f"Discord送信ステータス: {res.status_code}")


if __name__ == "__main__":
    stock = get_stock()
    send_discord(stock)
