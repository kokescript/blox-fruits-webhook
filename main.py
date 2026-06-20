import os
import re
import time
import requests
from datetime import datetime, timezone

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

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

            def to_names(slugs):
                return [slug.replace("-", " ").title() for slug in slugs]

            return {
                "normal": to_names(normal_slugs),
                "mirage": to_names(mirage_slugs),
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


def send_discord(stock_data):
    if not WEBHOOK_URL:
        print("警告: DISCORD_WEBHOOK_URL が設定されていません。GitHubのSecretsを確認してください。")
        return
    if not stock_data or (not stock_data["normal"] and not stock_data["mirage"]):
        print("在庫取得失敗、または在庫が空です")
        return

    normal_text = "\n".join([f"• {fruit}" for fruit in stock_data["normal"]]) or "（取得できませんでした）"
    mirage_text = "\n".join([f"• {fruit}" for fruit in stock_data["mirage"]]) or "（取得できませんでした）"

    # Discordの相対時刻表示（例: "数秒前"）用のUnixタイムスタンプ
    now_unix = int(datetime.now(timezone.utc).timestamp())
    timestamp_text = f"<t:{now_unix}:R>"

    description = (
        f"**ノーマルフルーツディーラー**\n{normal_text}\n\n"
        f"**ミラージュフルーツディーラー**\n
