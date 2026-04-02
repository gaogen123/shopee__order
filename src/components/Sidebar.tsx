import { LayoutGrid, Package, BarChart2, Bot, Globe } from "lucide-react";
import { cn } from "./ui/utils";

interface SidebarProps {
    activeTab: 'dashboard' | 'orders' | 'mappings' | 'pdd' | 'selection-guide';
    onTabChange: (tab: 'dashboard' | 'orders' | 'mappings' | 'pdd' | 'selection-guide') => void;
}

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
    return (
        <div className="bg-white border-r border-gray-200 flex flex-col h-full z-40 shrink-0" style={{ width: '264px' }}>
            <div className="p-6 border-b border-gray-100">
                <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                    订单管理系统
                </h1>
            </div>

            <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
                <button
                    onClick={() => onTabChange('dashboard')}
                    className={cn(
                        "w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium text-sm",
                        activeTab === 'dashboard'
                            ? "bg-blue-600 text-white shadow-lg shadow-blue-900/20"
                            : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    )}
                    style={activeTab === 'dashboard' ? { backgroundColor: '#2563eb', color: 'white' } : {}}
                >
                    <BarChart2 className={cn("w-5 h-5", activeTab === 'dashboard' ? "text-white" : "text-gray-400")} />
                    数据概览
                </button>

                <button
                    onClick={() => onTabChange('orders')}
                    className={cn(
                        "w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium text-sm",
                        activeTab === 'orders'
                            ? "bg-blue-600 text-white shadow-lg shadow-blue-900/20"
                            : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    )}
                    style={activeTab === 'orders' ? { backgroundColor: '#2563eb', color: 'white' } : {}}
                >
                    <LayoutGrid className={cn("w-5 h-5", activeTab === 'orders' ? "text-white" : "text-gray-400")} />
                    我的订单
                </button>

                <button
                    onClick={() => onTabChange('mappings')}
                    className={cn(
                        "w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium text-sm",
                        activeTab === 'mappings'
                            ? "bg-blue-600 text-white shadow-lg shadow-blue-900/20"
                            : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    )}
                    style={activeTab === 'mappings' ? { backgroundColor: '#2563eb', color: 'white' } : {}}
                >
                    <Package className={cn("w-5 h-5", activeTab === 'mappings' ? "text-white" : "text-gray-400")} />
                    移动映射管理
                </button>

                <button
                    onClick={() => onTabChange('selection-guide')}
                    className={cn(
                        "w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium text-sm",
                        activeTab === 'selection-guide'
                            ? "bg-blue-600 text-white shadow-lg shadow-blue-900/20"
                            : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    )}
                    style={activeTab === 'selection-guide' ? { backgroundColor: '#ea580c', color: 'white' } : {}}
                >
                    <Globe className={cn("w-5 h-5", activeTab === 'selection-guide' ? "text-white" : "text-gray-400")} />
                    选品指南
                </button>

                <button
                    onClick={() => onTabChange('pdd')}
                    className={cn(
                        "w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium text-sm",
                        activeTab === 'pdd'
                            ? "bg-blue-600 text-white shadow-lg shadow-blue-900/20"
                            : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    )}
                    style={activeTab === 'pdd' ? { backgroundColor: '#db2777', color: 'white' } : {}}
                >
                    <Bot className={cn("w-5 h-5", activeTab === 'pdd' ? "text-white" : "text-gray-400")} />
                    Shopee智能助手
                </button>
            </nav>
        </div>
    );
}
