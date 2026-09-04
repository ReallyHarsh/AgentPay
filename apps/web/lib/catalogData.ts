import { MerchantInfo, CatalogProduct, MerchantQuote } from '@/types/commerce';

/**
 * Deterministically generates realistic merchant quotes for a product.
 * Randomizes availability so that not every merchant stocks every product:
 * - ~40% Single merchant exclusive (only the primary stocking merchant)
 * - ~43% Dual merchant availability (primary merchant + 1 competing merchant)
 * - ~17% Tri-merchant network availability (carried across all 3 certified merchants)
 */
export function buildMerchantQuotes(
  productId: string,
  basePrice: number,
  primaryMerchantId: string = 'merchant_001'
): MerchantQuote[] {
  let hash = 0;
  for (let i = 0; i < productId.length; i++) {
    hash = ((hash << 5) - hash) + productId.charCodeAt(i);
    hash |= 0;
  }
  const posHash = Math.abs(hash);

  const merchantMeta: Record<string, { name: string; fastEta: string; stdEta: string; warranty: string }> = {
    merchant_001: {
      name: 'Croma',
      fastEta: 'Arrives Tomorrow',
      stdEta: 'Arrives in 2 days',
      warranty: 'Official Brand Warranty + Tata Support'
    },
    merchant_002: {
      name: 'Reliance Digital',
      fastEta: 'Express Air Freight (Tomorrow)',
      stdEta: 'Arrives in 2-3 days',
      warranty: 'Manufacturer Sealed Warranty + ResQ Repair'
    },
    merchant_003: {
      name: 'Amazon Prime Direct',
      fastEta: 'Same-Day / Tomorrow by 11 AM',
      stdEta: 'Arrives Thursday',
      warranty: 'A-to-z Authenticity & 7-Day Replacement'
    }
  };

  const validPrimary = merchantMeta[primaryMerchantId] ? primaryMerchantId : 'merchant_001';
  const otherIds = ['merchant_001', 'merchant_002', 'merchant_003'].filter(id => id !== validPrimary);

  const slot = posHash % 10;
  const activeMerchantIds: string[] = [validPrimary];

  if (slot >= 4 && slot <= 7) {
    // 2 merchants: choose one competitor
    const competitorId = ((posHash >> 2) % 2 === 0) ? otherIds[0] : otherIds[1];
    activeMerchantIds.push(competitorId);
  } else if (slot >= 8) {
    // 3 merchants: all carry it
    activeMerchantIds.push(otherIds[0], otherIds[1]);
  }
  // slot 0, 1, 2, 3: Single merchant exclusive!

  const quotes: MerchantQuote[] = activeMerchantIds.map((mId, index) => {
    const meta = merchantMeta[mId];
    if (mId === validPrimary) {
      return {
        merchantId: mId,
        merchantName: meta.name,
        price: basePrice,
        deliveryEta: meta.fastEta,
        warranty: meta.warranty,
        inStock: true,
        isBest: false
      };
    }

    const priceVarianceRatio = ((posHash + index * 7) % 7) - 2;
    const adjustedPrice = Math.round(basePrice * (1 + priceVarianceRatio * 0.015));
    const finalPrice = Math.max(1, adjustedPrice);

    return {
      merchantId: mId,
      merchantName: meta.name,
      price: finalPrice,
      deliveryEta: index === 1 ? meta.stdEta : meta.fastEta,
      warranty: meta.warranty,
      inStock: true,
      isBest: false
    };
  });

  const minPrice = Math.min(...quotes.map(q => q.price));
  for (const q of quotes) {
    if (q.price === minPrice) {
      q.isBest = true;
      break;
    }
  }

  return quotes;
}

export const MERCHANTS: MerchantInfo[] = [
  {
    id: 'merchant_001',
    name: 'Croma Electronics Hub',
    badge: 'Tata Certified Tier-1',
    network: 'Tata Digital Retail Network',
    account: 'acc_croma_enterprise',
    sla: 'Next-Day Priority Delivery',
    slaAdherence: '99.4%',
    rating: 4.9,
    totalOrders: 1420,
    warranty: 'Official Brand Warranty + Tata In-Store Support',
    specialties: ['Apple Authorized', 'Mechanical Keyboards', 'ANC Headphones', 'Premium Laptops'],
    description: 'Direct enterprise retail pipeline for consumer electronics with same-day metro dispatch and authentic warranty registration.',
    accentColor: '#FE7352'
  },
  {
    id: 'merchant_002',
    name: 'Reliance Digital Tech',
    badge: 'Reliance Retail Official',
    network: 'Reliance Retail National Grid',
    account: 'acc_reliance_prime',
    sla: '2-Day Express Air Freight',
    slaAdherence: '98.8%',
    rating: 4.8,
    totalOrders: 980,
    warranty: 'Manufacturer Sealed Warranty + ResQ Repair Support',
    specialties: ['Air Fryers & Kitchen Tech', 'Studio Monitors', 'Home Audio', 'Everyday Computing'],
    description: 'High-availability inventory backed by Reliance ResQ pan-India service centers with direct API catalog synchronization.',
    accentColor: '#0284C7'
  },
  {
    id: 'merchant_003',
    name: 'Amazon Prime Direct',
    badge: 'Prime Direct Certified',
    network: 'Amazon Business Direct Fulfillment',
    account: 'acc_amazon_direct',
    sla: 'Same-Day / Next-Morning Delivery',
    slaAdherence: '99.7%',
    rating: 4.9,
    totalOrders: 2100,
    warranty: 'A-to-z Authenticity & 7-Day Replacement Guarantee',
    specialties: ['Gaming Mice & Keyboards', 'Smart Peripherals', 'Eye-Care Displays', 'Lightweight Laptops'],
    description: 'Automated fulfillment centers guaranteeing rapid autonomous delivery routing and pre-cleared Razorpay business settlement.',
    accentColor: '#F59E0B'
  }
];

