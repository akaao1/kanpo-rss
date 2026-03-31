import feedparser
import json
import os
from datetime import datetime
import requests
import urllib3

# ----------------------------------------------------
# 設定
# ----------------------------------------------------
# 公式kanpo.go.jpの /rss/latest.xml は 404 なので、
# 動作するRSS配信元（第三者）に切替
RSS_URL = "https://martians-sheep.github.io/kanpo-rss/feed.xml"
JSON_FILE = "data/kanpo_feed.json"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch_feed_content(url: str) -> bytes:
    r = requests.get(
        url,
        timeout=30,
        verify=True,  # 第三者GitHub Pagesは通常verifyでOK
        headers={"User-Agent": "kanpo-rss-fetch/1.0 (+https://github.com/)"},
    )
    r.raise_for_status()
    return r.content

def fetch_and_merge_data():
    print(f"1. RSSフィード ({RSS_URL}) からデータを取得中...")

    try:
        content = fetch_feed_content(RSS_URL)
    except Exception as e:
        print("   => RSS取得に失敗しました。以下のエラー内容を確認してください：")
        print(f"      {type(e).__name__}: {e}")
        raise

    feed = feedparser.parse(content)

    if getattr(feed, "bozo", 0) == 1:
        print("   => RSS解析中に警告/エラーが出ています（bozo=1）。")
        print(f"      bozo_exception: {getattr(feed, 'bozo_exception', None)}")

    new_entries = []
    for entry in feed.entries:
        published_date = getattr(entry, "published", None) or getattr(entry, "updated", None)

        if getattr(entry, "title", None) and getattr(entry, "link", None) and published_date:
            new_entries.append(
                {
                    "title": entry.title,
                    "link": entry.link,
                    "published": published_date,
                    "id": getattr(entry, "id", entry.link),
                }
            )

    print(f"   => RSSフィードから {len(new_entries)} 件の記事を取得しました。")

    # 2. 既存のデータを読み込み
    old_entries = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                old_entries = data.get("entries", [])
            print(f"2. 既存のJSONファイルから {len(old_entries)} 件の記事を読み込みました。")
        except json.JSONDecodeError:
            print("2. 既存のJSONファイルの形式が不正です。新規ファイルとして処理を続行します。")

    # 3. 新旧データをマージし、重複を排除
    existing_ids = {entry.get("id") for entry in old_entries if entry.get("id")}
    unique_new_entries = [e for e in new_entries if e["id"] not in existing_ids]
    merged_entries = unique_new_entries + old_entries
    print(f"3. {len(unique_new_entries)} 件の新しい記事を追加しました。")

    # 4. 日付順に並べ替え
    def sort_key(entry):
        # RSS/Atomで形式が揺れるので、feedparserのparsedがあればそれを優先しても良いが、
        # ここでは既存ロジック維持のため簡易対応
        try:
            return datetime.strptime(entry["published"], "%a, %d %b %Y %H:%M:%S %z")
        except Exception:
            try:
                return datetime.fromisoformat(entry["published"].replace("Z", "+00:00"))
            except Exception:
                return datetime.min

    merged_entries.sort(key=sort_key, reverse=True)
    print(f"   => 合計 {len(merged_entries)} 件の記事を最新順に並べ替えました。")

    final_data = {"updated_at": datetime.now().isoformat(), "entries": merged_entries}

    os.makedirs(os.path.dirname(JSON_FILE), exist_ok=True)
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"4. 最新のデータ ({len(merged_entries)} 件) を {JSON_FILE} に保存しました。")

if __name__ == "__main__":
    fetch_and_merge_data()
