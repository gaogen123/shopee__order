import { useState, useEffect } from 'react';
import { Search, ChevronDown, RefreshCw, MoreHorizontal, Sparkles, Save, Calculator } from 'lucide-react';
import { DateRangePicker } from './DateRangePicker';
import { SiteShopSelector } from './SiteShopSelector';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Checkbox } from './ui/checkbox';
import { cn } from './ui/utils';

interface OrderSummary {
    order_sn: string;
    order_status: string;
    buyer_username: string;
    total_amount: number;
    currency: string;
    create_time: number;
    item_list: Array<{
        item_id: number;
        order_item_id?: number;
        item_name: string;
        image_info?: { image_url: string };
        model_id?: number;
        model_name?: string;
        model_sku?: string;
        model_quantity_purchased: number;
        model_discounted_price?: number;
        purchase_cost?: number;
        domestic_shipping_cost?: number;
    }>;
    shop_id?: number;
    shipping_carrier?: string;
    purchase_cost?: number;
    domestic_shipping_cost?: number;
    total_cost?: number;
    escrow_info?: any;
    financials?: {
        total_fees: number;
        order_income: number;
        commission_fee: number;
        service_fee: number;
        seller_transaction_fee: number;
        buyer_paid_shipping: number;
        shopee_shipping_rebate: number;
        actual_shipping_fee: number;
    };
}

interface OrderListProps {
    onSelectOrder: (orderSn: string) => void;
    onSync: (startDate: string, endDate: string) => void;
    onSyncSelected: (orderSns: string[]) => void;
    onMappingSaved?: () => void;
    syncing: boolean;
    syncTask: any;
    refreshTrigger?: number;
}

interface CostMapping {
    id: number;
    siteId: string;
    shopId: string;
    productId: string;
    productName: string;
    sku: string;
    purchaseCost: number;
    domesticShippingCost: number;
    createdAt: number;
}

interface Shop {
    value: string;
    label: string;
    siteId: string;
    region: string;
}

interface Site {
    value: string;
    label: string;
}

