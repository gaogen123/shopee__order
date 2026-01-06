import * as React from "react";
import { Calendar as CalendarIcon } from "lucide-react";
import { DateRange, DayPicker } from "react-day-picker";
import * as Popover from "@radix-ui/react-popover";

// Simple formatter that ensures local date string
const formatDate = (date: Date | undefined) => {
    if (!date) return "";
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

interface DateRangePickerProps {
    startDate: string;
    endDate: string;
    onChange: (start: string, end: string) => void;
}

export function DateRangePicker({ startDate, endDate, onChange }: DateRangePickerProps) {
    const [date, setDate] = React.useState<DateRange | undefined>({
        from: startDate ? new Date(startDate + "T00:00:00") : undefined,
        to: endDate ? new Date(endDate + "T00:00:00") : undefined,
    });

    const handleSelect = (range: DateRange | undefined) => {
        setDate(range);
        if (range?.from) {
            const start = formatDate(range.from);
            const end = range.to ? formatDate(range.to) : start; // If only one selected, make it same day
            onChange(start, end);
        }
    };

    return (
        <div className="grid gap-2">
            <Popover.Root>
                <Popover.Trigger asChild>
                    <button
                        className="flex items-center bg-white border border-gray-300 rounded-md px-4 py-2 shadow-sm hover:border-blue-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all group min-w-[280px]"
                    >
                        <CalendarIcon className="mr-3 h-4 w-4 text-gray-400 group-hover:text-blue-500" />
                        <div className="text-sm text-gray-700 flex items-center gap-3">
                            <span className="font-medium">{startDate || "开始日期"}</span>
                            <span className="text-gray-300 select-none font-light">至</span>
                            <span className="font-medium">{endDate || "结束日期"}</span>
                        </div>
                    </button>
                </Popover.Trigger>
                <Popover.Portal>
                    <Popover.Content
                        className="z-50 w-auto bg-white p-0 rounded-xl shadow-[0_10px_40px_rgba(0,0,0,0.15)] border border-gray-100 overflow-hidden animate-in fade-in zoom-in-95"
                        align="end"
                        sideOffset={8}
                    >
                        <div className="p-4 bg-gray-50 border-b flex items-center justify-between">
                            <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">选择日期范围</span>
                            <div className="flex gap-2 text-[10px]">
                                <span className="px-2 py-0.5 bg-blue-100 text-blue-600 rounded">同步最多支持90天范围</span>
                            </div>
                        </div>
                        <div className="p-4 bg-white">
                            <DayPicker
                                initialFocus
                                mode="range"
                                defaultMonth={date?.from}
                                selected={date}
                                onSelect={handleSelect}
                                numberOfMonths={2}
                                className="rdp-custom"
                            />
                        </div>
                        <div className="flex justify-end gap-3 p-4 bg-gray-50 border-t">
                            <button
                                onClick={() => { setDate(undefined); onChange("", ""); }}
                                className="px-4 py-1.5 text-xs text-gray-500 hover:text-gray-800 hover:bg-gray-200 rounded-md transition-colors"
                            >
                                清空
                            </button>
                            <Popover.Close className="px-5 py-1.5 text-xs bg-blue-500 text-white rounded-md hover:bg-blue-600 shadow-sm transition-all active:scale-95">
                                确定同步范围
                            </Popover.Close>
                        </div>
                    </Popover.Content>
                </Popover.Portal>
            </Popover.Root>

            <style>{`
        .rdp-custom {
            --rdp-accent-color: #3b82f6;
            --rdp-background-alpha: 0.1;
            margin: 0;
        }
        .rdp-months { display: flex; gap: 1.5rem; }
        .rdp-month { font-family: inherit; }
        .rdp-caption { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 1.5rem; 
            font-weight: 700;
            color: #1f2937;
        }
        .rdp-caption_label { font-size: 0.9375rem; }
        .rdp-nav { display: flex; gap: 0.5rem; }
        .rdp-nav_button {
            width: 1.75rem;
            height: 1.75rem;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 99px;
            color: #6b7280;
            transition: all 0.2s;
        }
        .rdp-nav_button:hover { background-color: #f3f4f6; color: #111827; }
        .rdp-head_cell { 
            font-size: 0.75rem; 
            font-weight: 600; 
            color: #9ca3af; 
            padding: 0.75rem 0.5rem;
            text-align: center;
        }
        .rdp-cell { padding: 0.05rem; }
        .rdp-day { 
            width: 2.25rem; 
            height: 2.25rem; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            border-radius: 0.5rem; 
            cursor: pointer; 
            font-size: 0.8125rem;
            color: #374151;
            transition: all 0.2s;
        }
        .rdp-day:hover { background-color: #eff6ff; color: #1d4ed8; }
        .rdp-day_selected { background-color: var(--rdp-accent-color) !important; color: white !important; font-weight: 600; }
        .rdp-day_outside { color: #d1d5db; opacity: 0.5; }
        .rdp-day_range_middle { 
            background-color: #eff6ff !important; 
            color: #1d4ed8 !important;
            border-radius: 0;
        }
        .rdp-day_range_start { border-top-right-radius: 0; border-bottom-right-radius: 0; }
        .rdp-day_range_end { border-top-left-radius: 0; border-bottom-left-radius: 0; }
        .rdp-button:focus-visible { outline: 2px solid #3b82f6; outline-offset: 2px; }
      `}</style>
        </div>
    );
}
