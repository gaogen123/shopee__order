import { Badge } from "./ui/badge";
import { Input } from "./ui/input";
import { Checkbox } from "./ui/checkbox";
import { Calculator, Sparkles, Save } from "lucide-react";
import { useState, useEffect } from "react";
import { ProductCostMapping } from "./ProductCostMappingManager";

export interface OrderItem {
  id: string;
  productName: string;
  color: string;
  quantity: number;
  image: string;
  purchaseCost?: number; // 采购成本（单价）
  domesticShippingCost?: number; // 国内物流成本
  price?: number; // 商品单价（售价）
  sku?: string; // SKU
  modelId?: number;
  originalItemId?: number;
}

export interface Order {
  id: string;
  orderNumber: string;
  username: string;
  status: 'pending' | 'processing' | 'shipped' | 'completed' | 'cancelled';
  statusText: string;
  siteId?: string; // 站点 (region)
  siteName?: string;
  shopId?: string;
  shopName?: string;
  orderDate?: string; // 订单日期
  items: OrderItem[]; // 订单项数组
  manualTotalCost?: number; // 手动调整的订单总成本
  shippingFee?: number; // 预估运费总额 (净额)
  otherFees?: number; // 其他费用
  estimatedRevenue?: number; // 预估订单收入 (实际收入, 原币种)
  estimatedProfit?: number;  // 预估利润 (RMB)
  currency?: string; // 币种
  exchangeRate?: number; // 汇率
}

interface OrderCardProps {
  order: Order;
  onViewDetails: (orderId: string) => void;
  onItemCostUpdate?: (orderId: string, itemId: string, purchaseCost: number, domesticShippingCost: number) => void;
  onOrderTotalCostUpdate?: (orderId: string, totalCost: number) => void;
  isSelected?: boolean;
  onSelectionChange?: (orderId: string, selected: boolean) => void;
  costMappings?: ProductCostMapping[];
  onSaveMapping?: (productId: string, productName: string, sku: string | undefined, siteId: string, shopId: string, purchaseCost: number, domesticShippingCost: number) => void;
}

