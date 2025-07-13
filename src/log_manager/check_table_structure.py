#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库表结构的脚本
"""

import sqlite3
import os
from pathlib import Path

def check_table_structure():
    """检查数据库表结构"""
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent
    
    db_path = project_root / "src" / "log_manager" / "shellm_sessions.db"
    
    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 要检查的表
    tables = ['mysql_session', 'mysql_command', 'http_session', 'http_request', 'ssh_session', 'pop3_session', 'pop3_command']
    
    for table in tables:
        print(f"\n=== {table} 表结构 ===")
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'} - {'PRIMARY KEY' if col[5] else ''}")
            
            # 显示示例数据
            cursor.execute(f"SELECT * FROM {table} LIMIT 1")
            sample = cursor.fetchone()
            if sample:
                print(f"\n示例数据:")
                for i, col in enumerate(columns):
                    print(f"  {col[1]}: {sample[i]}")
        except sqlite3.OperationalError as e:
            print(f"  表不存在: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_table_structure() 