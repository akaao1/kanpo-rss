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

# ----------------------------------------------------
# メインデータ処理関数
# ----------------------------------------------------

def fetch_and_merge_data():
    """
    RSSフィードから最新データを取得し、既存のJSONデータとマージして保存する
    """
    print(f"1. RSSフィード ({RSS_URL}) からデータを取得中...")
    
    # 1. RSSフィードから最新データを取得
    feed = feedparser.parse(RSS_URL)
    
    new_entries = []
    for entry in feed.entries:
        published_date = getattr(entry, 'published', None)
        
        if entry.title and entry.link and published_date:
            new_entries.append({
                'title': entry.title,
                'link': entry.link,
                'published': published_date,
                'id': getattr(entry, 'id', entry.link) 
            })
    
    print(f"   => RSSフィードから {len(new_entries)} 件の記事を取得しました。")

    # 2. 既存のデータを読み込み
    old_entries = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                old_entries = data.get('entries', [])
            print(f"2. 既存のJSONファイルから {len(old_entries)} 件の記事を読み込みました。")
        except json.JSONDecodeError:
            print("2. 既存のJSONファイルの形式が不正です。新規ファイルとして処理を続行します。")

    # 3. 新旧データをマージし、重複を排除
    
    existing_ids = {entry['id'] for entry in old_entries}
    
    unique_new_entries = [
        entry for entry in new_entries
        if entry['id'] not in existing_ids
    ]
    
    merged_entries = unique_new_entries + old_entries
    
    print(f"3. {len(unique_new_entries)} 件の新しい記事を追加しました。")

    # 4. 日付順に並べ替え（最新の日付が上になるように降順でソート）
    def sort_key(entry):
        try:
            # RFC 822形式
            return datetime.strptime(entry['published'], '%a, %d %b %Y %H:%M:%S %z')
        except ValueError:
            try:
                # ISO 8601形式などの代替処理
                return datetime.fromisoformat(entry['published'].replace('Z', '+00:00'))
            except ValueError:
                return datetime.min

    merged_entries.sort(key=sort_key, reverse=True)
    
    print(f"   => 合計 {len(merged_entries)} 件の記事を最新順に並べ替えました。")

    # 5. 最終データをJSON形式で保存
    final_data = {
        'updated_at': datetime.now().isoformat(),
        'entries': merged_entries
    }

    os.makedirs(os.path.dirname(JSON_FILE), exist_ok=True)
    
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"4. 最新のデータ ({len(merged_entries)} 件) を {JSON_FILE} に保存しました。")
    
    # HTML更新のために最終データを返す
    return final_data

# ----------------------------------------------------
# HTML生成・更新のための関数（NotebookLM対策）
# ----------------------------------------------------

def create_article_list_html(entries):
    """記事データのリストを受け取り、HTMLのリスト形式に変換して返す"""
    html_list = '<ul>'
    
    if not entries:
        return '<p style="text-align: center; color: #777; padding-top: 20px;">記事が見つかりませんでした。</p>'

    for item in entries:
        # 日付を読みやすい形式に整形
        try:
            date_obj = datetime.strptime(item['published'], '%a, %d %b %Y %H:%M:%S %z')
            pubDate = date_obj.strftime('%Y/%m/%d')
        except ValueError:
            pubDate = '日付不明' 
            
        html_list += f"""
            <li>
                <p><strong><a href="{item['link']}" target="_blank" rel="noopener noreferrer">{item['title']}</a></strong></p>
                <p><small>公開日: {pubDate}</small></p>
            </li>
        """
    html_list += '</ul>'
    return html_list

def update_index_html(html_list):
    """生成されたHTMLリストをindex.htmlの目印の間に書き込む"""
    INDEX_FILE = 'index.html'
    
    # 目印タグを定義（index.htmlで設定したものと完全に一致させる必要があります）
    START_TAG = ''
    END_TAG = ''
    
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # 目印の間にあるコンテンツを検索
        start_index = html_content.find(START_TAG)
        end_index = html_content.find(END_TAG)
        
        if start_index != -1 and end_index != -1:
            # 新しいコンテンツを構築 (目印タグは残す)
            new_content = html_content[:start_index + len(START_TAG)] + \
                          html_list + \
                          html_content[end_index:]
            
            # index.htmlを上書き保存
            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"5. {INDEX_FILE} を静的な記事リストで更新しました。")
        else:
            print(f"5. ERROR: {START_TAG} または {END_TAG} が {INDEX_FILE} 内に見つかりません。HTMLの目印を確認してください。")
            
    except FileNotFoundError:
        print(f"5. ERROR: {INDEX_FILE} が見つかりません。")


# ----------------------------------------------------
# スクリプト実行開始点
# ----------------------------------------------------
if __name__ == '__main__':
    final_data = fetch_and_merge_data() # データ取得・マージ関数を実行し、最終データを取得

    # HTMLの更新
    if final_data and final_data.get('entries'):
        # 記事リストHTMLを生成
        html_list = create_article_list_html(final_data['entries'])
        # index.htmlに書き込み
        update_index_html(html_list)
