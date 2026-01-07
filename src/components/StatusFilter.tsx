interface StatusFilterProps {
  activeStatus: string;
  onStatusChange: (status: string) => void;
  statusCounts: Record<string, number>;
}

export function StatusFilter({ activeStatus, onStatusChange, statusCounts }: StatusFilterProps) {
  const statuses = [
    { value: 'all', label: '全部', color: 'text-foreground' },
    { value: 'pending', label: '待付款', color: 'text-orange-600' },
    { value: 'processing', label: '已收货', color: 'text-blue-600' },
    { value: 'shipped', label: '运出中', color: 'text-purple-600' },
    { value: 'completed', label: '已完成', color: 'text-green-600' },
  ];

  return (
    <div className="flex flex-wrap gap-2 mb-6">
      {statuses.map((status) => {
        const isActive = activeStatus === status.value;
        const count = statusCounts[status.value] || 0;
        
        return (
          <button
            key={status.value}
            onClick={() => onStatusChange(status.value)}
            className={`
              px-4 py-2 rounded-lg transition-all
              ${isActive 
                ? 'bg-primary text-primary-foreground shadow-sm' 
                : 'bg-white text-muted-foreground hover:bg-muted border border-border'
              }
            `}
          >
            <span className={isActive ? '' : status.color}>
              {status.label}
            </span>
            <span className="ml-2 text-sm">
              ({count})
            </span>
          </button>
        );
      })}
    </div>
  );
}
