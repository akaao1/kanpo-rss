// ページ全体が読み込まれた後に実行します
document.addEventListener('DOMContentLoaded', function() {
    // データを表示するためのHTML要素（IDが'rss-output'の要素）を見つけます
    const container = document.getElementById('rss-output');
    
    // データファイルへのパスを指定します
    const jsonUrl = './data/kanpo_feed.json'; 

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
            // 3. 変換後のJSONデータを使ってHTMLの内容を作成

            let htmlContent = '<ul>';
            
            // JSONの構造に合わせて data.entries を参照します
            const itemsToShow = data.entries.slice(0, 5); 

            itemsToShow.forEach(item => { 
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
            
            // 4. 作成したHTMLをWebページに挿入
            container.innerHTML = htmlContent;
        })
        .catch(error => {
            // エラーが発生した場合のメッセージ表示
            container.innerHTML = `<p style="color: red;">フィードの表示中にエラーが発生しました: ${error.message}</p>`;
            console.error(error);
        });
});
