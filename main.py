import os
import time
import requests

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# HTMLスクレイピングではなく、MediaWikiの公式APIを直接叩く方式に変更
# (HTMLページはCloudflareのbot対策でブロックされやすいが、api.phpは比較的安定している)
API_URL = "https://blox-fruits.fandom.com/api.php"

FRUIT_NAMES = [
    "Rocket", "Spin", "Chop", "Spring", "Bomb", "Smoke", "Spike", "Flame",
    "Falcon", "Ice", "Sand", "Dark", "Diamond", "Light", "Rubber", "Ghost",
    "Magma", "Quake", "Buddha", "Love", "Spider", "Sound", "Phoenix", "Portal",
    "Rumble", "Pain", "Blizzard", "Gravity", "Mammoth", "T-Rex", "Dough",
    "Shadow", "Venom", "Control", "Spirit", "Dragon", "Leopard", "Kitsune"
]


def get_stock(max_retries=3, retry_delay=5):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    })

    params = {
        "action": "parse",
        "page": "Template:CurrentStock",
        "format": "json",
        "prop": "wikitext",
    }

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(API_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            page_text = data.get("parse", {}).get("wikitext", {}).get("*", "")
            if not page_text:
                print(f"デバッグ: APIレスポンス全体 = {data}")
                raise ValueError("APIレスポンスにwikitextが含まれていません")

            print(f"デバッグ: 取得したwikitextの長さ = {len(page_text)} 文字")
            print(f"デバッグ: 先頭500文字 = {page_text[:500]}")

            fruits = [fruit for fruit in FRUIT_NAMES if fruit in page_text]
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
