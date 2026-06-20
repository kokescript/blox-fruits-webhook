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


# フルーツ名(小文字スラッグ) → カスタム絵文字 の対応表
# 絵文字が登録されていないフルーツは、自動でテキストのみの表示になる
FRUIT_EMOJIS = {
    "rocket": "<:rocket:1517892353023541319>",
    "spin": "<:spin:1517892327321108640>",
    "blade": "<:blade:1517892297524510851>",
    "spring": "<:spring:1517892266587455558>",
    "bomb": "<:bomb:1517892227513323570>",
    "smoke": "<:smoke:1517892174081953882>",
    "spike": "<:spike:1517892145955078266>",
    "flame": "<:Flame:1517892093123760328>",
    "dark": "<:dark:1517891982087946310>",
    "sand": "<:sand:1517891871920226516>",
    "ice": "<:ICE:1517891849950331030>",
    "rubber": "<:rubber:1517891823945650237>",
    "ghost": "<:Ghost:1517891777288343733>",
    "eagle": "<:Falcon:1517891710921736482>",
    "light": "<:Light:1517896780019404948>",
    "quake": "<:Quake:1517896834754940969>",
    "diamond": "<:diamond:1517891345602183392>",
    "magma": "<:magma:1517891248357380098>",
    "love": "<:Love:1517891188751859842>",
    "spider": "<:spider:1517891167696719892>",
    "sound": "<:sound:1517891139942744184>",
    "phoenix": "<:__:1517891089837588714>",
    "blizzard": "<:Blizzard:1517891040873283584>",
    "shadow": "<:SHADOW:1517891015749664788>",
    "mammoth": "<:mammoth:1517890988087971992>",
    "portal": "<:Portal:1517890967464575077>",
    "buddha": "<:Baddha:1517890833330995401>",
    "spirit": "<:Spirit:1517890810769707009>",
    "control": "<:control:1517890776149922102>",
    "venom": "<:venom:1517890755387986122>",
    "gravity": "<:Gravity:1517890734257344542>",
    "pain": "<:pain:1517890712887234641>",
    "t-rex": "<:TLEX:1517890689285886172>",
    "dough": "<:Dough:1517890671002779841>",
    "rumble": "<:Rumble:1517890636332793994>",
    "tiger": "<:tiger:1517890600878211215>",
    "gas": "<:GAS:1517890586517045280>",
    "yeti": "<:Yeti:1517890567328108554>",
    "kitsune": "<:kitsune:1517890548482965735>",
    "dragon-east": "<:DragonEast:1517890531823456316>",
    "dragon-west": "<:DragonWest:1517890511367700510>",
}


def fruit_display(fruit, use_emoji=False):
    """use_emoji=Trueなら絵文字付き、Falseならテキストのみで表示用文字列を作る"""
    if use_emoji:
        emoji = FRUIT_EMOJIS.get(fruit["slug"], "")
        if emoji:
            return f"{emoji} {fruit['name']}"
    return f"• {fruit['name']}"


def build_payload(stock_data, use_emoji=False):
    now_unix = int(datetime.now(timezone.utc).timestamp())
    timestamp_text = f"<t:{now_unix}:R>"

    normal_text = "\n".join([fruit_display(f, use_emoji) for f in stock_data["normal"]]) or "（取得できませんでした）"
    mirage_text = "\n".join([fruit_display(f, use_emoji) for f in stock_data["mirage"]]) or "（取得できませんでした）"

    description = (
        "**ノーマルフルーツディーラー**" + "\n" + normal_text + "\n\n" +
        "**ミラージュフルーツディーラー**" + "\n" + mirage_text + "\n\n" +
        timestamp_text
    )

    return {
        "username": "ブロフル入荷Bot",
        "embeds": [{
            "title": "🏪 フルーツディーラー在庫",
            "description": description,
            "color": 16753920
        }]
    }


def send_discord(stock_data):
    if not WEBHOOK_URL and not WEBHOOK_URL_2:
        print("警告: DISCORD_WEBHOOK_URL が設定されていません。GitHubのSecretsを確認してください。")
        return
    if not stock_data or (not stock_data["normal"] and not stock_data["mirage"]):
        print("在庫取得失敗、または在庫が空です")
        return

    # 1つ目のWebhook: テキストのみ（絵文字なし）
    if WEBHOOK_URL:
        payload = build_payload(stock_data, use_emoji=False)
        res = requests.post(WEBHOOK_URL, json=payload)
        print(f"Discord送信ステータス (Webhook 1, テキストのみ): {res.status_code}")

    # 2つ目のWebhook: 絵文字付き
    if WEBHOOK_URL_2:
        payload = build_payload(stock_data, use_emoji=True)
        res = requests.post(WEBHOOK_URL_2, json=payload)
        print(f"Discord送信ステータス (Webhook 2, 絵文字付き): {res.status_code}")


if __name__ == "__main__":
    stock = get_stock()
    send_discord(stock)
