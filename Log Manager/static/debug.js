// 调试脚本
console.log('Debug script loaded');

// 检查页面元素
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, checking elements...');
    
    // 检查按钮
    const buttons = ['refreshBtn', 'exportBtn', 'sshSessionsBtn', 'httpSessionsBtn', 'mysqlSessionsBtn', 'pop3SessionsBtn'];
    buttons.forEach(btnId => {
        const btn = document.getElementById(btnId);
        if (btn) {
            console.log(`✓ Button ${btnId} found`);
        } else {
            console.error(`✗ Button ${btnId} not found`);
        }
    });
    
    // 检查图表容器
    const charts = ['sessionsTrendChart', 'serviceDistributionChart', 'attackTypesChart', 'geoDistributionChart'];
    charts.forEach(chartId => {
        const chart = document.getElementById(chartId);
        if (chart) {
            console.log(`✓ Chart ${chartId} found`);
        } else {
            console.error(`✗ Chart ${chartId} not found`);
        }
    });
    
    // 检查表格
    const tables = ['ssh-sessions-table', 'http-sessions-table', 'mysql-sessions-table', 'pop3-sessions-table'];
    tables.forEach(tableId => {
        const table = document.getElementById(tableId);
        if (table) {
            console.log(`✓ Table ${tableId} found`);
        } else {
            console.error(`✗ Table ${tableId} not found`);
        }
    });
    
    // 检查CSS和JS文件加载
    const styleSheets = Array.from(document.styleSheets);
    console.log('Loaded stylesheets:', styleSheets.map(sheet => sheet.href || 'inline'));
    
    // 检查外部库
    if (typeof Chart !== 'undefined') {
        console.log('✓ Chart.js loaded');
    } else {
        console.error('✗ Chart.js not loaded');
    }
    
    if (typeof echarts !== 'undefined') {
        console.log('✓ ECharts loaded');
    } else {
        console.error('✗ ECharts not loaded');
    }
    
    // 测试API连接
    testAPI();
});

// 测试API连接
async function testAPI() {
    console.log('Testing API connections...');
    
    try {
        const response = await fetch('http://127.0.0.1:5000/api/overview-stats');
        if (response.ok) {
            const data = await response.json();
            console.log('✓ API connection successful:', data);
        } else {
            console.error('✗ API connection failed:', response.status);
        }
    } catch (error) {
        console.error('✗ API connection error:', error);
    }
}

// 添加全局错误处理
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    console.error('Error details:', {
        message: e.message,
        filename: e.filename,
        lineno: e.lineno,
        colno: e.colno
    });
});

// 添加未处理的Promise错误处理
window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
}); 