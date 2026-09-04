import React, { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { fetchAgentPolicy, updateAgentPolicy, AgentPolicy } from '@/lib/api';

interface CategoryRule {
  id: string;
  name: string;
  description: string;
  allowed: boolean;
}

interface MerchantRule {
  id: string;
  name: string;
  preference: 'approved' | 'ask_first' | 'blocked';
  sla: string;
}

export default function ControlPage() {
  const [policy, setPolicy] = useState<AgentPolicy | null>(null);
  
  // Interactive Limit States
  const [dailyLimit, setDailyLimit] = useState(20000);
  const [perTxLimit, setPerTxLimit] = useState(5000);
  const [spentToday, setSpentToday] = useState(12499);
  
  // Interactive Category Matrix
  const [categories, setCategories] = useState<CategoryRule[]>([
    { id: 'electronics', name: 'Electronics & Computing', description: 'Mice, keyboards, displays, laptops', allowed: true },
    { id: 'audio', name: 'Audio & Peripherals', description: 'Headphones, ANC earbuds, desktop speakers', allowed: true },
    { id: 'appliances', name: 'Home & Kitchen Appliances', description: 'Air fryers, coffee makers, smart kettles', allowed: true },
    { id: 'furniture', name: 'Office & Desk Gear', description: 'Ergonomic chairs, monitor arms, desk mats', allowed: true },
    { id: 'luxury', name: 'Luxury & Jewelry', description: 'High-end watches, jewelry, designer apparel', allowed: false }
  ]);

  // Interactive Merchant Rules
  const [merchants, setMerchants] = useState<MerchantRule[]>([
    { id: 'croma', name: 'Croma Electronics Hub', preference: 'approved', sla: 'Express 1-2 Day' },
    { id: 'reliance', name: 'Reliance Digital Tech', preference: 'approved', sla: 'Standard 2-3 Day' },
    { id: 'amazon', name: 'Amazon Prime Direct', preference: 'ask_first', sla: 'Next-Day Prime' }
  ]);

  // Live status feedback
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);

  // Policy Simulator States
  const [simAmount, setSimAmount] = useState('4499');
  const [simCategory, setSimCategory] = useState('electronics');
  const [simMerchant, setSimMerchant] = useState('Croma Electronics Hub');
  const [showSimTrail, setShowSimTrail] = useState(false);

  // Load policy on mount and on policy update events
  useEffect(() => {
    const loadPolicy = () => {
      let savedPolicy: any = null;
      try {
        const saved = localStorage.getItem('agentpay_custom_policy');
        if (saved) {
          savedPolicy = JSON.parse(saved);
          if (savedPolicy.daily_spending_limit) setDailyLimit(savedPolicy.daily_spending_limit);
          if (savedPolicy.per_transaction_limit) setPerTxLimit(savedPolicy.per_transaction_limit);
          if (savedPolicy.spent_today !== undefined) setSpentToday(savedPolicy.spent_today);
          if (savedPolicy.allowed_categories) {
            setCategories(prev => prev.map(c => ({
              ...c,
              allowed: savedPolicy.allowed_categories.includes(c.id)
            })));
          }
          if (savedPolicy.merchant_rules) {
            setMerchants(savedPolicy.merchant_rules);
          }
        }
      } catch (e) {
        console.error('Failed to read saved policy', e);
      }

      fetchAgentPolicy('agent_001')
        .then((p) => {
          setPolicy(p);
          if (!savedPolicy?.per_transaction_limit && p.per_transaction_limit) {
            setPerTxLimit(p.per_transaction_limit);
          }
          if (!savedPolicy?.daily_spending_limit && p.daily_spending_limit) {
            setDailyLimit(p.daily_spending_limit);
          }
          const liveSpent = Math.max(savedPolicy?.spent_today ?? 0, p.spent_today ?? 0);
          setSpentToday(liveSpent);
        })
        .catch(() => {
          // defaults already initialized
        });
    };

    loadPolicy();
    window.addEventListener('agentpay-policy-updated', loadPolicy);
    window.addEventListener('storage', loadPolicy);
    return () => {
      window.removeEventListener('agentpay-policy-updated', loadPolicy);
      window.removeEventListener('storage', loadPolicy);
    };
  }, []);

  // Save current limits and rules to localStorage and API
  const handleSavePolicy = async () => {
    setSaveStatus('Saving policy safeguards...');
    const allowedCatIds = categories.filter(c => c.allowed).map(c => c.id);
    const blockedMerchNames = merchants.filter(m => m.preference === 'blocked').map(m => m.name);

    const updatedPolicyObj = {
      id: 'policy_001',
      agent_id: 'agent_001',
      currency: 'INR',
      per_transaction_limit: perTxLimit,
      daily_spending_limit: dailyLimit,
      spent_today: spentToday,
      available_budget: Math.max(0, dailyLimit - spentToday),
      allowed_categories: allowedCatIds,
      blocked_merchants: blockedMerchNames,
      merchant_rules: merchants
    };

    try {
      localStorage.setItem('agentpay_custom_policy', JSON.stringify(updatedPolicyObj));
      // Dispatch custom sync event so FloatingNav budget updates immediately
      window.dispatchEvent(new Event('agentpay-policy-updated'));
      window.dispatchEvent(new Event('storage'));

      await updateAgentPolicy('agent_001', {
        per_transaction_limit: perTxLimit,
        daily_spending_limit: dailyLimit,
        allowed_categories: allowedCatIds,
        blocked_merchants: blockedMerchNames
      });
      setSaveStatus('Policy safeguards updated & active.');
      setIsDirty(false);
      setTimeout(() => setSaveStatus(null), 3000);
    } catch (e) {
      setSaveStatus('Policy saved locally and active.');
      setIsDirty(false);
      setTimeout(() => setSaveStatus(null), 3000);
    }
  };

  // Reset to default limits
  const handleResetDefaults = () => {
    setDailyLimit(20000);
    setPerTxLimit(5000);
    setCategories([
      { id: 'electronics', name: 'Electronics & Computing', description: 'Mice, keyboards, displays, laptops', allowed: true },
      { id: 'audio', name: 'Audio & Peripherals', description: 'Headphones, ANC earbuds, desktop speakers', allowed: true },
      { id: 'appliances', name: 'Home & Kitchen Appliances', description: 'Air fryers, coffee makers, smart kettles', allowed: true },
      { id: 'furniture', name: 'Office & Desk Gear', description: 'Ergonomic chairs, monitor arms, desk mats', allowed: true },
      { id: 'luxury', name: 'Luxury & Jewelry', description: 'High-end watches, jewelry, designer apparel', allowed: false }
    ]);
    setMerchants([
      { id: 'croma', name: 'Croma Electronics Hub', preference: 'approved', sla: 'Express 1-2 Day' },
      { id: 'reliance', name: 'Reliance Digital Tech', preference: 'approved', sla: 'Standard 2-3 Day' },
      { id: 'amazon', name: 'Amazon Prime Direct', preference: 'ask_first', sla: 'Next-Day Prime' }
    ]);
    setIsDirty(true);
  };

  // Toggle category
  const toggleCategory = (id: string) => {
    setCategories(prev => prev.map(c => c.id === id ? { ...c, allowed: !c.allowed } : c));
    setIsDirty(true);
  };

  // Cycle merchant preference
  const cycleMerchantPreference = (id: string) => {
    setMerchants(prev => prev.map(m => {
      if (m.id !== id) return m;
      const nextPref: 'approved' | 'ask_first' | 'blocked' =
        m.preference === 'approved' ? 'ask_first' : m.preference === 'ask_first' ? 'blocked' : 'approved';
      return { ...m, preference: nextPref };
    }));
    setIsDirty(true);
  };

  // Dynamic calculations
  const availableBudget = Math.max(0, dailyLimit - spentToday);
  const budgetUtilizationPercent = Math.min(100, Math.round((spentToday / (dailyLimit || 1)) * 100));

  // Live Simulator Evaluation
  const amountNum = parseFloat(simAmount) || 0;
  const targetCategoryObj = categories.find(c => c.id === simCategory);
  const targetMerchantObj = merchants.find(m => m.name === simMerchant || m.id === simMerchant.toLowerCase());

  const isCatAllowed = targetCategoryObj ? targetCategoryObj.allowed : true;
  const isMerchantBlocked = targetMerchantObj ? targetMerchantObj.preference === 'blocked' : false;
  const isMerchantAskFirst = targetMerchantObj ? targetMerchantObj.preference === 'ask_first' : false;
  const exceedsDaily = (spentToday + amountNum) > dailyLimit;
  const exceedsPerTx = amountNum > perTxLimit;

  let simOutcome: 'approved' | 'ask_first' | 'denied' = 'approved';
  let simReason = 'Order matches all active enterprise safeguards and executes autonomously.';

  if (isMerchantBlocked) {
    simOutcome = 'denied';
    simReason = `Merchant "${simMerchant}" is blocked by your merchant policy.`;
  } else if (!isCatAllowed) {
    simOutcome = 'denied';
    simReason = `Category "${targetCategoryObj?.name || simCategory}" is blocked in your allowed categories.`;
  } else if (exceedsDaily) {
    simOutcome = 'denied';
    simReason = `Total spend (₹${(spentToday + amountNum).toLocaleString('en-IN')}) would exceed daily spending cap of ₹${dailyLimit.toLocaleString('en-IN')}.`;
  } else if (exceedsPerTx || isMerchantAskFirst) {
    simOutcome = 'ask_first';
    simReason = exceedsPerTx
      ? `Amount ₹${amountNum.toLocaleString('en-IN')} exceeds auto-buy cap of ₹${perTxLimit.toLocaleString('en-IN')}. Requires manual authorization.`
      : `Merchant "${simMerchant}" is configured to "Ask First" before completing payment.`;
  }

  return (
    <>
      <Head>
        <title>Control — Purchase Policy & Safeguards</title>
        <meta
          name="description"
          content="Configure autonomous agent spending limits, category permissions, and certified merchant rules."
        />
      </Head>

      <div className="w-full max-w-3xl mx-auto py-6 space-y-8">
        
        {/* Page Header with Live Status & Actions */}
        <div className="border-b border-[#E4E2E2]/70 dark:border-white/10 pb-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-xs font-mono uppercase tracking-wider text-emerald-700 dark:text-emerald-400 font-semibold">
                Policy Active & Enforced
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#1B1C1C] dark:text-white">
              Policy & Safeguards
            </h1>
            <p className="text-xs sm:text-sm text-[#7E7576] dark:text-[#9E9697] mt-0.5">
              Interactive constraints governing every autonomous purchase, budget reserve, and settlement.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            {saveStatus ? (
              <span className="font-mono text-xs text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/60 px-3 py-1.5 rounded-xl border border-emerald-200 dark:border-emerald-800/40 animate-fadeIn">
                {saveStatus}
              </span>
            ) : isDirty ? (
              <span className="font-mono text-[11px] text-[#AA361A] dark:text-[#FE7352] bg-[#FE7352]/10 px-2.5 py-1 rounded-lg">
                Unsaved changes
              </span>
            ) : null}

            <button
              onClick={handleResetDefaults}
              className="px-3 py-2 text-xs font-medium text-[#7E7576] hover:text-[#1B1C1C] dark:text-[#9E9697] dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/10 rounded-xl transition-colors"
            >
              Reset Defaults
            </button>

            <button
              onClick={handleSavePolicy}
              className={`px-4 py-2 text-xs font-semibold rounded-xl transition-all shadow-sm flex items-center gap-1.5 ${
                isDirty
                  ? 'bg-[#AA361A] hover:bg-[#8e2d15] text-white dark:bg-[#FE7352] dark:text-[#141212]'
                  : 'bg-[#1B1C1C] hover:bg-black text-white dark:bg-white dark:text-[#141212] dark:hover:bg-neutral-200'
              }`}
            >
              <span>Save Safeguards</span>
              <span>✓</span>
            </button>
          </div>
        </div>

        {/* SECTION 1: DYNAMIC PLAIN-LANGUAGE CONTRACT */}
        <div className="paper-card p-6 sm:p-7 dark:bg-[#161515] dark:border-white/10 relative overflow-hidden">
          <div className="flex items-center justify-between gap-2 pb-3 mb-3 border-b border-[#E4E2E2]/60 dark:border-white/10">
            <span className="text-[10px] uppercase font-mono tracking-wider font-semibold text-[#7E7576] dark:text-[#9E9697]">
              Autonomous Governance Contract
            </span>
            <span className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400">
              Live Bound
            </span>
          </div>

          <p className="text-base sm:text-lg text-[#1B1C1C] dark:text-white leading-relaxed font-normal">
            AgentPay is authorized to autonomously purchase from{' '}
            <strong className="font-semibold text-[#1B1C1C] dark:text-white underline decoration-[#AA361A]/40 underline-offset-4">
              approved merchants
            </strong>{' '}
            when the order amount is below{' '}
            <span className="font-mono font-bold text-[#AA361A] dark:text-[#FE7352] bg-[#FE7352]/10 px-2 py-0.5 rounded-lg inline-block">
              ₹{perTxLimit.toLocaleString('en-IN')}
            </span>{' '}
            and cumulative daily spend remains under{' '}
            <span className="font-mono font-bold text-[#AA361A] dark:text-[#FE7352] bg-[#FE7352]/10 px-2 py-0.5 rounded-lg inline-block">
              ₹{dailyLimit.toLocaleString('en-IN')}
            </span>
            . Orders exceeding{' '}
            <span className="font-mono font-semibold text-[#1B1C1C] dark:text-white">
              ₹{perTxLimit.toLocaleString('en-IN')}
            </span>{' '}
            or placed with &ldquo;Ask First&rdquo; vendors pause for manual authorization.
          </p>
        </div>

        {/* SECTION 2: INTERACTIVE SPENDING LIMITS (SLIDERS & NUMERIC INPUTS) */}
        <div className="paper-card p-6 sm:p-7 dark:bg-[#161515] dark:border-white/10 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-semibold tracking-tight text-[#1B1C1C] dark:text-white">
                Spending Limits & Thresholds
              </h2>
              <p className="text-xs text-[#7E7576] dark:text-[#9E9697] mt-0.5">
                Drag the sliders or enter exact amounts to configure auto-approval thresholds.
              </p>
            </div>
            <span className="text-[11px] font-mono text-[#7E7576] dark:text-[#9E9697]">
              Currency: INR (₹)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
            
            {/* Control 1: Daily Spending Limit */}
            <div className="p-4 rounded-2xl bg-black/[0.02] dark:bg-white/[0.02] border border-black/5 dark:border-white/10 space-y-3.5">
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-xs font-semibold text-[#1B1C1C] dark:text-white block">
                    Daily Spending Cap
                  </label>
                  <span className="text-[11px] text-[#7E7576] dark:text-[#9E9697] block">
                    Maximum daily agent budget
                  </span>
                </div>

                {/* Direct Number Input */}
                <div className="relative w-32">
                  <span className="absolute left-2.5 top-2 text-xs font-mono text-[#7E7576] dark:text-[#9E9697]">
                    ₹
                  </span>
                  <input
                    type="number"
                    min="2000"
                    max="100000"
                    step="500"
                    value={dailyLimit}
                    onChange={(e) => {
                      const val = Math.max(1000, Number(e.target.value) || 0);
                      setDailyLimit(val);
                      if (perTxLimit > val) setPerTxLimit(val);
                      setIsDirty(true);
                    }}
                    className="w-full pl-6 pr-2 py-1.5 rounded-lg border border-[#E4E2E2] dark:border-white/15 bg-white dark:bg-[#1F1E1E] text-xs font-mono font-bold text-[#1B1C1C] dark:text-white focus:outline-none focus:border-[#AA361A] text-right"
                  />
                </div>
              </div>

              {/* Slider */}
              <div>
                <input
                  type="range"
                  min="5000"
                  max="100000"
                  step="1000"
                  value={dailyLimit}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setDailyLimit(val);
                    if (perTxLimit > val) setPerTxLimit(val);
                    setIsDirty(true);
                  }}
                  className="w-full accent-[#AA361A] dark:accent-[#FE7352] cursor-pointer h-2 rounded-lg bg-black/10 dark:bg-white/10"
                />
                <div className="flex justify-between text-[10px] font-mono text-[#7E7576] dark:text-[#9E9697] mt-1">
                  <span>₹5,000</span>
                  <span>₹50,000</span>
                  <span>₹1,00,000</span>
                </div>
              </div>

              {/* Quick Preset Pills */}
              <div className="flex items-center gap-1.5 pt-1">
                <span className="text-[10px] font-mono text-[#7E7576] dark:text-[#9E9697] mr-1">Presets:</span>
                {[10000, 20000, 50000, 100000].map((preset) => (
                  <button
                    key={preset}
                    onClick={() => {
                      setDailyLimit(preset);
                      if (perTxLimit > preset) setPerTxLimit(preset);
                      setIsDirty(true);
                    }}
                    className={`px-2 py-1 rounded-lg text-[10px] font-mono transition-colors ${
                      dailyLimit === preset
                        ? 'bg-[#1B1C1C] text-white dark:bg-white dark:text-black font-semibold'
                        : 'bg-black/5 dark:bg-white/10 text-[#4C4546] dark:text-[#C4BCBC] hover:bg-black/10 dark:hover:bg-white/15'
                    }`}
                  >
                    ₹{(preset / 1000)}k
                  </button>
                ))}
              </div>

              {/* Live Budget Utilization Gauge */}
              <div className="pt-2 border-t border-black/5 dark:border-white/10 text-[11px] space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-[#7E7576] dark:text-[#9E9697]">Spent Today: ₹{spentToday.toLocaleString('en-IN')}</span>
                  <span className="font-mono font-semibold text-emerald-700 dark:text-emerald-400">
                    ₹{availableBudget.toLocaleString('en-IN')} left
                  </span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-black/10 dark:bg-white/10 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      budgetUtilizationPercent > 90 ? 'bg-red-500' : budgetUtilizationPercent > 70 ? 'bg-amber-500' : 'bg-emerald-500'
                    }`}
                    style={{ width: `${budgetUtilizationPercent}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Control 2: Per-Transaction Auto-Approval Cap */}
            <div className="p-4 rounded-2xl bg-black/[0.02] dark:bg-white/[0.02] border border-black/5 dark:border-white/10 space-y-3.5">
              <div className="flex items-center justify-between">
                <div>
                  <label className="text-xs font-semibold text-[#1B1C1C] dark:text-white block">
                    Per-Order Auto-Buy Cap
                  </label>
                  <span className="text-[11px] text-[#7E7576] dark:text-[#9E9697] block">
                    Above this requires confirmation
                  </span>
                </div>

                {/* Direct Number Input */}
                <div className="relative w-32">
                  <span className="absolute left-2.5 top-2 text-xs font-mono text-[#7E7576] dark:text-[#9E9697]">
                    ₹
                  </span>
                  <input
                    type="number"
                    min="500"
                    max={dailyLimit}
                    step="500"
                    value={perTxLimit}
                    onChange={(e) => {
                      const val = Math.min(dailyLimit, Math.max(500, Number(e.target.value) || 0));
                      setPerTxLimit(val);
                      setIsDirty(true);
                    }}
                    className="w-full pl-6 pr-2 py-1.5 rounded-lg border border-[#E4E2E2] dark:border-white/15 bg-white dark:bg-[#1F1E1E] text-xs font-mono font-bold text-[#1B1C1C] dark:text-white focus:outline-none focus:border-[#AA361A] text-right"
                  />
                </div>
              </div>

              {/* Slider */}
              <div>
                <input
                  type="range"
                  min="1000"
                  max={Math.min(dailyLimit, 30000)}
                  step="500"
                  value={perTxLimit}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setPerTxLimit(val);
                    setIsDirty(true);
                  }}
                  className="w-full accent-[#AA361A] dark:accent-[#FE7352] cursor-pointer h-2 rounded-lg bg-black/10 dark:bg-white/10"
                />
                <div className="flex justify-between text-[10px] font-mono text-[#7E7576] dark:text-[#9E9697] mt-1">
                  <span>₹1,000</span>
                  <span>₹15,000</span>
                  <span>₹{Math.min(dailyLimit, 30000).toLocaleString('en-IN')}</span>
                </div>
              </div>

              {/* Quick Preset Pills */}
              <div className="flex items-center gap-1.5 pt-1">
                <span className="text-[10px] font-mono text-[#7E7576] dark:text-[#9E9697] mr-1">Presets:</span>
                {[2500, 5000, 10000, 15000].map((preset) => {
                  const isDisabled = preset > dailyLimit;
                  return (
                    <button
                      key={preset}
                      disabled={isDisabled}
                      onClick={() => {
                        setPerTxLimit(preset);
                        setIsDirty(true);
                      }}
                      className={`px-2 py-1 rounded-lg text-[10px] font-mono transition-colors ${
                        perTxLimit === preset
                          ? 'bg-[#1B1C1C] text-white dark:bg-white dark:text-black font-semibold'
                          : isDisabled
                          ? 'opacity-40 cursor-not-allowed bg-black/5 dark:bg-white/5 text-[#7E7576]'
                          : 'bg-black/5 dark:bg-white/10 text-[#4C4546] dark:text-[#C4BCBC] hover:bg-black/10 dark:hover:bg-white/15'
                      }`}
                    >
                      ₹{(preset / 1000)}k
                    </button>
                  );
                })}
              </div>

              {/* Status Note */}
              <div className="pt-2 border-t border-black/5 dark:border-white/10 text-[11px] text-[#7E7576] dark:text-[#9E9697]">
                Orders up to <span className="font-semibold text-[#1B1C1C] dark:text-white font-mono">₹{perTxLimit.toLocaleString('en-IN')}</span> settle instantly with 2-phase reserve lock.
              </div>
            </div>

          </div>
        </div>

        {/* SECTION 3: INTERACTIVE CATEGORY MATRIX (ALLOW / BLOCK TOGGLES) */}
        <div className="paper-card p-6 sm:p-7 dark:bg-[#161515] dark:border-white/10 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold tracking-tight text-[#1B1C1C] dark:text-white">
                Allowed Commerce Categories
              </h2>
              <p className="text-xs text-[#7E7576] dark:text-[#9E9697] mt-0.5">
                Click any category card to toggle permissions. Blocked categories are rejected immediately.
              </p>
            </div>
            <span className="text-[11px] font-mono text-[#7E7576] dark:text-[#9E9697]">
              {categories.filter(c => c.allowed).length} of {categories.length} Allowed
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            {categories.map((cat) => (
              <div
                key={cat.id}
                onClick={() => toggleCategory(cat.id)}
                className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                  cat.allowed
                    ? 'bg-black/[0.02] dark:bg-white/[0.03] border-black/10 dark:border-white/15 hover:border-black/20 dark:hover:border-white/25'
                    : 'bg-red-50/30 dark:bg-red-950/15 border-red-200 dark:border-red-900/40 opacity-80'
                }`}
              >
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-[#1B1C1C] dark:text-white">
                      {cat.name}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#7E7576] dark:text-[#9E9697]">
                    {cat.description}
                  </p>
                </div>

                <div className="shrink-0">
                  <span
                    className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold transition-colors ${
                      cat.allowed
                        ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/40'
                        : 'bg-red-50 dark:bg-red-950/60 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800/40'
                    }`}
                  >
                    {cat.allowed ? '✓ Allowed' : '✕ Blocked'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* SECTION 4: INTERACTIVE CERTIFIED MERCHANT RULES */}
        <div className="paper-card p-6 sm:p-7 dark:bg-[#161515] dark:border-white/10 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold tracking-tight text-[#1B1C1C] dark:text-white">
                Certified Merchant Governance
              </h2>
              <p className="text-xs text-[#7E7576] dark:text-[#9E9697] mt-0.5">
                Set autonomous checkout behavior per vendor: Auto-Approve, Ask First, or Block.
              </p>
            </div>
            <span className="text-[11px] font-mono text-[#7E7576] dark:text-[#9E9697]">
              Multi-Supplier Arbitrage
            </span>
          </div>

          <div className="space-y-2.5 pt-1">
            {merchants.map((merchant) => (
              <div
                key={merchant.id}
                className="p-3.5 rounded-2xl bg-black/[0.02] dark:bg-white/[0.02] border border-black/5 dark:border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-[#1B1C1C] dark:text-white font-sans">
                      {merchant.name}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-black/5 dark:bg-white/10 text-[#7E7576] dark:text-[#9E9697]">
                      {merchant.sla}
                    </span>
                  </div>
                  <span className="text-[11px] text-[#7E7576] dark:text-[#9E9697]">
                    Certified Razorpay Settlement Rail Partner
                  </span>
                </div>

                {/* 3-Way Segment Selector */}
                <div className="flex items-center gap-1 p-1 rounded-xl bg-black/5 dark:bg-white/5 border border-black/5 dark:border-white/10 text-xs shrink-0 self-start sm:self-auto">
                  <button
                    onClick={() => {
                      setMerchants(prev => prev.map(m => m.id === merchant.id ? { ...m, preference: 'approved' } : m));
                      setIsDirty(true);
                    }}
                    className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all ${
                      merchant.preference === 'approved'
                        ? 'bg-emerald-600 text-white font-semibold shadow-xs'
                        : 'text-[#7E7576] dark:text-[#9E9697] hover:text-[#1B1C1C] dark:hover:text-white'
                    }`}
                  >
                    Auto-Approve
                  </button>

                  <button
                    onClick={() => {
                      setMerchants(prev => prev.map(m => m.id === merchant.id ? { ...m, preference: 'ask_first' } : m));
                      setIsDirty(true);
                    }}
                    className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all ${
                      merchant.preference === 'ask_first'
                        ? 'bg-amber-600 text-white font-semibold shadow-xs'
                        : 'text-[#7E7576] dark:text-[#9E9697] hover:text-[#1B1C1C] dark:hover:text-white'
                    }`}
                  >
                    Ask First
                  </button>

                  <button
                    onClick={() => {
                      setMerchants(prev => prev.map(m => m.id === merchant.id ? { ...m, preference: 'blocked' } : m));
                      setIsDirty(true);
                    }}
                    className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all ${
                      merchant.preference === 'blocked'
                        ? 'bg-red-600 text-white font-semibold shadow-xs'
                        : 'text-[#7E7576] dark:text-[#9E9697] hover:text-[#1B1C1C] dark:hover:text-white'
                    }`}
                  >
                    Block
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* SECTION 5: LIVE NARRATIVE POLICY SANDBOX (SIMULATOR) */}
        <div className="paper-card p-6 sm:p-7 dark:bg-[#161515] dark:border-white/10 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold tracking-tight text-[#1B1C1C] dark:text-white">
                Live Safeguard Sandbox
              </h2>
              <p className="text-xs text-[#7E7576] dark:text-[#9E9697] mt-0.5">
                Simulate how the policy engine evaluates an incoming autonomous order in real-time.
              </p>
            </div>
            <span className="font-mono text-[11px] text-emerald-600 dark:text-emerald-400">
              Live Evaluation
            </span>
          </div>

          {/* Input Row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
            <div>
              <label className="block text-[10px] font-mono text-[#7E7576] dark:text-[#9E9697] uppercase mb-1">
                ORDER AMOUNT (₹)
              </label>
              <input
                type="number"
                value={simAmount}
                onChange={(e) => setSimAmount(e.target.value)}
                className="w-full bg-white/70 dark:bg-[#1A1919] border border-[#E4E2E2] dark:border-white/15 rounded-xl px-3 py-2 font-mono text-xs text-[#1B1C1C] dark:text-white focus:outline-none focus:border-[#AA361A]"
              />
            </div>

            <div>
              <label className="block text-[10px] font-mono text-[#7E7576] dark:text-[#9E9697] uppercase mb-1">
                CATEGORY
              </label>
              <select
                value={simCategory}
                onChange={(e) => setSimCategory(e.target.value)}
                className="w-full bg-white/70 dark:bg-[#1A1919] border border-[#E4E2E2] dark:border-white/15 rounded-xl px-3 py-2 text-xs text-[#1B1C1C] dark:text-white focus:outline-none focus:border-[#AA361A]"
              >
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} {!c.allowed ? '(Blocked)' : ''}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-mono text-[#7E7576] dark:text-[#9E9697] uppercase mb-1">
                MERCHANT
              </label>
              <select
                value={simMerchant}
                onChange={(e) => setSimMerchant(e.target.value)}
                className="w-full bg-white/70 dark:bg-[#1A1919] border border-[#E4E2E2] dark:border-white/15 rounded-xl px-3 py-2 text-xs text-[#1B1C1C] dark:text-white focus:outline-none focus:border-[#AA361A]"
              >
                {merchants.map((m) => (
                  <option key={m.id} value={m.name}>
                    {m.name} ({m.preference === 'approved' ? 'Auto' : m.preference === 'ask_first' ? 'Ask' : 'Blocked'})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Live Verdict Banner */}
          <div
            className={`p-4 rounded-2xl text-xs sm:text-sm font-medium flex items-center justify-between gap-3 transition-all ${
              simOutcome === 'approved'
                ? 'bg-emerald-50/70 dark:bg-emerald-950/40 text-emerald-900 dark:text-emerald-200 border border-emerald-200 dark:border-emerald-800/40'
                : simOutcome === 'ask_first'
                ? 'bg-amber-50/70 dark:bg-amber-950/40 text-amber-900 dark:text-amber-200 border border-amber-200 dark:border-amber-800/40'
                : 'bg-red-50/70 dark:bg-red-950/40 text-red-900 dark:text-red-200 border border-red-200 dark:border-red-800/40'
            }`}
          >
            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm">
                  {simOutcome === 'approved' ? '✓ APPROVED' : simOutcome === 'ask_first' ? '⚠ REQUIRES HUMAN CONFIRMATION' : '✕ DENIED BY POLICY'}
                </span>
              </div>
              <p className="text-xs opacity-90 leading-relaxed">
                {simReason}
              </p>
            </div>

            <button
              onClick={() => setShowSimTrail(!showSimTrail)}
              className="text-xs font-mono underline underline-offset-4 shrink-0 transition-colors"
            >
              {showSimTrail ? 'Hide Trail' : 'Inspect Trail'}
            </button>
          </div>

          {/* Detailed Guardrail Pipeline Breakdown */}
          {showSimTrail && (
            <div className="p-4 rounded-xl bg-black/[0.02] dark:bg-white/[0.02] border border-black/5 dark:border-white/10 font-mono text-xs space-y-2 text-[#4C4546] dark:text-[#C4BCBC] animate-fadeIn">
              <div className="flex justify-between items-center py-1 border-b border-black/5 dark:border-white/5">
                <span>Guardrail 1: Category Whitelist Check</span>
                <span className={isCatAllowed ? 'text-emerald-600 dark:text-emerald-400 font-semibold' : 'text-red-600 dark:text-red-400 font-semibold'}>
                  {isCatAllowed ? 'PASSED (Allowed Category)' : 'FAILED (Category Blocked)'}
                </span>
              </div>

              <div className="flex justify-between items-center py-1 border-b border-black/5 dark:border-white/5">
                <span>Guardrail 2: Merchant Governance Rule</span>
                <span className={isMerchantBlocked ? 'text-red-600 dark:text-red-400 font-semibold' : isMerchantAskFirst ? 'text-amber-600 dark:text-amber-400 font-semibold' : 'text-emerald-600 dark:text-emerald-400 font-semibold'}>
                  {isMerchantBlocked ? 'FAILED (Merchant Blocked)' : isMerchantAskFirst ? 'FLAGGED (Ask First Required)' : 'PASSED (Auto-Approve Partner)'}
                </span>
              </div>

              <div className="flex justify-between items-center py-1 border-b border-black/5 dark:border-white/5">
                <span>Guardrail 3: Cumulative Daily Allowance (₹{dailyLimit.toLocaleString('en-IN')})</span>
                <span className={exceedsDaily ? 'text-red-600 dark:text-red-400 font-semibold' : 'text-emerald-600 dark:text-emerald-400 font-semibold'}>
                  {exceedsDaily ? `FAILED (Needs ₹${amountNum.toLocaleString('en-IN')}, only ₹${availableBudget.toLocaleString('en-IN')} available)` : `PASSED (₹${Math.max(0, availableBudget - amountNum).toLocaleString('en-IN')} remaining)`}
                </span>
              </div>

              <div className="flex justify-between items-center py-1">
                <span>Guardrail 4: Per-Transaction Auto-Buy Cap (₹{perTxLimit.toLocaleString('en-IN')})</span>
                <span className={exceedsPerTx ? 'text-amber-600 dark:text-amber-400 font-semibold' : 'text-emerald-600 dark:text-emerald-400 font-semibold'}>
                  {exceedsPerTx ? 'HUMAN_AUTHORIZATION_REQUIRED' : 'PASSED (Autonomous Settle)'}
                </span>
              </div>
            </div>
          )}
        </div>

      </div>
    </>
  );
}
