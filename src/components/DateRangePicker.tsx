import { Calendar as CalendarIcon } from "lucide-react";
import { DateRange } from "react-day-picker";
import { zhCN } from "date-fns/locale";
import { useEffect, useState } from "react";

import { cn } from "./ui/utils";
import { Button } from "./ui/button";
import { Calendar } from "./ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "./ui/popover";

interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onChange: (start: string, end: string) => void;
  className?: string;
}

export function DateRangePicker({
  startDate,
  endDate,
  onChange,
  className,
}: DateRangePickerProps) {
  // 简单的日期解析函数: "YYYY-MM-DD" -> Date
  const parseDate = (dateStr: string) => {
    if (!dateStr) return undefined;
    const parts = dateStr.split('-');
    if (parts.length !== 3) return undefined;
    const [y, m, d] = parts.map(Number);
    if (isNaN(y) || isNaN(m) || isNaN(d)) return undefined;
    return new Date(y, m - 1, d);
  };

  // 简单的日期格式化函数: Date -> "YYYY-MM-DD"
  const formatDate = (date: Date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const [date, setDate] = useState<DateRange | undefined>({
    from: parseDate(startDate),
    to: parseDate(endDate),
  });

  // 当外部 props 变化时同步内部状态
  useEffect(() => {
    const from = parseDate(startDate);
    const to = parseDate(endDate);

    // 避免不必要的更新
    if (
      from?.getTime() !== date?.from?.getTime() ||
      to?.getTime() !== date?.to?.getTime()
    ) {
      setDate({ from, to });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startDate, endDate]);

  const handleSelect = (newDate: DateRange | undefined) => {
    setDate(newDate);

    if (newDate?.from) {
      const s = formatDate(newDate.from);
      // 如果只有开始时间，结束时间暂取开始时间，或者等待用户选择结束时间
      // 这里策略是：只要有 from，就尝试更新。如果有 to，则更新 range。
      const e = newDate.to ? formatDate(newDate.to) : s;

      // 只有当这是有效的范围更新时（或者至少选择了开始时间），才通知父组件
      if (newDate.to) {
        onChange(s, e);
      }
    }
  };

  return (
    <div className={cn("grid gap-2", className)}>
      <Popover>
        <PopoverTrigger asChild>
          <Button
            id="date"
            variant={"outline"}
            className={cn(
              "w-[260px] justify-start text-left font-normal h-11 rounded-2xl bg-gray-100 border-transparent hover:bg-white hover:border-orange-500 transition-all text-sm",
              !date && "text-muted-foreground"
            )}
          >
            <CalendarIcon className="mr-2 h-4 w-4 text-gray-400" />
            {date?.from ? (
              date.to ? (
                <span className="font-bold text-gray-900">
                  {formatDate(date.from)} <span className="text-gray-400 mx-1">至</span> {formatDate(date.to)}
                </span>
              ) : (
                <span className="font-bold text-gray-900">{formatDate(date.from)}</span>
              )
            ) : (
              <span className="text-gray-400">选择日期范围</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0 rounded-xl shadow-xl border-gray-100" align="end">
          <Calendar
            initialFocus
            mode="range"
            defaultMonth={date?.from}
            selected={date}
            onSelect={handleSelect}
            numberOfMonths={2}
            className="p-3"
            locale={zhCN}
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}
