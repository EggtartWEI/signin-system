/**
 * 签到数据同步 - AirScript Webhook 脚本 (双表格版本)
 * 语言: JavaScript (ES6)
 * 
 * 说明：
 * 1. 此脚本部署在金山文档 AirScript 中
 * 2. 外部通过 Webhook + 脚本令牌调用
 * 3. 参数通过 Context.argv 获取
 * 4. 支持写入两个表格："历史签到数据"和"当天签到数据"
 * 
 * 官方文档：https://airsheet.wps.cn/docs/apitoken/api.html
 */

/**
 * 主入口函数
 * AirScript Webhook 调用时，参数通过 Context.argv 传递
 * 
 * 外部调用方式：
 * POST /api/v3/ide/file/:file_id/script/:script_id/sync_task
 * Header: AirScript-Token: <你的脚本令牌>
 * Body: {
 *   "Context": {
 *     "argv": {
 *       "data": [["日期", "部门", "姓名"], ["2025-01-12", "技术部", "张三"]],
 *       "sync_time": "2025-01-12 10:00:00",
 *       "total_rows": 1,
 *       "table_name": "历史签到数据"  // 或 "当天签到数据"
 *     }
 *   }
 * }
 */
function sync_task() {
    try {
        console.log("=== AirScript 同步开始 ===");
        
        // 从 Context.argv 获取传入的参数
        var params = null;
        
        if (typeof Context !== 'undefined' && Context.argv) {
            params = Context.argv;
            console.log("从 Context.argv 获取到参数");
        } else {
            console.log("Context.argv 不存在或为空");
            return {
                code: -1,
                success: false,
                msg: "未接收到参数，请检查调用方式"
            };
        }
        
        console.log("接收到的参数: " + JSON.stringify(params));
        
        // 获取表格名称（用于区分写入哪个表格）
        var tableName = params.table_name || "默认表格";
        console.log("目标表格: " + tableName);
        
        // 根据表格名称获取对应的工作表
        var sheet = null;
        
        try {
            // 尝试通过名称获取表格
            // 表格名称应该与云文档中的工作表名称一致
            if (tableName === "历史签到数据") {
                // 尝试获取名为"历史签到数据"的工作表
                try {
                    sheet = Application.Sheets.Item("历史签到数据");
                    console.log("找到工作表: 历史签到数据");
                } catch (e) {
                    // 如果找不到指定名称的工作表，使用第一个
                    sheet = Application.Sheets.Item(1);
                    console.log("未找到'历史签到数据'工作表，使用第一个工作表");
                }
            } else if (tableName === "当天签到数据") {
                // 尝试获取名为"当天签到数据"的工作表
                try {
                    sheet = Application.Sheets.Item("当天签到数据");
                    console.log("找到工作表: 当天签到数据");
                } catch (e) {
                    // 如果找不到指定名称的工作表，使用第二个（如果存在）
                    try {
                        sheet = Application.Sheets.Item(2);
                        console.log("未找到'当天签到数据'工作表，使用第二个工作表");
                    } catch (e2) {
                        sheet = Application.Sheets.Item(1);
                        console.log("未找到'当天签到数据'工作表，使用第一个工作表");
                    }
                }
            } else {
                // 默认使用活动工作表或第一个工作表
                sheet = Application.ActiveSheet;
                if (!sheet) {
                    sheet = Application.Sheets.Item(1);
                    console.log("使用第一个工作表");
                }
            }
        } catch (e) {
            console.log("获取工作表失败: " + e.message);
            return {
                code: -1,
                success: false,
                msg: "无法获取工作表: " + e.message
            };
        }
        
        if (!sheet) {
            return {
                code: -1,
                success: false,
                msg: "无法获取表格，请确保文档中包含表格"
            };
        }
        
        console.log("成功获取工作表");
        
        // 从参数中获取数据
        var rows = null;
        
        if (params && params.data) {
            rows = params.data;
            console.log("从 params.data 获取数据");
        }
        
        if (!rows || !Array.isArray(rows) || rows.length === 0) {
            console.log("没有有效数据");
            return {
                code: -1,
                success: false,
                msg: "没有数据或数据格式不正确",
                received_params: JSON.stringify(params)
            };
        }
        
        console.log("数据行数: " + rows.length);
        
        // 清空表格原有数据
        try {
            var usedRange = sheet.UsedRange;
            if (usedRange && usedRange.Rows.Count > 0) {
                console.log("清空原有数据，原数据行数: " + usedRange.Rows.Count);
                usedRange.ClearContents();
            }
        } catch (clearError) {
            console.log("清空数据时出错（可能表格原本为空）: " + clearError.message);
        }
        
        // 写入数据到表格
        console.log("开始写入数据...");
        for (var i = 0; i < rows.length; i++) {
            var row = rows[i];
            if (!Array.isArray(row)) {
                console.log("第 " + (i + 1) + " 行不是数组，跳过");
                continue;
            }
            
            for (var j = 0; j < row.length; j++) {
                try {
                    // Cells(row, column) - 行列从 1 开始
                    sheet.Cells(i + 1, j + 1).Value2 = row[j] || "";
                } catch (cellError) {
                    console.log("写入单元格失败 (" + (i + 1) + "," + (j + 1) + "): " + cellError.message);
                }
            }
        }
        
        console.log("数据写入完成");
        
        // 自动调整列宽
        try {
            var usedRange2 = sheet.UsedRange;
            if (usedRange2) {
                usedRange2.Columns.AutoFit();
                console.log("自动调整列宽完成");
            }
        } catch (autoFitError) {
            console.log("自动调整列宽失败: " + autoFitError.message);
        }
        
        return {
            code: 0,
            success: true,
            msg: tableName + " 同步成功",
            rows: rows.length,
            columns: rows.length > 0 ? rows[0].length : 0,
            table_name: tableName,
            sync_time: params && params.sync_time ? params.sync_time : new Date().toLocaleString()
        };
        
    } catch (e) {
        console.log("发生错误: " + e.message);
        console.log("错误堆栈: " + (e.stack || "无堆栈信息"));
        return {
            code: -1,
            success: false,
            msg: "错误: " + e.message,
            stack: e.stack || ""
        };
    }
}

