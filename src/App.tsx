import { useState, useMemo, useEffect } from "react";
import { Filter, RefreshCw, Package } from "lucide-react";
import { OrderCard, Order, OrderItem } from "./components/OrderCard";
import { OrderFilters } from "./components/OrderFilters";
import { StatusFilter } from "./components/StatusFilter";
import { SiteShopSelector } from "./components/SiteShopSelector";
import { Pagination } from "./components/Pagination";
import { OrderSort, SortField, SortDirection } from "./components/OrderSort";
import { SyncProgress } from "./components/SyncProgress";
import { CostStatusFilter, CostStatus } from "./components/CostStatusFilter";
import { ProductCostMappingManager, ProductCostMapping } from "./components/ProductCostMappingManager";
import { OrderDetail } from "./components/OrderDetail";
import { Checkbox } from "./components/ui/checkbox";
import { toast } from "sonner@2.0.3";
import { Toaster } from "./components/ui/sonner";

// Mock data for orders
const mockOrders: Order[] = [
  {
    id: "1",
    orderNumber: "2601069NC34KCU",
    username: "jaciaraoliveir4940",
    status: "pending",
    statusText: "待付款",
    siteId: "tiktok",
    shopId: "shop1",
    orderDate: "2026-01-05",
    shippingFee: 15.50,
    otherFees: 5.00,
    items: [
      {
        id: "1-1",
        productName: "Bolsa de bebê de mãe portátil de grande capacidade",
        color: "Cor de damasco",
        quantity: 1,
        price: 89.90,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
        sku: "1-2",
      },
      {
        id: "1-2",
        productName: "Mochila infantil colorida para escola",
        color: "Azul",
        quantity: 2,
        price: 45.50,
        image: "https://images.unsplash.com/photo-1577655197620-704858b270ac?w=400",
        sku: "1-3",
      }
    ]
  },
  {
    id: "2",
    orderNumber: "2601057YTE9PDY",
    username: "bianca_eloahnpg",
    status: "processing",
    statusText: "已收货",
    siteId: "shopee",
    shopId: "shop2",
    orderDate: "2026-01-06",
    shippingFee: 20.00,
    otherFees: 8.50,
    items: [
      {
        id: "2-1",
        productName: "Bolsa de bebê de mãe portátil de grande capacidade",
        color: "Cor de damasco",
        quantity: 1,
        price: 89.90,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
        sku: "2-1",
      },
      {
        id: "2-2",
        productName: "Mochila Mamãe Novo Estilo Mãe Para Bebê Grande Capacidade",
        color: "Rosa",
        quantity: 2,
        price: 95.00,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
        sku: "2-2",
      },
      {
        id: "2-3",
        productName: "Organizador de fraldas portátil",
        color: "Branco",
        quantity: 1,
        price: 35.80,
        image: "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=400",
        sku: "2-3",
      }
    ]
  },
  {
    id: "3",
    orderNumber: "2601045JUKSH1N",
    username: "a.muticarleze",
    status: "shipped",
    statusText: "运出中",
    siteId: "tiktok",
    shopId: "shop1",
    orderDate: "2026-01-05",
    shippingFee: 12.80,
    otherFees: 3.20,
    items: [
      {
        id: "3-1",
        productName: "Bolsa de bebê de mãe portátil de grande capacidade",
        color: "Verde",
        quantity: 1,
        price: 89.90,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
      },
      {
        id: "3-2",
        productName: "Kit berço portátil de viagem",
        color: "Cinza",
        quantity: 1,
        price: 125.00,
        image: "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=400",
      }
    ]
  },
  {
    id: "4",
    orderNumber: "2601044P04N9DB",
    username: "hayasam",
    status: "processing",
    statusText: "已收货",
    siteId: "amazon",
    shopId: "shop3",
    orderDate: "2026-01-04",
    shippingFee: 25.00,
    otherFees: 10.00,
    items: [
      {
        id: "4-1",
        productName: "Mochila Mamãe Novo Estilo Mãe Para Bebê Grande Capacidade Agasalho Multifuncional",
        color: "Arroz em pó",
        quantity: 1,
        price: 105.50,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
      },
      {
        id: "4-2",
        productName: "Trocador de fraldas dobrável",
        color: "Bege",
        quantity: 1,
        price: 68.00,
        image: "https://images.unsplash.com/photo-1555940280-66b7000c6981?w=400",
      },
      {
        id: "4-3",
        productName: "Porta mamadeira térmico",
        color: "Preto",
        quantity: 3,
        price: 28.50,
        image: "https://images.unsplash.com/photo-1566576721346-d4a3b4eaeb55?w=400",
      }
    ]
  },
  {
    id: "5",
    orderNumber: "2601042K3LMP8V",
    username: "maria.eduarda2345",
    status: "completed",
    statusText: "查看详情",
    siteId: "shopee",
    shopId: "shop2",
    orderDate: "2026-01-03",
    shippingFee: 8.50,
    otherFees: 2.00,
    items: [
      {
        id: "5-1",
        productName: "Bolsa de bebê de mãe portátil de grande capacidade",
        color: "Preto",
        quantity: 1,
        price: 89.90,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
      }
    ]
  },
  {
    id: "6",
    orderNumber: "2601038LL2NP9C",
    username: "fernanda_costa88",
    status: "pending",
    statusText: "待付款",
    siteId: "tiktok",
    shopId: "shop1",
    orderDate: "2026-01-02",
    shippingFee: 22.00,
    otherFees: 7.50,
    items: [
      {
        id: "6-1",
        productName: "Bolsa de bebê de mãe portátil de grande capacidade",
        color: "Azul marinho",
        quantity: 2,
        price: 89.90,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
      },
      {
        id: "6-2",
        productName: "Cestinho organizador para carrinho",
        color: "Cinza claro",
        quantity: 1,
        price: 42.00,
        image: "https://images.unsplash.com/photo-1519181245277-cffeb31da2e3?w=400",
      },
      {
        id: "6-3",
        productName: "Capa de chuva para carrinho de bebê",
        color: "Transparente",
        quantity: 1,
        price: 25.80,
        image: "https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?w=400",
      },
      {
        id: "6-4",
        productName: "Mosquiteiro para carrinho",
        color: "Branco",
        quantity: 1,
        price: 18.90,
        image: "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=400",
      }
    ]
  },
  {
    id: "7",
    orderNumber: "2601032ML9KH4T",
    username: "juliana_mendes01",
    status: "shipped",
    statusText: "运出中",
    siteId: "amazon",
    shopId: "shop4",
    orderDate: "2026-01-01",
    items: [
      {
        id: "7-1",
        productName: "Mochila Mamãe Novo Estilo Mãe Para Bebê Grande Capacidade Agasalho Multifuncional",
        color: "Cinza",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
      },
      {
        id: "7-2",
        productName: "Bolsa de bebê de mãe portátil de grande capacidade",
        color: "Preto",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
      },
      {
        id: "7-3",
        productName: "Mochila infantil colorida",
        color: "Amarelo",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1577655197620-704858b270ac?w=400",
      }
    ]
  },
  {
    id: "8",
    orderNumber: "2601028PP5RT6Y",
    username: "carla.silva99",
    status: "processing",
    statusText: "已收货",
    siteId: "shopee",
    shopId: "shop2",
    orderDate: "2025-12-31",
    items: [
      {
        id: "8-1",
        productName: "Bolsa de bebê de mãe portátil de grande capacidade",
        color: "Rosa",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
      },
      {
        id: "8-2",
        productName: "Necessaire organizadora de higiene",
        color: "Rosa claro",
        quantity: 2,
        image: "https://images.unsplash.com/photo-1566576721346-d4a3b4eaeb55?w=400",
      }
    ]
  },
  {
    id: "9",
    orderNumber: "2601021HH8VB3W",
    username: "amanda_rodrigues",
    status: "completed",
    statusText: "查看详情",
    siteId: "tiktok",
    shopId: "shop1",
    orderDate: "2025-12-30",
    items: [
      {
        id: "9-1",
        productName: "Bolsa de bebê de mãe portátil de grande capacidade",
        color: "Bege",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
      }
    ]
  },
  {
    id: "10",
    orderNumber: "2601019MM2QP7L",
    username: "patricia_alves23",
    status: "pending",
    statusText: "待付款",
    siteId: "amazon",
    shopId: "shop3",
    orderDate: "2025-12-29",
    items: [
      {
        id: "10-1",
        productName: "Mochila Mamãe Novo Estilo Mãe Para Bebê Grande Capacidade Agasalho Multifuncional",
        color: "Verde escuro",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
      },
      {
        id: "10-2",
        productName: "Bolsa térmica para mamadeira dupla",
        color: "Verde água",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1566576721346-d4a3b4eaeb55?w=400",
      },
      {
        id: "10-3",
        productName: "Mini kit primeiros socorros",
        color: "Vermelho",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1603398938378-e54eab446dde?w=400",
      }
    ]
  },
  {
    id: "11",
    orderNumber: "2601015NN9KL2M",
    username: "beatriz_santos77",
    status: "shipped",
    statusText: "运出中",
    siteId: "shopee",
    shopId: "shop5",
    orderDate: "2025-12-28",
    items: [
      {
        id: "11-1",
        productName: "Bolsa de bebê de mãe portátil de grande capacidade",
        color: "Vermelho",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
      },
      {
        id: "11-2",
        productName: "Almofada de amamentação ergonômica",
        color: "Azul bebê",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1522771739844-6a9f6d5f14af?w=400",
      }
    ]
  },
  {
    id: "12",
    orderNumber: "2601012TT6WX8N",
    username: "roberta_lima55",
    status: "processing",
    statusText: "已收货",
    siteId: "tiktok",
    shopId: "shop1",
    orderDate: "2025-12-27",
    items: [
      {
        id: "12-1",
        productName: "Bolsa de bebê de mãe portátil de grande capacidade",
        color: "Cor de damasco",
        quantity: 2,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
      }
    ]
  },
  {
    id: "13",
    orderNumber: "2601008VV3YZ5P",
    username: "lucas_pereira88",
    status: "completed",
    statusText: "查看详情",
    siteId: "amazon",
    shopId: "shop4",
    orderDate: "2025-12-26",
    items: [
      {
        id: "13-1",
        productName: "Mochila Mamãe Novo Estilo Mãe Para Bebê Grande Capacidade Agasalho Multifuncional",
        color: "Preto",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
      },
      {
        id: "13-2",
        productName: "Capa protetora para assento de carro",
        color: "Preto",
        quantity: 2,
        image: "https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?w=400",
      },
      {
        id: "13-3",
        productName: "Espelho retrovisor para bebê",
        color: "Preto",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1519181245277-cffeb31da2e3?w=400",
      }
    ]
  },
  {
    id: "14",
    orderNumber: "2601005QQ1AB9R",
    username: "isabela_gomes12",
    status: "pending",
    statusText: "待付款",
    siteId: "shopee",
    shopId: "shop2",
    orderDate: "2025-12-25",
    items: [
      {
        id: "14-1",
        productName: "Bolsa de bebê de mãe portátil de grande capacidade",
        color: "Marrom",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
      }
    ]
  },
  {
    id: "15",
    orderNumber: "2601001RR7CD4S",
    username: "gabriela_martins34",
    status: "shipped",
    statusText: "运出中",
    siteId: "tiktok",
    shopId: "shop1",
    orderDate: "2025-12-24",
    items: [
      {
        id: "15-1",
        productName: "Bolsa de bebê de mãe portátil de grande capacidade",
        color: "Azul claro",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1677740785568-21a762413949?w=400",
      },
      {
        id: "15-2",
        productName: "Cesto de roupas dobráveis para bebê",
        color: "Listrado azul",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=400",
      },
      {
        id: "15-3",
        productName: "Conjunto de panos de boca 10 unidades",
        color: "Multicolorido",
        quantity: 1,
        image: "https://images.unsplash.com/photo-1555940280-66b7000c6981?w=400",
      }
    ]
  }
];

