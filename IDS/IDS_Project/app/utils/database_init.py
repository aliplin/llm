"""
数据库初始化模块
负责数据库的创建、表结构初始化和基础数据插入
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash
from .database import get_db_connection

def init_db():
    """初始化数据库"""
    try:
        # 确保data目录存在
        os.makedirs('data', exist_ok=True)
        
        # 连接数据库
        conn = sqlite3.connect('data/packet_stats.db')
        c = conn.cursor()
        
        # 读取并执行SQL脚本
        with open('data/schema.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
        c.executescript(sql_script)
        
        # 检查并创建默认管理员用户
        c.execute("SELECT * FROM users WHERE username = 'admin'")
        if not c.fetchone():
            admin_password = generate_password_hash('admin123')
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                      ('admin', admin_password, 'admin'))
            print("✅ 默认管理员用户已创建 - 用户名: admin, 密码: admin123")
        
        # 检查events表是否有event_type列，如果没有则添加
        c.execute("PRAGMA table_info(events)")
        columns = [col[1] for col in c.fetchall()]
        if 'event_type' not in columns:
            c.execute("ALTER TABLE events ADD COLUMN event_type TEXT")
            print("✅ 已为events表添加event_type列")
        
        # 检查并创建packet_logs表
        c.execute("""
            CREATE TABLE IF NOT EXISTS packet_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                src_ip TEXT,
                dst_ip TEXT,
                src_port INTEGER,
                dst_port INTEGER,
                protocol TEXT,
                payload TEXT,
                timestamp TEXT,
                length INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 检查并创建settings表
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                value TEXT,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 插入默认设置
        default_settings = [
            ('max_events', '10000', '最大事件数量'),
            ('log_level', 'INFO', '日志级别'),
            ('monitor_interval', '30', '监控间隔（秒）'),
            ('high_severity_threshold', '5', '高严重性事件阈值'),
            ('timezone', 'Asia/Shanghai', '时区设置')
        ]
        
        for name, value, description in default_settings:
            c.execute("""
                INSERT OR IGNORE INTO settings (name, value, description)
                VALUES (?, ?, ?)
            """, (name, value, description))
        
        conn.commit()
        conn.close()
        
        print("✅ 数据库初始化完成")
        return True
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False

def check_database():
    """检查数据库状态"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # 检查表是否存在
        tables = ['users', 'events', 'rules', 'settings', 'packet_logs']
        missing_tables = []
        
        for table in tables:
            c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not c.fetchone():
                missing_tables.append(table)
        
        if missing_tables:
            print(f"⚠️  缺少表: {', '.join(missing_tables)}")
            return False
        
        # 检查用户数量
        c.execute("SELECT COUNT(*) FROM users")
        user_count = c.fetchone()[0]
        print(f"✅ 数据库检查完成 - 用户数量: {user_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        return False

def reset_database():
    """重置数据库（危险操作）"""
    try:
        # 删除数据库文件
        if os.path.exists('data/packet_stats.db'):
            os.remove('data/packet_stats.db')
            print("🗑️  已删除旧数据库文件")
        
        # 重新初始化
        return init_db()
        
    except Exception as e:
        print(f"❌ 重置数据库失败: {e}")
        return False

def backup_database():
    """备份数据库"""
    try:
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"data/packet_stats_backup_{timestamp}.db"
        
        shutil.copy2('data/packet_stats.db', backup_path)
        print(f"✅ 数据库已备份到: {backup_path}")
        return True
        
    except Exception as e:
        print(f"❌ 数据库备份失败: {e}")
        return False 