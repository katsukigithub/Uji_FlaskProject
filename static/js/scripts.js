// グラフをロードする関数 (index.htmlで使用)
function loadGraph(tableName) {
    fetch(`/graph/${tableName}`)   
    .then(response => response.json()) //サーバーからのJSONレスポンス
    .then(data => {
        const graphDiv = document.getElementById('graph-container');
        Plotly.newPlot(graphDiv, JSON.parse(data).data, JSON.parse(data).layout);
        

        


    })
    .catch(error => console.error('Error loading graph:', error));
}


//fetch関数で指定したURLにHTTPリクエストを送信　Flaskアプリのルート/graph/<table_name>にリクエスト送信
//Flaskアプリはリクエストを受け取ると、指定されたテーブルからデータを取得し、JSON形式で返す。
//fetchの結果をthenで処理。response.json()は、レスポンスデータをJSON形式に変換して返す関数。これにより、データをJavaScriptオブジェクトとして利用できる。
//次のthenで、JSONデータが変数dataに渡される。このdataには、Flaskアプリが返したグラフのデータとレイアウト情報が含まれる。
//graphDivという変数を作成し、HTML内のid="graph"の要素を取得する。ここにグラフを表示。
//Plotly.newPlot関数を使って、graphDiv（id="graph"の要素）に新しいグラフを描画。
//dataの内容をJSON.parse(data)で解析し、Plotlyの描画に必要なデータ（data）とレイアウト設定（layout）を取り出してグラフを生成。
//エラーハンドリング用のcatch。データの取得やグラフの生成中にエラーが発生した場合、console.errorでエラーメッセージを表示。