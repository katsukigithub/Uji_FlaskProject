import sqlite3

# データベースに接続
conn = sqlite3.connect('data.db')
cursor = conn.cursor()

# テーブル一覧を取得
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

# テーブル名を表示（デバッグ用）
print("Tables in the database:", tables)

# テーブルを削除
for table in tables:
    table_name = table[0]
    print(f"Dropping table: {table_name}")
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

# 変更をコミット
conn.commit()
conn.close()