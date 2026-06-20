import os
import requests
import json
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def get_stock():
    try:
        url = "https://blox-fruits.fandom.com/wiki/Blox_Fruits_Wiki"

        # 完全にブラウザのふりをするためのUser-Agent
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        fruits = []

        # Wikiページ全体から果物名候補を探す
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

    except Exception as e:
        print(f"エラー発生: {e}")
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

    res = requests.post(
        WEBHOOK_URL,
        json=payload
    )
    print(f"Discord送信ステータス: {res.status_code}")

if __name__ == "__main__":
    stock = get_stock()
    send_discord(stock)
