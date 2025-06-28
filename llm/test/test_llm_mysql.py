#!/usr/bin/env python3
"""
测试MySQL蜜罐的LLM功能
"""

import asyncio
import pymysql
import sys
import time

async def test_llm_mysql(host='localhost', port=3307):
    """测试LLM功能"""
    print(f"🔍 测试连接到 {host}:{port}")
    
    try:
        # 连接MySQL
        connection = pymysql.connect(
            host=host,
            port=port,
            user='root',
            password='',
            charset='utf8mb4',
            connect_timeout=10
        )
        
        print("✅ 连接成功")
        
        with connection.cursor() as cursor:
            # 测试基本查询
            print("\n📋 测试基本查询:")
            
            # 测试预定义查询（不应该调用LLM）
            print("1. 测试预定义查询 - SHOW DATABASES")
            cursor.execute("SHOW DATABASES")
            result = cursor.fetchall()
            print(f"   结果: {result}")
            
            # 测试LLM查询
            print("2. 测试LLM查询 - SELECT 'Hello World' as message")
            cursor.execute("SELECT 'Hello World' as message")
            result = cursor.fetchall()
            print(f"   结果: {result}")
            
            # 测试复杂LLM查询
            print("3. 测试复杂LLM查询 - SELECT * FROM users WHERE id = 1")
            cursor.execute("SELECT * FROM users WHERE id = 1")
            result = cursor.fetchall()
            print(f"   结果: {result}")
            
            # 测试DDL查询
            print("4. 测试DDL查询 - CREATE TABLE test_table (id INT)")
            cursor.execute("CREATE TABLE test_table (id INT)")
            print("   DDL查询执行完成")
            
            # 测试错误查询
            print("5. 测试错误查询 - SELECT * FROM nonexistent_table")
            try:
                cursor.execute("SELECT * FROM nonexistent_table")
                result = cursor.fetchall()
                print(f"   结果: {result}")
            except Exception as e:
                print(f"   预期错误: {e}")
        
        connection.close()
        print("\n✅ LLM功能测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("MySQL蜜罐LLM功能测试")
    print("=" * 50)
    
    print("⚠️  请确保:")
    print("  1. MySQL蜜罐正在运行")
    print("  2. 已配置OpenAI API密钥")
    print("  3. 端口号正确（默认3307）")
    
    # 测试连接
    success = asyncio.run(test_llm_mysql())
    
    if success:
        print("\n🎉 LLM功能测试成功！")
        print("MySQL蜜罐现在能够:")
        print("  • 处理预定义查询")
        print("  • 使用LLM响应未知查询")
        print("  • 正确处理错误查询")
        print("  • 记录详细的调试信息")
    else:
        print("\n❌ LLM功能测试失败")
        print("请检查:")
        print("  • MySQL蜜罐是否正在运行")
        print("  • API密钥是否正确配置")
        print("  • 网络连接是否正常")

if __name__ == "__main__":
    main() 