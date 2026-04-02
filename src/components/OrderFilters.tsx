import { Search } from "lucide-react";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { DateRangePicker } from "./DateRangePicker";

interface OrderFiltersProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  dateRange: string;
  onDateRangeChange: (range: string) => void;
  onSync: () => void;
}

export function OrderFilters({
  searchQuery,
  onSearchChange,
  dateRange,
  onDateRangeChange,
  onSync
}: OrderFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-3 mb-6">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
          type="text"
          placeholder="搜索订单号 / 商品名称 / 订单状态"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-9"
        />
      </div>

      <DateRangePicker
        startDate={dateRange.split(' 至 ')[0] || ''}
        endDate={dateRange.split(' 至 ')[1] || ''}
        onChange={(start, end) => onDateRangeChange(`${start} 至 ${end}`)}
      />

      <Button
        onClick={onSync}
        className="bg-orange-500 hover:bg-orange-600 text-white"
      >
        同步订单
      </Button>
    </div>
  );
}