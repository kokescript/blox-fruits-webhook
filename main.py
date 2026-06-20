import os
import re
import time
import requests
from datetime import datetime, timezone

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
WEBHOOK_URL_2 = os.environ.get("DISCORD_WEBHOOK_URL_2")

# fruityblox.com はゲーム内ショップから自動でデータを取得しているため、
# Wikiの手動更新よりも正確・リアルタイムに近い
STOCK_URL = "https://fruityblox.com/stock"


def get_stock(max_retries=3, retry_delay=5):
    """Normal在庫とMirage在庫の両方を取得して辞書で返す"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    })

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(STOCK_URL, timeout=15)
            response.raise_for_status()
            html = response.text

            normal_start = html.find(">Normal<")
            mirage_start = html.find(">Mirage<")
            if normal_start == -1 or mirage_start == -1:
                raise ValueError("NormalまたはMirageのセクションが見つかりませんでした")

            # Normalセクション: "Normal"の見出しから"Mirage"の見出しまで
            normal_section = html[normal_start:mirage_start]
            # Mirageセクション: "Mirage"の見出しから先(ページ末尾近くまで)
            mirage_section = html[mirage_start:mirage_start + 5000]

            normal_slugs = re.findall(r'/items/([a-z0-9\-]+)', normal_section)
            mirage_slugs = re.findall(r'/items/([a-z0-9\-]+)', mirage_section)

            if not normal_slugs and not mirage_slugs:
                raise ValueError("在庫アイテムが見つかりませんでした")

            def to_fruit_list(slugs):
                return [
                    {"name": slug.replace("-", " ").title(), "slug": slug}
                    for slug in slugs
                ]

            return {
                "normal": to_fruit_list(normal_slugs),
                "mirage": to_fruit_list(mirage_slugs),
            }

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
    return None


FRUIT_IMAGE_BASE = "https://fruityblox.com/images/fruits/"


def send_discord(stock_data):
    # 設定されているWebhook URLをすべて集める（未設定のものは除く）
    webhook_urls = [url for url in [WEBHOOK_URL, WEBHOOK_URL_2] if url]

    if not webhook_urls:
        print("警告: DISCORD_WEBHOOK_URL が設定されていません。GitHubのSecretsを確認してください。")
        return
    if not stock_data or (not stock_data["normal"] and not stock_data["mirage"]):
        print("在庫取得失敗、または在庫が空です")
        return

    # Discordの相対時刻表示（例: "数秒前"）用のUnixタイムスタンプ
    now_unix = int(datetime.now(timezone.utc).timestamp())
    timestamp_text = f"<t:{now_unix}:R>"

    embeds = []

    # 見出し用の最初の埋め込み（オレンジ色）
    embeds.append({
        "title": "🏪 フルーツディーラー在庫",
        "description": "**ノーマルフルーツディーラー**" + "\n" + timestamp_text,
        "color": 16753920
    })

    # ノーマル在庫: フルーツごとに画像付き埋め込み
    for fruit in stock_data["normal"]:
        embeds.append({
            "description": "• " + fruit["name"],
            "color": 16753920,
            "thumbnail": {"url": FRUIT_IMAGE_BASE + fruit["slug"] + ".webp"}
        })

    # ミラージュ見出し
    embeds.append({
        "description": "**ミラージュフルーツディーラー**",
        "color": 10181046
    })

    # ミラージュ在庫: フルーツごとに画像付き埋め込み
    for fruit in stock_data["mirage"]:
        embeds.append({
            "description": "• " + fruit["name"],
            "color": 10181046,
            "thumbnail": {"url": FRUIT_IMAGE_BASE + fruit["slug"] + ".webp"}
        })

    # Discordは1メッセージにつきembed最大10個まで。超える場合は分割して送信する
    chunk_size = 10

    # 設定されている全てのWebhook URL（=全サーバー）に同じ内容を送る
    for webhook_url in webhook_urls:
        for i in range(0, len(embeds), chunk_size):
            chunk = embeds[i:i + chunk_size]
            payload = {
                "username": "ブロフル入荷Bot",
                "embeds": chunk
            }
            res = requests.post(webhook_url, json=payload)
            print(f"Discord送信ステータス (送信先末尾: ...{webhook_url[-6:]}, {i // chunk_size + 1}通目): {res.status_code}")


if __name__ == "__main__":
    stock = get_stock()
    send_discord(stock)
