const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

export interface Product {
  id: string;
  merchant_id: string;
  merchant_name?: string;
  name: string;
  brand?: string;
  description: string;
  category: string;
  price: number;
  currency: string;
  stock: number;
  rating?: number;
  specs?: Record<string, any>;
  in_stock: boolean;
}

export interface AuditEvent {
  id: string;
  event_type: string;
  actor_type: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface Transaction {
  id: string;
  status: string;
  created_at: string;
  updated_at: string;
  purchase_intent?: {
    id: string;
    agent_id: string;
    merchant_id: string;
    product_id: string;
    amount: number;
    currency: string;
    status: string;
  };
  payment_intent_id?: string;
  payment_intent?: {
    id: string;
    status: string;
    provider: string;
    provider_payment_id?: string;
    amount: number;
    currency: string;
    reserved_at?: string;
    committed_at?: string;
    released_at?: string;
  };
  budget_summary?: {
    per_transaction_limit: number;
    daily_spending_limit: number;
    spent_today: number;
    currently_reserved: number;
    available_budget: number;
    currency: string;
  };
  budget_lifecycle?: {
    has_reservation: boolean;
    lifecycle_stage: string;
    reserved_amount: number;
    pre_reserve_available: number;
    post_reserve_available?: number;
    final_available: number;
    currently_reserved: number;
    net_debited: number;
    is_committed: boolean;
    is_released: boolean;
    events: Array<{
      event_type: string;
      lifecycle_stage?: string;
      amount?: number;
      available_budget?: number;
      currently_reserved?: number;
      spent_today?: number;
      note?: string;
      created_at?: string;
    }>;
  };
  policy_result?: {
    approved: boolean;
    code: string;
    reason: string;
    limit: number;
    requested_amount: number;
    currency: string;
    daily_limit?: number;
    spent_today?: number;
    currently_reserved?: number;
    available_budget?: number;
  };
  receipt?: {
    id: string;
    receipt_number: string;
    amount: number;
    currency: string;
    details: Record<string, any>;
  };
  audit_events: AuditEvent[];
}

export interface BudgetLifecycle {
  has_reservation: boolean;
  lifecycle_stage: string;
  reserved_amount: number;
  pre_reserve_available: number;
  post_reserve_available?: number;
  final_available: number;
  currently_reserved: number;
  net_debited: number;
  is_committed: boolean;
  is_released: boolean;
  events: Array<{
    event_type: string;
    lifecycle_stage?: string;
    amount?: number;
    available_budget?: number;
    currently_reserved?: number;
    spent_today?: number;
    note?: string;
    created_at?: string;
  }>;
}

export interface AgentPolicy {
  id: string;
  agent_id: string;
  currency: string;
  per_transaction_limit: number;
  daily_spending_limit?: number;
  spent_today?: number;
  currently_reserved?: number;
  available_budget?: number;
  allowed_categories: string[];
  blocked_merchants: string[];
}

export interface Clarification {
  question: string;
  options: Array<{
    label: string;
    prompt: string;
  }>;
}

export interface TieredOption {
  tier: string;
  product_id: string;
  name: string;
  price: number;
  merchant_id: string;
  merchant_name: string;
  badge: string;
}

export interface CheckoutProposal {
  product_id: string;
  name: string;
  brand?: string;
  category?: string;
  price: number;
  currency?: string;
  rating?: number;
  merchant_id: string;
  merchant_name: string;
  specs?: Record<string, any>;
  comparison?: Array<{
    product_id: string;
    merchant_id: string;
    merchant_name: string;
    name: string;
    total_amount: number;
    in_stock: boolean;
    specs?: Record<string, any>;
  }>;
  tiered_options?: TieredOption[];
  rationale?: string;
  eligible_for_instant_checkout: boolean;
  policy_limit?: number;
}

export interface ChatResponse {
  response: string;
  steps: Array<{
    step: string;
    tool?: string;
    arguments?: Record<string, any>;
    thought?: string;
    output?: any;
  }>;
  clarification?: Clarification;
  proposal?: CheckoutProposal;
  transaction?: Transaction;
}

export async function fetchProducts(query?: string, limit: number = 250): Promise<Product[]> {
  const url = new URL(`${API_BASE}/products`);
  if (query) url.searchParams.append('query', query);
  if (limit) url.searchParams.append('limit', String(limit));
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('Failed to fetch products');
  return res.json();
}

export async function fetchTransactions(): Promise<Transaction[]> {
  const res = await fetch(`${API_BASE}/transactions`);
  if (!res.ok) throw new Error('Failed to fetch transactions');
  return res.json();
}

export async function fetchTransaction(id: string): Promise<Transaction> {
  const res = await fetch(`${API_BASE}/transactions/${id}`);
  if (!res.ok) throw new Error('Failed to fetch transaction');
  return res.json();
}

export async function fetchAgentPolicy(agentId: string = 'agent_001'): Promise<AgentPolicy> {
  const res = await fetch(`${API_BASE}/agents/${agentId}/policy`);
  if (!res.ok) throw new Error('Failed to fetch policy');
  return res.json();
}

export async function updateAgentPolicy(agentId: string, payload: Partial<AgentPolicy>): Promise<any> {
  const res = await fetch(`${API_BASE}/agents/${agentId}/policy`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to update policy');
  return res.json();
}

export async function sendChatMessage(message: string, agentId: string = 'agent_001'): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, agent_id: agentId }),
  });
  if (!res.ok) throw new Error('Failed to send message');
  return res.json();
}

export async function reservePurchaseIntent(payload: {
  agent_id?: string;
  merchant_id: string;
  product_id: string;
  amount: number;
  currency?: string;
  idempotency_key?: string;
}): Promise<Transaction> {
  const res = await fetch(`${API_BASE}/purchase-intents/reserve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      agent_id: payload.agent_id || 'agent_001',
      merchant_id: payload.merchant_id,
      product_id: payload.product_id,
      amount: payload.amount,
      currency: payload.currency || 'INR',
      idempotency_key: payload.idempotency_key
    }),
  });
  if (!res.ok) throw new Error('Failed to reserve purchase intent');
  return res.json();
}

export async function finalizeTransaction(transactionId: string, simulateFailure: boolean = false): Promise<Transaction> {
  const res = await fetch(`${API_BASE}/transactions/${transactionId}/finalize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ simulate_failure: simulateFailure }),
  });
  if (!res.ok) throw new Error('Failed to finalize transaction');
  return res.json();
}

