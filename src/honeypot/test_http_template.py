#!/usr/bin/env python3
"""
HTTP模板系统性能测试脚本
测试模板化HTTP响应的速度、会话管理和内容一致性
"""

import time
import requests
import json
import hashlib
from datetime import datetime

def test_http_response_speed():
    """测试HTTP响应速度"""
    base_url = "http://127.0.0.1:8080"
    
    # 测试路径列表
    test_paths = [
        "/",
        "/documentation", 
        "/styles.css",
        "/about",
        "/contact"
    ]
    
    print("开始HTTP模板系统性能测试...")
    print("=" * 50)
    
    total_time = 0
    successful_requests = 0
    
    for i, path in enumerate(test_paths, 1):
        print(f"\n测试 {i}: {path}")
        
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}{path}", timeout=10)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            total_time += response_time
            successful_requests += 1
            
            print(f"  状态码: {response.status_code}")
            print(f"  响应时间: {response_time:.2f}ms")
            print(f"  内容长度: {len(response.content)} bytes")
            
            # 检查响应内容类型
            if path == "/styles.css":
                print(f"  内容类型: CSS")
            else:
                print(f"  内容类型: HTML")
                
        except requests.exceptions.RequestException as e:
            print(f"  错误: {e}")
        except Exception as e:
            print(f"  未知错误: {e}")
    
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print(f"成功请求数: {successful_requests}/{len(test_paths)}")
    if successful_requests > 0:
        avg_time = total_time / successful_requests
        print(f"平均响应时间: {avg_time:.2f}ms")
        print(f"总响应时间: {total_time:.2f}ms")
        
        # 性能评估
        if avg_time < 100:
            print("性能评级: 优秀 (响应时间 < 100ms)")
        elif avg_time < 500:
            print("性能评级: 良好 (响应时间 < 500ms)")
        elif avg_time < 1000:
            print("性能评级: 一般 (响应时间 < 1000ms)")
        else:
            print("性能评级: 需要优化 (响应时间 > 1000ms)")

def test_content_consistency():
    """测试内容一致性 - 同一页面多次访问应该返回相同内容"""
    print("\n开始内容一致性测试...")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8080"
    test_paths = ["/", "/documentation", "/about"]
    
    for path in test_paths:
        print(f"\n测试路径: {path}")
        
        # 第一次访问
        try:
            response1 = requests.get(f"{base_url}{path}", timeout=10)
            content1 = response1.text
            hash1 = hashlib.md5(content1.encode()).hexdigest()
            print(f"  第一次访问 - 内容长度: {len(content1)} bytes, MD5: {hash1[:8]}...")
        except Exception as e:
            print(f"  第一次访问失败: {e}")
            continue
        
        # 第二次访问
        try:
            response2 = requests.get(f"{base_url}{path}", timeout=10)
            content2 = response2.text
            hash2 = hashlib.md5(content2.encode()).hexdigest()
            print(f"  第二次访问 - 内容长度: {len(content2)} bytes, MD5: {hash2[:8]}...")
        except Exception as e:
            print(f"  第二次访问失败: {e}")
            continue
        
        # 比较内容
        if hash1 == hash2:
            print(f"  ✓ 内容一致性: 通过 (两次访问内容完全相同)")
        else:
            print(f"  ✗ 内容一致性: 失败 (两次访问内容不同)")
            # 显示差异
            if len(content1) != len(content2):
                print(f"    内容长度不同: {len(content1)} vs {len(content2)}")
            else:
                # 找到第一个不同的字符
                for i, (c1, c2) in enumerate(zip(content1, content2)):
                    if c1 != c2:
                        print(f"    第一个差异位置: {i}, '{c1}' vs '{c2}'")
                        break

