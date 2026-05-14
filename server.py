#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
南宁公司值班签到系统 - Python后端服务器
兼容 Python 2 和 Python 3
"""

from __future__ import print_function
import sys
import os
import json
import datetime

# 根据Python版本导入不同模块
if sys.version_info[0] >= 3:
    # Python 3
    import http.server as BaseHTTPServer
    import socketserver
    from urllib.parse import urlparse, parse_qs
    from urllib.parse import unquote
else:
    # Python 2
    import BaseHTTPServer
    import SocketServer as socketserver
    from urlparse import urlparse, parse_qs
    from urllib import unquote

# 配置
PORT = 3000
DATA_FILE = 'data.json'
MODE_FILE = 'mode.json'

# 部门结构定义（与前端保持一致）
DEPT_STRUCTURE = {
    '公司值班': ['公司领导', '公司中层', '公司干部'],
    '计划部': ['库管'],
    '运行部': ['管理'],
    'D标': ['北京腾疆'],
    '生产管理': [
        '管理', 
        '汽机', 
        '锅炉', 
        '输煤环保', 
        {'name': '电气专业', 'slots': 2}, 
        {'name': '热控专业', 'slots': 2}
    ],
    'A标': ['管理', '汽机', '锅炉', '电气', '热控', '输煤', '硫硝'],
    '其他': ['起重维护', '保安', '保洁']
}

# MIME类型映射
MIME_TYPES = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon'
}


def init_data_files():
    """初始化数据文件"""
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({}, f)
    if not os.path.exists(MODE_FILE):
        with open(MODE_FILE, 'w') as f:
            json.dump({'mode': 'open', 'allowedIPs': []}, f)


def generate_default_records(date):
    """生成某天的默认空签到记录"""
    records = []
    for category, items in DEPT_STRUCTURE.items():
        for item in items:
            if isinstance(item, dict):
                # 多签到位置
                for i in range(item['slots']):
                    dept_name = item['name'] if i == 0 else '{}({})'.format(item['name'], i + 1)
                    full_dept = '{}-{}'.format(category, item['name'])
                    records.append({
                        'department': full_dept,
                        'displayName': dept_name,
                        'name': '-',
                        'employeeId': '-',
                        'phone': '-',
                        'signInTime': None,
                        'latitude': '',
                        'longitude': '',
                        'location': '',
                        'ip': '',
                        'isDefault': True
                    })
            else:
                full_dept = '{}-{}'.format(category, item)
                records.append({
                    'department': full_dept,
                    'displayName': item,
                    'name': '-',
                    'employeeId': '-',
                    'phone': '-',
                    'signInTime': None,
                    'latitude': '',
                    'longitude': '',
                    'location': '',
                    'ip': '',
                    'isDefault': True
                })
    return records


def get_or_create_daily_records(date):
    """获取或创建某天的签到记录"""
    data = read_data()
    if date not in data:
        # 生成默认空记录
        data[date] = generate_default_records(date)
        save_data(data)
    return data[date]


def update_record(date, department, updates):
    """更新指定部门的签到记录"""
    data = read_data()
    if date not in data:
        return False
    
    for record in data[date]:
        if record['department'] == department:
            record.update(updates)
            record['isDefault'] = False
            save_data(data)
            return True
    return False


def read_data():
    """读取签到数据"""
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_data(data):
    """保存签到数据"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_mode():
    """读取模式设置"""
    try:
        with open(MODE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'mode': 'open', 'allowedIPs': []}


