// 调试数据加载的脚本
console.log('=== 调试数据加载 ===');

// 测试API调用
async function debugDataLoading() {
    const endpoints = [
        '/ssh_sessions',
        '/http_sessions', 
        '/mysql_sessions',
        '/pop3_sessions',
        '/api/overview-stats',
        '/api/chart-data'
    ];
    
    for (const endpoint of endpoints) {
        try {
            console.log(`\n--- 测试 ${endpoint} ---`);
            const response = await fetch(endpoint);
            const data = await response.json();
            console.log('状态码:', response.status);
            console.log('数据类型:', typeof data);
            console.log('数据长度:', Array.isArray(data) ? data.length : 'N/A');
            console.log('数据内容:', data);
        } catch (error) {
            console.error(`错误 ${endpoint}:`, error);
        }
    }
}

// 测试表格显示
function debugTableDisplay() {
    console.log('\n=== 调试表格显示 ===');
    
    const tables = document.querySelectorAll('.data-table');
    console.log('找到的表格数量:', tables.length);
    
    tables.forEach((table, index) => {
        console.log(`\n表格 ${index + 1}:`, table.id);
        console.log('显示状态:', table.style.display);
        console.log('行数:', table.querySelectorAll('tbody tr').length);
    });
}

// 测试按钮事件
function debugButtonEvents() {
    console.log('\n=== 调试按钮事件 ===');
    
    const buttons = document.querySelectorAll('.service-btn');
    console.log('服务按钮数量:', buttons.length);
    
    buttons.forEach((btn, index) => {
        console.log(`按钮 ${index + 1}:`, btn.textContent.trim());
        console.log('点击事件:', btn.onclick);
    });
}

// 运行调试
setTimeout(() => {
    debugDataLoading();
    debugTableDisplay();
    debugButtonEvents();
}, 2000); 