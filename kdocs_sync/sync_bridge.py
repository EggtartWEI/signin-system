#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据同步桥接脚本

功能：
1. 从内网生产服务器获取签到数据
2. 同步到金山云文档

运行环境：需要有网络访问的机器（同步服务器）
定时任务：建议每 5-10 分钟运行一次，或每天晚上 20:00 运行
"""

import json
import sys
import os
import requests
from datetime import datetime

# 配置
# 生产服务器地址（内网IP）
PROD_SERVER_URL = os.getenv("PROD_SERVER_URL", "http://10.45.140.70:3000")

# AirScript Webhook 配置
AIRSCRIPT_WEBHOOK_URL = os.getenv("AIRSCRIPT_WEBHOOK_URL", "")
AIRSCRIPT_TOKEN = os.getenv("AIRSCRIPT_TOKEN", "")

# 超时设置
REQUEST_TIMEOUT = 30


def fetch_data_from_prod():
    """
    从生产服务器获取签到数据
    
    返回:
        dict: 签到数据，失败返回 None
    """
    try:
        url = f"{PROD_SERVER_URL}/api/export/data"
        print(f"[{datetime.now()}] 正在从生产服务器获取数据: {url}")
        
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            record_count = data.get('record_count', 0)
            print(f"[{datetime.now()}] 成功获取数据，共 {record_count} 天记录")
            return data.get('data', {})
        else:
            print(f"[{datetime.now()}] 获取数据失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError as e:
        print(f"[{datetime.now()}] 连接生产服务器失败: {e}")
        print("请检查:")
        print("  1. 生产服务器是否运行")
        print("  2. 网络是否连通")
        print(f"  3. 地址是否正确: {PROD_SERVER_URL}")
        return None
    except requests.exceptions.Timeout:
        print(f"[{datetime.now()}] 请求超时")
        return None
    except Exception as e:
        print(f"[{datetime.now()}] 获取数据时出错: {e}")
        return None


def sync_to_kdocs(data):
    """
    同步数据到金山云文档
    
    参数:
        data: 签到数据字典
    
    返回:
        bool: 是否成功
    """
    if not AIRSCRIPT_WEBHOOK_URL or not AIRSCRIPT_TOKEN:
        print(f"[{datetime.now()}] 错误: 未配置 AirScript Webhook")
        print("请设置环境变量:")
        print("  AIRSCRIPT_WEBHOOK_URL")
        print("  AIRSCRIPT_TOKEN")
        return False
    
    try:
        print(f"[{datetime.now()}] 正在同步到金山云文档...")
        
        # 准备请求数据
        payload = {
            "token": AIRSCRIPT_TOKEN,
            "data": data,
            "sync_time": datetime.now().isoformat()
        }
        
        # 发送请求
        response = requests.post(
            AIRSCRIPT_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print(f"[{datetime.now()}] 同步成功: {result.get('message', 'OK')}")
                return True
            else:
                print(f"[{datetime.now()}] 同步失败: {result.get('message', 'Unknown error')}")
                return False
        else:
            print(f"[{datetime.now()}] 同步失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"[{datetime.now()}] 同步超时")
        return False
    except Exception as e:
        print(f"[{datetime.now()}] 同步时出错: {e}")
        return False


def save_data_locally(data, backup_dir="backup"):
    """
    本地备份数据
    
    参数:
        data: 签到数据
        backup_dir: 备份目录
    """
    try:
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{backup_dir}/sync-backup-{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"[{datetime.now()}] 数据已备份到: {filename}")
        
        # 只保留最近 30 个备份
        backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('sync-backup-')])
        if len(backups) > 30:
            for old_file in backups[:-30]:
                os.remove(os.path.join(backup_dir, old_file))
                print(f"  删除旧备份: {old_file}")
                
    except Exception as e:
        print(f"[{datetime.now()}] 备份数据时出错: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print(f"[{datetime.now()}] 开始数据同步桥接任务")
    print("=" * 60)
    
    # 1. 从生产服务器获取数据
    data = fetch_data_from_prod()
    if not data:
        print(f"[{datetime.now()}] 获取数据失败，同步终止")
        return 1
    
    # 2. 本地备份
    save_data_locally(data)
    
    # 3. 同步到云文档
    success = sync_to_kdocs(data)
    if not success:
        print(f"[{datetime.now()}] 同步到云文档失败")
        return 1
    
    print("=" * 60)
    print(f"[{datetime.now()}] 同步任务完成")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
