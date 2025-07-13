#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目配置文件
统一管理所有模块的配置
"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 源代码目录
SRC_DIR = PROJECT_ROOT / "src"

# 配置文件目录
CONFIG_DIR = PROJECT_ROOT / "config"

# 文档目录
DOCS_DIR = PROJECT_ROOT / "docs"

# 日志目录
LOGS_DIR = PROJECT_ROOT / "logs"

# 数据库文件
DATABASE_DIR = PROJECT_ROOT / "data"

# 创建必要的目录
for directory in [LOGS_DIR, DATABASE_DIR]:
    directory.mkdir(exist_ok=True)

# 服务端口配置
PORTS = {
    "honeypot_ssh": 5656,
    "honeypot_http": 8080,
    "honeypot_mysql": 3306,
    "honeypot_pop3": 110,
    "ids_web": 5001,
    "log_manager": 5000
}

# API配置
API_CONFIG = {
    "kimi_api_key": os.getenv("KIMI_API_KEY", ""),
    "token_limit": 1000000,  # 每日Token限制
    "timeout": 30
}

# 数据库配置
DATABASE_CONFIG = {
    "sqlite": {
        "path": DATABASE_DIR / "ids.db"
    },
    "mysql": {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "",
        "database": "ids"
    }
}

# 日志配置
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": LOGS_DIR / "system.log"
}

# 安全配置
SECURITY_CONFIG = {
    "admin_username": "admin",
    "admin_password": "admin123",
    "session_timeout": 3600,  # 1小时
    "max_login_attempts": 5
}

# 蜜罐配置
HONEYPOT_CONFIG = {
    "ssh": {
        "enabled": True,
        "port": PORTS["honeypot_ssh"],
        "config_file": CONFIG_DIR / "configSSH.yml"
    },
    "http": {
        "enabled": True,
        "port": PORTS["honeypot_http"],
        "config_file": CONFIG_DIR / "configHTTP.yml"
    },
    "mysql": {
        "enabled": True,
        "port": PORTS["honeypot_mysql"],
        "config_file": CONFIG_DIR / "configMySQL.yml"
    },
    "pop3": {
        "enabled": True,
        "port": PORTS["honeypot_pop3"],
        "config_file": CONFIG_DIR / "configPOP3.yml"
    }
}

# IDS配置
IDS_CONFIG = {
    "enabled": True,
    "web_port": PORTS["ids_web"],
    "log_level": "INFO",
    "auto_ban": True,
    "ban_duration": 3600  # 1小时
}

# 日志管理器配置
LOG_MANAGER_CONFIG = {
    "enabled": True,
    "port": PORTS["log_manager"],
    "log_retention_days": 30,
    "max_log_size": 100 * 1024 * 1024  # 100MB
} 