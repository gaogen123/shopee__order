import { CheckCircle2, AlertCircle } from "lucide-react";

export type CostStatus = 'all' | 'recorded' | 'unrecorded';

interface CostStatusFilterProps {
  activeCostStatus: CostStatus;
  onCostStatusChange: (status: CostStatus) => void;
  costStatusCounts: {
    total: number;
    recorded: number;
    unrecorded: number;
  };
}

export function CostStatusFilter({ 
  activeCostStatus, 
  onCostStatusChange, 
  costStatusCounts
}: CostStatusFilterProps) {
  return (
    <div className="bg-white border border-border rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <span className="text-sm font-medium text-foreground">成本录入状态:</span>
        
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => onCostStatusChange('all')}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all
              ${activeCostStatus === 'all'
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }
            `}
          >
            <span>全部</span>
            <span className={`
              px-2 py-0.5 rounded-full text-xs font-medium
              ${activeCostStatus === 'all' 
                ? 'bg-primary-foreground/20 text-primary-foreground' 
                : 'bg-background text-foreground'
              }
            `}>
              {costStatusCounts.total}
            </span>
          </button>

          <button
            onClick={() => onCostStatusChange('recorded')}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all
              ${activeCostStatus === 'recorded'
                ? 'bg-green-600 text-white shadow-sm'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }
            `}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>已录入</span>
            <span className={`
              px-2 py-0.5 rounded-full text-xs font-medium
              ${activeCostStatus === 'recorded' 
                ? 'bg-white/20 text-white' 
                : 'bg-green-100 text-green-700'
              }
            `}>
              {costStatusCounts.recorded}
            </span>
          </button>

          <button
            onClick={() => onCostStatusChange('unrecorded')}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-all
              ${activeCostStatus === 'unrecorded'
                ? 'bg-orange-600 text-white shadow-sm'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }
            `}
          >
            <AlertCircle className="w-4 h-4" />
            <span>未录入</span>
            <span className={`
              px-2 py-0.5 rounded-full text-xs font-medium
              ${activeCostStatus === 'unrecorded' 
                ? 'bg-white/20 text-white' 
                : 'bg-orange-100 text-orange-700'
              }
            `}>
              {costStatusCounts.unrecorded}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}