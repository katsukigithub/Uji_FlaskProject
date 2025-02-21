from flask import Flask, render_template, jsonify, url_for, request, redirect
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import traceback

app = Flask(__name__)



# 初期化処理: 必要なテーブルを作成
def initialize_database():
    conn = sqlite3.connect('data.db')
    cursor = conn.cursor()
    # `table_titles` テーブルの存在確認と作成
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS table_titles (
        table_name TEXT PRIMARY KEY,
        title TEXT
    )
    """)
    conn.commit()
    conn.close()

initialize_database()  # アプリ起動時に実行


# データベース接続用関数
def get_db_connection():
    return sqlite3.connect('data.db')

# データベースのテーブルからタイトルを取得
def get_table_title(table_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM table_titles WHERE table_name = ?", (table_name,))
    result = cursor.fetchone()
    conn.close()
    if result:
        print(f"取得したタイトル: {result[0]}")  # デバッグ用
        return result[0]
    else:
        print(f"デフォルトタイトルを使用: {table_name}のデータ")  # デバッグ用
        return f"{table_name}のデータ"

# データベースのテーブルのタイトルを更新
def update_table_title(table_name, new_title):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO table_titles (table_name, title)
        VALUES (?, ?)
        ON CONFLICT(table_name) DO UPDATE SET title = excluded.title
    """, (table_name, new_title))
    conn.commit()
    
    # デバッグ用: 保存内容を出力
    cursor.execute("SELECT * FROM table_titles WHERE table_name = ?", (table_name,))
    updated_title = cursor.fetchone()
    print(f"更新されたタイトル: {updated_title}")

    conn.close()

# テーブル一覧を取得する関数
def get_table_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return  sorted([table for table in tables if table != 'table_titles'])


