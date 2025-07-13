#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite数据库初始化脚本
创建所有必要的表结构
"""

import sqlite3
import os
from pathlib import Path

def init_sqlite_database():
    """初始化SQLite数据库"""
    
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent
    
    # 数据库文件路径
    db_path = project_root / "src" / "log_manager" / "shellm_sessions.db"
    
    # 连接到SQLite数据库（如果不存在会自动创建）
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print(f"正在初始化SQLite数据库: {db_path}")
    
    # 创建attacker_session表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attacker_session (
            attacker_session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            src_ip VARCHAR(45) NOT NULL
        )
    ''')
    
    # 创建ssh_session表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ssh_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(255) NOT NULL,
            time_date DATETIME NOT NULL,
            src_ip VARCHAR(45) NOT NULL,
            dst_ip VARCHAR(45) NOT NULL,
            src_port INTEGER,
            dst_port INTEGER
        )
    ''')
    
    # 创建shellm_session表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shellm_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ssh_session_id INTEGER,
            model VARCHAR(255) NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            attacker_id INTEGER,
            FOREIGN KEY (ssh_session_id) REFERENCES ssh_session (id),
            FOREIGN KEY (attacker_id) REFERENCES attacker_session (attacker_session_id)
        )
    ''')
    
    # 创建commands表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commands (
            command_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shellm_session_id INTEGER,
            command TEXT NOT NULL,
            FOREIGN KEY (shellm_session_id) REFERENCES shellm_session (id)
        )
    ''')
    
    # 创建answers表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            command_id INTEGER,
            answer TEXT NOT NULL,
            FOREIGN KEY (command_id) REFERENCES commands (command_id)
        )
    ''')
    
    # 创建http_session表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS http_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_ip VARCHAR(45) NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME
        )
    ''')
    
    # 创建http_request表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS http_request (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            http_session_id INTEGER,
            method VARCHAR(16) NOT NULL,
            path VARCHAR(1024) NOT NULL,
            headers TEXT,
            request_time DATETIME NOT NULL,
            response TEXT NOT NULL,
            FOREIGN KEY (http_session_id) REFERENCES http_session (id)
        )
    ''')
    
    # 创建pop3_session表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pop3_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(255) NOT NULL,
            time_date DATETIME NOT NULL,
            src_ip VARCHAR(45) NOT NULL,
            dst_ip VARCHAR(45) NOT NULL,
            src_port INTEGER,
            dst_port INTEGER
        )
    ''')
    
    # 创建pop3_command表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pop3_command (
            command_id INTEGER PRIMARY KEY AUTOINCREMENT,
            pop3_session_id INTEGER,
            command TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            FOREIGN KEY (pop3_session_id) REFERENCES pop3_session (id)
        )
    ''')
    
    # 创建mysql_session表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mysql_session (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(255) NOT NULL,
            time_date DATETIME NOT NULL,
            src_ip VARCHAR(45) NOT NULL,
            dst_ip VARCHAR(45) NOT NULL,
            src_port INTEGER,
            dst_port INTEGER,
            database_name VARCHAR(255)
        )
    ''')
    
    # 创建mysql_command表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mysql_command (
            command_id INTEGER PRIMARY KEY AUTOINCREMENT,
            mysql_session_id INTEGER,
            command TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            command_type VARCHAR(50),
            affected_rows INTEGER,
            FOREIGN KEY (mysql_session_id) REFERENCES mysql_session (id)
        )
    ''')
    
    # 提交更改
    conn.commit()
    
    # 创建索引以提高查询性能
    print("正在创建索引...")
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ssh_session_time ON ssh_session(time_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shellm_session_ssh ON shellm_session(ssh_session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_shellm_session_attacker ON shellm_session(attacker_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_commands_session ON commands(shellm_session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_answers_command ON answers(command_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_http_request_session ON http_request(http_session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pop3_command_session ON pop3_command(pop3_session_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mysql_session_time ON mysql_session(time_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_mysql_command_session ON mysql_command(mysql_session_id)')
    
    conn.commit()
    
    # 关闭连接
    cursor.close()
    conn.close()
    
    print("SQLite数据库初始化完成！")
    print(f"数据库文件位置: {db_path}")
    
    return str(db_path)

if __name__ == "__main__":
    init_sqlite_database() 