"""
数据库连接模块
提供数据库连接和基础操作功能
"""

import sqlite3
import os
from pathlib import Path

def get_db_connection():
    """
    获取数据库连接
    
    Returns:
        sqlite3.Connection: 数据库连接对象
    """
    # 获取项目根目录
    project_root = Path(__file__).parent.parent.parent.parent.parent
    
    # 确保data目录存在
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    
    # 连接到数据库
    db_path = data_dir / "packet_stats.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
    
    return conn

def close_db_connection(conn):
    """
    关闭数据库连接
    
    Args:
        conn (sqlite3.Connection): 数据库连接对象
    """
    if conn:
        conn.close()

def execute_query(query, params=None):
    """
    执行查询语句
    
    Args:
        query (str): SQL查询语句
        params (tuple, optional): 查询参数
        
    Returns:
        list: 查询结果列表
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        results = cursor.fetchall()
        return results
    finally:
        close_db_connection(conn)

def execute_update(query, params=None):
    """
    执行更新语句
    
    Args:
        query (str): SQL更新语句
        params (tuple, optional): 更新参数
        
    Returns:
        int: 影响的行数
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        conn.commit()
        return cursor.rowcount
    finally:
        close_db_connection(conn)
