#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
签到数据同步模块 - 供服务器调用

此模块提供同步功能，可以被 server_with_auth.py 导入使用
"""

import json
import sys
import os
import requests
import threading
from datetime import datetime

# 线程锁（用于同一进程内的多线程）
_thread_lock = threading.Lock()

# 配置
# 数据文件路径（上级目录的 data.json）
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data.json')

# AirScript Webhook URL
AIRSCRIPT_WEBHOOK_URL = "https://www.kdocs.cn/api/v3/ide/file/cqrKey08JOk2/script/V2-6HFGPAYuP3dKcs3MSWvEu3/sync_task"

# 脚本令牌
AIRSCRIPT_TOKEN = "20LTgJrJX3oTp9UCkltr3M"

# 部门结构定义（与服务器保持一致）
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


def save_data(data):
    """
    保存签到数据（原子写操作，防止并发覆盖）
    使用临时文件+重命名的方式确保原子性
    """
    import time
    
    # 使用线程锁保护同一进程内的多线程并发
    with _thread_lock:
        # 原子写：先写入临时文件，再重命名
        temp_file = DATA_FILE + '.tmp'
        max_retries = 5
        
        for retry in range(max_retries):
            try:
                # 写入临时文件
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                # 原子重命名（Windows 和 Linux 都支持）
                if os.path.exists(DATA_FILE):
                    os.replace(temp_file, DATA_FILE)
                else:
                    os.rename(temp_file, DATA_FILE)
                
                return True
                
            except (IOError, OSError) as e:
                # 如果被占用，等待后重试
                if retry < max_retries - 1:
                    time.sleep(0.1 * (retry + 1))
                    continue
                else:
                    raise
        
        return False


def ensure_today_record():
    """
    确保当天的记录存在，如果不存在则创建空记录
    返回: (data, today_str) - 完整数据字典和当天日期字符串
    """
    data = read_data()
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 如果当天没有记录，创建空记录
    if today not in data:
        print(f"[数据初始化] 创建 {today} 的空记录")
        data[today] = generate_default_records(today)
        save_data(data)
    
    return data, today


def read_data():
    """读取签到数据（带重试机制）"""
    import time
    encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
    
    # 重试机制：如果文件被占用，等待后重试
    max_retries = 5
    for retry in range(max_retries):
        for encoding in encodings:
            try:
                with open(DATA_FILE, 'r', encoding=encoding) as f:
                    return json.load(f)
            except UnicodeDecodeError:
                continue
            except (IOError, OSError) as e:
                # 文件被占用或其他IO错误，等待后重试
                if retry < max_retries - 1:
                    time.sleep(0.1 * (retry + 1))
                    break
                continue
            except Exception as e:
                continue
    
    return {}


def format_data_for_sheet(data, date_filter=None):
    """
    将数据格式化为表格格式
    
    参数:
        data: 签到数据字典
        date_filter: 日期过滤，如 '2026-05-15'，为 None 则返回所有数据
    """
    rows = []
    
    # 添加表头
    rows.append(['日期', '部门', '姓名', '工号', '电话', '签到时间', '签到状态', '是否迟到'])
    
    # 过滤日期
    if date_filter:
        filtered_dates = [date_filter] if date_filter in data else []
    else:
        filtered_dates = sorted(data.keys())
    
    # 添加数据行
    for date in filtered_dates:
        records = data.get(date, [])
        for record in records:
            dept = record.get('department', '-')
            employee_id = record.get('employeeId', '-')
            sign_in_time = record.get('signInTime', '')
            is_default = record.get('isDefault', False)
            
            if is_default:
                name = '-'
                phone = '-'
                time_str = '-'
                sign_status = '未签到'
                is_late = '-'
            else:
                name = record.get('name', '-') if record.get('name') else '-'
                phone = record.get('phone', '-') if record.get('phone') else '-'
                sign_status = '已签到'
                
                time_str = '-'
                is_late = '否'
                if sign_in_time:
                    try:
                        dt = datetime.fromisoformat(sign_in_time.replace('Z', '+00:00'))
                        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                        if dt.hour >= 20:
                            is_late = '是'
                    except:
                        time_str = sign_in_time
            
            rows.append([date, dept, name, employee_id, phone, time_str, sign_status, is_late])
    
    return rows


def send_to_webhook(webhook_url, sheet_data, table_name):
    """
    发送数据到 Webhook
    
    参数:
        webhook_url: Webhook URL
        sheet_data: 表格数据
        table_name: 表格名称
    
    返回:
        (success: bool, message: str)
    """
    payload = {
        "Context": {
            "argv": {
                "data": sheet_data,
                "sync_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_rows": len(sheet_data) - 1,
                "table_name": table_name
            }
        }
    }
    
    headers = {
        'Content-Type': 'application/json',
        'AirScript-Token': AIRSCRIPT_TOKEN
    }
    
    try:
        response = requests.post(
            webhook_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            try:
                result = response.json()
                status = result.get('status', '')
                error_msg = result.get('error', '')
                
                if status == 'finished' and not error_msg:
                    return True, f"{table_name} 同步成功，共 {len(sheet_data)-1} 行数据"
                else:
                    return False, f"{table_name} 同步失败: {error_msg}"
            except:
                return True, f"{table_name} 同步成功（HTTP 200）"
        else:
            return False, f"{table_name} 同步失败: HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"{table_name} 同步失败: {str(e)}"


def sync_today_data():
    """
    同步当天数据到云文档
    供服务器在签到后调用
    
    返回:
        (success: bool, message: str)
    """
    try:
        # 确保当天记录存在（如果没有则创建空记录）
        data, today = ensure_today_record()
        
        if not data:
            return False, "没有数据需要同步"
        
        # 格式化当天数据
        today_data = format_data_for_sheet(data, date_filter=today)
        
        if len(today_data) <= 1:  # 只有表头，没有数据行
            return False, f"当天 ({today}) 没有签到记录"
        
        # 发送数据到云文档
        success, message = send_to_webhook(AIRSCRIPT_WEBHOOK_URL, today_data, "当天签到数据")
        
        return success, message
        
    except Exception as e:
        return False, f"同步异常: {str(e)}"


def sync_all_data():
    """
    同步所有数据到云文档（历史和当天）
    供定时任务调用
    
    返回:
        (success: bool, message: str)
    """
    try:
        # 确保当天记录存在（如果没有则创建空记录）
        data, today = ensure_today_record()
        
        if not data:
            return False, "没有数据需要同步"
        
        # 格式化历史数据（所有数据）
        history_data = format_data_for_sheet(data, date_filter=None)
        
        # 格式化当天数据
        today_data = format_data_for_sheet(data, date_filter=today)
        if len(today_data) <= 1:  # 没有数据
            today_data = [history_data[0]]  # 复制表头
        
        # 发送历史数据
        history_success, history_msg = send_to_webhook(AIRSCRIPT_WEBHOOK_URL, history_data, "历史签到数据")
        
        # 发送当天数据
        today_success, today_msg = send_to_webhook(AIRSCRIPT_WEBHOOK_URL, today_data, "当天签到数据")
        
        # 汇总结果
        if history_success and today_success:
            return True, f"同步成功 | 历史: {len(history_data)-1} 行, 当天: {len(today_data)-1} 行"
        elif history_success:
            return False, f"历史数据同步成功，当天数据同步失败: {today_msg}"
        elif today_success:
            return False, f"当天数据同步成功，历史数据同步失败: {history_msg}"
        else:
            return False, f"同步失败 | 历史: {history_msg}, 当天: {today_msg}"
            
    except Exception as e:
        return False, f"同步异常: {str(e)}"


# 兼容旧脚本的入口函数
def sync_via_webhook(webhook_url=None):
    """
    通过 AirScript Webhook 同步数据（兼容旧接口）
    """
    if webhook_url is None:
        webhook_url = AIRSCRIPT_WEBHOOK_URL
    
    print("=" * 70)
    print("签到数据同步到金山云文档")
    print("=" * 70)
    print()
    
    success, message = sync_all_data()
    
    print()
    print("=" * 70)
    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")
    print("=" * 70)
    
    return success


if __name__ == '__main__':
    # 作为主脚本运行
    sync_via_webhook()