/**
 * 测试函数
 * 在 AirScript 编辑器中点击【运行】按钮测试此脚本
 */
function test() {
    console.log("=== 开始测试 ===");
    
    // 在 AirScript 编辑器中测试时，手动设置 Context.argv
    if (typeof Context === 'undefined') {
        Context = {};
    }
    if (!Context.argv) {
        Context.argv = {
            data: [
                ["日期", "部门", "姓名", "工号", "电话", "签到时间", "签到状态", "是否迟到"],
                ["2025-01-12", "技术部", "张三", "1001", "13800138000", "2025-01-12 09:00:00", "已签到", "否"],
                ["2025-01-12", "销售部", "李四", "1002", "13900139000", "2025-01-12 09:30:00", "已签到", "否"]
            ],
            sync_time: "2025-01-12 10:00:00",
            total_rows: 2,
            table_name: "历史签到数据"  // 测试时指定表格名称
        };
    }
    
    console.log("测试数据: " + JSON.stringify(Context.argv));
    
    var result = sync_task();
    
    console.log("测试结果: " + JSON.stringify(result));
    
    return result;
}

/**
 * 清空表格函数
 */
function clear_sheet() {
    try {
        var sheet = Application.ActiveSheet;
        if (!sheet) {
            sheet = Application.Sheets.Item(1);
        }
        
        if (sheet) {
            var usedRange = sheet.UsedRange;
            if (usedRange) {
                usedRange.ClearContents();
                return { success: true, msg: "表格已清空" };
            }
        }
        return { success: false, msg: "无法获取表格" };
    } catch (e) {
        return { success: false, msg: "错误: " + e.message };
    }
}

// 当在 AirScript 编辑器中点击【运行】时，默认执行 test 函数
// 注意：实际 Webhook 调用时不会执行这行代码
test();
