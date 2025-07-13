import os
from pathlib import Path
from datetime import timedelta

class Config:
    """应用配置类"""
    
    # Flask基础配置
    SECRET_KEY = 'your_secret_key'
    DEBUG = True
    
    # 获取项目根目录
    PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
    
    # 数据库配置
    DATABASE_PATH = PROJECT_ROOT / "data" / "packet_stats.db"
    
    # 网络配置
    NETWORK_INTERFACE = 'WLAN'
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 安全配置
    IP_BLOCK_DURATION = 3600  # IP封禁时长（秒）
    MAX_EVENTS = 10000  # 数据库中保留的最大事件数
    EVENT_CLEANUP_THRESHOLD = 0.2  # 清理阈值（20%）
    
    # 监控配置
    MONITOR_INTERVAL = 60  # 监控间隔（秒）
    HIGH_SEVERITY_THRESHOLD = 10  # 高严重性事件阈值
    
    # 时区配置
    TIMEZONE = 'Asia/Shanghai'
    
    # 分页配置
    DEFAULT_PAGE_SIZE = 20
    
    # 日志配置
    LOGS_DIR = PROJECT_ROOT / "logs" 