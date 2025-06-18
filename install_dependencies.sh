#!/bin/bash

echo "========================================"
echo "LLM蜜罐项目依赖库一键安装脚本"
echo "========================================"
echo

echo "正在检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到Python3环境，请先安装Python 3.8+"
    exit 1
fi

python3 --version

echo
echo "正在升级pip..."
python3 -m pip install --upgrade pip

echo
echo "正在安装项目依赖库..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo
    echo "========================================"
    echo "依赖库安装完成！"
    echo "========================================"
    echo
    echo "已安装的库："
    echo "- openai: OpenAI API客户端"
    echo "- tiktoken: Token计数工具"
    echo "- python-dotenv: 环境变量管理"
    echo "- PyYAML: YAML配置文件解析"
    echo "- mysql-connector-python: MySQL数据库连接"
    echo "- Flask: Web框架"
    echo "- Flask-CORS: CORS支持"
    echo "- paramiko: SSH服务器"
    echo
    echo "现在可以运行项目了！"
else
    echo
    echo "错误：依赖库安装失败，请检查网络连接或手动安装"
    exit 1
fi 