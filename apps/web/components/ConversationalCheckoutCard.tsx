import React, { useState } from 'react';
import { CheckoutProposal } from '@/lib/api';

interface ConversationalCheckoutCardProps {
  proposal: CheckoutProposal;
  onConfirmPurchase: (productId: string, merchantId: string, amount: number) => void;
  onSendFeedback: (feedbackText: string) => void;
  disabled?: boolean;
}

export const ConversationalCheckoutCard: React.FC<ConversationalCheckoutCardProps> = ({
  proposal,
  onConfirmPurchase,
  onSendFeedback,
  disabled = false
}) => {
  const [selectedMerchantId, setSelectedMerchantId] = useState<string>(proposal.merchant_id);
  const [selectedPrice, setSelectedPrice] = useState<number>(proposal.price);
  const [selectedMerchantName, setSelectedMerchantName] = useState<string>(proposal.merchant_name);
  const [deliveryOption, setDeliveryOption] = useState<'standard' | 'express'>('standard');
  const [opinionText, setOpinionText] = useState('');
  const [isOpinionExpanded, setIsOpinionExpanded] = useState(false);

  const isOverLimit = selectedPrice > (proposal.policy_limit || 5000.0);
  const isEligible = !isOverLimit;

  const handleMerchantChange = (item: any) => {
    setSelectedMerchantId(item.merchant_id);
    setSelectedPrice(item.total_amount);
    setSelectedMerchantName(item.merchant_name || item.merchant_id);
  };

  const handleConfirm = () => {
    onConfirmPurchase(proposal.product_id, selectedMerchantId, selectedPrice);
  };

  const handleOpinionSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!opinionText.trim() || disabled) return;
    onSendFeedback(opinionText.trim());
    setOpinionText('');
  };

  const quickOpinions = [
    { label: "💰 Find cheaper alternative", text: `Find a cheaper alternative to ${proposal.name} under ₹${Math.round(selectedPrice * 0.8)}` },
    { label: "⭐ Show flagship options", text: `Show only top rated flagship items with highest reviews for ${proposal.category || 'this'}` },
    { label: "🔋 Max battery life", text: `Find the model with the longest battery life for ${proposal.name}` },
    { label: "🏢 Switch merchant", text: selectedMerchantId === 'merchant_001' ? 'Show quote from Reliance Digital' : 'Show quote from Croma' }
  ];

  return (
    <div className="mt-4 rounded-2xl bg-surface-container-lowest border border-outline-variant/40 shadow-soft overflow-hidden transition-all duration-300">
      {/* Top Banner: In-App Checkout Header */}
      <div className="bg-primary px-5 py-3 text-white flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[20px] text-secondary">shopping_bag</span>
          <span className="font-bold text-xs font-label-caps tracking-wider uppercase">
            Conversational In-App Checkout Proposal
          </span>
        </div>
        <span className="text-[10px] bg-surface-container-high/20 px-2.5 py-0.5 rounded-full border border-white/20 font-mono">
          Human-in-the-Loop
        </span>
      </div>

      {/* Main Content Area */}
      <div className="p-5 space-y-4 text-primary">
        {/* Product Title & Brand */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-3 border-b border-outline-variant/20">
          <div>
            <div className="flex items-center gap-2 mb-1">
              {proposal.brand && (
                <span className="text-[10px] font-bold font-label-caps px-2 py-0.5 rounded bg-surface-container text-primary uppercase">
                  {proposal.brand}
                </span>
              )}
              <span className="text-xs font-bold text-amber-600 flex items-center gap-0.5">
                <span className="material-symbols-outlined text-[13px]">star</span>
                {proposal.rating || 4.8} / 5.0
              </span>
            </div>
            <h4 className="font-bold text-sm sm:text-base leading-snug">{proposal.name}</h4>
          </div>

          <div className="text-left sm:text-right shrink-0">
            <div className="text-[10px] uppercase font-label-caps text-outline font-bold">Lock-In Price</div>
            <div className="font-mono text-xl font-bold text-secondary">
              ₹{selectedPrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
          </div>
        </div>

        {/* Multi-Merchant Selector (if comparison available) */}
        {proposal.comparison && proposal.comparison.length > 1 && (
          <div className="space-y-1.5 p-3 rounded-xl bg-surface-container-low border border-outline-variant/30">
            <div className="text-[10px] font-label-caps uppercase text-outline font-bold flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[14px] text-secondary">storefront</span>
              <span>Select Participating Merchant:</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
              {proposal.comparison.map((comp, idx) => {
                const isSelected = selectedMerchantId === comp.merchant_id;
                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleMerchantChange(comp)}
                    disabled={disabled}
                    className={`px-3 py-2 rounded-xl text-left border flex items-center justify-between transition-all ${
                      isSelected
                        ? 'bg-white border-secondary shadow-sm ring-1 ring-secondary'
                        : 'bg-surface-container hover:bg-surface-container-high border-outline-variant/30 text-on-surface-variant'
                    }`}
                  >
                    <div>
                      <div className="font-bold text-xs flex items-center gap-1">
                        <span>{comp.merchant_name || comp.merchant_id}</span>
                        {isSelected && <span className="text-[10px] text-secondary font-bold">✓</span>}
                      </div>
                      <div className="text-[10px] text-outline">Verified Stock Available</div>
                    </div>
                    <div className="font-mono font-bold text-xs">
                      ₹{comp.total_amount.toLocaleString('en-IN')}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Tiered Options / Alternative Choices */}
        {proposal.tiered_options && proposal.tiered_options.length > 0 && (
          <div className="space-y-1.5 p-3 rounded-xl bg-surface-container-low border border-outline-variant/30">
            <div className="text-[10px] font-label-caps uppercase text-outline font-bold flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[14px] text-secondary">alt_route</span>
              <span>Compare Price & Feature Tiers:</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
              {proposal.tiered_options.map((opt, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onSendFeedback(`Show details for ${opt.name}`)}
                  disabled={disabled}
                  className="p-2.5 rounded-xl text-left bg-white hover:bg-surface-container-high border border-outline-variant/30 text-primary transition-all flex items-center justify-between group shadow-2xs"
                >
                  <div className="overflow-hidden pr-2">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="text-[9px] font-bold font-label-caps px-1.5 py-0.2 rounded bg-surface-container text-primary uppercase">
                        {opt.tier}
                      </span>
                      <span className="text-[9px] text-secondary font-mono font-bold">₹{opt.price.toLocaleString('en-IN')}</span>
                    </div>
                    <div className="text-xs font-bold truncate">{opt.name}</div>
                  </div>
                  <span className="material-symbols-outlined text-[14px] text-outline group-hover:text-secondary shrink-0">arrow_forward</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Specs Highlights */}
        {proposal.specs && Object.keys(proposal.specs).length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(proposal.specs).slice(0, 3).map(([k, v]) => (
              <span
                key={k}
                className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-surface-container-low border border-outline-variant/20 text-on-surface-variant"
              >
                <strong className="text-primary">{k.replace('_', ' ')}:</strong> {Array.isArray(v) ? v.join(', ') : String(v)}
              </span>
            ))}
          </div>
        )}

        {/* Delivery Options */}
        <div className="flex items-center gap-3 text-xs pt-1">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="radio"
              name={`delivery_${proposal.product_id}`}
              checked={deliveryOption === 'standard'}
              onChange={() => setDeliveryOption('standard')}
              className="accent-secondary"
            />
            <span className="font-medium text-xs">Standard Free Delivery (2-3 Days)</span>
          </label>
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input
              type="radio"
              name={`delivery_${proposal.product_id}`}
              checked={deliveryOption === 'express'}
              onChange={() => setDeliveryOption('express')}
              className="accent-secondary"
            />
            <span className="font-medium text-xs">Express Priority (Next Day, +₹99)</span>
          </label>
        </div>

        {/* Policy Guard Check Banner */}
        <div
          className={`p-3 rounded-xl border flex items-center justify-between text-xs ${
            isEligible
              ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
              : 'bg-error-container/30 border-error/40 text-on-error-container'
          }`}
        >
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">
              {isEligible ? 'verified_user' : 'gpp_bad'}
            </span>
            <div>
              <div className="font-bold text-[11px]">
                {isEligible ? 'AgentPay Policy Evaluation: PRE-APPROVED' : 'Policy Ceiling Exceeded'}
              </div>
              <div className="text-[10px] opacity-90">
                {isEligible
                  ? `Amount is within your per-transaction spending limit of ₹${(proposal.policy_limit || 5000).toLocaleString('en-IN')}.`
                  : `Amount exceeds your ₹${(proposal.policy_limit || 5000).toLocaleString('en-IN')} limit. Transaction will be blocked unless authorized by admin.`}
              </div>
            </div>
          </div>
        </div>

        {/* User Opinion & Feedback Section */}
        <div className="border-t border-outline-variant/30 pt-3 space-y-2">
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => setIsOpinionExpanded(!isOpinionExpanded)}
              className="text-[11px] font-bold text-secondary flex items-center gap-1 hover:underline"
            >
              <span className="material-symbols-outlined text-[15px]">rate_review</span>
              <span>Want to give opinion or customize requirements?</span>
              <span className="material-symbols-outlined text-[14px]">
                {isOpinionExpanded ? 'expand_less' : 'expand_more'}
              </span>
            </button>
          </div>

          {/* Quick Opinion Chips */}
          <div className="flex flex-wrap gap-1.5 pt-1">
            {quickOpinions.map((op, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onSendFeedback(op.text)}
                disabled={disabled}
                className="text-[10px] font-bold font-label-caps px-2.5 py-1 rounded-full bg-surface-container hover:bg-surface-container-high border border-outline-variant/30 text-on-surface-variant transition-all"
              >
                {op.label}
              </button>
            ))}
          </div>

          {/* Custom Opinion Form */}
          {isOpinionExpanded && (
            <form onSubmit={handleOpinionSubmit} className="pt-2 flex gap-2">
              <input
                type="text"
                value={opinionText}
                onChange={(e) => setOpinionText(e.target.value)}
                placeholder="Give feedback (e.g., 'I want a different color' or 'Check for 2-year warranty')..."
                disabled={disabled}
                className="flex-1 bg-surface-container-low px-3 py-1.5 rounded-xl border border-outline-variant/30 text-xs text-primary focus:outline-none focus:ring-1 focus:ring-secondary"
              />
              <button
                type="submit"
                disabled={disabled || !opinionText.trim()}
                className="px-3 py-1.5 rounded-xl bg-primary text-white text-xs font-bold hover:opacity-90 disabled:opacity-40 transition-opacity"
              >
                Send
              </button>
            </form>
          )}
        </div>

        {/* Action Button: One-Click AgentPay Checkout */}
        <div className="pt-2">
          <button
            type="button"
            onClick={handleConfirm}
            disabled={disabled}
            className="w-full py-3 rounded-xl bg-secondary text-on-secondary font-bold text-xs sm:text-sm font-label-caps flex items-center justify-center gap-2 hover:opacity-95 transition-all shadow-sm active:scale-[0.99]"
          >
            <span className="material-symbols-outlined text-[18px]">lock</span>
            <span>Authorize & Checkout ₹{selectedPrice.toLocaleString('en-IN')} via AgentPay</span>
            <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
          </button>
        </div>
      </div>
    </div>
  );
};