export const CATALOG_ITEMS: CatalogProduct[] = [
  // Mice / Input
  {
    id: 'prod_logitech_mx_master',
    name: 'Logitech MX Master 3S Wireless Performance Mouse',
    brand: 'Logitech',
    category: 'accessories',
    categoryLabel: 'Input & Peripherals',
    price: 8995,
    rating: 4.9,
    reviewsCount: 428,
    inStock: true,
    stockCount: 40,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '2 Years Manufacturer Warranty',
    specs: ['8K DPI Track-on-Glass', 'MagSpeed Quiet Clicks', 'USB-C Fast Recharge', 'Flow Cross-Computer Control'],
    description: 'An iconic ergonomic mouse designed for precision workflows and quiet, high-productivity computing.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 15000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 8995, deliveryEta: 'Arrives Tomorrow', warranty: '2 Years Manufacturer Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 9299, deliveryEta: 'Arrives in 2 days', warranty: '2 Years Manufacturer Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 9499, deliveryEta: 'Arrives Thursday', warranty: '2 Years Manufacturer Warranty' }
    ]
  },
  {
    id: 'prod_dell_ms5320w',
    name: 'Dell Premier Multi-Device Wireless Mouse MS5320W',
    brand: 'Dell',
    category: 'accessories',
    categoryLabel: 'Input & Peripherals',
    price: 2999,
    rating: 4.6,
    reviewsCount: 192,
    inStock: true,
    stockCount: 49,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '3 Years Advanced Exchange Warranty',
    specs: ['Dual-Mode 2.4GHz & Bluetooth 5.0', '36-Month Battery Life', '1600 DPI Sensor', 'Programmable Shortcut Buttons'],
    description: 'Seamless multi-device connectivity allowing quick toggling across up to 3 PCs or workstations.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 5000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 2999, deliveryEta: 'Arrives Tomorrow', warranty: '3 Years Advanced Exchange Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 3199, deliveryEta: 'Arrives in 2 days', warranty: '3 Years Advanced Exchange Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 3299, deliveryEta: 'Arrives in 3 days', warranty: '3 Years Advanced Exchange Warranty' }
    ]
  },
  {
    id: 'prod_razer_deathadder',
    name: 'Razer DeathAdder Essential Ergonomic Gaming Mouse',
    brand: 'Razer',
    category: 'accessories',
    categoryLabel: 'Input & Peripherals',
    price: 1499,
    rating: 4.5,
    reviewsCount: 512,
    inStock: true,
    stockCount: 65,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '2 Years Official Razer Warranty',
    specs: ['6,400 DPI Optical Sensor', '5 Hyperesponse Buttons', '10M Click Durability', 'Ergonomic Right-Hand Form'],
    description: 'Trusted esports-grade ergonomic mouse engineered for swift response and enduring comfort.',
    primaryMerchantId: 'merchant_003',
    primaryMerchantName: 'Amazon Prime Direct',
    policyCap: 3000,
    merchantQuotes: [
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 1499, deliveryEta: 'Arrives Tomorrow', warranty: '2 Years Official Razer Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 1699, deliveryEta: 'Arrives in 2 days', warranty: '2 Years Official Razer Warranty' },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 1799, deliveryEta: 'Arrives Wednesday', warranty: '2 Years Official Razer Warranty' }
    ]
  },

  // Keyboards
  {
    id: 'prod_logitech_mx_keys_mini',
    name: 'Logitech MX Keys Mini Minimalist Wireless Illuminated Keyboard',
    brand: 'Logitech',
    category: 'accessories',
    categoryLabel: 'Input & Peripherals',
    price: 8495,
    rating: 4.8,
    reviewsCount: 318,
    inStock: true,
    stockCount: 28,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Manufacturer Warranty',
    specs: ['Perfect Stroke Scissor Keys', 'Smart Backlighting with Hand Proximity', 'Bluetooth Low Energy', 'Compact 75% Layout'],
    description: 'Minimalist form factor with premium spherical-dished keys matching finger shape for effortless typing.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 12000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 8495, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Manufacturer Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 8799, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Manufacturer Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 8999, deliveryEta: 'Arrives Thursday', warranty: '1 Year Manufacturer Warranty' }
    ]
  },
  {
    id: 'prod_keychron_k2_pro',
    name: 'Keychron K2 Pro QMK/VIA Custom Mechanical Keyboard',
    brand: 'Keychron',
    category: 'accessories',
    categoryLabel: 'Input & Peripherals',
    price: 8499,
    rating: 4.9,
    reviewsCount: 284,
    inStock: true,
    stockCount: 19,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Official Warranty',
    specs: ['Full QMK/VIA Key Remapping', 'Hot-Swappable Switches', 'South-Facing RGB', 'Sound Absorbing Acoustic Foam'],
    description: 'Enthusiast wireless mechanical keyboard engineered with Mac and Windows keycaps and open-source firmware.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 12000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 8499, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Official Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 8799, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Official Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 8999, deliveryEta: 'Arrives Thursday', warranty: '1 Year Official Warranty' }
    ]
  },
  {
    id: 'prod_redragon_k552',
    name: 'Redragon K552 Kumara Tenkeyless RGB Mechanical Keyboard',
    brand: 'Redragon',
    category: 'accessories',
    categoryLabel: 'Input & Peripherals',
    price: 2899,
    rating: 4.5,
    reviewsCount: 640,
    inStock: true,
    stockCount: 52,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Official Warranty',
    specs: ['Dust-Proof Red/Blue Switches', 'Aircraft-Grade Aluminum Construction', 'Rainbow Backlit Modes', 'Compact 87-Key Tenkeyless'],
    description: 'Durable and tactile mechanical keyboard built with metal base and responsive mechanical key action.',
    primaryMerchantId: 'merchant_003',
    primaryMerchantName: 'Amazon Prime Direct',
    policyCap: 4000,
    merchantQuotes: [
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 2899, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Official Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 2999, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Official Warranty' },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 3199, deliveryEta: 'Arrives Thursday', warranty: '1 Year Official Warranty' }
    ]
  },

  // Audio / ANC
  {
    id: 'prod_jbl_770nc',
    name: 'JBL Tune 770NC Wireless Adaptive ANC Headphones',
    brand: 'JBL',
    category: 'audio',
    categoryLabel: 'Audio & ANC',
    price: 4499,
    rating: 4.6,
    reviewsCount: 388,
    inStock: true,
    stockCount: 45,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Brand Warranty',
    specs: ['Adaptive Active Noise Cancelling', '70 Hours Battery Life', 'Bluetooth 5.3 with LE Audio', 'JBL Pure Bass Sound'],
    description: 'Lightweight over-ear headphones featuring Smart Ambient mode and up to 70 hours of uninterrupted wireless playback.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 6000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 4499, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Brand Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 4699, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Brand Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 4899, deliveryEta: 'Arrives in 3 days', warranty: '1 Year Brand Warranty' }
    ]
  },
  {
    id: 'prod_sony_wh1000xm5',
    name: 'Sony WH-1000XM5 Flagship Wireless ANC Headphones',
    brand: 'Sony',
    category: 'audio',
    categoryLabel: 'Audio & ANC',
    price: 29990,
    rating: 4.9,
    reviewsCount: 820,
    inStock: true,
    stockCount: 22,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Comprehensive Sony Warranty',
    specs: ['Dual Processor V1 & QN1 ANC', '8 Microphones with AI Noise Reduction', '30 Hours Battery with Fast Charging', 'Hi-Res Audio Wireless LDAC'],
    description: 'Industry-leading noise cancelling with Auto NC Optimizer, calibrated for whisper-quiet travel and studio listening.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 35000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 29990, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Comprehensive Sony Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 30990, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Comprehensive Sony Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 31490, deliveryEta: 'Arrives Wednesday', warranty: '1 Year Comprehensive Sony Warranty' }
    ]
  },
  {
    id: 'prod_sony_whch720n',
    name: 'Sony WH-CH720N Noise Cancelling Wireless Headphones',
    brand: 'Sony',
    category: 'audio',
    categoryLabel: 'Audio & ANC',
    price: 7990,
    rating: 4.7,
    reviewsCount: 310,
    inStock: true,
    stockCount: 30,
    deliveryEta: 'Arrives in 2 days',
    warranty: '1 Year Brand Warranty',
    specs: ['Integrated Processor V1', '35 Hours Battery Life', 'Lightweight 192g Chassis', 'Multipoint Connection'],
    description: 'All-day comfort with balanced sound profile and natural ambient sound capture modes.',
    primaryMerchantId: 'merchant_002',
    primaryMerchantName: 'Reliance Digital',
    policyCap: 10000,
    merchantQuotes: [
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 7990, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Brand Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 8290, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Brand Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 8490, deliveryEta: 'Arrives Thursday', warranty: '1 Year Brand Warranty' }
    ]
  },

  // Displays & Monitors
  {
    id: 'prod_lg_ultragear_27',
    name: 'LG UltraGear 27-inch QHD 144Hz IPS Gaming Monitor',
    brand: 'LG',
    category: 'displays',
    categoryLabel: 'Displays & Monitors',
    price: 24999,
    rating: 4.8,
    reviewsCount: 275,
    inStock: true,
    stockCount: 18,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '3 Years Comprehensive Onsite Warranty',
    specs: ['2560x1440 IPS Panel', '144Hz Refresh Rate', '1ms GtG Response', 'HDR10 & G-SYNC Compatible'],
    description: 'Crisp QHD resolution and wide color gamut for high-speed gaming and accurate creative grading.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 30000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 24999, deliveryEta: 'Arrives Tomorrow', warranty: '3 Years Comprehensive Onsite Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 25499, deliveryEta: 'Arrives in 2 days', warranty: '3 Years Comprehensive Onsite Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 25999, deliveryEta: 'Arrives Wednesday', warranty: '3 Years Comprehensive Onsite Warranty' }
    ]
  },
  {
    id: 'prod_samsung_odyssey_g5',
    name: 'Samsung Odyssey G5 27-inch WQHD 144Hz Curved Gaming Monitor',
    brand: 'Samsung',
    category: 'displays',
    categoryLabel: 'Displays & Monitors',
    price: 21999,
    rating: 4.6,
    reviewsCount: 220,
    inStock: true,
    stockCount: 14,
    deliveryEta: 'Arrives in 2 days',
    warranty: '3 Years Samsung Warranty',
    specs: ['1000R Deep Immersion Curve', '2560x1440 WQHD VA', '144Hz & AMD FreeSync Premium', '1ms MPRT Response'],
    description: 'Wraps peripheral vision in deep 1000R curvature with high static contrast ratio for cinematic depth.',
    primaryMerchantId: 'merchant_002',
    primaryMerchantName: 'Reliance Digital',
    policyCap: 30000,
    merchantQuotes: [
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 21999, deliveryEta: 'Arrives in 2 days', warranty: '3 Years Samsung Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 22499, deliveryEta: 'Arrives in 3 days', warranty: '3 Years Samsung Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 22999, deliveryEta: 'Arrives Thursday', warranty: '3 Years Samsung Warranty' }
    ]
  },
  {
    id: 'prod_benq_gw2780',
    name: 'BenQ GW2780 27-inch Full HD Eye-Care IPS Monitor',
    brand: 'BenQ',
    category: 'displays',
    categoryLabel: 'Displays & Monitors',
    price: 12990,
    rating: 4.5,
    reviewsCount: 410,
    inStock: true,
    stockCount: 33,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '3 Years Onsite Warranty',
    specs: ['Edge-to-Edge Slim Bezel', 'Brightness Intelligence (B.I.) Sensor', 'Low Blue Light & Flicker-Free', 'Built-in Dual Stereo Speakers'],
    description: 'Designed for prolonged workstation comfort with ambient lighting adaptation and clean cable management.',
    primaryMerchantId: 'merchant_003',
    primaryMerchantName: 'Amazon Prime Direct',
    policyCap: 18000,
    merchantQuotes: [
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 12990, deliveryEta: 'Arrives Tomorrow', warranty: '3 Years Onsite Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 13490, deliveryEta: 'Arrives in 2 days', warranty: '3 Years Onsite Warranty' },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 13990, deliveryEta: 'Arrives in 3 days', warranty: '3 Years Onsite Warranty' }
    ]
  },

  // Kitchen Appliances
  {
    id: 'prod_philips_airfryer',
    name: 'Philips Essential Digital Air Fryer 4.1L (Rapid Air Technology)',
    brand: 'Philips',
    category: 'appliances',
    categoryLabel: 'Kitchen Appliances',
    price: 5499,
    rating: 4.6,
    reviewsCount: 390,
    inStock: true,
    stockCount: 25,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '2 Years Worldwide Philips Warranty',
    specs: ['4.1L Basket Capacity', 'Rapid Air 90% Less Fat Cooking', '7 Pre-set One-Touch Cooking Programs', '1400W Rapid Heating'],
    description: 'Starfish design bottom enables high-velocity vortex airflow for even frying and roasting with minimal oil.',
    primaryMerchantId: 'merchant_002',
    primaryMerchantName: 'Reliance Digital',
    policyCap: 8000,
    merchantQuotes: [
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 5499, deliveryEta: 'Arrives Tomorrow', warranty: '2 Years Worldwide Philips Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 5899, deliveryEta: 'Arrives in 3 days', warranty: '2 Years Worldwide Philips Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 5999, deliveryEta: 'Arrives Wednesday', warranty: '2 Years Worldwide Philips Warranty' }
    ]
  },
  {
    id: 'prod_inalsa_airfryer',
    name: 'Inalsa Digital Air Fryer 4.2L with Air Crisp Technology',
    brand: 'Inalsa',
    category: 'appliances',
    categoryLabel: 'Kitchen Appliances',
    price: 3699,
    rating: 4.4,
    reviewsCount: 180,
    inStock: true,
    stockCount: 38,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '2 Years Inalsa Brand Warranty',
    specs: ['4.2L Volume Pan', '8 Preset Digital Menus', '1400W High Thermal Transfer', 'Non-Stick Dishwasher Safe Parts'],
    description: 'Compact high-efficiency air fryer with intelligent overheat protection and auto shut-off safety.',
    primaryMerchantId: 'merchant_003',
    primaryMerchantName: 'Amazon Prime Direct',
    policyCap: 8000,
    merchantQuotes: [
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 3699, deliveryEta: 'Arrives Tomorrow', warranty: '2 Years Inalsa Brand Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 3899, deliveryEta: 'Arrives in 2 days', warranty: '2 Years Inalsa Brand Warranty' },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 3999, deliveryEta: 'Arrives in 3 days', warranty: '2 Years Inalsa Brand Warranty' }
    ]
  },
  {
    id: 'prod_prestige_airfryer',
    name: 'Prestige Nutrifry Electric Digital Air Fryer 4.5L',
    brand: 'Prestige',
    category: 'appliances',
    categoryLabel: 'Kitchen Appliances',
    price: 4299,
    rating: 4.5,
    reviewsCount: 165,
    inStock: true,
    stockCount: 29,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Prestige Warranty',
    specs: ['4.5L High-Volume Basket', '30-Minute Auto Timer', '1500W High Efficiency', 'Slide-Out Safety Basket'],
    description: 'Designed for larger family meals with precision temperature control between 80°C and 200°C.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 8000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 4299, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Prestige Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 4599, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Prestige Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 4799, deliveryEta: 'Arrives Friday', warranty: '1 Year Prestige Warranty' }
    ]
  },

  // Computing & Laptops
  {
    id: 'prod_apple_macbook_air_m2',
    name: 'Apple MacBook Air 13-inch M2 Chip 8GB RAM 256GB SSD',
    brand: 'Apple',
    category: 'computing',
    categoryLabel: 'Laptops & Computing',
    price: 89900,
    rating: 4.9,
    reviewsCount: 650,
    inStock: true,
    stockCount: 16,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Apple Official Warranty',
    specs: ['Apple M2 Chip with 8-Core CPU', '13.6-inch Liquid Retina Display', '18 Hours Battery Life', 'MagSafe 3 Charging · 1.24kg'],
    description: 'Incredibly thin aluminum unibody with silent fanless thermal architecture and all-day power efficiency.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 100000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 89900, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Apple Official Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 91900, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Apple Official Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 92490, deliveryEta: 'Arrives Thursday', warranty: '1 Year Apple Official Warranty' }
    ]
  },
  {
    id: 'prod_asus_vivobook_15',
    name: 'ASUS Vivobook 15 Intel Core i5 16GB RAM 512GB SSD',
    brand: 'ASUS',
    category: 'computing',
    categoryLabel: 'Laptops & Computing',
    price: 49990,
    rating: 4.7,
    reviewsCount: 290,
    inStock: true,
    stockCount: 22,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Onsite Manufacturer Warranty',
    specs: ['Intel Core i5 12th Gen', '16GB DDR4 High-Bandwidth RAM', '512GB PCIe 4.0 NVMe SSD', '15.6-inch FHD Anti-Glare Display'],
    description: 'Responsive everyday productivity laptop with 180° lay-flat hinge and webcam privacy shutter.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 70000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 49990, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Onsite Manufacturer Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 51990, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Onsite Manufacturer Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 52490, deliveryEta: 'Arrives Thursday', warranty: '1 Year Onsite Manufacturer Warranty' }
    ]
  },
  {
    id: 'prod_lenovo_ideapad_slim3',
    name: 'Lenovo IdeaPad Slim 3 15-inch Intel Core i3 8GB 512GB SSD',
    brand: 'Lenovo',
    category: 'computing',
    categoryLabel: 'Laptops & Computing',
    price: 37990,
    rating: 4.4,
    reviewsCount: 310,
    inStock: true,
    stockCount: 35,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '2 Years Lenovo Warranty',
    specs: ['Intel Core i3 12th Gen', '8GB RAM & 512GB SSD', 'Rapid Charge Boost', '1.63kg Lightweight Chassis'],
    description: 'Accessible computing power designed for research, study, and daily cloud productivity.',
    primaryMerchantId: 'merchant_003',
    primaryMerchantName: 'Amazon Prime Direct',
    policyCap: 50000,
    merchantQuotes: [
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 37990, deliveryEta: 'Arrives Tomorrow', warranty: '2 Years Lenovo Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 38990, deliveryEta: 'Arrives in 2 days', warranty: '2 Years Lenovo Warranty' },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 39490, deliveryEta: 'Arrives in 3 days', warranty: '2 Years Lenovo Warranty' }
    ]
  },

  // Additional Premium Computing & Flagships
  {
    id: 'prod_apple_macbook_pro_14',
    name: 'Apple MacBook Pro 14-inch M3 Pro Chip 18GB Unified RAM 512GB SSD',
    brand: 'Apple',
    category: 'computing',
    categoryLabel: 'Laptops & Computing',
    price: 199900,
    rating: 4.9,
    reviewsCount: 240,
    inStock: true,
    stockCount: 12,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Apple Official Warranty',
    specs: ['Apple M3 Pro Chip (11-Core CPU, 14-Core GPU)', '14.2-inch Liquid Retina XDR Display', 'Up to 18 Hours Battery', 'ProMotion 120Hz & Space Black Finish'],
    description: 'Pro workstation performance in a compact footprint with unprecedented battery efficiency and studio-grade sound.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 250000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 199900, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Apple Official Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 202900, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Apple Official Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 204900, deliveryEta: 'Arrives Wednesday', warranty: '1 Year Apple Official Warranty' }
    ]
  },
  {
    id: 'prod_dell_xps_13_plus',
    name: 'Dell XPS 13 Plus 13.4-inch 3.5K OLED Intel Core i7 16GB 1TB SSD',
    brand: 'Dell',
    category: 'computing',
    categoryLabel: 'Laptops & Computing',
    price: 164990,
    rating: 4.7,
    reviewsCount: 145,
    inStock: true,
    stockCount: 15,
    deliveryEta: 'Arrives in 2 days',
    warranty: '2 Years Premium Onsite Support',
    specs: ['12th Gen Intel Core i7-1260P', '3.5K (3456x2160) OLED InfinityEdge Touch', 'Seamless Glass Haptic Trackpad', 'Capacitive Touch Function Row'],
    description: 'Ultra-modern executive ultrabook with zero-lattice keyboard and edge-to-edge Corning Gorilla Glass.',
    primaryMerchantId: 'merchant_002',
    primaryMerchantName: 'Reliance Digital',
    policyCap: 200000,
    merchantQuotes: [
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 164990, deliveryEta: 'Arrives in 2 days', warranty: '2 Years Premium Onsite Support', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 167990, deliveryEta: 'Arrives in 3 days', warranty: '2 Years Premium Onsite Support' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 169990, deliveryEta: 'Arrives Thursday', warranty: '2 Years Premium Onsite Support' }
    ]
  },

  // Gaming Consoles
  {
    id: 'prod_ps5_slim_disc',
    name: 'Sony PlayStation 5 Slim Console (Disc Edition with DualSense)',
    brand: 'Sony',
    category: 'computing',
    categoryLabel: 'Laptops & Computing',
    price: 54990,
    rating: 4.9,
    reviewsCount: 780,
    inStock: true,
    stockCount: 20,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Sony Official Warranty',
    specs: ['Custom AMD Zen 2 CPU & RDNA 2 GPU', '1TB High-Speed Custom SSD', 'Ultra HD Blu-ray Disc Drive', 'DualSense Wireless Controller Included'],
    description: 'Compact redesign offering 30% reduction in volume with lightning-fast load times and ray-traced 4K graphics.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 65000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 54990, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Sony Official Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 55490, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Sony Official Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 55990, deliveryEta: 'Arrives Wednesday', warranty: '1 Year Sony Official Warranty' }
    ]
  },
  {
    id: 'prod_xbox_series_x',
    name: 'Microsoft Xbox Series X 1TB Console (Carbon Black)',
    brand: 'Microsoft',
    category: 'computing',
    categoryLabel: 'Laptops & Computing',
    price: 52990,
    rating: 4.8,
    reviewsCount: 460,
    inStock: true,
    stockCount: 18,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Microsoft Hardware Warranty',
    specs: ['12 Teraflops GPU Computing Power', '1TB Custom NVMe SSD', 'Quick Resume & 120 FPS Gaming', 'Xbox Velocity Architecture'],
    description: 'The fastest, most powerful Xbox ever engineered, built for high-framerate 4K fidelity and Game Pass.',
    primaryMerchantId: 'merchant_003',
    primaryMerchantName: 'Amazon Prime Direct',
    policyCap: 65000,
    merchantQuotes: [
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 52990, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Microsoft Hardware Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 53990, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Microsoft Hardware Warranty' },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 54490, deliveryEta: 'Arrives Thursday', warranty: '1 Year Microsoft Hardware Warranty' }
    ]
  },

  // Audio Earbuds & Speakers
  {
    id: 'prod_apple_airpods_pro_2',
    name: 'Apple AirPods Pro (2nd Generation) with MagSafe Case (USB-C)',
    brand: 'Apple',
    category: 'audio',
    categoryLabel: 'Audio & ANC',
    price: 24900,
    rating: 4.9,
    reviewsCount: 920,
    inStock: true,
    stockCount: 45,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Apple Warranty',
    specs: ['Apple H2 Headphone Chip', '2x Stronger Active Noise Cancellation', 'Adaptive Audio & Transparency', 'Up to 30 Hours Total Listening'],
    description: 'Next-level Active Noise Cancellation and personalized Spatial Audio with dynamic head tracking and dust resistance.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 30000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 24900, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Apple Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 25490, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Apple Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 25900, deliveryEta: 'Arrives Wednesday', warranty: '1 Year Apple Warranty' }
    ]
  },
  {
    id: 'prod_sony_wf1000xm5',
    name: 'Sony WF-1000XM5 True Wireless Noise Cancelling Earbuds',
    brand: 'Sony',
    category: 'audio',
    categoryLabel: 'Audio & ANC',
    price: 24990,
    rating: 4.8,
    reviewsCount: 410,
    inStock: true,
    stockCount: 30,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Comprehensive Sony Warranty',
    specs: ['Integrated Processor V2 & QN2e Chip', 'Dynamic Driver X for Rich Vocals', 'Bone Conduction Sensors & AI Noise Reduction', '24 Hours Total Battery with Qi Wireless Charging'],
    description: 'Precision engineered for audiophiles with deep active noise reduction, multipoint Bluetooth connection, and LDAC support.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 30000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 24990, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Comprehensive Sony Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 25490, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Comprehensive Sony Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 25990, deliveryEta: 'Arrives Thursday', warranty: '1 Year Comprehensive Sony Warranty' }
    ]
  },
  {
    id: 'prod_bose_qc_ultra',
    name: 'Bose QuietComfort Ultra Wireless Noise Cancelling Headphones',
    brand: 'Bose',
    category: 'audio',
    categoryLabel: 'Audio & ANC',
    price: 35900,
    rating: 4.8,
    reviewsCount: 320,
    inStock: true,
    stockCount: 16,
    deliveryEta: 'Arrives in 2 days',
    warranty: '1 Year Bose India Warranty',
    specs: ['Bose Immersive Spatial Audio', 'CustomTune Sound Calibration', 'Quiet Mode, Aware Mode, Immersion Mode', '24 Hours Battery Life · USB-C'],
    description: 'Groundbreaking spatialized audio meets world-class noise cancellation in an elevated, ultra-comfortable silhouette.',
    primaryMerchantId: 'merchant_002',
    primaryMerchantName: 'Reliance Digital',
    policyCap: 45000,
    merchantQuotes: [
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 35900, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Bose India Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 36490, deliveryEta: 'Arrives in 3 days', warranty: '1 Year Bose India Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 36900, deliveryEta: 'Arrives Wednesday', warranty: '1 Year Bose India Warranty' }
    ]
  },
  {
    id: 'prod_sonos_era_100',
    name: 'Sonos Era 100 Smart Wireless Multi-Room Speaker',
    brand: 'Sonos',
    category: 'audio',
    categoryLabel: 'Audio & ANC',
    price: 29999,
    rating: 4.8,
    reviewsCount: 195,
    inStock: true,
    stockCount: 22,
    deliveryEta: 'Arrives in 2 days',
    warranty: '1 Year Official Warranty',
    specs: ['Dual Angled Tweeters & Deep Bass Woofer', 'Trueplay Room Tuning Calibration', 'Apple AirPlay 2 & Bluetooth 5.0', 'Direct WiFi Lossless Streaming'],
    description: 'Acoustic architecture delivering stereo sound and rich low-end response, perfect for home office and living spaces.',
    primaryMerchantId: 'merchant_002',
    primaryMerchantName: 'Reliance Digital',
    policyCap: 40000,
    merchantQuotes: [
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 29999, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Official Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 30999, deliveryEta: 'Arrives in 3 days', warranty: '1 Year Official Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 31499, deliveryEta: 'Arrives Thursday', warranty: '1 Year Official Warranty' }
    ]
  },
  {
    id: 'prod_marshall_stanmore_3',
    name: 'Marshall Stanmore III Bluetooth Wireless Home Speaker',
    brand: 'Marshall',
    category: 'audio',
    categoryLabel: 'Audio & ANC',
    price: 37999,
    rating: 4.9,
    reviewsCount: 380,
    inStock: true,
    stockCount: 14,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Marshall Warranty',
    specs: ['Dynamic Loudness Tonal Balance', 'Dual 3/4\" Tweeters & 50W Class D Woofer', 'Brass Control Knobs & Vintage Tolex', 'Bluetooth 5.2 with 3.5mm & RCA inputs'],
    description: 'Re-engineered with a wider soundstage and dynamic loudness, delivering iconic room-filling Marshall tone.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 45000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 37999, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Marshall Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 38999, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Marshall Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 39499, deliveryEta: 'Arrives Thursday', warranty: '1 Year Marshall Warranty' }
    ]
  },

  // Pro Displays
  {
    id: 'prod_apple_studio_display',
    name: 'Apple Studio Display 27-inch 5K Retina (Standard Glass, Tilt Stand)',
    brand: 'Apple',
    category: 'displays',
    categoryLabel: 'Displays & Monitors',
    price: 159900,
    rating: 4.9,
    reviewsCount: 180,
    inStock: true,
    stockCount: 8,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Apple Official Warranty',
    specs: ['5120x2880 5K Retina Resolution at 218 ppi', '600 Nits Brightness & P3 Wide Color', '12MP Ultra Wide Camera with Center Stage', 'Six-Speaker Sound System with Spatial Audio'],
    description: 'Immersive 27-inch 5K Retina canvas with A13 Bionic chip processing studio audio and intelligent camera framing.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 200000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 159900, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Apple Official Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 162900, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Apple Official Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 164900, deliveryEta: 'Arrives Thursday', warranty: '1 Year Apple Official Warranty' }
    ]
  },
  {
    id: 'prod_dell_u3223qe',
    name: 'Dell UltraSharp 32-inch 4K USB-C Hub Monitor (U3223QE IPS Black)',
    brand: 'Dell',
    category: 'displays',
    categoryLabel: 'Displays & Monitors',
    price: 78990,
    rating: 4.8,
    reviewsCount: 215,
    inStock: true,
    stockCount: 16,
    deliveryEta: 'Arrives in 2 days',
    warranty: '3 Years Advanced Exchange Service',
    specs: ['IPS Black Panel Technology with 2000:1 Contrast', '3840x2160 4K UHD Resolution', '90W USB-C Power Delivery & RJ45 Ethernet', 'Built-in KVM Switch & Picture-by-Picture'],
    description: 'Groundbreaking IPS Black contrast ratio with comprehensive single-cable docking for multi-system productivity.',
    primaryMerchantId: 'merchant_002',
    primaryMerchantName: 'Reliance Digital',
    policyCap: 90000,
    merchantQuotes: [
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 78990, deliveryEta: 'Arrives in 2 days', warranty: '3 Years Advanced Exchange Service', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 80490, deliveryEta: 'Arrives in 3 days', warranty: '3 Years Advanced Exchange Service' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 81990, deliveryEta: 'Arrives Wednesday', warranty: '3 Years Advanced Exchange Service' }
    ]
  },

  // Smart Desk Accessories & Microphones
  {
    id: 'prod_elgato_stream_deck_mk2',
    name: 'Elgato Stream Deck MK.2 15 Customizable LCD Keys Controller',
    brand: 'Elgato',
    category: 'accessories',
    categoryLabel: 'Input & Peripherals',
    price: 13990,
    rating: 4.8,
    reviewsCount: 520,
    inStock: true,
    stockCount: 34,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '2 Years Manufacturer Warranty',
    specs: ['15 Customizable Tactile LCD Keys', 'One-Touch Macro & Scene Switching', 'Detachable Faceplate & 45° Desktop Stand', 'Direct Plugins for OBS, Twitch, Spotify, Zoom'],
    description: 'Studio automation console empowering streamers, developers, and power users with tactile macro control.',
    primaryMerchantId: 'merchant_003',
    primaryMerchantName: 'Amazon Prime Direct',
    policyCap: 18000,
    merchantQuotes: [
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 13990, deliveryEta: 'Arrives Tomorrow', warranty: '2 Years Manufacturer Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 14490, deliveryEta: 'Arrives in 2 days', warranty: '2 Years Manufacturer Warranty' },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 14990, deliveryEta: 'Arrives Thursday', warranty: '2 Years Manufacturer Warranty' }
    ]
  },
  {
    id: 'prod_shure_sm7b',
    name: 'Shure SM7B Cardioid Dynamic Studio Vocal Microphone',
    brand: 'Shure',
    category: 'accessories',
    categoryLabel: 'Input & Peripherals',
    price: 38500,
    rating: 4.9,
    reviewsCount: 610,
    inStock: true,
    stockCount: 19,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '2 Years Shure Official Warranty',
    specs: ['Smooth Wide-Range Frequency Response', 'Bass Rolloff & Mid-Range Presence Boost', 'Internal Air Suspension Shock Isolation', 'Advanced Electromagnetic Hum Shielding'],
    description: 'The legendary dynamic microphone used by broadcasters, podcasters, and recording artists worldwide.',
    primaryMerchantId: 'merchant_003',
    primaryMerchantName: 'Amazon Prime Direct',
    policyCap: 50000,
    merchantQuotes: [
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 38500, deliveryEta: 'Arrives Tomorrow', warranty: '2 Years Shure Official Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 39490, deliveryEta: 'Arrives in 2 days', warranty: '2 Years Shure Official Warranty' },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 39990, deliveryEta: 'Arrives Thursday', warranty: '2 Years Shure Official Warranty' }
    ]
  },
  {
    id: 'prod_logitech_mx_brio',
    name: 'Logitech MX Brio Ultra HD 4K Streaming & Collaboration Webcam',
    brand: 'Logitech',
    category: 'accessories',
    categoryLabel: 'Input & Peripherals',
    price: 19995,
    rating: 4.7,
    reviewsCount: 230,
    inStock: true,
    stockCount: 28,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '2 Years Official Warranty',
    specs: ['Ultra HD 4K Sensor with 70% Larger Pixels', 'AI-Enhanced Face Visibility & Auto-Exposure', 'Show Mode Desktop Tilting', 'Dual Beamforming Noise-Canceling Microphones'],
    description: 'Flagship 4K video clarity with advanced sensor engineering and physical privacy shutter for executive meetings.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 25000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 19995, deliveryEta: 'Arrives Tomorrow', warranty: '2 Years Official Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 20495, deliveryEta: 'Arrives in 2 days', warranty: '2 Years Official Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 20995, deliveryEta: 'Arrives Wednesday', warranty: '2 Years Official Warranty' }
    ]
  },

  // Smart Home & Air Care Appliances
  {
    id: 'prod_dyson_v12_detect_slim',
    name: 'Dyson V12 Detect Slim Total Clean Cordless Vacuum Cleaner',
    brand: 'Dyson',
    category: 'appliances',
    categoryLabel: 'Kitchen Appliances',
    price: 52900,
    rating: 4.8,
    reviewsCount: 390,
    inStock: true,
    stockCount: 14,
    deliveryEta: 'Arrives in 2 days',
    warranty: '2 Years Comprehensive Dyson Warranty',
    specs: ['Laser Slim Fluffy Cleaner Head (Reveals Invisible Dust)', 'Piezo Sensor Counts & Measures Dust Particles', 'Lightweight 2.2kg Balanced Handheld Form', 'Up to 60 Minutes Fade-Free Suction'],
    description: 'Intelligent cord-free vacuum that calculates particle quantity in real time and automatically ramps motor power.',
    primaryMerchantId: 'merchant_002',
    primaryMerchantName: 'Reliance Digital',
    policyCap: 65000,
    merchantQuotes: [
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 52900, deliveryEta: 'Arrives in 2 days', warranty: '2 Years Comprehensive Dyson Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 53900, deliveryEta: 'Arrives in 3 days', warranty: '2 Years Comprehensive Dyson Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 54490, deliveryEta: 'Arrives Thursday', warranty: '2 Years Comprehensive Dyson Warranty' }
    ]
  },
  {
    id: 'prod_dyson_hp10_purifier_heater',
    name: 'Dyson Purifier Hot+Cool Gen1 HP10 Air Purifier & Fan Heater',
    brand: 'Dyson',
    category: 'appliances',
    categoryLabel: 'Kitchen Appliances',
    price: 49900,
    rating: 4.8,
    reviewsCount: 270,
    inStock: true,
    stockCount: 18,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '2 Years Dyson Warranty',
    specs: ['HEPA H13 Sealed Filter Captures 99.95% of Ultrafine Particles', 'Air Multiplier 350° Oscillation Circulation', 'Thermostatic Ceramic Space Heating', 'Real-Time Air Quality Sensor with LCD'],
    description: 'Year-round climate control that purifies indoor air, warms rooms in winter, and cools with high-velocity airflow in summer.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 60000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 49900, deliveryEta: 'Arrives Tomorrow', warranty: '2 Years Dyson Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 50900, deliveryEta: 'Arrives in 2 days', warranty: '2 Years Dyson Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 51490, deliveryEta: 'Arrives Wednesday', warranty: '2 Years Dyson Warranty' }
    ]
  },
  {
    id: 'prod_xiaomi_purifier_4_pro',
    name: 'Xiaomi Smart Air Purifier 4 Pro (High CADR 500m³/h)',
    brand: 'Xiaomi',
    category: 'appliances',
    categoryLabel: 'Kitchen Appliances',
    price: 14999,
    rating: 4.6,
    reviewsCount: 480,
    inStock: true,
    stockCount: 40,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '1 Year Brand Warranty',
    specs: ['500m³/h PM CADR (Covers Up to 60m² Rooms)', 'Triple Layer 99.97% 0.3μm High Efficiency Filter', 'OLED Touch Display with PM2.5 / PM10 Sensor', 'Negative Air Ionization & Mi Home App Control'],
    description: 'High-speed air purification engineered for large living rooms, clearing smoke, pollen, and airborne pet dander.',
    primaryMerchantId: 'merchant_003',
    primaryMerchantName: 'Amazon Prime Direct',
    policyCap: 20000,
    merchantQuotes: [
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 14999, deliveryEta: 'Arrives Tomorrow', warranty: '1 Year Brand Warranty', isBest: true },
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 15499, deliveryEta: 'Arrives in 2 days', warranty: '1 Year Brand Warranty' },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 15999, deliveryEta: 'Arrives in 3 days', warranty: '1 Year Brand Warranty' }
    ]
  },
  {
    id: 'prod_nespresso_vertuo_pop',
    name: 'Nespresso Vertuo Pop Automatic Coffee Machine with Aeroccino Milk Frother',
    brand: 'Nespresso',
    category: 'appliances',
    categoryLabel: 'Kitchen Appliances',
    price: 16999,
    rating: 4.7,
    reviewsCount: 310,
    inStock: true,
    stockCount: 25,
    deliveryEta: 'Arrives Tomorrow',
    warranty: '2 Years Official Warranty',
    specs: ['Centrifusion Extraction Technology (4,000 RPM)', 'Barcode Recognition for 4 Cup Sizes', 'Aeroccino3 Included for Hot & Cold Froth', '30-Second Fast Heat-Up'],
    description: 'Compact capsule espresso and coffee machine producing velvety crema with intelligent barcode cup sizing.',
    primaryMerchantId: 'merchant_001',
    primaryMerchantName: 'Croma',
    policyCap: 22000,
    merchantQuotes: [
      { merchantId: 'merchant_001', merchantName: 'Croma', price: 16999, deliveryEta: 'Arrives Tomorrow', warranty: '2 Years Official Warranty', isBest: true },
      { merchantId: 'merchant_002', merchantName: 'Reliance Digital', price: 17499, deliveryEta: 'Arrives in 2 days', warranty: '2 Years Official Warranty' },
      { merchantId: 'merchant_003', merchantName: 'Amazon Prime Direct', price: 17999, deliveryEta: 'Arrives Thursday', warranty: '2 Years Official Warranty' }
    ]
  }
];

// Ensure fallback items also feature realistic randomized availability per merchant
for (const item of CATALOG_ITEMS) {
  item.merchantQuotes = buildMerchantQuotes(item.id, item.price, item.primaryMerchantId);
}


