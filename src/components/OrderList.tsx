import { useState, useEffect } from 'react';
import { Search, MessageCircle, ChevronRight } from 'lucide-react';
import { DateRangePicker } from './DateRangePicker';

interface OrderSummary {
    order_sn: string;
    order_status: string;
    buyer_username: string;
    total_amount: number;
    currency: string;
    create_time: number;
    item_list: any[]; // items from raw_data
    shipping_carrier?: string;
    shipping_carrier_shipping_method?: string; // Sometimes carrier is here
}

interface OrderListProps {
    onSelectOrder: (orderSn: string) => void;
    onSync: (startDate: string, endDate: string) => void;
    syncing: boolean;
    refreshTrigger?: number;
}

export function OrderList({ onSelectOrder, onSync, syncing, refreshTrigger }: OrderListProps) {
    const [activeTab, setActiveTab] = useState('ALL');
    const [keyword, setKeyword] = useState('');
    const [orders, setOrders] = useState<OrderSummary[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(false);
    const [startDate, setStartDate] = useState(() => {
        const d = new Date();
        d.setDate(d.getDate() - 7); // 默认最近7天
        return d.toISOString().split('T')[0];
    });
    const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);

    // Tab definition matching Shopee standard somewhat
    const tabs = [
        { id: 'ALL', label: '全部' },
        { id: 'UNPAID', label: '待付款' },
        { id: 'READY_TO_SHIP', label: '待出货' },
        { id: 'SHIPPED', label: '运送中' },
        { id: 'COMPLETED', label: '已完成' },
        { id: 'CANCELLED', label: '退货/退款/取消' },
    ];

    const fetchOrders = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                page: page.toString(),
                limit: '20'
            });
            if (activeTab !== 'ALL') params.append('status', activeTab);
            if (keyword) params.append('keyword', keyword);

            const res = await fetch(`http://localhost:8000/api/orders?${params}`);
            const data = await res.json();

            setOrders(data.orders || []);
            setTotal(data.total || 0);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchOrders();
    }, [activeTab, page, refreshTrigger]);

    const handleSearch = () => {
        setPage(1);
        fetchOrders();
    }

    // Helper to format currency
    const fmtMoney = (val: number, currency = 'BRL') => {
        // Basic formatting
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: currency }).format(val);
    };

    // Status mapping
    const getStatusLabel = (status: string) => {
        const map: { [key: string]: string } = {
            'UNPAID': '待付款',
            'READY_TO_SHIP': '待出货',
            'PROCESSED': '已处理',
            'RETRY_SHIP': '待出货',
            'SHIPPED': '运送中',
            'COMPLETED': '已完成',
            'IN_CANCEL': '取消中',
            'CANCELLED': '已取消',
            'TO_RETURN': '退货/退款'
        };
        return map[status] || status;
    };

    return (
        <div className="max-w-7xl mx-auto p-6 relative">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-medium">我的订单</h1>

                {/* Sync Controls */}
                <div className="flex items-center gap-3">
                    <DateRangePicker
                        startDate={startDate}
                        endDate={endDate}
                        onChange={(s, e) => {
                            setStartDate(s);
                            setEndDate(e);
                        }}
                    />

                    <button
                        onClick={() => {
                            console.log("Triggering sync with:", startDate, endDate);
                            onSync(startDate, endDate);
                        }}
                        disabled={syncing}
                        className={`px-4 py-2 rounded text-sm font-medium transition-all shadow-sm h-[38px] ${syncing
                            ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                            : 'bg-orange-500 text-white hover:bg-orange-600 active:scale-95'
                            }`}
                    >
                        {syncing ? '正在同步...' : '同步订单'}
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b mb-6 overflow-x-auto">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        className={`px-6 py-3 text-sm font-medium whitespace-nowrap transition-colors relative ${activeTab === tab.id
                            ? 'text-orange-500 border-b-2 border-orange-500'
                            : 'text-gray-600 hover:text-orange-500'
                            }`}
                        onClick={() => { setActiveTab(tab.id); setPage(1); }}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Search & Filters */}
            <div className="bg-white p-4 rounded-lg shadow-sm mb-6 flex flex-wrap gap-4 items-center">
                <div className="flex bg-gray-100 rounded-md overflow-hidden border focus-within:ring-1 focus-within:ring-orange-500">
                    <div className="px-3 py-2 text-gray-500 bg-gray-50 border-r text-sm w-28 text-center flex items-center justify-between cursor-pointer">
                        订单编号 <ChevronRight className="w-3 h-3 rotate-90" />
                    </div>
                    <input
                        type="text"
                        className="px-4 py-2 bg-transparent focus:outline-none w-64 text-sm"
                        placeholder="订单编号"
                        value={keyword}
                        onChange={e => setKeyword(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSearch()}
                    />
                    <button onClick={handleSearch} className="px-4 text-gray-400 hover:text-gray-600">
                        <Search className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Count */}
            <div className="text-xl font-medium mb-4 text-gray-800">{total} 订单</div>

            {/* List Header */}
            <div className="bg-gray-100 p-3 rounded-t-lg grid grid-cols-12 gap-4 text-sm text-gray-500 font-medium">
                <div className="col-span-12 pl-2">商品</div>
            </div>

            {/* Orders */}
            <div className="space-y-4">
                {loading ? <div className="text-center py-10 text-gray-500">加载中...</div> : (
                    orders.map(order => (
                        <div key={order.order_sn} className="bg-white border rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow">
                            {/* Header */}
                            <div className="bg-gray-50 px-4 py-2 flex items-center justify-between border-b text-sm">
                                <div className="flex items-center gap-2">
                                    <div className="w-6 h-6 rounded-full bg-gray-300 overflow-hidden flex items-center justify-center text-xs text-white uppercase">
                                        {order.buyer_username.slice(0, 1)}
                                    </div>
                                    <span className="font-medium text-gray-900">{order.buyer_username}</span>
                                </div>
                                <div className="text-gray-500 flex items-center gap-4">
                                    <div className="flex items-center gap-2">
                                        <span>订单号: {order.order_sn}</span>
                                        <span className="px-2 py-0.5 bg-orange-100 text-orange-600 rounded text-xs font-medium">
                                            {getStatusLabel(order.order_status)}
                                        </span>
                                    </div>
                                    <div className="w-[1px] h-3 bg-gray-300 mx-1"></div>
                                    <button className="text-blue-500 hover:underline" onClick={() => onSelectOrder(order.order_sn)}>查看详情</button>
                                </div>
                            </div>

                            {/* Items Logic - We map items, or just first few if too many? For now map all */}
                            {(order.item_list || []).map((item: any, idx: number) => (
                                <div key={idx} className="p-4 grid grid-cols-12 gap-4 items-center border-b last:border-0 text-sm">
                                    {/* Product Column - Expanded to full width */}
                                    <div className="col-span-12 flex gap-3 cursor-pointer" onClick={() => onSelectOrder(order.order_sn)}>
                                        <div className="w-16 h-16 flex-shrink-0 border rounded overflow-hidden bg-gray-100">
                                            {item.image_info?.image_url && (
                                                <img src={item.image_info?.image_url} className="w-full h-full object-cover" alt="" />
                                            )}
                                        </div>
                                        <div>
                                            <div className="font-medium line-clamp-2 text-gray-800">{item.item_name}</div>
                                            <div className="text-gray-500 mt-1">{item.model_name ? `规格: ${item.model_name}` : ''}</div>
                                            <div className="mt-1 text-gray-600">x{item.model_quantity_purchased}</div>
                                        </div>
                                    </div>
                                </div>
                            ))}

                            {/* Empty Items Fallback if missing item_list in DB */}
                            {(!order.item_list || order.item_list.length === 0) && (
                                <div className="p-4 text-center text-gray-400">暂无商品信息的旧数据</div>
                            )}
                        </div>
                    ))
                )}
            </div>

            {/* Footer / Pagination */}
            <div className="flex justify-center mt-6 gap-4 items-center text-sm">
                <button
                    disabled={page === 1}
                    onClick={() => setPage(p => p - 1)}
                    className="px-4 py-2 border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    上一页
                </button>
                <div className="px-2">第 {page} 页</div>
                <button
                    disabled={orders.length < 20}
                    onClick={() => setPage(p => p + 1)}
                    className="px-4 py-2 border rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    下一页
                </button>
            </div>
        </div>
    );
}
