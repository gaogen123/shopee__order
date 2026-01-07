import { useEffect, useState } from "react";
import { Progress } from "./ui/progress";
import { CheckCircle2, RefreshCw } from "lucide-react";

interface SyncProgressProps {
  isVisible: boolean;
  onComplete: () => void;
}

export function SyncProgress({ isVisible, onComplete }: SyncProgressProps) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("正在同步订单...");
  const [isCompleted, setIsCompleted] = useState(false);

  useEffect(() => {
    if (!isVisible) {
      setProgress(0);
      setIsCompleted(false);
      return;
    }

    const steps = [
      { progress: 15, status: "正在连接服务器...", duration: 300 },
      { progress: 30, status: "正在获取订单数据...", duration: 500 },
      { progress: 50, status: "正在解析订单信息...", duration: 600 },
      { progress: 70, status: "正在更新本地数据...", duration: 500 },
      { progress: 85, status: "正在验证数据完整性...", duration: 400 },
      { progress: 100, status: "同步完成！", duration: 300 },
    ];

    let currentStep = 0;
    let timeoutId: NodeJS.Timeout;

    const runNextStep = () => {
      if (currentStep < steps.length) {
        const step = steps[currentStep];
        setProgress(step.progress);
        setStatus(step.status);
        
        if (step.progress === 100) {
          setIsCompleted(true);
          timeoutId = setTimeout(() => {
            onComplete();
          }, 1500);
        } else {
          timeoutId = setTimeout(() => {
            currentStep++;
            runNextStep();
          }, step.duration);
        }
      }
    };

    runNextStep();

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [isVisible, onComplete]);

  if (!isVisible) return null;

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm w-full sm:w-96 animate-in slide-in-from-top-5">
      <div className="bg-white rounded-lg shadow-xl border border-border p-4">
        <div className="flex items-start gap-3">
          {isCompleted ? (
            <div className="bg-green-100 rounded-full p-2 flex-shrink-0">
              <CheckCircle2 className="w-5 h-5 text-green-600" />
            </div>
          ) : (
            <div className="bg-orange-100 rounded-full p-2 flex-shrink-0 animate-spin">
              <RefreshCw className="w-5 h-5 text-orange-600" />
            </div>
          )}
          
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-sm mb-1">
              {isCompleted ? "同步成功" : "正在同步"}
            </h3>
            
            <p className="text-xs text-muted-foreground mb-3">
              {status}
            </p>
            
            <div className="space-y-1.5">
              <Progress value={progress} className="h-2" />
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