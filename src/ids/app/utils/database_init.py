"""
数据库初始化模块
负责数据库的创建、表结构初始化和基础数据插入
"""

import sqlite3
import os
from pathlib import Path
from werkzeug.security import generate_password_hash
from .database import get_db_connection

def init_db():
    """初始化数据库"""
    try:
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent.parent.parent
        
        # 确保data目录存在
        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)
        
        # 连接数据库
        db_path = data_dir / "packet_stats.db"
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        
        # 读取并执行SQL脚本
        schema_path = project_root / "src" / "ids" / "data" / "schema.sql"
        with open(schema_path, 'r', encoding='utf-8') as f:
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
        
        # 检查并创建蜜罐相关表
        create_honeypot_tables(c)
        
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

def create_honeypot_tables(c):
    """创建蜜罐相关的表"""
    # 攻击者会话表
    c.execute("""
        CREATE TABLE IF NOT EXISTS attacker_session (
            attacker_session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            src_ip VARCHAR(45)
        )
    """)
    
    # SSH会话表
    c.execute("""
        CREATE TABLE IF NOT EXISTS ssh_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(255),
            time_date DATETIME,
            src_ip VARCHAR(45),
            dst_ip VARCHAR(45),
            src_port INTEGER,
            dst_port INTEGER
        )
    """)
    
    # Shell会话表
    c.execute("""
        CREATE TABLE IF NOT EXISTS shellm_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ssh_session_id INTEGER,
            model VARCHAR(255),
            start_time DATETIME,
            end_time DATETIME,
            attacker_id INTEGER,
            FOREIGN KEY (ssh_session_id) REFERENCES ssh_session (id),
            FOREIGN KEY (attacker_id) REFERENCES attacker_session (attacker_session_id)
        )
    """)
    
    # 命令表
    c.execute("""
        CREATE TABLE IF NOT EXISTS commands (
            command_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shellm_session_id INTEGER,
            command TEXT,
            FOREIGN KEY (shellm_session_id) REFERENCES shellm_session (id)
        )
    """)
    
    # 答案表
    c.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            command_id INTEGER,
            answer TEXT,
            FOREIGN KEY (command_id) REFERENCES commands (command_id)
        )
    """)
    
    # HTTP会话表
    c.execute("""
        CREATE TABLE IF NOT EXISTS http_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_ip VARCHAR(45),
            start_time DATETIME,
            end_time DATETIME
        )
    """)
    
    # HTTP请求表
    c.execute("""
        CREATE TABLE IF NOT EXISTS http_request (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            http_session_id INTEGER,
            method VARCHAR(16),
            path VARCHAR(1024),
            headers TEXT,
            request_time DATETIME,
            response TEXT,
            FOREIGN KEY (http_session_id) REFERENCES http_session (id)
        )
    """)
    
    # POP3会话表
    c.execute("""
        CREATE TABLE IF NOT EXISTS pop3_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(255),
            time_date DATETIME,
            src_ip VARCHAR(45),
            dst_ip VARCHAR(45),
            src_port INTEGER,
            dst_port INTEGER
        )
    """)
    
    # POP3命令表
    c.execute("""
        CREATE TABLE IF NOT EXISTS pop3_command (
            command_id INTEGER PRIMARY KEY AUTOINCREMENT,
            pop3_session_id INTEGER,
            command TEXT,
            response TEXT,
            timestamp DATETIME,
            FOREIGN KEY (pop3_session_id) REFERENCES pop3_session (id)
        )
    """)
    
    # MySQL会话表
    c.execute("""
        CREATE TABLE IF NOT EXISTS mysql_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(255),
            time_date DATETIME,
            src_ip VARCHAR(45),
            dst_ip VARCHAR(45),
            src_port INTEGER,
            dst_port INTEGER,
            database_name VARCHAR(255)
        )
    """)
    
    # MySQL命令表
    c.execute("""
        CREATE TABLE IF NOT EXISTS mysql_command (
            command_id INTEGER PRIMARY KEY AUTOINCREMENT,
            mysql_session_id INTEGER,
            command TEXT,
            response TEXT,
            timestamp DATETIME,
            command_type VARCHAR(50),
            affected_rows INTEGER,
            FOREIGN KEY (mysql_session_id) REFERENCES mysql_session (id)
        )
    """)
    
    print("✅ 蜜罐相关表创建完成")

def check_database():
    """检查数据库状态"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # 检查表是否存在
        tables = [
            'users', 'events', 'rules', 'settings', 'packet_logs',
            'attacker_session', 'ssh_session', 'shellm_session', 
            'commands', 'answers', 'http_session', 'http_request',
            'pop3_session', 'pop3_command', 'mysql_session', 'mysql_command'
        ]
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
        
        # 检查各服务会话数量
        c.execute("SELECT COUNT(*) FROM ssh_session")
        ssh_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM http_session")
        http_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM mysql_session")
        mysql_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM pop3_session")
        pop3_count = c.fetchone()[0]
        
        print(f"✅ 数据库检查完成")
        print(f"  - 用户数量: {user_count}")
        print(f"  - SSH会话: {ssh_count}")
        print(f"  - HTTP会话: {http_count}")
        print(f"  - MySQL会话: {mysql_count}")
        print(f"  - POP3会话: {pop3_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        return False

def reset_database():
    """重置数据库（危险操作）"""
    try:
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent.parent.parent
        
        # 删除数据库文件
        db_path = project_root / "data" / "packet_stats.db"
        if db_path.exists():
            db_path.unlink()
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
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent.parent.parent
        backup_path = project_root / "data" / f"packet_stats_backup_{timestamp}.db"
        
        shutil.copy2('data/packet_stats.db', backup_path)
        print(f"✅ 数据库已备份到: {backup_path}")
        return True
        
    except Exception as e:
        print(f"❌ 数据库备份失败: {e}")
        return False 