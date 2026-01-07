import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";

export type SortField = 'productTotal' | 'purchaseCost' | 'shippingFee' | 'otherFees' | 'revenue' | 'none';
export type SortDirection = 'asc' | 'desc';

interface OrderSortProps {
  sortField: SortField;
  sortDirection: SortDirection;
  onSortChange: (field: SortField) => void;
}

export function OrderSort({ sortField, sortDirection, onSortChange }: OrderSortProps) {
  const sortOptions = [
    { value: 'productTotal', label: '商品总额' },
    { value: 'purchaseCost', label: '采购总成本' },
    { value: 'shippingFee', label: '预估运费总额' },
    { value: 'otherFees', label: '费用' },
    { value: 'revenue', label: '预估订单收入' },
  ];

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="w-3 h-3 text-muted-foreground" />;
    }
    return sortDirection === 'asc' 
      ? <ArrowUp className="w-3 h-3 text-primary" />
      : <ArrowDown className="w-3 h-3 text-primary" />;
  };

  return (
    <div className="bg-white border border-border rounded-lg p-3 mb-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="text-sm font-medium text-foreground">排序:</span>
        <div className="flex items-center gap-2 flex-wrap">
          {sortOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => onSortChange(option.value as SortField)}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-all
                ${sortField === option.value 
                  ? 'bg-primary text-primary-foreground shadow-sm' 
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }
              `}
            >
              {getSortIcon(option.value as SortField)}
              <span>{option.label}</span>
            </button>
          ))}
          {sortField !== 'none' && (
            <button
              onClick={() => onSortChange('none')}
              className="px-3 py-1.5 rounded-md text-sm bg-gray-100 text-gray-600 hover:bg-gray-200 transition-all"
            >
              清除排序
            </button>
          )}
        </div>
      </div>
    </div>
  );
}