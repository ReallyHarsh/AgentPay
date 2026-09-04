import React from 'react';
import { OrganicBrainLogo } from './Logo';

interface Props {
  receipt: {
    id: string;
    receipt_number: string;
    amount: number;
    currency: string;
    details?: Record<string, any>;
  } | null;
  onClose: () => void;
}

export const ReceiptModal: React.FC<Props> = ({ receipt, onClose }) => {
  if (!receipt) return null;

  const details = receipt.details || {};
  const formattedDate = details.issued_at 
    ? new Date(details.issued_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  const productName = details.product_name || 'Autonomous Agent SKU';
  const amountNum = receipt.amount || 0;
  const basePrice = Math.max(0, amountNum * 0.85);
  const taxPrice = amountNum * 0.15;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-charcoal/50 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-[580px] my-auto">
        {/* Back Action Bar */}
        <div className="mb-3 flex justify-between items-center">
          <button
            onClick={onClose}
            className="inline-flex items-center gap-2 text-on-surface-variant font-label-md text-label-md hover:text-primary transition-colors bg-surface-container-lowest px-3 py-1.5 rounded-lg border border-outline-variant shadow-sm"
          >
            <span className="material-symbols-outlined text-[18px]">arrow_back</span>
            Back to Dashboard
          </button>
          <button
            onClick={onClose}
            className="text-on-surface-variant hover:text-primary p-1 rounded-full hover:bg-surface-container-high transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Receipt Physical Paper Card */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden relative shadow-[0_4px_16px_rgba(45,62,80,0.12)]">
          {/* Header Section */}
          <div className="p-6 bg-surface-container-lowest">
            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="inline-flex items-center gap-1.5 bg-secondary-container text-on-secondary-container px-2.5 py-1 rounded-full font-label-sm text-label-sm uppercase tracking-wider mb-2.5 border border-secondary-fixed-dim">
                  <span className="material-symbols-outlined text-[14px]">check_circle</span>
                  Completed & Verified
                </div>
                <h2 className="font-headline-md text-headline-md text-on-surface font-bold">{productName}</h2>
                <p className="font-body-sm text-body-sm text-on-surface-variant mt-0.5">
                  Merchant: {details.merchant_name || 'OmniTech India Electronics'}
                </p>
              </div>
              <div className="w-12 h-12 rounded-lg bg-primary-container text-white flex items-center justify-center border border-outline-variant shadow-sm shrink-0">
                <OrganicBrainLogo size={28} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mt-6 border-t border-dashed border-outline-variant pt-4">
              <div>
                <p className="font-label-sm text-label-sm text-on-surface-variant uppercase">Date</p>
                <p className="font-body-md text-body-md text-on-surface mt-0.5 font-semibold">{formattedDate}</p>
              </div>
              <div>
                <p className="font-label-sm text-label-sm text-on-surface-variant uppercase">Receipt No.</p>
                <p className="font-body-md text-body-md text-on-surface mt-0.5 font-mono font-bold text-primary">
                  {receipt.receipt_number}
                </p>
              </div>
            </div>
          </div>

          {/* Tear Separator */}
          <div className="receipt-tear"></div>

          {/* Body Section */}
          <div className="p-6 bg-surface-container-lowest">
            {/* Line Items */}
            <div className="mb-6">
              <h3 className="font-label-md text-label-md text-on-surface-variant uppercase mb-3 tracking-wider border-b border-outline-variant pb-2">
                Purchase Details
              </h3>
              <div className="flex justify-between items-center py-2.5 border-b border-outline-variant/50">
                <div>
                  <p className="font-body-md text-body-md text-on-surface font-medium">{productName}</p>
                  <p className="font-body-sm text-body-sm text-on-surface-variant">Autonomous AI Procurement License</p>
                </div>
                <p className="font-body-md text-body-md text-on-surface font-mono font-semibold">
                  ₹{basePrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className="flex justify-between items-center py-2.5 border-b border-outline-variant/50">
                <div>
                  <p className="font-body-md text-body-md text-on-surface font-medium">GST & Policy Processing</p>
                  <p className="font-body-sm text-body-sm text-on-surface-variant">Deterministic Invariant Guard</p>
                </div>
                <p className="font-body-md text-body-md text-on-surface font-mono font-semibold">
                  ₹{taxPrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </p>
              </div>
            </div>

            {/* Totals */}
            <div className="bg-surface-container p-4 rounded-lg mb-6 border border-outline-variant">
              <div className="flex justify-between items-center mb-1.5">
                <p className="font-body-sm text-body-sm text-on-surface-variant">Subtotal</p>
                <p className="font-body-sm text-body-sm text-on-surface-variant font-mono">
                  ₹{basePrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className="flex justify-between items-center mb-3 pb-3 border-b border-outline-variant">
                <p className="font-body-sm text-body-sm text-on-surface-variant">Tax & Settlement Rails</p>
                <p className="font-body-sm text-body-sm text-on-surface-variant font-mono">
                  ₹{taxPrice.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className="flex justify-between items-center">
                <p className="font-headline-sm text-headline-sm text-on-surface font-bold">Total Paid</p>
                <p className="font-headline-sm text-headline-sm text-primary font-bold font-mono">
                  ₹{amountNum.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </p>
              </div>
            </div>

            {/* Projected Impact & Policy Security Invariant */}
            <div>
              <h3 className="font-label-md text-label-md text-on-surface-variant uppercase mb-3 tracking-wider flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[16px] text-primary">bolt</span>
                Institutional Audit Verification
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="border border-outline-variant rounded-lg p-3 bg-surface-container">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="material-symbols-outlined text-primary text-[18px]">verified_user</span>
                    <p className="font-label-sm text-label-sm text-on-surface-variant">Policy Engine</p>
                  </div>
                  <p className="font-headline-sm text-sm text-on-surface font-bold">Approved &lt; ₹5k Limit</p>
                </div>
                <div className="border border-outline-variant rounded-lg p-3 bg-surface-container">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="material-symbols-outlined text-secondary text-[18px]">payments</span>
                    <p className="font-label-sm text-label-sm text-on-surface-variant">Payment Rails</p>
                  </div>
                  <p className="font-headline-sm text-sm text-on-surface font-bold">Razorpay Test Mode</p>
                </div>
              </div>
            </div>
          </div>

          {/* Action Footer */}
          <div className="p-4 border-t border-outline-variant bg-surface-container-lowest flex justify-end gap-3 rounded-b-xl">
            <button
              onClick={() => window.print()}
              className="px-4 py-2 border border-outline-variant text-on-surface font-label-md text-label-md rounded-lg hover:bg-surface-container transition-colors flex items-center gap-2"
            >
              <span className="material-symbols-outlined text-[18px]">print</span>
              Print Receipt
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-primary text-on-primary font-label-md text-label-md rounded-lg hover:bg-primary-container hover:text-on-primary-container transition-colors shadow-sm"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
