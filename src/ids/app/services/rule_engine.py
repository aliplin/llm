import re
import time
import threading
from ..utils.database import get_db_connection

class RuleEngine:
    """规则引擎类"""
    
    def __init__(self):
        self.rules = []
        self.load_rules()
        self.lock = threading.Lock()
        self.blocked_ips = {}

    def load_rules(self):
        """从数据库加载规则"""
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM rules WHERE enabled = 1")
        rules_data = c.fetchall()
        conn.close()
        
        print(f"加载了 {len(rules_data)} 条规则")
        self.rules = []
        for rule in rules_data:
            try:
                pattern = re.compile(rule[3], re.IGNORECASE)
                self.rules.append({
                    'id': rule[0],
                    'name': rule[1],
                    'pattern': pattern,
                    'severity': rule[4],
                    'category': rule[5],
                    'description': rule[2]
                })
                print(f"加载规则: {rule[1]} - {rule[3]}")
            except re.error:
                print(f"无效的正则表达式模式: {rule[3]}")

    def check_rule(self, rule, targets, request_data, results):
        """检查单个规则"""
        for target in targets:
            if rule['pattern'].search(target):
                with self.lock:
                    results.append({
                        'rule_id': rule['id'],
                        'rule_name': rule['name'],
                        'event_type': rule['category'],
                        'severity': rule['severity'],
                        'description': rule['description'],
                        'matched_pattern': rule['pattern'].pattern,
                        'request_data': request_data
                    })
                break

    def check_request(self, request):
        """检查请求是否匹配规则"""
        ip = request.remote_addr
        
        # 检查IP是否被封禁
        if ip in self.blocked_ips:
            if time.time() < self.blocked_ips[ip]:
                return [{'type': 'blocked_ip', 'severity': 'high'}]
            else:
                del self.blocked_ips[ip]
        
        results = []
        request_data = {
            'path': request.path,
            'method': request.method,
            'args': dict(request.args),
            'form': dict(request.form),
            'headers': dict(request.headers),
            'ip': ip,
            'user_agent': request.user_agent.string
        }
        
        targets = [
            request.path,
            str(request.args),
            str(request.form),
            request.user_agent.string
        ]
        
        print(f"检查请求: {request.method} {request.path}")
        print(f"目标字符串: {targets}")
        
        # 多线程规则匹配
        threads = []
        for rule in self.rules:
            thread = threading.Thread(target=self.check_rule, args=(rule, targets, request_data, results))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        if results:
            print(f"检测到 {len(results)} 个匹配的规则")
            for result in results:
                print(f"  - {result['rule_name']}: {result['description']}")
        else:
            print("未检测到匹配的规则")

        return results

    def block_ip(self, ip, duration=3600):
        """封禁IP地址"""
        self.blocked_ips[ip] = time.time() + duration
        return True
