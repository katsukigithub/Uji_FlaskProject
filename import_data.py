import sqlite3
import pandas as pd
import os

# データベース内の全テーブルを削除する関数
def delete_all_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for table in tables:
        table_name = table[0]
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        print(f"テーブル '{table_name}' が削除されました。")
    conn.commit()


#import_csv_to_db関数→指定されたCSVファイルをSQLiteデータベースにインポート
def import_csv_to_db(csv_file, table_name): #csv_file:インポートするcsvファイルのパス　table_name:データベース内でcsvのデータ保存するテーブルの名前
    df = pd.read_csv(csv_file)
    try:
        df.to_sql(table_name, conn, if_exists='replace', index=False) #データフレームをデータベースの指定テーブルに保存
        print(f"'{csv_file}' がテーブル '{table_name}' に正常にインポートされました。")
    except Exception as e:
        print(f"'{csv_file}'のインポート中にエラーが発生しました: {e}")
        
data_folder = './data'  #データフォルダのパスを指定。このフォルダ内のすべてのファイルをすべてデータベースにインポート。    
conn = sqlite3.connect('data.db')  #data.dbという名前のSQLiteデータベースに接続。接続オブジェクトconnを生成
# dataフォルダ内の全てのCSVをデータベースにインポート

for csv_file in os.listdir(data_folder):
    if csv_file.endswith('.csv'):
        table_name = csv_file.split('.')[0]  # テーブル名はファイル名に基づく
        import_csv_to_db(os.path.join(data_folder, csv_file), table_name)
        
        
conn.close()
print("データベースへのインポートが完了しました。")