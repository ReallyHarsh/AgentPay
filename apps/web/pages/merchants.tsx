import React, { useState, useEffect, useMemo } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { fetchAgentPolicy, AgentPolicy, fetchProducts } from '@/lib/api';
import { MerchantInfo, CatalogProduct } from '@/types/commerce';
import { MERCHANTS, CATALOG_ITEMS, buildMerchantQuotes } from '@/lib/catalogData';
import { ProtocolModal } from '@/components/ProtocolModal';


export default function MerchantsCatalogPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMerchantId, setSelectedMerchantId] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'recommended' | 'price_asc' | 'price_desc' | 'rating'>('recommended');
  const [filterWithinBudget, setFilterWithinBudget] = useState(false);
  const [expandedBidsId, setExpandedBidsId] = useState<string | null>(null);
  const [isProtocolModalOpen, setIsProtocolModalOpen] = useState(false);

  const [policy, setPolicy] = useState<AgentPolicy | null>(null);
  const [catalogProducts, setCatalogProducts] = useState<CatalogProduct[]>(CATALOG_ITEMS);
  const [isLiveDatabase, setIsLiveDatabase] = useState(false);
  const [isLoadingProducts, setIsLoadingProducts] = useState(false);

  // Load custom policy or fallback
  useEffect(() => {
    const loadPolicy = () => {
      try {
        const saved = localStorage.getItem('agentpay_custom_policy');
        if (saved) {
          setPolicy(JSON.parse(saved));
          return;
        }
      } catch (e) {
        console.error(e);
      }
      fetchAgentPolicy()
        .then(p => setPolicy(p))
        .catch(() => {
          setPolicy({
            id: 'policy_001',
            agent_id: 'agent_001',
            currency: 'INR',
            per_transaction_limit: 5000,
            daily_spending_limit: 20000,
            spent_today: 12499,
            available_budget: 7501,
            allowed_categories: ['electronics', 'audio'],
            blocked_merchants: []
          });
        });
    };

    loadPolicy();
    window.addEventListener('agentpay-policy-updated', loadPolicy);
    return () => window.removeEventListener('agentpay-policy-updated', loadPolicy);
  }, []);

  // Fetch live products from the FastAPI SQLite/PostgreSQL database
  useEffect(() => {
    let isCurrent = true;
    setIsLoadingProducts(true);

    fetchProducts(searchQuery, 250)
      .then((dbItems) => {
        if (!isCurrent) return;
        if (dbItems && dbItems.length > 0) {
          const mapped: CatalogProduct[] = dbItems.map((item) => {
            const itemPrice = item.price;
            const quotes = buildMerchantQuotes(item.id, itemPrice, item.merchant_id);
            const bestQuote = quotes.find(q => q.isBest) || quotes[0];
            const primaryMerchant = item.merchant_id === 'merchant_002' ? 'Reliance Digital Tech' : item.merchant_id === 'merchant_003' ? 'Amazon Prime Direct' : 'Croma Electronics Hub';
            const cat = (['accessories', 'audio', 'displays', 'appliances', 'computing'].includes(item.category) ? item.category : 'accessories') as any;
            const catLabel = cat === 'accessories' ? 'Input & Peripherals' : cat === 'audio' ? 'Audio & ANC' : cat === 'displays' ? 'Monitors & Displays' : cat === 'appliances' ? 'Kitchen Appliances' : 'Laptops & Computing';
            return {
              id: item.id,
              name: item.name,
              brand: item.brand || item.name.split(' ')[0],
              category: cat,
              categoryLabel: catLabel,
              price: bestQuote ? bestQuote.price : itemPrice,
              rating: item.rating || 4.8,
              reviewsCount: 150 + Math.floor((itemPrice * 7) % 350),
              inStock: item.in_stock,
              stockCount: item.stock || 25,
              deliveryEta: bestQuote?.deliveryEta || 'Arrives Tomorrow',
              warranty: bestQuote?.warranty || '1 Year Brand Sealed Warranty',
              specs: item.specs && Object.keys(item.specs).length > 0
                ? Object.entries(item.specs).map(([k, v]) => `${k}: ${v}`)
                : ['Verified Authentic SKU', 'Manufacturer Warranty Included'],
              description: item.description || item.name,
              primaryMerchantId: item.merchant_id,
              primaryMerchantName: primaryMerchant.split(' ')[0],
              policyCap: Math.round(itemPrice * 1.25),
              merchantQuotes: quotes
            };
          });
          setCatalogProducts(mapped);
          setIsLiveDatabase(true);
        } else {
          // Empty search results in DB
          if (searchQuery.trim()) {
            setCatalogProducts([]);
          } else {
            setCatalogProducts(CATALOG_ITEMS);
          }
          setIsLiveDatabase(true);
        }
      })
      .catch(() => {
        // Backend offline: keep resilient default catalog fallback
        if (!isCurrent) return;
        setIsLiveDatabase(false);
        setCatalogProducts(CATALOG_ITEMS);
      })
      .finally(() => {
        if (isCurrent) setIsLoadingProducts(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [searchQuery]);

  const remainingBudget = policy?.available_budget !== undefined
    ? policy.available_budget
    : (policy?.daily_spending_limit ? Math.max(0, policy.daily_spending_limit - (policy.spent_today || 12499)) : 7501);

  const baseCatalogList = catalogProducts.length > 0 ? catalogProducts : CATALOG_ITEMS;

  // Filter and sort catalog
  const filteredProducts = useMemo(() => {
    let list = [...catalogProducts];

    // Filter by merchant (only products stocked/quoted by this merchant)
    if (selectedMerchantId !== 'all') {
      list = list.filter(item =>
        item.merchantQuotes.some(q => q.merchantId === selectedMerchantId)
      );
    }

    // Filter by category
    if (selectedCategory !== 'all') {
      list = list.filter(item => item.category === selectedCategory);
    }

    // Filter by budget
    if (filterWithinBudget) {
      list = list.filter(item => item.price <= remainingBudget);
    }

    // Filter by search query (if running in client fallback mode)
    if (!isLiveDatabase && searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(item =>
        item.name.toLowerCase().includes(q) ||
        item.brand.toLowerCase().includes(q) ||
        item.categoryLabel.toLowerCase().includes(q) ||
        item.description.toLowerCase().includes(q) ||
        item.specs.some(s => s.toLowerCase().includes(q)) ||
        item.merchantQuotes.some(mq => mq.merchantName.toLowerCase().includes(q))
      );
    }

    // Sorting
    if (sortBy === 'price_asc') {
      list.sort((a, b) => a.price - b.price);
    } else if (sortBy === 'price_desc') {
      list.sort((a, b) => b.price - a.price);
    } else if (sortBy === 'rating') {
      list.sort((a, b) => b.rating - a.rating);
    }

    return list;
  }, [catalogProducts, isLiveDatabase, selectedMerchantId, selectedCategory, filterWithinBudget, searchQuery, sortBy, remainingBudget]);

  const handleBuyWithAgent = (productName: string) => {
    router.push(`/?q=${encodeURIComponent(`Find and buy ${productName}`)}`);
  };

  const toggleBids = (productId: string) => {
    setExpandedBidsId(prev => prev === productId ? null : productId);
  };

  return (
    <>
      <Head>
        <title>Merchants & Catalog — AgentPay Verified Ecosystem</title>
        <meta
          name="description"
          content="Explore certified merchant networks, live delivered inventory, and launch autonomous purchasing backed by Razorpay settlement."
        />
      </Head>

      <div className="w-full max-w-5xl mx-auto space-y-8 animate-fadeIn pb-12">
        {/* Header Hero */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-[#E4E2E2]/80 dark:border-white/10 pb-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="w-2 h-2 rounded-full bg-[#FE7352] animate-pulse" />
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#AA361A] dark:text-[#FE7352] font-semibold">
                Tier-1 Partner Ecosystem · Razorpay Rails
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[#1B1C1C] dark:text-white">
              Approved Merchants & Catalog
            </h1>
            <p className="text-xs sm:text-sm text-[#4C4546] dark:text-[#C4BCBC] mt-1 max-w-2xl">
              Inspect verified merchant networks, direct settlement accounts, and live agent-searchable inventories.
              Every item is backed by authentic brand warranty and deterministic budget limits.
            </p>
          </div>

          <div className="flex items-center gap-2 font-mono text-xs shrink-0 flex-wrap">
            <button
              onClick={() => setIsProtocolModalOpen(true)}
              className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-[#FE7352]/15 to-[#D94F30]/15 hover:from-[#FE7352]/25 hover:to-[#D94F30]/25 text-[#AA361A] dark:text-[#FE7352] border border-[#FE7352]/30 flex items-center gap-2 font-semibold transition-all shadow-sm group cursor-pointer"
              title="Inspect UAP, ACP, llms.txt, and test live HTTP 402 challenge"
            >
              <span className="w-2 h-2 rounded-full bg-[#FE7352] animate-ping" />
              <span>Protocol Hub (UAP · x402 · llms.txt)</span>
              <span className="group-hover:translate-x-0.5 transition-transform text-[11px]">↗</span>
            </button>
            {isLiveDatabase ? (
              <span className="px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/40 flex items-center gap-1.5 font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>SQLite DB Connected</span>
              </span>
            ) : (
              <span className="px-3 py-1.5 rounded-lg bg-black/5 dark:bg-white/10 text-[#4C4546] dark:text-[#C4BCBC] border border-transparent flex items-center gap-1.5 font-medium">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                <span>Standalone Demo Mode</span>
              </span>
            )}
            <span className="px-3 py-1.5 rounded-lg bg-black/5 dark:bg-white/10 text-[#1B1C1C] dark:text-white">
              {filteredProducts.length} Items Loaded
            </span>
          </div>
        </div>

        {/* SECTION 1: VERIFIED MERCHANT PROFILES */}
        <section aria-labelledby="merchants-heading" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 id="merchants-heading" className="text-sm font-mono uppercase tracking-wider text-[#7E7576] dark:text-[#9E9697] font-semibold">
              Certified Merchant Networks
            </h2>
            {selectedMerchantId !== 'all' && (
              <button
                onClick={() => setSelectedMerchantId('all')}
                className="text-xs font-mono text-[#AA361A] dark:text-[#FE7352] hover:underline flex items-center gap-1"
              >
                <span>Reset to all merchants</span>
                <span>×</span>
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {MERCHANTS.map((m) => {
              const isSelected = selectedMerchantId === m.id;
              const merchantItemCount = baseCatalogList.filter(item =>
                item.merchantQuotes.some(q => q.merchantId === m.id)
              ).length;

              return (
                <div
                  key={m.id}
                  onClick={() => setSelectedMerchantId(isSelected ? 'all' : m.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setSelectedMerchantId(isSelected ? 'all' : m.id);
                    }
                  }}
                  className={`paper-card p-5 rounded-2xl transition-all cursor-pointer select-none flex flex-col justify-between relative ${
                    isSelected
                      ? 'border-2 border-[#FE7352] bg-gradient-to-b from-white to-[#FFF9F7] dark:from-[#211E1D] dark:to-[#181514] shadow-md ring-2 ring-[#FE7352]/20'
                      : 'hover:border-[#CFBFC0] dark:hover:border-white/20 hover:shadow-sm'
                  }`}
                >
                  <div>
                    {/* Top row: Badge & Rating */}
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded font-semibold bg-black/5 dark:bg-white/10 text-[#4C4546] dark:text-[#D4CCCC]">
                        {m.badge}
                      </span>
                      <span className="text-xs font-mono font-medium text-amber-600 dark:text-amber-400 flex items-center gap-1">
                        <span>★</span>
                        <span>{m.rating}</span>
                        <span className="text-[10px] text-[#7E7576] dark:text-[#9E9697]">({m.totalOrders})</span>
                      </span>
                    </div>

                    {/* Merchant Name */}
                    <h3 className="text-base font-bold text-[#1B1C1C] dark:text-white">
                      {m.name}
                    </h3>
                    <div className="font-mono text-[11px] text-[#7E7576] dark:text-[#9E9697] mt-0.5">
                      Rail: <span className="text-[#1B1C1C] dark:text-neutral-200">{m.account}</span>
                    </div>

                    <p className="text-xs text-[#4C4546] dark:text-[#C4BCBC] mt-2.5 line-clamp-2 leading-relaxed">
                      {m.description}
                    </p>

                    {/* Meta SLA Badges */}
                    <div className="space-y-1.5 mt-3 pt-3 border-t border-[#E4E2E2]/60 dark:border-white/10 text-[11px]">
                      <div className="flex items-center justify-between text-[#4C4546] dark:text-[#C4BCBC]">
                        <span className="font-mono text-[#7E7576] dark:text-[#9E9697]">Fulfillment SLA:</span>
                        <span className="font-medium">{m.sla}</span>
                      </div>
                      <div className="flex items-center justify-between text-[#4C4546] dark:text-[#C4BCBC]">
                        <span className="font-mono text-[#7E7576] dark:text-[#9E9697]">SLA Adherence:</span>
                        <span className="font-mono font-semibold text-emerald-700 dark:text-emerald-400">{m.slaAdherence}</span>
                      </div>
                    </div>
                  </div>

                  {/* Card Bottom CTA */}
                  <div className="mt-4 pt-3 border-t border-[#E4E2E2]/60 dark:border-white/10 flex items-center justify-between">
                    <span className="text-xs font-mono text-[#7E7576] dark:text-[#9E9697]">
                      {merchantItemCount} live bids
                    </span>
                    <span className={`text-xs font-semibold flex items-center gap-1 ${
                      isSelected
                        ? 'text-[#AA361A] dark:text-[#FE7352]'
                        : 'text-[#1B1C1C] dark:text-white'
                    }`}>
                      <span>{isSelected ? 'Active Filter' : 'Filter Catalog'}</span>
                      <span>{isSelected ? '✓' : '→'}</span>
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* SECTION 2: LIVE CATALOG SEARCH & FILTERS */}
        <section aria-labelledby="catalog-heading" className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-4 border-t border-[#E4E2E2]/60 dark:border-white/10">
            <div>
              <h2 id="catalog-heading" className="text-lg font-bold text-[#1B1C1C] dark:text-white">
                Merchant Catalog ({filteredProducts.length} items)
              </h2>
              <p className="text-xs text-[#7E7576] dark:text-[#9E9697]">
                Compare live prices across certified merchants and dispatch directly to AgentPay.
              </p>
            </div>

            {/* Sort Selector */}
            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="text-[#7E7576] dark:text-[#9E9697] shrink-0">Sort:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="bg-white dark:bg-[#201E1E] border border-[#E4E2E2] dark:border-white/15 rounded-lg px-2.5 py-1.5 text-xs text-[#1B1C1C] dark:text-white focus:outline-none focus:border-[#AA361A]"
              >
                <option value="recommended">Recommended</option>
                <option value="price_asc">Price: Low to High</option>
                <option value="price_desc">Price: High to Low</option>
                <option value="rating">Highest Rated</option>
              </select>
            </div>
          </div>

          {/* Search Bar & Budget Toggle */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="md:col-span-2 relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search products by title, brand, specs, or merchant..."
                className="w-full bg-white dark:bg-[#1E1C1C] border border-[#E4E2E2] dark:border-white/15 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-[#1B1C1C] dark:text-white placeholder-[#7E7576] dark:placeholder-[#8C8485] focus:outline-none focus:border-[#FE7352] transition-colors shadow-2xs"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-mono text-[#7E7576] hover:text-[#1B1C1C] dark:hover:text-white"
                >
                  Clear
                </button>
              )}
            </div>

            {/* Within Budget Guardrail Toggle */}
            <label className="paper-card px-4 py-2 rounded-xl flex items-center justify-between gap-2 cursor-pointer select-none hover:border-[#CFBFC0] dark:hover:border-white/20 transition-all">
              <div className="text-xs">
                <span className="font-semibold block text-[#1B1C1C] dark:text-white">Within Active Budget</span>
                <span className="text-[11px] font-mono text-[#7E7576] dark:text-[#9E9697]">
                  ≤ ₹{remainingBudget.toLocaleString('en-IN')} left
                </span>
              </div>
              <input
                type="checkbox"
                checked={filterWithinBudget}
                onChange={(e) => setFilterWithinBudget(e.target.checked)}
                className="w-4 h-4 rounded text-[#FE7352] accent-[#FE7352] cursor-pointer"
              />
            </label>
          </div>

          {/* Category Filter Pills & Merchant Quick Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <div className="flex flex-wrap items-center gap-1.5">
              {[
                { id: 'all', label: 'All Categories' },
                { id: 'accessories', label: 'Input & Peripherals' },
                { id: 'audio', label: 'Audio & ANC' },
                { id: 'displays', label: 'Monitors & Displays' },
                { id: 'appliances', label: 'Kitchen & Appliances' },
                { id: 'computing', label: 'Laptops & PCs' },
              ].map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={`px-3 py-1 text-xs rounded-full font-medium transition-all ${
                    selectedCategory === cat.id
                      ? 'bg-[#1B1C1C] text-white dark:bg-white dark:text-[#1B1C1C] shadow-xs'
                      : 'bg-black/5 hover:bg-black/10 dark:bg-white/10 dark:hover:bg-white/15 text-[#4C4546] dark:text-[#D4CCCC]'
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>

            {/* Merchant Quick Filter Tabs */}
            <div className="flex items-center gap-1 text-xs font-mono">
              <span className="text-[#7E7576] dark:text-[#9E9697] text-[11px] mr-1">Merchant:</span>
              <button
                onClick={() => setSelectedMerchantId('all')}
                className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all ${
                  selectedMerchantId === 'all'
                    ? 'bg-[#FE7352] text-white font-semibold'
                    : 'text-[#4C4546] dark:text-[#C4BCBC] hover:bg-black/5 dark:hover:bg-white/10'
                }`}
              >
                All ({baseCatalogList.length})
              </button>
              {MERCHANTS.map(m => {
                const count = baseCatalogList.filter(i =>
                  i.merchantQuotes.some(q => q.merchantId === m.id)
                ).length;
                return (
                  <button
                    key={m.id}
                    onClick={() => setSelectedMerchantId(m.id)}
                    className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all ${
                      selectedMerchantId === m.id
                        ? 'bg-[#FE7352] text-white font-semibold'
                        : 'text-[#4C4546] dark:text-[#C4BCBC] hover:bg-black/5 dark:hover:bg-white/10'
                    }`}
                  >
                    {m.name.split(' ')[0]} ({count})
                  </button>
                );
              })}
            </div>
          </div>

          {/* Empty State */}
          {filteredProducts.length === 0 && (
            <div className="paper-card p-12 text-center rounded-2xl space-y-3">
              <div className="text-3xl">🔍</div>
              <h3 className="text-base font-semibold text-[#1B1C1C] dark:text-white">
                No matching catalog items found
              </h3>
              <p className="text-xs text-[#7E7576] dark:text-[#9E9697] max-w-sm mx-auto">
                No products match your current filters. Try relaxing your budget constraint or searching for a different term.
              </p>
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSelectedMerchantId('all');
                  setSelectedCategory('all');
                  setFilterWithinBudget(false);
                }}
                className="px-4 py-2 rounded-xl bg-[#1B1C1C] hover:bg-black text-white dark:bg-white dark:text-black dark:hover:bg-neutral-200 text-xs font-semibold"
              >
                Reset All Filters
              </button>
            </div>
          )}

          {/* Product Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredProducts.map((prod) => {
              const isBidsExpanded = expandedBidsId === prod.id;
              const isWithinBudget = prod.price <= remainingBudget;

              return (
                <div
                  key={prod.id}
                  className="paper-card p-5 rounded-2xl flex flex-col justify-between gap-4 transition-all hover:shadow-md dark:border-white/10"
                >
                  {/* Card Content Top */}
                  <div>
                    {/* Header Chips: Merchant Badge + Category + Stock */}
                    <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="text-[10px] font-mono uppercase bg-[#FE7352]/10 dark:bg-[#FE7352]/20 text-[#AA361A] dark:text-[#FE7352] border border-[#FE7352]/30 px-2 py-0.5 rounded font-semibold">
                          {prod.primaryMerchantName}
                        </span>
                        {prod.merchantQuotes.length === 1 ? (
                          <span className="text-[10px] font-mono uppercase bg-amber-500/10 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded font-semibold">
                            Single Merchant Exclusive
                          </span>
                        ) : (
                          <span className="text-[10px] font-mono uppercase bg-blue-500/10 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded font-semibold">
                            {prod.merchantQuotes.length} Merchant Bids
                          </span>
                        )}
                        <span className="text-[10px] font-mono text-[#7E7576] dark:text-[#9E9697] uppercase tracking-wider">
                          {prod.categoryLabel}
                        </span>
                      </div>

                      <div className="flex items-center gap-1 text-[11px] font-mono text-emerald-700 dark:text-emerald-400 font-medium">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
                        <span>In Stock ({prod.stockCount})</span>
                      </div>
                    </div>

                    {/* Brand & Product Name */}
                    <div className="text-[11px] font-mono text-[#7E7576] dark:text-[#9E9697] uppercase tracking-wider">
                      {prod.brand}
                    </div>
                    <h3 className="text-base font-bold text-[#1B1C1C] dark:text-white leading-snug mt-0.5">
                      {prod.name}
                    </h3>

                    {/* Rating & Reviews */}
                    <div className="flex items-center gap-2 mt-1.5 text-xs">
                      <span className="font-mono text-amber-500 font-semibold flex items-center gap-0.5">
                        <span>★</span>
                        <span>{prod.rating}</span>
                      </span>
                      <span className="text-[#7E7576] dark:text-[#9E9697] font-mono text-[11px]">
                        ({prod.reviewsCount} reviews)
                      </span>
                      <span className="text-[#CFBFC0] dark:text-white/20">·</span>
                      <span className="text-[11px] text-[#7E7576] dark:text-[#9E9697] font-mono">
                        {prod.deliveryEta}
                      </span>
                    </div>

                    {/* Specs Pill List */}
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {prod.specs.map((spec, idx) => (
                        <span
                          key={idx}
                          className="text-[11px] font-mono px-2 py-0.5 rounded bg-black/5 dark:bg-white/10 text-[#4C4546] dark:text-[#D4CCCC]"
                        >
                          {spec}
                        </span>
                      ))}
                    </div>

                    {/* Warranty & Description */}
                    <p className="text-xs text-[#4C4546] dark:text-[#C4BCBC] mt-3 line-clamp-2 leading-relaxed">
                      {prod.description}
                    </p>
                  </div>

                  {/* Multi-Merchant Live Bids Expansion */}
                  {isBidsExpanded && (
                    <div className="bg-[#FAF9F8] dark:bg-[#181717] rounded-xl p-3 border border-[#E4E2E2]/80 dark:border-white/10 space-y-2 animate-fadeIn text-xs">
                      <div className="flex items-center justify-between text-[11px] font-mono text-[#7E7576] dark:text-[#9E9697] uppercase tracking-wider border-b border-[#E4E2E2] dark:border-white/10 pb-1">
                        <span>
                          {prod.merchantQuotes.length === 1 ? 'Exclusive Stock Quote' : `${prod.merchantQuotes.length} Verified Merchant Bids`}
                        </span>
                        <span>Delivered Quote</span>
                      </div>
                      <div className="space-y-1.5">
                        {prod.merchantQuotes.map((q) => (
                          <div
                            key={q.merchantId}
                            className="flex items-center justify-between p-2 rounded bg-white dark:bg-[#201E1E] border border-[#E4E2E2]/60 dark:border-white/10"
                          >
                            <div>
                              <div className="flex items-center gap-1.5 font-semibold text-xs text-[#1B1C1C] dark:text-white">
                                <span>{q.merchantName}</span>
                                {q.isBest && (
                                  <span className="text-[9px] font-mono uppercase bg-[#AA361A] text-white px-1 py-0.2 rounded">
                                    Lowest
                                  </span>
                                )}
                              </div>
                              <span className="text-[10px] text-[#7E7576] dark:text-[#9E9697] block font-mono">
                                {q.deliveryEta} · {q.warranty}
                              </span>
                            </div>
                            <span className="font-mono font-bold text-sm text-[#1B1C1C] dark:text-white">
                              ₹{q.price.toLocaleString('en-IN')}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Card Bottom: Price, Policy Status, and Action Button */}
                  <div className="pt-3 border-t border-[#E4E2E2]/70 dark:border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-xl font-bold font-mono text-[#1B1C1C] dark:text-white">
                          ₹{prod.price.toLocaleString('en-IN')}
                        </span>
                        <span className="text-[10px] font-mono text-[#7E7576] dark:text-[#9E9697]">
                          Delivered
                        </span>
                      </div>

                      {/* Policy Verification Pill */}
                      <div className="flex items-center gap-1 text-[11px] mt-0.5">
                        {isWithinBudget ? (
                          <span className="text-emerald-700 dark:text-emerald-400 font-mono flex items-center gap-0.5">
                            <span>✓</span>
                            <span>Within policy cap</span>
                          </span>
                        ) : (
                          <span className="text-amber-600 dark:text-amber-400 font-mono">
                            ⚠ Exceeds daily budget (₹{remainingBudget.toLocaleString('en-IN')})
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => toggleBids(prod.id)}
                        className="px-3 py-2 rounded-xl text-xs font-mono text-[#4C4546] dark:text-[#D4CCCC] bg-black/5 hover:bg-black/10 dark:bg-white/10 dark:hover:bg-white/15 transition-colors"
                        title="Compare verified bids across approved merchants"
                      >
                        {isBidsExpanded
                          ? 'Hide Bids'
                          : prod.merchantQuotes.length > 1
                            ? `Compare Bids (${prod.merchantQuotes.length})`
                            : 'Exclusive (1 Bid)'}
                      </button>

                      <button
                        onClick={() => handleBuyWithAgent(prod.name)}
                        className="px-4 py-2 rounded-xl bg-[#1B1C1C] hover:bg-black text-white dark:bg-white dark:text-[#1B1C1C] dark:hover:bg-neutral-200 text-xs font-semibold tracking-tight transition-all active:scale-98 shadow-sm flex items-center gap-1"
                      >
                        <span>Buy with AgentPay</span>
                        <span>→</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Footer info strip */}
        <div className="paper-card-subtle p-5 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-[#7E7576] dark:text-[#9E9697]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>
              All catalog orders route through Razorpay two-phase reserve escrow rails with deterministic buyer policy validation.
            </span>
          </div>
          <Link
            href="/control"
            className="text-[#AA361A] dark:text-[#FE7352] hover:underline font-mono text-[11px] shrink-0"
          >
            Adjust Spending Limits & Merchant Whitelist →
          </Link>
        </div>
      </div>

      {/* Protocol Hub Modal */}
      <ProtocolModal
        isOpen={isProtocolModalOpen}
        onClose={() => setIsProtocolModalOpen(false)}
      />
    </>
  );
}
