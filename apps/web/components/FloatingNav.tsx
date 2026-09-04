import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { fetchAgentPolicy, AgentPolicy } from '@/lib/api';
import { useTheme } from '@/lib/ThemeContext';

export function FloatingNav() {
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();
  const [policy, setPolicy] = useState<AgentPolicy | null>(null);
  const [isAutonomyOn, setIsAutonomyOn] = useState(true);
  const [showAutonomyModal, setShowAutonomyModal] = useState(false);

  useEffect(() => {
    const loadPolicy = () => {
      try {
        const saved = localStorage.getItem('agentpay_custom_policy');
        if (saved) {
          const parsed = JSON.parse(saved);
          setPolicy(parsed);
          return;
        }
      } catch (e) {
        console.error('Failed to read custom policy', e);
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
    window.addEventListener('storage', loadPolicy);
    return () => {
      window.removeEventListener('agentpay-policy-updated', loadPolicy);
      window.removeEventListener('storage', loadPolicy);
    };
  }, []);

  const remainingBudget = policy?.available_budget !== undefined
    ? policy.available_budget
    : (policy?.daily_spending_limit ? Math.max(0, policy.daily_spending_limit - (policy.spent_today || 12499)) : 7501);

  const currentPath = router.pathname;
  const isBuy = currentPath === '/' || currentPath === '/buy' || currentPath === '/chat';
  const isControl = currentPath === '/control' || currentPath === '/policy';
  const isMerchants = currentPath === '/merchants' || currentPath === '/catalog';
  const isHistory = currentPath === '/history' || currentPath === '/evidence' || currentPath === '/timeline';

  return (
    <>
      <header className="fixed top-5 left-1/2 -translate-x-1/2 z-50 w-full max-w-3xl px-4 pointer-events-none">
        <div className="glass-nav rounded-full px-3.5 py-2 sm:px-6 sm:py-2.5 flex items-center justify-between pointer-events-auto transition-all">
          {/* Logo Mark */}
          <Link href="/" className="flex items-center gap-2 group">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FE7352] group-hover:scale-110 transition-transform"></span>
            <span className="font-semibold text-sm tracking-tight text-[#1B1C1C] dark:text-white">AgentPay</span>
          </Link>

          {/* Mode Navigation */}
          <nav className="flex items-center gap-1 sm:gap-1.5">
            <Link
              href="/"
              className={`px-2.5 sm:px-3 py-1 text-xs sm:text-sm font-medium rounded-full transition-all ${
                isBuy
                  ? 'bg-[#1B1C1C] text-white dark:bg-white dark:text-[#1B1C1C] shadow-sm'
                  : 'text-[#4C4546] hover:text-[#1B1C1C] hover:bg-black/5 dark:text-[#A8A29E] dark:hover:text-white dark:hover:bg-white/10'
              }`}
            >
              Buy
            </Link>
            <Link
              href="/control"
              className={`px-2.5 sm:px-3 py-1 text-xs sm:text-sm font-medium rounded-full transition-all ${
                isControl
                  ? 'bg-[#1B1C1C] text-white dark:bg-white dark:text-[#1B1C1C] shadow-sm'
                  : 'text-[#4C4546] hover:text-[#1B1C1C] hover:bg-black/5 dark:text-[#A8A29E] dark:hover:text-white dark:hover:bg-white/10'
              }`}
            >
              Control
            </Link>
            <Link
              href="/merchants"
              className={`px-2.5 sm:px-3 py-1 text-xs sm:text-sm font-medium rounded-full transition-all ${
                isMerchants
                  ? 'bg-[#1B1C1C] text-white dark:bg-white dark:text-[#1B1C1C] shadow-sm'
                  : 'text-[#4C4546] hover:text-[#1B1C1C] hover:bg-black/5 dark:text-[#A8A29E] dark:hover:text-white dark:hover:bg-white/10'
              }`}
            >
              Merchants
            </Link>
            <Link
              href="/history"
              className={`px-2.5 sm:px-3 py-1 text-xs sm:text-sm font-medium rounded-full transition-all ${
                isHistory
                  ? 'bg-[#1B1C1C] text-white dark:bg-white dark:text-[#1B1C1C] shadow-sm'
                  : 'text-[#4C4546] hover:text-[#1B1C1C] hover:bg-black/5 dark:text-[#A8A29E] dark:hover:text-white dark:hover:bg-white/10'
              }`}
            >
              History
            </Link>
          </nav>

          {/* Budget, Autonomy & Theme Control */}
          <div className="flex items-center gap-2 sm:gap-3 text-xs sm:text-sm">
            <span className="font-mono text-[11px] sm:text-xs text-[#7E7576] dark:text-[#9E9697] hidden md:inline-block">
              ₹{remainingBudget.toLocaleString('en-IN')} left
            </span>
            <span className="text-[#CFBFC0] dark:text-white/20 hidden md:inline-block">|</span>

            {/* Autonomy Toggle */}
            <button
              onClick={() => setShowAutonomyModal(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/5 hover:bg-black/10 dark:bg-white/10 dark:hover:bg-white/15 transition-colors text-[#1B1C1C] dark:text-white text-xs font-medium"
              title="Toggle Autonomous Shopping"
            >
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  isAutonomyOn ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
                }`}
              ></span>
              <span className="hidden sm:inline">Autonomy {isAutonomyOn ? 'On' : 'Paused'}</span>
              <span className="sm:hidden">{isAutonomyOn ? 'Auto' : 'Hold'}</span>
            </button>

            {/* Dark Mode Option Toggle */}
            <button
              id="theme-toggle-btn"
              onClick={toggleTheme}
              aria-label={theme === 'dark' ? "Switch to light mode" : "Switch to dark mode"}
              title={theme === 'dark' ? "Switch to light mode" : "Switch to dark mode"}
              className="w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center bg-black/5 hover:bg-black/10 dark:bg-white/10 dark:hover:bg-white/15 text-[#4C4546] dark:text-amber-300 transition-transform active:scale-95"
            >
              {theme === 'dark' ? (
                /* Sun Icon */
                <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              ) : (
                /* Moon Icon */
                <svg className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[#4C4546]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Autonomy Pause Confirmation Sheet */}
      {showAutonomyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/25 dark:bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="glass-sheet max-w-sm w-full p-6 rounded-2xl relative shadow-2xl">
            <h3 className="text-base font-semibold text-[#1B1C1C] dark:text-white mb-2">
              {isAutonomyOn ? 'Pause autonomous purchases?' : 'Resume autonomous purchases?'}
            </h3>
            <p className="text-xs text-[#4C4546] dark:text-[#C4BCBC] leading-relaxed mb-5">
              {isAutonomyOn
                ? 'Pause new autonomous purchases? Existing authorized holds can finish settling without interruption.'
                : 'Resume autonomous purchasing? The AI Buyer will proceed within your configured limits.'}
            </p>
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => setShowAutonomyModal(false)}
                className="px-3 py-1.5 text-xs text-[#4C4546] hover:text-[#1B1C1C] dark:text-[#C4BCBC] dark:hover:text-white rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setIsAutonomyOn(!isAutonomyOn);
                  setShowAutonomyModal(false);
                }}
                className="px-4 py-1.5 text-xs font-medium rounded-lg bg-[#1B1C1C] text-white hover:bg-black dark:bg-white dark:text-black dark:hover:bg-neutral-200 transition-colors"
              >
                {isAutonomyOn ? 'Pause Autonomy' : 'Resume Autonomy'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

