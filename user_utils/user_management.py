import sqlite3
from datetime import datetime
from sqlite3 import Error
import logging

class UserManager:
    def __init__(self, db_file, 
                 owner_id=None, 
                 get_id_func=None):
        self.db_file = db_file
        # 实际管理者用户ID
        self.owner_id = owner_id
        # 用于user_name转换为实际的user_id
        self.get_id = get_id_func
        # 创建数据库
        # user_id: 用户ID, string
        # email: 用户邮箱, string
        # user_type: 用户类型, string
        # memory: 用户记忆, list
        # tags: 用户标签, list
        try:
            with self.connect() as conn:
                c = conn.cursor()
                c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                if not c.fetchone():  # 如果表不存在，则创建表
                    c.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        email TEXT NOT NULL,
                        user_type TEXT NOT NULL,
                        memory TEXT,
                        tags TEXT
                    )''')
                    logging.info("User table created successfully.")
                else:
                    logging.info("User table already exists.")
        except Error as e:
            logging.error(e)
    
    def connect(self):
        """ 创建一个数据库连接到SQLite数据库 """
        return sqlite3.connect(self.db_file)
    
    def __getitem__(self, user_id):
        return self.get_user(user_id)
    
    def __setitem__(self, user_id, value):
        return self.add_user(user_id, value['email'], value['user_type'], value['memory'], value['tags'])
    
    def __delitem__(self, user_id):
        return self.delete_user(user_id)
    
    def add_user(self, user_id, email, user_type="regular", memory=[], tags=[]):
        """添加新用户
        user_type: 用户类型，如regular, star, owner等
        """
        memory_str = ';'.join(memory)
        tags_str = ','.join(tags)
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                # 首先检查user_id是否已存在
                cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                if cur.fetchone() is not None:
                    return f"Error: A user with user_id '{user_id}' already exists."
                
                # 如果user_id不存在，添加新用户
                sql = '''INSERT INTO users(user_id, email, user_type, memory, tags)
                        VALUES(?,?,?,?,?)'''
                cur = conn.cursor()
                cur.execute(sql, (user_id, email, user_type, memory_str, tags_str))
                conn.commit()
                return cur.lastrowid
        except Error as e:
            logging.error(e)
            return None
        
    def delete_user(self, user_id):
        """ 删除用户 """
        sql = 'DELETE FROM users WHERE user_id=?'
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                # 首先检查用户是否存在
                cur.execute('SELECT * FROM users WHERE user_id=?', (user_id,))
                if cur.fetchone() is not None:
                    # 用户存在，执行删除操作
                    cur.execute('DELETE FROM users WHERE user_id=?', (user_id,))
                    conn.commit()
                    return f"User ({user_id}) deleted successfully."
                else:
                    # 用户不存在
                    return f"User ({user_id}) not found."
        except Error as e:
            logging.error(e)
            return None
        
    def get_user(self, user_id):
        """获取某个用户的所有信息"""
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                result = cur.fetchone()
                if result:
                    user_info = {
                        "user_id": result[0],
                        "email": result[1],
                        "user_type": result[2],
                        "memory": result[3].split(';') if result[3] else [],
                        "tags": result[4].split(',') if result[4] else []
                    }
                    return user_info
                else:
                    return None
        except Error as e:
            logging.error(e)
            return None
    
    def list_users_by_type(self, user_type=None):
        """列出所有特定类型的用户"""
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                if user_type:
                    sql = 'SELECT user_id, email, memory, tags FROM users WHERE user_type = ?'
                    param = (user_type,)
                else:
                    sql = 'SELECT user_id, email, memory, tags FROM users'
                    param = ()
                cur.execute(sql, param)
                rows = cur.fetchall()
                result = []
                for row in rows:
                    user_info = {
                        "user_id": row[0],
                        "email": row[1],
                        "memory": row[2].split(';') if row[2] else [],
                        "tags": row[3].split(',') if row[3] else []
                    }
                    result.append(user_info)
                return result
        except Error as e:
            print(e)
            return None


    def get_user_field(self, user_id, field):
        """获取某个用户的特定域信息"""
        try:
            with self.connect() as conn:
                cur = conn.cursor()
                # 参数化查询以防止SQL注入
                cur.execute(f"SELECT {field} FROM users WHERE user_id = ?", (user_id,))
                result = cur.fetchone()
                if result:
                    value = result[0]
                    if field == 'memory' and value is not None:
                        value = value.split(';')
                    elif field == "tags" and value is not None:
                        value = value.split(',')
                    return value
                else:
                    if field == 'memory' or field == 'tags':
                        return []
                    return None
        except Error as e:
            print(e)
            return None
        
    def set_user_field(self, user_id, field, value):
        """通用的更新用户属性函数"""
        # 如果用户不存在，则直接创建新的用户
        if self.get_user(user_id) is None:
            logging.info(f"User {user_id} does not exist. Creating a new user.")
            self.add_user(user_id, '', 'regular')

        if field == 'memory':
            value = ';'.join(value)
        elif field == "tags":
            value = ','.join(value)
        sql = f'UPDATE users SET {field} = ? WHERE user_id = ?'
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, (value, user_id))
            conn.commit()
        return f"user ({user_id}:{field}) updated successfully."
        

def main():
    # 创建数据库连接
    DATABASE = 'data/user_data_test.db'
    user_manager = UserManager(DATABASE)
    
    # 示例操作
    # 添加用户
    ## 创建用户记忆，具体格式是 [YYYY-MM-DD HH:MM 内容]
    memory_example = [f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}::内测用户"]
    tag_exmaple = ["AI领域投资人", "AI技术研发", "商汤科技", "MSRA", "IDG资本", "Facebook Reality Labs"]
    # 添加用户
    print(user_manager.add_user("user123", "user123@example.com", "star", memory=memory_example, tags=tag_exmaple))
    # 获取用户信息
    print(user_manager["user123"])
    # 获取用户记忆
    print(user_manager.get_user_field("user123", "memory"))
    # 更新用户邮箱
    print(user_manager.set_user_field("user123", "email", "updated@example.com"))
    # 显示所有用户信息
    print(user_manager.list_users_by_type())
    # 删除用户
    print(user_manager.delete_user("user123"))

if __name__ == '__main__':
    main()

