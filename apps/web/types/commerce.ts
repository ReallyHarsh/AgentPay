export interface MerchantInfo {
  id: string;
  name: string;
  badge: string;
  network: string;
  account: string;
  sla: string;
  slaAdherence: string;
  rating: number;
  totalOrders: number;
  warranty: string;
  specialties: string[];
  description: string;
  accentColor: string;
}

export interface MerchantQuote {
  merchantId: string;
  merchantName: string;
  price: number;
  currency?: string;
  deliveryEta: string;
  warranty: string;
  inStock?: boolean;
  isBest?: boolean;
  quoteExpiresInSec?: number;
}

export interface CatalogProduct {
  id: string;
  name: string;
  brand: string;
  category: 'accessories' | 'audio' | 'displays' | 'appliances' | 'computing';
  categoryLabel: string;
  price: number;
  rating: number;
  reviewsCount: number;
  inStock: boolean;
  stockCount: number;
  deliveryEta: string;
  warranty: string;
  specs: string[];
  description: string;
  primaryMerchantId: string;
  primaryMerchantName: string;
  policyCap: number;
  merchantQuotes: MerchantQuote[];
}

export interface ProductOption {
  id: string;
  name: string;
  brand: string;
  price: number;
  rating: number;
  badge: string;
  specsLine: string;
  policyCap: number;
  quotes: MerchantQuote[];
  savingsText: string;
}

export interface PurchaseStory {
  query: string;
  queryTime: string;
  candidateProducts: ProductOption[];
  selectedProductId: string;
  productName: string;
  specsLine: string;
  quotes: MerchantQuote[];
  savingsText: string;
  policyVerdict: {
    passed: boolean;
    ruleSummary: string;
    details: string;
  };
  chosenQuote: MerchantQuote;
  authPrice: number;
  settlementState: 'idle' | 'authorizing' | 'holding' | 'order_created' | 'settled' | 'failed';
  settlementDetails?: {
    receiptId: string;
    razorpayPaymentId: string;
    idempotencyKey: string;
    settledAt: string;
  };
}
