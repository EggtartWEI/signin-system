#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
签到数据同步到金山云文档 - 通过 AirScript Webhook
用法: python sync_via_webhook.py

此脚本通过调用金山文档 AirScript 的 Webhook 来同步数据
需要在云文档中创建 AirScript 脚本并发布 Webhook
"""

import json
import sys
import os
import requests
from datetime import datetime

# 配置
DATA_FILE = 'data.json'

# AirScript Webhook URL
# 需要在金山文档中创建 AirScript 脚本并发布 Webhook 后获取
# 格式: https://www.kdocs.cn/api/v3/ide/file/xxx/script/xxx/webhook/xxx
AIRSCRIPT_WEBHOOK_URL = "https://www.kdocs.cn/api/v3/ide/file/cqrKey08JOk2/script/V2-6HFGPAYuP3dKcs3MSWvEu3/sync_task"

# 脚本令牌 (Script Token)
# 用于验证 Webhook 调用权限
# 在 AirScript 编辑器中【发布】→【脚本令牌】获取
AIRSCRIPT_TOKEN = "20LTgJrJX3oTp9UCkltr3M"


def read_data():
    """读取签到数据"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    
    for encoding in encodings:
        try:
            with open(DATA_FILE, 'r', encoding=encoding) as f:
                return json.load(f)
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"使用 {encoding} 编码读取失败: {str(e)}")
            continue
    
    print("所有编码尝试失败，返回空数据")
    return {}


def format_data_for_sheet(data):
    """将数据格式化为表格格式"""
    rows = []
    
    # 添加表头
    rows.append(['日期', '部门', '姓名', '电话', '记录时间'])
    
    # 添加数据行
    for date, records in sorted(data.items()):
        for record in records:
            name = record.get('name', '-') if record.get('name') else '-'
            phone = record.get('phone', '-') if record.get('phone') else '-'
            dept = record.get('department', '-')
            timestamp = record.get('timestamp', '-')
            
            rows.append([date, dept, name, phone, timestamp])
    
    return rows


def sync_via_webhook(webhook_url):
    """
    通过 AirScript Webhook 同步数据
    
    参数:
        webhook_url: AirScript 发布的 Webhook URL
    """
    print("=" * 70)
    print("签到数据同步到金山云文档 (Webhook 方式)")
    print("=" * 70)
    print()
    
    # 检查数据文件
    if not os.path.exists(DATA_FILE):
        print(f"错误: 数据文件不存在: {DATA_FILE}")
        return False
    
    print("✓ 数据文件检查通过")
    print()
    
    # 读取数据
    print("正在读取数据...")
    data = read_data()
    if not data:
        print("没有数据需要同步")
        return False
    
    total_records = sum(len(records) for records in data.values())
    print(f"✓ 读取到 {len(data)} 天的数据，共 {total_records} 条记录")
    print()
    
    # 格式化数据
    print("正在格式化数据...")
    sheet_data = format_data_for_sheet(data)
    print(f"✓ 格式化完成，共 {len(sheet_data)} 行（含表头）")
    print()
    
    # 发送数据到 Webhook
    print("正在发送数据到云文档...")
    
    # 注意：根据 Webhook URL，入口函数是 sync_task
    # URL 格式: .../script/xxx/sync_task
    # 所以数据直接作为参数传递，不需要 action 字段
    payload = {
        "data": sheet_data,
        "sync_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_rows": len(sheet_data) - 1  # 不含表头
    }
    
    try:
        headers = {
            'Content-Type': 'application/json',
            'Airscript-Token': AIRSCRIPT_TOKEN
        }
        
        print(f"请求头: {headers}")
        
        response = requests.post(
            webhook_url,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        print(f"响应状态码: {response.status_code}")
        
        try:
            result = response.json()
            print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)[:800]}")
            
            if response.status_code == 200:
                # AirScript Webhook 返回的是执行日志
                # 只要 HTTP 200 就认为请求成功
                print()
                print("=" * 70)
                print("✓ 数据同步成功！")
                print(f"\n同步时间: {payload['sync_time']}")
                print(f"数据行数: {payload['total_rows']}")
                return True
            else:
                print(f"\n✗ 请求失败: HTTP {response.status_code}")
                return False
                
        except json.JSONDecodeError:
            print(f"响应内容（非JSON）: {response.text[:200]}")
            if response.status_code == 200:
                print()
                print("=" * 70)
                print("✓ 数据同步成功！")
                return True
            else:
                print(f"\n✗ 请求失败: HTTP {response.status_code}")
                return False
                
    except requests.exceptions.Timeout:
        print("\n✗ 请求超时，请检查网络连接")
        return False
    except requests.exceptions.ConnectionError:
        print("\n✗ 连接错误，请检查网络连接")
        return False
    except Exception as e:
        print(f"\n✗ 发送请求失败: {str(e)}")
        return False


def main():
    """主函数"""
    # 检查是否配置了 Webhook URL 和脚本令牌
    if not AIRSCRIPT_WEBHOOK_URL or not AIRSCRIPT_TOKEN:
        print("=" * 70)
        print("签到数据同步到金山云文档 (Webhook 方式)")
        print("=" * 70)
        print()
        print("错误: 未配置 AirScript Webhook URL 或脚本令牌")
        print()
        print("请按以下步骤操作:")
        print("1. 在金山文档中打开目标表格")
        print("2. 点击【工具】-【脚本】-【新建脚本】")
        print("3. 创建接收数据的脚本")
        print("4. 保存脚本")
        print("5. 点击【发布】→【Webhook】获取 Webhook URL")
        print("6. 点击【发布】→【脚本令牌】生成令牌")
        print("7. 将 Webhook URL 和脚本令牌填入本脚本")
        print()
        print("云文档链接: https://www.kdocs.cn/l/cqrKey08JOk2")
        print()
        sys.exit(1)
    
    try:
        if sync_via_webhook(AIRSCRIPT_WEBHOOK_URL):
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()