def save_mode(mode):
    """保存模式设置"""
    with open(MODE_FILE, 'w') as f:
        json.dump(mode, f, ensure_ascii=False, indent=2)


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """自定义请求处理器"""
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print("[%s] %s" % (timestamp, args[0]))
    
    def send_cors_headers(self):
        """发送CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_OPTIONS(self):
        """处理OPTIONS请求"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # API路由
        if path == '/api/records':
            self.handle_get_records()
            return
        
        if path == '/api/mode':
            self.handle_get_mode()
            return
        
        if path == '/api/ip':
            self.handle_get_ip()
            return
        
        # 静态文件服务
        if path == '/':
            path = '/index.html'
        
        # 移除开头的 /
        file_path = os.path.join(os.path.dirname(__file__), path.lstrip('/'))
        
        # 安全检查：防止目录遍历
        base_dir = os.path.abspath(os.path.dirname(__file__))
        target_path = os.path.abspath(file_path)
        if not target_path.startswith(base_dir):
            self.send_error(403, "Forbidden")
            return
        
        if os.path.exists(file_path) and os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            content_type = MIME_TYPES.get(ext, 'application/octet-stream')
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_cors_headers()
            self.end_headers()
            
            # 二进制模式读取
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "File not found")
    
    def do_POST(self):
        """处理POST请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/records':
            self.handle_post_record()
            return
        
        if path == '/api/mode':
            self.handle_post_mode()
            return
        
        self.send_error(404, "Not found")
    
    def do_DELETE(self):
        """处理DELETE请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/api/records':
            self.handle_delete_record()
            return
        
        self.send_error(404, "Not found")
    
    def read_body(self):
        """读取请求体"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            if sys.version_info[0] >= 3:
                return self.rfile.read(content_length).decode('utf-8')
            else:
                return self.rfile.read(content_length)
        return '{}'
    
    def handle_get_records(self):
        """获取所有签到记录"""
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        
        # 如果指定了日期，确保该日期的记录存在
        date_param = query_params.get('date', [None])[0]
        if date_param:
            get_or_create_daily_records(date_param)
        
        data = read_data()
        self.send_json_response(data)
    
    def handle_get_mode(self):
        """获取模式设置"""
        mode = read_mode()
        self.send_json_response(mode)
    
    def handle_get_ip(self):
        """获取客户端IP"""
        client_ip = self.headers.get('X-Forwarded-For', self.client_address[0])
        self.send_json_response({'ip': client_ip})
    
    def handle_post_record(self):
        """添加或更新签到记录"""
        try:
            body = self.read_body()
            data = json.loads(body)
            
            date = data.get('date')
            record = data.get('record')
            
            if not date or not record:
                self.send_error_response(400, 'Missing parameters')
                return
            
            # 获取客户端IP
            client_ip = self.headers.get('X-Forwarded-For', self.client_address[0])
            record['ip'] = client_ip  # 记录IP地址
            
            # 确保该日期的记录已初始化
            records = get_or_create_daily_records(date)
            
            # 检查是否为管理员操作（补签/修改）
            is_admin_action = record.get('isAdminAction') == True
            department = record.get('department')
            
            # 只有普通签到才进行IP限制检查
            if not is_admin_action:
                # 检查该IP今天是否已经签过到（同一部门可以重复签到换人，不同部门不行）
                for r in records:
                    if r.get('ip') == client_ip and r.get('department') != department:
                        self.send_error_response(403, '签到失败，当前IP已签到，请更换IP签到')
                        return
            
            # 查找并更新对应部门的记录
            found = False
            for r in records:
                if r.get('department') == department:
                    # 更新记录（保留displayName）
                    display_name = r.get('displayName')
                    r.update(record)
                    r['displayName'] = display_name
                    r['isDefault'] = False
                    found = True
                    break
            
            if not found:
                # 如果找不到对应部门（不应该发生），添加新记录
                records.append(record)
            
            # 读取完整数据，更新当前日期，保留其他日期
            all_data = read_data()
            all_data[date] = records
            save_data(all_data)
            self.send_json_response({'success': True})
            
        except ValueError as e:
            self.send_error_response(400, 'JSON parse error')
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def handle_delete_record(self):
        """删除签到记录"""
        try:
            body = self.read_body()
            data = json.loads(body)
            
            date = data.get('date')
            department = data.get('department')
            name = data.get('name')
            
            if not date or not department or not name:
                self.send_error_response(400, 'Missing parameters')
                return
            
            records = read_data()
            
            if date in records:
                records[date] = [
                    r for r in records[date] 
                    if not (r.get('department') == department and r.get('name') == name)
                ]
                
                # 如果该日期没有记录了，删除该日期
                if len(records[date]) == 0:
                    del records[date]
                
                save_data(records)
            
            self.send_json_response({'success': True})
            
        except ValueError:
            self.send_error_response(400, 'JSON parse error')
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def handle_post_mode(self):
        """保存模式设置"""
        try:
            body = self.read_body()
            mode = json.loads(body)
            
            save_mode(mode)
            self.send_json_response({'success': True})
            
        except ValueError:
            self.send_error_response(400, 'JSON parse error')
        except Exception as e:
            self.send_error_response(500, str(e))
    
    def send_json_response(self, data):
        """发送JSON响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_cors_headers()
        self.end_headers()
        
        response = json.dumps(data, ensure_ascii=False)
        if sys.version_info[0] >= 3:
            self.wfile.write(response.encode('utf-8'))
        else:
            self.wfile.write(response)
    
    def send_error_response(self, code, message):
        """发送错误响应"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_cors_headers()
        self.end_headers()
        
        response = json.dumps({'error': message}, ensure_ascii=False)
        if sys.version_info[0] >= 3:
            self.wfile.write(response.encode('utf-8'))
        else:
            self.wfile.write(response)


def get_local_ip():
    """获取本机IP地址"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def main():
    """主函数"""
    init_data_files()
    
    local_ip = get_local_ip()
    
    server = socketserver.TCPServer(("", PORT), RequestHandler)
    
    print("=" * 50)
    print("  南宁公司值班签到系统 - Python服务器")
    print("=" * 50)
    print("")
    print("服务器启动成功！")
    print("")
    print("访问地址：")
    print("  - 本机访问：http://localhost:%d" % PORT)
    print("  - 局域网访问：http://%s:%d" % (local_ip, PORT))
    print("")
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    print("")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        server.shutdown()


if __name__ == '__main__':
    main()
