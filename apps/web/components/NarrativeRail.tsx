import React from 'react';

export type StageKey = 'ask' | 'explore' | 'compare' | 'guardrail' | 'authorize' | 'receipt';

export interface StageInfo {
  key: StageKey;
  number: string;
  label: string;
  timestamp?: string;
  status: 'inactive' | 'active' | 'completed' | 'blocked';
  detailSnippet?: string;
}

interface NarrativeRailProps {
  currentStage: StageKey;
  stages: StageInfo[];
  onStageClick?: (stageKey: StageKey) => void;
}

export function NarrativeRail({ currentStage, stages, onStageClick }: NarrativeRailProps) {
  return (
    <nav
      aria-label="Commerce Progress Rail"
      className="w-full overflow-x-auto py-3 px-2 border-b border-[#E4E2E2]/70 dark:border-white/10 mb-8 select-none"
    >
      <div className="flex items-center gap-4 sm:gap-6 min-w-max text-xs sm:text-sm">
        <span className="font-semibold text-xs uppercase tracking-wider text-[#1B1C1C] dark:text-white mr-2">
          AgentPay
        </span>

        {stages.map((stage) => {
          const isActive = stage.key === currentStage;
          const isCompleted = stage.status === 'completed';
          const isBlocked = stage.status === 'blocked';
          const isInactive = stage.status === 'inactive';

          return (
            <button
              key={stage.key}
              onClick={() => onStageClick?.(stage.key)}
              disabled={isInactive}
              className={`flex items-center gap-1.5 transition-all text-left ${
                isActive
                  ? 'text-[#AA361A] dark:text-[#FE7352] font-semibold'
                  : isCompleted
                  ? 'text-[#1B1C1C] hover:text-[#AA361A] dark:text-[#F5F3F3] dark:hover:text-[#FE7352]'
                  : isBlocked
                  ? 'text-[#BA1A1A] font-semibold'
                  : 'text-[#9C9495] dark:text-[#7E7576] cursor-default'
              }`}
            >
              {/* Stage Node Icon */}
              <span
                className={`w-2 h-2 rounded-full transition-all ${
                  isActive
                    ? 'bg-[#FE7352] ring-4 ring-[#FE7352]/20 animate-pulse'
                    : isCompleted
                    ? 'bg-[#1B1C1C] dark:bg-white'
                    : isBlocked
                    ? 'bg-[#BA1A1A]'
                    : 'bg-[#CFBFC0] dark:bg-white/20'
                }`}
              />

              <span className="font-mono text-[10px] text-[#7E7576] dark:text-[#9E9697]">
                {stage.number}
              </span>

              <span>{stage.label}</span>

              {stage.timestamp && isCompleted && (
                <span className="font-mono text-[10px] text-[#7E7576] dark:text-[#9E9697] ml-1">
                  [{stage.timestamp}]
                </span>
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
