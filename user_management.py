import sqlite3
from datetime import datetime
from sqlite3 import Error

DATABASE = 'data/user_data_test.db'

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
    """创建用户表，增加类型、描述和标签"""
    try:
        c = conn.cursor()
        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            wechat_id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            user_type TEXT NOT NULL,
            memory TEXT,
            tags TEXT
        )''')
    except Error as e:
        print(e)

def add_user(conn, wechat_id, email, user_type="regular", memory=[], tags=[]):
    """添加新用户
    user_type: 用户类型，如regular, star, admin等
    """
    memory_str = ','.join(memory)
    tags_str = ','.join(tags)
    try:
        cur = conn.cursor()
        # 首先检查wechat_id是否已存在
        cur.execute("SELECT * FROM users WHERE wechat_id = ?", (wechat_id,))
        if cur.fetchone() is not None:
            return f"Error: A user with wechat_id '{wechat_id}' already exists."
        
        # 如果wechat_id不存在，添加新用户
        sql = '''INSERT INTO users(wechat_id, email, user_type, memory, tags)
                VALUES(?,?,?,?,?)'''
        cur = conn.cursor()
        cur.execute(sql, (wechat_id, email, user_type, memory_str, tags_str))
        conn.commit()
        return cur.lastrowid
    except Error as e:
        print(e)
        return None
    

def get_user_email(conn, wechat_id):
    """ 根据微信ID获取用户的邮箱地址 """
    # cur = conn.cursor()
    # cur.execute("SELECT email FROM users WHERE wechat_id=?", (wechat_id,))
    # rows = cur.fetchall()
    # return rows[0][0] if rows else None
    return get_user_field(conn, wechat_id, 'email')

def get_user_field(conn, wechat_id, field):
    """获取某个用户的特定域信息"""
    try:
        cur = conn.cursor()
        # 参数化查询以防止SQL注入
        cur.execute(f"SELECT {field} FROM users WHERE wechat_id = ?", (wechat_id,))
        result = cur.fetchone()
        if result:
            value = result[0]
            if field in ['memory', 'tags']:
                value = value.split(',')
            return value
        else:
            return None
    except Error as e:
        print(e)
        return None


def update_user_field(conn, wechat_id, field, value):
    """通用的更新用户属性函数"""
    if field in ['memory', 'tags']:
        value = ','.join(value)
    sql = f'UPDATE users SET {field} = ? WHERE wechat_id = ?'
    cur = conn.cursor()
    cur.execute(sql, (value, wechat_id))
    conn.commit()

def update_user_email(conn, wechat_id, email):
    """ 更新用户的邮箱地址 """
    # sql = ''' UPDATE users
    #           SET email = ?
    #           WHERE wechat_id = ?'''
    # cur = conn.cursor()
    # cur.execute(sql, (email, wechat_id))
    # conn.commit()
    update_user_field(conn, wechat_id, 'email', email)

def clear_user_field(conn, wechat_id, field):
    """通用的清除用户属性函数"""
    if field in ['memory', 'tags']:
        update_value = "" 
    elif field == 'user_type':
        update_value = 'regular'
    update_user_field(conn, wechat_id, field, update_value)

def list_users_by_type(conn, user_type=None):
    """列出所有特定类型的用户"""
    cur = conn.cursor()
    if user_type:
        sql = 'SELECT wechat_id, email, memory, tags FROM users WHERE user_type = ?'
        param = (user_type,)
    else:
        sql = 'SELECT wechat_id, email, memory, tags FROM users'
        param = ()
    cur.execute(sql, param)
    rows = cur.fetchall()
    return [(wechat_id, email, mem.split(','), tags.split(',')) for wechat_id, email, mem, tags in rows]


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
    ## 创建用户记忆，具体格式是 [YYYY-MM-DD HH:MM 内容]
    memory_example = [f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}::内测用户"]
    print(add_user(conn, "李怡康 Yikang", "yikang_li@idgcapital.com", "owner", memory=memory_example, tags=["AI领域投资人", "AI技术研发", "商汤科技", "MSRA", "IDG资本", "Facebook Reality Labs"]))
    print(add_user(conn, "user123", "user123@example.com", "star", memory=memory_example, tags=["上级", "学术圈"]))
    # 获取用户邮箱
    print(get_user_email(conn, "user123"))
    # 获取用户记忆
    print(get_user_field(conn, "user123", "memory"))
    # 更新用户邮箱
    update_user_field(conn, "user123", "email", "updated@example.com")
    # 显示所有用户信息
    print(list_users_by_type(conn))
    # 删除用户
    delete_user(conn, "user123")

if __name__ == '__main__':
    main()

