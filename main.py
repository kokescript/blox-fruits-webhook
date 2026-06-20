import os
import re
import time
import requests

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# HTMLスクレイピングではなく、MediaWikiの公式APIを直接叩く方式に変更
# (HTMLページはCloudflareのbot対策でブロックされやすいが、api.phpは比較的安定している)
API_URL = "https://blox-fruits.fandom.com/api.php"


def get_stock(max_retries=3, retry_delay=5):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    })

    params = {
        "action": "parse",
        "page": 'Blox Fruits "Stock"',
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
                raise ValueError("APIレスポンスにwikitextが含まれていません")

            # "|Current = Flame, Sand, Love" のような行だけを取り出す
            match = re.search(r"\|\s*Current\s*=\s*(.+)", page_text)
            if not match:
                raise ValueError("Current在庫の行が見つかりませんでした")

            current_line = match.group(1).strip()
            fruits = [f.strip() for f in current_line.split(",") if f.strip()]
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
    import re
    import requests as _requests

    _url = "https://fruityblox.com/stock"
    _headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    _response = _requests.get(_url, headers=_headers, timeout=15)
    _text = _response.text

    print("===== preloadされている画像からフルーツ名を抽出 =====")
    _preload_fruits = re.findall(r'/images/fruits/([a-z0-9\-]+)\.webp', _text)
    print(_preload_fruits)

    print("===== 'Normal' という単語の前後500文字 =====")
    _idx = _text.find(">Normal<")
    if _idx == -1:
        _idx = _text.find("Normal")
    print(_text[max(0, _idx-200):_idx+800])

    print("===== href=\"/items/\" のリンク一覧 =====")
    _item_links = re.findall(r'/items/([a-z0-9\-]+)', _text)
    print(_item_links)
