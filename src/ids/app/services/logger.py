"""
日志服务模块
负责系统日志记录和管理
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from ..utils.database import get_db_connection

class Logger:
    def __init__(self, name='ids_system'):
        self.name = name
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志配置"""
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent.parent.parent
        
        # 确保logs目录存在
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # 设置日志级别
        self.logger.setLevel(logging.INFO)
        
        # 清除现有的处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 创建文件处理器
        log_file = logs_dir / "ids_system.log"
        file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def info(self, message):
        """记录信息日志"""
        self.logger.info(message)
        self._save_to_db('INFO', message)
    
    def warning(self, message):
        """记录警告日志"""
        self.logger.warning(message)
        self._save_to_db('WARNING', message)
    
    def error(self, message):
        """记录错误日志"""
        self.logger.error(message)
        self._save_to_db('ERROR', message)
    
    def critical(self, message):
        """记录严重错误日志"""
        self.logger.critical(message)
        self._save_to_db('CRITICAL', message)
    
    def debug(self, message):
        """记录调试日志"""
        self.logger.debug(message)
        self._save_to_db('DEBUG', message)
    
    def _save_to_db(self, level, message):
        """保存日志到数据库"""
        try:
            conn = get_db_connection()
            c = conn.cursor()
            
            c.execute("""
                INSERT INTO system_logs (level, message, timestamp)
                VALUES (?, ?, ?)
            """, (level, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            # 如果数据库保存失败，只记录到文件
            self.logger.error(f"保存日志到数据库失败: {e}")
    
    def get_recent_logs(self, limit=100):
        """获取最近的日志"""
        try:
            conn = get_db_connection()
            c = conn.cursor()
            
            c.execute("""
                SELECT level, message, timestamp
                FROM system_logs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            logs = []
            for row in c.fetchall():
                logs.append({
                    'level': row[0],
                    'message': row[1],
                    'timestamp': row[2]
                })
            
            conn.close()
            return logs
            
        except Exception as e:
            self.logger.error(f"获取日志失败: {e}")
            return []
    
    def clear_logs(self, days=30):
        """清理旧日志"""
        try:
            conn = get_db_connection()
            c = conn.cursor()
            
            # 删除指定天数之前的日志
            c.execute("""
                DELETE FROM system_logs
                WHERE timestamp < datetime('now', '-{} days')
            """.format(days))
            
            deleted_count = c.rowcount
            conn.commit()
            conn.close()
            
            self.info(f"清理了 {deleted_count} 条旧日志")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"清理日志失败: {e}")
            return 0

# 创建全局日志实例
system_logger = Logger('ids_system')

def get_logger(name=None):
    """获取日志实例"""
    if name:
        return Logger(name)
    return system_logger
