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
            
            records = read_data()
            
            if date not in records:
                records[date] = []
            
            # 检查是否已存在（同部门同名）
            existing_index = -1
            for i, r in enumerate(records[date]):
                if r.get('department') == record.get('department') and r.get('name') == record.get('name'):
                    existing_index = i
                    break
            
            if existing_index >= 0:
                records[date][existing_index] = record
            else:
                records[date].append(record)
            
            save_data(records)
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
