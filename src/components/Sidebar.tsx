import { LayoutGrid, Package } from "lucide-react";
import { cn } from "./ui/utils";

interface SidebarProps {
    activeTab: 'orders' | 'mappings';
    onTabChange: (tab: 'orders' | 'mappings') => void;
}

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
    return (
        <div className="fixed left-0 top-0 bg-white border-r border-gray-200 flex flex-col h-screen z-40" style={{ width: '264px' }}>
            <div className="p-6 border-b border-gray-100">
                <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                    订单管理系统
                </h1>
            </div>

            <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
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
                    成本映射管理
                </button>
            </nav>
        </div>
    );
}
