
import React, { useState, useEffect } from 'react';
import { Search, ChevronDown, Star, Grid, LayoutList, Package, Loader2, Languages, RefreshCw, ChevronLeft, ChevronRight, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { cn } from './ui/utils';
import { Button } from './ui/button';

// -----------------------------------------------------------------------------
// 类型定义
// -----------------------------------------------------------------------------

interface Product {
    id: string;
    image: string;
    site: string;
    sellerType: string;
    category: string;
    subCategory: string; // 二级类目
    keywords: string;
    description: string;
    translatedDescription?: string; // 翻译后的中文描述
    translatedKeywords?: string;    // 翻译后的中文关键词
    minPrice: string;
    maxPrice: string;
    currency: string;    // 货币符号
    reason: string;      // 推荐理由
    isFavorite: boolean; // 是否收藏
}

// -----------------------------------------------------------------------------
// 组件实现
// -----------------------------------------------------------------------------

export function SelectionGuide() {
    // 菜单激活状态
    const [activeMenu, setActiveMenu] = useState('site-trends');

    // 筛选条件状态
    const [site, setSite] = useState('TW');            // 站点
    const [category, setCategory] = useState('All');   // 品类 (英文 Value)
    const [sellerType, setSellerType] = useState('All');// 卖家类型
    const [searchQuery, setSearchQuery] = useState('');// 搜索关键词
    const [minPrice, setMinPrice] = useState('');      // 最低价
    const [maxPrice, setMaxPrice] = useState('');      // 最高价
    const [onlyFavorites, setOnlyFavorites] = useState(false); // 仅查看收藏

    // 数据状态
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(false);
    const [total, setTotal] = useState(0);             // 总记录数
    const [page, setPage] = useState(1);               // 当前页码
    const [limit, setLimit] = useState(20);            // 每页条数
    const [totalPages, setTotalPages] = useState(0);   // 总页数

    // 动态选项状态
    const [categoryOptions, setCategoryOptions] = useState<{ value: string, label: string }[]>([]);
    const [sellerTypeOptions, setSellerTypeOptions] = useState<string[]>([]);

    // 翻译相关状态
    const [translatingIds, setTranslatingIds] = useState<Set<string>>(new Set());
    const [isChineseMode, setIsChineseMode] = useState(false); // 全局中文模式开关
    const [batchTranslating, setBatchTranslating] = useState(false); // 批量翻译加载状态

    const [errorMsg, setErrorMsg] = useState('');

    // -----------------------------------------------------------------------------
    // 数据获取逻辑
    // -----------------------------------------------------------------------------

    // 获取商品列表
    const fetchProducts = async () => {
        setLoading(true);
        setErrorMsg('');
        // 切换页面时，暂时保持中文模式状态，但不自动触发翻译（除非用户希望如此）。
        // 现在的逻辑是：如果模式开启，新数据加载后，如果没有翻译，则显示原文。
        // 用户需要再次点击开关或触发翻译。或者我们可以自动触发。
        // 为了体验，这里设为：翻页后保留模式，显示的文字如果没翻译则显示原文，
        // 并可以提供一个显眼的“加载翻译”提示，或者在模式开启时自动请求翻译。
        // 鉴于API成本，我们先不自动请求，而是让用户手动切一下，或者保持模式但显示原文。
        // 简单起见：翻页不重置模式，但需要重新检测是否需要翻译。
        // 修正：翻页重置模式可能更安全？不，用户希望“默认展示翻译后的”。
        // 那么：翻页后，如果 isChineseMode 为 true，则自动触发批量翻译。

        try {
            const params = new URLSearchParams({
                page: page.toString(),
                limit: limit.toString(),
                site,
                category,
                seller_type: sellerType,
                only_favorites: onlyFavorites ? 'true' : 'false'
            });

            if (searchQuery) params.append('keyword', searchQuery);
            if (minPrice) params.append('min_price', minPrice);
            if (maxPrice) params.append('max_price', maxPrice);

            const response = await fetch(`http://localhost:9000/api/selection/products?${params.toString()}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            if (data.products) {
                setProducts(data.products);
                setTotal(data.total);
                setTotalPages(data.totalPages);
            } else {
                setProducts([]);
                setTotal(0);
            }
        } catch (error: any) {
            console.error("Failed to fetch selection products:", error);
            setErrorMsg(error.message || "Fetch failed");
        } finally {
            setLoading(false);
        }
    };

    // 监听筛选条件变化
    useEffect(() => {
        fetchProducts();
    }, [page, limit, site, category, sellerType, onlyFavorites]);

    // 菜单折叠状态 (key: menu group id)
    const [expandedMenus, setExpandedMenus] = useState<Set<string>>(new Set(['goods', 'selection']));

    const toggleMenu = (menuId: string) => {
        setExpandedMenus(prev => {
            const next = new Set(prev);
            if (next.has(menuId)) next.delete(menuId);
            else next.add(menuId);
            return next;
        });
    };

    const [languageOverrides, setLanguageOverrides] = useState<Set<string>>(new Set());

    // 每次切换全局模式时，清空个别行的覆盖状态，避免逻辑混乱
    useEffect(() => {
        setLanguageOverrides(new Set());
    }, [isChineseMode]);

    // 侧边栏展开状态
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);

    // 如果在中文模式下加载了新数据，尝试自动翻译（可选，这里先手动）
    // 为了满足“默认展示翻译后的”，最好是自动翻译。
    useEffect(() => {
        if (isChineseMode && products.length > 0) {
            // 检查是否有未翻译的（描述或关键词）
            const needsTrans = products.some(p => !p.translatedDescription || !p.translatedKeywords);
            if (needsTrans && !batchTranslating && !loading) {
                handleBatchTranslate(products.filter(p => !p.translatedDescription || !p.translatedKeywords));
            }
        }
    }, [products, isChineseMode]);
    // 注意：这里可能会在 products 更新后立即触发 effect。

    // 初始化加载选项
    useEffect(() => {
        const fetchOptions = async () => {
            try {
                const res = await fetch('http://localhost:9000/api/selection/categories');
                const data = await res.json();
                if (data.categories) setCategoryOptions(data.categories);
            } catch (e) { console.error(e); }

            try {
                const res = await fetch('http://localhost:9000/api/selection/seller-types');
                const data = await res.json();
                if (data.sellerTypes) setSellerTypeOptions(data.sellerTypes);
            } catch (e) { console.error(e); }
        };
        fetchOptions();
    }, []);

    // -----------------------------------------------------------------------------
    // 事件处理
    // -----------------------------------------------------------------------------

    const handleSearch = () => {
        setPage(1);
        fetchProducts();
    };

    const toggleFavorite = async (productId: string, currentStatus: boolean) => {
        try {
            setProducts(products.map(p =>
                p.id === productId ? { ...p, isFavorite: !currentStatus } : p
            ));

            const res = await fetch('http://localhost:9000/api/selection/favorite', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ product_id: parseInt(productId), is_favorite: !currentStatus })
            });

            if (!res.ok) throw new Error('Failed to update favorite');
        } catch (e) {
            console.error(e);
            setProducts(products.map(p =>
                p.id === productId ? { ...p, isFavorite: currentStatus } : p
            ));
        }
    };

    // 单个翻译 (保留功能)
    const handleTranslate = async (id: string, text: string) => {
        if (translatingIds.has(id)) return;
        setTranslatingIds(prev => new Set(prev).add(id));
        try {
            const res = await fetch('http://localhost:9000/api/selection/translate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            const data = await res.json();
            if (data.translatedText && !data.translatedText.startsWith("Error")) {
                setProducts(prev => prev.map(p =>
                    p.id === id ? { ...p, translatedDescription: data.translatedText } : p
                ));
            } else {
                alert(`翻译失败: ${data.translatedText}`);
            }
        } catch (e: any) {
            alert(e.message);
        } finally {
            setTranslatingIds(prev => {
                const next = new Set(prev);
                next.delete(id);
                return next;
            });
        }
    };

    // 批量翻译核心逻辑
    const handleBatchTranslate = async (itemsToTranslate: Product[]) => {
        if (itemsToTranslate.length === 0) return;

        setBatchTranslating(true);
        try {
            // 准备数据：构建符合后端 BatchTranslateRequest 的 items 数组
            const items = itemsToTranslate.flatMap(p => [
                { id: p.id, text: p.description || "", field: "description" },
                { id: p.id, text: p.keywords || "", field: "keywords" }
            ]);

            // 记录ID顺序以便匹配并不是必须的，因为 flatMap 顺序固定，但为了后续 Map 映射方便，可以复用逻辑
            // 这里的 ids 其实只是用来最后映射回 state 的，逻辑可以保持不变，只要知道 items 是成对生成的
            const ids = itemsToTranslate.map(p => p.id);

            const res = await fetch('http://localhost:9000/api/selection/translate/batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items })
            });

            const data = await res.json();
            // 注意：items 长度是 itemsToTranslate.length * 2
            if (data.translations && data.translations.length === items.length) {
                setProducts(prev => {
                    const descMap = new Map();
                    const keyMap = new Map();

                    ids.forEach((id, idx) => {
                        // 对应的翻译结果索引
                        const baseIdx = idx * 2;
                        descMap.set(id, data.translations[baseIdx]);
                        keyMap.set(id, data.translations[baseIdx + 1]);
                    });

                    return prev.map(p =>
                        descMap.has(p.id) ? {
                            ...p,
                            translatedDescription: descMap.get(p.id),
                            translatedKeywords: keyMap.get(p.id)
                        } : p
                    );
                });
            }
        } catch (e) {
            console.error("Batch translate failed", e);
        } finally {
            setBatchTranslating(false);
        }
    };

    // 单行点击切换语言（中文模式下看原文，原文模式下看中文）
    const toggleRowLanguage = async (e: React.MouseEvent, product: Product) => {
        e.stopPropagation(); // 防止事件冒泡

        const isCurrentlyOverridden = languageOverrides.has(product.id);
        // 目标状态：是否显示翻译
        // 中文模式(True) && 没Override(False) -> 显示中文。点击 -> Override(True) -> 显示原文(False)
        // 中文模式(True) && 有Override(True) -> 显示原文。点击 -> Override(False) -> 显示中文(True)
        // 原文模式(False) && 没Override(False) -> 显示原文。点击 -> Override(True) -> 显示中文(True)
        const willShowTranslated = isChineseMode ? isCurrentlyOverridden : !isCurrentlyOverridden;

        if (willShowTranslated) {
            // 如果要显示中文，但还没有翻译，则触发翻译
            if (!product.translatedDescription || !product.translatedKeywords) {
                await handleBatchTranslate([product]);
            }
        }

        setLanguageOverrides(prev => {
            const next = new Set(prev);
            if (next.has(product.id)) next.delete(product.id);
            else next.add(product.id);
            return next;
        });
    };

    // 切换语言模式按钮点击
    const toggleLanguageMode = () => {
        setIsChineseMode(!isChineseMode);
        // 如果开启中文模式，Effect 会自动检测并翻译
    };

    const handlePageChange = (newPage: number) => {
        if (newPage >= 1 && newPage <= totalPages) {
            setPage(newPage);
        }
    };

    const SubMenuItem = ({ id, label }: { id: string, label: string }) => (
        <button
            onClick={() => setActiveMenu(id)}
            className={cn(
                "w-full text-left px-4 py-2 text-sm transition-colors",
                activeMenu === id ? "text-red-500 font-medium bg-red-50/50" : "text-gray-600 hover:text-red-500"
            )}
        >
            {label}
        </button>
    );

    return (
        <div className="flex h-full bg-gray-100 font-sans relative">
            {/* 左侧侧边栏 */}
            <div
                className={cn(
                    "bg-white border-r border-gray-200 flex-shrink-0 overflow-y-auto transition-all duration-300 ease-in-out relative",
                    isSidebarOpen ? "w-64 opacity-100" : "w-0 opacity-0 overflow-hidden border-r-0"
                )}
            >
                {/* 侧边栏收起按钮 */}
                <button
                    onClick={() => setIsSidebarOpen(false)}
                    className="absolute top-2 right-2 p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors z-10"
                    title="收起侧边栏"
                >
                    <PanelLeftClose className="w-4 h-4" />
                </button>

                <div className="p-4 pt-10">
                    <div className="space-y-4">
                        {/* 菜单组 1: 商品推荐 */}
                        <div>
                            <div
                                className="flex items-center justify-between text-gray-700 font-medium mb-2 cursor-pointer hover:bg-gray-50 p-2 rounded transition-colors select-none"
                                onClick={() => toggleMenu('goods')}
                            >
                                <div className="flex items-center gap-2">
                                    <Package className="w-4 h-4" />
                                    <span>商品推荐</span>
                                </div>
                                <ChevronDown className={cn("w-4 h-4 transition-transform duration-200", expandedMenus.has('goods') ? "" : "-rotate-90")} />
                            </div>
                            {expandedMenus.has('goods') && (
                                <div className="pl-4 space-y-1 animate-in slide-in-from-top-2 fade-in duration-200">
                                    <SubMenuItem id="site-trends" label="站点趋势商品" />
                                </div>
                            )}
                        </div>

                        {/* 菜单组 2: 选品精选内容 */}
                        <div>
                            <div
                                className="flex items-center justify-between text-gray-700 font-medium mb-2 cursor-pointer hover:bg-gray-50 p-2 rounded transition-colors select-none"
                                onClick={() => toggleMenu('selection')}
                            >
                                <div className="flex items-center gap-2">
                                    <Grid className="w-4 h-4" />
                                    <span>选品精选内容</span>
                                </div>
                                <ChevronDown className={cn("w-4 h-4 transition-transform duration-200", expandedMenus.has('selection') ? "" : "-rotate-90")} />
                            </div>
                            {expandedMenus.has('selection') && (
                                <div className="pl-4 space-y-1 animate-in slide-in-from-top-2 fade-in duration-200">
                                    <SubMenuItem id="market-weekly" label="市场周报" />
                                    <SubMenuItem id="selection-articles" label="选品推文" />
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* 主内容区域 */}
            <div className="flex-1 flex flex-col overflow-hidden">
                <div className="bg-white p-4 border-b border-gray-200 flex items-start gap-3">
                    {/* 侧边栏展开按钮 (当侧边栏关闭时显示) */}
                    {!isSidebarOpen && (
                        <button
                            onClick={() => setIsSidebarOpen(true)}
                            className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0 mt-0.5"
                            title="展开侧边栏"
                        >
                            <PanelLeftOpen className="w-5 h-5" />
                        </button>
                    )}

                    <div className="bg-orange-50 border border-orange-100 rounded-lg p-3 flex items-start gap-3 flex-1">
                        <div className="bg-orange-100 p-1 rounded-full mt-0.5">
                            <Star className="w-4 h-4 text-orange-500 fill-orange-500" />
                        </div>
                        <div className="text-sm text-gray-700">
                            <p>精选各站点的本地热销趋势，卖家朋友们可以按照站点和品类进行筛选，也可以将意向商品加入收藏夹，方便后续查找。</p>
                        </div>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4">
                    <div className="bg-white rounded-lg shadow-sm">
                        <div className="p-4 border-b border-gray-100 space-y-4">
                            {/* 第一行筛选 */}
                            <div className="flex flex-wrap items-center gap-4">
                                <div className="flex items-center gap-2">
                                    <span className="text-sm text-gray-600">站点</span>
                                    <select
                                        value={site}
                                        onChange={(e) => { setSite(e.target.value); setPage(1); }}
                                        className="border border-gray-300 rounded px-2 py-1.5 text-sm min-w-[100px] bg-white"
                                    >
                                        <option value="TW">TW</option>
                                        <option value="MY">MY</option>
                                        <option value="PH">PH</option>
                                        <option value="TH">TH</option>
                                        <option value="VN">VN</option>
                                        <option value="BR">BR</option>
                                        <option value="All">All Sites</option>
                                    </select>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-sm text-gray-600">品类</span>
                                    <select
                                        value={category}
                                        onChange={(e) => { setCategory(e.target.value); setPage(1); }}
                                        className="border border-gray-300 rounded px-2 py-1.5 text-sm min-w-[150px] bg-white"
                                    >
                                        <option value="All">All</option>
                                        {categoryOptions.map(cat => (
                                            <option key={cat.value} value={cat.value}>{cat.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-sm text-gray-600">卖家类型</span>
                                    <select
                                        value={sellerType}
                                        onChange={(e) => { setSellerType(e.target.value); setPage(1); }}
                                        className="border border-gray-300 rounded px-2 py-1.5 text-sm min-w-[100px] bg-white"
                                    >
                                        <option value="All">All</option>
                                        {sellerTypeOptions.map(type => (
                                            <option key={type} value={type}>{type}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="flex-1 flex justify-end">
                                    <div className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded border border-green-100 flex items-center gap-1">
                                        <span>●</span> 数据更新时间: {new Date().toISOString().split('T')[0]} 查看更新内容
                                    </div>
                                </div>
                            </div>

                            {/* 第二行筛选：搜索、翻译按钮 */}
                            <div className="flex flex-wrap items-center gap-4">
                                <div className="flex items-center gap-2 flex-1 max-w-md">
                                    <span className="text-sm text-gray-600 whitespace-nowrap">搜索</span>
                                    <div className="relative flex-1">
                                        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                        <input
                                            type="text"
                                            placeholder="可搜索关键词、描述、推荐理由"
                                            value={searchQuery}
                                            onChange={(e) => setSearchQuery(e.target.value)}
                                            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                                            className="w-full pl-9 pr-12 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:border-red-500"
                                        />
                                        <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-gray-400">{searchQuery.length} / 30</span>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2">
                                    <span className="text-sm text-gray-600">价格</span>
                                    <input
                                        type="text"
                                        placeholder="最低价"
                                        value={minPrice}
                                        onChange={(e) => setMinPrice(e.target.value)}
                                        className="w-20 px-2 py-1.5 text-sm border border-gray-300 rounded"
                                    />
                                    <span className="text-gray-400">-</span>
                                    <input
                                        type="text"
                                        placeholder="最高价"
                                        value={maxPrice}
                                        onChange={(e) => setMaxPrice(e.target.value)}
                                        className="w-20 px-2 py-1.5 text-sm border border-gray-300 rounded"
                                    />
                                </div>

                                <Button onClick={handleSearch} className="bg-red-500 hover:bg-red-600 text-white px-6">
                                    搜索
                                </Button>

                                <div className="w-px h-6 bg-gray-200 mx-2"></div>

                                {/* 翻译模式开关 */}
                                <Button
                                    onClick={toggleLanguageMode}
                                    variant="outline"
                                    className={cn(
                                        "flex items-center gap-2 border-gray-300",
                                        isChineseMode ? "bg-blue-50 border-blue-200 text-blue-600" : "text-gray-600"
                                    )}
                                    title="开启后将自动翻译本页所有描述"
                                >
                                    {batchTranslating ? (
                                        <RefreshCw className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Languages className="w-4 h-4" />
                                    )}
                                    <span>{isChineseMode ? "中文模式" : "原文模式"}</span>
                                </Button>

                                <div className="flex items-center gap-2 ml-4">
                                    <span className="text-sm text-gray-600">仅看收藏</span>
                                    <div
                                        className={cn(
                                            "w-10 h-5 rounded-full p-0.5 cursor-pointer transition-colors",
                                            onlyFavorites ? "bg-red-500" : "bg-gray-300"
                                        )}
                                        onClick={() => { setOnlyFavorites(!onlyFavorites); setPage(1); }}
                                    >
                                        <div className={cn(
                                            "w-4 h-4 bg-white rounded-full shadow-sm transition-transform transform",
                                            onlyFavorites ? "translate-x-5" : "translate-x-0"
                                        )} />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* 商品数据表格 */}
                        <div className="overflow-x-auto min-h-[400px]">
                            {errorMsg ? (
                                <div className="flex flex-col items-center justify-center h-64 text-red-500">
                                    <p className="font-medium">Error loading data</p>
                                    <p className="text-sm mt-1">{errorMsg}</p>
                                    <Button onClick={fetchProducts} className="mt-4 bg-red-100 text-red-600 hover:bg-red-200">
                                        Retry
                                    </Button>
                                </div>
                            ) : loading ? (
                                <div className="flex items-center justify-center h-64">
                                    <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                                </div>
                            ) : products.length > 0 ? (
                                <table className="w-full text-left">
                                    <thead className="bg-gray-50 text-gray-500 text-sm">
                                        <tr>
                                            <th className="px-6 py-4 font-medium w-20 text-center">收藏</th>
                                            <th className="px-6 py-4 font-medium w-32 text-center">产品</th>
                                            <th className="px-6 py-4 font-medium">卖家类型</th>
                                            <th className="px-6 py-4 font-medium w-48">品类</th>
                                            <th className="px-6 py-4 font-medium w-32">关键词 ({isChineseMode ? "中文" : "原文"})</th>
                                            <th className="px-6 py-4 font-medium w-64">描述 ({isChineseMode ? "中文" : "原文"})</th>
                                            <th className="px-6 py-4 font-medium text-right">最低价</th>
                                            <th className="px-6 py-4 font-medium text-right">最高价</th>
                                            <th className="px-6 py-4 font-medium">推荐理由</th>
                                            <th className="px-4 py-4 w-16"></th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-100">
                                        {products.map((product) => {
                                            // 决定显示的描述和关键词
                                            // 逻辑：全局模式 XOR 覆盖状态
                                            const isOverridden = languageOverrides.has(product.id);
                                            const showTranslated = isChineseMode ? !isOverridden : isOverridden;

                                            const displayDesc = (showTranslated && product.translatedDescription) ? product.translatedDescription : product.description;
                                            const hoverDesc = (showTranslated && product.translatedDescription) ? "点击查看原文" : "点击查看中文";

                                            const displayKeywords = (showTranslated && product.translatedKeywords) ? product.translatedKeywords : product.keywords;
                                            const hoverKeywords = (showTranslated && product.translatedKeywords) ? "点击查看原文" : "点击查看中文";

                                            return (
                                                <tr key={product.id} className="hover:bg-gray-50 transition-colors">
                                                    <td className="px-6 py-4 text-center align-middle">
                                                        <div onClick={() => toggleFavorite(product.id, product.isFavorite)}>
                                                            <Star className={cn("w-5 h-5 mx-auto cursor-pointer transition-colors", product.isFavorite ? "fill-yellow-400 text-yellow-400" : "text-gray-300 hover:text-yellow-400")} />
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 align-middle">
                                                        <div className="w-24 h-24 bg-gray-100 rounded border border-gray-200 overflow-hidden mx-auto flex items-center justify-center">
                                                            {product.image ? (
                                                                <img src={product.image} alt="product" className="w-full h-full object-cover" />
                                                            ) : (
                                                                <div className="w-full h-full flex items-center justify-center bg-gray-200 text-xs text-gray-500">No Img</div>
                                                            )}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-4 text-gray-600 text-sm align-middle">{product.sellerType}</td>
                                                    <td className="px-6 py-4 text-gray-600 text-sm align-middle">
                                                        <div className="space-y-1">
                                                            <div>{product.category}</div>
                                                            <div className="text-gray-400 text-xs">{product.subCategory}</div>
                                                        </div>
                                                    </td>
                                                    <td
                                                        className="px-6 py-4 text-gray-600 text-sm align-middle cursor-pointer hover:bg-blue-50/50 transition-colors relative"
                                                        title={hoverKeywords}
                                                        onClick={(e) => toggleRowLanguage(e, product)}
                                                    >
                                                        {displayKeywords}
                                                        {isOverridden && <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-red-400 rounded-full"></span>}
                                                    </td>

                                                    {/* 描述列：支持翻译模式 */}
                                                    <td
                                                        className="px-6 py-4 text-gray-600 text-sm align-middle relative group cursor-pointer hover:bg-blue-50/50 transition-colors"
                                                        onClick={(e) => toggleRowLanguage(e, product)}
                                                    >
                                                        <p
                                                            className="line-clamp-3 leading-relaxed pr-6"
                                                            title={hoverDesc}
                                                        >
                                                            {displayDesc}
                                                        </p>
                                                        {isOverridden && <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-red-400 rounded-full"></span>}
                                                        {/* 如果未开启中文模式，显示单个翻译按钮 */}
                                                        {!isChineseMode && (
                                                            <button
                                                                onClick={() => handleTranslate(product.id, product.description)}
                                                                className={cn(
                                                                    "absolute top-4 right-2 p-1 bg-white/80 rounded hover:bg-white shadow-sm transition-opacity",
                                                                    translatingIds.has(product.id) ? "opacity-100" : "opacity-0 group-hover:opacity-100"
                                                                )}
                                                                title="单条翻译"
                                                            >
                                                                <Languages className={cn("w-4 h-4", translatingIds.has(product.id) ? "animate-pulse text-blue-500" : "text-gray-400 hover:text-blue-500")} />
                                                            </button>
                                                        )}
                                                    </td>

                                                    <td className="px-6 py-4 text-gray-600 text-sm text-right align-middle">
                                                        {product.minPrice} {product.currency}
                                                    </td>
                                                    <td className="px-6 py-4 text-gray-600 text-sm text-right align-middle">
                                                        {product.maxPrice} {product.currency}
                                                    </td>
                                                    <td className="px-6 py-4 text-gray-600 text-sm align-middle">{product.reason}</td>
                                                    <td className="px-4 py-4 align-middle">
                                                        <div className="flex flex-col gap-2">
                                                            <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-gray-600">
                                                                <LayoutList className="w-4 h-4" />
                                                            </Button>
                                                            <Button variant="ghost" size="icon" className="h-8 w-8 text-red-400 hover:text-red-600 bg-red-50 hover:bg-red-100">
                                                                <span className="text-xs font-bold">虾</span>
                                                            </Button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            )
                                        })}
                                    </tbody>
                                </table>
                            ) : (
                                <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                                    <Package className="w-12 h-12 mb-2 text-gray-300" />
                                    <p>暂无数据</p>
                                </div>
                            )}
                        </div>

                        {/* 分页 */}
                        <div className="p-4 border-t border-gray-100 bg-gray-50 text-sm text-gray-500 flex justify-end items-center gap-4">
                            <span>共 {total} 条</span>
                            <select
                                value={limit}
                                onChange={(e) => { setLimit(Number(e.target.value)); setPage(1); }}
                                className="border border-gray-300 rounded px-2 py-1 bg-white"
                            >
                                <option value={10}>10条/页</option>
                                <option value={20}>20条/页</option>
                                <option value={50}>50条/页</option>
                            </select>

                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => handlePageChange(page - 1)}
                                    disabled={page <= 1}
                                    className="px-2 py-1 border border-gray-300 rounded bg-white hover:bg-gray-50 text-xs disabled:opacity-50"
                                >
                                    &lt;
                                </button>
                                <span className="px-2 text-gray-600">
                                    第 <span className="text-red-500 font-medium">{page}</span> / {Math.max(1, totalPages)} 页
                                </span>
                                <button
                                    onClick={() => handlePageChange(page + 1)}
                                    disabled={page >= totalPages}
                                    className="px-2 py-1 border border-gray-300 rounded bg-white hover:bg-gray-50 text-xs disabled:opacity-50"
                                >
                                    &gt;
                                </button>
                            </div>

                            <div className="flex items-center gap-2">
                                <span>前往</span>
                                <input
                                    type="text"
                                    value={page}
                                    onChange={(e) => {
                                        const p = parseInt(e.target.value);
                                        if (!isNaN(p)) setPage(p);
                                    }}
                                    className="w-10 text-center border border-gray-300 rounded py-1"
                                />
                                <span>页</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
