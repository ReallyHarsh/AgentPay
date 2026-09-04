import React from 'react';

export type EventStatus = 'pending' | 'running' | 'complete' | 'approval-needed' | 'denied' | 'settlement-failed';

export interface TimelineEventProps {
  id: string;
  title: string;
  timestamp?: string;
  status: EventStatus;
  isLast?: boolean;
  children: React.ReactNode;
}

export function TimelineEvent({
  id,
  title,
  timestamp,
  status,
  isLast = false,
  children,
}: TimelineEventProps) {
  return (
    <div id={`node-${id}`} className="relative pl-8 sm:pl-10 pb-12 last:pb-0 transition-all">
      {/* 1px Vertical Thread Line */}
      {!isLast && (
        <div
          className="absolute left-[11px] top-4 bottom-0 w-[1px] bg-[#E4E2E2] dark:bg-white/10"
          aria-hidden="true"
        />
      )}

      {/* Node Marker */}
      <div className="absolute left-0 top-1 flex items-center justify-center">
        {status === 'running' && (
          <span className="relative flex h-6 w-6 items-center justify-center">
            <span className="animate-ping absolute inline-flex h-4 w-4 rounded-full bg-[#FE7352] opacity-40"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-[#AA361A]"></span>
          </span>
        )}

        {status === 'complete' && (
          <div className="w-5 h-5 rounded-full bg-[#1B1C1C] dark:bg-white text-white dark:text-[#141212] flex items-center justify-center text-[10px]">
            <svg
              className="w-3 h-3 stroke-white dark:stroke-[#141212] stroke-[2.5]"
              fill="none"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )}

        {status === 'approval-needed' && (
          <div className="w-5 h-5 rounded-full bg-[#AA361A] text-white flex items-center justify-center text-[10px] font-bold">
            !
          </div>
        )}

        {status === 'denied' && (
          <div className="w-5 h-5 rounded-full bg-[#BA1A1A] text-white flex items-center justify-center text-[10px]">
            ✕
          </div>
        )}

        {status === 'settlement-failed' && (
          <div className="w-5 h-5 rounded-full bg-[#BA1A1A] text-white flex items-center justify-center text-[10px]">
            ⚠
          </div>
        )}

        {status === 'pending' && (
          <div className="w-4 h-4 rounded-full border border-[#CFBFC0] dark:border-white/20 bg-[#FBF9F9] dark:bg-[#1A1919] ml-0.5 mt-0.5" />
        )}
      </div>

      {/* Event Header */}
      <div className="flex flex-wrap items-baseline gap-2 sm:gap-3 mb-3">
        <h2 className="text-sm font-semibold tracking-tight text-[#1B1C1C] dark:text-white">
          {title}
        </h2>
        {timestamp && (
          <span className="font-mono text-xs text-[#7E7576] dark:text-[#9E9697]">
            {timestamp}
          </span>
        )}
      </div>

      {/* Event Content Body */}
      <div className="text-sm text-[#1B1C1C] dark:text-[#E2DFDF] leading-relaxed">
        {children}
      </div>
    </div>
  );
}
