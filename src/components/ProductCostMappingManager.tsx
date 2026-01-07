import { useState } from "react";
import { Package, Trash2, Plus, X, Search, AlertCircle, Calendar } from "lucide-react";

export interface ProductCostMapping {
  id: string;
  productId: string;
  productName: string;
  sku?: string;
  siteId: string;
  shopId: string;
  purchaseCost: number;
  domesticShippingCost: number;
  createdAt: string;
}

interface Site {
  value: string;
  label: string;
}

interface Shop {
  value: string;
  label: string;
  siteId: string;
}

interface Product {
  id: string;
  name: string;
  sku?: string;
}

interface ProductCostMappingManagerProps {
  mappings: ProductCostMapping[];
  onAddMapping: (mapping: Omit<ProductCostMapping, "id" | "createdAt">) => void;
  onDeleteMapping: (id: string) => void;
  onClose?: () => void; // Optional if mode is embedded
  sites: Site[];
  shops: Shop[];
  products: Product[];
  orders: Order[];
  mode?: 'modal' | 'embedded';
}

interface Order {
  id: string;
  orderNumber: string;
  siteId: string;
  shopId: string;
  orderDate?: string; // 订单日期
  items: OrderItem[];
}

interface OrderItem {
  id: string;
  productName: string;
  sku?: string;
}

