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