export function OrderCard({ order, onViewDetails, onItemCostUpdate, onOrderTotalCostUpdate, isSelected, onSelectionChange, costMappings, onSaveMapping }: OrderCardProps) {
  // Calculate total cost for the entire order
  const orderTotalCost = order.items.reduce((sum, item) => {
    const itemTotal = ((item.purchaseCost || 0) + (item.domesticShippingCost || 0)) * item.quantity;
    return sum + itemTotal;
  }, 0);

  // Calculate product total amount (商品总额)
  const productTotalAmount = order.items.reduce((sum, item) => {
    return sum + (item.price || 0) * item.quantity;
  }, 0);

  // Use manual total cost if set, otherwise use auto-calculated
  const displayTotalCost = order.manualTotalCost !== undefined ? order.manualTotalCost : orderTotalCost;
  const [manualTotalCost, setManualTotalCost] = useState(displayTotalCost.toString());

  // Calculate estimated order revenue (预估订单收入) - 直接使用后端值
  const estimatedRevenue = order.estimatedRevenue || 0;

  // Calculate Estimated Profit (预估利润) - 直接使用后端值
  const estimatedProfit = order.estimatedProfit !== undefined ? order.estimatedProfit : 0;

  const statusColors = {
    pending: 'bg-orange-100 text-orange-700 border-orange-200',
    processing: 'bg-blue-100 text-blue-700 border-blue-200',
    shipped: 'bg-purple-100 text-purple-700 border-purple-200',
    completed: 'bg-green-100 text-green-700 border-green-200',
    cancelled: 'bg-gray-100 text-gray-700 border-gray-200',
  };

  const handleManualTotalCostChange = (value: string) => {
    setManualTotalCost(value);
    const cost = parseFloat(value) || 0;
    onOrderTotalCostUpdate?.(order.id, cost);
  };

  useEffect(() => {
    const newDisplayCost = order.manualTotalCost !== undefined ? order.manualTotalCost : orderTotalCost;
    setManualTotalCost(newDisplayCost.toString());
  }, [order.manualTotalCost, orderTotalCost]);

  return (
    <div className={`bg-white border rounded-lg p-4 hover:shadow-md transition-all ${isSelected ? 'border-primary border-2 bg-primary/5' : 'border-border'}`}>
      <div className="flex items-start gap-3 mb-3">
        {/* Selection Checkbox */}
        {onSelectionChange && (
          <div className="pt-0.5">
            <Checkbox
              checked={isSelected}
              onCheckedChange={(checked) => onSelectionChange(order.id, checked === true)}
              aria-label="选择订单"
            />
          </div>
        )}

        <div className="flex-1 flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              {(order.siteName || order.shopName) && (
                <div className="flex items-center gap-1 mr-2">
                  {order.siteName && (
                    <Badge variant="secondary" className="bg-gray-100 text-gray-700 hover:bg-gray-200">
                      {order.siteName}
                    </Badge>
                  )}
                  {order.shopName && (
                    <span className="text-sm font-semibold text-foreground">
                      {order.shopName}
                    </span>
                  )}
                </div>
              )}
              <span className="text-sm text-muted-foreground">订单号: {order.orderNumber}</span>
              <Badge
                variant="outline"
                className={`${statusColors[order.status]} font-medium`}
              >
                {order.statusText}
              </Badge>
            </div>
          </div>
          <button
            onClick={() => onViewDetails(order.id)}
            className="text-sm text-primary hover:underline ml-2 whitespace-nowrap"
          >
            查看详情
          </button>
        </div>
      </div>

      {/* Order Items */}
      <div className="space-y-4">
        {order.items.map((item, index) => (
          <OrderItemRow
            key={item.id}
            item={item}
            orderId={order.id}
            siteId={order.siteId || ""}
            shopId={order.shopId || ""}
            showDivider={index > 0}
            onItemCostUpdate={onItemCostUpdate}
            costMappings={costMappings}
            onSaveMapping={onSaveMapping}
          />
        ))}
      </div>

      {/* Order Financial Summary */}
      <div className="mt-4 pt-4 border-t-2 border-gray-200">
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-3">
          <div className="flex items-start justify-between gap-1 overflow-x-auto scrollbar-none">

            <div className="flex flex-col min-w-[60px]">
              <span className="text-[10px] text-muted-foreground font-medium whitespace-nowrap mb-0.5">商品总额</span>
              <span className="text-sm font-bold text-foreground leading-tight">
                <span className="text-[10px] text-muted-foreground font-normal mr-0.5">{order.currency || '¥'}</span>
                {productTotalAmount.toFixed(2)}
              </span>
            </div>

            <div className="w-px bg-gray-200 mx-1 shrink-0 h-8 self-center" />

            <div className="flex flex-col min-w-[60px]">
              <span className="text-[10px] text-muted-foreground font-medium whitespace-nowrap mb-0.5">预估运费</span>
              <span className="text-sm font-bold text-orange-600 leading-tight">
                <span className="text-[10px] text-orange-400 font-normal mr-0.5">{order.currency || '¥'}</span>
                {Math.abs(order.shippingFee || 0).toFixed(2)}
              </span>
            </div>

            <div className="w-px bg-gray-200 mx-1 shrink-0 h-8 self-center" />

            <div className="flex flex-col min-w-[40px]">
              <span className="text-[10px] text-muted-foreground font-medium whitespace-nowrap mb-0.5">费用</span>
              <span className="text-sm font-bold text-red-600 leading-tight">
                <span className="text-[10px] text-red-400 font-normal mr-0.5">{order.currency || '¥'}</span>
                {(order.otherFees || 0).toFixed(2)}
              </span>
            </div>

            <div className="w-px bg-gray-200 mx-1 shrink-0 h-8 self-center" />

            <div className="flex flex-col min-w-[70px]">
              <span className="text-[10px] text-muted-foreground font-medium whitespace-nowrap mb-0.5">预估收入</span>
              <span className={`text-sm font-bold leading-tight ${estimatedRevenue >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                <span className="text-[10px] opacity-70 font-normal mr-0.5">{order.currency || '¥'}</span>
                {estimatedRevenue.toFixed(2)}
              </span>
            </div>

            <div className="w-px bg-gray-300 mx-1 shrink-0 h-8 self-center" />

            {/* Estimated Profit */}
            <div className="flex flex-col min-w-[70px]">
              <span className="text-[10px] text-gray-500 font-black whitespace-nowrap mb-0.5">预估利润(RMB)</span>
              <span className={`text-base font-black leading-tight ${estimatedProfit >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                <span className="text-[10px] text-gray-400 font-normal mr-0.5">¥</span>
                {estimatedProfit.toFixed(2)}
              </span>
              {order.exchangeRate && (
                <span className="text-[9px] text-gray-400 scale-90 origin-left mt-0.5">汇率: {order.exchangeRate}</span>
              )}
            </div>

          </div>
        </div>
      </div>

      {/* Order Total Cost Section */}
      <div className="mt-4 pt-4 border-t-2 border-primary/20">
        <div className="bg-blue-50 rounded-md p-3">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 flex-1">
              <Calculator className="w-4 h-4 text-primary" />
              <span className="text-sm font-semibold text-foreground">采购总成本</span>
              <span className="text-xs text-muted-foreground">({order.items.length} 个订单项)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">¥</span>
              <Input
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={manualTotalCost}
                onChange={(e) => handleManualTotalCostChange(e.target.value)}
                className="h-8 text-sm w-32 bg-white"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface OrderItemRowProps {
  item: OrderItem;
  orderId: string;
  siteId: string;
  shopId: string;
  showDivider: boolean;
  onItemCostUpdate?: (orderId: string, itemId: string, purchaseCost: number, domesticShippingCost: number) => void;
  costMappings?: ProductCostMapping[];
  onSaveMapping?: (productId: string, productName: string, sku: string | undefined, siteId: string, shopId: string, purchaseCost: number, domesticShippingCost: number) => void;
}

function OrderItemRow({ item, orderId, siteId, shopId, showDivider, onItemCostUpdate, costMappings, onSaveMapping }: OrderItemRowProps) {
  const [purchaseCost, setPurchaseCost] = useState(item.purchaseCost?.toString() || "");
  const [domesticShippingCost, setDomesticShippingCost] = useState(item.domesticShippingCost?.toString() || "");

  // Find matching cost mapping for this product
  // 严格匹配：站点、店铺、商品ID和SKU，避免错误匹配不同ID的商品
  const matchingMapping = costMappings?.find(
    mapping =>
      mapping.siteId === siteId &&
      mapping.shopId === shopId &&
      mapping.productId === item.id && // 商品ID必须完全匹配
      mapping.sku === (item.sku || "") // SKU也要匹配
  );

  // Check if current values match the mapping
  const hasCostEntered = (parseFloat(purchaseCost) || 0) > 0 || (parseFloat(domesticShippingCost) || 0) > 0;

  // Calculate total cost: (采购成本 + 国内物流成) * 数量
  const itemTotalCost = ((parseFloat(purchaseCost) || 0) + (parseFloat(domesticShippingCost) || 0)) * item.quantity;

  useEffect(() => {
    setPurchaseCost(item.purchaseCost?.toString() || "");
    setDomesticShippingCost(item.domesticShippingCost?.toString() || "");
  }, [item.purchaseCost, item.domesticShippingCost]);

  const handlePurchaseCostChange = (value: string) => {
    setPurchaseCost(value);
    const cost = parseFloat(value) || 0;
    const shipping = parseFloat(domesticShippingCost) || 0;
    onItemCostUpdate?.(orderId, item.id, cost, shipping);
  };

  const handleShippingCostChange = (value: string) => {
    setDomesticShippingCost(value);
    const cost = parseFloat(purchaseCost) || 0;
    const shipping = parseFloat(value) || 0;
    onItemCostUpdate?.(orderId, item.id, cost, shipping);
  };

  const handleSaveMapping = () => {
    const cost = parseFloat(purchaseCost) || 0;
    const shipping = parseFloat(domesticShippingCost) || 0;
    if (cost > 0 || shipping > 0) {
      onSaveMapping?.(item.id, item.productName, item.sku, siteId, shopId, cost, shipping);
    }
  };

  const handleApplyMapping = () => {
    if (matchingMapping) {
      setPurchaseCost(matchingMapping.purchaseCost.toString());
      setDomesticShippingCost(matchingMapping.domesticShippingCost.toString());
      onItemCostUpdate?.(orderId, item.id, matchingMapping.purchaseCost, matchingMapping.domesticShippingCost);
    }
  };

  return (
    <div className={showDivider ? "pt-4 border-t border-border" : ""}>
      {/* Product Info */}
      <div className="flex items-center gap-4 mb-3">
        <img
          src={item.image}
          alt={item.productName}
          className="w-20 h-20 object-cover rounded-md bg-muted flex-shrink-0"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm line-clamp-2 flex-1">
              {item.productName}
            </h3>
          </div>
          <p className="text-sm text-muted-foreground">
            颜色: {item.color}
          </p>
          <p className="text-sm text-muted-foreground">
            ×{item.quantity}
          </p>
          <p className="text-xs text-muted-foreground/70 mt-1">
            商品ID: {item.id}
          </p>
          {item.sku && (
            <p className="text-xs text-muted-foreground/70">
              SKU: {item.sku}
            </p>
          )}
        </div>
      </div>

      {/* Cost Calculation Section */}
      <div className="bg-gray-50 rounded-md p-3">
        {/* Mapping Detection Alert */}
        {matchingMapping && !hasCostEntered && (
          <div className="mb-3 p-3 bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg">
            <div className="flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-green-900">检测到商品成本映射</span>
                </div>
                <div className="text-xs text-green-700 space-y-1">
                  <p>采购成本: ¥{matchingMapping.purchaseCost.toFixed(2)} | 国内物流: ¥{matchingMapping.domesticShippingCost.toFixed(2)}</p>
                  <p className="text-green-600">总计: ¥{(matchingMapping.purchaseCost + matchingMapping.domesticShippingCost).toFixed(2)}</p>
                </div>
              </div>
              <button
                onClick={handleApplyMapping}
                className="px-3 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-xs font-medium flex items-center gap-1 whitespace-nowrap"
              >
                <Sparkles className="w-3 h-3" />
                一键应用
              </button>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Calculator className="w-4 h-4 text-primary" />
            <span className="text-xs font-medium text-foreground">成本计算</span>
          </div>
          <span className="text-xs font-mono text-muted-foreground bg-white px-2 py-0.5 rounded border border-border">
            {item.sku ? `SKU: ${item.sku}` : `ID: ${item.id}`}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">采购成本（单价）</label>
            <div className="flex items-center gap-1">
              <span className="text-xs text-muted-foreground">¥</span>
              <Input
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={purchaseCost}
                onChange={(e) => handlePurchaseCostChange(e.target.value)}
                className="h-8 text-sm"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">国内物流成本</label>
            <div className="flex items-center gap-1">
              <span className="text-xs text-muted-foreground">¥</span>
              <Input
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={domesticShippingCost}
                onChange={(e) => handleShippingCostChange(e.target.value)}
                className="h-8 text-sm"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">订单项总成本</label>
            <div className="h-8 px-3 bg-white rounded-md flex items-center justify-between border border-border">
              <span className="text-sm font-medium text-foreground">
                ¥{itemTotalCost.toFixed(2)}
              </span>
              {itemTotalCost > 0 && (
                <span className="text-xs text-muted-foreground">
                  (¥{purchaseCost || 0} + ¥{domesticShippingCost || 0}) × {item.quantity}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Save Mapping Button */}
        {onSaveMapping && hasCostEntered && (
          <div className="mt-3 pt-3 border-t border-border/50">
            <button
              onClick={handleSaveMapping}
              disabled={!hasCostEntered}
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2 bg-primary/10 text-primary rounded-lg hover:bg-primary/20 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="w-4 h-4" />
              保存成本映射
            </button>
          </div>
        )}
      </div>
    </div>
  );
}