export function ProductCostMappingManager({
  mappings,
  onAddMapping,
  onDeleteMapping,
  onClose,
  sites,
  shops,
  products,
  orders,
  mode = 'modal',
}: ProductCostMappingManagerProps) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [orderNumberQuery, setOrderNumberQuery] = useState("");
  const [orderDateQuery, setOrderDateQuery] = useState("");
  const [productSearchQuery, setProductSearchQuery] = useState("");
  const [newMapping, setNewMapping] = useState({
    productId: "",
    productName: "",
    sku: "",
    siteId: "",
    shopId: "",
    purchaseCost: 0,
    domesticShippingCost: 0,
  });

  // Search order by order number, product ID, or SKU - find all matching items
  const searchResults = orderNumberQuery
    ? orders.flatMap(order => {
      // Check if order number matches
      const orderNumberMatches = order.orderNumber.includes(orderNumberQuery);

      // Find matching items within this order
      const matchingItems = order.items.filter(item =>
        item.id.includes(orderNumberQuery) ||
        (item.sku && item.sku.toLowerCase().includes(orderNumberQuery.toLowerCase()))
      );

      // If order number matches, return all items; otherwise return only matching items
      if (orderNumberMatches) {
        return order.items.map(item => ({
          order,
          item,
          matchType: 'orderNumber' as const
        }));
      } else if (matchingItems.length > 0) {
        return matchingItems.map(item => ({
          order,
          item,
          matchType: 'item' as const
        }));
      }
      return [];
    })
    : [];

  // Check which items already have mappings
  const itemMappingStatus = searchResults.map(result => {
    const existingMapping = result.item.sku
      ? mappings.find(
        m => m.sku === result.item.sku && m.siteId === result.order.siteId && m.shopId === result.order.shopId
      )
      : null;
    return {
      order: result.order,
      item: result.item,
      matchType: result.matchType,
      hasMapping: !!existingMapping,
      mapping: existingMapping,
    };
  });

  // Group items by order
  const itemsByOrder = itemMappingStatus.reduce((acc, status) => {
    const orderNumber = status.order.orderNumber;
    if (!acc[orderNumber]) {
      acc[orderNumber] = {
        order: status.order,
        items: []
      };
    }
    acc[orderNumber].items.push(status);
    return acc;
  }, {} as Record<string, { order: Order; items: typeof itemMappingStatus }>);

  // Build product options from orders with order number, date and SKU
  const productOptions = orders.flatMap(order =>
    order.items.map(item => ({
      id: item.id,
      name: item.productName,
      sku: item.sku,
      orderNumber: order.orderNumber,
      orderDate: order.orderDate,
      siteId: order.siteId,
      shopId: order.shopId,
      displayText: `${item.productName}${item.sku ? ` (SKU: ${item.sku})` : ''}`,
      searchText: `${order.orderNumber} ${order.orderDate} ${item.id} ${item.productName} ${item.sku || ''}`.toLowerCase(),
    }))
  );

  // Filter products based on search query and date query
  let filteredProducts = productOptions;

  if (productSearchQuery) {
    filteredProducts = filteredProducts.filter(p => p.searchText.includes(productSearchQuery.toLowerCase()));
  }

  if (orderDateQuery) {
    filteredProducts = filteredProducts.filter(p => p.orderDate === orderDateQuery);
  }

  // Filter shops based on selected site
  const availableShops = newMapping.siteId
    ? shops.filter((shop) => shop.siteId === newMapping.siteId)
    : [];

  // Handle site change
  const handleSiteChange = (siteId: string) => {
    setNewMapping({
      ...newMapping,
      siteId,
      shopId: "", // Reset shop when site changes
    });
  };

  // Handle product selection from dropdown
  const handleProductSelect = (productId: string) => {
    const product = productOptions.find((p) => p.id === productId);
    if (product) {
      setNewMapping({
        ...newMapping,
        productId: product.id,
        productName: product.name,
        sku: product.sku || "",
        siteId: product.siteId || "",
        shopId: product.shopId || "",
      });
      setProductSearchQuery(product.displayText);
    }
  };

  const handleAddMapping = () => {
    if (!newMapping.productName.trim() || !newMapping.siteId || !newMapping.shopId) {
      return;
    }
    onAddMapping({
      productId: newMapping.productId || `manual-${Date.now()}`,
      productName: newMapping.productName,
      sku: newMapping.sku || undefined,
      siteId: newMapping.siteId,
      shopId: newMapping.shopId,
      purchaseCost: newMapping.purchaseCost,
      domesticShippingCost: newMapping.domesticShippingCost,
    });
    setNewMapping({
      productId: "",
      productName: "",
      sku: "",
      siteId: "",
      shopId: "",
      purchaseCost: 0,
      domesticShippingCost: 0,
    });
    setShowAddForm(false);
  };

  const isModal = mode === 'modal';

  return (
    <div className={isModal ? "fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" : "flex flex-col h-full bg-white"}>
      <div className={isModal ? "bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col" : "flex-1 flex flex-col overflow-hidden"}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-border">
          <div className="flex items-center gap-2">
            <Package className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold">商品成本映射管理</h2>
          </div>
          {isModal && onClose && (
            <button
              onClick={onClose}
              className="p-1 hover:bg-muted rounded-lg transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Order Number Search */}
          <div className="mb-4">
            <label className="block text-xs text-muted-foreground mb-1">
              按订单号查询
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                value={orderNumberQuery}
                onChange={(e) => setOrderNumberQuery(e.target.value)}
                placeholder="搜索订单号/商品ID/SKU"
                className="w-full pl-9 pr-3 py-2 border border-border rounded-lg text-sm"
              />
            </div>
          </div>

          {/* Order Date Search */}
          <div className="mb-4">
            <label className="block text-xs text-muted-foreground mb-2">
              订单日期查询
            </label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="date"
                value={orderDateQuery}
                onChange={(e) => setOrderDateQuery(e.target.value)}
                placeholder="从订单中选择或手动输入"
                className="w-full pl-9 pr-3 py-2 border border-border rounded-lg text-sm"
              />
            </div>
          </div>

          {/* Search Results */}
          {orderNumberQuery && searchResults.length > 0 && (
            <div className="mb-4 space-y-3">
              {Object.values(itemsByOrder).map((orderGroup, orderIndex) => (
                <div key={orderIndex} className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center gap-2 mb-3">
                    <Package className="w-4 h-4 text-blue-600" />
                    <h4 className="text-sm font-medium text-blue-900">
                      订单: {orderGroup.order.orderNumber}
                    </h4>
                    {orderGroup.order.orderDate && (
                      <span className="text-xs text-blue-700">
                        ({orderGroup.order.orderDate})
                      </span>
                    )}
                  </div>
                  <div className="space-y-2">
                    {orderGroup.items.map((status, index) => (
                      <div
                        key={index}
                        className={`p-3 rounded-lg border ${status.hasMapping
                          ? 'bg-green-50 border-green-200'
                          : 'bg-white border-border'
                          }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1 flex-wrap">
                              <span className="text-sm font-medium truncate">
                                {status.item.productName}
                              </span>
                              {status.item.sku && (
                                <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                                  SKU: {status.item.sku}
                                </span>
                              )}
                              <span className="text-xs text-muted-foreground">
                                商品ID: {status.item.id}
                              </span>
                            </div>
                            {status.hasMapping && status.mapping ? (
                              <div className="flex items-center gap-1 text-xs text-green-700">
                                <AlertCircle className="w-3 h-3" />
                                <span>
                                  已录入成本: 采购 R${status.mapping.purchaseCost.toFixed(2)} +
                                  物流 R${status.mapping.domesticShippingCost.toFixed(2)} =
                                  R${(status.mapping.purchaseCost + status.mapping.domesticShippingCost).toFixed(2)}
                                </span>
                              </div>
                            ) : (
                              <div className="text-xs text-muted-foreground">
                                {status.item.sku ? '未录入成本' : '无SKU信息'}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {orderNumberQuery && searchResults.length === 0 && (
            <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg text-center">
              <p className="text-sm text-amber-800">未找到订单号: {orderNumberQuery}</p>
            </div>
          )}

          {/* Add Button */}
          {!showAddForm && (
            <button
              onClick={() => setShowAddForm(true)}
              className="w-full mb-4 px-4 py-3 border-2 border-dashed border-border rounded-lg hover:border-primary hover:bg-primary/5 transition-colors flex items-center justify-center gap-2 text-muted-foreground hover:text-primary"
            >
              <Plus className="w-4 h-4" />
              <span>添加新映射</span>
            </button>
          )}

          {/* Add Form */}
          {showAddForm && (
            <div className="mb-4 p-4 bg-muted/50 rounded-lg border border-border">
              <h3 className="text-sm font-medium mb-3">添加商品成本映射</h3>
              <div className="space-y-3">
                {/* Site and Shop Selection */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">
                      站点 *
                    </label>
                    <select
                      value={newMapping.siteId}
                      onChange={(e) => handleSiteChange(e.target.value)}
                      className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-white"
                    >
                      <option value="">选择站点</option>
                      {sites.filter(s => s.value !== 'all').map((site) => (
                        <option key={site.value} value={site.value}>
                          {site.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">
                      店铺 *
                    </label>
                    <select
                      value={newMapping.shopId}
                      onChange={(e) =>
                        setNewMapping({ ...newMapping, shopId: e.target.value })
                      }
                      disabled={!newMapping.siteId}
                      className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-white disabled:bg-muted disabled:cursor-not-allowed"
                    >
                      <option value="">选择店铺</option>
                      {availableShops.map((shop) => (
                        <option key={shop.value} value={shop.value}>
                          {shop.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Product Selection */}
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">
                    选择商品
                  </label>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                      type="text"
                      value={productSearchQuery}
                      onChange={(e) => setProductSearchQuery(e.target.value)}
                      placeholder="输入订单号/商品名称/商品ID/SKU查询"
                      className="w-full pl-9 pr-3 py-2 border border-border rounded-lg text-sm"
                    />
                  </div>

                  {/* Search Results Dropdown */}
                  {productSearchQuery && filteredProducts.length > 0 && (
                    <div className="mt-1 max-h-48 overflow-y-auto border border-border rounded-lg bg-white shadow-lg">
                      {filteredProducts.slice(0, 10).map((product) => (
                        <button
                          key={product.id}
                          type="button"
                          onClick={() => handleProductSelect(product.id)}
                          className="w-full px-3 py-2 text-left hover:bg-blue-50 border-b border-border last:border-b-0 transition-colors"
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
                              {product.orderNumber}
                            </span>
                            {product.sku && (
                              <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                                SKU: {product.sku}
                              </span>
                            )}
                          </div>
                          <div className="text-sm text-foreground truncate">
                            {product.name}
                          </div>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            ID: {product.id}
                          </div>
                        </button>
                      ))}
                      {filteredProducts.length > 10 && (
                        <div className="px-3 py-2 text-xs text-muted-foreground text-center bg-muted">
                          还有 {filteredProducts.length - 10} 个结果...
                        </div>
                      )}
                    </div>
                  )}

                  {productSearchQuery && filteredProducts.length === 0 && (
                    <div className="mt-1 px-3 py-2 border border-border rounded-lg bg-amber-50 text-xs text-amber-800 text-center">
                      未找到匹配的商品
                    </div>
                  )}
                </div>

                {/* Manual Product Name */}
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">
                    商品名称 *
                  </label>
                  <input
                    type="text"
                    value={newMapping.productName}
                    onChange={(e) =>
                      setNewMapping({ ...newMapping, productName: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-border rounded-lg text-sm"
                    placeholder="输入商品名称"
                  />
                </div>

                {/* SKU Selection */}
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">
                    SKU
                  </label>
                  <select
                    value={newMapping.sku}
                    onChange={(e) =>
                      setNewMapping({ ...newMapping, sku: e.target.value })
                    }
                    className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-white"
                  >
                    <option value="">选择SKU</option>
                    {Array.from(new Set(products.filter(p => p.sku).map(p => p.sku))).map((sku) => (
                      <option key={sku} value={sku}>
                        {sku}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Costs */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">
                      采购成本 (R$)
                    </label>
                    <input
                      type="number"
                      value={newMapping.purchaseCost || ""}
                      onChange={(e) =>
                        setNewMapping({
                          ...newMapping,
                          purchaseCost: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-full px-3 py-2 border border-border rounded-lg text-sm"
                      placeholder="0.00"
                      step="0.01"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">
                      国内物流 (R$)
                    </label>
                    <input
                      type="number"
                      value={newMapping.domesticShippingCost || ""}
                      onChange={(e) =>
                        setNewMapping({
                          ...newMapping,
                          domesticShippingCost: parseFloat(e.target.value) || 0,
                        })
                      }
                      className="w-full px-3 py-2 border border-border rounded-lg text-sm"
                      placeholder="0.00"
                      step="0.01"
                    />
                  </div>
                </div>

                {/* Buttons */}
                <div className="flex gap-2 pt-2">
                  <button
                    onClick={handleAddMapping}
                    disabled={!newMapping.productName.trim() || !newMapping.siteId || !newMapping.shopId}
                    className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    保存
                  </button>
                  <button
                    onClick={() => {
                      setShowAddForm(false);
                      setNewMapping({
                        productId: "",
                        productName: "",
                        sku: "",
                        siteId: "",
                        shopId: "",
                        purchaseCost: 0,
                        domesticShippingCost: 0,
                      });
                    }}
                    className="px-4 py-2 bg-muted text-foreground rounded-lg hover:bg-muted/80 transition-colors text-sm"
                  >
                    取消
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Mappings List */}
          {mappings.length > 0 ? (
            <div className="space-y-2">
              {mappings.map((mapping) => (
                <div
                  key={mapping.id}
                  className="p-4 bg-white border border-border rounded-lg hover:shadow-sm transition-shadow"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <h4 className="text-sm font-medium truncate">
                          {mapping.productName}
                        </h4>
                        {mapping.sku && (
                          <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
                            SKU: {mapping.sku}
                          </span>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1 mb-2 text-xs text-muted-foreground">
                        <span>
                          商品ID: <span className="font-medium text-foreground">{mapping.productId}</span>
                        </span>
                        <span>
                          站点: <span className="font-medium text-foreground">{mapping.siteId}</span>
                        </span>
                        <span>
                          店铺: <span className="font-medium text-foreground">{mapping.shopId}</span>
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>
                          采购成本: <span className="font-medium text-foreground">R$ {mapping.purchaseCost.toFixed(2)}</span>
                        </span>
                        <span>
                          国内物流: <span className="font-medium text-foreground">R$ {mapping.domesticShippingCost.toFixed(2)}</span>
                        </span>
                        <span>
                          总计: <span className="font-medium text-primary">R$ {(mapping.purchaseCost + mapping.domesticShippingCost).toFixed(2)}</span>
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => onDeleteMapping(mapping.id)}
                      className="p-2 hover:bg-destructive/10 rounded-lg transition-colors group"
                      title="删除映射"
                    >
                      <Trash2 className="w-4 h-4 text-muted-foreground group-hover:text-destructive" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Package className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p className="text-sm">暂无商品成本映射</p>
              <p className="text-xs mt-1">点击上方按钮添加新映射</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border bg-muted/30">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>共 {mappings.length} 个商品映射</span>
            <span>可在订单项中一键应用已保存的成本</span>
          </div>
        </div>
      </div>
    </div>
  );
}