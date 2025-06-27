#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络接口检测脚本
帮助用户了解系统可用的网络接口
"""

import netifaces
import platform

def check_network_interfaces():
    """检查网络接口"""
    print("=" * 60)
    print("🌐 网络接口检测工具")
    print("=" * 60)
    
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"Python版本: {platform.python_version()}")
    print()
    
    try:
        # 获取所有网络接口
        interfaces = netifaces.interfaces()
        print(f"发现 {len(interfaces)} 个网络接口:")
        print()
        
        available_interfaces = []
        
        for i, iface in enumerate(interfaces, 1):
            print(f"{i:2d}. {iface}")
            
            try:
                # 获取接口地址信息
                addrs = netifaces.ifaddresses(iface)
                
                # 检查IPv4地址
                if netifaces.AF_INET in addrs:
                    for addr_info in addrs[netifaces.AF_INET]:
                        ip = addr_info['addr']
                        netmask = addr_info.get('netmask', 'N/A')
                        
                        # 判断接口类型
                        if ip.startswith('127.'):
                            interface_type = "回环接口"
                        elif iface.startswith('{'):
                            interface_type = "虚拟接口"
                        elif iface.startswith('vEthernet') or iface.startswith('VMware'):
                            interface_type = "虚拟机接口"
                        else:
                            interface_type = "物理接口"
                            if not ip.startswith('127.'):
                                available_interfaces.append((iface, ip, netmask))
                        
                        print(f"     IPv4: {ip}/{netmask} ({interface_type})")
                
                # 检查IPv6地址
                if netifaces.AF_INET6 in addrs:
                    for addr_info in addrs[netifaces.AF_INET6]:
                        ip = addr_info['addr']
                        print(f"     IPv6: {ip}")
                
                # 检查MAC地址
                if netifaces.AF_LINK in addrs:
                    for addr_info in addrs[netifaces.AF_LINK]:
                        mac = addr_info['addr']
                        print(f"     MAC:  {mac}")
                        
            except Exception as e:
                print(f"     错误: {e}")
            
            print()
        
        # 显示推荐接口
        if available_interfaces:
            print("=" * 60)
            print("✅ 推荐使用的网络接口:")
            print("=" * 60)
            
            for i, (iface, ip, netmask) in enumerate(available_interfaces, 1):
                print(f"{i}. {iface} - {ip}/{netmask}")
            
            print()
            print("💡 系统将自动选择第一个可用的物理接口")
        else:
            print("⚠️  未找到可用的物理网络接口")
            print("   请检查网络配置或使用虚拟机环境")
        
        return True
        
    except Exception as e:
        print(f"❌ 检测网络接口时发生错误: {e}")
        return False

def test_interface_connectivity(interface_name):
    """测试接口连通性"""
    print(f"\n🧪 测试接口 {interface_name} 的连通性...")
    
    try:
        # 获取接口IP
        addrs = netifaces.ifaddresses(interface_name)
        if netifaces.AF_INET in addrs:
            ip = addrs[netifaces.AF_INET][0]['addr']
            print(f"   接口IP: {ip}")
            
            # 简单的连通性测试
            import socket
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
            test_socket.close()
            print("✅ 接口权限检查通过")
            return True
        else:
            print("❌ 接口没有IPv4地址")
            return False
            
    except PermissionError:
        print("❌ 需要管理员权限来测试接口")
        print("   请以管理员身份运行此脚本")
        return False
    except Exception as e:
        print(f"❌ 测试接口时发生错误: {e}")
        return False

def main():
    """主函数"""
    if check_network_interfaces():
        print("\n" + "=" * 60)
        print("🔧 配置建议")
        print("=" * 60)
        
        print("1. 如果系统自动检测失败，可以手动指定网络接口")
        print("2. 在 ids_llm.py 中修改 get_interface_ip() 调用:")
        print("   PVM_IP_ADDRESS, interface_name = get_interface_ip('你的接口名称')")
        print("3. 确保以管理员权限运行IDS系统")
        print("4. 在Windows上，可能需要禁用防火墙或添加例外")
        
        print("\n" + "=" * 60)
        print("🚀 下一步")
        print("=" * 60)
        print("1. 运行测试: python test_system.py")
        print("2. 启动系统: python start_ids.py")
        print("3. 访问Web界面: http://localhost:5001")

if __name__ == "__main__":
    main() 