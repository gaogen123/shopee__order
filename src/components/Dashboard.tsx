import { TrendingUp, TrendingDown, ShoppingBag, DollarSign, Package, AlertCircle, RefreshCw, ChevronRight } from 'lucide-react';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useState, useEffect } from 'react';
import { flushSync } from 'react-dom';
import { SiteShopSelector } from './SiteShopSelector';
import { Pagination } from './Pagination';

// API Response Types
interface DashboardStats {
    orders: {
        total: number;
        to_ship: number;
        shipping: number;
        completed: number;
        cancelled: number;
        cost_entered: number;
        cost_not_entered: number;
    };
    financials: {
        sales: number;
        revenue?: number;
        revenue_rmb?: number;
        cost: number;
        profit: number;
        margin: number;
    };
    history: {
        date: string;
        sales: number;
        revenue: number;
        cost: number;
        profit: number;
    }[];
}

interface RecentOrder {
    order_sn: string;
    order_status: string;
    buyer_username: string;
    total_amount: number;
    create_time: number;
    shop_id: number;
    item_list: any[];
}

interface DashboardProps {
    onViewOrder?: (order: { orderNumber: string, shopId: string, siteId: string }) => void;
}

export function Dashboard({ onViewOrder }: DashboardProps) {
    const [selectedSite, setSelectedSite] = useState('all');
    const [selectedStore, setSelectedStore] = useState('all');
    const [selectedStatus, setSelectedStatus] = useState('all');
    // Default to last 30 days
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);

    const [startDate, setStartDate] = useState(thirtyDaysAgo.toISOString().split('T')[0]);
    const [endDate, setEndDate] = useState(today.toISOString().split('T')[0]);

    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [recentOrders, setRecentOrders] = useState<RecentOrder[]>([]);

    const [visibleSeries, setVisibleSeries] = useState<{ [key: string]: boolean }>({
        "销售额": true,
        "收入": true,
        "成本": true,
        "利润": true
    });

    const [loading, setLoading] = useState(false);

    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const [totalOrders, setTotalOrders] = useState(0);
    const itemsPerPage = 10;

    // Dynamic Sites/Shops
    const [sites, setSites] = useState<{ value: string, label: string }[]>([]);
    const [shops, setShops] = useState<{ value: string, label: string, siteId: string }[]>([]);

    useEffect(() => {
        // Fetch sites and shops
        fetch('http://localhost:9000/api/shops')
            .then(res => res.json())
            .then(data => {
                setSites(data.sites || []);
                setShops(data.shops || []);
            })
            .catch(err => console.error("Failed to fetch shops", err));
    }, []);

    const fetchStats = async () => {
        setLoading(true);
        try {
            const [startY, startM, startD] = startDate.split('-').map(Number);
            const startTs = new Date(startY, startM - 1, startD).getTime() / 1000;

            const [endY, endM, endD] = endDate.split('-').map(Number);
            const endTs = new Date(endY, endM - 1, endD).getTime() / 1000 + 86400; // include end date

            const params = new URLSearchParams({
                time_from: startTs.toString(),
                time_to: endTs.toString(),
                shop_id: selectedStore,
                site_id: selectedSite,
                status: selectedStatus
            });

            // 构建筛选参数
            const statsParams = new URLSearchParams({
                start_time: startTs.toString(),
                end_time: endTs.toString()
            });

            // 应用店铺筛选
            if (selectedStore !== 'all') {
                statsParams.append('shop_id', parseInt(selectedStore));
            }

            // 应用站点筛选
            if (selectedSite !== 'all') {
                statsParams.append('site_id', selectedSite);
            }

            // 应用状态筛选
            if (selectedStatus !== 'all') {
                statsParams.append('status', selectedStatus);
            }

            // 获取订单统计
            const statsRes = await fetch(`http://localhost:9000/api/orders/stats?${statsParams.toString()}&_t=${new Date().getTime()}`);
            let statsData = null;
            if (statsRes.ok) {
                statsData = await statsRes.json();
            }

            // 获取财务统计
            const financialsRes = await fetch(`http://localhost:9000/api/dashboard/financials?${statsParams.toString()}&_t=${new Date().getTime()}`);
            let financialsData = null;
            if (financialsRes.ok) {
                financialsData = await financialsRes.json();
            }

            // 合并数据
            if (statsData || financialsData) {
                const newStats = {
                    orders: {
                        total: statsData?.total || 0,
                        // 直接使用Shopee状态，不进行映射
                        UNPAID: statsData?.status_counts?.UNPAID || 0,
                        READY_TO_SHIP: statsData?.status_counts?.READY_TO_SHIP || 0,
                        PROCESSED: statsData?.status_counts?.PROCESSED || 0,
                        RETRY_SHIP: statsData?.status_counts?.RETRY_SHIP || 0,
                        SHIPPED: statsData?.status_counts?.SHIPPED || 0,
                        TO_CONFIRM_RECEIVE: statsData?.status_counts?.TO_CONFIRM_RECEIVE || 0,
                        COMPLETED: statsData?.status_counts?.COMPLETED || 0,
                        IN_CANCEL: statsData?.status_counts?.IN_CANCEL || 0,
                        CANCELLED: statsData?.status_counts?.CANCELLED || 0,
                        TO_RETURN: statsData?.status_counts?.TO_RETURN || 0,
                        cost_entered: financialsData?.summary?.orders_with_cost || 0,
                        cost_not_entered: (financialsData?.summary?.total_orders || 0) - (financialsData?.summary?.orders_with_cost || 0)
                    },
                    financials: {
                        sales: financialsData?.financials?.sales || 0,
                        revenue: financialsData?.financials?.revenue || 0,
                        revenue_rmb: financialsData?.financials?.revenue_rmb || 0,
                        cost: financialsData?.financials?.cost || 0,
                        profit: financialsData?.financials?.profit || 0,
                        margin: financialsData?.financials?.margin || 0
                    },
                    history: financialsData?.history || []
                };
                flushSync(() => {
                    setStats(newStats);
                });
            } else {
                // 如果都没有数据，设置默认空状态
                setStats({
                    orders: {
                        total: 0,
                        UNPAID: 0,
                        READY_TO_SHIP: 0,
                        PROCESSED: 0,
                        RETRY_SHIP: 0,
                        SHIPPED: 0,
                        TO_CONFIRM_RECEIVE: 0,
                        COMPLETED: 0,
                        IN_CANCEL: 0,
                        CANCELLED: 0,
                        TO_RETURN: 0,
                        cost_entered: 0,
                        cost_not_entered: 0
                    },
                    financials: {
                        sales: 0,
                        cost: 0,
                        profit: 0,
                        margin: 0
                    },
                    history: []
                });
            }

            // Fetch Orders
            fetchRecentOrders();

        } catch (error) {
            console.error("Failed to fetch dashboard stats", error);
        } finally {
            setLoading(false);
        }
    };

    const fetchRecentOrders = async () => {
        try {
            const [startY, startM, startD] = startDate.split('-').map(Number);
            const startTs = new Date(startY, startM - 1, startD).getTime() / 1000;

            const [endY, endM, endD] = endDate.split('-').map(Number);
            const endTs = new Date(endY, endM - 1, endD).getTime() / 1000 + 86400;

            const orderParams = new URLSearchParams({
                page: currentPage.toString(),
                limit: itemsPerPage.toString()
            });
            if (startTs) orderParams.append('time_from', startTs.toString());
            if (endTs) orderParams.append('time_to', endTs.toString());
            if (selectedStore !== 'all') orderParams.append('shop_id', selectedStore);
            if (selectedSite !== 'all') orderParams.append('site_id', selectedSite);
            if (selectedStatus !== 'all') orderParams.append('status', selectedStatus);

            const ordersRes = await fetch(`http://localhost:9000/api/orders?${orderParams}`);
            if (ordersRes.ok) {
                const ordersData = await ordersRes.json();

                const orders = ordersData.orders || [];

                // Use exchange rate from backend directly
                const ordersWithRate = orders.map((o: any) => ({
                    ...o,
                    exchangeRate: o.exchange_rate || 1
                }));

                setRecentOrders(ordersWithRate);
                setTotalOrders(ordersData.total || 0);
            }
        } catch (error) {
            console.error("Failed to fetch recent orders", error);
        }
    };

    // Trigger stats fetch on filters change
    useEffect(() => {
        setCurrentPage(1); // Reset page on filter change
        fetchStats();
    }, [startDate, endDate, selectedStore, selectedSite, selectedStatus]);

    // Trigger orders fetch on page change or filters change
    useEffect(() => {
        fetchRecentOrders();
    }, [currentPage, startDate, endDate, selectedStore, selectedSite, selectedStatus]);


    // Format currency - 显示当地货币
    const formatCurrency = (val: number) => {
        // 主要使用巴西雷亚尔显示，因为当前数据主要是巴西的
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
    };

    const orderStats = [
        {
            title: '总订单数',
            value: stats?.orders?.total || 0,
            icon: ShoppingBag,
            color: 'blue'
        },
        {
            title: '未支付',
            value: stats?.orders?.UNPAID || 0,
            icon: Package,
            color: 'orange'
        },
        {
            title: '准备发货',
            value: stats?.orders?.READY_TO_SHIP || 0,
            icon: TrendingUp,
            color: 'purple'
        },
        {
            title: '已处理',
            value: stats?.orders?.PROCESSED || 0,
            icon: AlertCircle,
            color: 'green'
        },
        {
            title: '重试发货',
            value: stats?.orders?.RETRY_SHIP || 0,
            icon: AlertCircle,
            color: 'red'
        },
        {
            title: '已发货',
            value: stats?.orders?.SHIPPED || 0,
            icon: TrendingUp,
            color: 'blue'
        },
        {
            title: '待确认收货',
            value: stats?.orders?.TO_CONFIRM_RECEIVE || 0,
            icon: AlertCircle,
            color: 'orange'
        },
        {
            title: '已完成',
            value: stats?.orders?.COMPLETED || 0,
            icon: AlertCircle,
            color: 'green'
        },
        {
            title: '取消中',
            value: stats?.orders?.IN_CANCEL || 0,
            icon: AlertCircle,
            color: 'red'
        },
        {
            title: '已取消',
            value: stats?.orders?.CANCELLED || 0,
            icon: AlertCircle,
            color: 'red'
        },
        {
            title: '退货中',
            value: stats?.orders?.TO_RETURN || 0,
            icon: AlertCircle,
            color: 'red'
        }
    ];

    const financialStats = [
        {
            title: '总销售额',
            value: formatCurrency(stats?.financials?.sales || 0),
            icon: DollarSign,
            color: 'green'
        },
        {
            title: '总收入',
            value: formatCurrency(stats?.financials?.revenue || 0),
            icon: DollarSign,
            color: 'green'
        },
        {
            title: '总成本',
            // 总成本显示为人民币（用户录入成本以人民币计）
            value: `¥${(stats?.financials?.cost || 0).toFixed(2)}`,
            icon: TrendingUp,
            color: 'red'
        },
        {
            title: '总利润',
            value: `¥${(stats?.financials?.profit || 0).toFixed(2)}`,
            icon: TrendingUp,
            color: 'blue'
        },
        {
            title: '利润率',
            value: `${(stats?.financials?.margin || 0).toFixed(1)}%`,
            icon: TrendingUp,
            color: 'purple'
        }
    ];

    // Real Chart Data from Backend History
    // Real Chart Data from Backend History
    const chartData = (stats?.history || []).map(item => ({
        date: item.date.substring(5), // MM-DD
        "销售额": item.sales,
        "收入": item.revenue || 0,
        "成本": item.cost,
        "利润": item.profit
    }));

    const handleLegendClick = (e: any) => {
        const { dataKey } = e;
        setVisibleSeries(prev => ({
            ...prev,
            [dataKey]: !prev[dataKey]
        }));
    };

    // Derived from cancelled vs total (Mock specific status breakdown)
    // Real Status Breakdown
    const costStatusData = [
        { name: '已录入', value: stats?.orders?.cost_entered || 0, color: '#22c55e' },
        { name: '未录入', value: stats?.orders?.cost_not_entered || 0, color: '#ef4444' }
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

    const getStatusInfo = (status: string) => {
        const map: any = {
            'UNPAID': { label: '待付款', bg: 'bg-orange-100', text: 'text-orange-600' },
            'READY_TO_SHIP': { label: '待出货', bg: 'bg-blue-100', text: 'text-blue-600' },
            'SHIPPED': { label: '运送中', bg: 'bg-purple-100', text: 'text-purple-600' },
            'TO_CONFIRM_RECEIVE': { label: '待确认收货', bg: 'bg-orange-100', text: 'text-orange-600' },
            'COMPLETED': { label: '已完成', bg: 'bg-green-100', text: 'text-green-600' },
            'CANCELLED': { label: '已取消', bg: 'bg-red-100', text: 'text-red-600' },
            'TO_RETURN': { label: '退货/退款', bg: 'bg-red-50', text: 'text-red-500' }
        };
        return map[status] || { label: status, bg: 'bg-gray-100', text: 'text-gray-600' };
    };

    const statusOptions = [
        { value: 'all', label: '全部状态' },
        { value: 'UNPAID', label: '未支付' },
        { value: 'READY_TO_SHIP', label: '准备发货' },
        { value: 'PROCESSED', label: '已处理' },
        { value: 'RETRY_SHIP', label: '重试发货' },
        { value: 'SHIPPED', label: '已发货' },
        { value: 'TO_CONFIRM_RECEIVE', label: '待确认收货' },
        { value: 'COMPLETED', label: '已完成' },
        { value: 'IN_CANCEL', label: '取消中' },
        { value: 'CANCELLED', label: '已取消' },
        { value: 'TO_RETURN', label: '退货中' },
    ];

    return (
        <div className="p-6 space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-xl font-semibold text-gray-900">数据概览</h1>
                    <p className="text-sm text-gray-500 mt-1">实时查看订单和成本利润情况</p>
                </div>
                <button
                    onClick={fetchStats}
                    disabled={loading}
                    className="p-2 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors"
                >
                    <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
                </button>
            </div>

            {/* 筛选区域 */}
            <div className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex flex-col md:flex-row gap-4">
                    {/* Site & Shop Selector */}
                    <div className="flex-1">
                        <SiteShopSelector
                            selectedSite={selectedSite}
                            selectedShop={selectedStore}
                            onSiteChange={setSelectedSite}
                            onShopChange={setSelectedStore}
                            sites={sites}
                            shops={shops}
                        />
                    </div>

                    {/* Status Selector */}
                    <div className="min-w-[120px]">
                        <select
                            value={selectedStatus}
                            onChange={(e) => setSelectedStatus(e.target.value)}
                            className="w-full h-10 px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            {statusOptions.map(option => (
                                <option key={option.value} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Date Range */}
                    <div className="flex gap-4">
                        <div>
                            <input
                                type="date"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <div>
                            <input
                                type="date"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* 订单状态卡片 */}
            <div>
                <h2 className="text-base font-semibold text-gray-900 mb-4">订单情况</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
                    {orderStats.map((stat, index) => {
                        const Icon = stat.icon;
                        return (
                            <div key={index} className="bg-white rounded-lg border border-gray-200 p-5">
                                <div className="flex items-center justify-between">
                                    <div className="flex-1">
                                        <p className="text-sm text-gray-600">{stat.title}</p>
                                        <div className="flex items-baseline gap-2 mt-2">
                                            <span className="text-2xl font-semibold text-gray-900">{stat.value}</span>
                                        </div>
                                        {(stat as any).subtitle && (
                                            <p className="text-xs text-gray-500 mt-1">{(stat as any).subtitle}</p>
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
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                    {financialStats.map((stat, index) => {
                        const Icon = stat.icon;
                        return (
                            <div key={index} className="bg-white rounded-lg border border-gray-200 p-5">
                                <div className="flex items-center justify-between">
                                    <div className="flex-1">
                                        <p className="text-sm text-gray-600">{stat.title}</p>
                                        <div className="flex items-baseline gap-2 mt-2">
                                            <span className="text-2xl font-semibold text-gray-900">{stat.value}</span>
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
                <div className="lg:col-span-2 bg-white rounded-lg border border-gray-200 p-6">
                    <div className="flex justify-between mb-4">
                        <h3 className="text-base font-semibold text-gray-900">销售与利润趋势</h3>
                    </div>
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                            <YAxis tick={{ fontSize: 12 }} />
                            <Tooltip />
                            <Legend onClick={handleLegendClick} cursor="pointer" />
                            <Line
                                type="monotone"
                                dataKey="销售额"
                                stroke="#3b82f6"
                                strokeWidth={2}
                                hide={!visibleSeries["销售额"]}
                                dot={{ r: 4 }}
                                activeDot={{ r: 6 }}
                            />
                            <Line
                                type="monotone"
                                dataKey="收入"
                                stroke="#10b981"
                                strokeWidth={2}
                                hide={!visibleSeries["收入"]}
                                dot={{ r: 4 }}
                                activeDot={{ r: 6 }}
                            />
                            <Line
                                type="monotone"
                                dataKey="成本"
                                stroke="#ef4444"
                                strokeWidth={2}
                                hide={!visibleSeries["成本"]}
                                dot={{ r: 4 }}
                                activeDot={{ r: 6 }}
                            />
                            <Line
                                type="monotone"
                                dataKey="利润"
                                stroke="#8b5cf6"
                                strokeWidth={2}
                                hide={!visibleSeries["利润"]}
                                dot={{ r: 4 }}
                                activeDot={{ r: 6 }}
                            />
                        </LineChart>
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

            {/* Recent Orders Section */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-base font-semibold text-gray-900">订单详情</h3>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-gray-50 text-gray-500 font-medium">
                            <tr>
                                <th className="px-4 py-3 rounded-l-lg">订单号</th>
                                <th className="px-4 py-3">订单日期</th>
                                <th className="px-4 py-3 text-right">商品总额</th>
                                <th className="px-4 py-3 text-right">预估运费</th>
                                <th className="px-4 py-3 text-right">费用</th>
                                <th className="px-4 py-3 text-right">预估收入</th>
                                <th className="px-4 py-3 text-right">总成本</th>
                                <th className="px-4 py-3 text-right">利润</th>
                                <th className="px-4 py-3">状态</th>
                                <th className="px-4 py-3 rounded-r-lg text-right">操作</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {recentOrders.length > 0 ? (
                                recentOrders.map(order => {
                                    const status = getStatusInfo(order.order_status);

                                    const currency = order.currency || 'BRL';
                                    const CURRENCY_SYMBOLS: { [key: string]: string } = {
                                        'BRL': 'R$', 'USD': '$', 'SGD': 'S$', 'MYR': 'RM',
                                        'PHP': '₱', 'IDR': 'Rp', 'THB': '฿', 'VND': '₫', 'TWD': 'NT$',
                                        'CNY': '¥'
                                    };
                                    const currencySymbol = CURRENCY_SYMBOLS[currency] || currency;

                                    // 计算商品总额 (用于显示)
                                    const itemList = order.item_list || [];
                                    const itemTotal = itemList.reduce((sum: number, item: any) =>
                                        sum + (item.model_discounted_price || 0) * (item.model_quantity_purchased || 0), 0
                                    );

                                    // 预估运费与费用 (用于显示)
                                    // 从 backend estimated_shipping_fee 取值 (它是净运费吗? 以前逻辑是 buyer_paid - actual + rebate)
                                    // 为保持一致性，如果 backend 有 estimated_shipping_fee，直接用?
                                    // 但 Dashboard 只有 order 对象。
                                    // 使用简单逻辑用于 Dashboard 展示，或者复用之前逻辑但不参与 Profit 计算

                                    const financials = order.financials || {};
                                    // 之前的逻辑: estimatedShipping = buyerPaid - actual + rebate
                                    const estimatedShippingFee = financials.actual_shipping_fee || 0;
                                    const buyerPaidShipping = financials.buyer_paid_shipping || 0;
                                    const shopeeShippingRebate = financials.shopee_shipping_rebate || 0;
                                    const estimatedShipping = buyerPaidShipping - estimatedShippingFee + shopeeShippingRebate;

                                    const totalFees = financials.total_fees || 0;

                                    // 直接使用后端返回的预估收入、总成本和利润
                                    // 确保字段存在，如果数据库未更新这些字段（旧数据），可能为 null 或 0
                                    // 但根据 user request，我们直接取用

                                    const estimatedRevenue = order.estimated_revenue || 0;
                                    const cost = order.total_cost || 0;
                                    // total_cost 在数据库中存储的是 RMB
                                    const costIsRMB = true;
                                    const profit = order.estimated_profit || 0;

                                    // 本地显示货币 (用于收入列)
                                    // 注意：estimated_revenue 是原币种
                                    const revenueLocal = estimatedRevenue;

                                    return (
                                        <tr key={order.order_sn} className="hover:bg-gray-50 transition-colors">
                                            <td className="px-4 py-4">
                                                <span className="font-semibold text-gray-900">{order.order_sn}</span>
                                            </td>
                                            <td className="px-4 py-4">
                                                <span className="text-gray-700">
                                                    {new Date(order.create_time * 1000).toLocaleDateString('zh-CN')}
                                                </span>
                                            </td>
                                            <td className="px-4 py-4 text-right font-medium text-gray-900">
                                                {currencySymbol}{itemTotal.toFixed(2)}
                                            </td>
                                            <td className="px-4 py-4 text-right font-medium text-blue-600">
                                                {currencySymbol}{estimatedShipping.toFixed(2)}
                                            </td>
                                            <td className="px-4 py-4 text-right font-medium text-red-600">
                                                {currencySymbol}{totalFees.toFixed(2)}
                                            </td>
                                            <td className="px-4 py-4 text-right font-medium text-green-600">
                                                {currencySymbol}{revenueLocal.toFixed(2)}
                                            </td>
                                            <td className="px-4 py-4 text-right font-medium text-orange-600">
                                                {costIsRMB ? '¥' : currencySymbol}{cost.toFixed(2)}
                                            </td>
                                            <td className="px-4 py-4 text-right font-medium">
                                                <span className={profit >= 0 ? 'text-green-600' : 'text-red-600'}>
                                                    {costIsRMB ? '¥' : currencySymbol}{profit.toFixed(2)}
                                                </span>
                                            </td>
                                            <td className="px-4 py-4">
                                                <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${status.bg} ${status.text}`}>
                                                    {status.label}
                                                </span>
                                            </td>
                                            <td className="px-4 py-4 text-right">
                                                <button
                                                    onClick={() => onViewOrder && onViewOrder({
                                                        orderNumber: order.order_sn,
                                                        shopId: String(order.shop_id),
                                                        siteId: shops.find(s => s.value === String(order.shop_id))?.siteId || ''
                                                    })}
                                                    className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 font-medium"
                                                >
                                                    查看
                                                    <ChevronRight className="w-4 h-4" />
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })
                            ) : (
                                <tr>
                                    <td colSpan={10} className="px-4 py-8 text-center text-gray-500">
                                        暂无订单数据
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                {totalOrders > itemsPerPage && (
                    <div className="mt-4 border-t border-gray-100 pt-4">
                        <Pagination
                            currentPage={currentPage}
                            totalPages={Math.ceil(totalOrders / itemsPerPage)}
                            totalItems={totalOrders}
                            itemsPerPage={itemsPerPage}
                            onPageChange={setCurrentPage}
                        />
                    </div>
                )}
            </div>
        </div>
    );
}
