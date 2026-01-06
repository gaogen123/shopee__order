import { useState, useEffect } from 'react';
import { OrderDetail } from './components/OrderDetail';
import { OrderList } from './components/OrderList';
import { CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

interface SyncStatus {
  task_id: string;
  status: 'starting' | 'running' | 'completed' | 'failed';
  current: number;
  total: number;
  count: number;
}

export default function App() {
  const [view, setView] = useState<'LIST' | 'DETAIL'>('LIST');
  const [selectedOrderSn, setSelectedOrderSn] = useState<string | null>(null);
  const [syncTask, setSyncTask] = useState<SyncStatus | null>(null);
  const [showNotification, setShowNotification] = useState(false);
  const [lastRefreshTime, setLastRefreshTime] = useState(Date.now());

  // Background polling for sync status
  useEffect(() => {
    let timer: any;
    const currentTaskId = syncTask?.task_id;

    if (currentTaskId && (syncTask.status === 'starting' || syncTask.status === 'running')) {
      timer = setInterval(async () => {
        try {
          const res = await fetch(`http://localhost:8000/api/sync/status/${currentTaskId}`);
          if (res.ok) {
            const status = await res.json();
            // Merge with previous state to ensure task_id is preserved
            setSyncTask(prev => prev ? { ...prev, ...status } : status);

            if (status.status === 'completed' || status.status === 'failed') {
              setShowNotification(true);
              setLastRefreshTime(Date.now()); // 同步完成后更新刷新时间
              // Auto hide notification after 5 seconds
              setTimeout(() => setShowNotification(false), 5000);
            }
          }
        } catch (e) {
          console.error("Polling error:", e);
        }
      }, 2000);
    }
    return () => clearInterval(timer);
  }, [syncTask?.task_id, syncTask?.status]);

  const handleStartSync = async (startDate: string, endDate: string) => {
    try {
      const time_from = Math.floor(new Date(startDate + 'T00:00:00').getTime() / 1000);
      const time_to = Math.floor(new Date(endDate + 'T23:59:59').getTime() / 1000);

      const res = await fetch('http://localhost:8000/api/sync_orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ time_from, time_to })
      });

      if (res.ok) {
        const { task_id } = await res.json();
        setSyncTask({ task_id, status: 'starting', current: 0, total: 0, count: 0 });
        setShowNotification(false);
      }
    } catch (e) {
      alert("起动同步失败");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 relative">
      {/* Background Sync Indicator */}
      {syncTask && (syncTask.status === 'starting' || syncTask.status === 'running') && (
        <div className="fixed bottom-6 right-6 z-50 bg-white rounded-xl shadow-2xl border p-4 w-72 animate-in slide-in-from-bottom-4">
          <div className="flex items-center gap-3 mb-3">
            <Loader2 className="w-5 h-5 text-orange-500 animate-spin" />
            <span className="font-medium text-sm text-gray-800">正在异步同步订单...</span>
          </div>
          <div className="relative pt-1">
            <div className="overflow-hidden h-2 mb-2 text-xs flex rounded-full bg-gray-100">
              <div
                style={{ width: `${syncTask.total > 0 ? (syncTask.current / syncTask.total) * 100 : 0}%` }}
                className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-orange-500 transition-all duration-500"
              ></div>
            </div>
            <div className="flex justify-between text-[10px] text-gray-500">
              <span>已处理: {syncTask.current}/{syncTask.total}</span>
              <span>成功: {syncTask.count}</span>
            </div>
          </div>
        </div>
      )}

      {/* Completion Notification */}
      {showNotification && syncTask && (
        <div className="fixed top-6 right-6 z-[60] bg-white rounded-lg shadow-xl border-l-4 border-l-green-500 p-4 w-80 animate-in fade-in slide-in-from-top-4">
          <div className="flex items-start gap-3">
            {syncTask.status === 'completed' ? (
              <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" />
            )}
            <div>
              <h4 className="text-sm font-bold text-gray-800">
                {syncTask.status === 'completed' ? '同步任务已完成' : '同步任务失败'}
              </h4>
              <p className="text-xs text-gray-500 mt-1">
                {syncTask.status === 'completed'
                  ? `成功拉取 ${syncTask.count} 个订单详情数据。`
                  : '同步过程中发生错误。'}
              </p>
            </div>
          </div>
        </div>
      )}

      {view === 'LIST' ? (
        <OrderList
          onSelectOrder={(sn) => {
            setSelectedOrderSn(sn);
            setView('DETAIL');
          }}
          onSync={handleStartSync}
          syncing={!!syncTask && (syncTask.status === 'starting' || syncTask.status === 'running')}
          refreshTrigger={lastRefreshTime}
        />
      ) : (
        <div>
          <div className="max-w-7xl mx-auto px-6 pt-4">
            <button
              onClick={() => setView('LIST')}
              className="px-4 py-2 bg-white border rounded shadow-sm hover:bg-gray-50 text-sm text-gray-700 font-medium"
            >
              &larr; 返回订单列表
            </button>
          </div>
          <OrderDetail orderSn={selectedOrderSn || undefined} />
        </div>
      )}
    </div>
  );
}
