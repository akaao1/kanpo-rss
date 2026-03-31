import json
import os
import re
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin

import requests

BASE_URL = "https://www.kanpo.go.jp/"
JSON_FILE = "data/kanpo_feed.json"


class LinkExtractor(HTMLParser):
    """HTMLからaタグのhrefとテキストを拾うだけの最小パーサ"""
    def __init__(self):
        super().__init__()
        self.links = []
        self._in_a = False
        self._href = None
        self._text_parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._in_a = True
            self._href = dict(attrs).get("href")
            self._text_parts = []

    def handle_data(self, data):
        if self._in_a and data:
            self._text_parts.append(data.strip())

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._in_a:
            text = " ".join([t for t in self._text_parts if t]).strip()
            self.links.append((self._href, text))
            self._in_a = False
            self._href = None
            self._text_parts = []


def fetch_top_page_html() -> str:
    # 重要：低頻度・短時間・UA明示（サイト負荷を上げない）
    r = requests.get(
        BASE_URL,
        timeout=20,
        headers={"User-Agent": "kanpo-minimal-fetch/1.0 (+https://github.com/)"},
    )
    r.raise_for_status()
    return r.text


def extract_publish_date_from_html(html: str) -> str:
    """
    トップページ内の「令和 8年3月31日」のような表記を探して、
    1つ見つかったものを published に使う（見つからなければ今日の日付）
    """
    m = re.search(r"令和\s*\d+\s*年\s*\d+\s*月\s*\d+\s*日", html)
    if m:
        return m.group(0).replace(" ", "")
    return datetime.now().date().isoformat()


def pick_today_links(html: str):
    """
    トップページ内のリンクから「本日の官報」っぽいものを抽出する。
    なるべく“URLパターン”で拾う（HTML構造変更に強くする）
    """
    parser = LinkExtractor()
    parser.feed(html)

    candidates = []
    for href, text in parser.links:
        if not href:
            continue
        abs_url = urljoin(BASE_URL, href)

        # 官報ドメインのリンクだけ対象
        if not abs_url.startswith("https://www.kanpo.go.jp/"):
            continue

        # 今日の官報付近のリンクは /YYYYMMDD/ を含むことが多い（例：/20260316/…）
        # ただし必須ではないので、スコアリングで優先度付けする
        score = 0
        if re.search(r"/\d{8}/", abs_url):
            score += 3
        if "/pdf/" in abs_url:
            score += 2
        if any(k in text for k in ["本紙", "号外", "政府調達", "特別号外", "全体目次"]):
            score += 2

        # ある程度それっぽいものだけ残す
        if score >= 2:
            candidates.append((score, abs_url, text))

    # スコア降順で上位を返す（重複URLは除く）
    candidates.sort(key=lambda x: x[0], reverse=True)
    seen = set()
    results = []
    for score, url, text in candidates:
        if url in seen:
            continue
        seen.add(url)
        results.append((url, text, score))
    return results


def load_old_entries():
    if not os.path.exists(JSON_FILE):
        return []
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("entries", [])
    except json.JSONDecodeError:
        return []


def save_entries(entries):
    os.makedirs(os.path.dirname(JSON_FILE), exist_ok=True)
    final_data = {"updated_at": datetime.now().isoformat(), "entries": entries}
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)


def fetch_and_merge_data():
    print(f"1. 官報トップページ ({BASE_URL}) からデータを取得中...")

    html = fetch_top_page_html()
    published = extract_publish_date_from_html(html)

    links = pick_today_links(html)
    print(f"   => 候補リンク {len(links)} 件を抽出しました。")

    # 取得件数を絞る（負荷/ノイズ対策）：上位20件まで
    links = links[:20]

    new_entries = []
    for url, text, score in links:
        title = text if text else url
        new_entries.append(
            {
                "title": title,
                "link": url,
                "published": published,
                "id": url,
                "score": score,  # デバッグ用（不要なら削除OK）
                "source": "kanpo.go.jp top page",
            }
        )

    old_entries = load_old_entries()
    existing_ids = {e.get("id") for e in old_entries if e.get("id")}
    unique_new = [e for e in new_entries if e["id"] not in existing_ids]

    merged = unique_new + old_entries
    print(f"2. 新規 {len(unique_new)} 件を追加しました。")

    # publishedは日付文字列なので、ここでは新規優先で先頭に積むだけでもOK
    # 厳密ソートしたい場合は和暦→西暦変換が必要（後述）
    save_entries(merged)

    print(f"3. 合計 {len(merged)} 件を {JSON_FILE} に保存しました。")


if __name__ == "__main__":
    fetch_and_merge_data()
