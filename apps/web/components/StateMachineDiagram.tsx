import React from 'react';

interface Props {
  currentStatus: string;
}

export const StateMachineDiagram: React.FC<Props> = ({ currentStatus }) => {
  const isDenied = currentStatus === 'DENIED';
  const isFailed = currentStatus === 'PAYMENT_FAILED';

  const stages = [
    { key: 'CREATED', label: 'Intent Created', icon: 'schedule', sub: 'CREATED' },
    { key: 'POLICY_CHECKED', label: 'Policy Checked', icon: 'verified_user', sub: 'CHECKED' },
    { 
      key: isDenied ? 'DENIED' : 'APPROVED', 
      label: isDenied ? 'Policy Denied' : 'Approved (Hold)', 
      sub: isDenied ? 'DENIED' : 'AUTHORIZED',
      icon: isDenied ? 'cancel' : 'lock_clock' 
    },
    { key: 'PAYMENT_CREATED', label: 'Rails Auth', icon: 'credit_card', sub: 'IN_FLIGHT', skipIfDenied: true },
    { 
      key: isFailed ? 'PAYMENT_FAILED' : 'PAYMENT_SUCCESS', 
      label: isFailed ? 'Decline (Release)' : 'Capture (Commit)', 
      sub: isFailed ? 'RELEASED' : 'CAPTURED',
      icon: isFailed ? 'replay' : 'payments', 
      skipIfDenied: true 
    },
    { key: 'ORDER_CONFIRMED', label: 'Order Booked', icon: 'inventory_2', sub: 'CONFIRMED', skipIfDenied: true, skipIfFailed: true },
    { key: 'RECEIPT_GENERATED', label: 'Receipt Issued', icon: 'receipt_long', sub: 'SETTLED', skipIfDenied: true, skipIfFailed: true },
  ];

  const statusOrder = [
    'CREATED',
    'POLICY_CHECKED',
    isDenied ? 'DENIED' : 'APPROVED',
    'PAYMENT_CREATED',
    isFailed ? 'PAYMENT_FAILED' : 'PAYMENT_SUCCESS',
    'ORDER_CONFIRMED',
    'RECEIPT_GENERATED'
  ];

  const currentIndex = statusOrder.indexOf(currentStatus);

  return (
    <div className="w-full bento-card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
          State Machine Progression
        </h3>
        <span className={`text-xs font-label-caps px-3 py-1 rounded-full border font-bold uppercase ${
          isDenied 
            ? 'bg-error-container text-on-error-container border-error' 
            : isFailed
            ? 'bg-amber-100 text-amber-900 border-amber-400'
            : currentStatus === 'RECEIPT_GENERATED' 
            ? 'bg-secondary-container text-on-secondary-container border-secondary-fixed' 
            : 'bg-surface-container-high text-primary border-outline-variant/30'
        }`}>
          {isFailed ? 'PAYMENT_FAILED (RESERVATION RELEASED)' : currentStatus}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
        {stages.map((stage, idx) => {
          const isPassed = !isDenied && (isFailed ? idx <= 4 && currentIndex >= idx : currentIndex >= idx);
          const isCurrent = currentStatus === stage.key;
          const isBlocked = (isDenied && idx >= 2) || (isFailed && idx >= 5);

          let colorClasses = 'bg-surface-container-low border-outline-variant/20 text-on-surface-variant';
          if (isCurrent && isDenied) {
            colorClasses = 'bg-error-container border-error text-on-error-container font-bold';
          } else if (isCurrent && isFailed) {
            colorClasses = 'bg-amber-100 border-amber-400 text-amber-900 font-bold';
          } else if (isCurrent) {
            colorClasses = 'bg-secondary-container border-secondary text-on-secondary-container font-bold';
          } else if (isPassed) {
            colorClasses = 'bg-secondary-fixed/50 border-secondary-fixed text-on-secondary-fixed font-semibold';
          } else if (isBlocked) {
            colorClasses = 'bg-surface-container-highest/40 border-transparent text-outline opacity-40 line-through';
          }

          return (
            <div
              key={stage.key}
              className={`p-3 rounded-2xl border flex flex-col items-center text-center transition-all ${colorClasses}`}
            >
              <div className="p-2 rounded-xl bg-white shadow-sm mb-2 text-primary">
                <span className="material-symbols-outlined text-[16px]">{stage.icon}</span>
              </div>
              <span className="font-body-sm text-[12px] leading-tight font-bold">{stage.label}</span>
              <span className="font-label-caps text-[9px] opacity-75 mt-1 font-mono">{stage.sub || stage.key}</span>
            </div>
          );
        })}
      </div>

      {isDenied && (
        <div className="mt-4 p-3.5 rounded-xl bg-error-container border border-error text-on-error-container flex items-start gap-2.5">
          <span className="material-symbols-outlined text-[18px] text-error shrink-0 mt-0.5">error</span>
          <div className="font-body-sm text-xs text-on-error-container">
            <span className="font-bold">Deterministic Security Guarantee: </span>
            Policy engine rejected purchase intent. State machine terminated before payment rails were accessed.
          </div>
        </div>
      )}

      {isFailed && (
        <div className="mt-4 p-3.5 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 flex items-start gap-2.5">
          <span className="material-symbols-outlined text-[18px] text-amber-600 shrink-0 mt-0.5">published_with_changes</span>
          <div className="font-body-sm text-xs text-amber-900">
            <span className="font-bold">Graceful Failure & Reserve-Then-Commit Invariant: </span>
            Payment was declined by the bank rail. The active budget reservation was <strong>automatically voided and released</strong>, restoring your full available daily limit.
          </div>
        </div>
      )}
    </div>
  );
};
