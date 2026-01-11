import { useEffect, useState, useRef } from "react";
import { Progress } from "./ui/progress";
import { CheckCircle2, RefreshCw, AlertCircle } from "lucide-react";
import { toast } from "sonner";

interface SyncProgressProps {
  isVisible: boolean;
  taskId?: string;
  onComplete: () => void;
}

export function SyncProgress({ isVisible, taskId, onComplete }: SyncProgressProps) {
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("准备同步...");
  const [currentCount, setCurrentCount] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use ref to track if component is mounted to avoid state updates after unmount
  const isMounted = useRef(false);

  useEffect(() => {
    isMounted.current = true;
    return () => { isMounted.current = false; };
  }, []);

  useEffect(() => {
    if (!isVisible) {
      setProgress(0);
      setStatusText("准备同步...");
      setCurrentCount(0);
      setTotalCount(0);
      setIsCompleted(false);
      setError(null);
      return;
    }

    if (!taskId) {
      // Fallback for demo / legacy without taskId
      // ... (Original fake progress logic could go here if needed, but let's assume we always have taskId for new flow)
      setStatusText("初始化任务...");
      return;
    }

    let intervalId: NodeJS.Timeout;

    const pollStatus = async () => {
      try {
        const res = await fetch(`http://localhost:9000/api/sync/status/${taskId}`);
        if (!res.ok) throw new Error("Status check failed");

        const data = await res.json();

        if (!isMounted.current) return;

        if (data.status === "failed") {
          setError(data.error || "同步失败");
          setStatusText("同步失败");
          clearInterval(intervalId);
          toast.error(`同步失败: ${data.error}`);
          return;
        }

        if (data.total > 0) {
          const pct = Math.round((data.current / data.total) * 100);
          setProgress(pct);
          setCurrentCount(data.current);
          setTotalCount(data.total);
          setStatusText(`正在同步... (${data.current}/${data.total})`);
        } else {
          // Maybe getting list
          setStatusText(data.count > 0 ? `已同步 ${data.count} 个订单...` : "正在获取订单列表...");
          // Indeterminate progress?
          if (data.status === "running") {
            setProgress((prev) => (prev < 90 ? prev + 5 : prev));
          }
        }

        if (data.status === "completed") {
          setProgress(100);
          setStatusText("同步完成！");
          setIsCompleted(true);
          clearInterval(intervalId);
          setTimeout(() => {
            if (isMounted.current) onComplete();
          }, 1000);
        }

      } catch (err) {
        console.error("Poll error:", err);
        // Don't stop polling immediately on transient network error, but maybe log it?
      }
    };

    // Poll immediately then interval
    pollStatus();
    intervalId = setInterval(pollStatus, 1000);

    return () => {
      clearInterval(intervalId);
    };

  }, [isVisible, taskId, onComplete]);

  if (!isVisible) return null;

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm w-full sm:w-96 animate-in slide-in-from-top-5">
      <div className={`bg-white rounded-lg shadow-xl border ${error ? 'border-destructive' : 'border-border'} p-4`}>
        <div className="flex items-start gap-3">
          {error ? (
            <div className="bg-destructive/10 rounded-full p-2 flex-shrink-0">
              <AlertCircle className="w-5 h-5 text-destructive" />
            </div>
          ) : isCompleted ? (
            <div className="bg-green-100 rounded-full p-2 flex-shrink-0">
              <CheckCircle2 className="w-5 h-5 text-green-600" />
            </div>
          ) : (
            <div className="bg-orange-100 rounded-full p-2 flex-shrink-0 animate-spin">
              <RefreshCw className="w-5 h-5 text-orange-600" />
            </div>
          )}

          <div className="flex-1 min-w-0">
            <h3 className={`font-medium text-sm mb-1 ${error ? 'text-destructive' : ''}`}>
              {error ? "同步出错" : (isCompleted ? "同步成功" : "正在同步")}
            </h3>

            <p className="text-xs text-muted-foreground mb-3">
              {statusText}
            </p>

            <div className="space-y-1.5">
              <Progress value={progress} className={`h-2 ${error ? 'bg-destructive/20' : ''}`} />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{progress}%</span>
                <span>{isCompleted ? "已完成" : "进行中"}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}