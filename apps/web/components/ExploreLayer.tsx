import React, { useState, useEffect } from 'react';
import { fetchProducts, Product } from '@/lib/api';

interface ExploreLayerProps {
  isOpen: boolean;
  onClose: () => void;
  onAskAboutProduct: (productName: string, productPrice: number) => void;
}

export function ExploreLayer({ isOpen, onClose, onAskAboutProduct }: ExploreLayerProps) {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      fetchProducts()
        .then(res => setProducts(res))
        .catch(() => {
          // Curated catalog fallback
          setProducts([
            {
              id: 'prod_logitech_mx_master',
              merchant_id: 'merchant_001',
              merchant_name: 'Croma',
              name: 'Logitech MX Master 3S Wireless Performance Mouse',
              category: 'accessories',
              price: 8995,
              currency: 'INR',
              stock: 40,
              in_stock: true,
              rating: 4.9,
              description: '8K DPI any-surface tracking, MagSpeed electromagnetic scrolling, USB-C fast charging.',
              specs: { dpi: '8,000 DPI', sensor: 'Darkfield', battery: '70 days' }
            },
            {
              id: 'prod_dell_ms5320w',
              merchant_id: 'merchant_001',
              merchant_name: 'Croma',
              name: 'Dell Premier Multi-Device Wireless Mouse MS5320W',
              category: 'accessories',
              price: 2999,
              currency: 'INR',
              stock: 49,
              in_stock: true,
              rating: 4.6,
              description: 'Seamlessly work across 3 PCs with 2.4GHz wireless and Bluetooth 5.0, 36-month battery life.',
              specs: { connectivity: '2.4GHz & Bluetooth 5.0', battery: '36 months', dpi: '1600 DPI' }
            },
            {
              id: 'prod_jbl_770nc',
              merchant_id: 'merchant_001',
              merchant_name: 'Croma',
              name: 'JBL Tune 770NC Wireless Adaptive ANC Headphones',
              category: 'audio',
              price: 4499,
              currency: 'INR',
              stock: 45,
              in_stock: true,
              rating: 4.6,
              description: 'Adaptive Noise Cancelling with Smart Ambient mode, Bluetooth 5.3, 70 hours battery life.',
              specs: { battery: '70h', bluetooth: '5.3', driver: '40mm' }
            },
            {
              id: 'prod_sony_whch720n',
              merchant_id: 'merchant_002',
              merchant_name: 'Reliance Digital',
              name: 'Sony WH-CH720N Noise Cancelling Wireless Headphones',
              category: 'audio',
              price: 7990,
              currency: 'INR',
              stock: 30,
              in_stock: true,
              rating: 4.7,
              description: 'Dual Noise Sensor technology with integrated V1 processor, ultra-comfortable 192g lightweight chassis.',
              specs: { battery: '35h', weight: '192g', processor: 'V1' }
            },
            {
              id: 'prod_lg_ultragear_27',
              merchant_id: 'merchant_001',
              merchant_name: 'Croma',
              name: 'LG UltraGear 27-inch QHD 144Hz IPS Gaming Monitor',
              category: 'displays',
              price: 24999,
              currency: 'INR',
              stock: 18,
              in_stock: true,
              rating: 4.8,
              description: '2560x1440 IPS panel, 1ms response time, HDR10, NVIDIA G-SYNC & AMD FreeSync compatible.',
              specs: { refresh: '144Hz', panel: 'IPS QHD', response: '1ms' }
            },
            {
              id: 'prod_acer_nitro_27',
              merchant_id: 'merchant_003',
              merchant_name: 'Amazon Prime Direct',
              name: 'Acer Nitro VG271U 27-inch 144Hz WQHD IPS Monitor',
              category: 'displays',
              price: 22499,
              currency: 'INR',
              stock: 22,
              in_stock: true,
              rating: 4.5,
              description: '2K WQHD IPS display, 0.5ms response time, 99% sRGB color gamut, dual HDMI 2.0 & DisplayPort.',
              specs: { refresh: '144Hz', panel: 'IPS WQHD', response: '0.5ms' }
            },
            {
              id: 'prod_philips_airfryer',
              merchant_id: 'merchant_002',
              merchant_name: 'Reliance Digital',
              name: 'Philips Essential Digital Air Fryer 4.1L with Rapid Air',
              category: 'appliances',
              price: 5499,
              currency: 'INR',
              stock: 25,
              in_stock: true,
              rating: 4.6,
              description: 'Cook with up to 90% less fat. Touch screen with 7 presets, keep warm function, dishwasher safe parts.',
              specs: { capacity: '4.1L', presets: '7 modes', power: '1400W' }
            }
          ]);
        })
        .finally(() => setLoading(false));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const filtered = products.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.category.toLowerCase().includes(search.toLowerCase()) ||
    (p.merchant_name && p.merchant_name.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/25 dark:bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="glass-sheet max-w-4xl w-full max-h-[85vh] rounded-2xl flex flex-col shadow-2xl overflow-hidden dark:bg-[#161515] dark:border-white/10">
        {/* Header */}
        <div className="p-6 border-b border-[#E4E2E2]/80 dark:border-white/10 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="w-2 h-2 rounded-full bg-[#FE7352]"></span>
              <h2 className="text-base font-semibold text-[#1B1C1C] dark:text-white">
                Explore Layer
              </h2>
            </div>
            <p className="text-xs text-[#7E7576] dark:text-[#9E9697]">
              Browse verified inventory across approved merchants. Route any item directly to AgentPay.
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-[#7E7576] dark:text-[#9E9697] hover:text-[#1B1C1C] dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/10 transition-colors text-lg"
          >
            ✕
          </button>
        </div>

        {/* Search Bar */}
        <div className="px-6 py-3 border-b border-[#E4E2E2]/60 dark:border-white/10 bg-white/40 dark:bg-[#1A1919]">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search verified catalog by item, merchant, or category..."
            className="w-full bg-white/80 dark:bg-[#201F1F] border border-[#E4E2E2] dark:border-white/10 rounded-xl px-4 py-2 text-xs sm:text-sm text-[#1B1C1C] dark:text-white placeholder-[#9C9495] dark:placeholder-[#7E7576] focus:outline-none focus:border-[#AA361A] transition-colors"
          />
        </div>

        {/* Product List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          {loading ? (
            <div className="py-16 text-center text-xs text-[#7E7576] dark:text-[#9E9697] animate-pulse">
              Retrieving live catalog records...
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-16 text-center text-xs text-[#7E7576] dark:text-[#9E9697]">
              No products found matching &ldquo;{search}&rdquo;.
            </div>
          ) : (
            filtered.map((prod) => (
              <div
                key={prod.id}
                className="paper-card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-[#CFBFC0] dark:hover:border-white/20 dark:bg-[#1A1919] dark:border-white/10 transition-colors"
              >
                <div className="space-y-1 max-w-xl">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-black/5 dark:bg-white/10 text-[#4C4546] dark:text-[#C4BCBC]">
                      {prod.merchant_name || 'Verified Merchant'}
                    </span>
                    <span className="text-xs text-[#7E7576] dark:text-[#9E9697] uppercase tracking-wider">
                      {prod.category}
                    </span>
                  </div>
                  <h4 className="text-sm font-semibold text-[#1B1C1C] dark:text-white">
                    {prod.name}
                  </h4>
                  <p className="text-xs text-[#4C4546] dark:text-[#C4BCBC] line-clamp-1">
                    {prod.description}
                  </p>
                </div>

                <div className="flex items-center justify-between sm:justify-end gap-4 shrink-0">
                  <div className="text-right">
                    <div className="font-mono text-sm sm:text-base font-semibold text-[#1B1C1C] dark:text-white">
                      ₹{prod.price.toLocaleString('en-IN')}
                    </div>
                    <div className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">
                      In Stock
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      onAskAboutProduct(prod.name, prod.price);
                      onClose();
                    }}
                    className="px-3.5 py-1.5 rounded-lg bg-[#1B1C1C] hover:bg-black dark:bg-white dark:text-[#141212] dark:hover:bg-neutral-200 text-white text-xs font-medium transition-all flex items-center gap-1 group shadow-sm"
                  >
                    <span>Ask AgentPay</span>
                    <span className="group-hover:translate-x-0.5 transition-transform">↗</span>
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
