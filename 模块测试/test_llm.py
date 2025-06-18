#!/usr/bin/env python3
"""
LLM API测试脚本
验证Moonshot AI API调用是否正常
"""

import os
from dotenv import dotenv_values
from openai import OpenAI

def test_llm_api():
    """测试LLM API调用"""
    print("=== LLM API测试 ===")
    
    try:
        # 检查.env文件
        env_file = ".env"
        if not os.path.exists(env_file):
            print(f"✗ .env文件不存在: {env_file}")
            return False
        
        # 读取环境变量
        env = dotenv_values(env_file)
        if "KIMI_API_KEY" not in env:
            print("✗ .env文件中没有KIMI_API_KEY")
            return False
        
        api_key = env["KIMI_API_KEY"]
        print(f"✓ 找到API密钥: {api_key[:10]}...")
        
        # 创建OpenAI客户端
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1",
            timeout=60
        )
        print("✓ OpenAI客户端创建成功")
        
        # 测试API调用
        print("正在调用LLM API...")
        response = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=[
                {"role": "system", "content": "你是一个Linux终端，请模拟ls命令的输出。"},
                {"role": "user", "content": "ls"}
            ],
            temperature=0.3,
            max_tokens=1024
        )
        
        ai_response = response.choices[0].message.content
        print(f"✓ LLM响应成功: {repr(ai_response)}")
        print(f"响应内容:\n{ai_response}")
        
        return True
        
    except Exception as e:
        print(f"✗ LLM API调用失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ssh_config():
    """测试SSH配置文件"""
    print("\n=== SSH配置测试 ===")
    
    try:
        import yaml
        
        # 读取SSH配置文件
        config_file = "configSSH.yml"
        if not os.path.exists(config_file):
            print(f"✗ 配置文件不存在: {config_file}")
            return False
        
        with open(config_file, 'r', encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        personality = config.get('personality', {})
        
        print(f"✓ 配置文件读取成功")
        print(f"模型: {personality.get('model', 'N/A')}")
        print(f"温度: {personality.get('temperature', 'N/A')}")
        print(f"最大token: {personality.get('max_tokens', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"✗ 配置文件读取失败: {e}")
        return False

if __name__ == "__main__":
    print("开始LLM API测试...")
    
    # 测试配置文件
    config_ok = test_ssh_config()
    
    # 测试LLM API
    api_ok = test_llm_api()
    
    print(f"\n=== 测试结果 ===")
    print(f"配置文件: {'✓' if config_ok else '✗'}")
    print(f"LLM API: {'✓' if api_ok else '✗'}")
    
    if config_ok and api_ok:
        print("✓ 所有测试通过，SSH蜜罐应该能正常工作")
    else:
        print("✗ 存在问题，请检查配置") 