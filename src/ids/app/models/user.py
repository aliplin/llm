from flask_login import UserMixin
from werkzeug.security import check_password_hash
from ..utils.database import get_db_connection

class User(UserMixin):
    """用户模型类"""
    
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def get_by_id(user_id):
        """根据ID获取用户"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user_data = c.fetchone()
        conn.close()
        
        if user_data:
            return User(user_data[0], user_data[1], user_data[2])
        return None
    
    @staticmethod
    def get_by_username(username):
        """根据用户名获取用户"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_data = c.fetchone()
        conn.close()
        
        if user_data:
            return User(user_data[0], user_data[1], user_data[2])
        return None
