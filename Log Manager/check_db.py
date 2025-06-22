#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库内容的脚本
"""

import sqlite3
import os

def check_database():
    """检查数据库内容"""
    db_path = os.path.join(os.path.dirname(__file__), 'shellm_sessions.db')
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("数据库中的表:")
    for table in tables:
        print(f"  - {table[0]}")
    
    print("\n各表的数据统计:")
    
    # 检查MySQL相关表
    try:
        cursor.execute("SELECT COUNT(*) FROM mysql_session")
        mysql_sessions = cursor.fetchone()[0]
        print(f"MySQL会话数: {mysql_sessions}")
        
        cursor.execute("SELECT COUNT(*) FROM mysql_command")
        mysql_commands = cursor.fetchone()[0]
        print(f"MySQL命令数: {mysql_commands}")
        
        if mysql_sessions > 0:
            cursor.execute("SELECT * FROM mysql_session LIMIT 3")
            sessions = cursor.fetchall()
            print("\nMySQL会话示例:")
            for session in sessions:
                print(f"  ID: {session[0]}, 用户: {session[1]}, 时间: {session[2]}, IP: {session[3]}")
        
        if mysql_commands > 0:
            cursor.execute("SELECT * FROM mysql_command LIMIT 3")
            commands = cursor.fetchall()
            print("\nMySQL命令示例:")
            for cmd in commands:
                print(f"  ID: {cmd[0]}, 会话ID: {cmd[1]}, 命令: {cmd[2][:50]}...")
                
    except sqlite3.OperationalError as e:
        print(f"MySQL表不存在: {e}")
    
    # 检查其他表
    try:
        cursor.execute("SELECT COUNT(*) FROM ssh_session")
        ssh_sessions = cursor.fetchone()[0]
        print(f"SSH会话数: {ssh_sessions}")
    except:
        print("SSH会话表不存在")
    
    try:
        cursor.execute("SELECT COUNT(*) FROM pop3_session")
        pop3_sessions = cursor.fetchone()[0]
        print(f"POP3会话数: {pop3_sessions}")
    except:
        print("POP3会话表不存在")
    
    try:
        cursor.execute("SELECT COUNT(*) FROM http_session")
        http_sessions = cursor.fetchone()[0]
        print(f"HTTP会话数: {http_sessions}")
    except:
        print("HTTP会话表不存在")
    
    conn.close()

if __name__ == "__main__":
    check_database() 