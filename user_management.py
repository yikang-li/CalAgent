import sqlite3
from sqlite3 import Error

DATABASE = 'data/user_data.db'

def create_connection(db_file):
    """ 创建一个数据库连接到SQLite数据库 """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        if conn is not None:
            create_table(conn)
        return conn
    except Error as e:
        print(e)
    return conn

def create_table(conn):
    """ 创建用户表 """
    try:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (wechat_id TEXT PRIMARY KEY, email TEXT NOT NULL)''')
    except Error as e:
        print(e)

def add_user(conn, wechat_id, email):
    """ 添加新用户 """
    sql = ''' INSERT INTO users(wechat_id,email)
              VALUES(?,?) '''
    cur = conn.cursor()
    cur.execute(sql, (wechat_id, email))
    conn.commit()
    return cur.lastrowid

def get_user_email(conn, wechat_id):
    """ 根据微信ID获取用户的邮箱地址 """
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE wechat_id=?", (wechat_id,))
    rows = cur.fetchall()
    return rows[0][0] if rows else None

def update_user_email(conn, wechat_id, email):
    """ 更新用户的邮箱地址 """
    sql = ''' UPDATE users
              SET email = ?
              WHERE wechat_id = ?'''
    cur = conn.cursor()
    cur.execute(sql, (email, wechat_id))
    conn.commit()

def delete_user(conn, wechat_id):
    """ 删除用户 """
    sql = 'DELETE FROM users WHERE wechat_id=?'
    cur = conn.cursor()
    cur.execute(sql, (wechat_id,))
    conn.commit()

def main():
    # 创建数据库连接
    conn = create_connection(DATABASE)
    
    # 创建表
    if conn is not None:
        create_table(conn)
    else:
        print("Error! cannot create the database connection.")
    
    # 示例操作
    # 添加用户
    add_user(conn, "user123", "user123@example.com")
    # 获取用户邮箱
    print(get_user_email(conn, "user123"))
    # 更新用户邮箱
    update_user_email(conn, "user123", "newemail@example.com")
    # 删除用户
    delete_user(conn, "user123")

if __name__ == '__main__':
    main()
