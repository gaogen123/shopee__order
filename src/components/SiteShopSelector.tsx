import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Store, Building2 } from "lucide-react";

interface SiteShopSelectorProps {
  selectedSite: string;
  selectedShop: string;
  onSiteChange: (site: string) => void;
  onShopChange: (shop: string) => void;
  sites: { value: string; label: string }[];
  shops: { value: string; label: string; siteId: string }[];
}

export function SiteShopSelector({
  selectedSite,
  selectedShop,
  onSiteChange,
  onShopChange,
  sites,
  shops,
}: SiteShopSelectorProps) {
  // Filter shops based on selected site
  const availableShops = selectedSite === 'all' 
    ? shops 
    : shops.filter(shop => shop.siteId === selectedSite);

  const handleSiteChange = (value: string) => {
    onSiteChange(value);
    // Reset shop selection when site changes
    if (value === 'all') {
      onShopChange('all');
    } else {
      // If current shop doesn't belong to new site, reset to 'all'
      const currentShop = shops.find(s => s.value === selectedShop);
      if (!currentShop || currentShop.siteId !== value) {
        onShopChange('all');
      }
    }
  };

  return (
    <div className="flex flex-col sm:flex-row gap-3">
      <div className="flex-1">
        <Select value={selectedSite} onValueChange={handleSiteChange}>
          <SelectTrigger className="w-full">
            <div className="flex items-center gap-2">
              <Building2 className="size-4 text-muted-foreground" />
              <SelectValue placeholder="选择站点" />
            </div>
          </SelectTrigger>
          <SelectContent>
            {sites.map((site) => (
              <SelectItem key={site.value} value={site.value}>
                {site.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex-1">
        <Select value={selectedShop} onValueChange={onShopChange}>
          <SelectTrigger className="w-full">
            <div className="flex items-center gap-2">
              <Store className="size-4 text-muted-foreground" />
              <SelectValue placeholder="选择店铺" />
            </div>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部店铺</SelectItem>
            {availableShops.map((shop) => (
              <SelectItem key={shop.value} value={shop.value}>
                {shop.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
