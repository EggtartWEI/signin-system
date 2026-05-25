#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os

# 尝试用不同编码读取
encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
data = {}

for enc in encodings:
    try:
        with open('data.json', 'r', encoding=enc) as f:
            data = json.load(f)
        print(f'成功使用 {enc} 编码读取')
        break
    except Exception as e:
        continue

print(f'\n现有日期: {list(data.keys())}')

# 部门结构
DEPT_STRUCTURE = {
    '公司值班': ['公司领导', '公司中层', '公司干部'],
    '计划部': ['库管'],
    '运行部': ['管理'],
    'D标': ['北京腾疆'],
    '生产管理': ['管理', '汽机', '锅炉', '输煤环保', {'name': '电气专业', 'slots': 2}, {'name': '热控专业', 'slots': 2}],
    'A标': ['管理', '汽机', '锅炉', '电气', '热控', '输煤', '硫硝'],
    '其他': ['起重维护', '保安', '保洁']
}

def generate_records(date):
    records = []
    for category, items in DEPT_STRUCTURE.items():
        for item in items:
            if isinstance(item, dict):
                for i in range(item['slots']):
                    dept_name = item['name'] if i == 0 else '{}({})'.format(item['name'], i + 1)
                    full_dept = '{}-{}'.format(category, item['name'])
                    records.append({'department': full_dept, 'displayName': dept_name, 'name': '-', 'employeeId': '-', 'phone': '-', 'signInTime': None, 'latitude': '', 'longitude': '', 'location': '', 'ip': '', 'isDefault': True})
            else:
                full_dept = '{}-{}'.format(category, item)
                records.append({'department': full_dept, 'displayName': item, 'name': '-', 'employeeId': '-', 'phone': '-', 'signInTime': None, 'latitude': '', 'longitude': '', 'location': '', 'ip': '', 'isDefault': True})
    return records

# 创建 23、24 号数据
for date in ['2026-05-23', '2026-05-24']:
    if date not in data:
        data[date] = generate_records(date)
        print('创建 {}: {} 条记录'.format(date, len(data[date])))
    else:
        print('{} 已存在'.format(date))

# 保存
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('\n完成！所有日期: {}'.format(sorted(data.keys())))
