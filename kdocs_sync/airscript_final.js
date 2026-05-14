/**
 * 签到数据同步 - AirScript Webhook 脚本 (最终版)
 * 语言: JavaScript (不是 Python!)
 * 入口函数: sync_task
 */

function sync_task(data) {
    try {
        // 获取当前活动表格
        var sheet = Application.ActiveSheet;
        
        // 如果无法获取活动表格，尝试获取第一个表格
        if (!sheet) {
            sheet = Application.Sheets.Item(1);
        }
        
        if (!sheet) {
            return {
                code: -1,
                success: false,
                msg: "无法获取表格"
            };
        }
        
        // 获取数据
        var rows = data.data;
        if (!rows || rows.length === 0) {
            return {
                code: -1,
                success: false,
                msg: "没有数据"
            };
        }
        
        // 写入数据到表格
        for (var i = 0; i < rows.length; i++) {
            var row = rows[i];
            for (var j = 0; j < row.length; j++) {
                sheet.Cells(i + 1, j + 1).Value2 = row[j];
            }
        }
        
        return {
            code: 0,
            success: true,
            msg: "同步成功",
            rows: rows.length
        };
        
    } catch (e) {
        return {
            code: -1,
            success: false,
            msg: "错误: " + e.message
        };
    }
}

// 测试函数 - 在 AirScript 编辑器中点击"运行"测试
function test() {
    var testData = {
        data: [
            ["日期", "部门", "姓名", "电话", "记录时间"],
            ["2025-01-12", "技术部", "张三", "13800138000", "09:00"],
            ["2025-01-12", "销售部", "李四", "13900139000", "09:30"]
        ]
    };
    
    var result = sync_task(testData);
    console.log(JSON.stringify(result));
}