# データベースからグラフデータを取得して生成する関数
def create_plot(table_name, chart_type, start_date=None, end_date=None):
    # データベース接続
    conn = get_db_connection()
    #指定されたtable_nameの全データを取得
    query = f"SELECT * FROM {table_name}"
    
    # データを取得し結果をpandasのデータフレームに読み込む
    df = pd.read_sql_query(query, conn)
    conn.close()

    # 日付列をdatetimeに変換
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # フィルタリング処理
    if start_date:
        df = df[df['Date'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['Date'] <= pd.to_datetime(end_date)]
        
    # 数値列だけを選択し、新しいいデータフレームdf_numericに格納
    df_numeric = df.select_dtypes(include=['float64', 'int64'])
    
    # 統計情報を計算
    statistics = {
        col: {
            "mean": df_numeric[col].mean(),
            "median": df_numeric[col].median(),
            "max": df_numeric[col].max(),
            "min": df_numeric[col].min(), 
            "std_dev": df_numeric[col].std(),  # 標準偏差
            "variance": df_numeric[col].var()  # 分散
            
        }
        for col in df_numeric.columns
    }
    
    #  statistics の値を JSON シリアライズ可能なデータ型に変換
    for col in statistics:
        for key in statistics[col]:
            if pd.notna(statistics[col][key]):
                statistics[col][key] = float(statistics[col][key])
            else:
                statistics[col][key] = None  # NaN の場合は None を設定
                
    # グラフを生成
    fig = go.Figure()
    
    #グラフの種類を判別する
    if chart_type == 'line':   

        # 各項目に対して異なる線を追加
        for col in df_numeric.columns:
            fig.add_trace(go.Scatter(x=df['Date'], y=df_numeric[col], mode='lines', name=col))
        
        #y軸の最大値を計算（数値列のみ使用）
        y_max = dict(range=[0, df_numeric.max()])     

        # レイアウト設定
        fig.update_layout(
            #title=f'{table_name}のデータ',
            width=1900,
            height=600,
            xaxis_title="Date",
            yaxis_title="Value",
            yaxis=dict(range=[0, df_numeric.max().max()]),  # y軸の最大値を設定　最小値を0に設定
            legend=dict(   
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05
            ),
            margin=dict(t=100, r=200),
            hovermode="x unified",
            xaxis=dict(
                hoverformat="%Y-%m-%d" )     
        )
            
    elif chart_type == 'bar':
        # 棒グラフ
        for col in df_numeric.columns:
            fig.add_trace(go.Bar(x=df['Date'], y=df_numeric[col], name=col))
            
    elif chart_type == 'pie':
        # 円グラフ（最初の数値列を使用）
        if len(df_numeric.columns) > 0:
            fig = go.Figure(data=[go.Pie(labels=df['Date'], values=df_numeric.iloc[:, 0])])
            
    elif chart_type == 'scatter':
        # 散布図
        for col in df_numeric.columns:
            fig.add_trace(go.Scatter(x=df['Date'], y=df_numeric[col], mode='markers', name=col))


    # グラフをJSON形式に変換。JAvaScriptを使ってHTMLにグラフを埋め込む
    graph_json = fig.to_json()
    #print("Generated graph JSON:", graph_json)  # デバッグ用
    return graph_json, statistics  #JSON形式のグラフデータを返します。

#/ホームページへのアクセスを処理する関数。index.htmlをレンダリングして返す
@app.route('/')
def index():
    tables = get_table_list()
    return render_template('index.html', tables=tables)


# 各ボタンのルートを定義し、それぞれ異なるテーブルのグラフを表示
#/graph/<table_name>というURLパターンに基づき、任意のtable_nameを指定してグラフページを表示
#create_plot(table_name)を呼び出して指定のテーブルのグラフデータを取得し、JSON形式でgraph_jsonに格納
#graph.htmlテンプレートをレンダリングし、table_nameとgraph_dataを渡してグラフを表示
@app.route('/graph/<table_name>', methods=['GET'])
def graph(table_name):
    #全テーブルのリストを取得
    tables = get_table_list()

     #指定されたテーブル名が存在しない場合は404エラー
    if table_name not in tables:
        return "Table not found", 404
    
    # グラフタイプをGETパラメータから取得
    chart_type = request.args.get('chart_type', 'line')  # デフォルトは 'line'
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    
    # 現在のテーブルのインデックスを取得
    current_index = tables.index(table_name)
    
    # Ajaxリクエストの場合はJSONデータのみを返す
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'graph_html': graph_json,
            'statistics': statistics
        })
    
    
    # 前後のグラフをスキップしつつループする
    prev_index = (current_index - 1) % len(tables)
    next_index = (current_index + 1) % len(tables)
    prev_url = url_for('graph', table_name=tables[prev_index], chart_type=chart_type, start_date=start_date, end_date=end_date)
    next_url = url_for('graph', table_name=tables[next_index], chart_type=chart_type, start_date=start_date, end_date=end_date)

    
    # 現在のテーブルタイトルを取得
    table_title = get_table_title(table_name)
    print(f"テンプレートに渡すタイトル: {table_title}")  # デバッグ用

    
    graph_json, statistics = create_plot(table_name, chart_type, start_date, end_date)
    
    return render_template(
        'graph.html', 
        table_name=table_name, 
        graph_data=graph_json,
        prev_url=prev_url,
        next_url=next_url,
        chart_type=chart_type,
        table_title=table_title,
        start_date=start_date,
        end_date=end_date,
        statistics=statistics
        
    )
    

@app.route('/update_title', methods=['POST'])
def update_title():
    data = request.get_json()
    table_name = data.get('table_name')
    new_title = data.get('new_title')
    if not table_name or not new_title:
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400

    update_table_title(table_name, new_title)
    return jsonify({'status': 'success', 'message': 'Title updated successfully'})

