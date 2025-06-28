#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试配置文件加载功能
"""

import os
import sys
import yaml

def load_config(config_file='configMySQL.yml'):
    """加载YAML配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), config_file)
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"成功加载配置文件: {config_path}")
        return config
    except FileNotFoundError:
        print(f"配置文件未找到: {config_path}")
        return None
    except yaml.YAMLError as e:
        print(f"配置文件解析错误: {e}")
        return None
    except Exception as e:
        print(f"加载配置文件时发生错误: {e}")
        return None

def test_config_loading():
    """测试配置文件加载"""
    print("=" * 50)
    print("测试配置文件加载功能")
    print("=" * 50)
    
    # 加载配置
    config = load_config()
    
    if config:
        print("\n配置内容:")
        print("-" * 30)
        
        # 检查personality部分
        if 'personality' in config:
            personality = config['personality']
            print(f"模型: {personality.get('model', '未设置')}")
            print(f"温度: {personality.get('temperature', '未设置')}")
            print(f"最大令牌数: {personality.get('max_tokens', '未设置')}")
            print(f"提示词长度: {len(personality.get('prompt', ''))} 字符")
            print(f"重置提示词长度: {len(personality.get('reset_prompt', ''))} 字符")
            print(f"最终指令: {personality.get('final_instr', '未设置')}")
        else:
            print("未找到personality配置")
        
        # 检查API密钥
        if 'api_key' in config:
            api_key = config['api_key']
            if api_key:
                print(f"API密钥: {'*' * (len(api_key) - 4) + api_key[-4:]}")
            else:
                print("API密钥: 未设置（将使用环境变量）")
        else:
            print("API密钥: 未在配置文件中找到")
            
    else:
        print("配置文件加载失败")

if __name__ == "__main__":
    test_config_loading() 