export function OrderList({ onSelectOrder, onSync, onSyncSelected, onMappingSaved, syncing, syncTask, refreshTrigger }: OrderListProps) {
    const [activeTab, setActiveTab] = useState('ALL');
    const [keyword, setKeyword] = useState('');
    const [orders, setOrders] = useState<OrderSummary[]>([]);
    const [mappings, setMappings] = useState<CostMapping[]>([]);
    const [shops, setShops] = useState<Shop[]>([]);
    const [sites, setSites] = useState<Site[]>([]);

    // Filter States
    const [selectedSite, setSelectedSite] = useState('all');
    const [selectedShop, setSelectedShop] = useState('all');

    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(false);
    const [selectedSns, setSelectedSns] = useState<Set<string>>(new Set());

    // Default to last 30 days (Consistent with Dashboard)
    const [startDate, setStartDate] = useState(() => {
        const d = new Date();
        d.setDate(d.getDate() - 30);
        return d.toISOString().split('T')[0];
    });
    const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);

    const tabs = [
        { id: 'ALL', label: '全部', count: total },
        { id: 'UNPAID', label: '待付款', count: 5 },
        { id: 'READY_TO_SHIP', label: '待出货', count: 3 },
        { id: 'SHIPPED', label: '运送中', count: 2 },
        { id: 'COMPLETED', label: '已完成', count: 5 },
        { id: 'CANCELLED', label: '退货/取消', count: 0 },
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

            // Date Filtering
            if (startDate) {
                const [y, m, d] = startDate.split('-').map(Number);
                const startTs = Math.floor(new Date(y, m - 1, d).getTime() / 1000);
                params.append('time_from', startTs.toString());
            }
            if (endDate) {
                const [y, m, d] = endDate.split('-').map(Number);
                // Include the entire end day (add 24 hours to the start of the end day)
                const endTs = Math.floor(new Date(y, m - 1, d).getTime() / 1000) + 86400;
                params.append('time_to', endTs.toString());
            }

            // Site/Shop Filtering
            if (selectedSite !== 'all') params.append('site_id', selectedSite);
            if (selectedShop !== 'all') params.append('shop_id', selectedShop);

            const res = await fetch(`http://localhost:9000/api/orders?${params}`);
            const data = await res.json();

            setOrders(data.orders || []);
            setTotal(data.total || 0);
            setSelectedSns(new Set());
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const fetchMappingsAndShops = async () => {
            try {
                const [mappingsRes, shopsRes] = await Promise.all([
                    fetch('http://localhost:9000/api/mappings'),
                    fetch('http://localhost:9000/api/shops')
                ]);
                const mappingsData = await mappingsRes.json();
                const shopsData = await shopsRes.json();
                setMappings(mappingsData);
                setShops(shopsData.shops || []);
                setSites(shopsData.sites || []);
            } catch (e) {
                console.error("Failed to load mappings or shops", e);
            }
        };
        fetchMappingsAndShops();
    }, []); // Only load once

    // Re-fetch orders when filters change
    useEffect(() => {
        fetchOrders();
    }, [activeTab, page, refreshTrigger, startDate, endDate, selectedSite, selectedShop]);

    const handleMappingSaved = () => {
        // Refresh mappings
        fetch('http://localhost:9000/api/mappings')
            .then(res => res.json())
            .then(data => setMappings(data))
            .catch(console.error);
        if (onMappingSaved) onMappingSaved();
    };

    const handleSearch = () => {
        setPage(1);
        fetchOrders();
    }

    const toggleSelectAll = (checked: boolean) => {
        if (checked) {
            setSelectedSns(new Set(orders.map(o => o.order_sn)));
        } else {
            setSelectedSns(new Set());
        }
    };

    const toggleSelect = (sn: string) => {
        const next = new Set(selectedSns);
        if (next.has(sn)) next.delete(sn);
        else next.add(sn);
        setSelectedSns(next);
    };

    return (
        <div className="max-w-7xl mx-auto p-6 space-y-8 animate-in fade-in duration-500 ">
            {/* Header Section */}
            <div className="flex flex-col gap-6">
                <div className="flex items-center justify-between">
                    <h1 className="text-3xl font-black tracking-tight text-gray-900">我的订单</h1>
                    <Button variant="outline" className="h-10 gap-2 bg-white border-gray-200 hover:bg-gray-50 shadow-sm transition-all rounded-xl px-5 border">
                        <div className="w-4 h-4 rounded-full bg-orange-100 flex items-center justify-center">
                            <div className="w-1.5 h-1.5 bg-orange-600 rounded-full" />
                        </div>
                        <span className="font-bold text-sm text-gray-700">成本映射管理</span>
                    </Button>
                </div>

                {/* Site & Shop Selectors */}
                <div className="w-full">
                    <SiteShopSelector
                        selectedSite={selectedSite}
                        selectedShop={selectedShop}
                        onSiteChange={(v) => { setSelectedSite(v); setPage(1); }}
                        onShopChange={(v) => { setSelectedShop(v); setPage(1); }}
                        sites={sites}
                        shops={shops}
                    />
                </div>

                {/* Filter Bar */}
                <div className="flex gap-3 items-center">
                    <div className="relative flex-1 group">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 group-focus-within:text-orange-500 transition-colors" />
                        <Input
                            placeholder="搜索订单号 / 商品名称 / 订单状态"
                            className="pl-11 h-11 bg-gray-100 border-transparent focus:bg-white focus:border-orange-500 transition-all rounded-2xl text-sm"
                            value={keyword}
                            onChange={e => setKeyword(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleSearch()}
                        />
                    </div>

                    <DateRangePicker
                        startDate={startDate}
                        endDate={endDate}
                        onChange={(s, e) => {
                            setStartDate(s);
                            setEndDate(e);
                        }}
                    />

                    <Button
                        onClick={() => selectedSns.size > 0 ? onSyncSelected(Array.from(selectedSns)) : onSync(startDate, endDate)}
                        disabled={syncing}
                        className="h-11 px-8 bg-[#ff6900] hover:bg-[#ff8533] text-white rounded-2xl shadow-lg shadow-orange-500/20 active:scale-95 transition-all gap-2 font-bold"
                    >
                        {syncing ? <RefreshCw className="w-4 h-4 animate-spin" /> : null}
                        {selectedSns.size > 0 ? `同步选中 (${selectedSns.size})` : '同步订单'}
                    </Button>
                </div>
            </div>

            {/* Sync Progress Banner */}
            {syncing && syncTask && (
                <div className="bg-[#030213] text-white rounded-2xl p-5 shadow-2xl relative overflow-hidden group">
                    <div className="absolute top-0 left-0 h-full bg-orange-500/10 transition-all duration-500"
                        style={{ width: `${(syncTask.current / (syncTask.total || 1)) * 100}%` }} />
                    <div className="relative flex items-center justify-between z-10">
                        <div className="flex items-center gap-4">
                            <div className="w-10 h-10 rounded-full bg-orange-500/20 flex items-center justify-center">
                                <RefreshCw className="w-5 h-5 text-orange-500 animate-spin" />
                            </div>
                            <div>
                                <h3 className="font-bold text-sm">正在同步订单数据...</h3>
                                <p className="text-[11px] text-gray-400 mt-0.5">请勿关闭页面，系统正在更新您的订单及财务明细信息</p>
                            </div>
                        </div>
                        <div className="flex flex-col items-end gap-2">
                            <div className="text-[11px] font-black text-orange-500 bg-orange-500/10 px-2 py-0.5 rounded-md">
                                {Math.round((syncTask.current / (syncTask.total || 1)) * 100)}%
                            </div>
                            <div className="text-[10px] text-gray-400 font-medium">
                                已处理: <span className="text-white">{syncTask.current}</span> / {syncTask.total} (成功: {syncTask.count})
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Main Content Card */}
            <div className="bg-white rounded-3xl shadow-2xl shadow-gray-200/50 border border-gray-100/50 p-8">
                {/* Tabs */}
                <div className="flex gap-3 mb-10 overflow-x-auto pb-2 scrollbar-none">
                    {tabs.map(tab => (
                        <button
                            key={tab.id}
                            className={cn(
                                "flex items-center gap-2 px-6 py-3 rounded-2xl text-sm font-bold transition-all duration-300 whitespace-nowrap",
                                activeTab === tab.id
                                    ? "bg-[#030213] text-white shadow-xl shadow-black/20 translate-y-[-2px]"
                                    : "text-gray-400 hover:text-gray-900 border border-transparent hover:bg-gray-50 hover:border-gray-100"
                            )}
                            onClick={() => { setActiveTab(tab.id); setPage(1); }}
                        >
                            <span className={cn(
                                activeTab === tab.id ? "text-orange-500" : "text-gray-300"
                            )}>{tab.label}</span>
                            {tab.count > 0 && (
                                <span className={cn(
                                    "text-[10px] px-2 py-0.5 rounded-lg",
                                    activeTab === tab.id ? "bg-white/20 text-white" : "bg-gray-100 text-gray-500"
                                )}>
                                    {tab.count}
                                </span>
                            )}
                        </button>
                    ))}
                </div>

                {/* List Header / Sort Section */}
                <div className="flex items-center justify-between mb-8 pb-3 border-b border-gray-100/50">
                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-3">
                            <Checkbox
                                id="all-check"
                                checked={orders.length > 0 && selectedSns.size === orders.length}
                                onCheckedChange={(checked) => toggleSelectAll(!!checked)}
                                className="w-5 h-5 rounded-md"
                            />
                            <label htmlFor="all-check" className="text-sm font-bold text-gray-900 cursor-pointer select-none">全选</label>
                        </div>
                        <div className="h-4 w-px bg-gray-200" />
                        <div className="text-sm font-black text-gray-900 flex items-center gap-2">
                            {orders.length} <span className="text-gray-400 font-bold">订单</span>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <span className="text-xs text-gray-400 font-black uppercase tracking-wider">排序方式:</span>
                        <div className="flex bg-gray-50 p-1.5 rounded-xl gap-2">
                            {['创建时间', '商品总额', '预估运费', '费用', '预估订单收入'].map(sort => (
                                <Button key={sort} variant="ghost" size="sm" className={cn(
                                    "h-8 text-[11px] font-black px-4 rounded-lg transition-all",
                                    sort === '创建时间' ? "bg-white text-gray-900 shadow-sm" : "text-gray-400 hover:bg-white hover:text-gray-900"
                                )}>
                                    {sort}
                                </Button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Orders List */}
                <div className="space-y-8">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-32 gap-6">
                            <div className="w-16 h-16 rounded-full border-4 border-gray-100 border-t-orange-500 animate-spin" />
                            <p className="text-lg font-black text-gray-300 animate-pulse uppercase tracking-widest">Loading Data</p>
                        </div>
                    ) : (
                        orders.map(order => (
                            <OrderCard
                                key={order.order_sn}
                                order={order}
                                onSelect={() => onSelectOrder(order.order_sn)}
                                selected={selectedSns.has(order.order_sn)}
                                onToggleSelect={() => toggleSelect(order.order_sn)}
                                onMappingSaved={handleMappingSaved}
                                itemCosts={null} // Controlled internally if not provided
                                mappings={mappings}
                                shops={shops}
                            />
                        ))
                    )}
                </div>

                {/* Simplified Pagination */}
                <div className="flex items-center justify-between mt-12 pt-8 border-t border-gray-50">
                    <p className="text-xs text-gray-400 font-bold">显示 {orders.length} 个结果，共 {total} 个</p>
                    <div className="flex gap-3">
                        <Button
                            variant="outline"
                            disabled={page === 1}
                            onClick={() => setPage(p => p - 1)}
                            className="rounded-xl h-10 px-6 font-bold"
                        >
                            Prev
                        </Button>
                        <Button
                            variant="outline"
                            disabled={orders.length < 20}
                            onClick={() => setPage(p => p + 1)}
                            className="rounded-xl h-10 px-6 font-bold"
                        >
                            Next
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}

function OrderCard({ order, onSelect, selected, onToggleSelect, onMappingSaved, mappings, shops, itemCosts: propItemCosts }: {
    order: OrderSummary,
    onSelect: () => void,
    selected: boolean,
    onToggleSelect: () => void,
    onMappingSaved?: () => void,
    mappings?: CostMapping[],
    shops?: Shop[],
    itemCosts?: any
}) {
    const [itemCosts, setItemCosts] = useState<{ [key: string]: { purchase: number, shipping: number } }>(
        propItemCosts || (order.item_list || []).reduce((acc: any, item: any, idx: number) => ({
            ...acc,
            [`${item.item_id}-${idx}`]: {
                purchase: item.purchase_cost || 0,
                shipping: item.domestic_shipping_cost || 0
            }
        }), {})
    );
    const [saving, setSaving] = useState(false);

    const handleUpdateCost = async (itemId: number, modelName: string, idx: number, type: 'purchase' | 'shipping', val: string) => {
        const num = parseFloat(val) || 0;
        const key = `${itemId}-${idx}`;
        const nextCosts = { ...itemCosts, [key]: { ...itemCosts[key], [type]: num } };
        setItemCosts(nextCosts);

        // Auto-save on blur
        setSaving(true);
        try {
            await fetch(`http://localhost:9000/api/order/${order.order_sn}/item/cost`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    item_id: itemId,
                    model_name: modelName,
                    purchase_cost: nextCosts[key].purchase,
                    domestic_shipping_cost: nextCosts[key].shipping
                })
            });
        } catch (e) {
            console.error(e);
        } finally {
            setSaving(false);
        }
    };

    const handleSaveToMapping = async (itemId: number, modelName: string, modelId: number | undefined, sku: string | undefined, idx: number) => {
        const key = `${itemId}-${idx}`;
        const cost = itemCosts[key];

        // Find siteId from shopId
        const shop = shops?.find(s => s.value === String(order.shop_id));
        const siteId = shop?.siteId || "Unknown";

        setSaving(true);
        try {
            await fetch(`http://localhost:9000/api/mappings/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    site_id: siteId,
                    shop_id: String(order.shop_id),
                    item_id: itemId,
                    sku_id: sku || modelName || "",
                    product_name: order.item_list[idx]?.item_name || "",
                    purchase_cost: cost.purchase,
                    domestic_shipping_cost: cost.shipping
                })
            });
            if (onMappingSaved) onMappingSaved();
        } catch (e) {
            console.error(e);
        } finally {
            setSaving(false);
        }
    };

    const handleApplyMapping = async (itemId: number, modelName: string, idx: number, purchase: number, shipping: number) => {
        const key = `${itemId}-${idx}`;
        const nextCosts = { ...itemCosts, [key]: { purchase, shipping } };
        setItemCosts(nextCosts);

        // Also save to DB
        handleUpdateCost(itemId, modelName, idx, 'purchase', String(purchase));
        handleUpdateCost(itemId, modelName, idx, 'shipping', String(shipping));
    };

    const statusInfo: any = {
        'UNPAID': { label: '待付款', color: 'bg-orange-100 text-orange-600' },
        'READY_TO_SHIP': { label: '待出货', color: 'bg-blue-100 text-blue-600' },
        'SHIPPED': { label: '运送中', color: 'bg-purple-100 text-purple-600' },
        'COMPLETED': { label: '已完成', color: 'bg-green-100 text-green-600' },
        'CANCELLED': { label: '已取消', color: 'bg-red-100 text-red-600' },
        'TO_RETURN': { label: '退货/退款', color: 'bg-red-50 text-red-500' }
    }[order.order_status] || { label: order.order_status, color: 'bg-gray-100 text-gray-600' };

    // Safe Access helper
    const getVal = (val: any) => parseFloat(val) || 0;

    const escrow = order.escrow_info || {};

    // Financial Components
    const itemTotal = getVal(escrow.original_price) || getVal(order.total_amount); // Fallback to total if original missing? No, total_amount includes shipping.
    // Better Item Total: Sum of items specific price?
    const calculatedItemTotal = (order.item_list || []).reduce((acc, item) => acc + (item.model_discounted_price || 0) * item.model_quantity_purchased, 0);
    const finalItemTotal = calculatedItemTotal > 0 ? calculatedItemTotal : (getVal(escrow.original_price) || 0);

    const buyerPaidShipping = getVal(escrow.buyer_paid_shipping_fee) || getVal(order.financials?.buyer_paid_shipping);
    const shopeeRebate = getVal(escrow.shopee_shipping_rebate) || getVal(order.financials?.shopee_shipping_rebate);
    const actualShipping = getVal(escrow.actual_shipping_fee) || getVal(order.financials?.actual_shipping_fee);
    const estimatedShipping = getVal(escrow.estimated_shipping_fee) || getVal(order.estimated_shipping_fee);

    // Dynamic Shipping for Loop
    // Income Logic:
    // If completed: order_income_amount is accurate.
    // If not: ItemTotal + (BuyerPaidShipping + Rebate - ActualShipping) - Fees
    // But ActualShipping might be 0 if not shipped. Then use Estimated? Or 0?
    // Let's use logic from OrderDetail:
    // estimatedRevenue = order_income_amount ?? ((ItemTotal + EstimatedShipping - ActualShipping) - TotalFees) 
    // Wait, OrderDetail has: ((calculatedItemTotal + ((estimated_shipping_fee) - (actual_shipping_fee))) - fees)
    // This implies 'estimated_shipping_fee' contains (BuyerPaid - Rebate)? No.
    // Let's stick to a safe net logic:

    const fees = getVal(escrow.commission_fee) + getVal(escrow.service_fee) + getVal(escrow.seller_transaction_fee);

    let estimatedRevenue = getVal(escrow.order_income_amount);

    if (estimatedRevenue <= 0) {
        // Fallback Calculation
        const shippingIncome = buyerPaidShipping + shopeeRebate;
        let shippingCost = actualShipping > 0 ? actualShipping : estimatedShipping;

        // Critical Fix for Estimations:
        // If we don't know the shipping cost (est=0, actual=0) but buyer paid shipping,
        // we should conservatively assume the cost is at least what the buyer paid,
        // so we don't count buyer's shipping payment as pure profit.
        if (shippingCost === 0 && buyerPaidShipping > 0) {
            shippingCost = buyerPaidShipping;
        }

        estimatedRevenue = finalItemTotal + shippingIncome - shippingCost - fees;
    }

    const financials = {
        itemTotal: finalItemTotal,
        shipping: estimatedShipping,
        fees: fees,
        estimatedRevenue: estimatedRevenue,
        totalPaid: getVal(escrow.buyer_total_amount) || getVal(order.total_amount)
    };

    // Exchange Rates (Consistent with Dashboard)
    const currency = order.currency || 'BRL';
    const EXCHANGE_RATES: { [key: string]: number } = {
        'BRL': 1.25, 'USD': 7.2, 'SGD': 5.3, 'MYR': 1.6,
        'PHP': 0.13, 'IDR': 0.00046, 'THB': 0.2, 'VND': 0.00029, 'TWD': 0.23,
        'CNY': 1.0
    };
    const rate = EXCHANGE_RATES[currency] || 1.0;
    const currencySymbol = currency === 'BRL' ? 'R$' : (currency === 'USD' ? '$' : currency);

    const orderTotalCost = Object.values(itemCosts).reduce((sum: number, cost: any, idx) => {
        const qty = order.item_list[idx]?.model_quantity_purchased || 0;
        return sum + (cost.purchase * qty) + cost.shipping;
    }, 0);

    // Calculate Profit: (Revenue * Rate) - Cost
    const revenueRMB = financials.estimatedRevenue * rate;
    const estimatedProfit = revenueRMB - orderTotalCost;

    return (
        <div className={cn(
            "group border-2 rounded-[2rem] overflow-hidden transition-all duration-400",
            selected ? "border-orange-500 bg-orange-50/10 shadow-2xl shadow-orange-500/10" : "border-gray-50 hover:border-gray-200"
        )}>
            {/* Header */}
            <div className="bg-gray-50/50 px-8 py-4 flex items-center justify-between border-b border-gray-100/50 group-hover:bg-white transition-colors">
                <div className="flex items-center gap-6">
                    <Checkbox checked={selected} onCheckedChange={() => onToggleSelect()} className="w-5 h-5 rounded-md" />
                    <div className="text-sm font-bold text-gray-400">
                        订单号: <span className="text-gray-900 ml-2 font-mono">{order.order_sn}</span>
                    </div>
                    <Badge variant="outline" className={cn("px-3 py-0.5 rounded-lg font-black text-[10px] tracking-widest uppercase", statusInfo.color, "border-none shadow-sm")}>
                        {statusInfo.label}
                    </Badge>
                    {saving && <span className="text-[10px] text-orange-500 animate-pulse font-bold uppercase tracking-widest">Saving...</span>}
                </div>
                <Button variant="ghost" size="sm" onClick={onSelect} className="h-8 text-[11px] font-black text-blue-500 hover:text-blue-600 hover:bg-blue-50 tracking-wider">
                    查看详情 <MoreHorizontal className="w-4 h-4 ml-2" />
                </Button>
            </div>

            <div className="p-8 space-y-8">
                <div className="space-y-6">
                    {(order.item_list || []).map((item, idx) => {
                        const key = `${item.item_id}-${idx}`;
                        const cost = itemCosts[key] || { purchase: 0, shipping: 0 };
                        const itemTotalCost = cost.purchase * item.model_quantity_purchased + cost.shipping;

                        // Check for mapping
                        const shop = shops?.find(s => s.value === String(order.shop_id));
                        const siteId = shop?.siteId || "";

                        // 严格匹配：站点、店铺、商品ID和SKU
                        const matchingMapping = mappings?.find(m =>
                            m.siteId === siteId &&
                            m.shopId === String(order.shop_id) &&
                            m.productId === String(item.item_id) &&
                            (m.sku === (item.model_sku || item.model_name || ""))
                        );

                        const isCostZero = cost.purchase === 0 && cost.shipping === 0;

                        return (
                            <div key={`${order.order_sn}-${item.item_id}-${idx}`} className="space-y-4">
                                <div className="flex gap-6 items-start">
                                    <div className="w-24 h-24 rounded-2xl border border-gray-100 overflow-hidden bg-white shrink-0 shadow-sm group-hover:scale-105 transition-transform duration-500">
                                        {item.image_info?.image_url && (
                                            <img src={item.image_info?.image_url} className="w-full h-full object-cover" alt="" />
                                        )}
                                    </div>
                                    <div className="flex-1 space-y-2">
                                        <h4 className="text-sm font-black text-gray-900 leading-snug line-clamp-1">{item.item_name}</h4>
                                        <div className="flex items-center gap-3">
                                            <div className="text-[11px] font-bold text-gray-400 bg-gray-100 px-2 py-0.5 rounded-md">
                                                颜色: {item.model_name || '默认'}
                                            </div>
                                            <div className="text-[11px] font-black text-gray-900 border border-gray-100 px-2 py-0.5 rounded-md">
                                                ×{item.model_quantity_purchased}
                                            </div>
                                        </div>
                                        <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">
                                            ID: {item.item_id}
                                            {item.model_sku && <span className="ml-2 text-gray-300">SKU: {item.model_sku}</span>}
                                        </div>
                                    </div>
                                </div>

                                {/* Mapping Alert */}
                                {matchingMapping && isCostZero && (
                                    <div className="bg-gradient-to-r from-emerald-50 to-green-50 border border-emerald-100 rounded-xl p-3 flex items-center justify-between animate-in slide-in-from-top-2 duration-300">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center">
                                                <Sparkles className="w-4 h-4 text-emerald-600" />
                                            </div>
                                            <div>
                                                <div className="text-xs font-bold text-emerald-800 flex items-center gap-2">
                                                    检测到成本映射
                                                    <span className="bg-emerald-200/50 text-emerald-700 px-1.5 py-0.5 rounded text-[10px]">
                                                        {matchingMapping.siteId} / {matchingMapping.sku || '无SKU'}
                                                    </span>
                                                </div>
                                                <div className="text-[11px] text-emerald-600/80 mt-0.5 font-medium">
                                                    采购: ¥{matchingMapping.purchaseCost} | 运费: ¥{matchingMapping.domesticShippingCost}
                                                </div>
                                            </div>
                                        </div>
                                        <Button
                                            size="sm"
                                            onClick={() => handleApplyMapping(item.item_id, item.model_name || "", idx, matchingMapping.purchaseCost, matchingMapping.domesticShippingCost)}
                                            className="h-8 bg-emerald-600 hover:bg-emerald-700 text-white border-0 shadow-lg shadow-emerald-500/20"
                                        >
                                            应用
                                        </Button>
                                    </div>
                                )}

                                <div className="bg-gray-50/50 rounded-2xl p-5 border border-gray-100/50 flex flex-wrap gap-8 items-end relative overflow-hidden">
                                    <div className="absolute top-0 right-0 p-2 opacity-10">
                                        <Calculator className="w-12 h-12" />
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">采购成本 (单价)</label>
                                        <div className="relative">
                                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-bold">¥</span>
                                            <Input
                                                className="w-40 h-10 pl-7 font-black bg-white rounded-xl border-gray-200"
                                                defaultValue={cost.purchase.toFixed(2)}
                                                type="number"
                                                onBlur={(e) => handleUpdateCost(item.item_id, item.model_name || "", idx, 'purchase', e.target.value)}
                                            />
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest">国内物流成本</label>
                                        <div className="relative">
                                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-bold">¥</span>
                                            <Input
                                                className="w-40 h-10 pl-7 font-black bg-white rounded-xl border-gray-200"
                                                defaultValue={cost.shipping.toFixed(2)}
                                                type="number"
                                                onBlur={(e) => handleUpdateCost(item.item_id, item.model_name || "", idx, 'shipping', e.target.value)}
                                            />
                                        </div>
                                    </div>
                                    <div className="flex-1 min-w-[200px] flex flex-col items-end justify-center">
                                        <div className="flex flex-col items-end mb-1">
                                            <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">订单项总成本</span>
                                            {(!isCostZero || cost.purchase > 0 || cost.shipping > 0) && (
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleSaveToMapping(item.item_id, item.model_name || "", item.model_id, item.model_sku, idx)}
                                                    className="h-7 px-2 text-[10px] font-bold text-orange-500 hover:text-orange-600 hover:bg-orange-50 -mr-2 gap-1"
                                                >
                                                    <Save className="w-3 h-3" />
                                                    保存成本映射
                                                </Button>
                                            )}
                                        </div>
                                        <span className="text-xl font-black text-gray-900 leading-none">¥ {itemTotalCost.toFixed(2)}</span>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div className="bg-blue-50/30 rounded-2xl p-4 flex items-center justify-between border border-blue-50/50">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-blue-500/10 flex items-center justify-center">
                            <Calculator className="w-4 h-4 text-blue-500" />
                        </div>
                        <span className="text-xs font-black text-blue-900">订单总成本 <span className="text-blue-500/50 ml-1">({order.item_list?.length} 个订单项)</span></span>
                    </div>
                    <div className="flex items-center gap-3">
                        <span className="text-xs font-bold text-gray-400">¥</span>
                        <Input className="w-32 h-10 font-black text-right rounded-xl border-blue-100 bg-white" value={orderTotalCost.toFixed(2)} readOnly />
                    </div>
                </div>

                {/* Footer Financial Breakdown */}
                <div className="grid grid-cols-5 gap-4 px-2">
                    <div className="space-y-1">
                        <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">商品总额</p>
                        <p className="text-lg font-black leading-none text-gray-900">
                            {currencySymbol} {financials.itemTotal.toFixed(2)}
                        </p>
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">预估运费总额</p>
                        <p className="text-lg font-black leading-none text-orange-600">
                            {currencySymbol} {financials.shipping.toFixed(2)}
                        </p>
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">费用</p>
                        <p className="text-lg font-black leading-none text-red-500">
                            {currencySymbol} {financials.fees.toFixed(2)}
                        </p>
                    </div>
                    <div className="space-y-1">
                        <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">预估订单收入</p>
                        <p className="text-lg font-black leading-none text-green-600">
                            {currencySymbol} {financials.estimatedRevenue.toFixed(2)}
                        </p>
                    </div>
                    {/* Profit Section */}
                    <div className="space-y-1 bg-green-50/50 -my-2 -mx-2 px-2 py-2 rounded-xl border border-green-100/50">
                        <p className="text-[10px] font-black text-emerald-600/70 uppercase tracking-widest flex items-center gap-1">
                            预估利润 <span className="text-[8px] bg-white px-1 rounded shadow-sm border border-green-100">CNY</span>
                        </p>
                        <p className={cn("text-xl font-black leading-none", estimatedProfit >= 0 ? "text-emerald-600" : "text-red-500")}>
                            ¥ {estimatedProfit.toFixed(2)}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
