document.addEventListener('DOMContentLoaded', () => {
    // データファイルのURL
    const JSON_FILE_URL = 'data/kanpo_feed.json';

    // UIエレメント
    const currentMonthDisplay = document.getElementById('current-month-display');
    const calendarGrid = document.getElementById('calendar-grid');
    const prevMonthButton = document.getElementById('prev-month');
    const nextMonthButton = document.getElementById('next-month');
    const selectedDateDisplay = document.getElementById('selected-date-display');
    const rssOutput = document.getElementById('rss-output');

    // 状態管理
    let currentDate = new Date();
    let kanpoData = null; // 全記事データを保持
    let articlesByDate = {}; // 日付ごとの記事を保持

    // ----------------------------------------------------------------------
    // 1. データ読み込みと初期化
    // ----------------------------------------------------------------------

    /** データを読み込み、日付ごとに整理する */
    async function loadData() {
        try {
            const response = await fetch(JSON_FILE_URL);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            // 記事データがあるか確認
            if (data && data.entries) {
                kanpoData = data.entries;
                processArticles(kanpoData);
                // データ読み込み成功後、カレンダーを描画し、最新日付の記事を表示する
                renderCalendar(); 
                displayDefaultArticles();
            } else {
                 rssOutput.innerHTML = '<p style="color: red;">エラー: JSONファイルにデータが含まれていません。</p>';
            }

        } catch (error) {
            console.error('データの読み込み中にエラーが発生しました:', error);
            rssOutput.innerHTML = `<p style="color: red;">フィードの表示中にエラーが発生しました: ${error.message}</p>`;
        }
    }

    /** 記事を日付ごとに整理し、グローバル変数に格納する */
    function processArticles(entries) {
        articlesByDate = {};
        entries.forEach(entry => {
            try {
                // '2025-10-01'形式の日付キーを生成
                const dateKey = new Date(entry.published).toISOString().substring(0, 10);
                if (!articlesByDate[dateKey]) {
                    articlesByDate[dateKey] = [];
                }
                articlesByDate[dateKey].push(entry);
            } catch (e) {
                // 日付解析エラーを無視
                console.warn('日付解析エラー:', entry.published, e);
            }
        });
    }

    // ----------------------------------------------------------------------
    // 2. カレンダー描画ロジック
    // ----------------------------------------------------------------------

    /** カレンダーを描画する */
    function renderCalendar() {
        // カレンダーのクリアとヘッダー更新
        calendarGrid.innerHTML = '';
        currentMonthDisplay.textContent = formatMonthYear(currentDate);

        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();

        // 曜日の追加
        const dayNames = ['日', '月', '火', '水', '木', '金', '土'];
        dayNames.forEach(name => {
            const dayNameCell = document.createElement('div');
            dayNameCell.classList.add('day-name');
            dayNameCell.textContent = name;
            calendarGrid.appendChild(dayNameCell);
        });

        // 月の開始曜日と日数の計算
        const firstDayOfMonth = new Date(year, month, 1).getDay();
        const daysInMonth = new Date(year, month + 1, 0).getDate();

        // 空のセルの追加
        for (let i = 0; i < firstDayOfMonth; i++) {
            const emptyCell = document.createElement('div');
            emptyCell.classList.add('date-cell', 'empty');
            calendarGrid.appendChild(emptyCell);
        }

        // 日付セルの追加
        for (let day = 1; day <= daysInMonth; day++) {
            const dateCell = document.createElement('div');
            dateCell.classList.add('date-cell');
            dateCell.textContent = day;
            dateCell.dataset.date = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            
            // データが存在するかチェック
            if (articlesByDate[dateCell.dataset.date]) {
                dateCell.classList.add('has-data');
            }

            // クリックイベントの追加
            dateCell.addEventListener('click', (e) => {
                if (e.target.classList.contains('empty')) return;
                displayArticles(e.target.dataset.date);
                highlightSelectedDate(e.target);
            });

            calendarGrid.appendChild(dateCell);
        }
    }

    /** 選択された日付をハイライトする */
    function highlightSelectedDate(selectedCell) {
        document.querySelectorAll('.date-cell').forEach(cell => cell.classList.remove('active'));
        if (selectedCell) {
            selectedCell.classList.add('active');
        }
    }


    // ----------------------------------------------------------------------
    // 3. 記事表示ロジック
    // ----------------------------------------------------------------------
    
    /** サイトを開いたとき、最新日付の記事を表示する */
    function displayDefaultArticles() {
        if (!kanpoData || kanpoData.length === 0) return;

        // 全記事の最初の日付を取得 (データは最新順にソートされているはず)
        const latestEntry = kanpoData[0];
        const latestDateKey = new Date(latestEntry.published).toISOString().substring(0, 10);
        
        displayArticles(latestDateKey);
        
        // カレンダーに最新日付をハイライト（現在の月であれば）
        const latestDate = new Date(latestDateKey);
        if (latestDate.getFullYear() === currentDate.getFullYear() && latestDate.getMonth() === currentDate.getMonth()) {
            const cell = document.querySelector(`.date-cell[data-date="${latestDateKey}"]`);
            highlightSelectedDate(cell);
        }
    }

    /** 指定された日付の記事を表示する */
    function displayArticles(dateKey) {
        const articles = articlesByDate[dateKey] || [];
        
        selectedDateDisplay.textContent = formatDateKey(dateKey);

        if (articles.length === 0) {
            rssOutput.innerHTML = '<p>この日の官報記事はありません。</p>';
            return;
        }

        let html = '<ul>';
        articles.forEach(item => {
            const pubDate = formatDateKey(new Date(item.published).toISOString().substring(0, 10));

            html += `
                <li>
                    <a href="${item.link}" target="_blank" rel="noopener noreferrer">${item.title}</a>
                    <small>公開日: ${pubDate}</small>
                </li>
            `;
        });
        html += '</ul>';
        rssOutput.innerHTML = html;
    }

    // ----------------------------------------------------------------------
    // 4. イベントリスナーとユーティリティ
    // ----------------------------------------------------------------------

    prevMonthButton.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() - 1);
        renderCalendar();
    });

    nextMonthButton.addEventListener('click', () => {
        currentDate.setMonth(currentDate.getMonth() + 1);
        renderCalendar();
    });

    /** YYYY-MM-DD形式を「YYYY年M月D日」形式に変換 */
    function formatDateKey(dateKey) {
        const [year, month, day] = dateKey.split('-');
        return `${year}年${parseInt(month)}月${parseInt(day)}日`;
    }
    
    /** YYYY年M月形式に変換 */
    function formatMonthYear(date) {
        return `${date.getFullYear()}年${date.getMonth() + 1}月`;
    }


    // 初期実行
    loadData();
});
