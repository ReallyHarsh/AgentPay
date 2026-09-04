import React, { useState } from 'react';
import { Clarification } from '@/lib/api';

interface InteractiveClarificationCardProps {
  clarification: Clarification;
  onSelectOption: (prompt: string) => void;
  disabled?: boolean;
}

export const InteractiveClarificationCard: React.FC<InteractiveClarificationCardProps> = ({
  clarification,
  onSelectOption,
  disabled = false
}) => {
  const [customReply, setCustomReply] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customReply.trim() || disabled) return;
    onSelectOption(customReply.trim());
    setCustomReply('');
  };

  return (
    <div className="mt-4 rounded-2xl bg-surface-container-lowest border border-outline-variant/40 shadow-soft overflow-hidden transition-all duration-300">
      {/* Top Banner: Clarification Loop */}
      <div className="bg-primary px-5 py-3 text-white flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[20px] text-secondary">help_outline</span>
          <span className="font-bold text-xs font-label-caps tracking-wider uppercase">
            Human-In-The-Loop: Preferences & Clarification
          </span>
        </div>
        <span className="text-[10px] bg-surface-container-high/20 px-2.5 py-0.5 rounded-full border border-white/20 font-mono">
          Agent Waiting
        </span>
      </div>

      {/* Main Question & Option Pills */}
      <div className="p-5 space-y-4 text-primary">
        <div>
          <div className="text-[11px] font-bold font-label-caps text-outline uppercase mb-1">
            Clarifying Question
          </div>
          <h4 className="font-bold text-sm sm:text-base leading-snug text-primary">
            {clarification.question}
          </h4>
        </div>

        {/* Clickable Option Pills */}
        <div className="space-y-2">
          <div className="text-[10px] font-bold font-label-caps text-outline uppercase">
            Select Your Preferred Option:
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {clarification.options.map((opt, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onSelectOption(opt.prompt)}
                disabled={disabled}
                className="p-3 rounded-xl text-left bg-surface-container hover:bg-surface-container-high border border-outline-variant/30 text-on-surface hover:border-secondary transition-all flex items-center justify-between group active:scale-[0.99]"
              >
                <span className="font-bold text-xs group-hover:text-secondary transition-colors">
                  {opt.label}
                </span>
                <span className="material-symbols-outlined text-[16px] text-outline group-hover:text-secondary transition-transform group-hover:translate-x-0.5">
                  arrow_forward
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Custom Answer Input */}
        <form onSubmit={handleSubmit} className="pt-2 border-t border-outline-variant/20 flex gap-2">
          <input
            type="text"
            value={customReply}
            onChange={(e) => setCustomReply(e.target.value)}
            placeholder="Or type custom preferences (e.g., 'Under ₹10,000 with 30h battery')..."
            disabled={disabled}
            className="flex-1 bg-surface-container-low px-4 py-2 rounded-xl border border-outline-variant/30 text-xs text-primary focus:outline-none focus:ring-1 focus:ring-secondary"
          />
          <button
            type="submit"
            disabled={disabled || !customReply.trim()}
            className="px-4 py-2 rounded-xl bg-secondary text-on-secondary text-xs font-bold font-label-caps hover:opacity-90 disabled:opacity-40 transition-opacity flex items-center gap-1"
          >
            <span>Submit</span>
            <span className="material-symbols-outlined text-[14px]">send</span>
          </button>
        </form>
      </div>
    </div>
  );
};
