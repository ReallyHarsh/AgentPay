import React, { useState, useRef, useEffect } from 'react';
import Head from 'next/head';
import { sendChatMessage, fetchAgentPolicy, ChatResponse, Transaction, CheckoutProposal, Clarification, AgentPolicy } from '@/lib/api';
import { StateMachineDiagram } from '@/components/StateMachineDiagram';
import { ReceiptModal } from '@/components/ReceiptModal';
import { ConversationalCheckoutCard } from '@/components/ConversationalCheckoutCard';
import { InteractiveClarificationCard } from '@/components/InteractiveClarificationCard';

interface Message {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  steps?: ChatResponse['steps'];
  clarification?: Clarification;
  proposal?: CheckoutProposal;
  transaction?: Transaction;
  feedbackGiven?: boolean;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg_welcome',
      sender: 'agent',
      text: (
        "👋 **Welcome to AgentPay Conversational AI Checkout!**\n\n" +
        "I am your **Autonomous AI Buyer Agent**. Driven by a unified multi-tool calling loop, I search multi-vendor catalogs, compare candidate quotes, request clarifications when criteria are broad, and execute authorized purchases through the AgentPay Gateway with **two-phase reserve-then-commit** budget controls.\n\n" +
        "⚡ **Try asking naturally:**\n" +
        "- *'Find me some headphones'* (Interactive Inquiry Loop)\n" +
        "- *'Find a 27-inch 4K monitor for coding'* (Multi-Choice Proposal)\n" +
        "- *'Auto-buy wireless ANC headphones under ₹5,000'* (Autonomous Fast Path)\n" +
        "- *'Auto-buy Keychron K2 keyboard under ₹5,000 (test payment failure)'* (Reserve-Then-Release Graceful Failure Demo)"
      )
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeReceipt, setActiveReceipt] = useState<any>(null);
  const [expandedTraceId, setExpandedTraceId] = useState<string | null>(null);
  const [ratings, setRatings] = useState<Record<string, number>>({});
  const [livePolicy, setLivePolicy] = useState<AgentPolicy | null>(null);
  const [activeReserveAnimation, setActiveReserveAnimation] = useState<{
    stage: 'RESERVED' | 'RELEASED' | 'COMMITTED';
    amount: number;
    preAvailable: number;
    postAvailable: number;
    finalAvailable: number;
  } | null>(null);

  const refreshPolicy = async () => {
    try {
      const p = await fetchAgentPolicy('agent_001');
      setLivePolicy(p);
    } catch (e) {
      console.error('Failed to fetch live policy', e);
    }
  };

  const triggerConsequenceAnimation = (lifecycle: any) => {
    if (!lifecycle || !lifecycle.has_reservation) return;
    const amount = lifecycle.reserved_amount || 4999;
    const preAvailable = lifecycle.pre_reserve_available || 20000;
    const postAvailable = lifecycle.post_reserve_available !== undefined ? lifecycle.post_reserve_available : (preAvailable - amount);
    const finalAvailable = lifecycle.final_available !== undefined ? lifecycle.final_available : (lifecycle.is_released ? preAvailable : postAvailable);

    // Step 1: Immediate hold on policy approval (Show Available Budget go down!)
    setActiveReserveAnimation({
      stage: 'RESERVED',
      amount,
      preAvailable,
      postAvailable,
      finalAvailable
    });
    setLivePolicy(prev => prev ? {
      ...prev,
      available_budget: postAvailable,
      currently_reserved: amount
    } : prev);

    // Step 2: After 1500ms pause, trigger Phase 2 (Release back UP or Commit)
    setTimeout(() => {
      if (lifecycle.is_released) {
        setActiveReserveAnimation({
          stage: 'RELEASED',
          amount,
          preAvailable,
          postAvailable,
          finalAvailable
        });
        setLivePolicy(prev => prev ? {
          ...prev,
          available_budget: finalAvailable,
          currently_reserved: 0
        } : prev);

        setTimeout(() => {
          setActiveReserveAnimation(null);
        }, 2800);
      } else {
        setActiveReserveAnimation({
          stage: 'COMMITTED',
          amount,
          preAvailable,
          postAvailable,
          finalAvailable
        });
        setLivePolicy(prev => prev ? {
          ...prev,
          available_budget: finalAvailable,
          currently_reserved: 0,
          spent_today: (prev.spent_today || 0) + amount
        } : prev);

        setTimeout(() => {
          setActiveReserveAnimation(null);
        }, 2400);
      }
    }, 1600);
  };

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    refreshPolicy();
  }, []);

  const handleSend = async (customMessage?: string) => {
    const textToSend = customMessage || input;
    if (!textToSend.trim() || loading) return;

    const userMsgId = `user_${Date.now()}`;
    const newMessages: Message[] = [
      ...messages,
      { id: userMsgId, sender: 'user', text: textToSend }
    ];
    setMessages(newMessages);
    if (!customMessage) setInput('');
    setLoading(true);

    try {
      const response = await sendChatMessage(textToSend);
      const agentMsgId = `agent_${Date.now()}`;
      setMessages([
        ...newMessages,
        {
          id: agentMsgId,
          sender: 'agent',
          text: response.response,
          steps: response.steps,
          clarification: response.clarification,
          proposal: response.proposal,
          transaction: response.transaction
        }
      ]);
      if (response.transaction) {
        setExpandedTraceId(agentMsgId);
        if (response.transaction.budget_lifecycle?.has_reservation) {
          triggerConsequenceAnimation(response.transaction.budget_lifecycle);
        } else {
          await refreshPolicy();
        }
      } else {
        await refreshPolicy();
      }
    } catch (err: any) {
      setMessages([
        ...newMessages,
        {
          id: `err_${Date.now()}`,
          sender: 'agent',
          text: `⚠️ **Error communicating with AI Buyer Agent:** ${err.message || 'Could not connect to AgentPay backend.'}`
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmPurchase = (productId: string, merchantId: string, amount: number) => {
    handleSend(`Confirm and authorize purchase of SKU ${productId} from merchant ${merchantId} for ₹${amount}`);
  };

  const handleFeedbackSubmit = (msgId: string, starRating: number) => {
    setRatings(prev => ({ ...prev, [msgId]: starRating }));
    setMessages(prev => prev.map(m => m.id === msgId ? { ...m, feedbackGiven: true } : m));
  };

  const presetDemos = [
    {
      title: "Broad Query (Clarification Loop)",
      subtitle: "Asks user for preferences",
      prompt: "Find me some headphones",
      badge: "CLARIFY QUESTION",
      badgeClass: "bg-surface-container-high text-primary border-outline-variant/30"
    },
    {
      title: "Interactive Monitor Choice",
      subtitle: "Presents 4K options to pick",
      prompt: "Find a 27-inch 4K monitor with USB-C for my setup",
      badge: "KEEP IN LOOP",
      badgeClass: "bg-secondary-container text-on-secondary-container border-secondary-fixed"
    },
    {
      title: "Autonomous Buy Bypass",
      subtitle: "Explicit auto-buy instruction",
      prompt: "Auto-buy wireless ANC headphones under ₹5,000 without asking",
      badge: "AUTO-BUY (₹4,499)",
      badgeClass: "bg-emerald-100 text-emerald-900 border-emerald-300"
    },
    {
      title: "Graceful Failure (Reserve ➔ Release)",
      subtitle: "Declined card restores budget",
      prompt: "Auto-buy Keychron K2 mechanical keyboard under ₹5,000 (test payment failure)",
      badge: "RESERVE ➔ RELEASE",
      badgeClass: "bg-amber-100 text-amber-900 border-amber-300"
    },
    {
      title: "OLED Laptop (Policy Denied)",
      subtitle: "32GB RAM, 1TB SSD",
      prompt: "Auto-buy Dell XPS 15 OLED laptop with 32GB RAM",
      badge: "POLICY BLOCKED",
      badgeClass: "bg-error-container text-on-error-container border-error"
    }
  ];

  return (
    <div className="flex flex-col gap-6 w-full">
      <Head>
        <title>Dashboard & Conversational AI Checkout — AgentPay</title>
      </Head>

      {/* Hero Section */}
      <div className="flex flex-col xl:flex-row justify-between items-start xl:items-end gap-6 pb-2">
        <div className="flex items-center gap-6">
          <div className="w-20 h-20 rounded-full border border-outline-variant/40 flex flex-col items-center justify-center bg-white shadow-soft shrink-0">
            <span className="font-display-md text-display-md text-primary leading-none text-3xl font-bold">
              {new Date().getDate()}
            </span>
          </div>
          <div>
            <h2 className="font-headline-lg text-headline-lg font-bold text-primary text-2xl sm:text-3xl">
              {new Date().toLocaleDateString('en-US', { weekday: 'short' })},
            </h2>
            <p className="font-headline-lg text-headline-lg text-on-surface-variant text-2xl sm:text-3xl">
              {new Date().toLocaleDateString('en-US', { month: 'long' })}
            </p>
          </div>
          <button
            onClick={() => handleSend("Find me some headphones")}
            className="hidden sm:flex ml-4 bg-secondary text-on-secondary px-6 py-3.5 rounded-full font-body-lg font-bold items-center gap-2 hover:opacity-90 transition-opacity shadow-sm"
          >
            <span>Ask AI Buyer (HITL Demo)</span>
            <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
          </button>
        </div>

        <div className="text-right flex items-center gap-4 self-end xl:self-auto">
          <div>
            <h1 className="font-display-lg text-display-lg font-bold text-primary mb-0.5 text-2xl sm:text-3xl">
              Human-in-the-Loop Checkout 🤝
            </h1>
            <p className="font-display-md text-display-md text-outline text-lg sm:text-xl">
              Interactive Inquiries • Multi-Choice Resolution • AgentPay Guardrails
            </p>
          </div>
        </div>
      </div>

      {/* Bento Grid: AI Status & Intent Chips */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-bento-gap">
        {/* Live Intent Radar (8 cols) */}
        <div className="lg:col-span-8 bento-card p-6 relative overflow-hidden flex flex-col justify-between min-h-[220px]">
          <div className="flex justify-between items-start z-10">
            <div className="flex items-center gap-3">
              <div className="relative w-10 h-10 flex items-center justify-center">
                <div className="absolute inset-0 border-2 border-secondary rounded-full pulse-ring"></div>
                <span className="material-symbols-outlined text-secondary z-10 text-[24px]">psychology</span>
              </div>
              <div>
                <h3 className="font-stat-lg text-stat-lg text-primary font-bold">Autonomous AI Buyer Active (Single Agent)</h3>
                <p className="text-xs text-on-surface-variant">Architecture: Single Agent with iterative Multi-Tool Calling Loop & Human-in-the-loop safeguards.</p>
              </div>
            </div>
            <span className="bg-surface-container-high text-xs px-3 py-1 rounded-full font-label-caps tracking-wide border border-outline-variant/30 flex items-center gap-1.5 font-bold">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span> HITL By Default
            </span>
          </div>

          <div className="mt-4 z-10 space-y-2">
            <div className="flex items-center gap-2.5 text-xs text-on-surface-variant">
              <span className="material-symbols-outlined text-sm text-secondary">help_outline</span>
              <span><strong>Interactive Inquiries:</strong> Agent asks for missing constraints (size, noise cancellation, RAM) when goals are broad.</span>
            </div>
            <div className="flex items-center gap-2.5 text-xs text-on-surface-variant">
              <span className="material-symbols-outlined text-sm text-secondary">alt_route</span>
              <span><strong>Choice Resolution:</strong> Compare Budget Friendly vs Flagship Pro tiers with merchant switching.</span>
            </div>
            <div className="flex items-center gap-2.5 text-xs text-primary font-bold relative">
              <span className="material-symbols-outlined text-secondary text-sm">lock</span>
              <span><strong>Explicit Bypass:</strong> Say "Auto-buy" to authorize autonomous zero-touch purchase.</span>
            </div>
          </div>
        </div>

        {/* Intent Parameters (4 cols) */}
        <div className="lg:col-span-4 bento-card p-6 flex flex-col justify-between min-h-[220px]">
          <div>
            <h3 className="font-body-lg text-body-lg text-primary mb-3 flex items-center gap-2 font-bold">
              <span className="material-symbols-outlined text-lg text-secondary">tune</span> Try Sample Inquiries
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {presetDemos.map((demo, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(demo.prompt)}
                  disabled={loading}
                  className="bg-surface-container hover:bg-surface-container-high text-xs px-3 py-1.5 rounded-lg border border-outline-variant/30 flex items-center gap-1.5 font-bold transition-all"
                >
                  <span>{demo.title}</span>
                  <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded-full border uppercase ${demo.badgeClass}`}>
                    {demo.badge}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className={`mt-4 p-3.5 rounded-xl border transition-all duration-300 space-y-2 ${
            activeReserveAnimation?.stage === 'RESERVED'
              ? 'bg-amber-50/70 border-amber-400 ring-2 ring-amber-300/60 shadow-md'
              : activeReserveAnimation?.stage === 'RELEASED'
              ? 'bg-emerald-50/70 border-emerald-400 ring-2 ring-emerald-300/60 shadow-md'
              : 'bg-surface-container border-outline-variant/30'
          }`}>
            {/* Live Animation Status Badge */}
            {activeReserveAnimation && (
              <div className={`text-[10px] px-2.5 py-1 rounded-lg border font-bold flex items-center justify-between animate-fadeIn ${
                activeReserveAnimation.stage === 'RESERVED'
                  ? 'bg-amber-100 text-amber-900 border-amber-300'
                  : activeReserveAnimation.stage === 'RELEASED'
                  ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                  : 'bg-secondary-container text-on-secondary-container border-secondary-fixed'
              }`}>
                <div className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[13px] animate-spin">
                    {activeReserveAnimation.stage === 'RESERVED' ? 'lock_clock' : activeReserveAnimation.stage === 'RELEASED' ? 'published_with_changes' : 'task_alt'}
                  </span>
                  <span>
                    {activeReserveAnimation.stage === 'RESERVED'
                      ? `Phase 1: Reserve Hold (-₹${activeReserveAnimation.amount.toLocaleString()})`
                      : activeReserveAnimation.stage === 'RELEASED'
                      ? `Phase 2: Hold Released (+₹${activeReserveAnimation.amount.toLocaleString()})`
                      : `Phase 2: Committed (₹${activeReserveAnimation.amount.toLocaleString()})`}
                  </span>
                </div>
                <span className="font-mono text-[9px] uppercase px-1.5 py-0.5 rounded bg-white/70">
                  {activeReserveAnimation.stage === 'RESERVED' ? 'AUTHORIZED' : activeReserveAnimation.stage === 'RELEASED' ? 'RELEASED' : 'CAPTURED'}
                </span>
              </div>
            )}

            <div className="flex justify-between items-center text-[11px] text-on-surface-variant uppercase tracking-wider font-label-caps font-bold">
              <span>Available Budget</span>
              <span className={`font-mono text-xs font-bold transition-all duration-300 ${
                activeReserveAnimation?.stage === 'RESERVED'
                  ? 'text-amber-700 scale-105'
                  : activeReserveAnimation?.stage === 'RELEASED'
                  ? 'text-emerald-700 scale-105'
                  : 'text-secondary'
              }`}>
                ₹{(livePolicy?.available_budget !== undefined ? livePolicy.available_budget : 20000).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </span>
            </div>
            <div className="w-full bg-surface-container-high rounded-full h-1.5 overflow-hidden border border-outline-variant/20">
              <div
                className={`h-full transition-all duration-500 ${
                  activeReserveAnimation?.stage === 'RESERVED'
                    ? 'bg-amber-500'
                    : activeReserveAnimation?.stage === 'RELEASED'
                    ? 'bg-emerald-500'
                    : 'bg-secondary'
                }`}
                style={{
                  width: `${Math.min(100, Math.round(((livePolicy?.available_budget ?? 20000) / (livePolicy?.daily_spending_limit ?? 20000)) * 100))}%`
                }}
              />
            </div>
            <div className="flex justify-between items-center text-[10px] text-on-surface-variant pt-0.5">
              <span>Per-Tx Ceiling: ₹{(livePolicy?.per_transaction_limit ?? 5000).toLocaleString()}</span>
              {livePolicy?.currently_reserved ? (
                <span className="text-amber-700 font-bold flex items-center gap-1 font-mono">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
                  Hold: ₹{livePolicy.currently_reserved.toLocaleString()} (AUTHORIZED)
                </span>
              ) : (
                <span className="text-outline">0 In-Flight Holds</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Chat Messages Stream */}
      <div className="bento-card p-6 space-y-6 min-h-[360px] max-h-[700px] overflow-y-auto">
        {messages.map((msg) => {
          const isAgent = msg.sender === 'agent';
          const isExpanded = expandedTraceId === msg.id;

          return (
            <div
              key={msg.id}
              className={`flex gap-3.5 ${isAgent ? 'justify-start' : 'justify-end'} animate-fadeIn`}
            >
              {isAgent && (
                <div className="w-10 h-10 rounded-xl bg-primary text-white flex items-center justify-center shrink-0 shadow-sm mt-0.5">
                  <span className="material-symbols-outlined text-[20px]">smart_toy</span>
                </div>
              )}

              <div className={`space-y-3 max-w-2xl ${isAgent ? 'w-full' : ''}`}>
                <div
                  className={`p-5 rounded-2xl text-xs sm:text-sm leading-relaxed border shadow-sm ${
                    isAgent
                      ? 'bg-surface-container-low border-outline-variant/30 text-on-surface'
                      : 'bg-primary text-on-primary border-primary font-medium'
                  }`}
                >
                  <div className="whitespace-pre-wrap font-body-md">
                    {msg.text}
                  </div>

                  {/* Clarification & Interactive Preferences Card */}
                  {msg.clarification && (
                    <InteractiveClarificationCard
                      clarification={msg.clarification}
                      onSelectOption={(selectedPrompt) => handleSend(selectedPrompt)}
                      disabled={loading}
                    />
                  )}

                  {/* Interactive Conversational In-App Checkout Card */}
                  {msg.proposal && !msg.transaction && (
                    <ConversationalCheckoutCard
                      proposal={msg.proposal}
                      onConfirmPurchase={handleConfirmPurchase}
                      onSendFeedback={(feedbackText) => handleSend(feedbackText)}
                      disabled={loading}
                    />
                  )}

                  {/* Receipt Trigger Button */}
                  {msg.transaction?.receipt && (
                    <div className="mt-4 pt-3 border-t border-outline-variant/30 flex items-center justify-between">
                      <div className="text-[11px] font-medium text-on-surface-variant font-mono">
                        Official tax invoice: {msg.transaction.receipt.receipt_number}
                      </div>
                      <button
                        onClick={() => setActiveReceipt(msg.transaction?.receipt)}
                        className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-secondary-container text-on-secondary-container border border-secondary-fixed text-xs font-bold hover:opacity-90 transition-all shadow-sm"
                      >
                        <span className="material-symbols-outlined text-[16px]">receipt_long</span>
                        <span>View Receipt</span>
                      </button>
                    </div>
                  )}

                  {/* Post-Purchase User Feedback & Rating Box */}
                  {msg.transaction && msg.transaction.status === 'RECEIPT_GENERATED' && (
                    <div className="mt-3 p-3.5 rounded-xl bg-surface-container border border-outline-variant/20 space-y-2">
                      <div className="flex items-center justify-between text-xs font-bold text-primary">
                        <span>Rate AI Buyer's Autonomous Execution & Checkout:</span>
                        {msg.feedbackGiven && <span className="text-emerald-700 font-normal text-[11px]">Thank you for your feedback!</span>}
                      </div>
                      {!msg.feedbackGiven ? (
                        <div className="flex items-center gap-1">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <button
                              key={star}
                              type="button"
                              onClick={() => handleFeedbackSubmit(msg.id, star)}
                              className="text-amber-500 hover:scale-125 transition-transform"
                            >
                              <span className="material-symbols-outlined text-[20px]">
                                {(ratings[msg.id] || 0) >= star ? 'star' : 'star_border'}
                              </span>
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  )}
                </div>

                {/* State Machine Visualization & Reserve-Then-Commit Banner */}
                {msg.transaction && (
                  <div className="space-y-3">
                    <StateMachineDiagram currentStatus={msg.transaction.status} />

                    {/* Two-Phase Reserve-Then-Commit Ledger Consequence Card */}
                    {msg.transaction.budget_lifecycle?.has_reservation ? (
                      <div className="rounded-2xl border border-outline-variant/40 bg-surface-container-low p-4 space-y-3 shadow-soft">
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-outline-variant/30 pb-2.5">
                          <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-[20px] text-secondary">account_balance_wallet</span>
                            <div>
                              <h4 className="text-xs font-bold text-primary flex items-center gap-2">
                                <span>Two-Phase Reserve-Then-Commit Lifecycle</span>
                                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border uppercase bg-surface-container font-bold text-outline">
                                  Razorpay Semantics
                                </span>
                              </h4>
                              <p className="text-[11px] text-on-surface-variant">
                                Amount locked against rolling 24h budget on approval; committed on capture or released on failure.
                              </p>
                            </div>
                          </div>

                          <button
                            type="button"
                            onClick={() => triggerConsequenceAnimation(msg.transaction?.budget_lifecycle)}
                            className="text-[11px] px-3 py-1 rounded-full bg-secondary-container text-on-secondary-container border border-secondary-fixed font-bold hover:opacity-90 flex items-center gap-1.5 transition-all shadow-xs"
                          >
                            <span className="material-symbols-outlined text-[14px]">replay</span>
                            <span>Replay Budget Impact</span>
                          </button>
                        </div>

                        {/* Visual 3-Stage Consequence Grid */}
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1 text-xs">
                          {/* Stage 1: Approval Hold */}
                          <div className="p-3 rounded-xl bg-white border border-outline-variant/30 space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-mono font-bold text-amber-800 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                                1. APPROVAL HOLD
                              </span>
                              <span className="text-[10px] font-mono text-outline font-bold">AUTHORIZED</span>
                            </div>
                            <div className="text-primary font-bold text-xs pt-1">
                              Budget Locked: ₹{msg.transaction.budget_lifecycle.reserved_amount.toLocaleString()}
                            </div>
                            <div className="text-[11px] text-on-surface-variant font-mono">
                              Available: ₹{msg.transaction.budget_lifecycle.pre_reserve_available.toLocaleString()} ➔ <span className="text-amber-700 font-bold">₹{(msg.transaction.budget_lifecycle.post_reserve_available ?? (msg.transaction.budget_lifecycle.pre_reserve_available - msg.transaction.budget_lifecycle.reserved_amount)).toLocaleString()}</span>
                            </div>
                            <p className="text-[10px] text-outline pt-0.5">
                              Locked immediately before Razorpay call completes.
                            </p>
                          </div>

                          {/* Stage 2: Gateway Execution */}
                          <div className="p-3 rounded-xl bg-white border border-outline-variant/30 space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-mono font-bold text-secondary bg-secondary-container/30 px-1.5 py-0.5 rounded border border-secondary-fixed">
                                2. RAZORPAY RAILS
                              </span>
                              <span className="text-[10px] font-mono text-outline font-bold">GATEWAY</span>
                            </div>
                            <div className="text-primary font-bold text-xs pt-1">
                              {msg.transaction.budget_lifecycle.is_released ? 'Bank Declined Card' : 'Payment Captured'}
                            </div>
                            <div className="text-[11px] text-on-surface-variant font-mono">
                              {msg.transaction.budget_lifecycle.is_released ? (
                                <span className="text-error font-bold">Simulated Card Decline Error</span>
                              ) : (
                                <span className="text-emerald-700 font-bold">Authorized & Captured</span>
                              )}
                            </div>
                            <p className="text-[10px] text-outline pt-0.5">
                              Synchronous gateway verification & response.
                            </p>
                          </div>

                          {/* Stage 3: Outcome Reconciliation */}
                          <div className={`p-3 rounded-xl border space-y-1 ${
                            msg.transaction.budget_lifecycle.is_released
                              ? 'bg-emerald-50/60 border-emerald-300'
                              : 'bg-secondary-container/20 border-secondary-fixed'
                          }`}>
                            <div className="flex items-center justify-between">
                              <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border ${
                                msg.transaction.budget_lifecycle.is_released
                                  ? 'text-emerald-900 bg-emerald-100 border-emerald-300'
                                  : 'text-primary bg-surface-container border-outline-variant/40'
                              }`}>
                                {msg.transaction.budget_lifecycle.is_released ? '3. AUTO-RELEASE' : '3. PERMANENT COMMIT'}
                              </span>
                              <span className="text-[10px] font-mono font-bold text-primary">
                                {msg.transaction.budget_lifecycle.is_released ? 'RELEASED' : 'CAPTURED'}
                              </span>
                            </div>
                            <div className="text-primary font-bold text-xs pt-1">
                              {msg.transaction.budget_lifecycle.is_released
                                ? `Restored: +₹${msg.transaction.budget_lifecycle.reserved_amount.toLocaleString()}`
                                : `Committed: ₹${msg.transaction.budget_lifecycle.reserved_amount.toLocaleString()}`}
                            </div>
                            <div className="text-[11px] text-on-surface-variant font-mono">
                              Available: <span className="text-secondary font-bold">₹{msg.transaction.budget_lifecycle.final_available.toLocaleString()}</span>
                            </div>
                            <p className="text-[10px] font-bold text-emerald-800 pt-0.5">
                              {msg.transaction.budget_lifecycle.is_released ? '✓ Zero funds leaked / debited' : '✓ 24h spend ledger updated'}
                            </p>
                          </div>
                        </div>
                      </div>
                    ) : (
                      msg.transaction.budget_summary && (
                        <div className="p-3.5 rounded-xl bg-surface-container-low border border-outline-variant/30 flex flex-wrap items-center justify-between text-xs gap-3">
                          <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-[18px] text-secondary">account_balance_wallet</span>
                            <span className="font-bold text-primary font-body-sm">Two-Phase Budget Impact:</span>
                          </div>
                          <div className="flex items-center gap-3 font-mono text-[11px]">
                            <span className="text-on-surface-variant">Limit: <strong>₹{msg.transaction.budget_summary.daily_spending_limit.toLocaleString()}</strong></span>
                            <span className="text-on-surface-variant">Committed: <strong>₹{msg.transaction.budget_summary.spent_today.toLocaleString()}</strong></span>
                            {msg.transaction.budget_summary.currently_reserved > 0 && (
                              <span className="text-amber-600 font-bold flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
                                Active Reserve: ₹{msg.transaction.budget_summary.currently_reserved.toLocaleString()} (AUTHORIZED)
                              </span>
                            )}
                            <span className="text-secondary font-bold">
                              Available: ₹{msg.transaction.budget_summary.available_budget.toLocaleString()}
                            </span>
                          </div>
                        </div>
                      )
                    )}
                  </div>
                )}

                {/* Step-by-Step AI Buyer Agent Tool Calling Trace Drawer */}
                {msg.steps && msg.steps.length > 0 && (
                  <div className="bento-card rounded-2xl overflow-hidden p-0 mt-3">
                    <button
                      onClick={() => setExpandedTraceId(isExpanded ? null : msg.id)}
                      className="w-full px-5 py-3 bg-surface-container-low hover:bg-surface-container flex items-center justify-between text-xs font-bold text-on-surface transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-secondary text-[18px]">terminal</span>
                        <span>AI Buyer Agent Tool Calling Execution Pipeline ({msg.steps.length} tool calls / stages)</span>
                      </div>
                      <span className="material-symbols-outlined text-[18px]">
                        {isExpanded ? 'expand_less' : 'expand_more'}
                      </span>
                    </button>

                    {isExpanded && (
                      <div className="p-4 space-y-3 bg-surface-container-lowest border-t border-outline-variant/20 text-xs font-mono">
                        {msg.steps.map((step, sIdx) => {
                          let badgeBg = 'bg-surface-container-high text-primary border-outline-variant/30';
                          let agentLabel = step.step;

                          if (step.step === 'TOOL_CALL') {
                            if (step.tool === 'search_products') {
                              badgeBg = 'bg-amber-50 text-amber-900 border-amber-300';
                              agentLabel = '🔍 Tool Call: search_products';
                            } else if (step.tool === 'get_quote') {
                              badgeBg = 'bg-purple-50 text-purple-900 border-purple-300';
                              agentLabel = '📊 Tool Call: get_quote';
                            } else if (step.tool === 'create_purchase_intent') {
                              badgeBg = 'bg-emerald-50 text-emerald-900 border-emerald-300';
                              agentLabel = '💳 Tool Call: create_purchase_intent';
                            } else if (step.tool === 'get_receipt') {
                              badgeBg = 'bg-teal-50 text-teal-900 border-teal-300';
                              agentLabel = '🧾 Tool Call: get_receipt';
                            } else if (step.tool === 'get_transaction_status') {
                              badgeBg = 'bg-blue-50 text-blue-900 border-blue-300';
                              agentLabel = '📡 Tool Call: get_transaction_status';
                            } else {
                              badgeBg = 'bg-blue-50 text-blue-900 border-blue-300';
                              agentLabel = `🔧 Tool Call: ${step.tool}`;
                            }
                          } else if (step.step === 'CLARIFICATION_REQUIRED' || step.step === 'HUMAN_IN_THE_LOOP') {
                            badgeBg = 'bg-indigo-50 text-indigo-900 border-indigo-300';
                            agentLabel = '🤝 Human-In-The-Loop Clarification';
                          } else if (step.step === 'GATEWAY_EVALUATION' || step.step === 'GATEWAY_RESPONSE') {
                            badgeBg = 'bg-slate-100 text-slate-900 border-slate-300';
                            agentLabel = '🛡️ AgentPay Policy & Rails Gateway';
                          } else if (step.step === 'INTENT_AGENT') {
                            badgeBg = 'bg-blue-50 text-blue-800 border-blue-200';
                            agentLabel = '🎯 Intent Analysis';
                          } else if (step.step === 'PRODUCT_AGENT') {
                            badgeBg = 'bg-amber-50 text-amber-800 border-amber-200';
                            agentLabel = '🔍 Catalog Discovery';
                          } else if (step.step === 'NEGOTIATION_AGENT') {
                            badgeBg = 'bg-purple-50 text-purple-800 border-purple-200';
                            agentLabel = '🤝 Quote Comparison';
                          } else if (step.step === 'PAYMENT_AGENT') {
                            badgeBg = 'bg-emerald-50 text-emerald-800 border-emerald-200';
                            agentLabel = '💳 Payment Intent';
                          }

                          return (
                            <div key={sIdx} className="p-3 rounded-xl bg-surface-container border border-outline-variant/30 space-y-1.5">
                              <div className="flex items-center justify-between text-[11px]">
                                <span className={`px-2 py-0.5 rounded-full border text-[10px] font-bold ${badgeBg}`}>
                                  {agentLabel}
                                </span>
                                <span className="text-outline text-[10px]">Stage {sIdx + 1}</span>
                              </div>
                              {step.thought && (
                                <div className="text-[11px] text-on-surface-variant font-sans italic pt-1">
                                  "{step.thought}"
                                </div>
                              )}
                              {step.arguments && (
                                <pre className="text-[10px] bg-white p-2.5 rounded-lg border border-outline-variant/30 text-primary overflow-x-auto">
                                  {JSON.stringify(step.arguments, null, 2)}
                                </pre>
                              )}
                              {step.output && (
                                <pre className="text-[10px] bg-white p-2.5 rounded-lg border border-outline-variant/30 text-emerald-900 overflow-x-auto">
                                  {JSON.stringify(step.output, null, 2)}
                                </pre>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {!isAgent && (
                <div className="w-10 h-10 rounded-xl bg-surface-container-high border border-outline-variant/30 flex items-center justify-center shrink-0 shadow-sm mt-0.5 text-primary">
                  <span className="material-symbols-outlined text-[20px]">person</span>
                </div>
              )}
            </div>
          );
        })}

        {loading && (
          <div className="flex items-center gap-3 text-xs text-on-surface-variant pl-2 animate-fadeIn">
            <div className="relative w-6 h-6 flex items-center justify-center">
              <div className="absolute inset-0 bg-secondary rounded-full pulse-ring"></div>
              <div className="w-2.5 h-2.5 bg-secondary rounded-full"></div>
            </div>
            <span className="font-bold">AI Buyer Agent is analyzing intent, searching 50+ SKUs & executing tool calls...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Conversational Input Bar */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="bento-card p-2 rounded-full flex items-center gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Instruct AI Buyer, specify preferences, or ask clarifying options..."
          disabled={loading}
          className="flex-1 bg-transparent px-6 py-2.5 text-body-sm text-on-surface placeholder:text-outline focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-6 py-3 rounded-full bg-secondary text-on-secondary font-label-caps text-label-caps disabled:opacity-40 transition-all shadow-sm flex items-center gap-1.5 shrink-0 hover:opacity-90 font-bold"
        >
          <span>Send Intent</span>
          <span className="material-symbols-outlined text-[16px]">send</span>
        </button>
      </form>

      {/* Receipt Modal */}
      <ReceiptModal receipt={activeReceipt} onClose={() => setActiveReceipt(null)} />
    </div>
  );
}
