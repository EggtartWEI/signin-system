// 最简单的测试 - 直接在 AirScript 编辑器中运行
function test() {
    // 获取第一个工作表
    var sheet = Application.Sheets.Item(1);
    
    // 在 A1 单元格写入数据
    sheet.Cells(1, 1).Value = "Hello";
    sheet.Cells(1, 2).Value = "World";
    sheet.Cells(2, 1).Value = new Date().toString();
    
    console.log("写入成功");
}

// 运行测试
test();
