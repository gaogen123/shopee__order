import { useState, useEffect } from 'react';
import { Package, User, Clock, CreditCard, Printer, AlertCircle, ChevronDown, HelpCircle, FileText, Receipt, ArrowLeft, ExternalLink, Store } from 'lucide-react';

// Shopee 订单详情链接生成函数
function getShopeeOrderDetailUrl(orderNumber: string, shopId?: string): string {
  if (shopId) {
    return `https://seller.shopee.cn/portal/sale/order/${orderNumber}?cnsc_shop_id=${shopId}`;
  }
  return `https://seller.shopee.cn/portal/sale/order/${orderNumber}`;
}

interface OrderDetailProps {
  orderSn?: string;
  shopId?: string;
  shopRegion?: string;
  shopName?: string;
  onBack?: () => void;
}

export function OrderDetail({ orderSn, shopId, shopRegion, shopName, onBack }: OrderDetailProps) {
  const [showFeeDetails, setShowFeeDetails] = useState(false);
  const [showServiceFeeDetails, setShowServiceFeeDetails] = useState(false);
  const [showRevenueDetails, setShowRevenueDetails] = useState(false);
  const [showBuyerPaymentDetails, setShowBuyerPaymentDetails] = useState(false);
  const [showShippingDetails, setShowShippingDetails] = useState(false);
  const [itemCosts, setItemCosts] = useState<{ [key: number]: string }>({});
  const [domesticLogisticsCost, setDomesticLogisticsCost] = useState<string>('');
  const [purchaseTotalOverride, setPurchaseTotalOverride] = useState<string | null>(null);
  const [totalCostOverride, setTotalCostOverride] = useState<string | null>(null);
  const [showCostDetails, setShowCostDetails] = useState(true);
  const [isEditingTotal, setIsEditingTotal] = useState(false);
  const [totalCostTemp, setTotalCostTemp] = useState('');

  const [orderNo, setOrderNo] = useState(orderSn || '251208RD57K1WM');

  useEffect(() => {
    if (orderSn) setOrderNo(orderSn);
  }, [orderSn]);

  // 处理单项成本输入变化
  const handleItemCostChange = (itemId: number, value: string) => {
    if (value === '' || /^\d*\.?\d{0,2}$/.test(value)) {
      setItemCosts(prev => ({ ...prev, [itemId]: value }));
      setPurchaseTotalOverride(null); // 修改明细时清除总额覆盖
    }
  };

  // 处理采购总金额输入 (Override)
  const handlePurchaseTotalChange = (value: string) => {
    if (value === '' || /^\d*\.?\d{0,2}$/.test(value)) {
      setPurchaseTotalOverride(value);
    }
  };

  // 处理国内物流成本输入变化
  const handleDomesticLogisticsCostChange = (value: string) => {
    if (value === '' || /^\d*\.?\d{0,2}$/.test(value)) {
      setDomesticLogisticsCost(value);
    }
  };

  // 计算采购总金额 (从商品明细累计)
  const calculateItemsPurchaseSum = () => {
    return order.items.reduce((total, item) => {
      const cost = parseFloat(itemCosts[item.id] || '0');
      return total + (cost * item.quantity);
    }, 0);
  };

  // 获取生效的采购总金额 (优先使用覆盖值)
  const getEffectivePurchaseTotal = () => {
    if (purchaseTotalOverride !== null) {
      return parseFloat(purchaseTotalOverride || '0');
    }
    return calculateItemsPurchaseSum();
  };

  // 计算总成本
  const calculateTotalCost = () => {
    if (totalCostOverride !== null) {
      return parseFloat(totalCostOverride);
    }
    const purchase = getEffectivePurchaseTotal();
    const logistics = parseFloat(domesticLogisticsCost || '0');
    return purchase + logistics;
  };

  // 处理总成本输入 (反推采购金额)
  const handleTotalCostChange = (value: string) => {
    if (value === '' || /^\d*\.?\d{0,2}$/.test(value)) {
      const total = value === '' ? 0 : parseFloat(value);
      const logistics = parseFloat(domesticLogisticsCost || '0');
      const newPurchase = Math.max(0, total - logistics);
      // 保留两位小数但如果是整数去掉.00以免输入体验太差? 
      // 还是保持统一
      setPurchaseTotalOverride(newPurchase.toFixed(2));
    }
  };

  // 计算预估利润
  const calculateEstimatedProfit = () => {
    const revenueInRMB = order.payment.estimatedRevenue * (order.exchangeRate || 1);
    return revenueInRMB - calculateTotalCost();
  };

  const handleExchangeRateChange = (value: string) => {
    if (value === '' || /^\d*\.?\d*$/.test(value)) {
      setOrder((prev: any) => ({
        ...prev,
        exchangeRate: value === '' ? 0 : parseFloat(value)
      }));
    }
  };

  // State for order data
  const [order, setOrder] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const getStatusLabel = (status: string) => {
    const statusMap: { [key: string]: string } = {
      'UNPAID': '未付款',
      'READY_TO_SHIP': '待出货',
      'PROCESSED': '已处理',
      'RETRY_SHIP': '运送失败(可重试)',
      'SHIPPED': '已出货',
      'TO_CONFIRM_RECEIVE': '待收货',
      'COMPLETED': '已完成',
      'IN_CANCEL': '取消中',
      'CANCELLED': '已取消',
      'TO_RETURN': '退货/退款',
    };
    return statusMap[status] || status;
  };

  useEffect(() => {
    const fetchOrder = async () => {
      try {
        // Query dynamic order
        const response = await fetch(`http://localhost:8000/api/order/${orderNo}`);
        if (!response.ok) {
          throw new Error('Failed to fetch order');
        }
        const data = await response.json();

        // Determine initial exchange rate (fallback)
        const currency = data.currency || 'BRL';
        const fallbackRates: { [key: string]: number } = {
          'BRL': 1.24, 'USD': 7.2, 'SGD': 5.3, 'MYR': 1.6,
          'PHP': 0.13, 'IDR': 0.00046, 'THB': 0.2, 'VND': 0.00029, 'TWD': 0.23,
        };
        const defaultRate = fallbackRates[currency] || 1;

        // Pre-calculate Item Total (Discounted) to ensure consistency
        const calculatedItemTotal = data.item_list?.reduce((acc: number, item: any) => acc + (item.model_discounted_price * item.model_quantity_purchased), 0) || 0;

        // Map Shopee API structure to Component structure
        setOrder({
          orderNo: data.order_sn,
          currency: currency,
          exchangeRate: defaultRate,
          status: getStatusLabel(data.order_status),
          statusColor: 'text-green-600 bg-green-50', // Simplified logic
          createTime: new Date(data.create_time * 1000).toLocaleString(),
          paymentTime: new Date((data.pay_time || data.create_time) * 1000).toLocaleString(),
          buyer: {
            username: data.buyer_username,
            name: data.recipient_address?.name || '',
            userId: data.buyer_user_id,
            messageToSeller: data.message_to_seller || '',
            phone: data.recipient_address?.phone || '',
            address: data.recipient_address?.full_address || '',
          },
          items: (data.item_list || []).map((item: any) => ({
            id: item.item_id,
            modelId: item.model_id,
            name: item.item_name,
            sku: item.model_name,
            skuCode: item.model_sku || '',
            price: item.model_discounted_price,
            quantity: item.model_quantity_purchased,
            image: item.image_info?.image_url || '',
          })),
          payment: {
            itemTotal: calculatedItemTotal,
            itemPrice: calculatedItemTotal, // Use calculated reduced price to match "Item Total"
            estimatedShipping: (data.financials?.estimated_shipping_fee || 0) - (data.escrow_info?.actual_shipping_fee || data.actual_shipping_fee || 0),
            buyerPaidShipping: (data.financials?.estimated_shipping_fee || 0) - (data.financials?.shopee_shipping_rebate || 0),
            // Logistics Fee = Prioritize escrow actual fee
            logisticsProviderFee: data.escrow_info?.actual_shipping_fee || data.actual_shipping_fee || 0,
            shopeeShippingRebate: data.financials?.shopee_shipping_rebate || 0,
            totalFees: data.financials?.total_fees || 0,
            commission: data.financials?.commission_fee || 0,
            serviceFee: data.financials?.service_fee || 0,
            transactionFee: data.financials?.seller_transaction_fee || 0,
            estimatedRevenue: (calculatedItemTotal + ((data.financials?.estimated_shipping_fee || 0) - (data.escrow_info?.actual_shipping_fee || data.actual_shipping_fee || 0))) - (data.financials?.total_fees || 0),
          },
          buyerPayment: {
            itemTotal: calculatedItemTotal, // Use calculated item total
            shipping: data.escrow_info?.seller_shipping_discount || 0,
            shopeeVoucher: data.escrow_info?.discount_from_voucher_shopee || 0,
            sellerVoucher: data.escrow_info?.seller_discount || 0,
            shopeeCoins: data.escrow_info?.discount_from_coin || 0,
            icms: data.escrow_info?.icms_tax_amount || 0,
            importTax: data.escrow_info?.import_tax_amount || 0,
            totalPaid: data.financials?.buyer_total_amount || data.total_amount,
          },
          logistics: [],
        });

        // Initialize Item Costs
        const costs: { [key: number]: string } = {};
        (data.item_list || []).forEach((item: any) => {
          if (item.sourcing_price > 0) costs[item.item_id] = String(item.sourcing_price);
        });
        setItemCosts(costs);

        if (data.purchase_cost > 0) {
          setPurchaseTotalOverride(data.purchase_cost);
        }
        if (data.domestic_shipping_cost) {
          setDomesticLogisticsCost(String(data.domestic_shipping_cost));
        }

        if (data.total_cost > 0) {
          setTotalCostOverride(String(data.total_cost));
        }

        // Fetch live exchange rate asynchronously
        if (currency) {
          fetch(`https://api.exchangerate-api.com/v4/latest/${currency}`)
            .then(res => res.json())
            .then(rateData => {
              const liveRate = rateData.rates['CNY'];
              if (liveRate) {
                setOrder((prev: any) => ({ ...prev, exchangeRate: liveRate }));
              }
            })
            .catch(e => console.error('Failed to fetch live exchange rate', e));
        }
      } catch (err: any) {
        setError(err.message);
        // Fallback or keep loading false
      } finally {
        setLoading(false);
      }
    };

    fetchOrder();
  }, [orderNo]);

  const handleSaveCosts = async (overrides?: { purchaseChoice?: string | null; totalChoice?: string | null }) => {
    if (!order) return;
    try {
      const payload = {
        purchase_cost: overrides && overrides.purchaseChoice !== undefined ? overrides.purchaseChoice : purchaseTotalOverride,
        domestic_shipping_cost: parseFloat(domesticLogisticsCost) || 0,
        total_cost: (overrides && overrides.totalChoice !== undefined) ? (overrides.totalChoice ? parseFloat(overrides.totalChoice) : null) : (totalCostOverride ? parseFloat(totalCostOverride) : null)
      };

      const response = await fetch(`http://localhost:8000/api/order/${order.orderNo}/cost`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        console.error('Failed to save costs');
      }
    } catch (e) {
      console.error('Error saving costs:', e);
    }
  };

  const handleSaveItemCost = async (itemId: number) => {
    if (!order) return;
    const item = order.items.find((i: any) => i.id === itemId);
    const price = parseFloat(itemCosts[itemId] || '0');

    try {
      const payload = [{
        item_id: itemId,
        model_id: item?.modelId || 0,
        sourcing_price: price
      }];

      await fetch(`http://localhost:8000/api/order/${order.orderNo}/items/cost`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch (e) {
      console.error('Error saving item cost:', e);
    }
  };

  if (loading) return <div className="p-10 text-center">Loading Order Data...</div>;
  if (error) return <div className="p-10 text-center text-red-500">Error: {error}</div>;
  if (!order) return <div className="p-10 text-center">No Order Found</div>;

  // 生成 Shopee 订单详情链接
  const shopeeOrderUrl = getShopeeOrderDetailUrl(order.orderNo, shopId);

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            {/* 返回按钮 */}
            {onBack && (
              <button
                onClick={onBack}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="返回"
              >
                <ArrowLeft className="w-5 h-5 text-gray-600" />
              </button>
            )}
            <div>
              <h1 className="text-2xl mb-2">订单详情</h1>
              <div className="flex items-center gap-4 text-gray-600">
                <span>订单号: {order.orderNo}</span>
                <span className={`px-3 py-1 rounded-full ${order.statusColor}`}>
                  {order.status}
                </span>
              </div>
            </div>
          </div>

          {/* 店铺信息和 Shopee 链接 */}
          <div className="flex items-center gap-3">
            {/* 店铺信息 */}
            {shopName && (
              <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg">
                <Store className="w-4 h-4 text-gray-500" />
                <span className="text-sm text-gray-700">{shopName}</span>
                {shopRegion && (
                  <span className="text-xs text-gray-400 bg-gray-200 px-1.5 py-0.5 rounded">{shopRegion}</span>
                )}
              </div>
            )}

            {/* Shopee 卖家中心链接 */}
            <a
              href={shopeeOrderUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors text-sm font-medium"
            >
              <ExternalLink className="w-4 h-4" />
              在 Shopee 查看
            </a>
          </div>
        </div>

        {/* Time info */}
        <div className="flex gap-8 text-sm text-gray-600">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            <span>下单时间: {order.createTime}</span>
          </div>
          <div className="flex items-center gap-2">
            <CreditCard className="w-4 h-4" />
            <span>付款时间: {order.paymentTime}</span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow-sm mb-4">
        <div className="p-6">
          <div className="space-y-6">
            {/* Buyer Info */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <User className="w-5 h-5 text-gray-600" />
                <h3>买家信息</h3>
              </div>
              <div className="space-y-2 text-sm">
                {order.buyer.userId && (
                  <div className="flex">
                    <span className="text-gray-600 w-24">User ID:</span>
                    <span>{order.buyer.userId}</span>
                  </div>
                )}
                <div className="flex">
                  <span className="text-gray-600 w-24">用户名:</span>
                  <span>{order.buyer.username}</span>
                </div>
                {order.buyer.messageToSeller && (
                  <div className="flex">
                    <span className="text-gray-600 w-24">买家留言:</span>
                    <span>{order.buyer.messageToSeller}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Items */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <Package className="w-5 h-5 text-gray-600" />
                <h3>商品信息</h3>
              </div>

              {/* Table Header */}
              <div className="flex gap-4 pb-2 mb-2 border-b text-sm text-gray-500">
                <div className="flex-1">商品</div>
                <div className="text-center w-24">采购金额</div>
                <div className="text-center w-24">单价</div>
                <div className="text-center w-16">数量</div>
                <div className="text-right w-24">小计</div>
              </div>

              <div className="space-y-4">
                {order.items.map((item) => (
                  <div key={item.id} className="flex gap-4">
                    <div className="text-gray-500 w-8 text-center">{item.id}</div>
                    <img
                      src={item.image}
                      alt={item.name}
                      className="w-20 h-20 object-cover rounded border"
                    />
                    <div className="flex-1">
                      <div className="mb-2">{item.name}</div>
                      <div className="text-sm text-gray-500">{item.sku}</div>
                      <div className="text-sm text-gray-500">{item.skuCode}</div>
                    </div>
                    <div className="text-center w-24">
                      <div className="flex items-center justify-center">
                        <span className="text-gray-400 mr-1 text-xs">¥</span>
                        <input
                          type="text"
                          value={itemCosts[item.id] || ''}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => handleItemCostChange(item.id, e.target.value)}
                          onBlur={() => handleSaveItemCost(item.id)}
                          className="w-16 px-1 py-0.5 text-sm border border-gray-300 rounded text-center focus:outline-none focus:border-orange-500"
                          placeholder="0.00"
                        />
                      </div>
                    </div>
                    <div className="text-center w-24">
                      <div>R${item.price.toFixed(2)}</div>
                    </div>
                    <div className="text-center w-16">
                      <div>{item.quantity}</div>
                    </div>
                    <div className="text-right w-24">
                      <div>R${(item.price * item.quantity).toFixed(2)}</div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6 pt-4 border-t">
                <div className="w-full md:w-[480px] ml-auto space-y-2">

                  {/* 总成本 - 展开控制 */}
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-1 cursor-pointer" onClick={() => setShowCostDetails(!showCostDetails)}>
                      <span className="text-gray-700 font-medium">总成本</span>
                      <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showCostDetails ? 'rotate-180' : ''}`} />
                    </div>
                    <div className="flex items-center">
                      <span className="text-gray-900 mr-1">-¥</span>
                      {isEditingTotal ? (
                        <input
                          type="text"
                          autoFocus
                          className="w-24 text-right border-b border-orange-500 focus:outline-none bg-transparent font-medium text-gray-900"
                          value={totalCostTemp}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => setTotalCostTemp(e.target.value)}
                          onBlur={() => {
                            let finalTotal: string | null = null;
                            if (totalCostTemp === '') {
                              setTotalCostOverride(null);
                            } else if (/^\d*\.?\d*$/.test(totalCostTemp)) {
                              finalTotal = parseFloat(totalCostTemp).toFixed(2);
                              setTotalCostOverride(finalTotal);
                            }

                            handleSaveCosts({ totalChoice: finalTotal });
                            setIsEditingTotal(false);
                          }}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              e.currentTarget.blur();
                            }
                          }}
                        />
                      ) : (
                        <span
                          className="text-gray-900 cursor-pointer border-b border-transparent hover:border-gray-300 min-w-[60px] text-right"
                          onClick={(e) => {
                            e.stopPropagation();
                            setTotalCostTemp(calculateTotalCost().toFixed(2));
                            setIsEditingTotal(true);
                          }}
                        >
                          {calculateTotalCost().toFixed(2)}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 成本明细 */}
                  {showCostDetails && (
                    <div className="bg-gray-50 rounded-md p-3 space-y-2 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">采购总金额</span>
                        <div className="flex items-center">
                          <span className={`text-sm mr-1 ${purchaseTotalOverride !== null ? 'text-orange-600' : 'text-gray-400'}`}>¥</span>
                          <input
                            type="text"
                            value={(() => {
                              const val = purchaseTotalOverride !== null ? purchaseTotalOverride : calculateItemsPurchaseSum().toFixed(2);
                              return parseFloat(val) === 0 ? '' : val;
                            })()}
                            onChange={(e) => handlePurchaseTotalChange(e.target.value)}
                            onBlur={() => handleSaveCosts()}
                            className={`w-20 text-right border-b border-gray-300 focus:border-orange-500 focus:outline-none bg-transparent ${purchaseTotalOverride !== null ? 'text-orange-600 font-medium' : 'text-gray-600'}`}
                            placeholder="0.00"
                          />
                        </div>
                      </div>

                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">国内物流成本</span>
                        <div className="flex items-center">
                          <span className="text-gray-400 mr-1 text-sm">¥</span>
                          <input
                            type="text"
                            value={parseFloat(domesticLogisticsCost || '0') === 0 ? '' : domesticLogisticsCost}
                            onChange={(e) => handleDomesticLogisticsCostChange(e.target.value)}
                            onBlur={() => handleSaveCosts()}
                            className="w-20 text-right border-b border-gray-300 focus:border-orange-500 focus:outline-none text-gray-600 bg-transparent"
                            placeholder="0.00"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 预估利润 - 始终显示 */}
                  <div className="flex justify-between items-start py-3 border-t border-dashed">
                    <div className="flex flex-col">
                      <span className="text-green-700 font-medium">预估利润</span>
                      <div className="flex items-center gap-1 mt-1 bg-gray-50 px-2 py-1 rounded">
                        <span className="text-xs text-gray-500">汇率:</span>
                        <input
                          type="number"
                          step="0.01"
                          value={order.exchangeRate}
                          onChange={(e) => handleExchangeRateChange(e.target.value)}
                          className="w-12 text-xs bg-transparent text-right border-b border-gray-300 focus:outline-none focus:border-orange-500 text-gray-600"
                        />
                        <span className="text-xs text-gray-500">{order.currency}</span>
                      </div>
                    </div>
                    <span className="text-green-600 text-xl font-bold">
                      ¥{calculateEstimatedProfit().toFixed(2)}
                    </span>
                  </div>

                  <div className="flex justify-end mb-4">
                    <button
                      onClick={() => setShowRevenueDetails(!showRevenueDetails)}
                      className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
                    >
                      {showRevenueDetails ? '隐藏收入进账详情' : '查看收入进账详情'}
                      <ChevronDown className={`w-3 h-3 transition-transform ${showRevenueDetails ? 'rotate-180' : ''}`} />
                    </button>
                  </div>

                  {showRevenueDetails && (
                    <table className="w-fit ml-auto text-sm border-separate border-spacing-y-2">
                      <tbody>
                        {/* 商品总额 */}
                        <tr>
                          <td className="text-right pr-6 text-gray-600 align-middle">商品总额</td>
                          <td className="text-right text-gray-900 font-medium whitespace-nowrap align-middle">R${order.payment.itemTotal.toFixed(2)}</td>
                        </tr>

                        {/* 商品价格 */}
                        <tr>
                          <td className="text-right pr-6 text-gray-400 text-xs text-gray-300 align-middle">商品价格</td>
                          <td className="text-right text-gray-400 text-xs text-gray-300 whitespace-nowrap align-middle">R${order.payment.itemPrice.toFixed(2)}</td>
                        </tr>

                        {/* 预估运费总额 */}
                        <tr className="cursor-pointer group" onClick={() => setShowShippingDetails(!showShippingDetails)}>
                          <td className="text-right pr-6 align-middle">
                            <div className="flex items-center justify-end gap-1 text-gray-900 group-hover:text-gray-700">
                              <span>预估运费总额</span>
                              <ChevronDown className={`w-3 h-3 text-gray-400 transition-transform ${showShippingDetails ? 'rotate-180' : ''}`} />
                            </div>
                          </td>
                          <td className="text-right text-gray-900 font-medium whitespace-nowrap align-middle">
                            {order.payment.estimatedShipping < 0 ? '-' : ''}R${Math.abs(order.payment.estimatedShipping).toFixed(2)}
                          </td>
                        </tr>

                        {/* 运费明细 */}
                        {showShippingDetails && (
                          <>
                            <tr>
                              <td className="text-right pr-6 text-gray-400 text-xs align-middle">买家支付运费</td>
                              <td className="text-right text-gray-400 text-xs whitespace-nowrap align-middle">R${order.payment.buyerPaidShipping.toFixed(2)}</td>
                            </tr>
                            <tr>
                              <td className="text-right pr-6 text-gray-400 text-xs align-middle">物流业者收取的预估运费</td>
                              <td className="text-right text-gray-400 text-xs whitespace-nowrap align-middle">-R${Math.abs(order.payment.logisticsProviderFee).toFixed(2)}</td>
                            </tr>
                            <tr>
                              <td className="text-right pr-6 text-gray-400 text-xs align-middle">Shopee预估运费回扣</td>
                              <td className="text-right text-gray-400 text-xs whitespace-nowrap align-middle">R${order.payment.shopeeShippingRebate.toFixed(2)}</td>
                            </tr>
                          </>
                        )}

                        {/* 费用 */}
                        <tr className="cursor-pointer group" onClick={() => setShowFeeDetails(!showFeeDetails)}>
                          <td className="text-right pr-6 pt-2 align-middle">
                            <div className="flex items-center justify-end gap-1 text-gray-900 group-hover:text-gray-700">
                              <span>费用</span>
                              <ChevronDown className={`w-3 h-3 text-gray-400 transition-transform ${showFeeDetails ? 'rotate-180' : ''}`} />
                            </div>
                          </td>
                          <td className="text-right text-gray-900 font-medium whitespace-nowrap pt-2 align-middle">
                            -R${Math.abs(order.payment.totalFees).toFixed(2)}
                          </td>
                        </tr>

                        {/* 费用明细 */}
                        {showFeeDetails && (
                          <>
                            <tr>
                              <td className="text-right pr-6 align-middle">
                                <div className="flex items-center justify-end gap-1 text-gray-400 text-xs">
                                  <span className={order.payment.commission > 0 ? "text-gray-400" : "text-gray-300"}>佣金</span>
                                  <HelpCircle className="w-3 h-3 text-gray-300" />
                                </div>
                              </td>
                              <td className="text-right text-gray-400 text-xs whitespace-nowrap align-middle">-R${Math.abs(order.payment.commission).toFixed(2)}</td>
                            </tr>

                            <tr className="cursor-pointer group" onClick={() => setShowServiceFeeDetails(!showServiceFeeDetails)}>
                              <td className="text-right pr-6 align-middle">
                                <div className="flex items-center justify-end gap-1 text-gray-400 text-xs group-hover:text-gray-500">
                                  <span>服务费</span>
                                  <ChevronDown className={`w-3 h-3 text-gray-300 transition-transform ${showServiceFeeDetails ? 'rotate-180' : ''}`} />
                                </div>
                              </td>
                              <td className="text-right text-gray-400 text-xs whitespace-nowrap align-middle">-R${Math.abs(order.payment.serviceFee).toFixed(2)}</td>
                            </tr>

                            <tr>
                              <td className="text-right pr-6 align-middle">
                                <div className="flex items-center justify-end gap-1 text-gray-400 text-xs">
                                  <span>交易手续费</span>
                                  <HelpCircle className="w-3 h-3 text-gray-300" />
                                </div>
                              </td>
                              <td className="text-right text-gray-400 text-xs whitespace-nowrap align-middle">-R${Math.abs(order.payment.transactionFee).toFixed(2)}</td>
                            </tr>
                          </>
                        )}
                      </tbody>

                      {/* 预估订单收入 - 作为 tfoot 或者最后的 tr */}
                      <tfoot>
                        <tr>
                          <td colSpan={2} className="pt-4 border-t border-dashed"></td>
                        </tr>
                        <tr>
                          <td className="text-right pr-6 text-gray-600 align-middle">预估订单收入</td>
                          <td className="text-right text-orange-600 font-bold text-xl whitespace-nowrap align-middle">
                            R${order.payment.estimatedRevenue.toFixed(2)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  )}

                  {!showRevenueDetails && (
                    <div className="flex justify-end gap-8 pt-2 text-sm text-gray-500">
                      <span>预估订单收入 (隐藏详情)</span>
                      <span>R${order.payment.estimatedRevenue.toFixed(2)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>



            {/* Final Amount & Cost */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-orange-600" />
                  <span className="text-gray-700">最终金额</span>
                </div>
                <span className="text-orange-600 text-xl">
                  R${order.payment.estimatedRevenue.toFixed(2)}
                </span>
              </div>
            </div>

            {/* Buyer Payment Amount */}
            <div className="border rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3 cursor-pointer select-none" onClick={() => setShowBuyerPaymentDetails(!showBuyerPaymentDetails)}>
                <Receipt className="w-5 h-5 text-gray-600" />
                <span className="text-gray-700 font-medium">买家实付金额</span>
                <span className="ml-auto mr-2 text-gray-900 font-medium">
                  R${order.buyerPayment.totalPaid.toFixed(2)}
                </span>
                <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showBuyerPaymentDetails ? 'rotate-180' : ''}`} />
              </div>

              {showBuyerPaymentDetails && (
                <div className="mt-3 pt-3 border-t space-y-2 text-sm pl-7 pr-2 bg-gray-50 rounded-md py-3 mb-2">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">商品总额</span>
                    <span className="text-gray-900">R${order.buyerPayment.itemTotal.toFixed(2)}</span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">运费</span>
                    <span className="text-gray-900">R${order.buyerPayment.shipping.toFixed(2)}</span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Shopee Voucher</span>
                    <span className="text-gray-900">R${order.buyerPayment.shopeeVoucher.toFixed(2)}</span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Seller Voucher</span>
                    <span className="text-gray-900">R${order.buyerPayment.sellerVoucher.toFixed(2)}</span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Shopee币折抵</span>
                    <span className="text-gray-900">
                      {order.buyerPayment.shopeeCoins > 0 ? '-' : ''}R${order.buyerPayment.shopeeCoins.toFixed(2)}
                    </span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">ICMS</span>
                    <span className="text-gray-900">R${order.buyerPayment.icms.toFixed(2)}</span>
                  </div>

                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Import Tax</span>
                    <span className="text-gray-900">R${order.buyerPayment.importTax.toFixed(2)}</span>
                  </div>

                  <div className="flex justify-between items-center pt-2 border-t mt-2 font-medium">
                    <span className="text-gray-900">所有买家款项</span>
                    <span className="text-gray-900">R${order.buyerPayment.totalPaid.toFixed(2)}</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}