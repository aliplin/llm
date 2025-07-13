#!/usr/bin/env python3
"""
IDS入侵检测系统启动
"""

import warnings
import logging
from app import create_app, socketio
# 抑制非关键警告
warnings.filterwarnings("ignore", category=DeprecationWarning, module="cryptography")
warnings.filterwarnings("ignore", message="Wireshark is installed, but cannot read manuf")

# 设置日志级别，减少scapy的警告输出
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)



def main():
    app = create_app()
    print("启动IDS入侵检测系统...")
    print("访问地址: http://localhost:5000")
    print("默认用户名: admin")
    print("默认密码: admin123")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()