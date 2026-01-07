import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { Button } from "./ui/button";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ 
  currentPage, 
  totalPages, 
  totalItems,
  itemsPerPage,
  onPageChange 
}: PaginationProps) {
  const startItem = totalItems === 0 ? 0 : (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);

  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    const showPages = 5; // 显示的页码数量
    
    if (totalPages <= showPages) {
      // 如果总页数小于等于显示数量，显示全部
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // 总是显示第一页
      pages.push(1);
      
      // 计算中间显示的页码
      let startPage = Math.max(2, currentPage - 1);
      let endPage = Math.min(totalPages - 1, currentPage + 1);
      
      // 调整显示范围
      if (currentPage <= 3) {
        endPage = 4;
      } else if (currentPage >= totalPages - 2) {
        startPage = totalPages - 3;
      }
      
      // 添加省略号
      if (startPage > 2) {
        pages.push('...');
      }
      
      // 添加中间页码
      for (let i = startPage; i <= endPage; i++) {
        pages.push(i);
      }
      
      // 添加省略号
      if (endPage < totalPages - 1) {
        pages.push('...');
      }
      
      // 总是显示最后一页
      pages.push(totalPages);
    }
    
    return pages;
  };

  if (totalPages <= 1) {
    return null;
  }

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-white border border-border rounded-lg">
      {/* 左侧：显示范围信息 */}
      <div className="flex-1 flex justify-start">
        <p className="text-sm text-muted-foreground">
          显示 <span className="font-medium text-foreground">{startItem}</span> 到{" "}
          <span className="font-medium text-foreground">{endItem}</span> 条，共{" "}
          <span className="font-medium text-foreground">{totalItems}</span> 条
        </p>
      </div>

      {/* 中间：页码按钮 */}
      <div className="flex items-center gap-1">
        {/* 第一页 */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1}
          className="h-8 w-8 p-0"
          aria-label="第一页"
        >
          <ChevronsLeft className="h-4 w-4" />
        </Button>

        {/* 上一页 */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="h-8 w-8 p-0"
          aria-label="上一页"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>

        {/* 页码 */}
        <div className="hidden sm:flex items-center gap-1">
          {getPageNumbers().map((page, index) => (
            <div key={index}>
              {page === '...' ? (
                <span className="px-3 py-1 text-sm text-muted-foreground">...</span>
              ) : (
                <Button
                  variant={currentPage === page ? "default" : "outline"}
                  size="sm"
                  onClick={() => onPageChange(page as number)}
                  className="h-8 min-w-8 px-3"
                >
                  {page}
                </Button>
              )}
            </div>
          ))}
        </div>

        {/* 移动端显示当前页 */}
        <div className="sm:hidden flex items-center px-3">
          <span className="text-sm">
            <span className="font-medium">{currentPage}</span>
            <span className="text-muted-foreground"> / {totalPages}</span>
          </span>
        </div>

        {/* 下一页 */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="h-8 w-8 p-0"
          aria-label="下一页"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>

        {/* 最后一页 */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages}
          className="h-8 w-8 p-0"
          aria-label="最后一页"
        >
          <ChevronsRight className="h-4 w-4" />
        </Button>
      </div>

      {/* 右侧：占位保持平衡 */}
      <div className="flex-1"></div>
    </div>
  );
}
