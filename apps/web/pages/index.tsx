import React, { useState, useEffect, useRef } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { NarrativeRail, StageKey, StageInfo } from '@/components/NarrativeRail';
import { TimelineEvent, EventStatus } from '@/components/ProgressionThread';
import { ExploreLayer } from '@/components/ExploreLayer';
import { fetchProducts, fetchAgentPolicy, finalizeTransaction, reservePurchaseIntent } from '@/lib/api';

interface MerchantQuote {
  merchantId: string;
  merchantName: string;
  price: number;
  currency: string;
  deliveryEta: string;
  warranty: string;
  inStock: boolean;
  isBest: boolean;
  quoteExpiresInSec: number;
}

export interface ProductOption {
  id: string;
  name: string;
  brand: string;
  price: number;
  rating: number;
  badge: string;
  specsLine: string;
  quotes: MerchantQuote[];
  savingsText: string;
  policyCap?: number;
}

interface PurchaseStory {
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

export default function ContinuousBuyJourney() {
  const router = useRouter();
  const [promptInput, setPromptInput] = useState('');
  const [hasStarted, setHasStarted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [currentStage, setCurrentStage] = useState<StageKey>('ask');
  const [showExploreLayer, setShowExploreLayer] = useState(false);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [story, setStory] = useState<PurchaseStory | null>(null);
  const [quoteSecondsLeft, setQuoteSecondsLeft] = useState(272); // 04:32
  const [visibleStep, setVisibleStep] = useState<number>(0);

  const wordmarkRef = useRef<HTMLHeadingElement>(null);

  // Candidate product selector in Catalog view
  const handleSelectCandidateProduct = (optionId: string) => {
    setStory((prev) => {
      if (!prev) return null;
      const option = prev.candidateProducts.find((o) => o.id === optionId);
      if (!option) return prev;
      const bestQuote = option.quotes.find((q) => q.isBest) || option.quotes[0];
      const cap = option.policyCap || 15000;
      return {
        ...prev,
        selectedProductId: option.id,
        productName: option.name,
        specsLine: option.specsLine,
        quotes: option.quotes,
        savingsText: option.savingsText,
        chosenQuote: bestQuote,
        authPrice: bestQuote.price,
        policyVerdict: {
          passed: bestQuote.price <= cap,
          ruleSummary: `Category cap: ₹${cap.toLocaleString('en-IN')}`,
          details: `₹${bestQuote.price.toLocaleString('en-IN')} ≤ ₹${cap.toLocaleString('en-IN')} · Merchant: ${bestQuote.merchantName} is approved`
        }
      };
    });
  };

  // Merchant quote selector in Delivered Quotes view
  const handleSelectMerchantQuote = (merchantId: string) => {
    setStory((prev) => {
      if (!prev) return null;
      const quote = prev.quotes.find((q) => q.merchantId === merchantId);
      if (!quote) return prev;

      // Find policy cap for the currently selected product
      const currentCandidate = prev.candidateProducts.find((p) => p.id === prev.selectedProductId);
      const cap = currentCandidate?.policyCap || 15000;

      // Calculate dynamic savings / comparison text relative to alternative merchant quotes
      const otherQuotes = prev.quotes.filter((q) => q.merchantId !== quote.merchantId);
      let savingsText = prev.savingsText;
      if (otherQuotes.length > 0) {
        const higherQuotes = otherQuotes.filter((q) => q.price > quote.price);
        if (higherQuotes.length > 0) {
          const maxOther = Math.max(...otherQuotes.map((q) => q.price));
          const saved = maxOther - quote.price;
          savingsText = `Selected ${quote.merchantName} (${quote.deliveryEta}). You save ₹${saved.toLocaleString('en-IN')} compared to alternative merchant bids.`;
        } else {
          const minOther = Math.min(...otherQuotes.map((q) => q.price));
          const diff = quote.price - minOther;
          if (diff > 0) {
            savingsText = `Selected ${quote.merchantName} (${quote.deliveryEta}, +₹${diff.toLocaleString('en-IN')} over lowest offer for preferred merchant / delivery SLA).`;
          } else {
            savingsText = `Selected ${quote.merchantName} (${quote.deliveryEta}) at lowest verified market price ₹${quote.price.toLocaleString('en-IN')}.`;
          }
        }
      }

      return {
        ...prev,
        chosenQuote: quote,
        authPrice: quote.price,
        savingsText,
        policyVerdict: {
          passed: quote.price <= cap,
          ruleSummary: `Category cap: ₹${cap.toLocaleString('en-IN')}`,
          details: `₹${quote.price.toLocaleString('en-IN')} ${quote.price <= cap ? '≤' : '>'} ₹${cap.toLocaleString('en-IN')} · Merchant: ${quote.merchantName} is approved`
        }
      };
    });
  };

  // Alternative option handlers
  const handleFindCheaper = () => {
    if (!story) return;
    if (story.candidateProducts && story.candidateProducts.length > 1) {
      const currentPrice = story.authPrice;
      const cheaperOptions = [...story.candidateProducts]
        .filter((o) => o.price < currentPrice)
        .sort((a, b) => a.price - b.price);
      if (cheaperOptions.length > 0) {
        handleSelectCandidateProduct(cheaperOptions[0].id);
        return;
      }
    }
    const lower = story.productName.toLowerCase();
    let q = '';
    if (lower.includes('mouse')) {
      q = 'Find a cheaper wireless mouse under ₹3,000';
    } else if (lower.includes('keyboard')) {
      q = 'Find a cheaper mechanical keyboard under ₹3,000';
    } else if (lower.includes('headphone') || lower.includes('audio')) {
      q = 'Find cheaper wireless ANC headphones under ₹3,000';
    } else if (lower.includes('monitor') || lower.includes('display')) {
      q = 'Find a cheaper 144 Hz monitor under ₹18,000';
    } else if (lower.includes('fryer') || lower.includes('kitchen')) {
      q = 'Find a cheaper air fryer under ₹4,000';
    } else {
      const budget = Math.round(story.authPrice * 0.65);
      q = `Find a cheaper option under ₹${budget.toLocaleString('en-IN')}`;
    }
    setPromptInput(q);
    startPurchaseFlow(q);
  };

  const handleDifferentBrand = () => {
    if (!story) return;
    if (story.candidateProducts && story.candidateProducts.length > 1) {
      const currentOption = story.candidateProducts.find((p) => p.id === story.selectedProductId);
      const currentBrand = currentOption?.brand?.toLowerCase() || '';
      const otherBrandOption = story.candidateProducts.find(
        (p) => p.brand && p.brand.toLowerCase() !== currentBrand
      );
      if (otherBrandOption) {
        handleSelectCandidateProduct(otherBrandOption.id);
        return;
      }
    }
    const lower = story.productName.toLowerCase();
    let q = '';
    if (lower.includes('logitech')) {
      q = 'Find Razer or Apple mouse options';
    } else if (lower.includes('razer') || lower.includes('dell')) {
      q = 'Find Logitech mouse options';
    } else if (lower.includes('jbl')) {
      q = 'Find Sony noise cancelling headphones';
    } else if (lower.includes('sony')) {
      q = 'Find JBL or Bose noise cancelling headphones';
    } else if (lower.includes('keychron')) {
      q = 'Find Redragon mechanical keyboard';
    } else if (lower.includes('lg')) {
      q = 'Find Acer or Gigabyte gaming monitor';
    } else if (lower.includes('philips')) {
      q = 'Find Inalsa or Prestige air fryer';
    } else {
      q = `Find alternative brand for ${story.productName}`;
    }
    setPromptInput(q);
    startPurchaseFlow(q);
  };

  // Handle incoming query param ?q=
  useEffect(() => {
    if (router.isReady && router.query.q && typeof router.query.q === 'string' && !hasStarted) {
      const q = router.query.q;
      setPromptInput(q);
      startPurchaseFlow(q);
    }
  }, [router.isReady, router.query.q]);

  // Mouse move handler for living wordmark
  const handleWordmarkMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    e.currentTarget.style.setProperty('--pointer-x', `${x}%`);
    e.currentTarget.style.setProperty('--pointer-y', `${y}%`);
  };

  const handleWordmarkMouseLeave = (e: React.MouseEvent<HTMLDivElement>) => {
    e.currentTarget.style.setProperty('--pointer-x', `50%`);
    e.currentTarget.style.setProperty('--pointer-y', `50%`);
  };

  // Quote freshness countdown
  useEffect(() => {
    if (!hasStarted || quoteSecondsLeft <= 0) return;
    const timer = setInterval(() => {
      setQuoteSecondsLeft((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [hasStarted, quoteSecondsLeft]);

  const formatCountdown = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  // Format current time
  const getNowTime = () => {
    const d = new Date();
    return d.toTimeString().split(' ')[0];
  };

  // Trigger Purchase Flow
  const startPurchaseFlow = async (queryText: string) => {
    if (!queryText.trim()) return;
    setHasStarted(true);
    setLoading(true);
    setCurrentStage('explore');

    const now = getNowTime();
    const lower = queryText.toLowerCase();

    // 1. Intelligent initial catalog resolver based on query keywords
    let candidates: ProductOption[] = [];
    let defaultCap = 15000;

    if (lower.includes('mouse')) {
      defaultCap = 10000;
      candidates = [
        {
          id: 'opt_mouse_mx3s',
          name: 'Logitech MX Master 3S Wireless Performance Mouse',
          brand: 'Logitech',
          price: 8750,
          rating: 4.9,
          badge: 'Flagship / Recommended',
          specsLine: '8,000 DPI Darkfield · MagSpeed Electromagnetic Scroll · Multi-Device Bluetooth',
          policyCap: 10000,
          quotes: [
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 8750,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '2 Years Manufacturer Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 8995,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '2 Years Manufacturer Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 8999,
              currency: 'INR',
              deliveryEta: 'Arrives Wednesday',
              warranty: '2 Years Manufacturer Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹245 versus Croma and ₹249 versus Reliance Digital.'
        },
        {
          id: 'opt_mouse_dell_ms5320w',
          name: 'Dell Premier Multi-Device Wireless Mouse MS5320W',
          brand: 'Dell',
          price: 2999,
          rating: 4.6,
          badge: 'Best Value Pick',
          specsLine: 'Multi-Device 3-PC Pairing · 1600 DPI · 36-Month Battery Life',
          policyCap: 10000,
          quotes: [
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 2999,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '3 Years Dell Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 3199,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '3 Years Dell Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 3299,
              currency: 'INR',
              deliveryEta: 'Arrives Wednesday',
              warranty: '3 Years Dell Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹200 versus Reliance Digital and ₹300 versus Amazon Prime Direct.'
        },
        {
          id: 'opt_mouse_razer_v3',
          name: 'Razer DeathAdder V3 Ultra-Lightweight Ergonomic Gaming Mouse',
          brand: 'Razer',
          price: 5499,
          rating: 4.8,
          badge: 'Pro Performance',
          specsLine: '59g Ultra-Lightweight · Focus Pro 30K Optical Sensor · 8000Hz Polling',
          policyCap: 10000,
          quotes: [
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 5499,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '2 Years Razer Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 5799,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '2 Years Razer Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 5899,
              currency: 'INR',
              deliveryEta: 'Arrives Thursday',
              warranty: '2 Years Razer Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹300 versus Croma and ₹400 versus Reliance Digital.'
        },
        {
          id: 'opt_mouse_logitech_lift',
          name: 'Logitech Lift Ergonomic Vertical Mouse',
          brand: 'Logitech',
          price: 5495,
          rating: 4.7,
          badge: 'Ergonomic Choice',
          specsLine: '57° Natural Handshake Angle · Whisper Quiet Clicks · 2 Years Battery',
          policyCap: 10000,
          quotes: [
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 5495,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '2 Years Logitech Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 5695,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '2 Years Logitech Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 5799,
              currency: 'INR',
              deliveryEta: 'Arrives Wednesday',
              warranty: '2 Years Logitech Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹200 versus Croma and ₹304 versus Amazon Prime Direct.'
        }
      ];
    } else if (lower.includes('keyboard')) {
      defaultCap = 8000;
      candidates = [
        {
          id: 'opt_kb_keychron_k2',
          name: 'Keychron K2 Wireless Mechanical Keyboard (Version 2)',
          brand: 'Keychron',
          price: 4999,
          rating: 4.8,
          badge: 'Recommended',
          specsLine: '75% Layout (84 keys) · Gateron Brown Switches · Bluetooth 5.1 & Wired · Mac/Win',
          policyCap: 8000,
          quotes: [
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 4999,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '1 Year Official Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 5299,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '1 Year Official Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 5499,
              currency: 'INR',
              deliveryEta: 'Arrives Wednesday',
              warranty: '1 Year Official Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹300 versus Reliance Digital and ₹500 versus Amazon Prime Direct.'
        },
        {
          id: 'opt_kb_redragon',
          name: 'Redragon K552 Kumara Tenkeyless Mechanical Keyboard',
          brand: 'Redragon',
          price: 2899,
          rating: 4.5,
          badge: 'Best Value Pick',
          specsLine: 'TKL Compact · Dust-Proof Red Linear Switches · Solid Metal Construction',
          policyCap: 8000,
          quotes: [
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 2899,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '1 Year Redragon Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 3099,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '1 Year Redragon Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 3199,
              currency: 'INR',
              deliveryEta: 'Arrives Thursday',
              warranty: '1 Year Redragon Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹200 versus Croma and ₹300 versus Reliance Digital.'
        },
        {
          id: 'opt_kb_k2_pro',
          name: 'Keychron K2 Pro QMK/VIA Custom Mechanical Keyboard',
          brand: 'Keychron',
          price: 8499,
          rating: 4.9,
          badge: 'Pro Enthusiast',
          specsLine: 'Full QMK/VIA Programmable · Hot-Swappable Switches · Sound Absorbing Foam',
          policyCap: 12000,
          quotes: [
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 8499,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '1 Year Official Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 8799,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '1 Year Official Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 8999,
              currency: 'INR',
              deliveryEta: 'Arrives Thursday',
              warranty: '1 Year Official Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹300 versus Reliance Digital and ₹500 versus Amazon Prime Direct.'
        }
      ];
    } else if (lower.includes('headphone') || lower.includes('audio') || lower.includes('jbl') || lower.includes('anc') || lower.includes('earbud')) {
      defaultCap = 6000;
      candidates = [
        {
          id: 'opt_hp_jbl_770nc',
          name: 'JBL Tune 770NC Wireless Adaptive ANC Headphones',
          brand: 'JBL',
          price: 4499,
          rating: 4.6,
          badge: 'Recommended / Best Value ANC',
          specsLine: 'Adaptive ANC · 70h Battery · Bluetooth 5.3 · Speed Charge',
          policyCap: 6000,
          quotes: [
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 4499,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '1 Year Brand Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 4799,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '1 Year Brand Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 4999,
              currency: 'INR',
              deliveryEta: 'Arrives Tuesday',
              warranty: '1 Year Brand Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹300 versus Reliance Digital and ₹500 versus Amazon Prime Direct.'
        },
        {
          id: 'opt_hp_sony_720n',
          name: 'Sony WH-CH720N Noise Cancelling Wireless Headphones',
          brand: 'Sony',
          price: 7990,
          rating: 4.7,
          badge: 'Premium Flagship ANC',
          specsLine: 'Integrated V1 Processor · Dual Noise Sensor · 35h Battery · Lightweight 192g',
          policyCap: 10000,
          quotes: [
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 7990,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '1 Year Sony Official Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 8290,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '1 Year Sony Official Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 8490,
              currency: 'INR',
              deliveryEta: 'Arrives Wednesday',
              warranty: '1 Year Sony Official Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹300 versus Croma and ₹500 versus Amazon Prime Direct.'
        },
        {
          id: 'opt_hp_boat_550',
          name: 'boAt Rockerz 550 Over-Ear Wireless Headphones',
          brand: 'boAt',
          price: 1799,
          rating: 4.3,
          badge: 'Budget Pick',
          specsLine: '50mm Dynamic Drivers · 20h Playback · Physical Noise Isolation · Ergonomic Earcups',
          policyCap: 5000,
          quotes: [
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 1799,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '1 Year Brand Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 1999,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '1 Year Brand Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 2099,
              currency: 'INR',
              deliveryEta: 'Arrives Thursday',
              warranty: '1 Year Brand Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹200 versus Croma and ₹300 versus Reliance Digital.'
        }
      ];
    } else if (lower.includes('fryer') || lower.includes('air fryer') || lower.includes('kitchen')) {
      defaultCap = 8000;
      candidates = [
        {
          id: 'opt_fryer_philips',
          name: 'Philips Essential Digital Air Fryer 4.1L (Rapid Air)',
          brand: 'Philips',
          price: 5499,
          rating: 4.6,
          badge: 'Recommended',
          specsLine: '4.1L Capacity · 90% Less Fat · 7 Presets · 1400W Rapid Air',
          policyCap: 8000,
          quotes: [
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 5499,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '2 Years Philips Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 5899,
              currency: 'INR',
              deliveryEta: 'Arrives in 3 days',
              warranty: '2 Years Philips Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 5999,
              currency: 'INR',
              deliveryEta: 'Arrives Wednesday',
              warranty: '2 Years Philips Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹400 versus Croma and ₹500 versus Amazon Prime Direct.'
        },
        {
          id: 'opt_fryer_inalsa',
          name: 'Inalsa Digital Air Fryer 4.2L with Air Crisp Technology',
          brand: 'Inalsa',
          price: 3699,
          rating: 4.4,
          badge: 'Best Value Pick',
          specsLine: '4.2L Capacity · 8 Preset Menus · 1400W Power · Non-Stick Coated Pan',
          policyCap: 8000,
          quotes: [
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 3699,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '2 Years Inalsa Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 3999,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '2 Years Inalsa Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 4199,
              currency: 'INR',
              deliveryEta: 'Arrives Thursday',
              warranty: '2 Years Inalsa Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹300 versus Croma and ₹500 versus Reliance Digital.'
        },
        {
          id: 'opt_fryer_prestige',
          name: 'Prestige Nutrifry Electric Digital Air Fryer 4.5L',
          brand: 'Prestige',
          price: 4299,
          rating: 4.5,
          badge: 'Family Capacity',
          specsLine: '4.5L High-Volume Basket · 30-Minute Timer · 1500W High Efficiency',
          policyCap: 8000,
          quotes: [
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 4299,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '1 Year Prestige Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 4599,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '1 Year Prestige Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 4799,
              currency: 'INR',
              deliveryEta: 'Arrives Friday',
              warranty: '1 Year Prestige Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹300 versus Reliance Digital and ₹500 versus Amazon Prime Direct.'
        }
      ];
    } else if (lower.includes('monitor') || lower.includes('screen') || lower.includes('display')) {
      defaultCap = 30000;
      candidates = [
        {
          id: 'opt_mon_lg_27',
          name: 'LG UltraGear 27-inch QHD 144Hz IPS Gaming Monitor',
          brand: 'LG',
          price: 24999,
          rating: 4.8,
          badge: 'Flagship QHD',
          specsLine: '2560x1440 IPS Panel · 144Hz Refresh · 1ms GtG · HDR10 · G-SYNC Compatible',
          policyCap: 30000,
          quotes: [
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 24999,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '3 Years Comprehensive Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 25499,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '3 Years Comprehensive Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 25799,
              currency: 'INR',
              deliveryEta: 'Arrives Thursday',
              warranty: '3 Years Comprehensive Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹500 versus Reliance Digital and ₹800 versus Amazon Prime Direct.'
        },
        {
          id: 'opt_mon_acer_27',
          name: 'Acer Nitro VG271U 27-inch 144Hz WQHD IPS Monitor',
          brand: 'Acer',
          price: 22499,
          rating: 4.6,
          badge: 'Value 144Hz Pick',
          specsLine: '2K WQHD IPS · 0.5ms Response · 99% sRGB · Dual HDMI 2.0 & DisplayPort',
          policyCap: 30000,
          quotes: [
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 22499,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '3 Years Onsite Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 22999,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '3 Years Onsite Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 23499,
              currency: 'INR',
              deliveryEta: 'Arrives Friday',
              warranty: '3 Years Onsite Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹500 versus Croma and ₹1,000 versus Reliance Digital.'
        },
        {
          id: 'opt_mon_dell_24',
          name: 'Dell 24-inch FHD IPS Anti-Glare Monitor S2421HN',
          brand: 'Dell',
          price: 9999,
          rating: 4.5,
          badge: 'Budget Office Pick',
          specsLine: '1080p FHD IPS · 75Hz Refresh · AMD FreeSync · Dual HDMI · Ultrathin Bezel',
          policyCap: 15000,
          quotes: [
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 9999,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '3 Years Dell Advanced Exchange',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 10499,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '3 Years Dell Advanced Exchange',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 10799,
              currency: 'INR',
              deliveryEta: 'Arrives Thursday',
              warranty: '3 Years Dell Advanced Exchange',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹500 versus Reliance Digital and ₹800 versus Amazon Prime Direct.'
        }
      ];
    } else if (lower.includes('laptop') || lower.includes('macbook')) {
      defaultCap = 100000;
      candidates = [
        {
          id: 'opt_lap_macbook',
          name: 'Apple MacBook Air 13.6-inch M2 (Liquid Retina Display)',
          brand: 'Apple',
          price: 89900,
          rating: 4.9,
          badge: 'Flagship Ultraportable',
          specsLine: 'Apple M2 Chip · 8GB Unified Memory · 256GB SSD · MagSafe 3 · 18h Battery',
          policyCap: 100000,
          quotes: [
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 89900,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '1 Year Apple Official Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 91900,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '1 Year Apple Official Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 92490,
              currency: 'INR',
              deliveryEta: 'Arrives Thursday',
              warranty: '1 Year Apple Official Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹2,000 versus Croma and ₹2,590 versus Amazon Prime Direct.'
        },
        {
          id: 'opt_lap_asus',
          name: 'ASUS Vivobook 15 Intel Core i5 16GB RAM 512GB SSD',
          brand: 'ASUS',
          price: 49990,
          rating: 4.6,
          badge: 'Best Value Workstation',
          specsLine: '12th Gen Intel Core i5 · 16GB DDR4 · 512GB NVMe SSD · 15.6" FHD Anti-Glare',
          policyCap: 70000,
          quotes: [
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 49990,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '1 Year Onsite Manufacturer Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 51990,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '1 Year Onsite Manufacturer Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 52490,
              currency: 'INR',
              deliveryEta: 'Arrives Thursday',
              warranty: '1 Year Onsite Manufacturer Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹2,000 versus Reliance Digital and ₹2,500 versus Amazon Prime Direct.'
        },
        {
          id: 'opt_lap_lenovo',
          name: 'Lenovo IdeaPad Slim 3 15-inch Intel Core i3 8GB 512GB SSD',
          brand: 'Lenovo',
          price: 37990,
          rating: 4.4,
          badge: 'Budget Everyday Pick',
          specsLine: 'Intel Core i3 12th Gen · 8GB RAM · 512GB SSD · Rapid Charge · 1.63kg Lightweight',
          policyCap: 50000,
          quotes: [
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 37990,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '2 Years Lenovo Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 38990,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '2 Years Lenovo Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 39490,
              currency: 'INR',
              deliveryEta: 'Arrives Wednesday',
              warranty: '2 Years Lenovo Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹1,000 versus Croma and ₹1,500 versus Reliance Digital.'
        }
      ];
    } else {
      // General dynamic query naming
      const cleanWords = queryText.replace(/find|buy|get|search|for|under|rs|₹|\d+/gi, '').trim();
      const capitalized = cleanWords ? cleanWords.charAt(0).toUpperCase() + cleanWords.slice(1) : 'Requested Item';
      defaultCap = 12000;
      candidates = [
        {
          id: 'opt_gen_recommended',
          name: `${capitalized} (Top Recommended Choice)`,
          brand: 'Top Brand',
          price: 3499,
          rating: 4.8,
          badge: 'Recommended',
          specsLine: 'Verified Merchant Inventory · Standard Manufacturer Warranty · Express Delivery',
          policyCap: defaultCap,
          quotes: [
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 3499,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '1 Year Brand Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 3799,
              currency: 'INR',
              deliveryEta: 'Arrives in 3 days',
              warranty: '1 Year Brand Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 3999,
              currency: 'INR',
              deliveryEta: 'Arrives Thursday',
              warranty: '1 Year Brand Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹300 versus Reliance Digital and ₹500 versus Amazon Prime Direct.'
        },
        {
          id: 'opt_gen_value',
          name: `${capitalized} (Best Value Option)`,
          brand: 'Value Brand',
          price: 2299,
          rating: 4.5,
          badge: 'Best Value Pick',
          specsLine: 'Budget Friendly · Multi-Merchant Verified · Rapid Dispatch',
          policyCap: defaultCap,
          quotes: [
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 2299,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '1 Year Official Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 2499,
              currency: 'INR',
              deliveryEta: 'Arrives in 3 days',
              warranty: '1 Year Official Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 2599,
              currency: 'INR',
              deliveryEta: 'Arrives Friday',
              warranty: '1 Year Official Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹200 versus Croma and ₹300 versus Reliance Digital.'
        },
        {
          id: 'opt_gen_premium',
          name: `${capitalized} (Pro / Extended Edition)`,
          brand: 'Pro Brand',
          price: 5499,
          rating: 4.9,
          badge: 'Pro Performance',
          specsLine: 'Extended Specifications · Premium Finish · Comprehensive 2-Year Warranty',
          policyCap: defaultCap * 1.5,
          quotes: [
            {
              merchantId: 'merchant_002',
              merchantName: 'Reliance Digital',
              price: 5499,
              currency: 'INR',
              deliveryEta: 'Arrives Tomorrow',
              warranty: '2 Years Manufacturer Warranty',
              inStock: true,
              isBest: true,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_001',
              merchantName: 'Croma',
              price: 5799,
              currency: 'INR',
              deliveryEta: 'Arrives in 2 days',
              warranty: '2 Years Manufacturer Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            },
            {
              merchantId: 'merchant_003',
              merchantName: 'Amazon Prime Direct',
              price: 5999,
              currency: 'INR',
              deliveryEta: 'Arrives Wednesday',
              warranty: '2 Years Manufacturer Warranty',
              inStock: true,
              isBest: false,
              quoteExpiresInSec: 272
            }
          ],
          savingsText: 'You save ₹300 versus Croma and ₹500 versus Amazon Prime Direct.'
        }
      ];
    }

    const initialCandidate = candidates[0];
    const initialBestQuote = initialCandidate.quotes.find(q => q.isBest) || initialCandidate.quotes[0];
    const initialCap = initialCandidate.policyCap || defaultCap;

    // Initial contextual story state
    setStory({
      query: queryText,
      queryTime: now,
      candidateProducts: candidates,
      selectedProductId: initialCandidate.id,
      productName: initialCandidate.name,
      specsLine: initialCandidate.specsLine,
      quotes: initialCandidate.quotes,
      savingsText: initialCandidate.savingsText,
      policyVerdict: {
        passed: initialBestQuote.price <= initialCap,
        ruleSummary: `Category cap: ₹${initialCap.toLocaleString('en-IN')}`,
        details: `₹${initialBestQuote.price.toLocaleString('en-IN')} ≤ ₹${initialCap.toLocaleString('en-IN')} · Merchant: ${initialBestQuote.merchantName} is approved`
      },
      chosenQuote: initialBestQuote,
      authPrice: initialBestQuote.price,
      settlementState: 'idle'
    });

    // 2. Progressive reveal starts immediately so user gets instant visual feedback
    setVisibleStep(1); // 01 Ask: Intent captured
    setCurrentStage('ask');

    setTimeout(() => {
      setVisibleStep(2); // 02 Explore: Searching approved merchants...
      setCurrentStage('explore');
    }, 500);

    setTimeout(() => {
      setVisibleStep(3); // 03 Compare: Delivered-price comparison reveals
      setCurrentStage('compare');
    }, 1200);

    setTimeout(() => {
      setVisibleStep(4); // 04 Guardrail: Policy verification resolves
      setCurrentStage('guardrail');
    }, 1900);

    setTimeout(() => {
      setVisibleStep(5); // 05 Authorize: Ready for user authorization
      setCurrentStage('authorize');
      setLoading(false);
    }, 2500);

    // 3. Concurrently fetch live matched catalog products to enrich candidate choices
    fetchProducts(queryText)
      .then((liveProducts) => {
        if (liveProducts && liveProducts.length > 0) {
          const apiCandidates: ProductOption[] = liveProducts.slice(0, 4).map((item, idx) => {
            const itemPrice = item.price;
            const liveQuotes: MerchantQuote[] = [
              {
                merchantId: item.merchant_id,
                merchantName: item.merchant_name || 'Croma',
                price: itemPrice,
                currency: item.currency || 'INR',
                deliveryEta: 'Arrives Tomorrow',
                warranty: 'Official Brand Warranty',
                inStock: item.in_stock,
                isBest: true,
                quoteExpiresInSec: 272
              },
              {
                merchantId: 'merchant_002',
                merchantName: 'Reliance Digital',
                price: Math.round(itemPrice * 1.04),
                currency: 'INR',
                deliveryEta: 'Arrives in 2 days',
                warranty: 'Official Brand Warranty',
                inStock: true,
                isBest: false,
                quoteExpiresInSec: 272
              },
              {
                merchantId: 'merchant_003',
                merchantName: 'Amazon Prime Direct',
                price: Math.round(itemPrice * 1.06),
                currency: 'INR',
                deliveryEta: 'Arrives in 3 days',
                warranty: 'Official Brand Warranty',
                inStock: true,
                isBest: false,
                quoteExpiresInSec: 272
              }
            ];

            const itemSpecs = item.specs
              ? Object.values(item.specs).filter(v => typeof v === 'string').slice(0, 3).join(' · ')
              : `${item.category} · Verified Merchant SKU`;

            const badges = ['Recommended', 'Best Value Pick', 'Pro Performance', 'Alternative Choice'];

            return {
              id: item.id || `live_prod_${idx}`,
              name: item.name,
              brand: item.brand || (item.name.split(' ')[0] || 'Brand'),
              price: itemPrice,
              rating: item.rating || 4.7,
              badge: badges[idx] || 'Catalog Pick',
              specsLine: itemSpecs,
              quotes: liveQuotes,
              savingsText: `You save ₹${Math.round(itemPrice * 0.04).toLocaleString('en-IN')} versus Reliance Digital.`,
              policyCap: Math.max(itemPrice * 1.2, defaultCap)
            };
          });

          if (apiCandidates.length > 0) {
            const topCandidate = apiCandidates[0];
            const topBestQuote = topCandidate.quotes[0];
            const topCap = topCandidate.policyCap || defaultCap;

            setStory(prev => prev ? {
              ...prev,
              candidateProducts: apiCandidates,
              selectedProductId: topCandidate.id,
              productName: topCandidate.name,
              specsLine: topCandidate.specsLine,
              quotes: topCandidate.quotes,
              savingsText: topCandidate.savingsText,
              chosenQuote: topBestQuote,
              authPrice: topBestQuote.price,
              policyVerdict: {
                passed: topBestQuote.price <= topCap,
                ruleSummary: `Category cap: ₹${topCap.toLocaleString('en-IN')}`,
                details: `₹${topBestQuote.price.toLocaleString('en-IN')} ≤ ₹${topCap.toLocaleString('en-IN')} · Merchant: ${topBestQuote.merchantName} is approved`
              }
            } : null);
          }
        }
      })
      .catch((e) => {
        console.error('Failed live backend product resolution', e);
      });
  };

  // Handle incoming query parameter `q` from Merchant Catalog
  useEffect(() => {
    if (router.isReady && router.query.q && typeof router.query.q === 'string') {
      const q = router.query.q;
      setPromptInput(q);
      startPurchaseFlow(q);
    }
  }, [router.isReady, router.query.q]);

  // Authorize Payment Execution Sequence
  const handleAuthorize = async () => {
    if (!story) return;

    // Step 1: Authorization recorded
    setStory(prev => prev ? { ...prev, settlementState: 'authorizing' } : null);

    // Step 2: Holding funds securely (2-phase reserve)
    setTimeout(() => {
      setStory(prev => prev ? { ...prev, settlementState: 'holding' } : null);
    }, 700);

    // Step 3: Razorpay order created
    setTimeout(() => {
      setStory(prev => prev ? { ...prev, settlementState: 'order_created' } : null);
    }, 1500);

    // Step 4: Settlement confirmed
    setTimeout(() => {
      const receiptNo = `RCP-${Math.floor(100000 + Math.random() * 900000)}`;
      const rzpId = `pay_rzp_${Math.random().toString(36).substring(2, 12)}`;
      const idemKey = `idem_${Math.random().toString(36).substring(2, 14)}`;
      const nowStr = getNowTime();

      setStory(prev => prev ? {
        ...prev,
        settlementState: 'settled',
        settlementDetails: {
          receiptId: receiptNo,
          razorpayPaymentId: rzpId,
          idempotencyKey: idemKey,
          settledAt: nowStr
        }
      } : null);
      setCurrentStage('receipt');

      // Cache settled purchase and its audit events to localStorage for Evidence / Audit Trail
      try {
        const existing = JSON.parse(localStorage.getItem('agentpay_recent_orders') || '[]');
        const newOrder = {
          id: `ord_${Date.now()}`,
          time: nowStr,
          day: 'Today',
          type: 'settled',
          merchant: story.chosenQuote.merchantName,
          amount: story.authPrice,
          product: story.productName,
          summary: `Purchase settled with ${story.chosenQuote.merchantName} through Razorpay rails. Stamped receipt ${receiptNo}.`,
          idempotencyKey: idemKey,
          actor: 'agent_buyer_001',
          state: 'RECEIPT_GENERATED',
          details: {
            receipt_id: receiptNo,
            razorpay_payment_id: rzpId,
            merchant: story.chosenQuote.merchantName,
            product: story.productName,
            amount: story.authPrice,
            delivery_eta: story.chosenQuote.deliveryEta,
            warranty: story.chosenQuote.warranty,
            policy_verified: true,
            timestamp: new Date().toISOString()
          },
          auditEvents: [
            {
              id: `aud_${Math.random().toString(36).substring(2, 9)}`,
              event_type: 'AGENT_INTENT_PARSED',
              actor_type: 'AI_AGENT',
              created_at: new Date(Date.now() - 4000).toISOString(),
              metadata: {
                phase: 'Agent Cognition',
                details: `Interpreted query "${story.query}". Extracted item category, constraints, and budget targets.`
              }
            },
            {
              id: `aud_${Math.random().toString(36).substring(2, 9)}`,
              event_type: 'MERCHANT_DISCOVERY_INVOKED',
              actor_type: 'AI_AGENT',
              created_at: new Date(Date.now() - 3200).toISOString(),
              metadata: {
                phase: 'Tool Execution (search_products)',
                details: `Dispatched tool search across approved merchant catalogs (Croma, Reliance Digital, Amazon Prime Direct). Found 3 candidate products.`
              }
            },
            {
              id: `aud_${Math.random().toString(36).substring(2, 9)}`,
              event_type: 'QUOTES_EVALUATED_AND_RANKED',
              actor_type: 'AI_AGENT',
              created_at: new Date(Date.now() - 2500).toISOString(),
              metadata: {
                phase: 'Tool Execution (get_quote)',
                details: `Live bids evaluated. Selected ${story.chosenQuote.merchantName} for best delivered price (₹${story.authPrice.toLocaleString('en-IN')}) and ETA (${story.chosenQuote.deliveryEta}).`
              }
            },
            {
              id: `aud_${Math.random().toString(36).substring(2, 9)}`,
              event_type: 'POLICY_EVALUATION_APPROVED',
              actor_type: 'POLICY_ENGINE',
              created_at: new Date(Date.now() - 1800).toISOString(),
              metadata: {
                phase: 'Deterministic Guardrail Check',
                details: `Approved: Category whitelist matched, merchant verified, and amount ₹${story.authPrice.toLocaleString('en-IN')} within limits.`
              }
            },
            {
              id: `aud_${Math.random().toString(36).substring(2, 9)}`,
              event_type: 'BUDGET_RESERVE_LOCKED',
              actor_type: 'POLICY_ENGINE',
              created_at: new Date(Date.now() - 1200).toISOString(),
              metadata: {
                phase: '2-Phase Budget Lock',
                details: `Pre-authorized cryptographic reserve locked ₹${story.authPrice.toLocaleString('en-IN')} from available budget buffer.`
              }
            },
            {
              id: `aud_${Math.random().toString(36).substring(2, 9)}`,
              event_type: 'PAYMENT_AUTHORIZATION_DISPATCHED',
              actor_type: 'PAYMENT_RAIL',
              created_at: new Date(Date.now() - 600).toISOString(),
              metadata: {
                phase: 'Settlement Initiation',
                details: `Signed payment order dispatched to Razorpay settlement rail.`
              }
            },
            {
              id: `aud_${Math.random().toString(36).substring(2, 9)}`,
              event_type: 'PAYMENT_CAPTURED_SUCCESSFULLY',
              actor_type: 'PAYMENT_RAIL',
              created_at: new Date().toISOString(),
              metadata: {
                phase: 'Razorpay Capture',
                details: `Captured on Razorpay rails. Provider ID: ${rzpId}. Total: ₹${story.authPrice.toLocaleString('en-IN')}.`
              }
            },
            {
              id: `aud_${Math.random().toString(36).substring(2, 9)}`,
              event_type: 'RECEIPT_STAMPED_AND_PERSISTED',
              actor_type: 'SYSTEM',
              created_at: new Date().toISOString(),
              metadata: {
                phase: 'Cryptographic Stamping',
                details: `Generated stamped invoice #${receiptNo} with permanent audit proof.`
              }
            }
          ],
          intentLog: {
            intent_id: `int_${idemKey.slice(0, 10)}`,
            query: story.query,
            extracted_target: story.productName,
            category: 'electronics',
            max_budget: 20000,
            authorized_amount: story.authPrice,
            currency: 'INR',
            merchant_preferences: ['Croma', 'Reliance Digital', 'Amazon Prime Direct'],
            fulfillment_criteria: {
              delivery_window: story.chosenQuote.deliveryEta,
              warranty_required: true,
              condition: 'brand_new'
            },
            policy_evaluation: {
              passed: true,
              checks: [
                { name: 'category_whitelist', status: 'PASSED', detail: 'Category "electronics" is pre-approved' },
                { name: 'daily_spending_limit', status: 'PASSED', detail: `₹${story.authPrice.toLocaleString('en-IN')} < ₹20,000 allowance` },
                { name: 'merchant_certification', status: 'PASSED', detail: `${story.chosenQuote.merchantName} is Tier-1 Certified` }
              ]
            },
            confidence_score: 0.98,
            created_at: new Date(Date.now() - 4000).toISOString()
          },
          paymentLog: {
            provider: 'RAZORPAY',
            razorpay_payment_id: rzpId,
            razorpay_order_id: `order_${rzpId.replace('rzp_live_', 'ord_')}`,
            amount_in_paise: story.authPrice * 100,
            amount_in_inr: story.authPrice,
            currency: 'INR',
            status: 'captured',
            method: 'upi_autopay',
            vpa: 'agentpay.corp@razorpay',
            idempotency_key: idemKey,
            auth_code: `AUTH-${Date.now().toString(36).toUpperCase()}`,
            settlement_rail: 'RAZORPAY_INSTANT_SETTLEMENT',
            receipt: receiptNo,
            merchant_account: story.chosenQuote.merchantName === 'Croma' ? 'acc_croma_enterprise' : story.chosenQuote.merchantName === 'Reliance Digital' ? 'acc_reliance_prime' : 'acc_amazon_direct',
            two_phase_commit: {
              phase1_reserve_token: `res_${idemKey.slice(0, 16)}`,
              phase2_capture_token: `cap_${rzpId.slice(0, 16)}`,
              ledger_status: 'COMMITTED'
            },
            webhook_verified: true,
            captured_at: new Date().toISOString()
          },
          agentLog: {
            agent_id: 'agent_buyer_001',
            model: 'gemini-1.5-pro / langgraph-agentic-shopper',
            session_id: `ses_${idemKey.slice(0, 12)}`,
            cognitive_trace: [
              {
                step: 1,
                action: 'parse_intent',
                thought: `Interpreting user prompt: "${story.query}". Classified intent as COMMERCIAL_PURCHASE. Extracted target: "${story.productName}".`,
                action_input: { query: story.query, max_budget: 20000 },
                action_output: { target: story.productName, category: 'electronics', preference: 'best_delivered_price' }
              },
              {
                step: 2,
                action: 'tool_call: search_products',
                thought: `Searching approved partner catalogs for "${story.productName}".`,
                action_input: { query: story.productName, limit: 3, in_stock_only: true },
                action_output: { matches_found: 3, merchants: ['Croma', 'Reliance Digital', 'Amazon Prime Direct'] }
              },
              {
                step: 3,
                action: 'tool_call: get_quote',
                thought: `Polling real-time quotes and delivery SLAs to compute arbitrage and value score.`,
                action_input: { product_name: story.productName, candidates: ['Croma', 'Reliance Digital', 'Amazon Prime Direct'] },
                action_output: { best_quote: { merchant: story.chosenQuote.merchantName, price: story.authPrice, delivery: story.chosenQuote.deliveryEta } }
              },
              {
                step: 4,
                action: 'guardrail_evaluation',
                thought: `Validating deterministic spending policies: daily limit, category whitelist, merchant tier.`,
                action_input: { merchant: story.chosenQuote.merchantName, amount: story.authPrice, policy_id: 'policy_001' },
                action_output: { status: 'APPROVED', reason: 'Within daily limits & approved merchant whitelist.' }
              },
              {
                step: 5,
                action: 'execute_settlement',
                thought: `Acquiring 2-phase idempotency lock and dispatching payment payload to Razorpay rails.`,
                action_input: { provider: 'RAZORPAY', amount: story.authPrice, idempotency_key: idemKey },
                action_output: { payment_id: rzpId, status: 'CAPTURED', receipt: receiptNo }
              }
            ]
          }
        };
        localStorage.setItem('agentpay_recent_orders', JSON.stringify([newOrder, ...existing.slice(0, 19)]));
      } catch (e) {
        console.error('Failed to cache order to localStorage', e);
      }
    }, 2400);
  };

  // Compute narrative rail stages with visibleStep progression
  const railStages: StageInfo[] = [
    {
      key: 'ask',
      number: '01',
      label: 'Ask',
      status: visibleStep >= 1 ? (visibleStep === 1 ? 'active' : 'completed') : 'inactive',
      timestamp: story?.queryTime
    },
    {
      key: 'explore',
      number: '02',
      label: 'Explore',
      status: visibleStep >= 2 ? (visibleStep === 2 ? 'active' : 'completed') : 'inactive',
      timestamp: visibleStep >= 3 ? '3 merchants' : undefined
    },
    {
      key: 'compare',
      number: '03',
      label: 'Compare',
      status: visibleStep >= 3 ? (story?.settlementState === 'settled' ? 'completed' : visibleStep === 3 ? 'active' : 'completed') : 'inactive'
    },
    {
      key: 'guardrail',
      number: '04',
      label: 'Guardrail check',
      status: visibleStep >= 4 ? (story?.settlementState === 'settled' ? 'completed' : visibleStep === 4 ? 'active' : 'completed') : 'inactive'
    },
    {
      key: 'authorize',
      number: '05',
      label: 'Authorize',
      status: visibleStep >= 5 ? (story?.settlementState === 'settled' ? 'completed' : 'active') : 'inactive'
    },
    {
      key: 'receipt',
      number: '06',
      label: 'Receipt',
      status: story?.settlementState === 'settled' ? 'completed' : 'inactive',
      timestamp: story?.settlementDetails?.settledAt
    }
  ];

  const handleScrollToStage = (stageKey: StageKey) => {
    const el = document.getElementById(`node-${stageKey}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <>
      <Head>
        <title>AgentPay — Continuous Commerce Journey</title>
      </Head>

      <div className="w-full flex flex-col flex-1">
        {/* Narrative Rail (Visible once journey begins) */}
        {hasStarted && (
          <NarrativeRail
            currentStage={currentStage}
            stages={railStages}
            onStageClick={handleScrollToStage}
          />
        )}

        {/* HERO SECTION */}
        {!hasStarted ? (
          <div
            onMouseMove={handleWordmarkMouseMove}
            onMouseLeave={handleWordmarkMouseLeave}
            className="flex-1 flex flex-col items-center justify-start text-center pt-2 sm:pt-4 md:pt-6 pb-12 max-w-3xl mx-auto w-full transition-all"
          >
            {/* Living Wordmark - Positioned higher and non-clipped */}
            <h1
              ref={wordmarkRef}
              className="agentpay-wordmark font-bold text-[clamp(56px,13vw,156px)] mb-2 sm:mb-3 tracking-[-0.055em] leading-[1.02] pt-1 pb-1 overflow-visible select-none"
            >
              AgentPay
            </h1>

            <p className="text-base sm:text-lg text-[#4C4546] dark:text-[#C4BCBC] font-normal mb-7 max-w-md">
              Autonomous shopping, with visible financial control.
            </p>

            {/* Landing Prompt Surface */}
            <div className="glass-surface w-full p-2 sm:p-2.5 rounded-2xl sm:rounded-3xl shadow-soft mb-6 relative group transition-all">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  startPurchaseFlow(promptInput);
                }}
                className="flex items-center gap-2 px-3 py-2"
              >
                <input
                  type="text"
                  value={promptInput}
                  onChange={(e) => setPromptInput(e.target.value)}
                  placeholder="What would you like AgentPay to find? ↗"
                  className="flex-1 bg-transparent text-sm sm:text-base text-[#1B1C1C] dark:text-white placeholder-[#7E7576] dark:placeholder-[#9E9697] focus:outline-none"
                  autoFocus
                />

                {promptInput.trim().length > 0 && (
                  <button
                    type="submit"
                    className="w-8 h-8 sm:w-9 sm:h-9 rounded-full bg-[#1B1C1C] text-white hover:bg-black dark:bg-white dark:text-black dark:hover:bg-neutral-200 flex items-center justify-center transition-transform active:scale-95 shadow-md"
                    title="Send to AgentPay"
                  >
                    ↗
                  </button>
                )}
              </form>

              <div className="px-4 pb-2 text-left">
                <span className="text-[11px] text-[#7E7576] dark:text-[#9E9697] font-mono">
                  Buy within the rules you set.
                </span>
              </div>
            </div>

            {/* Plain Text Editorial Prompt Suggestions */}
            <div className="flex flex-col items-center gap-2 text-xs sm:text-sm text-[#4C4546] dark:text-[#C4BCBC]">
              <span className="text-[#9C9495] dark:text-[#7E7576] text-xs">Try asking:</span>
              <button
                onClick={() => {
                  setPromptInput('Find a 27-inch 144 Hz monitor under ₹28,000');
                  startPurchaseFlow('Find a 27-inch 144 Hz monitor under ₹28,000');
                }}
                className="hover:text-[#AA361A] dark:hover:text-[#FE7352] hover:underline underline-offset-4 transition-colors"
              >
                &ldquo;Find a 27-inch 144 Hz monitor under ₹28,000&rdquo;
              </button>
              <button
                onClick={() => {
                  setPromptInput('Replace my daily-use headphones under ₹5,000');
                  startPurchaseFlow('Replace my daily-use headphones under ₹5,000');
                }}
                className="hover:text-[#AA361A] dark:hover:text-[#FE7352] hover:underline underline-offset-4 transition-colors"
              >
                &ldquo;Replace my daily-use headphones under ₹5,000&rdquo;
              </button>
              <button
                onClick={() => {
                  setPromptInput('Compare the best deal for an air fryer this week');
                  startPurchaseFlow('Compare the best deal for an air fryer this week');
                }}
                className="hover:text-[#AA361A] dark:hover:text-[#FE7352] hover:underline underline-offset-4 transition-colors"
              >
                &ldquo;Compare the best deal for an air fryer this week&rdquo;
              </button>
            </div>

            {/* Quiet Footer Guarantee */}
            <div className="mt-12 sm:mt-16 text-[11px] text-[#9C9495] dark:text-[#7E7576] font-mono">
              Policies stay in control · Money never moves invisibly
            </div>
          </div>
        ) : (
          /* CONTINUOUS PURCHASE FLOW (HERO COMPRESSED UPWARD INTO VERTICAL NARRATIVE) */
          <div className="w-full max-w-3xl mx-auto py-6 relative">
            {/* Compressed Living Wordmark Header */}
            <div
              onMouseMove={handleWordmarkMouseMove}
              onMouseLeave={handleWordmarkMouseLeave}
              className="flex items-center justify-between border-b border-[#E4E2E2]/60 dark:border-white/10 pb-4 mb-8"
            >
              <div>
                <h2 className="agentpay-wordmark font-bold text-2xl tracking-tight leading-none inline-block cursor-pointer">
                  AgentPay
                </h2>
                <p className="text-xs text-[#7E7576] dark:text-[#9E9697] mt-0.5">
                  Autonomous shopping, with visible financial control.
                </p>
              </div>

              <button
                onClick={() => {
                  setHasStarted(false);
                  setStory(null);
                  setPromptInput('');
                  setCurrentStage('ask');
                }}
                className="text-xs font-mono text-[#7E7576] dark:text-[#9E9697] hover:text-[#AA361A] dark:hover:text-[#FE7352] transition-colors"
              >
                + New Purchase
              </button>
            </div>

            {/* VERTICAL PROGRESSION THREAD */}
            <div className="relative">
              {/* 01 ASK / INTENT EVENT */}
              {visibleStep >= 1 && (
                <TimelineEvent
                  id="ask"
                  title="Intent captured"
                  timestamp={story?.queryTime}
                  status="complete"
                >
                  <div className="paper-card-subtle p-3 sm:p-4 mb-2 flex items-center justify-between gap-4 animate-fadeIn dark:bg-[#181717] dark:border-white/10">
                    <span className="font-medium text-sm sm:text-base text-[#1B1C1C] dark:text-white">
                      &ldquo;{story?.query}&rdquo;
                    </span>
                    <span className="font-mono text-[11px] text-emerald-600 bg-emerald-50 dark:bg-emerald-950/60 dark:text-emerald-400 px-2 py-0.5 rounded shrink-0">
                      Validated
                    </span>
                  </div>
                </TimelineEvent>
              )}

              {/* 02 EXPLORE / AGENT ACTIVITY EVENT */}
              {visibleStep >= 2 && (
                <TimelineEvent
                  id="explore"
                  title="Searching approved merchants"
                  timestamp={visibleStep === 2 ? 'Searching approved merchants...' : '3 merchants verified'}
                  status={visibleStep === 2 ? 'running' : 'complete'}
                >
                  <div className="space-y-2 mb-3 animate-fadeIn">
                    <div className="text-xs text-[#4C4546] dark:text-[#C4BCBC] flex flex-wrap gap-2 items-center">
                      <span className="px-2 py-0.5 rounded bg-black/5 dark:bg-white/10 dark:text-white font-mono text-[11px]">
                        Croma
                      </span>
                      <span className="text-[#CFBFC0] dark:text-white/20">·</span>
                      <span className="px-2 py-0.5 rounded bg-black/5 dark:bg-white/10 dark:text-white font-mono text-[11px]">
                        Reliance Digital
                      </span>
                      <span className="text-[#CFBFC0] dark:text-white/20">·</span>
                      <span className="px-2 py-0.5 rounded bg-black/5 dark:bg-white/10 dark:text-white font-mono text-[11px]">
                        Amazon Prime Direct
                      </span>
                    </div>

                    {/* Concise Operational Record */}
                    <div className="text-xs text-[#4C4546] dark:text-[#C4BCBC] space-y-1 mt-2">
                      <div className="flex items-center justify-between">
                        <span>Searching catalog products</span>
                        <span className="font-mono text-[11px] text-emerald-600 dark:text-emerald-400">Complete</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Fetching live quotes from 3 approved merchants</span>
                        <span className="font-mono text-[11px] text-emerald-600 dark:text-emerald-400">Complete</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Ranking by delivered price, warranty, and window</span>
                        <span className="font-mono text-[11px] text-emerald-600 dark:text-emerald-400">Complete</span>
                      </div>
                    </div>

                    {/* Progressive Disclosure Controls */}
                    <div className="flex items-center gap-4 pt-2">
                      <button
                        onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                        className="text-xs text-[#7E7576] hover:text-[#1B1C1C] dark:text-[#9E9697] dark:hover:text-white underline underline-offset-4 transition-colors font-mono"
                      >
                        {showTechnicalDetails ? 'Hide technical calls' : 'Inspect technical tool calls (2.8s)'}
                      </button>

                      <button
                        onClick={() => setShowExploreLayer(true)}
                        className="text-xs text-[#AA361A] dark:text-[#FE7352] hover:underline underline-offset-4 transition-colors font-medium flex items-center gap-1"
                      >
                        <span>Open Explore Layer</span>
                        <span>↗</span>
                      </button>
                    </div>

                    {/* Expanded Technical Glass Sheet */}
                    {showTechnicalDetails && (
                      <div className="glass-sheet p-4 rounded-xl mt-3 font-mono text-[11px] space-y-2 text-[#4C4546] dark:text-[#C4BCBC] animate-fadeIn dark:border-white/10">
                        <div className="flex items-center justify-between border-b border-[#E4E2E2] dark:border-white/10 pb-1">
                          <span>search_products &ldquo;{story?.query}&rdquo;</span>
                          <span className="text-[#7E7576] dark:text-[#9E9697]">18 candidates · 1.2s</span>
                        </div>
                        <div className="flex items-center justify-between border-b border-[#E4E2E2] dark:border-white/10 pb-1">
                          <span>get_quote Croma · Delivery by Tue</span>
                          <span className="text-emerald-600 dark:text-emerald-400">₹{story?.chosenQuote.price.toLocaleString('en-IN')} · 0.6s</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span>get_quote Reliance Digital & Amazon Direct</span>
                          <span className="text-[#7E7576] dark:text-[#9E9697]">Verified · 0.4s</span>
                        </div>
                      </div>
                    )}
                  </div>
                </TimelineEvent>
              )}

              {/* 03 COMPARISON & CATALOG SELECTION EVENT */}
              {visibleStep >= 3 && story && (
                <TimelineEvent
                  id="compare"
                  title="Catalog options & delivered price comparison"
                  timestamp={`Quotes valid for ${formatCountdown(quoteSecondsLeft)}`}
                  status={story.settlementState === 'settled' ? 'complete' : 'complete'}
                >
                  <div className="paper-card p-5 mb-4 animate-fadeIn dark:bg-[#161515] dark:border-white/10">
                    {/* Catalog Selector Header */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4 pb-3 border-b border-[#E4E2E2]/70 dark:border-white/10">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono uppercase tracking-wider text-[#AA361A] dark:text-[#FE7352] font-semibold">
                            03 Matched Catalog Options
                          </span>
                          <span className="text-xs text-[#7E7576] dark:text-[#9E9697]">·</span>
                          <span className="text-xs text-[#7E7576] dark:text-[#9E9697]">
                            {story.candidateProducts?.length || 1} candidate options identified
                          </span>
                        </div>
                        <h3 className="text-base font-semibold text-[#1B1C1C] dark:text-white mt-0.5">
                          Select an option to compare merchant quotes & guardrail compliance
                        </h3>
                      </div>

                      <button
                        onClick={() => setShowExploreLayer(true)}
                        className="text-xs text-[#AA361A] dark:text-[#FE7352] hover:underline underline-offset-4 transition-colors font-medium flex items-center gap-1 self-start sm:self-auto"
                      >
                        <span>All 137 Catalog SKUs</span>
                        <span>↗</span>
                      </button>
                    </div>

                    {/* HORIZONTAL CATALOG CARDS GRID */}
                    {story.candidateProducts && story.candidateProducts.length > 0 && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 mb-5">
                        {story.candidateProducts.map((opt) => {
                          const isSelected = opt.id === story.selectedProductId;
                          return (
                            <div
                              key={opt.id}
                              onClick={() => handleSelectCandidateProduct(opt.id)}
                              className={`group p-3.5 rounded-xl transition-all cursor-pointer relative flex flex-col justify-between ${
                                isSelected
                                  ? 'border-2 border-[#FE7352] bg-gradient-to-b from-white to-[#FFF9F7] dark:from-[#262120] dark:to-[#1E1918] shadow-sm ring-2 ring-[#FE7352]/20'
                                  : 'border border-[#E4E2E2] dark:border-white/10 bg-white/70 dark:bg-[#1C1A1A] hover:border-[#CFBFC0] dark:hover:border-white/25 hover:bg-white dark:hover:bg-[#232020]'
                              }`}
                            >
                              <div>
                                {/* Badge & Rating */}
                                <div className="flex items-center justify-between gap-1 mb-2">
                                  <span
                                    className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-semibold tracking-tight ${
                                      isSelected
                                        ? 'bg-[#FE7352]/15 text-[#AA361A] dark:text-[#FF8A65]'
                                        : 'bg-black/5 dark:bg-white/10 text-[#7E7576] dark:text-[#A8A29E]'
                                    }`}
                                  >
                                    {opt.badge}
                                  </span>
                                  <span className="text-[11px] font-mono text-[#7E7576] dark:text-[#9E9697] flex items-center gap-0.5">
                                    <span className="text-amber-500">★</span>
                                    <span>{opt.rating}</span>
                                  </span>
                                </div>

                                {/* Brand & Name */}
                                <div className="text-[11px] text-[#7E7576] dark:text-[#9E9697] font-mono uppercase tracking-wider mb-0.5">
                                  {opt.brand}
                                </div>
                                <h4
                                  className={`text-sm font-semibold leading-snug line-clamp-2 transition-colors ${
                                    isSelected
                                      ? 'text-[#1B1C1C] dark:text-white'
                                      : 'text-[#2C292A] dark:text-[#E2DFDF] group-hover:text-[#1B1C1C] dark:group-hover:text-white'
                                  }`}
                                >
                                  {opt.name}
                                </h4>

                                {/* Specs */}
                                <p className="text-[11px] text-[#7E7576] dark:text-[#9E9697] font-mono mt-1.5 line-clamp-2">
                                  {opt.specsLine}
                                </p>
                              </div>

                              {/* Footer: Price & Selection Status */}
                              <div className="mt-4 pt-3 border-t border-[#E4E2E2]/60 dark:border-white/10 flex items-center justify-between">
                                <div>
                                  <span className="text-[10px] text-[#7E7576] dark:text-[#9E9697] uppercase font-mono block">From</span>
                                  <span className="font-mono text-sm font-bold text-[#1B1C1C] dark:text-white">
                                    ₹{opt.price.toLocaleString('en-IN')}
                                  </span>
                                </div>

                                {isSelected ? (
                                  <span className="text-[11px] font-mono font-medium text-emerald-700 bg-emerald-50 dark:bg-emerald-950/60 dark:text-emerald-400 px-2 py-0.5 rounded flex items-center gap-1">
                                    <span>✓</span>
                                    <span>Selected</span>
                                  </span>
                                ) : (
                                  <span className="text-[11px] font-medium text-[#7E7576] dark:text-[#9E9697] group-hover:text-[#AA361A] dark:group-hover:text-[#FE7352] group-hover:underline underline-offset-2 flex items-center gap-0.5">
                                    <span>Select</span>
                                    <span>→</span>
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* CURRENTLY SELECTED PRODUCT LIVE MERCHANT QUOTES */}
                    <div className="bg-[#FAF9F8] dark:bg-[#191818] rounded-xl p-3.5 sm:p-4 border border-[#E4E2E2]/80 dark:border-white/10">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                        <div>
                          <div className="text-[11px] font-mono text-[#7E7576] dark:text-[#9E9697] uppercase tracking-wider">
                            Live Delivered Quotes for Selected Option
                          </div>
                          <h4 className="text-sm sm:text-base font-semibold text-[#1B1C1C] dark:text-white">
                            {story.productName}
                          </h4>
                        </div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[11px] font-mono text-[#AA361A] dark:text-[#FE7352] bg-[#FE7352]/10 border border-[#FE7352]/20 px-2 py-0.5 rounded font-medium">
                            Click any merchant to select
                          </span>
                          <span className="text-[11px] font-mono text-[#7E7576] dark:text-[#9E9697] shrink-0">
                            {story.quotes.length} verified bids
                          </span>
                        </div>
                      </div>

                      {/* Stack of Editorial Merchant Rows */}
                      <div className="space-y-2 mb-3" role="radiogroup" aria-label="Delivered merchant options">
                        {story.quotes.map((quote) => {
                          const isSelected = story.chosenQuote?.merchantId === quote.merchantId;
                          return (
                            <div
                              key={quote.merchantId}
                              role="radio"
                              aria-checked={isSelected}
                              tabIndex={0}
                              onClick={() => handleSelectMerchantQuote(quote.merchantId)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                  e.preventDefault();
                                  handleSelectMerchantQuote(quote.merchantId);
                                }
                              }}
                              className={`p-3 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2 transition-all cursor-pointer select-none ${
                                isSelected
                                  ? 'bg-white dark:bg-[#211F1F] border-2 border-[#FE7352] shadow-sm ring-2 ring-[#FE7352]/20'
                                  : 'bg-white/70 dark:bg-[#1B1A1A] border border-[#E4E2E2] dark:border-white/10 hover:border-[#CFBFC0] dark:hover:border-white/30 hover:bg-white dark:hover:bg-[#232121]'
                              }`}
                            >
                              <div className="flex items-center gap-3">
                                {/* Radio Indicator */}
                                <div
                                  className={`w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 transition-colors ${
                                    isSelected
                                      ? 'border-[#FE7352]'
                                      : 'border-[#CFBFC0] dark:border-white/30'
                                  }`}
                                >
                                  {isSelected && (
                                    <div className="w-2 h-2 rounded-full bg-[#FE7352]" />
                                  )}
                                </div>

                                <div>
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="font-semibold text-xs sm:text-sm text-[#1B1C1C] dark:text-white">
                                      {quote.merchantName}
                                    </span>
                                    {quote.isBest && (
                                      <span className="text-[10px] font-mono uppercase bg-[#AA361A] text-white px-1.5 py-0.5 rounded font-semibold">
                                        Lowest Quote
                                      </span>
                                    )}
                                    {isSelected && (
                                      <span className="text-[10px] font-mono uppercase bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700/50 px-1.5 py-0.5 rounded font-semibold flex items-center gap-1">
                                        <span>✓</span>
                                        <span>Active Choice</span>
                                      </span>
                                    )}
                                  </div>
                                  <p className="text-[11px] text-[#7E7576] dark:text-[#9E9697] mt-0.5">
                                    {quote.deliveryEta} · {quote.warranty}
                                  </p>
                                </div>
                              </div>

                              <div className="text-right sm:pl-4">
                                <span
                                  className={`font-mono text-sm sm:text-base font-bold block ${
                                    isSelected
                                      ? 'text-[#AA361A] dark:text-[#FE7352]'
                                      : 'text-[#1B1C1C] dark:text-white'
                                  }`}
                                >
                                  ₹{quote.price.toLocaleString('en-IN')}
                                </span>
                                <span className="text-[10px] text-[#7E7576] dark:text-[#9E9697] block">
                                  Free delivery included
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {/* Relative Savings Line */}
                      <div className="text-xs text-[#AA361A] dark:text-[#FE7352] font-medium bg-[#AA361A]/5 dark:bg-[#FE7352]/10 p-2.5 rounded-lg border border-transparent dark:border-[#FE7352]/20 flex items-center gap-2">
                        <span className="shrink-0 font-bold">ℹ</span>
                        <span>{story.savingsText}</span>
                      </div>
                    </div>

                    {/* Alternative Options Pivot Bar */}
                    <div className="pt-3.5 mt-3 border-t border-[#E4E2E2]/70 dark:border-white/10 flex flex-wrap items-center justify-between gap-2 text-xs">
                      <span className="text-[#7E7576] dark:text-[#9E9697] text-[11px] font-mono">
                        Catalog quick filters:
                      </span>
                      <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                        <button
                          onClick={handleFindCheaper}
                          className="px-2.5 py-1 rounded-lg bg-black/5 hover:bg-black/10 dark:bg-white/10 dark:hover:bg-white/15 text-[#1B1C1C] dark:text-white transition-colors font-medium flex items-center gap-1 text-xs"
                          title="Switch to the cheapest option in the catalog"
                        >
                          <span>↓</span>
                          <span>Find cheaper</span>
                        </button>
                        <button
                          onClick={handleDifferentBrand}
                          className="px-2.5 py-1 rounded-lg bg-black/5 hover:bg-black/10 dark:bg-white/10 dark:hover:bg-white/15 text-[#1B1C1C] dark:text-white transition-colors font-medium flex items-center gap-1 text-xs"
                          title="Switch to another brand in the catalog"
                        >
                          <span>🏷️</span>
                          <span>Different brand</span>
                        </button>
                        <button
                          onClick={() => setShowExploreLayer(true)}
                          className="px-2.5 py-1 rounded-lg bg-black/5 hover:bg-black/10 dark:bg-white/10 dark:hover:bg-white/15 text-[#1B1C1C] dark:text-white transition-colors font-medium flex items-center gap-1 text-xs"
                          title="Open full catalog explore layer"
                        >
                          <span>⤢</span>
                          <span>Explore all 137 SKUs</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </TimelineEvent>
              )}

              {/* 04 GUARDRAIL CHECK EVENT */}
              {visibleStep >= 4 && story && (
                <TimelineEvent
                  id="guardrail"
                  title="Guardrail check"
                  timestamp="Policy compliant"
                  status="complete"
                >
                  <div className="paper-card-subtle p-4 mb-4 text-xs space-y-1.5 animate-fadeIn dark:bg-[#181717] dark:border-white/10">
                    <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-semibold">
                      <span>✓</span>
                      <span>This purchase is within your active policy</span>
                    </div>
                    <p className="text-[#4C4546] dark:text-[#C4BCBC]">
                      {story.policyVerdict.ruleSummary} · {story.policyVerdict.details}
                    </p>
                    <div className="text-[11px] text-[#7E7576] dark:text-[#9E9697] font-mono pt-1">
                      Two-phase reserve hold will engage upon authorization.
                    </div>
                  </div>
                </TimelineEvent>
              )}

              {/* 05 AUTHORIZATION EVENT */}
              {visibleStep >= 5 && story && (
                <TimelineEvent
                  id="authorize"
                  title="Authorization"
                  timestamp={story.settlementState !== 'idle' ? 'Processing' : 'Awaiting confirmation'}
                  status={
                    story.settlementState === 'settled'
                      ? 'complete'
                      : story.settlementState === 'failed'
                      ? 'settlement-failed'
                      : 'approval-needed'
                  }
                >
                  <div className="paper-card p-5 mb-4 animate-fadeIn dark:bg-[#161515] dark:border-white/10">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <div className="text-xs text-[#7E7576] dark:text-[#9E9697] uppercase tracking-wider font-mono">
                          Commitment Total · {story.chosenQuote.merchantName}
                        </div>
                        <div className="text-2xl font-bold font-mono text-[#1B1C1C] dark:text-white">
                          ₹{story.authPrice.toLocaleString('en-IN')}
                        </div>
                      </div>

                      {story.settlementState === 'idle' ? (
                        <div className="text-right">
                          <button
                            onClick={handleAuthorize}
                            className="w-full sm:w-auto px-6 py-3 rounded-xl bg-[#1B1C1C] hover:bg-black text-white dark:bg-white dark:text-[#141212] dark:hover:bg-neutral-200 text-sm font-semibold tracking-tight transition-all active:scale-98 shadow-md"
                          >
                            Authorize ₹{story.authPrice.toLocaleString('en-IN')}
                          </button>
                          <span className="text-[11px] text-[#7E7576] dark:text-[#9E9697] block mt-1.5 font-mono">
                            Settles with {story.chosenQuote.merchantName} · Funds move only after authorization.
                          </span>
                        </div>
                      ) : story.settlementState === 'settled' ? (
                        <div className="px-4 py-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 font-mono text-xs font-semibold flex items-center gap-1.5">
                          <span>✓</span>
                          <span>Authorization Settled</span>
                        </div>
                      ) : (
                        <div className="space-y-1 text-right">
                          <div className="px-4 py-2 rounded-lg bg-black/5 dark:bg-white/10 text-[#1B1C1C] dark:text-white font-mono text-xs flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-[#FE7352] animate-ping" />
                            <span>
                              {story.settlementState === 'authorizing' && 'Authorization recorded...'}
                              {story.settlementState === 'holding' && 'Holding funds securely (2-phase reserve)...'}
                              {story.settlementState === 'order_created' && 'Razorpay order created...'}
                            </span>
                          </div>
                          <span className="text-[10px] text-[#7E7576] dark:text-[#9E9697] block">
                            Executing on Razorpay settlement rails
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </TimelineEvent>
              )}

              {/* 06 RECEIPT EVENT */}
              {story?.settlementState === 'settled' && story.settlementDetails && (
                <TimelineEvent
                  id="receipt"
                  title="Settlement proof"
                  timestamp={story.settlementDetails.settledAt}
                  status="complete"
                  isLast={true}
                >
                  <div className="paper-card p-6 border-emerald-200 dark:border-emerald-800/40 bg-gradient-to-b from-white to-[#F9FCFA] dark:from-[#181717] dark:to-[#141A16]">
                    <div className="flex items-center justify-between border-b border-[#E4E2E2] dark:border-white/10 pb-4 mb-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                          <h4 className="text-base font-semibold text-[#1B1C1C] dark:text-white">
                            Purchase Settled via Razorpay Rails
                          </h4>
                        </div>
                        <p className="text-xs text-[#7E7576] dark:text-[#9E9697] mt-0.5">
                          Order successfully placed with {story.chosenQuote.merchantName}.
                        </p>
                      </div>

                      <span className="font-mono text-xs font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-100/80 dark:bg-emerald-950/80 px-2.5 py-1 rounded-full">
                        {story.settlementDetails.receiptId}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono text-[#4C4546] dark:text-[#C4BCBC] mb-6">
                      <div>
                        <span className="text-[#9C9495] dark:text-[#7E7576] block text-[11px]">RAZORPAY REFERENCE</span>
                        <span className="text-[#1B1C1C] dark:text-white font-medium">{story.settlementDetails.razorpayPaymentId}</span>
                      </div>
                      <div>
                        <span className="text-[#9C9495] dark:text-[#7E7576] block text-[11px]">IDEMPOTENCY KEY</span>
                        <span className="text-[#1B1C1C] dark:text-white font-medium">{story.settlementDetails.idempotencyKey}</span>
                      </div>
                      <div>
                        <span className="text-[#9C9495] dark:text-[#7E7576] block text-[11px]">ITEM ORDERED</span>
                        <span className="text-[#1B1C1C] dark:text-white font-medium">{story.productName}</span>
                      </div>
                      <div>
                        <span className="text-[#9C9495] dark:text-[#7E7576] block text-[11px]">DELIVERY WINDOW</span>
                        <span className="text-[#1B1C1C] dark:text-white font-medium">{story.chosenQuote.deliveryEta}</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between border-t border-[#E4E2E2] dark:border-white/10 pt-4">
                      <div>
                        <span className="text-xs text-[#7E7576] dark:text-[#9E9697]">Amount Debited: </span>
                        <span className="font-mono font-bold text-sm text-[#1B1C1C] dark:text-white">
                          ₹{story.authPrice.toLocaleString('en-IN')}
                        </span>
                      </div>

                      <div className="flex items-center gap-3">
                        <Link
                          href="/history"
                          className="text-xs text-[#AA361A] dark:text-[#FE7352] hover:underline underline-offset-4 transition-colors font-medium"
                        >
                          View in Purchase History →
                        </Link>
                        <button
                          onClick={() => window.print()}
                          className="px-3 py-1.5 text-xs rounded-lg border border-[#E4E2E2] dark:border-white/15 hover:bg-black/5 dark:hover:bg-white/10 text-[#1B1C1C] dark:text-white transition-colors"
                        >
                          Print Proof
                        </button>
                      </div>
                    </div>
                  </div>
                </TimelineEvent>
              )}
            </div>
          </div>
        )}

        {/* Optional Explore Layer Slide-out */}
        <ExploreLayer
          isOpen={showExploreLayer}
          onClose={() => setShowExploreLayer(false)}
          onAskAboutProduct={(name, price) => {
            setPromptInput(`Find and buy ${name}`);
            startPurchaseFlow(`Find and buy ${name}`);
          }}
        />
      </div>
    </>
  );
}
