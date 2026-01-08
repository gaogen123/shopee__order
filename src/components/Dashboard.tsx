import { TrendingUp, TrendingDown, ShoppingBag, DollarSign, Package, AlertCircle } from 'lucide-react';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useState } from 'react';

export function Dashboard() {
    const [selectedSite, setSelectedSite] = useState('all');
    const [selectedStore, setSelectedStore] = useState('all');
    const [startDate, setStartDate] = useState('2025-12-30');
    const [endDate, setEndDate] = useState('2026-01-06');

    // 站点选项
    const sites = [
        { value: 'all', label: '全部站点' },
        { value: 'alibaba', label: 'Alibaba' },
        { value: 'temu', label: 'Temu' },
        { value: 'shopee', label: 'Shopee' },
        { value: 'lazada', label: 'Lazada' }
    ];

    // 店铺选项
    const stores = [
        { value: 'all', label: '全部店铺' },
        { value: 'store1', label: '旗舰店' },
        { value: 'store2', label: '专营店' },
        { value: 'store3', label: '海外店' }
    ];

    // 模拟数据
    const stats = [
        {
            title: '总订单数',
            value: '15',
            change: '+12.5%',
            trend: 'up',
            icon: ShoppingBag,
            color: 'blue'
        },
        {
            title: '待出货',
            value: '0',
            subtitle: '待付款: 0',
            icon: Package,
            color: 'orange'
        },
        {
            title: '运送中',
            value: '14',
            change: '+93.3%',
            trend: 'up',
            icon: TrendingUp,
            color: 'purple'
        },
        {
            title: '已完成',
            value: '0',
            subtitle: '退货/取消: 1',
            icon: AlertCircle,
            color: 'green'
        }
    ];

    const profitStats = [
        {
            title: '总销售额',
            value: '¥128,450',
            change: '+18.2%',
            trend: 'up',
            icon: DollarSign,
            color: 'green'
        },
        {
            title: '总成本',
            value: '¥85,620',
            change: '+15.8%',
            trend: 'up',
            icon: TrendingUp,
            color: 'red'
        },
        {
            title: '总利润',
            value: '¥42,830',
            change: '+23.5%',
            trend: 'up',
            icon: TrendingUp,
            color: 'blue'
        },
        {
            title: '利润率',
            value: '33.4%',
            change: '+2.1%',
            trend: 'up',
            icon: TrendingUp,
            color: 'purple'
        }
    ];

    const costStatusData = [
        { name: '已录入', value: 0, color: '#22c55e' },
        { name: '未录入', value: 15, color: '#ef4444' }
    ];

    const monthlyData = [
        { month: '7月', 销售额: 95000, 成本: 62000, 利润: 33000 },
        { month: '8月', 销售额: 102000, 成本: 68000, 利润: 34000 },
        { month: '9月', 销售额: 115000, 成本: 75000, 利润: 40000 },
        { month: '10月', 销售额: 108000, 成本: 71000, 利润: 37000 },
        { month: '11月', 销售额: 122000, 成本: 79000, 利润: 43000 },
        { month: '12月', 销售额: 128450, 成本: 85620, 利润: 42830 }
    ];

    const orderTrendData = [
        { date: '12-25', 订单数: 2 },
        { date: '12-26', 订单数: 3 },
        { date: '12-27', 订单数: 1 },
        { date: '12-28', 订单数: 4 },
        { date: '12-29', 订单数: 2 },
        { date: '12-30', 订单数: 3 },
        { date: '01-06', 订单数: 0 }
    ];

    const getColorClass = (color: string) => {
        const colors = {
            blue: 'bg-blue-50 text-blue-600',
            orange: 'bg-orange-50 text-orange-600',
            purple: 'bg-purple-50 text-purple-600',
            green: 'bg-green-50 text-green-600',
            red: 'bg-red-50 text-red-600'
        };
        return colors[color as keyof typeof colors] || colors.blue;
    };

    return (
        <div className="p-6 space-y-6">
            <div>
                <h1 className="text-xl font-semibold text-gray-900">数据概览</h1>
                <p className="text-sm text-gray-500 mt-1">实时查看订单和成本利润情况</p>
            </div>

            {/* 筛选区域 */}
            <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {/* 站点选择 */}
                    <div>
                        <label className="block text-sm text-gray-700 mb-2">站点</label>
                        <select
                            value={selectedSite}
                            onChange={(e) => setSelectedSite(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            {sites.map((site) => (
                                <option key={site.value} value={site.value}>
                                    {site.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* 店铺选择 */}
                    <div>
                        <label className="block text-sm text-gray-700 mb-2">店铺</label>
                        <select
                            value={selectedStore}
                            onChange={(e) => setSelectedStore(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            {stores.map((store) => (
                                <option key={store.value} value={store.value}>
                                    {store.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* 开始日期 */}
                    <div>
                        <label className="block text-sm text-gray-700 mb-2">开始日期</label>
                        <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    {/* 结束日期 */}
                    <div>
                        <label className="block text-sm text-gray-700 mb-2">结束日期</label>
                        <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                </div>
            </div>

            {/* 订单状态卡片 */}
            <div>
                <h2 className="text-base font-semibold text-gray-900 mb-4">订单情况</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {stats.map((stat, index) => {
                        const Icon = stat.icon;
                        return (
                            <div key={index} className="bg-white rounded-lg border border-gray-200 p-5">
                                <div className="flex items-center justify-between">
                                    <div className="flex-1">
                                        <p className="text-sm text-gray-600">{stat.title}</p>
                                        <div className="flex items-baseline gap-2 mt-2">
                                            <span className="text-2xl font-semibold text-gray-900">{stat.value}</span>
                                            {stat.change && (
                                                <span className={`text-xs ${stat.trend === 'up' ? 'text-green-600' : 'text-red-600'}`}>
                                                    {stat.change}
                                                </span>
                                            )}
                                        </div>
                                        {stat.subtitle && (
                                            <p className="text-xs text-gray-500 mt-1">{stat.subtitle}</p>
                                        )}
                                    </div>
                                    <div className={`p-3 rounded-lg ${getColorClass(stat.color)}`}>
                                        <Icon className="w-5 h-5" />
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* 成本利润卡片 */}
            <div>
                <h2 className="text-base font-semibold text-gray-900 mb-4">成本与利润</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {profitStats.map((stat, index) => {
                        const Icon = stat.icon;
                        return (
                            <div key={index} className="bg-white rounded-lg border border-gray-200 p-5">
                                <div className="flex items-center justify-between">
                                    <div className="flex-1">
                                        <p className="text-sm text-gray-600">{stat.title}</p>
                                        <div className="flex items-baseline gap-2 mt-2">
                                            <span className="text-2xl font-semibold text-gray-900">{stat.value}</span>
                                            {stat.change && (
                                                <span className={`text-xs flex items-center gap-0.5 ${stat.trend === 'up' ? 'text-green-600' : 'text-red-600'}`}>
                                                    {stat.trend === 'up' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                                                    {stat.change}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <div className={`p-3 rounded-lg ${getColorClass(stat.color)}`}>
                                        <Icon className="w-5 h-5" />
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* 图表区域 */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 月度趋势 */}
                <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 p-6">
                    <h3 className="text-base font-semibold text-gray-900 mb-4">月度销售与利润趋势</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={monthlyData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                            <YAxis tick={{ fontSize: 12 }} />
                            <Tooltip />
                            <Legend />
                            <Bar dataKey="销售额" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="成本" fill="#ef4444" radius={[4, 4, 0, 0]} />
                            <Bar dataKey="利润" fill="#22c55e" radius={[4, 4, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* 成本录入状态 */}
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                    <h3 className="text-base font-semibold text-gray-900 mb-4">成本录入状态</h3>
                    <div className="flex flex-col items-center justify-center">
                        <ResponsiveContainer width="100%" height={200}>
                            <PieChart>
                                <Pie
                                    data={costStatusData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {costStatusData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                        <div className="mt-4 space-y-2 w-full">
                            {costStatusData.map((item, index) => (
                                <div key={index} className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                                        <span className="text-sm text-gray-600">{item.name}</span>
                                    </div>
                                    <span className="text-sm font-semibold text-gray-900">{item.value}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* 订单趋势 */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h3 className="text-base font-semibold text-gray-900 mb-4">近7日订单趋势</h3>
                <ResponsiveContainer width="100%" height={250}>
                    <LineChart data={orderTrendData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="订单数" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 4 }} />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
