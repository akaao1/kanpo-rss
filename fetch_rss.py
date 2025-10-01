import feedparser
import json
import os
from datetime import datetime

# ----------------------------------------------------
# 設定
# ----------------------------------------------------
# 官報RSSフィードのURL
RSS_URL = 'https://www.kanpo.go.jp/rss/latest.xml'
# データファイルのパス
JSON_FILE = 'data/kanpo_feed.json'

def fetch_and_merge_data():
    """
    RSSフィードから最新データを取得し、既存のJSONデータとマージして保存する
    """
    print(f"1. RSSフィード ({RSS_URL}) からデータを取得中...")
    
    # 1. RSSフィードから最新データを取得
    feed = feedparser.parse(RSS_URL)
    
    # 新しい記事データを、JavaScriptで扱いやすい形式に変換
    new_entries = []
    for entry in feed.entries:
        # RSSフィードによっては 'published' がない場合があるため、チェック
        published_date = getattr(entry, 'published', None)
        
        # データの品質を保証するため、タイトルとリンクと発行日があるものだけを対象とする
        if entry.title and entry.link and published_date:
            new_entries.append({
                'title': entry.title,
                'link': entry.link,
                'published': published_date,
                # 記事のユニークID（重複排除用。linkがない場合に備えてIDを優先）
                'id': getattr(entry, 'id', entry.link) 
            })
    
    print(f"   => RSSフィードから {len(new_entries)} 件の記事を取得しました。")

    # 2. 既存のデータを読み込み
    old_entries = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # ファイル構造が { "entries": [...] } であることを前提とする
                old_entries = data.get('entries', [])
            print(f"2. 既存のJSONファイルから {len(old_entries)} 件の記事を読み込みました。")
        except json.JSONDecodeError:
            # JSONが不正な場合、空のリストから開始
            print("2. 既存のJSONファイルの形式が不正です。新規ファイルとして処理を続行します。")

    # 3. 新旧データをマージし、重複を排除
    
    # 既存の記事のIDリストを作成
    existing_ids = {entry['id'] for entry in old_entries}
    
    # 重複しない新しい記事だけを抽出
    unique_new_entries = [
        entry for entry in new_entries
        if entry['id'] not in existing_ids
    ]
    
    # 新しい記事と古い記事を結合
    merged_entries = unique_new_entries + old_entries
    
    print(f"3. {len(unique_new_entries)} 件の新しい記事を追加しました。")

    # 4. 日付順に並べ替え（最新の日付が上になるように降順でソート）
    # 日付文字列をdatetimeオブジェクトに変換してソート
    def sort_key(entry):
        try:
            # feedparserのpublishedはRFC 822形式の文字列であることが多いため、datetimeオブジェクトに変換
            return datetime.strptime(entry['published'], '%a, %d %b %Y %H:%M:%S %z')
        except ValueError:
             # 異なる形式の場合の代替処理 (例: ISO 8601形式など)
            try:
                return datetime.fromisoformat(entry['published'].replace('Z', '+00:00'))
            except ValueError:
                # 変換できない場合はソートの末尾に置くため古い日付を返す
                return datetime.min

    merged_entries.sort(key=sort_key, reverse=True)
    
    print(f"   => 合計 {len(merged_entries)} 件の記事を最新順に並べ替えました。")

    # 5. 最終データをJSON形式で保存
    final_data = {
        'updated_at': datetime.now().isoformat(),
        'entries': merged_entries
    }

    # dataディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(JSON_FILE), exist_ok=True)
    
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        # JSONを整形（indent=2）して書き込み、読みやすくする
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"4. 最新のデータ ({len(merged_entries)} 件) を {JSON_FILE} に保存しました。")


if __name__ == '__main__':
    fetch_and_merge_data()