def test_session_management():
    """测试会话管理 - 验证网站信息的一致性"""
    print("\n开始会话管理测试...")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8080"
    
    # 获取首页内容
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        content = response.text
        
        # 提取网站信息
        company_name = None
        model_name = None
        
        # 从标题中提取信息
        if '<title>' in content and '</title>' in content:
            title_start = content.find('<title>') + 7
            title_end = content.find('</title>')
            title = content[title_start:title_end]
            if ' - ' in title:
                parts = title.split(' - ')
                company_name = parts[0].strip()
                model_name = parts[1].strip()
        
        # 从header中提取信息
        if '<header>' in content and '</header>' in content:
            header_start = content.find('<header>')
            header_end = content.find('</header>')
            header_content = content[header_start:header_end]
            
            if not company_name and ' - ' in header_content:
                parts = header_content.split(' - ')
                if len(parts) >= 2:
                    company_name = parts[0].strip()
                    model_name = parts[1].strip()
        
        print(f"检测到的网站信息:")
        print(f"  公司名称: {company_name or '未检测到'}")
        print(f"  产品型号: {model_name or '未检测到'}")
        
        # 验证其他页面是否使用相同的网站信息
        other_paths = ["/documentation", "/about", "/contact"]
        for path in other_paths:
            try:
                response = requests.get(f"{base_url}{path}", timeout=10)
                other_content = response.text
                
                # 检查是否包含相同的公司名称和型号
                company_consistent = company_name is None or company_name in other_content
                model_consistent = model_name is None or model_name in other_content
                
                print(f"  {path}: 公司名称一致={company_consistent}, 型号一致={model_consistent}")
                
            except Exception as e:
                print(f"  {path}: 访问失败 - {e}")
                
    except Exception as e:
        print(f"会话管理测试失败: {e}")

def test_template_content():
    """测试模板内容质量"""
    print("\n开始模板内容质量测试...")
    print("=" * 50)
    
    try:
        # 测试首页
        response = requests.get("http://127.0.0.1:8080/", timeout=10)
        content = response.text
        
        # 检查关键元素
        checks = {
            "HTML结构": "<!DOCTYPE html>" in content,
            "公司名称": "Tech Soulutions" in content or "company_name" not in content,
            "型号名称": "TechPrint" in content or "model_name" not in content,
            "导航菜单": "nav" in content,
            "样式表": "style" in content,
            "页脚": "footer" in content
        }
        
        print("首页内容检查:")
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"  {status} {check_name}")
        
        # 测试文档页
        response = requests.get("http://127.0.0.1:8080/documentation", timeout=10)
        content = response.text
        
        doc_checks = {
            "文档标题": "Documentation" in content,
            "安装指南": "Installation" in content or "安装" in content,
            "技术规格": "Specifications" in content or "规格" in content,
            "HTML结构": "<!DOCTYPE html>" in content
        }
        
        print("\n文档页内容检查:")
        for check_name, result in doc_checks.items():
            status = "✓" if result else "✗"
            print(f"  {status} {check_name}")
            
    except Exception as e:
        print(f"内容测试错误: {e}")

def test_error_handling():
    """测试错误处理"""
    print("\n开始错误处理测试...")
    print("=" * 50)
    
    # 测试无效路径
    try:
        response = requests.get("http://127.0.0.1:8080/invalid_path", timeout=10)
        print(f"无效路径响应: 状态码 {response.status_code}")
        if "400" in response.text or "Bad Request" in response.text:
            print("  ✓ 正确返回400错误页面")
        else:
            print("  ✗ 未正确返回400错误页面")
    except Exception as e:
        print(f"错误处理测试失败: {e}")

def test_cache_performance():
    """测试缓存性能 - 连续访问同一页面"""
    print("\n开始缓存性能测试...")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8080"
    test_path = "/"
    num_requests = 5
    
    print(f"连续访问 {test_path} {num_requests} 次:")
    
    times = []
    for i in range(num_requests):
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}{test_path}", timeout=10)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            times.append(response_time)
            
            print(f"  第{i+1}次: {response_time:.2f}ms")
            
        except Exception as e:
            print(f"  第{i+1}次: 失败 - {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n缓存性能统计:")
        print(f"  平均响应时间: {avg_time:.2f}ms")
        print(f"  最快响应时间: {min_time:.2f}ms")
        print(f"  最慢响应时间: {max_time:.2f}ms")
        
        # 检查响应时间是否稳定
        time_variance = max_time - min_time
        if time_variance < 50:
            print(f"  ✓ 响应时间稳定 (方差: {time_variance:.2f}ms)")
        else:
            print(f"  ⚠ 响应时间不稳定 (方差: {time_variance:.2f}ms)")

if __name__ == "__main__":
    print("HTTP模板系统测试")
    print("=" * 50)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 运行所有测试
    test_http_response_speed()
    test_content_consistency()
    test_session_management()
    test_template_content()
    test_error_handling()
    test_cache_performance()
    
    print("\n测试完成!") 