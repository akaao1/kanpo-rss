// 全体のデータと状態を保持するグローバル変数
let kanpoData = [];
let articlesByDate = {}; // 日付をキーとして記事を格納する辞書
let currentMonth = new Date(); // 現在表示しているカレンダーの月
let selectedDate = null; // 現在選択している日付

// DOM要素の取得
const container = document.getElementById('rss-output');
const monthDisplay = document.getElementById('current-month-display');
const calendarGrid = document.getElementById('calendar-grid');
const selectedDateDisplay = document.getElementById('selected-date-display');
const prevMonthButton = document.getElementById('prev-month');
const nextMonthButton = document.getElementById('next-month');

// ----------------------------------------------------
// ユーティリティ関数
// ----------------------------------------------------

/**
 * Dateオブジェクトから 'YYYY-MM-DD' 形式の文字列を取得
 * @param {Date} date
 * @returns {string} 
 */
function formatDate(date) {
    // タイムゾーンのズレを避けるため、UTCベースで日付を取得
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

// ----------------------------------------------------
// カレンダーと表示のロジック
// ----------------------------------------------------

/**
 * 特定の日の記事だけをフィルタリングして表示する
 * @param {Date} date
 */
function displayArticlesByDate(date) {
    if (!container) return; // コンテナがない場合は処理しない
    
    const dateKey = formatDate(date);
    const articles = articlesByDate[dateKey] || [];
    
    // 日付表示を更新
    if (selectedDateDisplay) {
        selectedDateDisplay.textContent = `${date.getFullYear()}年 ${date.getMonth() + 1}月 ${date.getDate()}日の官報`;
    }

    let htmlContent = '<ul>';

    if (articles.length === 0) {
        htmlContent = `<p style="text-align: center; color: #777; padding-top: 20px;">この日の官報記事は見つかりませんでした。</p>`;
    } else {
        articles.forEach(item => {
            const pubDate = new Date(item.published).toLocaleDateString('ja-JP');
            
            htmlContent += `
                <li>
                    <p><strong><a href="${item.link}" target="_blank" rel="noopener noreferrer">${item.title}</a></strong></p>
                    <p><small>公開日: ${pubDate}</small></p>
                </li>
            `;
        });
        htmlContent += '</ul>';
    }
    
    container.innerHTML = htmlContent;
}


/**
 * カレンダーの日付セルがクリックされたときの処理
 * @param {Event} event
 */
function handleDateClick(event) {
    const cell = event.currentTarget;
    const dateString = cell.dataset.date; // YYYY-MM-DD
    
    if (!dateString || cell.classList.contains('inactive')) return; // 日付がない、または非アクティブなセルは無視

    // 現在選択されているセルを解除
    const prevSelectedCell = document.querySelector('.date-cell.selected');
    if (prevSelectedCell) {
        prevSelectedCell.classList.remove('selected');
    }

    // 新しい日付を設定し、リストを表示
    const parts = dateString.split('-').map(Number);
    // YYYY-MM-DD から Date オブジェクトを生成 (ローカルタイムゾーンで解釈)
    const newDate = new Date(parts[0], parts[1] - 1, parts[2]); 
    
    selectedDate = newDate;
    cell.classList.add('selected');

    displayArticlesByDate(selectedDate);
}


/**
 * カレンダーを生成し、データをマッピングする
 * @param {Date} targetMonth 
 */
function renderCalendar(targetMonth) {
    if (!calendarGrid || !monthDisplay) return;

    // 表示月を更新
    monthDisplay.textContent = `${targetMonth.getFullYear()}年 ${targetMonth.getMonth() + 1}月`;
    calendarGrid.innerHTML = ''; // カレンダーをクリア
    
    const year = targetMonth.getFullYear();
    const month = targetMonth.getMonth(); // 0-based

    // 曜日名の表示
    const dayNames = ['日', '月', '火', '水', '木', '金', '土'];
    dayNames.forEach(name => {
        const div = document.createElement('div');
        div.className = 'day-name';
        div.textContent = name;
        calendarGrid.appendChild(div);
    });

    // その月の1日
    const firstDayOfMonth = new Date(year, month, 1);
    // 1日の曜日 (0=日, 1=月, ...)
    const startingDayOfWeek = firstDayOfMonth.getDay();
    // 前月の最終日
    const lastDayOfPrevMonth = new Date(year, month, 0).getDate();
    // その月の最終日
    const lastDayOfMonth = new Date(year, month + 1, 0).getDate();
    
    const todayKey = formatDate(new Date());

    // 前月の余白セル
    for (let i = 0; i < startingDayOfWeek; i++) {
        // 余白セルの日付を計算
        const prevDate = lastDayOfPrevMonth - startingDayOfWeek + i + 1;
        const div = document.createElement('div');
        div.className = 'date-cell inactive';
        div.textContent = prevDate;
        calendarGrid.appendChild(div);
    }

    // その月の日付セル
    for (let day = 1; day <= lastDayOfMonth; day++) {
        const date = new Date(year, month, day);
        const dateKey = formatDate(date);
        const dayOfWeek = date.getDay(); // 0=日, 6=土
        
        const div = document.createElement('div');
        div.className = 'date-cell';
        div.textContent = day;
        div.dataset.date = dateKey;
        
        // 土日クラス
        if (dayOfWeek === 0) div.classList.add('sun');
        if (dayOfWeek === 6) div.classList.add('sat');

        // データ有無クラス
        if (articlesByDate[dateKey]) {
            div.classList.add('has-data');
        }
        
        // 今日クラス
        if (dateKey === todayKey) {
            div.classList.add('today');
        }

        // 選択日クラス
        if (selectedDate && dateKey === formatDate(selectedDate)) {
             div.classList.add('selected');
        }

        div.addEventListener('click', handleDateClick);
        calendarGrid.appendChild(div);
    }
}


// ----------------------------------------------------
// 初期化とデータ取得
// ----------------------------------------------------

// JSONデータを処理し、日付ごとに記事を整理する
function processKanpoData(data) {
    kanpoData = data.entries || [];
    articlesByDate = {}; // リセット

    kanpoData.forEach(item => {
        // 'published' タイムスタンプを YYYY-MM-DD 形式に正規化
        const date = new Date(item.published);
        // 時刻情報を無視し、日付だけをキーにする
        const dateKey = formatDate(date);
        
        if (!articlesByDate[dateKey]) {
            articlesByDate[dateKey] = [];
        }
        articlesByDate[dateKey].push(item);
    });

    // 最新の記事が存在する日を初期選択日とする
    if (kanpoData.length > 0) {
        const firstArticleDate = new Date(kanpoData[0].published);
        // 時刻情報をリセットして、日付だけを保持
        selectedDate = new Date(firstArticleDate.getFullYear(), firstArticleDate.getMonth(), firstArticleDate.getDate());
    } else {
        selectedDate = new Date(); // データがない場合は今日
    }
    
    // カレンダーをレンダリングし、初期記事を表示
    currentMonth = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1);
    renderCalendar(currentMonth);
    displayArticlesByDate(selectedDate);
}


// 月移動ボタンのイベントリスナーを設定
function setupEventListeners() {
    if (prevMonthButton) {
        prevMonthButton.addEventListener('click', () => {
            currentMonth.setMonth(currentMonth.getMonth() - 1);
            renderCalendar(currentMonth);
        });
    }

    if (nextMonthButton) {
        nextMonthButton.addEventListener('click', () => {
            currentMonth.setMonth(currentMonth.getMonth() + 1);
            renderCalendar(currentMonth);
        });
    }
}


document.addEventListener('DOMContentLoaded', function() {
    if (!container) {
        console.error('HTML要素 #rss-output が見つかりません。HTMLを確認してください。');
        return; 
    }
    
    // イベントリスナーを設定
    setupEventListeners();
    
    const jsonUrl = './data/kanpo_feed.json'; 

    fetch(jsonUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error('データの読み込みに失敗しました。ファイルパスまたはGitHub Actionsを確認してください。');
            }
            return response.json();
        })
        .then(processKanpoData)
        .catch(error => {
            container.innerHTML = `<p style="color: red; text-align: center;">データを取得できませんでした。コンソールで詳細を確認してください: ${error.message}</p>`;
            console.error(error);
        });
});
