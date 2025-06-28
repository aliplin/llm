import threading
import time
from scapy.all import sniff, Raw
from scapy.layers.inet import IP, TCP, UDP
from datetime import datetime
import logging
import re
from ..utils.database import get_db_connection

class PacketSniffer(threading.Thread):
    """数据包嗅探服务"""
    
    def __init__(self, socketio=None, iface=None):
        super().__init__()
        self.socketio = socketio
        self.iface = iface
        self.running = True
        self.logger = logging.getLogger('PacketSniffer')
        self.packet_counter = 0
        
        # 配置日志
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def run(self):
        """运行数据包嗅探"""
        self.logger.info("数据包嗅探服务已启动")
        
        try:
            # 开始嗅探数据包，不指定接口让系统自动选择
            sniff(prn=self.process_packet, store=0, stop_filter=lambda x: not self.running)
        except Exception as e:
            self.logger.error(f"数据包嗅探错误: {e}")
            # 如果嗅探失败，使用模拟数据包进行测试
            self.simulate_packets()
    
    def simulate_packets(self):
        """模拟数据包用于测试"""
        self.logger.info("使用模拟数据包模式")
        while self.running:
            try:
                # 模拟正常流量
                self.process_simulated_packet({
                    'src_ip': '192.168.1.100',
                    'dst_ip': '8.8.8.8',
                    'src_port': 12345,
                    'dst_port': 80,
                    'protocol': 'TCP',
                    'payload': 'GET / HTTP/1.1\r\nHost: example.com\r\n\r\n',
                    'timestamp': datetime.now().isoformat(),
                    'length': 150
                })
                
                time.sleep(2)
                
                # 模拟可疑流量
                self.process_simulated_packet({
                    'src_ip': '192.168.1.101',
                    'dst_ip': '192.168.1.1',
                    'src_port': 54321,
                    'dst_port': 22,
                    'protocol': 'TCP',
                    'payload': 'ssh connection attempt',
                    'timestamp': datetime.now().isoformat(),
                    'length': 100
                })
                
                time.sleep(3)
                
            except Exception as e:
                self.logger.error(f"模拟数据包错误: {e}")
                time.sleep(5)
    
    def process_simulated_packet(self, packet_data):
        """处理模拟数据包"""
        self.packet_counter += 1
        
        # 通过WebSocket发送实时数据包信息
        if self.socketio:
            self.socketio.emit('packet', {
                'type': 'packet',
                'packet': packet_data
            })
        
        # 检查是否触发规则
        self.check_packet_rules(packet_data)
    
    def process_packet(self, packet):
        """处理真实数据包"""
        try:
            if IP in packet:
                # 提取数据包信息
                packet_data = {
                    'src_ip': packet[IP].src,
                    'dst_ip': packet[IP].dst,
                    'src_port': 0,
                    'dst_port': 0,
                    'protocol': 'IP',
                    'timestamp': datetime.now().isoformat(),
                    'length': len(packet)
                }
                
                # 检查TCP
                if TCP in packet:
                    packet_data['protocol'] = 'TCP'
                    packet_data['src_port'] = packet[TCP].sport
                    packet_data['dst_port'] = packet[TCP].dport
                # 检查UDP
                elif UDP in packet:
                    packet_data['protocol'] = 'UDP'
                    packet_data['src_port'] = packet[UDP].sport
                    packet_data['dst_port'] = packet[UDP].dport
                
                # 检查是否有负载数据
                if Raw in packet:
                    payload = packet[Raw].load
                    try:
                        # 尝试解码为字符串
                        payload_str = payload.decode('utf-8', errors='ignore')
                        packet_data['payload'] = payload_str[:200]  # 限制长度
                    except:
                        packet_data['payload'] = str(payload)[:200]
                
                self.packet_counter += 1
                
                # 通过WebSocket发送实时数据包信息
                if self.socketio:
                    self.socketio.emit('packet', {
                        'type': 'packet',
                        'packet': packet_data
                    })
                
                # 检查是否触发规则
                self.check_packet_rules(packet_data)
                
        except Exception as e:
            self.logger.error(f"处理数据包错误: {e}")
    
    def check_packet_rules(self, packet_data):
        """检查数据包是否触发规则"""
        try:
            # 检查常见攻击端口
            suspicious_ports = [22, 23, 3389, 5900, 1433, 3306, 5432, 6379, 27017]
            if packet_data['dst_port'] in suspicious_ports:
                self.create_event('suspicious_port', 'high', 
                                f"检测到对可疑端口的访问: {packet_data['dst_ip']}:{packet_data['dst_port']}", 
                                packet_data)
            
            # 检查负载中的可疑内容
            payload = packet_data.get('payload', '').lower()
            
            # SQL注入检测
            sql_patterns = [r'\b(select|insert|update|delete|drop|union|or|and)\b', 
                           r'(\'|\")\s*(or|and)\s*\d+\s*=\s*\d+']
            for pattern in sql_patterns:
                if re.search(pattern, payload, re.IGNORECASE):
                    self.create_event('sql_injection', 'high', 
                                    f"检测到SQL注入尝试: {pattern}", 
                                    packet_data)
                    break
            
            # XSS检测
            xss_patterns = [r'<script[^>]*>.*?</script>', r'<[^>]*on\w+\s*=\s*[^>]*>']
            for pattern in xss_patterns:
                if re.search(pattern, payload, re.IGNORECASE):
                    self.create_event('xss_attack', 'high', 
                                    f"检测到XSS攻击尝试: {pattern}", 
                                    packet_data)
                    break
            
            # 命令注入检测
            cmd_patterns = [r'\b(wget|curl|nc|netcat|bash|sh|python|perl|ruby)\b.*?\$', 
                           r'\$\(.*?\)']
            for pattern in cmd_patterns:
                if re.search(pattern, payload, re.IGNORECASE):
                    self.create_event('command_injection', 'high', 
                                    f"检测到命令注入尝试: {pattern}", 
                                    packet_data)
                    break
                    
        except Exception as e:
            self.logger.error(f"检查数据包规则失败: {e}")
    
    def create_event(self, event_type, severity, description, packet_data):
        """创建事件"""
        try:
            # 保存事件到数据库
            conn = get_db_connection()
            c = conn.cursor()
            
            c.execute("""
                INSERT INTO events 
                (timestamp, ip_address, user_agent, request_path, request_method, request_data, severity, status, event_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                packet_data['src_ip'],
                f"{packet_data['protocol']} {packet_data['src_port']}",
                f"{packet_data['dst_ip']}:{packet_data['dst_port']}",
                packet_data['protocol'],
                str(packet_data),
                severity,
                'detected',
                event_type
            ))
            
            conn.commit()
            conn.close()
            
            # 通过WebSocket发送事件通知
            if self.socketio:
                event_data = {
                    'id': None,
                    'timestamp': packet_data['timestamp'],
                    'ip_address': packet_data['src_ip'],
                    'user_agent': f"{packet_data['protocol']} {packet_data['src_port']}",
                    'request_path': f"{packet_data['dst_ip']}:{packet_data['dst_port']}",
                    'request_method': packet_data['protocol'],
                    'request_data': packet_data,
                    'severity': severity,
                    'status': 'detected',
                    'event_type': event_type,
                    'rule_name': description,
                    'description': description,
                    'matched_pattern': event_type
                }
                
                self.socketio.emit('event', {
                    'type': 'event',
                    'event': event_data
                })
            
            self.logger.warning(f"检测到事件: {event_type} - {description}")
            
        except Exception as e:
            self.logger.error(f"创建事件失败: {e}")
    
    def stop(self):
        """停止数据包嗅探"""
        self.running = False
        self.logger.info("数据包嗅探服务已停止")

def start_packet_sniffer(rule_engine=None, iface='WLAN', socketio=None):
    """启动数据包嗅探服务"""
    sniffer = PacketSniffer(rule_engine, iface, socketio)
    sniffer.daemon = True
    sniffer.start()
    return sniffer