@app.route('/statistics/<table_name>', methods=['GET'])
def get_statistics(table_name):
    column = request.args.get('column')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not column:
        return jsonify({'status': 'error', 'message': 'No column specified'}), 400

    try:
        conn = get_db_connection()
        # デバッグ用: クエリ前に引数を出力
        print(f"Fetching statistics for table: {table_name}, column: {column}, start_date: {start_date}, end_date: {end_date}")

        # 指定されたテーブルから全データを取得するクエリ(Data列と指定列)
        query = "SELECT Date, [{}] FROM {}".format(column, table_name)
        print(f"Executing query: {query}")  # デバッグ用
        df = pd.read_sql_query(query, conn)
        conn.close()

        # Data列をdatetime型に変換
        df['Date'] = pd.to_datetime(df['Date'], format='%Y/%m/%d', errors='coerce')

        #フィルタリング前のデバッグ
        print(f"Original data range: {df['Date'].min()} to {df['Date'].max()}")

        # 日付範囲のフィルタリング
        if start_date:
            try:
                start_date = pd.to_datetime(f"{start_date}-01", format='%Y-%m-%d')
                df = df[df['Date'] >= start_date]
            except Exception as e:
                return jsonify({'status': 'error', 'message': f'Invalid start_date format: {start_date}'}), 400

        if end_date:
            try:
                end_year, end_month = map(int, end_date.split('-'))
                last_day_of_month = pd.Timestamp(end_year, end_month, 1) + pd.offsets.MonthEnd(0)
                df = df[df['Date'] <= last_day_of_month]
            except Exception as e:
                return jsonify({'status': 'error', 'message': f'Invalid end_date format: {end_date}'}), 400

        # 指定列にNaNがある行を削除
        if column not in df.columns:
            return jsonify({'status': 'error', 'message': f'Invalid column specified: {column}'}), 400
        df = df.dropna(subset=[column])

        # データが空の場合の処理
        if df.empty:
            return jsonify({'status': 'error', 'message': 'No data available for the specified criteria.'}), 404


        # 統計計算
        stats = {
            "mean": float(df[column].mean()) if not df[column].isna().all() else None,
            "median": float(df[column].median()) if not df[column].isna().all() else None,
            "max": float(df[column].max()) if not df[column].isna().all() else None,
            "min": float(df[column].min()) if not df[column].isna().all() else None,
            "std": float(df[column].std()) if not df[column].isna().all() else None,
            "variance": float(df[column].var()) if not df[column].isna().all() else None,
            "filtered_count": len(df),  # フィルタリング後のデータ数
            "date_range": {
                "start": df['Date'].min().strftime('%Y-%m-%d') if not df['Date'].isna().all() else None,
                "end": df['Date'].max().strftime('%Y-%m-%d') if not df['Date'].isna().all() else None
            }
        }
        
        # デバッグ: 計算された統計の出力
        print(f"Calculated statistics: {stats}")


        return jsonify({'status': 'success', 'statistics': stats})

    except Exception as e:
        # エラー内容を出力して返す
        print(f"Error occurred: {e}")  # デバッグ用
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@app.route('/table/<table_name>', methods=['GET'])
def view_table(table_name):
    # 全テーブルのリストを取得
    tables = get_table_list()

    if table_name not in tables:  # テーブル名の存在確認
        return "Table not found", 404

    # クエリパラメータの取得
    selected_columns = request.args.getlist('columns')  # 表示対象の列
    filters = request.args.getlist('filters')  # フィルタ条件 (例: column:operator:value)
    sort_column = request.args.get('sort_column')  # ソート対象の列
    sort_order = request.args.get('sort_order', 'asc')  # ソート順

    try:
        conn = get_db_connection()

        # カラムリスト取得
        column_query = f"PRAGMA table_info({table_name})"
        columns = pd.read_sql_query(column_query, conn)['name'].tolist()

        # 選択されたカラムの処理
        selected_columns = selected_columns.split(',') if selected_columns else None

        # カラム検証
        if selected_columns and any(col not in columns for col in selected_columns):
            return jsonify({'status': 'error', 'message': 'Invalid selected columns'}), 400
        if sort_column and sort_column not in columns:
            return jsonify({'status': 'error', 'message': 'Invalid sort column specified'}), 400

        # クエリ作成
        query = f"SELECT * FROM {table_name}"
        conditions = []
        params = []

        # フィルタ条件追加
        for filter_condition in filters:
            try:
                column, operator, value = filter_condition.split(':')
                if column not in columns:
                    return jsonify({'status': 'error', 'message': f'Invalid column: {column}'}), 400

                if operator == 'eq':  # 完全一致
                    conditions.append(f"{column} = ?")
                    params.append(value)
                elif operator == 'like':  # 部分一致
                    conditions.append(f"{column} LIKE ?")
                    params.append(f"%{value}%")
                elif operator == 'gt':  # 大なり
                    conditions.append(f"{column} > ?")
                    params.append(value)
                elif operator == 'lt':  # 小なり
                    conditions.append(f"{column} < ?")
                    params.append(value)
                elif operator == 'ge':  # 以上
                    conditions.append(f"{column} >= ?")
                    params.append(value)
                elif operator == 'le':  # 以下
                    conditions.append(f"{column} <= ?")
                    params.append(value)
                else:
                    return jsonify({'status': 'error', 'message': f'Invalid operator: {operator}'}), 400
            except ValueError:
                return jsonify({'status': 'error', 'message': f'Invalid filter format: {filter_condition}'}), 400

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # ソート追加
        if sort_column:
            query += f" ORDER BY {sort_column} {sort_order}"

        # データ取得
        data = pd.read_sql_query(query, conn, params=params)

        # 必要な列のみ選択
        if selected_columns:
            data = data[selected_columns]
            
        # 行データのリスト化
        row_data = data.values.tolist()

        # HTMLレンダリング
        table_html = data.to_html(index=False, classes="table table-bordered table-hover")

        return render_template(
            'table.html',
            table_name=table_name,
            table_html=table_html,
            column_names=columns,  
            row_count=len(data),
            selected_columns=selected_columns,
            data=row_data
        )

    except Exception as e:
        print(f"Error fetching table data: {e}")
        import traceback
        traceback.print_exc()  # エラー詳細を表示
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@app.route('/get_row_data', methods=['POST'])
def get_row_data():
    data = request.get_json()
    table_name = data.get('table_name')
    row_id = data.get('row_id')
    if not table_name or not row_id:
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400
    
    try:
        conn = get_db_connection()
        query = f"SELECT * FROM {table_name} WHERE id = ?"
        row_data = pd.read_sql_query(query, conn, params=[row_id])
        conn.close()
        
        if row_data.empty: 
            return jsonify({'status': 'error', 'message': 'Row not found'}), 404
        return jsonify({'status': 'success', 'row_data': row_data.to_dict(orient='records')[0]})
        
    except Exception as e:  
        print(f"Error fetching row data: {e}")  
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@app.route('/update_row_data', methods=['POST'])
def update_row_data():
    data = request.get_json()
    table_name = data.get('table_name')
    row_id = data.get('row_id')
    updated_data = data.get('updated_data')
    if not table_name or not row_id or not updated_data:
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        columns = ', '.join([f"{col} = ?" for col in updated_data.keys()])
        values = list(updated_data.values()) + [row_id]
        query = f"UPDATE {table_name} SET {columns} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'message': 'Row updated successfully'})
    
    except Exception as e:
            print(f"Error updating row data: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
        
@app.route('/api/table_data', methods=['GET'])
def api_table_data():
    table_name = request.args.get('table_name')
    column_filter = request.args.get('column')
    filter_value = request.args.get('value')
    page = int(request.args.get('page', 1))
    page_size = 20
    offset = (page - 1) * page_size

    try:
        conn = get_db_connection()

        # カラムリスト取得
        column_query = f"PRAGMA table_info({table_name})"
        columns = pd.read_sql_query(column_query, conn)['name'].tolist()

        if column_filter and column_filter not in columns:
            return jsonify({'status': 'error', 'message': 'Invalid column specified'}), 400

        # クエリ作成
        query = f"SELECT * FROM {table_name}"
        conditions = []
        params = []

        if column_filter and filter_value:
            conditions.append(f"{column_filter} LIKE ?")
            params.append(f"%{filter_value}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " LIMIT ? OFFSET ?"
        params.extend([page_size, offset])

        # データ取得
        data = pd.read_sql_query(query, conn, params=params)
        conn.close()

        total_rows_query = f"SELECT COUNT(*) as count FROM {table_name}"
        if conditions:
            total_rows_query += " WHERE " + " AND ".join(conditions)
        total_rows = pd.read_sql_query(total_rows_query, conn, params=params[:len(conditions)]).iloc[0]['count']

        return jsonify({
            'status': 'success',
            'data': data.to_dict(orient='records'),
            'page': page,
            'total_pages': (total_rows + page_size - 1) // page_size
        })

    except Exception as e:
        print(f"Error fetching table data: {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


# 日付フィルタリングAPI

@app.route('/filter_data/<table_name>', methods=['GET'])
def filter_data(table_name):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    chart_type = request.args.get('chart_type', 'line')

    try:
        graph_json, statistics = create_plot(table_name, chart_type, start_date, end_date)
        return jsonify({'status': 'success', 'graph_data': json.loads(graph_json), 'statistics': statistics})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

#アプリケーション起動
if __name__ == '__main__':
    app.run(debug=True)
    
    