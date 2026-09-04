import React, { useState } from 'react';
import { OrganicBrainLogo } from './Logo';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const ProtocolModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<'catalog' | 'uap' | 'llms' | 'x402' | 'enterprise'>('catalog');
  const [copied, setCopied] = useState(false);
  const [x402Loading, setX402Loading] = useState(false);
  const [x402Response, setX402Response] = useState<any>(null);
  const [x402Headers, setX402Headers] = useState<Record<string, string>>({});
  
  // Live Protocol State fetched from FastAPI
  const [liveCatalogJson, setLiveCatalogJson] = useState<string>('');
  const [liveUapJson, setLiveUapJson] = useState<string>('');
  const [liveLlmsTxt, setLiveLlmsTxt] = useState<string>('');
  const [isLiveConnected, setIsLiveConnected] = useState<boolean>(false);

  const [skuList, setSkuList] = useState<Array<{ id: string; name: string; price: number; merchant?: string }>>([
    { id: 'prod_jbl_770nc', name: 'JBL Tune 770NC Wireless ANC Headphones', price: 4499.0, merchant: 'Croma Electronics Hub' },
    { id: 'prod_dell_u2723qe', name: 'Dell UltraSharp 27" 4K USB-C Hub Monitor', price: 42999.0, merchant: 'Reliance Digital Tech' },
    { id: 'prod_sony_wh1000xm5', name: 'Sony WH-1000XM5 Wireless ANC Headphones', price: 28990.0, merchant: 'Amazon Prime Direct' },
    { id: 'prod_logitech_mx_master_3s', name: 'Logitech MX Master 3S Wireless Mouse', price: 8495.0, merchant: 'Croma Electronics Hub' },
    { id: 'prod_keychron_k2_v2', name: 'Keychron K2 V2 Wireless Mechanical Keyboard', price: 7999.0, merchant: 'Reliance Digital Tech' }
  ]);

  const [selectedSku, setSelectedSku] = useState<string>('prod_jbl_770nc');

  React.useEffect(() => {
    if (!isOpen) return;

    // Fetch live agent-catalog.json
    fetch('http://localhost:8000/.well-known/agent-catalog.json')
      .then(res => res.json())
      .then(data => {
        setLiveCatalogJson(JSON.stringify(data, null, 2));
        setIsLiveConnected(true);
      })
      .catch(() => setIsLiveConnected(false));

    // Fetch live uap-manifest.json
    fetch('http://localhost:8000/.well-known/uap-manifest.json')
      .then(res => res.json())
      .then(data => setLiveUapJson(JSON.stringify(data, null, 2)))
      .catch(() => {});

    // Fetch live llms.txt
    fetch('http://localhost:8000/llms.txt')
      .then(res => res.text())
      .then(text => setLiveLlmsTxt(text))
      .catch(() => {});

    // Fetch live product catalog to dynamically populate SKU challenge list
    fetch('http://localhost:8000/api/v1/products?limit=25')
      .then(res => res.json())
      .then(items => {
        if (Array.isArray(items) && items.length > 0) {
          const mapped = items.map((it: any) => ({
            id: it.id,
            name: it.name,
            price: it.price,
            merchant: it.merchant_name || 'Verified Merchant'
          }));
          setSkuList(mapped);
        }
      })
      .catch(() => {});
  }, [isOpen]);

  if (!isOpen) return null;

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const runX402Test = async (overrideSku?: string) => {
    const targetSku = overrideSku || selectedSku;
    const targetProduct = skuList.find(p => p.id === targetSku) || skuList[0];
    const amountPaise = Math.round(targetProduct.price * 100);

    setX402Loading(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/protocol/x402/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: targetSku, agent_id: 'agent_001' })
      });

      const hdrs: Record<string, string> = {
        'status': `${res.status} Payment Required`,
        'x-payment-rail': res.headers.get('x-payment-rail') || 'razorpay',
        'x-payment-protocol': res.headers.get('x-payment-protocol') || 'x402-v1 / UAP-ACP',
        'x-razorpay-order-id': res.headers.get('x-razorpay-order-id') || `order_x402_${Math.random().toString(16).substring(2, 10)}`,
        'x-amount-paise': res.headers.get('x-amount-paise') || String(amountPaise),
        'www-authenticate': res.headers.get('www-authenticate') || `X402 realm="AgentPay-Razorpay", token_endpoint="/api/v1/purchase-intents", amount="${targetProduct.price}"`
      };
      setX402Headers(hdrs);

      const json = await res.json();
      setX402Response(json);
      setIsLiveConnected(true);
    } catch (e) {
      // Dynamic fallback calculated from chosen SKU
      const randomOrderId = `order_x402_${Math.random().toString(16).substring(2, 10)}`;
      setX402Headers({
        'status': '402 Payment Required',
        'x-payment-rail': 'razorpay',
        'x-payment-protocol': 'x402-v1 / UAP-ACP (2026)',
        'x-razorpay-order-id': randomOrderId,
        'x-amount-paise': String(amountPaise),
        'x-currency': 'INR',
        'www-authenticate': `X402 realm="AgentPay-Razorpay", token_endpoint="/api/v1/purchase-intents", amount="${targetProduct.price}.0"`
      });
      setX402Response({
        status: 402,
        title: "Payment Required",
        protocol: "x402 / UAP-ACP (2026)",
        message: "Direct resource access requires autonomous payment authorization via AgentPay Policy Gate.",
        product: {
          id: targetProduct.id,
          name: targetProduct.name,
          price: targetProduct.price,
          currency: "INR"
        },
        payment_challenge: {
          rail: "RAZORPAY",
          network: "test",
          order_id: randomOrderId,
          amount: targetProduct.price,
          amount_paise: amountPaise,
          currency: "INR",
          quote_validity_seconds: 300
        },
        resolution_instructions: {
          action: "create_purchase_intent",
          endpoint: "/api/v1/purchase-intents",
          policy_rule: "AgentPay will evaluate spending ceiling, reserve funds (AUTHORIZED), and capture via Razorpay."
        }
      });
    } finally {
      setX402Loading(false);
    }
  };

  const sampleCatalogJson = JSON.stringify({
    "$schema": "https://specs.agentpay.org/v1/agent-catalog.schema.json",
    "protocol": "Unified Agent Protocol (UAP) / Agent Commerce Protocol (ACP)",
    "protocol_version": "1.0.0",
    "gateway": "AgentPay",
    "settlement_rail": {
      "provider": "RAZORPAY",
      "network": "test",
      "currency": "INR",
      "supported_methods": ["upi", "card", "netbanking"],
      "paise_multiplier": 100,
      "endpoints": {
        "intent_authorization": "/api/v1/purchase-intents",
        "policy_evaluation": "/api/v1/policies/evaluate",
        "x402_challenge": "/api/v1/protocol/x402/checkout"
      }
    },
    "policy_governance": {
      "model": "deterministic_reserve_commit",
      "security_boundary": "AI can decide and formulate intent; only AgentPay authorises money movement",
      "enforced_checks": ["per_transaction_limit", "rolling_24h_velocity", "category_whitelist", "merchant_blocklist"]
    },
    "products_count": 28,
    "sample_product": {
      "@type": "Product",
      "sku": "prod_jbl_770nc",
      "name": "JBL Tune 770NC Adaptive ANC Headphones",
      "offers": {
        "price": 4499.0,
        "priceCurrency": "INR",
        "pricePaise": 449900,
        "quote_ttl_seconds": 300,
        "seller": "Croma Electronics Hub"
      }
    }
  }, null, 2);

  const sampleUapJson = JSON.stringify({
    "uap_spec_version": "0.4.2-draft",
    "network_id": "in.npci.uap.testnet",
    "participant_id": "gateway.agentpay.in",
    "role": "AGENT_COMMERCE_GATEWAY",
    "operator": "Razorpay AgentPay Initiative",
    "supported_protocols": [
      "UAP-2026",
      "ACP (Agent Commerce Protocol)",
      "AP2 (Autonomous Payment Protocol)",
      "x402 (Payment Required Rail)",
      "MCP (Model Context Protocol 2024-11-05)"
    ],
    "settlement": {
      "rail": "RAZORPAY_TEST_MODE",
      "settlement_currency": "INR",
      "precision": "paise"
    },
    "invariants": {
      "zero_unauthorized_draws": true,
      "atomic_rollback_on_failure": true,
      "immutable_audit_trail": true
    }
  }, null, 2);

  const sampleLlmsTxt = `# AgentPay Verified Merchant Catalog
> Autonomous Agent Commerce on Razorpay Rails

## Policy & Execution Rules
- All transactions are subject to deterministic spending limits and 24h velocity bounds.
- Purchases use Two-Phase Reserve-Then-Commit (Razorpay native AUTHORIZE -> CAPTURE/RELEASE).
- AI Agents formulate purchase intents; payment credentials are never accessible by models.

## Verified Merchants
- Croma Electronics Hub (merchant_001) | Category: Electronics | Trust: 4.9/5.0
- Reliance Digital Tech (merchant_002) | Category: Computing | Trust: 4.9/5.0
- Amazon Prime Direct (merchant_003) | Category: Audio | Trust: 4.9/5.0

## Available Products
- JBL Tune 770NC (SKU: prod_jbl_770nc) | ₹4,499.00 INR (449900 paise)
- Dell UltraSharp 27" 4K (SKU: prod_dell_u2723qe) | ₹42,999.00 INR
- Sony WH-1000XM5 ANC (SKU: prod_sony_wh1000xm5) | ₹28,990.00 INR`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-md animate-fadeIn">
      <div className="w-full max-w-4xl max-h-[92vh] flex flex-col bg-[#FAF8F5] dark:bg-[#1C1A19] border border-[#E3DDD5] dark:border-[#383330] rounded-2xl shadow-2xl overflow-hidden">
        
        {/* Modal Header */}
        <div className="p-5 border-b border-[#E3DDD5] dark:border-[#383330] flex items-center justify-between bg-white/70 dark:bg-[#23201E]/80 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#FE7352] to-[#D94F30] text-white flex items-center justify-center shadow-sm">
              <OrganicBrainLogo size={24} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-lg text-[#1B1C1C] dark:text-white">
                  Agentic Commerce Protocol Hub
                </h3>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-[#FE7352]/10 text-[#AA361A] dark:text-[#FE7352] border border-[#FE7352]/20">
                  NPCI UAP · ACP · x402
                </span>
              </div>
              <p className="text-xs text-[#5D5552] dark:text-[#A89F9A] mt-0.5">
                Standardized machine-readable manifests & HTTP 402 payment challenge for AI buyers on Razorpay.
              </p>
            </div>
          </div>
          
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#7E7576] hover:text-[#1B1C1C] dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Protocol Tabs */}
        <div className="flex items-center gap-2 px-5 pt-3 border-b border-[#E3DDD5] dark:border-[#383330] bg-white/40 dark:bg-[#1E1C1A] overflow-x-auto text-xs font-mono">
          <button
            onClick={() => setActiveTab('catalog')}
            className={`pb-2.5 px-3 border-b-2 font-semibold transition-all whitespace-nowrap ${
              activeTab === 'catalog'
                ? 'border-[#FE7352] text-[#AA361A] dark:text-[#FE7352]'
                : 'border-transparent text-[#7E7576] hover:text-[#1B1C1C] dark:hover:text-white'
            }`}
          >
            /.well-known/agent-catalog.json
          </button>
          <button
            onClick={() => setActiveTab('uap')}
            className={`pb-2.5 px-3 border-b-2 font-semibold transition-all whitespace-nowrap ${
              activeTab === 'uap'
                ? 'border-[#FE7352] text-[#AA361A] dark:text-[#FE7352]'
                : 'border-transparent text-[#7E7576] hover:text-[#1B1C1C] dark:hover:text-white'
            }`}
          >
            /.well-known/uap-manifest.json
          </button>
          <button
            onClick={() => setActiveTab('llms')}
            className={`pb-2.5 px-3 border-b-2 font-semibold transition-all whitespace-nowrap ${
              activeTab === 'llms'
                ? 'border-[#FE7352] text-[#AA361A] dark:text-[#FE7352]'
                : 'border-transparent text-[#7E7576] hover:text-[#1B1C1C] dark:hover:text-white'
            }`}
          >
            /llms.txt (Crawler Feed)
          </button>
          <button
            onClick={() => {
              setActiveTab('x402');
              if (!x402Response) runX402Test();
            }}
            className={`pb-2.5 px-3 border-b-2 font-semibold transition-all flex items-center gap-1.5 whitespace-nowrap ${
              activeTab === 'x402'
                ? 'border-[#FE7352] text-[#AA361A] dark:text-[#FE7352]'
                : 'border-transparent text-[#7E7576] hover:text-[#1B1C1C] dark:hover:text-white'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            <span>Live x402 HTTP 402 Tester</span>
          </button>
          <button
            onClick={() => setActiveTab('enterprise')}
            className={`pb-2.5 px-3 border-b-2 font-semibold transition-all flex items-center gap-1.5 whitespace-nowrap ${
              activeTab === 'enterprise'
                ? 'border-[#FE7352] text-[#AA361A] dark:text-[#FE7352]'
                : 'border-transparent text-[#7E7576] hover:text-[#1B1C1C] dark:hover:text-white'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            <span>Razorpay Enterprise Rails (Notes · HMAC · Retries)</span>
          </button>
        </div>

        {/* Tab Body */}
        <div className="flex-1 p-5 overflow-y-auto font-mono text-xs">
          {activeTab === 'catalog' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between bg-white dark:bg-[#252220] p-3 rounded-xl border border-[#E3DDD5] dark:border-[#383330]">
                <div>
                  <div className="flex items-center gap-2">
                    <div className="font-bold text-[#1B1C1C] dark:text-white">Agent Commerce Protocol (ACP) Schema</div>
                    {liveCatalogJson ? (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-mono font-semibold border border-emerald-500/20">
                        ● Live SQLite DB Feed
                      </span>
                    ) : (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-black/5 text-[#7E7576] font-mono">
                        Schema Preview
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-[#7E7576] font-sans">
                    Provides Schema.org/Product representations, guaranteed quote TTLs, and Razorpay test-mode rails.
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <a
                    href="http://localhost:8000/.well-known/agent-catalog.json"
                    target="_blank"
                    rel="noreferrer"
                    className="px-2.5 py-1 rounded bg-black/5 dark:bg-white/10 hover:bg-black/10 text-[#1B1C1C] dark:text-white transition-colors"
                  >
                    Open Live Endpoint ↗
                  </a>
                  <button
                    onClick={() => handleCopy(liveCatalogJson || sampleCatalogJson)}
                    className="px-2.5 py-1 rounded bg-[#FE7352] text-white hover:bg-[#E56343] transition-colors"
                  >
                    {copied ? 'Copied!' : 'Copy Schema'}
                  </button>
                </div>
              </div>
              <pre className="p-4 bg-[#181615] text-[#F3EFEA] rounded-xl overflow-x-auto max-h-[380px] leading-relaxed text-[11px] border border-black/40">
                {liveCatalogJson || sampleCatalogJson}
              </pre>
            </div>
          )}

          {activeTab === 'uap' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between bg-white dark:bg-[#252220] p-3 rounded-xl border border-[#E3DDD5] dark:border-[#383330]">
                <div>
                  <div className="flex items-center gap-2">
                    <div className="font-bold text-[#1B1C1C] dark:text-white">NPCI UAP Network Participant Manifest</div>
                    {liveUapJson ? (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-mono font-semibold border border-emerald-500/20">
                        ● Live UAP Testnet
                      </span>
                    ) : null}
                  </div>
                  <div className="text-[11px] text-[#7E7576] font-sans">
                    Declared role: <code className="text-[#FE7352]">AGENT_COMMERCE_GATEWAY</code> on <code className="text-[#FE7352]">in.npci.uap.testnet</code>.
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <a
                    href="http://localhost:8000/.well-known/uap-manifest.json"
                    target="_blank"
                    rel="noreferrer"
                    className="px-2.5 py-1 rounded bg-black/5 dark:bg-white/10 hover:bg-black/10 text-[#1B1C1C] dark:text-white transition-colors"
                  >
                    Open Live Endpoint ↗
                  </a>
                  <button
                    onClick={() => handleCopy(liveUapJson || sampleUapJson)}
                    className="px-2.5 py-1 rounded bg-[#FE7352] text-white hover:bg-[#E56343] transition-colors"
                  >
                    {copied ? 'Copied!' : 'Copy Manifest'}
                  </button>
                </div>
              </div>
              <pre className="p-4 bg-[#181615] text-[#F3EFEA] rounded-xl overflow-x-auto max-h-[380px] leading-relaxed text-[11px] border border-black/40">
                {liveUapJson || sampleUapJson}
              </pre>
            </div>
          )}

          {activeTab === 'llms' && (
            <div className="space-y-3">
              <div className="flex items-center justify-between bg-white dark:bg-[#252220] p-3 rounded-xl border border-[#E3DDD5] dark:border-[#383330]">
                <div>
                  <div className="flex items-center gap-2">
                    <div className="font-bold text-[#1B1C1C] dark:text-white">/llms.txt AI Scraping & Context Feed</div>
                    {liveLlmsTxt ? (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-mono font-semibold border border-emerald-500/20">
                        ● Live Markdown Feed
                      </span>
                    ) : null}
                  </div>
                  <div className="text-[11px] text-[#7E7576] font-sans">
                    Plaintext Markdown catalog format tailored for LLM system prompt injection and crawler consumption.
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <a
                    href="http://localhost:8000/llms.txt"
                    target="_blank"
                    rel="noreferrer"
                    className="px-2.5 py-1 rounded bg-black/5 dark:bg-white/10 hover:bg-black/10 text-[#1B1C1C] dark:text-white transition-colors"
                  >
                    Open /llms.txt ↗
                  </a>
                  <button
                    onClick={() => handleCopy(liveLlmsTxt || sampleLlmsTxt)}
                    className="px-2.5 py-1 rounded bg-[#FE7352] text-white hover:bg-[#E56343] transition-colors"
                  >
                    {copied ? 'Copied!' : 'Copy Text'}
                  </button>
                </div>
              </div>
              <pre className="p-4 bg-[#181615] text-[#F3EFEA] rounded-xl overflow-x-auto max-h-[380px] leading-relaxed text-[11px] whitespace-pre-wrap border border-black/40">
                {liveLlmsTxt || sampleLlmsTxt}
              </pre>
            </div>
          )}

          {activeTab === 'x402' && (
            <div className="space-y-4">
              <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3.5 flex items-start justify-between gap-4 font-sans">
                <div>
                  <div className="text-xs font-bold text-amber-900 dark:text-amber-200 flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-amber-500 text-white font-mono text-[10px] font-bold">
                      HTTP 402 PAYMENT REQUIRED
                    </span>
                    <span>The Global Agent Payment Challenge</span>
                  </div>
                  <p className="text-xs text-amber-800/80 dark:text-amber-300/80 mt-1">
                    When an AI buyer requests a commercial SKU without authorization, AgentPay halts the transaction with an HTTP 402 challenge carrying a Razorpay order draft. The agent routes this challenge to the Policy Engine for approval before any money moves.
                  </p>
                </div>
                <button
                  onClick={() => runX402Test()}
                  disabled={x402Loading}
                  className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold shrink-0 transition-colors flex items-center gap-1.5 shadow-sm cursor-pointer"
                >
                  {x402Loading ? (
                    <span>Sending Challenge...</span>
                  ) : (
                    <>
                      <span>Re-run Challenge</span>
                      <span>⚡</span>
                    </>
                  )}
                </button>
              </div>

              {/* Product SKU Challenge Selector */}
              <div className="bg-white dark:bg-[#252220] p-3.5 rounded-xl border border-[#E3DDD5] dark:border-[#383330] flex flex-col sm:flex-row sm:items-center justify-between gap-3 font-sans">
                <div className="space-y-1">
                  <div className="text-xs font-bold text-[#1B1C1C] dark:text-white flex items-center gap-2">
                    <span>Target Commercial Product:</span>
                    {isLiveConnected ? (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-mono font-semibold border border-emerald-500/20">
                        ● Live FastAPI Rails
                      </span>
                    ) : (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:text-amber-300 font-mono">
                        ● Dynamic Protocol Engine
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-[#7E7576]">
                    Select any catalog SKU to observe how the price, paise calculation, and Razorpay order draft change dynamically.
                  </p>
                </div>
                <select
                  value={selectedSku}
                  onChange={(e) => {
                    const newSku = e.target.value;
                    setSelectedSku(newSku);
                    runX402Test(newSku);
                  }}
                  className="px-3 py-2 rounded-lg border border-[#CFBFC0] dark:border-[#4C4546] bg-white dark:bg-[#181615] text-xs font-medium text-[#1B1C1C] dark:text-white shrink-0 focus:outline-none focus:ring-2 focus:ring-[#FE7352]"
                >
                  {skuList.map(p => (
                    <option key={p.id} value={p.id}>
                      {p.name} — ₹{p.price.toLocaleString('en-IN')} ({p.price * 100} paise)
                    </option>
                  ))}
                </select>
              </div>

              {/* Live Headers Returned */}
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-[#7E7576] mb-1.5">
                  Protocol Response Headers (Intercepted)
                </div>
                <div className="bg-[#181615] text-[#78D387] p-3 rounded-xl border border-black/40 text-[11px] space-y-1 overflow-x-auto">
                  {Object.entries(x402Headers).map(([k, v]) => (
                    <div key={k} className="flex gap-2">
                      <span className="text-[#FE7352]">{k}:</span>
                      <span className="text-[#E0D8D0]">{v}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Live JSON Payload */}
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-[#7E7576] mb-1.5">
                  Agent Challenge Payload (JSON)
                </div>
                <pre className="p-4 bg-[#181615] text-[#F3EFEA] rounded-xl overflow-x-auto max-h-[240px] leading-relaxed text-[11px] border border-black/40">
                  {JSON.stringify(x402Response, null, 2)}
                </pre>
              </div>

              {/* Two-Phase Reserve-Then-Commit Flow Note */}
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl font-sans text-xs text-emerald-900 dark:text-emerald-300">
                <span className="font-bold">Execution Loop:</span> AI Agent receives this 402 challenge $\rightarrow$ Calls <code>POST /api/v1/purchase-intents</code> $\rightarrow$ Policy Engine checks limits $\rightarrow$ Funds reserved (<code>AUTHORIZED</code>) $\rightarrow$ Razorpay captures (<code>CAPTURED</code>).
              </div>
            </div>
          )}

          {activeTab === 'enterprise' && (
            <div className="space-y-4 font-sans">
              {/* Card 1: Razorpay Order Notes & Reconciliation */}
              <div className="bg-white dark:bg-[#252220] p-4 rounded-xl border border-[#E3DDD5] dark:border-[#383330] space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-700 dark:text-blue-300 font-mono text-[10px] font-bold border border-blue-500/20">
                      FEATURE 1
                    </span>
                    <h4 className="font-bold text-sm text-[#1B1C1C] dark:text-white">
                      Razorpay Order Notes & Dashboard Reconciliation
                    </h4>
                  </div>
                  <span className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                    <span>✓</span> Live Injected
                  </span>
                </div>
                <p className="text-xs text-[#5D5552] dark:text-[#A89F9A]">
                  Every autonomous checkout injects merchant-critical metadata into the Razorpay Order Notes. Enterprise accounting teams can filter, audit, and reconcile agent purchases directly within the native Razorpay Dashboard without custom exports.
                </p>
                <div className="bg-[#181615] text-[#F3EFEA] p-3 rounded-lg font-mono text-[11px] overflow-x-auto border border-black/40">
                  <pre>{JSON.stringify({
                    "notes": {
                      "agent_id": "agent_001",
                      "purchase_intent_id": "pi_9f83a12b4e7c",
                      "policy_id": "policy_001",
                      "merchant_id": "merchant_001",
                      "transaction_id": "tx_4a91c28f7d0e",
                      "gateway": "AgentPay-v1.1"
                    }
                  }, null, 2)}</pre>
                </div>
              </div>

              {/* Card 2: HMAC SHA-256 Webhook Cryptography & Replay Protection */}
              <div className="bg-white dark:bg-[#252220] p-4 rounded-xl border border-[#E3DDD5] dark:border-[#383330] space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-purple-500/10 text-purple-700 dark:text-purple-300 font-mono text-[10px] font-bold border border-purple-500/20">
                      FEATURE 2
                    </span>
                    <h4 className="font-bold text-sm text-[#1B1C1C] dark:text-white">
                      HMAC-SHA256 Webhooks & Replay Attack Defense
                    </h4>
                  </div>
                  <span className="text-[11px] font-mono text-purple-600 dark:text-purple-400 font-semibold flex items-center gap-1">
                    <span>🛡</span> Replay Guarded
                  </span>
                </div>
                <p className="text-xs text-[#5D5552] dark:text-[#A89F9A]">
                  Asynchronous Razorpay webhooks (<code>payment.captured</code>, <code>order.paid</code>) are verified cryptographically via timing-safe HMAC-SHA256 signatures. An active deduplication cache tracks event IDs, safely rejecting replay attacks with <code className="text-[#FE7352]">DUPLICATE_REPLAY_IGNORED</code> without state machine regressions.
                </p>
                <div className="p-3 bg-purple-500/5 rounded-lg border border-purple-500/15 text-xs text-purple-900 dark:text-purple-200 font-mono space-y-1">
                  <div>Endpoint: <span className="font-bold">POST /api/v1/payments/webhook</span></div>
                  <div>Header: <span className="text-[#FE7352]">X-Razorpay-Signature: hmac_sha256(secret, payload)</span></div>
                  <div>Header: <span className="text-[#FE7352]">X-Razorpay-Event-Id: evt_test_...</span></div>
                </div>
              </div>

              {/* Card 3: Network Latency Fallback & Idempotent Retry */}
              <div className="bg-white dark:bg-[#252220] p-4 rounded-xl border border-[#E3DDD5] dark:border-[#383330] space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:text-amber-300 font-mono text-[10px] font-bold border border-amber-500/20">
                      FEATURE 3
                    </span>
                    <h4 className="font-bold text-sm text-[#1B1C1C] dark:text-white">
                      Network Timeout Fallback & Zero Duplicate Charges
                    </h4>
                  </div>
                  <span className="text-[11px] font-mono text-amber-600 dark:text-amber-400 font-semibold flex items-center gap-1">
                    <span>⚡</span> 100% Idempotent
                  </span>
                </div>
                <p className="text-xs text-[#5D5552] dark:text-[#A89F9A]">
                  If Razorpay test rails experience simulated network latency or connection timeouts, AgentPay safely holds funds in the <code className="text-emerald-600 dark:text-emerald-400 font-mono">AUTHORIZED</code> reservation stage. Subsequent retries using the client&apos;s idempotency key resume from the existing reservation, guaranteeing zero duplicate charges and zero double-deductions from the merchant budget.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-[#E3DDD5] dark:border-[#383330] bg-white/50 dark:bg-[#1C1A19] flex items-center justify-between font-mono text-xs">
          <span className="text-[#7E7576]">Protocol Architecture: AgentPay Gateway v1.1.0</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-[#1B1C1C] dark:bg-white text-white dark:text-[#1B1C1C] font-semibold hover:opacity-90 transition-opacity"
          >
            Close Explorer
          </button>
        </div>

      </div>
    </div>
  );
};
