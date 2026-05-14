/**
 * 签到数据同步 - AirScript Webhook 脚本
 * 
 * 将此代码复制到金山文档的 AirScript 编辑器中
 * 然后发布为 Webhook
 */

/**
 * Webhook 入口函数
 * @param {Object} data - POST 请求的数据
 * @returns {Object} - 响应结果
 */
function webhook(data) {
    try {
        console.log("收到同步请求: " + JSON.stringify(data));
        
        // 获取当前活动表格
        var sheet = Application.ActiveSheet;
        if (!sheet) {
            return {
                code: -1,
                success: false,
                message: "无法获取当前表格"
            };
        }
        
        // 获取传入的数据
        var rows = data.data;
        var syncTime = data.sync_time;
        var totalRows = data.total_rows;
        
        if (!rows || !Array.isArray(rows) || rows.length === 0) {
            return {
                code: -1,
                success: false,
                message: "没有数据需要同步"
            };
        }
        
        console.log("同步时间: " + syncTime);
        console.log("数据行数: " + totalRows);
        
        // 清空现有数据（保留表头）
        var usedRange = sheet.UsedRange;
        var lastRow = usedRange.Rows.Count;
        
        if (lastRow > 1) {
            // 清除 A2 到最后一行的数据
            var clearRange = sheet.Range("A2:E" + lastRow);
            clearRange.Clear();
            console.log("已清空旧数据");
        }
        
        // 写入新数据
        var dataRowCount = 0;
        for (var i = 0; i < rows.length; i++) {
            var row = rows[i];
            if (!Array.isArray(row)) {
                continue;
            }
            
            // 写入每一列
            for (var j = 0; j < row.length; j++) {
                sheet.Cells(i + 1, j + 1).Value = row[j];
            }
            dataRowCount++;
        }
        
        // 自动调整列宽
        try {
            sheet.Columns("A:E").AutoFit();
        } catch (e) {
            console.log("自动调整列宽失败: " + e.message);
        }
        
        console.log("同步完成，写入 " + dataRowCount + " 行数据");
        
        return {
            code: 0,
            success: true,
            message: "数据同步成功",
            rows_written: dataRowCount,
            sync_time: syncTime
        };
        
    } catch (error) {
        console.error("同步失败: " + error.message);
        return {
            code: -1,
            success: false,
            message: "同步失败: " + error.message
        };
    }
}

/**
 * 测试函数 - 在 AirScript 编辑器中运行此函数测试
 */
function test() {
    var testData = {
        action: "sync_data",
        sync_time: "2025-01-12 10:30:00",
        total_rows: 3,
        data: [
            ["日期", "部门", "姓名", "电话", "记录时间"],
            ["2025-01-10", "技术部", "张三", "13800138000", "2025-01-10 09:00:00"],
            ["2025-01-10", "销售部", "李四", "13900139000", "2025-01-10 09:30:00"],
            ["2025-01-11", "技术部", "王五", "13700137000", "2025-01-11 08:45:00"]
        ]
    };
    
    var result = webhook(testData);
    console.log("测试结果: " + JSON.stringify(result));
}