import { Sidebar } from "./components/Sidebar";



// ... (existing helper function nearby, handled via imports)

export default function App() {
  const [currentView, setCurrentView] = useState<'orders' | 'mappings'>('orders');
  const [searchQuery, setSearchQuery] = useState("");
  const [dateRange, setDateRange] = useState("2025-12-30 至 2026-01-06");
  const [showFilters, setShowFilters] = useState(false);
  const [activeStatus, setActiveStatus] = useState("all");
  const [selectedSite, setSelectedSite] = useState("all");
  const [selectedShop, setSelectedShop] = useState("all");

  // Dynamic Site/Shop Options
  const [siteOptions, setSiteOptions] = useState<{ value: string, label: string }[]>([
    { value: 'all', label: '全部站点' }
  ]);
  const [shopOptions, setShopOptions] = useState<{ value: string, label: string, siteId: string }[]>([]);

  useEffect(() => {
    fetch('http://localhost:8000/api/shops')
      .then(res => res.json())
      .then(data => {
        if (data.sites) setSiteOptions(data.sites);
        if (data.shops) setShopOptions(data.shops);
      })
      .catch(err => console.error("Failed to fetch shops:", err));
  }, []);

  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoadingOrders, setIsLoadingOrders] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5; // 每页显示5个订单
  const [sortField, setSortField] = useState<SortField>('none');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [isSyncing, setIsSyncing] = useState(false);
  const [currentSyncTaskId, setCurrentSyncTaskId] = useState<string | undefined>(undefined);


  const [selectedOrders, setSelectedOrders] = useState<Set<string>>(new Set());
  const [costStatus, setCostStatus] = useState<CostStatus>('all');
  const [selectedOrderDetail, setSelectedOrderDetail] = useState<Order | null>(null);
  const [costMappings, setCostMappings] = useState<ProductCostMapping[]>([]);
  const [showMappingManager, setShowMappingManager] = useState(false);

  // Fetch orders from API
  const fetchOrders = () => {
    setIsLoadingOrders(true);
    fetch('http://localhost:8000/api/orders?limit=100')
      .then(res => res.json())
      .then(data => {
        if (data.orders) {
          // Transform backend order format to frontend Order format
          const transformedOrders: Order[] = data.orders.map((apiOrder: any, index: number) => {
            // Map order status
            const statusMap: Record<string, 'pending' | 'processing' | 'shipped' | 'completed' | 'cancelled'> = {
              'UNPAID': 'pending',
              'READY_TO_SHIP': 'processing',
              'SHIPPED': 'shipped',
              'COMPLETED': 'completed',
              'IN_CANCEL': 'cancelled',
              'CANCELLED': 'cancelled',
              'TO_RETURN': 'cancelled',
              'PROCESSED': 'processing',
              'TO_CONFIRM_RECEIVE': 'shipped',
              'RETRY_SHIP': 'processing',
            };
            const statusTextMap: Record<string, string> = {
              'UNPAID': '待付款',
              'READY_TO_SHIP': '待出货',
              'SHIPPED': '运送中',
              'COMPLETED': '已完成',
              'IN_CANCEL': '取消中',
              'CANCELLED': '已取消',
              'TO_RETURN': '退货中',
              'PROCESSED': '已处理',
              'TO_CONFIRM_RECEIVE': '运送中',
              'RETRY_SHIP': '重新发货',
            };

            // Extract items from API response
            const items: OrderItem[] = (apiOrder.item_list || []).map((item: any, itemIndex: number) => ({
              id: `${apiOrder.order_sn}-${item.item_id || itemIndex}`,
              productName: item.item_name || '未知商品',
              color: item.model_name || '',
              quantity: item.model_quantity_purchased || 1,
              price: item.model_discounted_price || 0,
              image: item.image_info?.image_url || 'https://via.placeholder.com/80',
              sku: item.model_sku || item.item_sku || '',
              purchaseCost: item.purchase_cost || 0,
              domesticShippingCost: item.domestic_shipping_cost || 0,
            }));

            // Extract shop_id from raw_data or use a default
            const shopId = apiOrder.shop_id ? String(apiOrder.shop_id) : '';

            // Find shop's region as siteId
            const shop = shopOptions.find(s => s.value === shopId);
            const siteId = shop?.siteId || '';
            const shopName = shop?.label || '';

            // Find site name
            const site = siteOptions.find(s => s.value === siteId);
            const siteName = site?.label || '';

            const rawStatus = (apiOrder.order_status || '').trim();
            const mappedStatus = statusMap[rawStatus] || 'processing';
            const mappedStatusText = statusTextMap[rawStatus] || rawStatus;

            const financials = apiOrder.financials || {};

            // Calculate Net Shipping for display purposes to match Detail View
            // (Est Shipping - Actual Shipping)
            // Note: Use financials.estimated_shipping_fee if available (from escrow), else fallback to order level
            const estShip = financials.estimated_shipping_fee !== undefined ? financials.estimated_shipping_fee : (apiOrder.estimated_shipping_fee || 0);
            const actShip = financials.actual_shipping_fee || 0;
            const netShipping = estShip - actShip;

            const currency = apiOrder.currency || 'BRL';
            const fallbackRates: { [key: string]: number } = {
              'BRL': 1.25, 'USD': 7.2, 'SGD': 5.3, 'MYR': 1.6,
              'PHP': 0.13, 'IDR': 0.00046, 'THB': 0.2, 'VND': 0.00029, 'TWD': 0.23,
              'CNY': 1
            };
            const exchangeRate = fallbackRates[currency] || 1;

            return {
              id: apiOrder.order_sn || `order-${index}`,
              orderNumber: apiOrder.order_sn || '',
              username: apiOrder.buyer_username || '',
              status: mappedStatus,
              statusText: mappedStatusText,
              siteId: siteId,
              siteName: siteName,
              shopId: shopId,
              shopName: shopName,
              orderDate: apiOrder.create_time
                ? new Date(apiOrder.create_time * 1000).toISOString().split('T')[0]
                : '',
              items: items.length > 0 ? items : [{
                id: `${apiOrder.order_sn}-default`,
                productName: '商品信息加载中',
                color: '',
                quantity: 1,
                price: apiOrder.total_amount || 0,
                image: 'https://via.placeholder.com/80',
              }],
              shippingFee: netShipping,
              otherFees: financials.total_fees || 0,
              estimatedRevenue: financials.order_income, // Use accurate revenue from backend
              manualTotalCost: apiOrder.total_cost || undefined, // 采购总成本（订单级别）
              currency: currency,
              exchangeRate: exchangeRate
            };
          });
          setOrders(transformedOrders);
        }
        setIsLoadingOrders(false);
      })
      .catch(err => {
        console.error("Failed to fetch orders:", err);
        setIsLoadingOrders(false);
      });
  };

  useEffect(() => {
    fetchOrders();
  }, [shopOptions]);

  // Helper function to check if an order has cost recorded
  const hasOrderCostRecorded = (order: Order): boolean => {
    // Check if all items have both purchaseCost and domesticShippingCost
    return order.items.every(item =>
      (item.purchaseCost !== undefined && item.purchaseCost > 0) ||
      (item.domesticShippingCost !== undefined && item.domesticShippingCost > 0)
    );
  };

  // Calculate status counts based on current site/shop selection
  const statusCounts = useMemo(() => {
    let filteredByLocation = orders;

    // Filter by site
    if (selectedSite !== 'all') {
      filteredByLocation = filteredByLocation.filter(order => order.siteId === selectedSite);
    }

    // Filter by shop
    if (selectedShop !== 'all') {
      filteredByLocation = filteredByLocation.filter(order => order.shopId === selectedShop);
    }

    const counts: Record<string, number> = {
      all: filteredByLocation.length,
      pending: 0,
      processing: 0,
      shipped: 0,
      completed: 0,
      cancelled: 0,
    };

    filteredByLocation.forEach(order => {
      counts[order.status] = (counts[order.status] || 0) + 1;
    });

    return counts;
  }, [selectedSite, selectedShop, orders]);

  // Reset to page 1 when filters change
  useMemo(() => {
    setCurrentPage(1);
  }, [searchQuery, activeStatus, selectedSite, selectedShop, costStatus]);

  // Calculate cost status counts from the base filtered orders (before cost filter)
  const costStatusCounts = useMemo(() => {
    let baseFiltered = orders;

    // Apply same site/shop/status/search filters as main filter
    if (selectedSite !== 'all') {
      baseFiltered = baseFiltered.filter(order => order.siteId === selectedSite);
    }

    if (selectedShop !== 'all') {
      baseFiltered = baseFiltered.filter(order => order.shopId === selectedShop);
    }

    if (activeStatus !== 'all') {
      baseFiltered = baseFiltered.filter(order => order.status === activeStatus);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      baseFiltered = baseFiltered.filter(order =>
        order.orderNumber.toLowerCase().includes(query) ||
        order.statusText.toLowerCase().includes(query) ||
        order.items.some(item => item.productName.toLowerCase().includes(query))
      );
    }

    const recorded = baseFiltered.filter(order => hasOrderCostRecorded(order)).length;
    const unrecorded = baseFiltered.length - recorded;

    return {
      total: baseFiltered.length,
      recorded,
      unrecorded
    };
  }, [orders, selectedSite, selectedShop, activeStatus, searchQuery]);

  // Filter orders based on all criteria
  const filteredOrders = useMemo(() => {
    let filtered = orders;

    // Filter by site
    if (selectedSite !== 'all') {
      filtered = filtered.filter(order => order.siteId === selectedSite);
    }

    // Filter by shop
    if (selectedShop !== 'all') {
      filtered = filtered.filter(order => order.shopId === selectedShop);
    }

    // Filter by status
    if (activeStatus !== 'all') {
      filtered = filtered.filter(order => order.status === activeStatus);
    }

    // Filter by cost status
    if (costStatus !== 'all') {
      filtered = filtered.filter(order => {
        const hasCost = hasOrderCostRecorded(order);
        return costStatus === 'recorded' ? hasCost : !hasCost;
      });
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(order =>
        order.orderNumber.toLowerCase().includes(query) ||
        order.statusText.toLowerCase().includes(query) ||
        order.items.some(item => item.productName.toLowerCase().includes(query))
      );
    }

    // Sort orders
    if (sortField !== 'none') {
      filtered = [...filtered].sort((a, b) => {
        let aValue = 0;
        let bValue = 0;

        if (sortField === 'productTotal') {
          // 商品总额
          aValue = a.items.reduce((sum, item) => sum + (item.price || 0) * item.quantity, 0);
          bValue = b.items.reduce((sum, item) => sum + (item.price || 0) * item.quantity, 0);
        } else if (sortField === 'purchaseCost') {
          // 采购总成本
          aValue = a.manualTotalCost !== undefined
            ? a.manualTotalCost
            : a.items.reduce((sum, item) => sum + ((item.purchaseCost || 0) + (item.domesticShippingCost || 0)) * item.quantity, 0);
          bValue = b.manualTotalCost !== undefined
            ? b.manualTotalCost
            : b.items.reduce((sum, item) => sum + ((item.purchaseCost || 0) + (item.domesticShippingCost || 0)) * item.quantity, 0);
        } else if (sortField === 'shippingFee') {
          // 预估运费总额
          aValue = a.shippingFee || 0;
          bValue = b.shippingFee || 0;
        } else if (sortField === 'otherFees') {
          // 费用
          aValue = a.otherFees || 0;
          bValue = b.otherFees || 0;
        } else if (sortField === 'revenue') {
          // 预估订单收入
          // Helper to get revenue logic
          const getRevenue = (order: Order) => {
            const productTotal = order.items.reduce((sum, item) => sum + (item.price || 0) * item.quantity, 0);
            return order.estimatedRevenue !== undefined
              ? order.estimatedRevenue
              : (productTotal - (order.shippingFee || 0) - (order.otherFees || 0));
          };
          aValue = getRevenue(a);
          bValue = getRevenue(b);
        } else if (sortField === 'profit') {
          // 预估利润
          // Formula: (Revenue * ExchangeRate) - Cost
          const calculateProfit = (order: Order) => {
            const productTotal = order.items.reduce((sum, item) => sum + (item.price || 0) * item.quantity, 0);

            // Revenue (Native Currency)
            const revenue = order.estimatedRevenue !== undefined
              ? order.estimatedRevenue
              : (productTotal - (order.shippingFee || 0) - (order.otherFees || 0));

            // Cost (RMB)
            const totalCost = order.manualTotalCost !== undefined
              ? order.manualTotalCost
              : order.items.reduce((sum, item) => sum + ((item.purchaseCost || 0) + (item.domesticShippingCost || 0)) * item.quantity, 0);

            // Exchange Rate
            const rate = order.exchangeRate || 1;

            return (revenue * rate) - totalCost;
          };

          aValue = calculateProfit(a);
          bValue = calculateProfit(b);
        }

        if (sortDirection === 'asc') {
          return aValue - bValue;
        } else {
          return bValue - aValue;
        }
      });
    }

    return filtered;
  }, [searchQuery, activeStatus, selectedSite, selectedShop, orders, sortField, sortDirection, costStatus]);

  // Calculate pagination
  const totalPages = Math.ceil(filteredOrders.length / itemsPerPage);
  const paginatedOrders = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return filteredOrders.slice(startIndex, endIndex);
  }, [filteredOrders, currentPage, itemsPerPage]);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleViewDetails = (orderId: string) => {
    const order = orders.find(o => o.id === orderId);
    if (order) {
      setSelectedOrderDetail(order);
    }
  };

  const handleItemCostUpdate = (orderId: string, itemId: string, purchaseCost: number, domesticShippingCost: number) => {
    // 更新前端状态
    setOrders(prevOrders =>
      prevOrders.map(order => {
        if (order.id === orderId) {
          return {
            ...order,
            items: order.items.map(item =>
              item.id === itemId
                ? { ...item, purchaseCost, domesticShippingCost }
                : item
            )
          };
        }
        return order;
      })
    );

    // 找到订单和订单项信息，保存到数据库
    const order = orders.find(o => o.id === orderId);
    const item = order?.items.find(i => i.id === itemId);
    if (order && item) {
      // 从 itemId 提取 item_id（格式：order_sn-item_id）
      const itemIdParts = itemId.split('-');
      const numericItemId = parseInt(itemIdParts[itemIdParts.length - 1]) || 0;

      fetch(`http://localhost:8000/api/order/${orderId}/items/cost`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify([{
          item_id: numericItemId,
          model_id: 0,
          sourcing_price: purchaseCost,
          purchase_cost: purchaseCost,
          domestic_shipping_cost: domesticShippingCost,
        }])
      }).catch(err => console.error("Failed to save item cost:", err));
    }
  };

  const handleOrderTotalCostUpdate = (orderId: string, totalCost: number) => {
    // 更新前端状态
    setOrders(prevOrders =>
      prevOrders.map(order =>
        order.id === orderId
          ? { ...order, manualTotalCost: totalCost }
          : order
      )
    );

    // 保存到数据库
    fetch(`http://localhost:8000/api/order/${orderId}/cost`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ total_cost: totalCost })
    }).catch(err => console.error("Failed to save order total cost:", err));
  };

  const handleSyncOrders = () => {
    if (selectedSite === 'all') {
      toast.error("请选择站点");
      return;
    }
    if (selectedShop === 'all') {
      toast.error("请选择店铺");
      return;
    }

    const shopId = selectedShop;

    // Parse date range
    const [startStr, endStr] = dateRange.split(' 至 ');
    if (!startStr || !endStr) {
      toast.error("请选择日期范围");
      return;
    }

    const fromDate = new Date(startStr);
    const toDate = new Date(endStr);

    // Set time to beginning of day and end of day
    fromDate.setHours(0, 0, 0, 0);
    toDate.setHours(23, 59, 59, 999);

    const timeFrom = Math.floor(fromDate.getTime() / 1000);
    const timeTo = Math.floor(toDate.getTime() / 1000);

    // Call API
    fetch('http://localhost:8000/api/sync_orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        shop_id: parseInt(shopId),
        time_from: timeFrom,
        time_to: timeTo
      })
    })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'accepted') {
          setCurrentSyncTaskId(data.task_id);
          setIsSyncing(true);
          toast.info("同步任务已开始");
        } else {
          toast.error("同步启动失败");
        }
      })
      .catch(err => {
        console.error("Sync error:", err);
        toast.error("同步请求失败");
      });
  };

  const handleSyncComplete = () => {
    setIsSyncing(false);
    setCurrentSyncTaskId(undefined);
    toast.success("订单已同步成功");
    fetchOrders(); // Reload orders
  };

  const handleDateRangeChange = (range: string) => {
    setDateRange(range);
    toast.success(`日期范围已更新: ${range}`);
  };

  const handleSortChange = (field: SortField) => {
    if (field === 'none') {
      setSortField('none');
      setSortDirection('desc');
    } else if (sortField === field) {
      // Toggle direction if clicking the same field
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New field, default to descending
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const handleOrderSelection = (orderId: string, selected: boolean) => {
    setSelectedOrders(prev => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(orderId);
      } else {
        newSet.delete(orderId);
      }
      return newSet;
    });
  };

  const handleSelectAll = (selected: boolean) => {
    if (selected) {
      setSelectedOrders(new Set(paginatedOrders.map(order => order.id)));
    } else {
      setSelectedOrders(new Set());
    }
  };

  const handleSyncSelected = () => {
    if (selectedOrders.size === 0) {
      toast.error("请先选择要同步的订单");
      return;
    }

    const itemsToSync: { order_sn: string, shop_id: number }[] = [];
    selectedOrders.forEach(orderId => {
      const order = orders.find(o => o.id === orderId);
      if (order) {
        // Ensure shopId is valid number. If it's missing or invalid, we might skip or error.
        // Assuming shopId is stored as string in Order but numeric in nature.
        const sId = parseInt(order.shopId);
        if (!isNaN(sId)) {
          itemsToSync.push({
            order_sn: order.orderNumber,
            shop_id: sId
          });
        }
      }
    });

    if (itemsToSync.length === 0) {
      toast.error("无法获取选中订单的店铺信息");
      return;
    }

    fetch('http://localhost:8000/api/sync_batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: itemsToSync })
    })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'accepted') {
          setCurrentSyncTaskId(data.task_id);
          setIsSyncing(true);
          toast.info("同步任务已开始");
        } else {
          toast.error("同步启动失败");
        }
      })
      .catch(err => {
        console.error("Batch sync error:", err);
        toast.error("同步请求失败");
      });
  };

  const allSelected = paginatedOrders.length > 0 && paginatedOrders.every(order => selectedOrders.has(order.id));
  const someSelected = paginatedOrders.some(order => selectedOrders.has(order.id)) && !allSelected;

  const handleAddMapping = (mapping: Omit<ProductCostMapping, "id" | "createdAt">) => {
    const newMapping: ProductCostMapping = {
      ...mapping,
      id: `mapping-${Date.now()}`,
      createdAt: new Date().toISOString(),
    };
    setCostMappings(prev => [...prev, newMapping]);
    toast.success(`已添加商品成本映射: ${mapping.productName}`);
  };

  const handleDeleteMapping = (id: string) => {
    setCostMappings(prev => prev.filter(m => m.id !== id));
    toast.success("已删除成本映射");
  };

  const handleSaveMapping = (productId: string, productName: string, sku: string | undefined, siteId: string, shopId: string, purchaseCost: number, domesticShippingCost: number) => {
    const existingMapping = costMappings.find(
      m => m.productId === productId && m.siteId === siteId && m.shopId === shopId
    );

    if (existingMapping) {
      setCostMappings(prev =>
        prev.map(m =>
          m.id === existingMapping.id
            ? { ...m, purchaseCost, domesticShippingCost, sku }
            : m
        )
      );
      toast.success("已更新成本映射");
    } else {
      handleAddMapping({ productId, productName, sku, siteId, shopId, purchaseCost, domesticShippingCost });
    }
  };

  // Extract unique products from all orders
  const availableProducts = useMemo(() => {
    const productMap = new Map<string, { id: string; name: string; sku?: string }>();

    orders.forEach(order => {
      order.items.forEach(item => {
        if (!productMap.has(item.id)) {
          productMap.set(item.id, {
            id: item.id,
            name: item.productName,
            sku: item.sku,
          });
        }
      });
    });

    return Array.from(productMap.values());
  }, [orders]);

  return (
    <div className="flex h-screen w-full bg-gray-50 overflow-hidden">
      <Toaster />
// SyncOrderModal removed

      <Sidebar activeTab={currentView} onTabChange={setCurrentView} />

      <main className="flex-1 flex flex-col h-screen overflow-y-auto" style={{ marginLeft: '264px' }}>
        <SyncProgress
          isVisible={isSyncing}
          taskId={currentSyncTaskId}
          onComplete={handleSyncComplete}
        />

        {/* 订单详情视图 */}
        {selectedOrderDetail ? (
          <div className="flex-1 p-4 sm:p-6 lg:p-8">
            <OrderDetail
              orderSn={selectedOrderDetail.orderNumber}
              shopId={selectedOrderDetail.shopId}
              shopRegion={selectedOrderDetail.siteId}
              shopName={shopOptions.find(s => s.value === selectedOrderDetail.shopId)?.label}
              onBack={() => setSelectedOrderDetail(null)}
            />
          </div>
        ) : currentView === 'orders' ? (
          <div className="flex-1 p-4 sm:p-6 lg:p-8">
            <div className="max-w-6xl mx-auto space-y-6">
              {/* Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-2xl font-bold tracking-tight text-gray-900">我的订单</h1>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentView('mappings')}
                    className="hidden sm:flex items-center gap-2 px-4 py-2 bg-white border border-border rounded-lg hover:bg-muted transition-colors text-sm font-medium text-gray-700 shadow-sm"
                  >
                    <Package className="w-4 h-4" />
                    成本映射管理
                  </button>
                  <button
                    onClick={() => setShowFilters(!showFilters)}
                    className="sm:hidden p-2 hover:bg-muted rounded-lg transition-colors"
                    aria-label="Toggle filters"
                  >
                    <Filter className="size-5" />
                  </button>
                </div>
              </div>

              {/* Site and Shop Selector */}
              <div className="mb-4">
                <SiteShopSelector
                  selectedSite={selectedSite}
                  selectedShop={selectedShop}
                  onSiteChange={setSelectedSite}
                  onShopChange={setSelectedShop}
                  sites={siteOptions}
                  shops={shopOptions}
                />
              </div>

              {/* Filters */}
              <div className={`${showFilters ? 'block' : 'hidden'} sm:block space-y-4`}>
                <OrderFilters
                  searchQuery={searchQuery}
                  onSearchChange={setSearchQuery}
                  dateRange={dateRange}
                  onDateRangeChange={handleDateRangeChange}
                  onSync={handleSyncOrders}
                />
                <StatusFilter
                  activeStatus={activeStatus}
                  onStatusChange={setActiveStatus}
                  statusCounts={statusCounts}
                />
                <CostStatusFilter
                  activeCostStatus={costStatus}
                  onCostStatusChange={setCostStatus}
                  costStatusCounts={costStatusCounts}
                />
                <div className="flex justify-end">
                  <OrderSort
                    onSortChange={handleSortChange}
                    sortField={sortField}
                    sortDirection={sortDirection}
                  />
                </div>
              </div>

              {/* Order Count & Actions */}
              <div className="flex items-center justify-between flex-wrap gap-3 pt-2">
                <div className="flex items-center gap-4">
                  {paginatedOrders.length > 0 && (
                    <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-gray-200">
                      <Checkbox
                        checked={allSelected}
                        onCheckedChange={(checked) => handleSelectAll(checked === true)}
                        aria-label="全选"
                        className={someSelected && !allSelected ? "data-[state=checked]:bg-primary" : ""}
                      />
                      <span className="text-sm text-gray-600 font-medium">全选</span>
                    </div>
                  )}

                  <h2 className="text-sm text-muted-foreground">
                    {searchQuery && (
                      <span>
                        搜索 "<span className="font-medium text-foreground">{searchQuery}</span>" 找到 {filteredOrders.length} 个结果
                      </span>
                    )}
                    {!searchQuery && (
                      <span>共 {filteredOrders.length} 个订单</span>
                    )}
                    {selectedOrders.size > 0 && (
                      <span className="ml-2 text-primary font-medium">
                        (已选 {selectedOrders.size} 个)
                      </span>
                    )}
                  </h2>
                </div>

                <div className="flex items-center gap-2">
                  {selectedOrders.size > 0 && (
                    <button
                      onClick={handleSyncSelected}
                      className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm shadow-sm"
                    >
                      <RefreshCw className="w-4 h-4" />
                      同步选中订单
                    </button>
                  )}
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery("")}
                      className="text-sm text-primary hover:underline"
                    >
                      清除搜索
                    </button>
                  )}
                </div>
              </div>

              {/* Orders List */}
              <div className="space-y-4 pb-8">
                {paginatedOrders.length > 0 ? (
                  paginatedOrders.map((order) => (
                    <OrderCard
                      key={order.id}
                      order={order}
                      onViewDetails={handleViewDetails}
                      onItemCostUpdate={handleItemCostUpdate}
                      onOrderTotalCostUpdate={handleOrderTotalCostUpdate}
                      isSelected={selectedOrders.has(order.id)}
                      onSelectionChange={handleOrderSelection}
                      costMappings={costMappings}
                      onSaveMapping={handleSaveMapping}
                    />
                  ))
                ) : (
                  <div className="text-center py-20 bg-white rounded-xl border border-dashed border-gray-300">
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-gray-100">
                      <Package className="h-6 w-6 text-gray-400" />
                    </div>
                    <h3 className="mt-2 text-sm font-semibold text-gray-900">暂无订单</h3>
                    <p className="mt-1 text-sm text-gray-500">
                      {searchQuery ? '没有找到匹配的订单，请尝试其他搜索词。' : '当前筛选条件下没有订单。'}
                    </p>
                  </div>
                )}
              </div>

              {/* Pagination */}
              {paginatedOrders.length > 0 && (
                <div className="mt-6">
                  <Pagination
                    currentPage={currentPage}
                    totalPages={totalPages}
                    totalItems={filteredOrders.length}
                    itemsPerPage={itemsPerPage}
                    onPageChange={handlePageChange}
                  />
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Mappings View */
          <div className="flex-1 flex flex-col p-4 sm:p-6 lg:p-8 h-full overflow-hidden bg-gray-50">
            <ProductCostMappingManager
              mappings={costMappings}
              onAddMapping={handleAddMapping}
              onDeleteMapping={handleDeleteMapping}
              sites={siteOptions}
              shops={shopOptions}
              products={availableProducts}
              orders={orders}
              mode="embedded"
            />
          </div>
        )}
      </main>
    </div>
  );
}