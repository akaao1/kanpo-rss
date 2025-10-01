// ページ全体が読み込まれた後に実行します
document.addEventListener('DOMContentLoaded', function() {
    // データを表示するためのHTML要素（IDが'rss-output'の要素）を見つけます
    const container = document.getElementById('rss-output');
    
    // データファイルへのパスを指定します
    const jsonUrl = './data/kanpo_feed.json'; 

    // 過去7日間の基準日を計算
    const today = new Date();
    // 7日前の日付を計算 (協定世界時UTCでの比較を避けるため、一旦日付をリセットしてから計算します)
    const sevenDaysAgo = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 7); 
    sevenDaysAgo.setHours(0, 0, 0, 0); // 7日前の0時0分0秒をフィルタリングの開始点とする

    // 1. JSONファイルを非同期で読み込み
    fetch(jsonUrl)
        .then(response => {
            // ファイルが正常に読み込まれたかチェック
            if (!response.ok) {
                // 失敗した場合はエラー
                throw new Error('データの読み込みに失敗しました。');
            }
            // 2. 応答（テキスト）をJavaScriptのJSONオブジェクトに変換
            return response.json();
        })
        .then(data => {
            // ----------------------------------------------------
            // ★★★ 修正箇所: 7日間の記事をフィルタリング ★★★
            // ----------------------------------------------------
            
            // 官報フィードのデータ（entries）を取得
            const allItems = data.entries || []; 

            // 7日以内に公開された記事のみをフィルタリング
            const recentItems = allItems.filter(item => {
                const itemDate = new Date(item.published);
                // 記事の公開日が、7日前以降であるかを確認
                return itemDate >= sevenDaysAgo;
            });
            
            // 並び替え (念のため、公開日で降順（新しい順）にソートします)
            // JSONデータが既に新しい順になっている可能性が高いですが、念のため実行します。
            recentItems.sort((a, b) => {
                return new Date(b.published) - new Date(a.published);
            });

            // ----------------------------------------------------
            
            // 3. フィルタリング後のデータを使ってHTMLの内容を作成
            let htmlContent = '<ul>';

            // フィルタリングされたすべての記事を表示
            recentItems.forEach(item => { 
                // 各記事の情報を使ってリスト要素を作成
                // item.published（公開日）を読みやすい形式に変換
                const pubDate = new Date(item.published).toLocaleDateString('ja-JP');
                
                htmlContent += `
                    <li>
                        <p><strong><a href="${item.link}" target="_blank" rel="noopener noreferrer">${item.title}</a></strong></p>
                        <p><small>公開日: ${pubDate}</small></p>
                    </li>
                `;
            });
            
            htmlContent += '</ul>';

            if (recentItems.length === 0) {
                htmlContent = '<p>直近7日間に官報の記事はありません。</p>';
            }
            
            // 4. 作成したHTMLをWebページに挿入
            container.innerHTML = htmlContent;
        })
        .catch(error => {
            // エラーが発生した場合のメッセージ表示
            container.innerHTML = `<p style="color: red;">フィードの表示中にエラーが発生しました: ${error.message}</p>`;
            console.error(error);
        });
});
