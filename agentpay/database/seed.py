import json
from sqlalchemy.orm import Session
from agentpay.database.models import (
    Base,
    engine,
    SessionLocal,
    Agent,
    AgentPolicy,
    Merchant,
    Product
)


def seed_database(db: Session = None):
    should_close = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        should_close = True

    try:
        # 1. Seed Multi-Merchant Ecosystem
        merchants_data = [
            {
                "id": "merchant_001",
                "name": "Croma Electronics Hub",
                "status": "ACTIVE",
                "currency": "INR"
            },
            {
                "id": "merchant_002",
                "name": "Reliance Digital Tech",
                "status": "ACTIVE",
                "currency": "INR"
            },
            {
                "id": "merchant_003",
                "name": "Amazon Prime Direct",
                "status": "ACTIVE",
                "currency": "INR"
            }
        ]

        for m_data in merchants_data:
            m = db.query(Merchant).filter(Merchant.id == m_data["id"]).first()
            if not m:
                m = Merchant(
                    id=m_data["id"],
                    name=m_data["name"],
                    status=m_data["status"],
                    currency=m_data["currency"]
                )
                db.add(m)
            else:
                m.name = m_data["name"]
                m.status = m_data["status"]
        db.commit()

        # 2. Seed Agent & Policy
        agent = db.query(Agent).filter(Agent.id == "agent_001").first()
        if not agent:
            agent = Agent(
                id="agent_001",
                name="AgentPay Autonomous Buyer Squad",
                status="ACTIVE"
            )
            db.add(agent)
            db.commit()

        policy = db.query(AgentPolicy).filter(AgentPolicy.agent_id == "agent_001").first()
        if not policy:
            policy = AgentPolicy(
                id="policy_001",
                agent_id="agent_001",
                currency="INR",
                per_transaction_limit=5000.0,
                daily_spending_limit=20000.0,
                _allowed_categories=json.dumps(["electronics", "audio", "accessories", "books", "office", "displays", "smart_devices", "wearables"]),
                _blocked_merchants=json.dumps([])
            )
            db.add(policy)
            db.commit()

        # 3. Seed Comprehensive Multi-Merchant Product Catalog (45+ SKUs)
        products_data = [
            # =========================================================================
            # AUDIO & ANC (11 SKUs)
            # =========================================================================
            {
                "id": "prod_jbl_770nc",
                "merchant_id": "merchant_001",
                "name": "JBL Tune 770NC Wireless Over-Ear Adaptive ANC Headphones",
                "brand": "JBL",
                "description": "Adaptive Noise Cancelling with Smart Ambient mode, Bluetooth 5.3, up to 70 hours battery life, speed charge (5 min = 3 hrs), 40mm dynamic drivers.",
                "category": "audio",
                "price": 4499.0,
                "currency": "INR",
                "stock": 50,
                "rating": 4.6,
                "specs": {
                    "battery_life": "70 hours",
                    "noise_cancellation": "Adaptive ANC",
                    "connectivity": ["Bluetooth 5.3", "3.5mm AUX"],
                    "driver_size": "40mm",
                    "weight": "232g",
                    "warranty": "1 Year Official Warranty"
                }
            },
            {
                "id": "prod_jbl_770nc_reliance",
                "merchant_id": "merchant_002",
                "name": "JBL Tune 770NC Wireless Adaptive ANC Headphones (Special Edition)",
                "brand": "JBL",
                "description": "Adaptive Noise Cancelling with Smart Ambient mode, Bluetooth 5.3, 70 hours battery life with Reliance 2-year warranty extension.",
                "category": "audio",
                "price": 4399.0,
                "currency": "INR",
                "stock": 35,
                "rating": 4.7,
                "specs": {
                    "battery_life": "70 hours",
                    "noise_cancellation": "Adaptive ANC",
                    "connectivity": ["Bluetooth 5.3", "3.5mm AUX"],
                    "driver_size": "40mm",
                    "warranty": "2 Year Extended Reliance Warranty"
                }
            },
            {
                "id": "prod_boat_rockerz_550",
                "merchant_id": "merchant_001",
                "name": "boAt Rockerz 550 Over-Ear Wireless Headphones",
                "brand": "boAt",
                "description": "Super Extra Bass with 50mm dynamic drivers, 20 hours playback, ergonomic plush earcups, physical bass boost switch.",
                "category": "audio",
                "price": 1799.0,
                "currency": "INR",
                "stock": 100,
                "rating": 4.2,
                "specs": {
                    "battery_life": "20 hours",
                    "noise_cancellation": "Passive Isolation",
                    "connectivity": ["Bluetooth 5.0", "AUX"],
                    "driver_size": "50mm"
                }
            },
            {
                "id": "prod_boat_airdopes_141",
                "merchant_id": "merchant_003",
                "name": "boAt Airdopes 141 True Wireless Earbuds (42H Playtime)",
                "brand": "boAt",
                "description": "42 hours total playtime, ENx noise cancellation for calls, 8mm drivers, ASAP charge (5 mins = 75 mins), IPX4 sweat and water resistance.",
                "category": "audio",
                "price": 1299.0,
                "currency": "INR",
                "stock": 150,
                "rating": 4.1,
                "specs": {
                    "battery_life": "42 hours total",
                    "noise_cancellation": "ENx Environmental Noise Cancellation",
                    "water_resistance": "IPX4",
                    "driver_size": "8mm"
                }
            },
            {
                "id": "prod_sony_wh1000xm5",
                "merchant_id": "merchant_001",
                "name": "Sony WH-1000XM5 Wireless Industry Leading Noise Canceling Headphones",
                "brand": "Sony",
                "description": "Integrated Processor V1 and QN1 with 8 microphones, Auto NC Optimizer, 30 hours battery life, LDAC Hi-Res Audio, crystal clear hands-free calling.",
                "category": "audio",
                "price": 26990.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.9,
                "specs": {
                    "battery_life": "30 hours",
                    "noise_cancellation": "Industry Leading Dual-Processor ANC",
                    "connectivity": ["Bluetooth 5.2", "LDAC", "3.5mm AUX"],
                    "driver_size": "30mm Carbon Fiber",
                    "spatial_audio": "360 Reality Audio"
                }
            },
            {
                "id": "prod_sony_wh1000xm5_reliance",
                "merchant_id": "merchant_002",
                "name": "Sony WH-1000XM5 Wireless Noise Canceling Headphones (Silver Edition)",
                "brand": "Sony",
                "description": "Flagship ANC headphones with dual processor audio, 30 hours battery, LDAC support. Fast in-store pickup available.",
                "category": "audio",
                "price": 25490.0,
                "currency": "INR",
                "stock": 18,
                "rating": 4.9,
                "specs": {
                    "battery_life": "30 hours",
                    "noise_cancellation": "Industry Leading Dual-Processor ANC",
                    "connectivity": ["Bluetooth 5.2", "LDAC"],
                    "driver_size": "30mm Carbon Fiber"
                }
            },
            {
                "id": "prod_sony_wf1000xm5",
                "merchant_id": "merchant_003",
                "name": "Sony WF-1000XM5 Truly Wireless Noise Canceling Earbuds",
                "brand": "Sony",
                "description": "Dynamic Driver X with Dual Feedback mics, Integrated Processor V2 and HD Noise Cancelling Processor QN2e, Hi-Res wireless audio with LDAC, bone conduction sensors.",
                "category": "audio",
                "price": 19990.0,
                "currency": "INR",
                "stock": 30,
                "rating": 4.8,
                "specs": {
                    "battery_life": "8 hours (24h with case)",
                    "noise_cancellation": "Dynamic Driver X ANC",
                    "connectivity": ["Bluetooth 5.3", "LDAC", "Multipoint"],
                    "water_resistance": "IPX4"
                }
            },
            {
                "id": "prod_bose_qc45",
                "merchant_id": "merchant_003",
                "name": "Bose QuietComfort 45 Wireless Noise Cancelling Headphones",
                "brand": "Bose",
                "description": "High-fidelity audio with TriPort acoustic architecture, Quiet and Aware modes, 24 hours battery life, lightweight synthetic leather cushions.",
                "category": "audio",
                "price": 24900.0,
                "currency": "INR",
                "stock": 20,
                "rating": 4.8,
                "specs": {
                    "battery_life": "24 hours",
                    "noise_cancellation": "Active Acoustic ANC",
                    "connectivity": ["Bluetooth 5.1", "USB-C"]
                }
            },
            {
                "id": "prod_bose_qc_ultra",
                "merchant_id": "merchant_001",
                "name": "Bose QuietComfort Ultra Wireless Noise Cancelling Headphones",
                "brand": "Bose",
                "description": "Breakthrough spatialized audio with Bose Immersive Audio, world-class active noise cancellation, CustomTune technology, luxury materials.",
                "category": "audio",
                "price": 35900.0,
                "currency": "INR",
                "stock": 15,
                "rating": 4.9,
                "specs": {
                    "battery_life": "24 hours (18 hours with Immersive Audio)",
                    "noise_cancellation": "CustomTune Adaptive ANC",
                    "connectivity": ["Bluetooth 5.3", "Snapdragon Sound"],
                    "spatial_audio": "Bose Immersive Audio"
                }
            },
            {
                "id": "prod_airpods_pro2",
                "merchant_id": "merchant_003",
                "name": "Apple AirPods Pro (2nd Generation, USB-C MagSafe Case)",
                "brand": "Apple",
                "description": "Apple H2 headphone chip, up to 2x more Active Noise Cancellation, Adaptive Audio, Transparency mode, Personalized Spatial Audio with dynamic head tracking.",
                "category": "audio",
                "price": 22900.0,
                "currency": "INR",
                "stock": 40,
                "rating": 4.9,
                "specs": {
                    "battery_life": "6 hours (30 hours with case)",
                    "noise_cancellation": "Adaptive ANC",
                    "connectivity": ["Bluetooth 5.3", "Apple H2"],
                    "water_resistance": "IP54 dust, sweat, and water resistant"
                }
            },
            {
                "id": "prod_shure_sm7b",
                "merchant_id": "merchant_003",
                "name": "Shure SM7B Cardioid Dynamic Vocal Microphone",
                "brand": "Shure",
                "description": "Legendary studio dynamic microphone with flat, wide-range frequency response, bass rolloff and mid-range emphasis controls, internal air suspension shock isolation.",
                "category": "audio",
                "price": 34500.0,
                "currency": "INR",
                "stock": 12,
                "rating": 5.0,
                "specs": {
                    "type": "Dynamic Cardioid",
                    "frequency_response": "50 to 20,000 Hz",
                    "connector": "3-pin professional XLR",
                    "shielding": "Electromagnetic hum shielding"
                }
            },

            # =========================================================================
            # ELECTRONICS & COMPUTING (8 SKUs)
            # =========================================================================
            {
                "id": "prod_dell_xps15",
                "merchant_id": "merchant_001",
                "name": "Dell XPS 15 OLED Laptop (Intel Core i9 13900H, 32GB RAM, 1TB SSD, RTX 4070)",
                "brand": "Dell",
                "description": "High performance 15.6-inch 3.5K OLED InfinityEdge touchscreen display, 14-core Intel i9 processor, NVIDIA GeForce RTX 4070 8GB GDDR6, CNC machined aluminum chassis.",
                "category": "electronics",
                "price": 85000.0,
                "currency": "INR",
                "stock": 10,
                "rating": 4.7,
                "specs": {
                    "processor": "Intel Core i9-13900H (14 cores, up to 5.4GHz)",
                    "ram": "32GB DDR5 4800MHz",
                    "storage": "1TB M.2 PCIe NVMe Gen4 SSD",
                    "graphics": "NVIDIA GeForce RTX 4070 8GB GDDR6",
                    "display": "15.6 inch 3.5K (3456x2160) OLED Touch Display"
                }
            },
            {
                "id": "prod_macbook_air_m3",
                "merchant_id": "merchant_003",
                "name": "Apple MacBook Air 13-inch (M3 Chip 8-Core CPU, 16GB Unified RAM, 512GB SSD)",
                "brand": "Apple",
                "description": "Supercharged by Apple M3 chip with 8-core CPU and 10-core GPU, 13.6-inch Liquid Retina display with 500 nits, up to 18 hours battery life, fanless silent design, Midnight color.",
                "category": "electronics",
                "price": 114900.0,
                "currency": "INR",
                "stock": 15,
                "rating": 4.9,
                "specs": {
                    "processor": "Apple M3 Chip (8-core CPU, 10-core GPU)",
                    "ram": "16GB Unified Memory",
                    "storage": "512GB High-Speed SSD",
                    "battery_life": "Up to 18 hours",
                    "display": "13.6-inch Liquid Retina Display (2560x1664)"
                }
            },
            {
                "id": "prod_macbook_pro_14_m3",
                "merchant_id": "merchant_002",
                "name": "Apple MacBook Pro 14-inch (M3 Pro 12-Core CPU, 18GB RAM, 512GB SSD, Space Black)",
                "brand": "Apple",
                "description": "Liquid Retina XDR display with ProMotion 120Hz, up to 22 hours battery life, advanced hardware-accelerated ray tracing, HDMI, SDXC, MagSafe 3.",
                "category": "electronics",
                "price": 199900.0,
                "currency": "INR",
                "stock": 8,
                "rating": 5.0,
                "specs": {
                    "processor": "Apple M3 Pro (12-core CPU, 18-core GPU)",
                    "ram": "18GB Unified RAM",
                    "storage": "512GB NVMe SSD",
                    "display": "14.2-inch Liquid Retina XDR (120Hz ProMotion, 1600 nits peak)"
                }
            },
            {
                "id": "prod_lenovo_thinkpad_x1",
                "merchant_id": "merchant_001",
                "name": "Lenovo ThinkPad X1 Carbon Gen 11 (Intel Core i7, 16GB RAM, 512GB SSD)",
                "brand": "Lenovo",
                "description": "Ultralight carbon-fiber business laptop, Intel Core i7-1355U, 14-inch WUXGA IPS anti-glare display, legendary spill-resistant keyboard, military-grade MIL-STD 810H durability.",
                "category": "electronics",
                "price": 138000.0,
                "currency": "INR",
                "stock": 8,
                "rating": 4.8,
                "specs": {
                    "processor": "Intel Core i7-1355U (10 cores)",
                    "ram": "16GB LPDDR5",
                    "storage": "512GB PCIe Gen4 NVMe SSD",
                    "display": "14-inch WUXGA (1920x1200) Anti-Glare IPS 400 nits"
                }
            },
            {
                "id": "prod_asus_zephyrus_g14",
                "merchant_id": "merchant_002",
                "name": "ASUS ROG Zephyrus G14 OLED (AMD Ryzen 9, 32GB RAM, 1TB SSD, RTX 4070)",
                "brand": "ASUS",
                "description": "14-inch 3K 120Hz OLED ROG Nebula display (0.2ms response), AMD Ryzen 9 8945HS with Ryzen AI, CNC aluminum unibody, Slash Lighting lid.",
                "category": "electronics",
                "price": 174990.0,
                "currency": "INR",
                "stock": 6,
                "rating": 4.9,
                "specs": {
                    "processor": "AMD Ryzen 9 8945HS (8 cores / 16 threads, 5.2GHz)",
                    "ram": "32GB LPDDR5X 6400MHz",
                    "storage": "1TB PCIe Gen4 SSD",
                    "graphics": "NVIDIA GeForce RTX 4070 8GB GDDR6",
                    "display": "14-inch 3K (2880x1800) 120Hz OLED 0.2ms"
                }
            },
            {
                "id": "prod_raspberry_pi_5",
                "merchant_id": "merchant_003",
                "name": "Raspberry Pi 5 Single Board Computer (8GB RAM, Broadcom BCM2712)",
                "brand": "Raspberry Pi",
                "description": "2.4GHz quad-core 64-bit Arm Cortex-A76 CPU, VideoCore VII GPU with dual 4Kp60 HDMI display outputs, PCIe 2.0 x1 interface, dual-band Wi-Fi and Bluetooth 5.0.",
                "category": "electronics",
                "price": 7499.0,
                "currency": "INR",
                "stock": 45,
                "rating": 4.8,
                "specs": {
                    "processor": "Broadcom BCM2712 2.4GHz quad-core 64-bit Arm Cortex-A76",
                    "ram": "8GB LPDDR4X-4267",
                    "connectivity": ["Dual 4K HDMI", "Gigabit Ethernet", "PCIe 2.0", "USB 3.0", "Wi-Fi 5"]
                }
            },
            {
                "id": "prod_raspberry_pi_5_kit",
                "merchant_id": "merchant_003",
                "name": "Raspberry Pi 5 8GB Official Starter Kit (Active Cooler + 27W USB-C PSU)",
                "brand": "Raspberry Pi",
                "description": "Complete bundle including 8GB board, official active cooler heatsink, official 27W PD power supply, and 64GB preloaded SanDisk Ultra micro-SD.",
                "category": "electronics",
                "price": 9499.0,
                "currency": "INR",
                "stock": 30,
                "rating": 4.9,
                "specs": {
                    "processor": "Broadcom BCM2712 2.4GHz 64-bit Arm",
                    "ram": "8GB LPDDR4X",
                    "included_accessories": ["Active Cooler Heatsink", "27W USB-C PSU", "64GB MicroSD", "Micro-HDMI Cable"]
                }
            },
            {
                "id": "prod_minisforum_um790",
                "merchant_id": "merchant_002",
                "name": "Minisforum UM790 Pro Mini PC (AMD Ryzen 9 7940HS, 32GB DDR5, 1TB NVMe)",
                "brand": "Minisforum",
                "description": "Ultra-compact mini workstation with AMD Ryzen 9 7940HS (Radeon 780M graphics), dual USB4 40Gbps ports with eGPU support, dual 2.5G LAN, liquid metal cooling.",
                "category": "electronics",
                "price": 56990.0,
                "currency": "INR",
                "stock": 14,
                "rating": 4.8,
                "specs": {
                    "processor": "AMD Ryzen 9 7940HS (8C/16T, up to 5.2GHz)",
                    "ram": "32GB DDR5 5600MHz",
                    "storage": "1TB PCIe 4.0 M.2 SSD",
                    "ports": ["2x USB4 (40Gbps)", "2x HDMI 2.1", "2.5G RJ45 Ethernet"]
                }
            },

            # =========================================================================
            # PERIPHERALS & ACCESSORIES (12 SKUs)
            # =========================================================================
            {
                "id": "prod_logitech_mx_master",
                "merchant_id": "merchant_001",
                "name": "Logitech MX Master 3S Wireless Performance Mouse",
                "brand": "Logitech",
                "description": "Quiet clicks with 8K DPI Darkfield any-surface tracking (including glass), MagSpeed electromagnetic scroll wheel (1,000 lines/sec), USB-C fast charging, Easy-Switch 3 devices.",
                "category": "accessories",
                "price": 8995.0,
                "currency": "INR",
                "stock": 40,
                "rating": 4.9,
                "specs": {
                    "dpi_sensor": "8,000 DPI Darkfield (tracks on glass)",
                    "scrolling": "MagSpeed Electromagnetic SmartShift",
                    "battery_life": "70 days on full charge",
                    "connectivity": ["Bluetooth Low Energy", "Logi Bolt USB Receiver"]
                }
            },
            {
                "id": "prod_logitech_mx_master_amazon",
                "merchant_id": "merchant_003",
                "name": "Logitech MX Master 3S Wireless Performance Mouse (Graphite)",
                "brand": "Logitech",
                "description": "Quiet clicks with 8K DPI Darkfield any-surface tracking, MagSpeed wheel, ergonomic thumb rest with gesture button. Includes Prime delivery.",
                "category": "accessories",
                "price": 8750.0,
                "currency": "INR",
                "stock": 55,
                "rating": 4.9,
                "specs": {
                    "dpi_sensor": "8,000 DPI Darkfield",
                    "battery_life": "70 days",
                    "connectivity": ["Bluetooth", "Logi Bolt"]
                }
            },
            {
                "id": "prod_logitech_lift",
                "merchant_id": "merchant_002",
                "name": "Logitech Lift Ergonomic Vertical Mouse",
                "brand": "Logitech",
                "description": "57-degree natural vertical handshake angle designed for small to medium hands, whisper-quiet clicks, SmartWheel speed/precision scrolling, up to 2 years battery life.",
                "category": "accessories",
                "price": 5495.0,
                "currency": "INR",
                "stock": 35,
                "rating": 4.7,
                "specs": {
                    "ergonomics": "57° vertical handshake angle",
                    "dpi_sensor": "400-4000 DPI optical",
                    "battery_life": "Up to 24 months on single AA",
                    "connectivity": ["Bluetooth Low Energy", "Logi Bolt"]
                }
            },
            {
                "id": "prod_keychron_k2",
                "merchant_id": "merchant_001",
                "name": "Keychron K2 Wireless Mechanical Keyboard (Version 2)",
                "brand": "Keychron",
                "description": "Compact 75% layout 84-key wireless mechanical keyboard, Gateron G Pro Brown tactile switches, Mac/Windows layout toggle, 4000mAh battery.",
                "category": "accessories",
                "price": 4999.0,
                "currency": "INR",
                "stock": 45,
                "rating": 4.7,
                "specs": {
                    "layout": "75% layout (84 keys)",
                    "switches": "Gateron G Pro Brown (Tactile)",
                    "connectivity": ["Bluetooth 5.1", "USB-C Wired"],
                    "battery": "4000mAh rechargeable"
                }
            },
            {
                "id": "prod_keychron_k2_pro",
                "merchant_id": "merchant_003",
                "name": "Keychron K2 Pro QMK/VIA Wireless Custom Mechanical Keyboard",
                "brand": "Keychron",
                "description": "75% compact wireless mechanical keyboard, QMK/VIA fully programmable keymaps and macros, hot-swappable PCB, south-facing RGB backlighting, pre-lubed Gateron G Pro Red switches.",
                "category": "accessories",
                "price": 8499.0,
                "currency": "INR",
                "stock": 30,
                "rating": 4.8,
                "specs": {
                    "layout": "75% layout (84 keys)",
                    "switches": "Gateron G Pro Red (Linear, Pre-lubed, Hot-swappable)",
                    "connectivity": ["Bluetooth 5.1", "USB-C Wired 1000Hz"]
                }
            },
            {
                "id": "prod_keychron_q1_pro",
                "merchant_id": "merchant_001",
                "name": "Keychron Q1 Pro Full Aluminum Wireless Custom Mechanical Keyboard",
                "brand": "Keychron",
                "description": "Full CNC machined 6063 aluminum body, double-gasket acoustic mount design, screw-in PCB stabilizers, south-facing RGB, KSA double-shot PBT keycaps.",
                "category": "accessories",
                "price": 17990.0,
                "currency": "INR",
                "stock": 15,
                "rating": 5.0,
                "specs": {
                    "body": "Full CNC Machined Aluminum (1.7kg)",
                    "mount": "Double-Gasket Sound Dampened",
                    "switches": "Keychron K Pro Banana (Tactile, Hot-swappable)",
                    "connectivity": ["Bluetooth 5.1 (3 devices)", "USB-C 1000Hz"]
                }
            },
            {
                "id": "prod_anker_powerbank",
                "merchant_id": "merchant_001",
                "name": "Anker 737 Power Bank (PowerCore 24K, 140W Fast Charger)",
                "brand": "Anker",
                "description": "Ultra-powerful 24,000mAh capacity with Power Delivery 3.1 and bi-directional 140W fast charging, smart interactive digital display showing output/input wattage.",
                "category": "accessories",
                "price": 9999.0,
                "currency": "INR",
                "stock": 50,
                "rating": 4.9,
                "specs": {
                    "capacity": "24,000mAh (86.4Wh)",
                    "max_output": "140W single port",
                    "display": "Smart Digital Color Display",
                    "ports": ["2x USB-C (140W)", "1x USB-A (18W)"]
                }
            },
            {
                "id": "prod_anker_65w_nano",
                "merchant_id": "merchant_003",
                "name": "Anker Nano II 65W GaN Fast Wall Charger",
                "brand": "Anker",
                "description": "GaN II technology shrinks charger size by 58%, high-speed 65W charging for laptops, tablets, and smartphones, foldable pins, universal USB-C Power Delivery with PPS.",
                "category": "accessories",
                "price": 2499.0,
                "currency": "INR",
                "stock": 80,
                "rating": 4.8,
                "specs": {
                    "power_output": "65W USB-C Power Delivery (PPS)",
                    "technology": "GaN II semiconductor",
                    "dimensions": "Ultra-compact (4.2 x 3.6 x 3.8 cm)"
                }
            },
            {
                "id": "prod_baseus_100w_gan",
                "merchant_id": "merchant_002",
                "name": "Baseus 100W 4-Port GaN Desktop Fast Charging Station",
                "brand": "Baseus",
                "description": "100W total output with 2x USB-C and 2x USB-A ports, charges two laptops simultaneously, BPS II smart power distribution technology.",
                "category": "accessories",
                "price": 4499.0,
                "currency": "INR",
                "stock": 60,
                "rating": 4.6,
                "specs": {
                    "power_output": "100W USB-C PD 3.0",
                    "ports": ["2x USB-C (100W Max)", "2x USB-A (60W Max)"],
                    "technology": "GaN Pro Fast Charge"
                }
            },
            {
                "id": "prod_samsung_t7_shield",
                "merchant_id": "merchant_001",
                "name": "Samsung T7 Shield 2TB Rugged Portable External SSD",
                "brand": "Samsung",
                "description": "Superfast USB 3.2 Gen 2 transfer speeds up to 1,050 MB/s, IP65 rating for water and dust resistance, rugged elastomer outer shell drop-resistant up to 3 meters.",
                "category": "accessories",
                "price": 14999.0,
                "currency": "INR",
                "stock": 40,
                "rating": 4.9,
                "specs": {
                    "capacity": "2TB NVMe",
                    "read_write_speed": "Up to 1,050 MB/s",
                    "durability": "IP65 water/dust resistant, 3m drop proof"
                }
            },
            {
                "id": "prod_sandisk_extreme_1tb",
                "merchant_id": "merchant_003",
                "name": "SanDisk Extreme 1TB Portable External NVMe SSD",
                "brand": "SanDisk",
                "description": "NVMe solid state performance with 1050MB/s read and 1000MB/s write speeds in a portable, high-capacity drive, 2-meter drop protection and IP55 water/dust resistance.",
                "category": "accessories",
                "price": 8499.0,
                "currency": "INR",
                "stock": 60,
                "rating": 4.7,
                "specs": {
                    "capacity": "1TB NVMe",
                    "read_speed": "1,050 MB/s",
                    "durability": "IP55 rating with carabiner loop"
                }
            },
            {
                "id": "prod_caldigit_ts4",
                "merchant_id": "merchant_001",
                "name": "CalDigit TS4 Thunderbolt 4 18-Port Docking Station (98W Host Power)",
                "brand": "CalDigit",
                "description": "The flagship Thunderbolt 4 dock with 18 ports of connectivity, 98W Power Delivery, 2.5Gbps Ethernet, UHS-II SD/microSD slots, dual 6K or single 8K display support.",
                "category": "accessories",
                "price": 36990.0,
                "currency": "INR",
                "stock": 10,
                "rating": 4.9,
                "specs": {
                    "ports": "18 Ports (3x TB4, 5x USB-A, 3x USB-C, 2.5GbE, DP 1.4, SD 4.0)",
                    "power_delivery": "98W continuous charging to host laptop",
                    "display_support": "Up to Dual 6K 60Hz or Single 8K 60Hz"
                }
            },
            {
                "id": "prod_logitech_brio_4k",
                "merchant_id": "merchant_003",
                "name": "Logitech Brio 4K Ultra HD Streaming Webcam with HDR",
                "brand": "Logitech",
                "description": "Ultra 4K HD video calling with RightLight 3 and HDR technology, dual omnidirectional noise-canceling microphones, Windows Hello facial recognition infrared sensor.",
                "category": "accessories",
                "price": 16495.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.7,
                "specs": {
                    "resolution": "4K Ultra HD at 30 fps / 1080p at 60 fps",
                    "field_of_view": "Adjustable 65°, 78°, and 90°",
                    "features": "RightLight 3 with HDR, Windows Hello IR facial login"
                }
            },

            # =========================================================================
            # MONITORS & DISPLAYS (8 SKUs)
            # =========================================================================
            {
                "id": "prod_lg_27up850",
                "merchant_id": "merchant_001",
                "name": "LG 27-inch 4K UHD IPS Monitor with USB-C 96W Power Delivery",
                "brand": "LG",
                "description": "27-inch 4K UHD (3840 x 2160) IPS display with DCI-P3 95% color gamut, VESA DisplayHDR 400, USB Type-C with 96W power delivery, height/pivot/tilt adjustable stand.",
                "category": "displays",
                "price": 28990.0,
                "currency": "INR",
                "stock": 18,
                "rating": 4.7,
                "specs": {
                    "resolution": "4K UHD (3840 x 2160) at 60Hz",
                    "panel_type": "IPS (DCI-P3 95%)",
                    "usb_c_pd": "96W Power Delivery (single cable video + power)",
                    "ports": ["1x USB-C (96W)", "2x HDMI 2.0", "1x DisplayPort 1.4"]
                }
            },
            {
                "id": "prod_lg_27up850_reliance",
                "merchant_id": "merchant_002",
                "name": "LG 27-inch 4K UHD IPS Monitor with USB-C 96W PD (Reliance Promo)",
                "brand": "LG",
                "description": "27-inch 4K IPS display with 96W USB-C PD, DisplayHDR 400, color calibrated from factory. Includes complimentary high-speed HDMI cable.",
                "category": "displays",
                "price": 27490.0,
                "currency": "INR",
                "stock": 14,
                "rating": 4.8,
                "specs": {
                    "resolution": "4K UHD (3840 x 2160)",
                    "panel_type": "IPS (DCI-P3 95%)",
                    "usb_c_pd": "96W Power Delivery",
                    "bundle": "Free HDMI 2.1 Cable Included"
                }
            },
            {
                "id": "prod_dell_u2723qe",
                "merchant_id": "merchant_001",
                "name": "Dell UltraSharp 27 4K USB-C Hub Monitor (IPS Black Technology)",
                "brand": "Dell",
                "description": "Brilliant 27-inch 4K monitor featuring revolutionary IPS Black technology with 2000:1 contrast ratio, 100% sRGB and 98% DCI-P3, 90W USB-C PD, RJ45 Ethernet, built-in KVM switch.",
                "category": "displays",
                "price": 48500.0,
                "currency": "INR",
                "stock": 12,
                "rating": 4.9,
                "specs": {
                    "resolution": "4K UHD (3840 x 2160)",
                    "panel_type": "IPS Black (2000:1 contrast ratio, 98% DCI-P3)",
                    "hub_features": ["90W USB-C PD", "RJ45 1Gbps Ethernet", "Built-in KVM Switch"]
                }
            },
            {
                "id": "prod_asus_rog_oled_27",
                "merchant_id": "merchant_002",
                "name": "ASUS ROG Swift 27-inch 1440p 240Hz OLED Gaming Monitor (PG27AQDM)",
                "brand": "ASUS",
                "description": "Ultra-fast 27-inch QHD (2560x1440) OLED panel with 240Hz refresh rate and 0.03ms response time, custom heatsink, anti-glare micro-texture coating, 99% DCI-P3.",
                "category": "displays",
                "price": 78990.0,
                "currency": "INR",
                "stock": 8,
                "rating": 4.9,
                "specs": {
                    "resolution": "QHD (2560 x 1440)",
                    "panel_type": "OLED (240Hz, 0.03ms GTG)",
                    "color_gamut": "99% DCI-P3, Delta E < 2",
                    "ports": ["2x HDMI 2.0", "1x DisplayPort 1.4", "USB 3.2 Hub"]
                }
            },
            {
                "id": "prod_samsung_odyssey_g9",
                "merchant_id": "merchant_003",
                "name": "Samsung Odyssey OLED G9 49-inch Curved Dual QHD 240Hz Monitor",
                "brand": "Samsung",
                "description": "Massive 49-inch 32:9 curved OLED display (5120x1440), Neo Quantum Processor Pro, 0.03ms response time, DisplayHDR True Black 400, Gaming Hub with cloud gaming.",
                "category": "displays",
                "price": 129990.0,
                "currency": "INR",
                "stock": 5,
                "rating": 4.9,
                "specs": {
                    "resolution": "Dual QHD (5120 x 1440) 32:9 Aspect Ratio",
                    "panel_type": "Curved OLED (1800R, 240Hz, 0.03ms)",
                    "hdr": "DisplayHDR True Black 400",
                    "smart_features": "Built-in Tizen OS, Samsung Gaming Hub, IoT Hub"
                }
            },
            {
                "id": "prod_benq_pd2705u",
                "merchant_id": "merchant_003",
                "name": "BenQ PD2705U 27-inch 4K Designer Color-Accurate Monitor with Hotkey Puck",
                "brand": "BenQ",
                "description": "Factory calibrated 4K UHD IPS display, 99% sRGB and Rec.709, USB-C 65W, KVM switch, DualView mode, external Hotkey Puck G2 controller.",
                "category": "displays",
                "price": 42500.0,
                "currency": "INR",
                "stock": 15,
                "rating": 4.8,
                "specs": {
                    "resolution": "4K UHD (3840 x 2160)",
                    "color_accuracy": "100% sRGB, Calman & Pantone Validated",
                    "features": ["65W USB-C PD", "Built-in KVM Switch", "Hotkey Puck G2 Dial"]
                }
            },
            {
                "id": "prod_asus_zenscreen_portable",
                "merchant_id": "merchant_001",
                "name": "ASUS ZenScreen 15.6-inch Full HD Portable IPS USB-C Monitor",
                "brand": "ASUS",
                "description": "Ultra-portable 15.6-inch 1080p IPS monitor weighing just 780g, hybrid-signal USB-C and micro-HDMI connectivity, foldaway smart kickstand.",
                "category": "displays",
                "price": 16990.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.6,
                "specs": {
                    "resolution": "Full HD (1920 x 1080) IPS",
                    "weight": "780g (Ultra-slim 8.5mm profile)",
                    "connectivity": "USB Type-C (DP Alt mode), Micro-HDMI"
                }
            },
            {
                "id": "prod_gigabyte_m27q",
                "merchant_id": "merchant_002",
                "name": "Gigabyte M27Q 27-inch 170Hz 1440p SS-IPS Gaming Monitor with KVM",
                "brand": "Gigabyte",
                "description": "SuperSpeed IPS panel with 170Hz refresh rate and 0.5ms MPRT, 92% DCI-P3, integrated hardware KVM switch to control two devices with one mouse/keyboard.",
                "category": "displays",
                "price": 22990.0,
                "currency": "INR",
                "stock": 20,
                "rating": 4.7,
                "specs": {
                    "resolution": "QHD (2560 x 1440) at 170Hz",
                    "panel_type": "SuperSpeed IPS (0.5ms MPRT)",
                    "features": ["Hardware KVM Button", "USB-C Video/Hub", "VESA DisplayHDR 400"]
                }
            },

            # =========================================================================
            # OFFICE & DESK SETUP (6 SKUs)
            # =========================================================================
            {
                "id": "prod_desk_mat",
                "merchant_id": "merchant_003",
                "name": "Ergonomic Anti-Fatigue Extended Office Desk Mat (90cm x 40cm)",
                "brand": "OmniDesk",
                "description": "Dual-sided premium PU leather waterproof desk pad protector, smooth surface for high-precision optical mouse tracking, reinforced stitched edges.",
                "category": "office",
                "price": 1899.0,
                "currency": "INR",
                "stock": 120,
                "rating": 4.6,
                "specs": {
                    "dimensions": "90cm x 40cm",
                    "material": "Dual-sided Waterproof PU Leather",
                    "thickness": "2.0mm"
                }
            },
            {
                "id": "prod_benq_screenbar",
                "merchant_id": "merchant_001",
                "name": "BenQ ScreenBar Halo e-Reading LED Monitor Light Bar",
                "brand": "BenQ",
                "description": "Zero screen glare asymmetric optical design, wireless desktop control dial, auto-dimming ambient light sensor, customizable 2700K-6500K color temperature, back ambient light.",
                "category": "office",
                "price": 12990.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.9,
                "specs": {
                    "illumination": "Asymmetric Optical Design (Zero Screen Glare)",
                    "control": "Wireless 2.4GHz Desktop Dial",
                    "color_temperature": "2700K - 6500K adjustable (CRI > 95)"
                }
            },
            {
                "id": "prod_benq_screenbar_plus",
                "merchant_id": "merchant_002",
                "name": "BenQ ScreenBar Plus e-Reading LED Monitor Light with Desktop Dial",
                "brand": "BenQ",
                "description": "Asymmetric optical design prevents monitor glare, desktop wired dial with built-in light sensor for automatic brightness adjustment.",
                "category": "office",
                "price": 10990.0,
                "currency": "INR",
                "stock": 20,
                "rating": 4.8,
                "specs": {
                    "illumination": "Asymmetric Optical Design",
                    "control": "Wired Desktop Dial Sensor",
                    "color_temperature": "2700K - 6500K adjustable"
                }
            },
            {
                "id": "prod_elgato_stream_deck",
                "merchant_id": "merchant_003",
                "name": "Elgato Stream Deck MK.2 (15 Customizable Tactile LCD Keys)",
                "brand": "Elgato",
                "description": "15 programmable tactile LCD keys for one-touch studio control, launch apps, trigger automated developer scripts, mute mics, adjust lighting, and control workflows.",
                "category": "office",
                "price": 12490.0,
                "currency": "INR",
                "stock": 35,
                "rating": 4.9,
                "specs": {
                    "keys": "15 customizable LCD keys",
                    "interface": "USB 2.0 with detachable 45° desktop stand",
                    "integrations": "OBS, Discord, Spotify, GitHub, Home Assistant, VSCode"
                }
            },
            {
                "id": "prod_elgato_stream_deck_plus",
                "merchant_id": "merchant_001",
                "name": "Elgato Stream Deck + with Tactile Dials and Touch Strip",
                "brand": "Elgato",
                "description": "8 customizable LCD keys, 4 push-rotary endless dials, dynamic touch strip display for multi-layer volume, audio mixing, color correction, and workspace navigation.",
                "category": "office",
                "price": 19990.0,
                "currency": "INR",
                "stock": 18,
                "rating": 4.9,
                "specs": {
                    "controls": "8 LCD Keys + 4 Push Dials + Touch Strip",
                    "software": "Wave Link audio mixing software included",
                    "connectivity": "USB 2.0"
                }
            },
            {
                "id": "prod_ergorise_dual_arm",
                "merchant_id": "merchant_003",
                "name": "ErgoRise Heavy-Duty Gas Spring Dual Monitor Arm (Up to 32-inch)",
                "brand": "ErgoRise",
                "description": "Aerospace-grade aluminum mechanical gas spring arms, supports two monitors up to 9kg each (17\"-32\"), full 360° rotation, tilt, and swivel with integrated cable management channels.",
                "category": "office",
                "price": 6499.0,
                "currency": "INR",
                "stock": 40,
                "rating": 4.7,
                "specs": {
                    "monitor_support": "Dual 17\" to 32\" screens (up to 9kg per arm)",
                    "vesa": "75x75mm and 100x100mm",
                    "movement": "+90°/-45° tilt, 180° swivel, 360° rotation"
                }
            },

            # =========================================================================
            # SMART PAPER & BOOKS (6 SKUs)
            # =========================================================================
            {
                "id": "prod_kindle_paperwhite",
                "merchant_id": "merchant_003",
                "name": "Amazon Kindle Paperwhite 16 GB (6.8-inch 300 ppi Display)",
                "brand": "Amazon",
                "description": "6.8-inch glare-free paperwhite screen with 300 ppi resolution, adjustable warm light (amber to white), up to 10 weeks battery life, 20% faster page turns, IPX8 waterproof rating.",
                "category": "books",
                "price": 14999.0,
                "currency": "INR",
                "stock": 30,
                "rating": 4.8,
                "specs": {
                    "screen": "6.8-inch Paperwhite 300 ppi glare-free",
                    "storage": "16 GB (thousands of books)",
                    "battery_life": "Up to 10 weeks on single charge",
                    "waterproofing": "IPX8 (survives immersion in 2m freshwater for 60 mins)",
                    "connectivity": "Wi-Fi, Bluetooth for Audible"
                }
            },
            {
                "id": "prod_kindle_paperwhite_reliance",
                "merchant_id": "merchant_002",
                "name": "Amazon Kindle Paperwhite 16 GB (Black) - Reliance Store Edition",
                "brand": "Amazon",
                "description": "6.8-inch 300 ppi glare-free display, adjustable warm light, 10 weeks battery life. Includes 3 months Kindle Unlimited trial voucher.",
                "category": "books",
                "price": 14499.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.8,
                "specs": {
                    "screen": "6.8-inch Paperwhite 300 ppi",
                    "storage": "16 GB",
                    "battery_life": "Up to 10 weeks",
                    "bundle": "Includes 3 Months Kindle Unlimited Voucher"
                }
            },
            {
                "id": "prod_kindle_scribe",
                "merchant_id": "merchant_003",
                "name": "Amazon Kindle Scribe 32 GB (10.2-inch 300 ppi with Premium Pen)",
                "brand": "Amazon",
                "description": "The first Kindle that is both a digital notebook and e-reader, 10.2-inch 300 ppi front-lit display, included battery-free Premium Pen with dedicated eraser and shortcut button, convert handwriting to text.",
                "category": "books",
                "price": 36999.0,
                "currency": "INR",
                "stock": 15,
                "rating": 4.8,
                "specs": {
                    "screen": "10.2-inch Paperwhite 300 ppi with Glare-Free glass",
                    "storage": "32 GB",
                    "pen": "Battery-free Premium Pen with eraser & shortcut button",
                    "features": "Handwriting to text conversion, PDF markup, notebooks"
                }
            },
            {
                "id": "prod_remarkable_2",
                "merchant_id": "merchant_003",
                "name": "reMarkable 2 Digital Paper Tablet with Marker Plus",
                "brand": "reMarkable",
                "description": "The world's thinnest tablet at 4.7mm, textured CANVAS display mimicking physical paper friction, distraction-free note-taking, reading, and sketching, weeks of battery life, cloud synchronization.",
                "category": "books",
                "price": 39999.0,
                "currency": "INR",
                "stock": 10,
                "rating": 4.9,
                "specs": {
                    "thickness": "4.7 mm (world's thinnest tablet)",
                    "display": "10.3-inch monochrome digital paper (226 DPI)",
                    "pen": "Marker Plus with built-in digital eraser",
                    "battery_life": "Up to 2 weeks"
                }
            },
            {
                "id": "prod_remarkable_2_croma",
                "merchant_id": "merchant_001",
                "name": "reMarkable 2 Digital Paper Tablet (Includes Folio Case & Marker Plus)",
                "brand": "reMarkable",
                "description": "Ultra-slim 4.7mm e-ink paper tablet with premium polymer weave gray folio protective sleeve and Marker Plus with digital eraser.",
                "category": "books",
                "price": 41990.0,
                "currency": "INR",
                "stock": 8,
                "rating": 4.9,
                "specs": {
                    "thickness": "4.7 mm",
                    "display": "10.3-inch monochrome digital paper",
                    "bundle": "Includes Gray Polymer Weave Folio Case"
                }
            },
            {
                "id": "prod_onyx_boox_note_air3",
                "merchant_id": "merchant_003",
                "name": "Onyx Boox Note Air3 C Color E-Ink Android Tablet (10.3-inch Kaleido 3)",
                "brand": "Onyx Boox",
                "description": "Color E-Ink tablet running open Android 12 with Google Play Store, Kaleido 3 glass screen, BSR (BOOX Super Refresh) technology, stylus with 4096 levels of pressure sensitivity.",
                "category": "books",
                "price": 49990.0,
                "currency": "INR",
                "stock": 12,
                "rating": 4.8,
                "specs": {
                    "screen": "10.3-inch Kaleido 3 Color E-Ink (300 ppi B&W, 150 ppi Color)",
                    "os": "Android 12 with Google Play Store",
                    "storage": "64GB UFS 2.2 + MicroSD slot",
                    "ram": "4GB LPDDR4X"
                }
            },
            # =========================================================================
            # WEARABLES & SMARTWATCHES (5 SKUs)
            # =========================================================================
            {
                "id": "prod_apple_watch_s9",
                "merchant_id": "merchant_003",
                "name": "Apple Watch Series 9 GPS 45mm Midnight Aluminum with Sport Band",
                "brand": "Apple",
                "description": "Powerful S9 SiP chip, double tap gesture, brighter Always-On display, crash detection, ECG, blood oxygen, 50m water resistant.",
                "category": "wearables",
                "price": 41900.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.9,
                "specs": {
                    "display": "Always-On Retina OLED (2000 nits)",
                    "processor": "Apple S9 SiP",
                    "battery": "18 hours all-day life",
                    "water_resistance": "50m Swimproof"
                }
            },
            {
                "id": "prod_samsung_galaxy_watch6",
                "merchant_id": "merchant_001",
                "name": "Samsung Galaxy Watch 6 Bluetooth 44mm (Graphite)",
                "brand": "Samsung",
                "description": "Super AMOLED display, advanced sleep coaching, body composition analysis (BIA), heart health monitoring, Sapphire Crystal glass.",
                "category": "wearables",
                "price": 26999.0,
                "currency": "INR",
                "stock": 30,
                "rating": 4.7,
                "specs": {
                    "display": "1.5-inch Super AMOLED (480x480)",
                    "processor": "Exynos W930 Dual Core",
                    "battery": "40 hours",
                    "durability": "MIL-STD-810H + 5ATM + IP68"
                }
            },
            {
                "id": "prod_oneplus_watch_2",
                "merchant_id": "merchant_002",
                "name": "OnePlus Watch 2 with Dual-Engine Architecture (Wear OS 4)",
                "brand": "OnePlus",
                "description": "Dual-engine architecture with Snapdragon W5 Gen 1, up to 100 hours of battery in Smart Mode, 1.43-inch AMOLED, sapphire crystal, dual-frequency GPS.",
                "category": "wearables",
                "price": 24999.0,
                "currency": "INR",
                "stock": 20,
                "rating": 4.8,
                "specs": {
                    "display": "1.43-inch AMOLED (466x466)",
                    "battery": "100 hours Smart Mode, 12 days Power Saver",
                    "os": "Google Wear OS 4 + RTOS",
                    "gps": "Dual Frequency L1+L5 GPS"
                }
            },
            {
                "id": "prod_noise_colorfit_pro5",
                "merchant_id": "merchant_001",
                "name": "Noise ColorFit Pro 5 Smartwatch with 1.85-inch AMOLED Display",
                "brand": "Noise",
                "description": "1.85-inch AMOLED display, Tru Sync Bluetooth calling, functional crown, 100+ sports modes, 7 days battery, Noise Health Suite with SpO2 and 24/7 heart rate.",
                "category": "wearables",
                "price": 3499.0,
                "currency": "INR",
                "stock": 80,
                "rating": 4.5,
                "specs": {
                    "display": "1.85-inch AMOLED (390x450)",
                    "battery": "7 days typical usage",
                    "bluetooth_calling": "Tru Sync Single-Chip BT Calling",
                    "water_resistance": "IP68 Dust and Water Resistant"
                }
            },
            {
                "id": "prod_boat_wave_call2",
                "merchant_id": "merchant_003",
                "name": "boAt Wave Call 2 Smartwatch with 1.83-inch HD Display",
                "brand": "boAt",
                "description": "1.83-inch HD display, advanced Bluetooth calling with dial pad, 700+ active modes, live cricket scores, IP67 dust and water resistance.",
                "category": "wearables",
                "price": 1499.0,
                "currency": "INR",
                "stock": 120,
                "rating": 4.3,
                "specs": {
                    "display": "1.83-inch HD 2.5D Curved Display",
                    "battery": "5 days battery backup",
                    "bluetooth_calling": "Dedicated speaker and mic",
                    "water_resistance": "IP67"
                }
            },
            # =========================================================================
            # FINE-GRAINED EARBUDS (2 SKUs)
            # =========================================================================
            {
                "id": "prod_oneplus_buds_pro2",
                "merchant_id": "merchant_002",
                "name": "OnePlus Buds Pro 2 True Wireless Earbuds with Dynaudio & Smart ANC",
                "brand": "OnePlus",
                "description": "Co-created with Dynaudio, MelodyBoost dual drivers, 48dB Smart Adaptive Noise Cancellation, spatial audio with head tracking, up to 39 hours playback.",
                "category": "audio",
                "price": 9999.0,
                "currency": "INR",
                "stock": 40,
                "rating": 4.7,
                "specs": {
                    "noise_cancellation": "Smart Adaptive 48dB ANC",
                    "battery_life": "39 hours with charging case",
                    "connectivity": ["Bluetooth 5.3", "Google Fast Pair"],
                    "driver": "11mm woofer + 6mm tweeter dual drivers"
                }
            },
            {
                "id": "prod_realme_buds_air5",
                "merchant_id": "merchant_001",
                "name": "realme Buds Air 5 Pro True Wireless Earbuds (50dB ANC)",
                "brand": "realme",
                "description": "Flagship 50dB Deep Sea Noise Cancellation 2.0, dual coaxial drivers (11mm bass + 6mm planar tweeter), 40 hours battery, LDAC Hi-Res Audio certification.",
                "category": "audio",
                "price": 4499.0,
                "currency": "INR",
                "stock": 60,
                "rating": 4.6,
                "specs": {
                    "noise_cancellation": "50dB Active Noise Cancellation",
                    "battery_life": "40 hours playback",
                    "audio_codec": "LDAC, AAC, SBC",
                    "driver": "11mm dynamic + 6mm planar tweeter"
                }
            },
            # =========================================================================
            # NEW EXPANDED CATALOG: MICE (4 SKUs)
            # =========================================================================
            {
                "id": "prod_razer_deathadder_v3",
                "merchant_id": "merchant_001",
                "name": "Razer DeathAdder V3 Ultra-Lightweight Ergonomic Gaming Mouse",
                "brand": "Razer",
                "description": "59g ultra-lightweight ergonomic design, Focus Pro 30K Optical Sensor, Gen-3 Optical Mouse Switches, 8000Hz polling rate.",
                "category": "accessories",
                "price": 5499.0,
                "currency": "INR",
                "stock": 45,
                "rating": 4.8,
                "specs": {
                    "sensor": "Focus Pro 30K Optical Sensor",
                    "dpi": "30,000 DPI",
                    "weight": "59g",
                    "switch_type": "Optical Mouse Switches Gen-3"
                }
            },
            {
                "id": "prod_logitech_g502_x",
                "merchant_id": "merchant_002",
                "name": "Logitech G502 X Wireless Gaming Mouse with LIGHTFORCE Hybrid Switches",
                "brand": "Logitech",
                "description": "LIGHTFORCE hybrid optical-mechanical switches, HERO 25K gaming sensor, 13 programmable controls, dual-mode hyper-fast scroll wheel.",
                "category": "accessories",
                "price": 7995.0,
                "currency": "INR",
                "stock": 35,
                "rating": 4.9,
                "specs": {
                    "sensor": "HERO 25K Sensor",
                    "dpi": "25,600 DPI",
                    "battery_life": "140 hours constant motion",
                    "switches": "LIGHTFORCE Hybrid Optical-Mechanical"
                }
            },
            {
                "id": "prod_apple_magic_mouse",
                "merchant_id": "merchant_003",
                "name": "Apple Magic Mouse Wireless Multi-Touch Surface",
                "brand": "Apple",
                "description": "Wireless and rechargeable Bluetooth mouse with Multi-Touch surface allowing gestures like swiping between web pages and scrolling documents.",
                "category": "accessories",
                "price": 7500.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.5,
                "specs": {
                    "connectivity": "Bluetooth & Lightning/USB-C",
                    "surface": "Multi-Touch Gesture Surface",
                    "battery": "Built-in Rechargeable Lithium-ion"
                }
            },
            {
                "id": "prod_dell_ms5320w",
                "merchant_id": "merchant_001",
                "name": "Dell Premier Multi-Device Wireless Mouse MS5320W",
                "brand": "Dell",
                "description": "Seamlessly work across 3 PCs with 2.4GHz wireless and Bluetooth 5.0 connectivity. 36-month battery life with 1600 DPI optical sensor.",
                "category": "accessories",
                "price": 2999.0,
                "currency": "INR",
                "stock": 50,
                "rating": 4.6,
                "specs": {
                    "connectivity": "2.4GHz Wireless & Dual Bluetooth 5.0",
                    "battery_life": "36 months",
                    "dpi": "1600 DPI adjustable",
                    "multi_device": "Up to 3 devices"
                }
            },
            # =========================================================================
            # NEW EXPANDED CATALOG: KEYBOARDS (4 SKUs)
            # =========================================================================
            {
                "id": "prod_logitech_mx_keys_s",
                "merchant_id": "merchant_001",
                "name": "Logitech MX Keys S Advanced Wireless Illuminated Keyboard",
                "brand": "Logitech",
                "description": "Low-profile spherically dished keys, smart backlighting with proximity sensors, Smart Actions automations, multi-device easy-switch.",
                "category": "accessories",
                "price": 9995.0,
                "currency": "INR",
                "stock": 30,
                "rating": 4.9,
                "specs": {
                    "key_type": "Perfect Stroke Spherically Dished Keys",
                    "backlight": "Smart Illumination with hand proximity",
                    "battery_life": "10 days (5 months without backlight)",
                    "connectivity": "Logi Bolt USB Receiver & Bluetooth Low Energy"
                }
            },
            {
                "id": "prod_razer_blackwidow_v4",
                "merchant_id": "merchant_003",
                "name": "Razer BlackWidow V4 Mechanical Gaming Keyboard with Green Clicky Switches",
                "brand": "Razer",
                "description": "Razer Green Mechanical Switches with tactile bump and clicky feedback, multi-function roller and 4 macro keys, Chroma RGB lighting.",
                "category": "accessories",
                "price": 13999.0,
                "currency": "INR",
                "stock": 20,
                "rating": 4.7,
                "specs": {
                    "switch_type": "Razer Green Clicky Mechanical Switches",
                    "polling_rate": "Up to 8000Hz",
                    "lighting": "Razer Chroma RGB per-key",
                    "macro_keys": "4 Dedicated Macro Keys"
                }
            },
            {
                "id": "prod_redragon_k552",
                "merchant_id": "merchant_002",
                "name": "Redragon K552 Kumara Tenkeyless Mechanical Keyboard Red Switches",
                "brand": "Redragon",
                "description": "Compact 87-key space-saving TKL mechanical keyboard with linear quiet red switches, metal construction, and rainbow LED backlighting.",
                "category": "accessories",
                "price": 2899.0,
                "currency": "INR",
                "stock": 60,
                "rating": 4.5,
                "specs": {
                    "layout": "87-Key Tenkeyless (TKL)",
                    "switches": "Linear Red Mechanical Switches",
                    "construction": "Aircraft-grade aluminum base"
                }
            },
            {
                "id": "prod_apple_magic_keyboard",
                "merchant_id": "merchant_003",
                "name": "Apple Magic Keyboard with Touch ID and Numeric Keypad",
                "brand": "Apple",
                "description": "Wireless rechargeable keyboard with Touch ID fingerprint authentication for fast secure logins, scissor mechanism, and numeric keypad.",
                "category": "accessories",
                "price": 17500.0,
                "currency": "INR",
                "stock": 15,
                "rating": 4.8,
                "specs": {
                    "authentication": "Touch ID Sensor",
                    "layout": "Full Size with Numeric Keypad",
                    "connectivity": "Bluetooth & USB-C to Lightning"
                }
            },
            # =========================================================================
            # NEW EXPANDED CATALOG: WEBCAMS (3 SKUs)
            # =========================================================================
            {
                "id": "prod_logitech_c920",
                "merchant_id": "merchant_001",
                "name": "Logitech C920 Pro Full HD 1080p Webcam with Stereo Audio",
                "brand": "Logitech",
                "description": "Full HD 1080p at 30fps video calling with auto light correction, dual stereo microphones with automatic noise reduction, glass lens.",
                "category": "accessories",
                "price": 6495.0,
                "currency": "INR",
                "stock": 40,
                "rating": 4.7,
                "specs": {
                    "resolution": "Full HD 1080p / 30fps",
                    "field_of_view": "78 degrees",
                    "microphones": "Dual stereo omni-directional mics",
                    "lens": "Full HD Glass Lens with Auto-focus"
                }
            },
            {
                "id": "prod_elgato_facecam",
                "merchant_id": "merchant_003",
                "name": "Elgato Facecam Full HD 1080p60 Uncompressed Streaming Camera",
                "brand": "Elgato",
                "description": "Studio-grade f/2.4 24mm all-glass Elgato Prime Lens, Sony STARVIS CMOS Sensor, uncompressed 1080p at 60 fps with onboard flash memory.",
                "category": "accessories",
                "price": 14990.0,
                "currency": "INR",
                "stock": 18,
                "rating": 4.8,
                "specs": {
                    "sensor": "Sony STARVIS CMOS Sensor",
                    "resolution": "1080p60 Uncompressed",
                    "optics": "Elgato Prime Lens (f/2.4 24mm)",
                    "connectivity": "USB 3.0 Type-C"
                }
            },
            {
                "id": "prod_anker_powerconf_c200",
                "merchant_id": "merchant_002",
                "name": "Anker PowerConf C200 2K Webcam with Dual Noise-Canceling Mics",
                "brand": "Anker",
                "description": "2K ultra-clear resolution with adjustable field of view (65/78/95 degrees), built-in physical privacy cover, AI dual-mic noise reduction.",
                "category": "accessories",
                "price": 4999.0,
                "currency": "INR",
                "stock": 35,
                "rating": 4.6,
                "specs": {
                    "resolution": "2K QHD (2560x1440) at 30fps",
                    "field_of_view": "Adjustable 65°, 78°, 95°",
                    "privacy": "Built-in physical privacy shutter"
                }
            },
            # =========================================================================
            # NEW EXPANDED CATALOG: CHARGERS & POWER BANKS (3 SKUs)
            # =========================================================================
            {
                "id": "prod_baseus_blade_100w",
                "merchant_id": "merchant_002",
                "name": "Baseus Blade 100W Ultra-Thin Laptop Power Bank 20000mAh",
                "brand": "Baseus",
                "description": "Ultra-slim 18mm profile 20000mAh battery pack capable of 100W Power Delivery output to fast-charge laptops, MacBooks, and tablets.",
                "category": "accessories",
                "price": 6499.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.7,
                "specs": {
                    "capacity": "20,000mAh / 74Wh",
                    "max_output": "100W USB-C Power Delivery",
                    "ports": "2x USB-C + 2x USB-A",
                    "display": "Digital status screen for power and time remaining"
                }
            },
            {
                "id": "prod_mi_powerbank_50w",
                "merchant_id": "merchant_001",
                "name": "Xiaomi Mi 20000mAh 50W Fast Charging Power Bank 3 Pro",
                "brand": "Xiaomi",
                "description": "50W max flash charging port for laptops and smartphones, triple port output, supports low-current charging for earbuds and smartwatches.",
                "category": "accessories",
                "price": 3499.0,
                "currency": "INR",
                "stock": 45,
                "rating": 4.5,
                "specs": {
                    "capacity": "20,000mAh",
                    "output": "50W MAX Type-C output",
                    "protection": "12-layer circuit protection"
                }
            },
            {
                "id": "prod_belkin_boostcharge_3in1",
                "merchant_id": "merchant_003",
                "name": "Belkin BoostCharge Pro 3-in-1 MagSafe 15W Wireless Charging Stand",
                "brand": "Belkin",
                "description": "Official Made for MagSafe 15W fast wireless charging stand for iPhone, Apple Watch, and AirPods simultaneously in premium chrome and silicone finish.",
                "category": "accessories",
                "price": 11999.0,
                "currency": "INR",
                "stock": 20,
                "rating": 4.8,
                "specs": {
                    "magsafe_output": "15W official MagSafe fast charging",
                    "devices": "Charges 3 devices simultaneously",
                    "compatibility": "iPhone 12-15, Apple Watch Series 7-9/Ultra, AirPods Pro"
                }
            },
            # =========================================================================
            # NEW EXPANDED CATALOG: HEADPHONES (4 SKUs)
            # =========================================================================
            {
                "id": "prod_sony_wh1000xm5_croma",
                "merchant_id": "merchant_001",
                "name": "Sony WH-1000XM5 Wireless Industry Leading Noise Canceling Headphones",
                "brand": "Sony",
                "description": "Two processors and 8 microphones for unprecedented ANC, Auto NC Optimizer, 30mm carbon fiber composite driver, 30 hours battery life with quick charge.",
                "category": "audio",
                "price": 29990.0,
                "currency": "INR",
                "stock": 30,
                "rating": 4.9,
                "specs": {
                    "anc_processor": "Integrated Processor V1 + HD Noise Cancelling QN1",
                    "battery_life": "30 hours (ANC on)",
                    "codecs": "LDAC, AAC, SBC",
                    "mics": "8 microphones with beamforming"
                }
            },
            {
                "id": "prod_sennheiser_momentum4",
                "merchant_id": "merchant_003",
                "name": "Sennheiser Momentum 4 Wireless ANC Headphones with 60-Hour Battery",
                "brand": "Sennheiser",
                "description": "Audiophile-inspired 42mm transducer system, adaptive noise cancellation, transparency mode, class-leading 60-hour battery life.",
                "category": "audio",
                "price": 24990.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.8,
                "specs": {
                    "driver": "42mm dynamic transducer",
                    "battery_life": "60 hours playback with ANC",
                    "audio_codecs": "aptX Adaptive, aptX, AAC, SBC"
                }
            },
            {
                "id": "prod_boat_rockerz_550_reliance",
                "merchant_id": "merchant_002",
                "name": "boAt Rockerz 550 Over-Ear Wireless Bluetooth Headphones",
                "brand": "boAt",
                "description": "50mm dynamic drivers with boAt Signature Sound, physical noise isolation cushions, up to 20 hours battery life, Bluetooth 5.0 and AUX mode.",
                "category": "audio",
                "price": 1799.0,
                "currency": "INR",
                "stock": 80,
                "rating": 4.4,
                "specs": {
                    "driver": "50mm Dynamic Drivers",
                    "battery_life": "20 hours playback",
                    "connectivity": "Bluetooth 5.0 + 3.5mm AUX"
                }
            },
            {
                "id": "prod_audio_technica_m50x",
                "merchant_id": "merchant_003",
                "name": "Audio-Technica ATH-M50x Professional Studio Monitor Headphones",
                "brand": "Audio-Technica",
                "description": "Critically acclaimed sonic performance praised by top audio engineers, proprietary 45mm large-aperture drivers with rare earth magnets.",
                "category": "audio",
                "price": 11499.0,
                "currency": "INR",
                "stock": 35,
                "rating": 4.9,
                "specs": {
                    "driver": "45mm large-aperture drivers",
                    "frequency_response": "15 - 28,000 Hz",
                    "earcups": "90-degree swiveling earcups for one-ear monitoring"
                }
            },
            # =========================================================================
            # NEW EXPANDED CATALOG: EARBUDS / TWS (4 SKUs)
            # =========================================================================
            {
                "id": "prod_apple_airpods_pro_2",
                "merchant_id": "merchant_003",
                "name": "Apple AirPods Pro 2 Wireless Earbuds with USB-C and Active Noise Cancellation",
                "brand": "Apple",
                "description": "Apple H2 chip, up to 2x more Active Noise Cancellation, Adaptive Audio, Transparency mode, Conversation Awareness, USB-C MagSafe case with speaker.",
                "category": "audio",
                "price": 24900.0,
                "currency": "INR",
                "stock": 40,
                "rating": 4.9,
                "specs": {
                    "processor": "Apple H2 Headphone Chip",
                    "anc": "2x Active Noise Cancellation + Adaptive Audio",
                    "battery_life": "6 hours (30 hours with case)",
                    "dust_water_resistance": "IP54 sweat and water resistant"
                }
            },
            {
                "id": "prod_sony_wf1000xm5_croma",
                "merchant_id": "merchant_001",
                "name": "Sony WF-1000XM5 Truly Wireless Noise Canceling Earbuds",
                "brand": "Sony",
                "description": "Integrated Processor V2 and HD Noise Cancelling Processor QN2e, Dynamic Driver X for wide frequency reproduction, Bone conduction sensors for clear calls.",
                "category": "audio",
                "price": 23990.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.8,
                "specs": {
                    "processor": "Integrated Processor V2 + QN2e",
                    "driver": "8.4mm Dynamic Driver X",
                    "hi_res_audio": "LDAC Wireless Hi-Res certified"
                }
            },
            {
                "id": "prod_nothing_ear_a",
                "merchant_id": "merchant_002",
                "name": "Nothing Ear (a) Hi-Res Audio True Wireless Earbuds with 45dB Smart ANC",
                "brand": "Nothing",
                "description": "Transparent iconic design with bright yellow finish, 11mm PMI + TPU dynamic drivers, 45dB smart active noise cancellation, LDAC Hi-Res audio, 42.5h total playback.",
                "category": "audio",
                "price": 6999.0,
                "currency": "INR",
                "stock": 50,
                "rating": 4.7,
                "specs": {
                    "driver": "11mm Dynamic Driver (PMI + TPU)",
                    "anc": "45dB Smart Active Noise Cancellation",
                    "battery_life": "42.5 hours total with case",
                    "codec": "LDAC Hi-Res Audio"
                }
            },
            {
                "id": "prod_samsung_galaxy_buds2_pro",
                "merchant_id": "merchant_001",
                "name": "Samsung Galaxy Buds 2 Pro 24-Bit Hi-Fi Sound ANC Earbuds",
                "brand": "Samsung",
                "description": "24-bit Hi-Fi audio with Samsung Seamless Codec, intelligent 3-mic Active Noise Cancellation, 360 Audio with direct multi-channel, IPX7 water resistance.",
                "category": "audio",
                "price": 11999.0,
                "currency": "INR",
                "stock": 35,
                "rating": 4.7,
                "specs": {
                    "audio_quality": "24-Bit Hi-Fi Audio with SSC",
                    "anc": "Intelligent Active Noise Cancelling",
                    "water_resistance": "IPX7 certified"
                }
            },
            # =========================================================================
            # NEW EXPANDED CATALOG: MICROPHONES (4 SKUs)
            # =========================================================================
            {
                "id": "prod_blue_yeti",
                "merchant_id": "merchant_001",
                "name": "Logitech Blue Yeti USB Microphone for Recording and Streaming",
                "brand": "Logitech",
                "description": "Custom 3-capsule array produces clear broadcast-quality sound. Four pickup patterns (cardioid, omni, bidirectional, stereo) for podcasting, streaming, and music.",
                "category": "audio",
                "price": 9995.0,
                "currency": "INR",
                "stock": 30,
                "rating": 4.8,
                "specs": {
                    "capsules": "3 proprietary 14mm condenser capsules",
                    "polar_patterns": "Cardioid, Bidirectional, Omnidirectional, Stereo",
                    "frequency_response": "20Hz - 20kHz",
                    "connectivity": "USB plug-and-play"
                }
            },
            {
                "id": "prod_elgato_wave3",
                "merchant_id": "merchant_003",
                "name": "Elgato Wave:3 Premium USB Condenser Microphone with Digital Mixing",
                "brand": "Elgato",
                "description": "Cardioid condenser capsule with tight speech pickup, 24-bit 96kHz analog-to-digital converter, proprietary Clipguard anti-distortion technology.",
                "category": "audio",
                "price": 14990.0,
                "currency": "INR",
                "stock": 20,
                "rating": 4.9,
                "specs": {
                    "sample_rate": "24-bit / 96kHz",
                    "capsule": "17mm Electret Condenser",
                    "technology": "Clipguard anti-distortion limiter",
                    "software": "Wave Link Digital Mixer included"
                }
            },
            {
                "id": "prod_rode_videomic_go2",
                "merchant_id": "merchant_002",
                "name": "Rode VideoMic GO II Lightweight Directional Microphone",
                "brand": "Rode",
                "description": "Broadcast-quality compact shotgun microphone with dual 3.5mm TRS and USB-C audio outputs for cameras, smartphones, and computers.",
                "category": "audio",
                "price": 8990.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.7,
                "specs": {
                    "polar_pattern": "Supercardioid directional pickup",
                    "output": "3.5mm TRS and USB-C digital audio",
                    "weight": "89g ultra-lightweight"
                }
            },
            {
                "id": "prod_fifine_k669b",
                "merchant_id": "merchant_003",
                "name": "Fifine K669B USB Cardioid Condenser Studio Vocal Microphone",
                "brand": "Fifine",
                "description": "Budget broadcast USB condenser microphone with solid metal body, volume gain knob, tripod stand, ideal for gaming, Discord, and voiceovers.",
                "category": "audio",
                "price": 2690.0,
                "currency": "INR",
                "stock": 50,
                "rating": 4.5,
                "specs": {
                    "polar_pattern": "Uni-directional Cardioid",
                    "body": "All-metal construction",
                    "controls": "On-mic volume gain knob"
                }
            },
            # =========================================================================
            # NEW EXPANDED CATALOG: SPEAKERS (4 SKUs)
            # =========================================================================
            {
                "id": "prod_jbl_flip6",
                "merchant_id": "merchant_001",
                "name": "JBL Flip 6 Portable Waterproof Bluetooth Speaker with 2-Way Speaker System",
                "brand": "JBL",
                "description": "2-way speaker system delivering loud powerful sound, IP67 waterproof and dustproof, 12 hours of playtime, PartyBoost multi-speaker pairing.",
                "category": "audio",
                "price": 9999.0,
                "currency": "INR",
                "stock": 40,
                "rating": 4.8,
                "specs": {
                    "output_power": "30W RMS (20W woofer + 10W tweeter)",
                    "battery_life": "12 hours playback",
                    "waterproofing": "IP67 waterproof & dustproof",
                    "connectivity": "Bluetooth 5.1"
                }
            },
            {
                "id": "prod_marshall_emberton2",
                "merchant_id": "merchant_003",
                "name": "Marshall Emberton II Portable Bluetooth Stereo Speaker",
                "brand": "Marshall",
                "description": "True Stereophonic multi-directional 360-degree sound, iconic vintage Marshall textured silicone casing, 30+ hours of portable playtime, IP67 rating.",
                "category": "audio",
                "price": 15999.0,
                "currency": "INR",
                "stock": 20,
                "rating": 4.9,
                "specs": {
                    "battery_life": "30+ hours on single charge",
                    "sound_type": "True Stereophonic 360-degree audio",
                    "waterproofing": "IP67 dust and water resistance",
                    "fast_charge": "20 min charge = 4 hours playtime"
                }
            },
            {
                "id": "prod_bose_soundlink_flex",
                "merchant_id": "merchant_002",
                "name": "Bose SoundLink Flex Bluetooth Portable Outdoor Waterproof Speaker",
                "brand": "Bose",
                "description": "Custom engineered transducer for deep rich audio, PositionIQ technology detects orientation and optimizes sound, IP67 waterproof (floats in water).",
                "category": "audio",
                "price": 14900.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.8,
                "specs": {
                    "technology": "PositionIQ Auto-Orientation Sound Adjustment",
                    "waterproofing": "IP67 rated & floatable",
                    "battery_life": "Up to 12 hours"
                }
            },
            {
                "id": "prod_sony_srs_xb100",
                "merchant_id": "merchant_001",
                "name": "Sony SRS-XB100 Compact Wireless Portable Travel Speaker with Extra Bass",
                "brand": "Sony",
                "description": "Sound Diffusion Processor expands sound in any space, Extra Bass compact radiator, 16 hours battery life, hands-free calling with echo cancellation.",
                "category": "audio",
                "price": 3990.0,
                "currency": "INR",
                "stock": 60,
                "rating": 4.6,
                "specs": {
                    "battery_life": "16 hours battery with indicator",
                    "sound": "Sound Diffusion Processor with Extra Bass",
                    "waterproofing": "IP67 waterproof and dustproof"
                }
            },
            # =========================================================================
            # NEW EXPANDED CATALOG: LAPTOPS (4 SKUs)
            # =========================================================================
            {
                "id": "prod_asus_rog_zephyrus_g14",
                "merchant_id": "merchant_002",
                "name": "ASUS ROG Zephyrus G14 OLED Gaming Laptop Ryzen 9 32GB RAM RTX 4070",
                "brand": "ASUS",
                "description": "14-inch 3K 120Hz 0.2ms OLED ROG Nebula Display, AMD Ryzen 9 8945HS processor, 32GB LPDDR5X RAM, 1TB NVMe Gen4 SSD, NVIDIA GeForce RTX 4070 8GB.",
                "category": "electronics",
                "price": 174990.0,
                "currency": "INR",
                "stock": 10,
                "rating": 4.9,
                "specs": {
                    "processor": "AMD Ryzen 9 8945HS (8 cores / 16 threads)",
                    "ram": "32GB LPDDR5X 6400MHz",
                    "storage": "1TB PCIe 4.0 NVMe SSD",
                    "gpu": "NVIDIA GeForce RTX 4070 8GB GDDR6",
                    "display": "14-inch 3K (2880 x 1800) OLED 120Hz"
                }
            },
            {
                "id": "prod_lenovo_thinkpad_x1_amazon",
                "merchant_id": "merchant_003",
                "name": "Lenovo ThinkPad X1 Carbon Gen 11 Ultrabook Intel i7 32GB RAM 1TB SSD",
                "brand": "Lenovo",
                "description": "Ultralight carbon-fiber chassis (1.12kg), Intel Core i7-1365U vPro, 32GB LPDDR5 RAM, 1TB PCIe 4.0 SSD, 14\" 2.8K OLED anti-glare display.",
                "category": "electronics",
                "price": 159990.0,
                "currency": "INR",
                "stock": 12,
                "rating": 4.9,
                "specs": {
                    "processor": "Intel Core i7-1365U vPro",
                    "ram": "32GB LPDDR5",
                    "storage": "1TB PCIe Gen4 SSD",
                    "display": "14-inch 2.8K (2880x1800) OLED Display",
                    "weight": "1.12 kg ultralight"
                }
            },
            {
                "id": "prod_hp_spectre_x360",
                "merchant_id": "merchant_001",
                "name": "HP Spectre x360 14 2-in-1 OLED Laptop Intel Core Ultra 7 16GB RAM",
                "brand": "HP",
                "description": "Intel Core Ultra 7 155H with Intel AI Boost NPU, 14-inch 2.8K 120Hz IMAX Enhanced OLED touch display, 16GB LPDDR5x RAM, 1TB SSD, rechargeable tilt pen.",
                "category": "electronics",
                "price": 134990.0,
                "currency": "INR",
                "stock": 15,
                "rating": 4.8,
                "specs": {
                    "processor": "Intel Core Ultra 7 155H (Intel Arc Graphics)",
                    "ram": "16GB LPDDR5x RAM",
                    "display": "14-inch 2.8K (2880x1800) OLED Touchscreen 120Hz",
                    "form_factor": "2-in-1 Convertible Laptop"
                }
            },
            {
                "id": "prod_dell_inspiron_15",
                "merchant_id": "merchant_001",
                "name": "Dell Inspiron 15 Core i5 16GB RAM 512GB SSD 120Hz Display",
                "brand": "Dell",
                "description": "Intel Core i5-1235U 10-core processor, 16GB DDR4 RAM, 512GB M.2 PCIe NVMe SSD, 15.6-inch FHD 120Hz anti-glare display, Windows 11 Home.",
                "category": "electronics",
                "price": 48990.0,
                "currency": "INR",
                "stock": 35,
                "rating": 4.6,
                "specs": {
                    "processor": "Intel Core i5-1235U (10 Cores, up to 4.40 GHz)",
                    "ram": "16GB DDR4 2666MHz",
                    "storage": "512GB M.2 PCIe NVMe SSD",
                    "display": "15.6\" FHD (1920x1080) 120Hz WVA"
                }
            },
            # =========================================================================
            # NEW EXPANDED CATALOG: DESKTOPS & MINI PCS (3 SKUs)
            # =========================================================================
            {
                "id": "prod_apple_mac_mini_m2",
                "merchant_id": "merchant_003",
                "name": "Apple Mac Mini M2 Desktop Computer 16GB Unified Memory 512GB SSD",
                "brand": "Apple",
                "description": "Apple M2 chip with 8-core CPU and 10-core GPU, 16GB unified memory, 512GB SSD storage, Gigabit Ethernet, Thunderbolt 4, HDMI, USB-A.",
                "category": "electronics",
                "price": 79900.0,
                "currency": "INR",
                "stock": 20,
                "rating": 4.9,
                "specs": {
                    "chip": "Apple M2 (8-core CPU, 10-core GPU, 16-core Neural Engine)",
                    "memory": "16GB Unified Memory",
                    "storage": "512GB High Speed SSD",
                    "ports": "2x Thunderbolt 4, 2x USB-A, HDMI, Gigabit Ethernet"
                }
            },
            {
                "id": "prod_intel_nuc_13",
                "merchant_id": "merchant_001",
                "name": "Intel NUC 13 Pro Mini PC Core i7 32GB DDR4 1TB NVMe SSD",
                "brand": "Intel",
                "description": "Intel Core i7-1360P 12-core processor, 32GB dual-channel DDR4 RAM, 1TB NVMe PCIe 4.0 SSD, dual HDMI 2.1, dual Thunderbolt 4 ports, compact 4x4 form-factor.",
                "category": "electronics",
                "price": 58990.0,
                "currency": "INR",
                "stock": 15,
                "rating": 4.8,
                "specs": {
                    "processor": "Intel Core i7-1360P (12 Cores, 16 Threads, up to 5.0 GHz)",
                    "ram": "32GB DDR4 3200MHz",
                    "storage": "1TB M.2 NVMe Gen4 SSD",
                    "form_factor": "Mini PC Desktop"
                }
            },
            {
                "id": "prod_beelink_ser5",
                "merchant_id": "merchant_002",
                "name": "Beelink SER5 MAX Mini PC AMD Ryzen 7 5800H 16GB RAM 500GB SSD",
                "brand": "Beelink",
                "description": "AMD Ryzen 7 5800H 8-core 16-thread processor up to 4.4GHz, 16GB DDR4 RAM, 500GB NVMe M.2 SSD, 4K triple display support via HDMI, DP, Type-C.",
                "category": "electronics",
                "price": 32990.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.7,
                "specs": {
                    "processor": "AMD Ryzen 7 5800H (8C/16T, up to 4.4GHz)",
                    "ram": "16GB DDR4 3200MHz",
                    "storage": "500GB M.2 NVMe SSD",
                    "display_support": "Triple 4K Display Output"
                }
            },
            # =========================================================================
            # NEW EXPANDED CATALOG: SMARTWATCHES & FITNESS BANDS (4 SKUs)
            # =========================================================================
            {
                "id": "prod_garmin_forerunner_265",
                "merchant_id": "merchant_003",
                "name": "Garmin Forerunner 265 GPS Running Smartwatch with AMOLED Display",
                "brand": "Garmin",
                "description": "Brilliant 1.3\" AMOLED touchscreen with traditional button controls, Training Readiness score, Multi-Band GPS, up to 13 days battery life in smartwatch mode.",
                "category": "wearables",
                "price": 42990.0,
                "currency": "INR",
                "stock": 15,
                "rating": 4.9,
                "specs": {
                    "display": "1.3-inch AMOLED Touchscreen Display",
                    "battery_life": "Up to 13 days smartwatch / 20 hours GPS",
                    "gps": "Multi-Band GNSS with SatIQ Technology",
                    "metrics": "VO2 Max, HRV Status, Training Readiness"
                }
            },
            {
                "id": "prod_amazfit_gtr4",
                "merchant_id": "merchant_002",
                "name": "Amazfit GTR 4 Smartwatch with Dual-Band GPS AMOLED 14-Day Battery",
                "brand": "Amazfit",
                "description": "Industry-first dual-band circularly-polarized GPS antenna, 1.43\" HD AMOLED display, 150+ sports modes, Bluetooth phone calls, up to 14 days battery.",
                "category": "wearables",
                "price": 16999.0,
                "currency": "INR",
                "stock": 30,
                "rating": 4.7,
                "specs": {
                    "display": "1.43\" HD AMOLED with Anti-Fingerprint Coating",
                    "battery_life": "14 days typical usage",
                    "calling": "Bluetooth phone calling with speaker & mic",
                    "sensors": "BioTracker 4.0 PPG biometric sensor"
                }
            },
            {
                "id": "prod_xiaomi_smart_band_8",
                "merchant_id": "merchant_001",
                "name": "Xiaomi Smart Band 8 Fitness Tracker with 1.62\" AMOLED 16-Day Battery",
                "brand": "Xiaomi",
                "description": "1.62\" 60Hz AMOLED display with 600 nits auto-brightness, all-day SpO2 & heart rate tracking, 150+ workout modes, quick-release stylish strap system.",
                "category": "wearables",
                "price": 2999.0,
                "currency": "INR",
                "stock": 60,
                "rating": 4.6,
                "specs": {
                    "display": "1.62-inch 60Hz AMOLED screen",
                    "battery_life": "Up to 16 days typical usage",
                    "water_resistance": "5 ATM waterproof (50m)",
                    "weight": "27g ultra-lightweight"
                }
            },
            {
                "id": "prod_fitbit_charge_6",
                "merchant_id": "merchant_003",
                "name": "Fitbit Charge 6 Fitness Tracker with Google Apps and Heart Rate on Equipment",
                "brand": "Fitbit",
                "description": "Most accurate heart rate tracking on a fitness tracker, built-in Google Maps and Google Wallet, EDA stress scan, ECG app, 7-day battery life.",
                "category": "wearables",
                "price": 12999.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.7,
                "specs": {
                    "google_services": "Google Maps, Google Wallet, YouTube Music controls",
                    "sensors": "ECG app for heart rhythm, EDA sensor for stress",
                    "battery_life": "Up to 7 days"
                }
            },
            # =========================================================================
            # NEW EXPANDED CATALOG: PORTABLE MONITORS (3 SKUs)
            # =========================================================================
            {
                "id": "prod_viewsonic_vp16",
                "merchant_id": "merchant_003",
                "name": "ViewSonic ColorPro VP16-OLED 15.6 Inch Portable FHD OLED Monitor",
                "brand": "ViewSonic",
                "description": "15.6\" 1080p OLED display with 100% DCI-P3 color gamut, Pantone validated, dual USB-C 40W two-way power delivery, built-in ergonomic foldable stand.",
                "category": "displays",
                "price": 29990.0,
                "currency": "INR",
                "stock": 15,
                "rating": 4.9,
                "specs": {
                    "panel": "15.6-inch Full HD (1920x1080) OLED",
                    "color_gamut": "100% DCI-P3, Delta E < 2",
                    "ports": "2x USB Type-C with 40W Power Delivery, 1x Micro-HDMI",
                    "stand": "Integrated multi-angle tripod mountable stand"
                }
            },
            {
                "id": "prod_arzopa_156",
                "merchant_id": "merchant_002",
                "name": "ARZOPA 15.6 Inch 1080P FHD Portable Laptop Monitor USB-C HDMI",
                "brand": "ARZOPA",
                "description": "Ultra-slim 0.3-inch 1.7lb portable monitor with 1080P IPS anti-glare screen, plug-and-play USB-C and Mini HDMI for laptops, Mac, PC, and consoles.",
                "category": "displays",
                "price": 8999.0,
                "currency": "INR",
                "stock": 40,
                "rating": 4.5,
                "specs": {
                    "panel": "15.6\" IPS 1080P FHD (1920x1080)",
                    "weight": "1.7 lbs (0.77 kg)",
                    "connectivity": "USB Type-C (Power + Signal), Mini HDMI"
                }
            },
            {
                "id": "prod_lenovo_thinkvision_m14d",
                "merchant_id": "merchant_001",
                "name": "Lenovo ThinkVision M14d 14 Inch 2.2K 16:10 USB-C Portable Display",
                "brand": "Lenovo",
                "description": "14-inch 2.2K (2240x1400) 16:10 productivity aspect ratio, 100% sRGB color coverage, dual USB-C power pass-through ports, 600g lightweight chassis.",
                "category": "displays",
                "price": 22990.0,
                "currency": "INR",
                "stock": 20,
                "rating": 4.8,
                "specs": {
                    "resolution": "2.2K (2240 x 1400) 16:10 aspect ratio",
                    "weight": "600 grams",
                    "color": "100% sRGB",
                    "ports": "Dual USB Type-C with Power Pass-Through"
                }
            },
            # =========================================================================
            # NEW EXPANDED CATALOG: E-READERS (2 SKUs)
            # =========================================================================
            {
                "id": "prod_kobo_clara_colour",
                "merchant_id": "merchant_003",
                "name": "Kobo Clara Colour 6\" Glare-Free Color E-Ink Waterproof E-Reader",
                "brand": "Kobo",
                "description": "6-inch E Ink Kaleido 3 display brings color to book covers, illustrations, and comics. ComfortLight PRO blue-light reduction and IPX8 waterproof rating.",
                "category": "books",
                "price": 15990.0,
                "currency": "INR",
                "stock": 20,
                "rating": 4.7,
                "specs": {
                    "screen": "6-inch E Ink Kaleido 3 Color Screen (300 ppi B&W / 150 ppi Color)",
                    "waterproofing": "IPX8 waterproof (up to 60 min in 2m water)",
                    "storage": "16GB (stores up to 12,000 books)"
                }
            },
            {
                "id": "prod_onyx_boox_palma",
                "merchant_id": "merchant_002",
                "name": "Onyx Boox Palma 6.13\" Pocket E-Ink Reader 6GB RAM 128GB Android 11",
                "brand": "Onyx Boox",
                "description": "Smartphone-sized 6.13\" Carta 1200 E-Ink paper display with BOOX Super Refresh (BSR) technology, octa-core processor, Google Play Store support.",
                "category": "books",
                "price": 28990.0,
                "currency": "INR",
                "stock": 15,
                "rating": 4.8,
                "specs": {
                    "display": "6.13\" HD Carta 1200 ePaper screen (300 ppi)",
                    "ram_storage": "6GB RAM + 128GB Storage (expandable via microSD)",
                    "os": "Android 11 with full Google Play Store access",
                    "refresh_tech": "BOOX Super Refresh (BSR)"
                }
            },
            # =========================================================================
            # NEW EXPANDED CATALOG: OFFICE & DESK (3 SKUs)
            # =========================================================================
            {
                "id": "prod_benq_wit_lamp",
                "merchant_id": "merchant_001",
                "name": "BenQ WiT e-Reading LED Desk Lamp with Auto-Dimming Curved Light",
                "brand": "BenQ",
                "description": "Wide curved lighting head illuminates 150% wider area than standard lamps. Built-in ambient light sensor auto-adjusts brightness; customizable color temperature.",
                "category": "office",
                "price": 18990.0,
                "currency": "INR",
                "stock": 20,
                "rating": 4.8,
                "specs": {
                    "lighting_area": "90cm illuminated range (150% wider)",
                    "sensor": "Auto-dimming ambient light sensor",
                    "color_temp": "2700K warm white to 5700K cool daylight"
                }
            },
            {
                "id": "prod_sihoo_doro_c300",
                "merchant_id": "merchant_003",
                "name": "SIHOO Doro C300 Ergonomic Office Chair with Dynamic Lumbar Support",
                "brand": "SIHOO",
                "description": "Self-adaptive dynamic chasing lumbar support, breathable cloud mesh backrest, 3D coordinated armrests, mechanical weight-sensing chassis.",
                "category": "office",
                "price": 24990.0,
                "currency": "INR",
                "stock": 15,
                "rating": 4.8,
                "specs": {
                    "lumbar": "Self-adaptive dynamic chasing lumbar support",
                    "material": "High tensile cloud mesh",
                    "armrests": "3D coordinated multi-angle armrests",
                    "recline": "3-position tilt angle lock up to 130 degrees"
                }
            },
            {
                "id": "prod_grovemade_desk_shelf",
                "merchant_id": "merchant_002",
                "name": "Grovemade Solid Walnut Wood Dual Monitor Desk Shelf Organizer",
                "brand": "Grovemade",
                "description": "Premium American solid walnut hardwood desk shelf with precision aluminum shelf insert, natural cork feet, elevates dual displays to ergonomic eye level.",
                "category": "office",
                "price": 19500.0,
                "currency": "INR",
                "stock": 12,
                "rating": 4.9,
                "specs": {
                    "material": "Solid American Walnut + Anodized Aluminum",
                    "dimensions": "46\" width (supports dual 27\" monitors)",
                    "storage": "Integrated lower shelf for laptop or keyboard tucking"
                }
            },
            # =========================================================================
            # NEW COMPREHENSIVE SEEDED PRODUCTS: AUDIO (4 SKUs)
            # =========================================================================
            {
                "id": "prod_bose_qc_ultra_white",
                "merchant_id": "merchant_003",
                "name": "Bose QuietComfort Ultra Wireless Noise Cancelling Headphones (White Smoke Edition)",
                "brand": "Bose",
                "description": "Breakthrough spatialized audio for more immersive listening, world-class active noise cancellation, CustomTune technology personalizes sound to ears, up to 24 hours battery life.",
                "category": "audio",
                "price": 34900.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.9,
                "specs": {
                    "spatial_audio": "Bose Immersive Audio with head tracking",
                    "noise_cancellation": "World-class CustomTune ANC",
                    "battery_life": "24 hours (18 hours with Immersive Audio)",
                    "connectivity": ["Bluetooth 5.3", "Snapdragon Sound", "3.5mm AUX"]
                }
            },
            {
                "id": "prod_marshall_major_v",
                "merchant_id": "merchant_001",
                "name": "Marshall Major V Wireless On-Ear Bluetooth Headphones",
                "brand": "Marshall",
                "description": "Iconic Marshall signature sound with 100+ hours of wireless playtime, rugged foldable design, customizable M-button, wireless charging support.",
                "category": "audio",
                "price": 14999.0,
                "currency": "INR",
                "stock": 40,
                "rating": 4.7,
                "specs": {
                    "battery_life": "100+ hours wireless playback",
                    "charging": "Wireless charging + USB-C fast charge (15 min = 15 hrs)",
                    "driver_size": "40mm dynamic customized drivers",
                    "foldable": "Rugged collapsible design"
                }
            },
            {
                "id": "prod_galaxy_buds_3_pro",
                "merchant_id": "merchant_002",
                "name": "Samsung Galaxy Buds 3 Pro AI Adaptive Noise Canceling Earbuds",
                "brand": "Samsung",
                "description": "Blade lights design, dual amplifiers with planar tweeter and dynamic woofer, 24-bit 96kHz Hi-Fi codec, Galaxy AI powered adaptive noise control and live interpreter.",
                "category": "audio",
                "price": 19999.0,
                "currency": "INR",
                "stock": 35,
                "rating": 4.8,
                "specs": {
                    "ai_features": "Adaptive Noise Control, Siren Detect, Voice Detect",
                    "audio_quality": "24-bit/96kHz SSC Hi-Fi Audio with 2-way speakers",
                    "water_resistance": "IP57 water and dust resistance",
                    "battery_life": "7 hours (30 hours with case)"
                }
            },
            {
                "id": "prod_marshall_emberton_2",
                "merchant_id": "merchant_001",
                "name": "Marshall Emberton II Portable Bluetooth Speaker with True Stereophonic 360 Audio",
                "brand": "Marshall",
                "description": "True Stereophonic multi-directional 360-degree sound from Marshall, 30+ hours of portable playtime, IP67 dust and water resistance, Stack Mode pairing.",
                "category": "audio",
                "price": 14999.0,
                "currency": "INR",
                "stock": 35,
                "rating": 4.8,
                "specs": {
                    "sound": "True Stereophonic 360-degree sound",
                    "battery_life": "30+ hours portable playtime",
                    "durability": "IP67 dust and water resistance",
                    "stack_mode": "Connect multiple Emberton II speakers"
                }
            },
            # =========================================================================
            # NEW COMPREHENSIVE SEEDED PRODUCTS: ELECTRONICS & COMPUTING (4 SKUs)
            # =========================================================================
            {
                "id": "prod_mac_mini_m4",
                "merchant_id": "merchant_003",
                "name": "Apple Mac mini (M4 Chip 10-core CPU, 10-core GPU, 16GB RAM, 256GB SSD)",
                "brand": "Apple",
                "description": "Ultra-compact 5x5-inch design powered by Apple M4 chip with Apple Intelligence, front and back Thunderbolt ports, HDMI, gigabit ethernet, incredible whisper-quiet thermal design.",
                "category": "electronics",
                "price": 59900.0,
                "currency": "INR",
                "stock": 20,
                "rating": 4.9,
                "specs": {
                    "processor": "Apple M4 chip (10-core CPU with 4 performance & 6 efficiency cores)",
                    "gpu": "10-core GPU with hardware-accelerated ray tracing",
                    "ram": "16GB unified memory (120GB/s bandwidth)",
                    "storage": "256GB high-speed SSD",
                    "ports": "3x Thunderbolt 4, 2x USB-C front ports, HDMI, Gigabit Ethernet"
                }
            },
            {
                "id": "prod_ipad_air_m2",
                "merchant_id": "merchant_001",
                "name": "Apple iPad Air 11-inch M2 Chip Liquid Retina Display (128GB Wi-Fi Space Grey)",
                "brand": "Apple",
                "description": "Powered by Apple M2 chip, 11-inch Liquid Retina display with P3 wide color and True Tone, landscape 12MP front camera with Center Stage, Apple Pencil Pro support.",
                "category": "electronics",
                "price": 59900.0,
                "currency": "INR",
                "stock": 28,
                "rating": 4.9,
                "specs": {
                    "chip": "Apple M2 (8-core CPU, 9-core GPU, 16-core Neural Engine)",
                    "display": "11-inch Liquid Retina display (2360x1640, 500 nits, antireflective)",
                    "storage": "128GB",
                    "camera": "Landscape 12MP Ultra Wide with Center Stage + 12MP Wide back 4K"
                }
            },
            {
                "id": "prod_steam_deck_oled",
                "merchant_id": "merchant_003",
                "name": "Valve Steam Deck OLED 512GB Handheld Gaming Computer Console",
                "brand": "Valve",
                "description": "7.4-inch 90Hz HDR OLED display with 1,000 nits peak brightness, 6nm AMD APU, 50Wh battery offering 3-12 hours gameplay, Wi-Fi 6E, full-size thumbsticks with capacitive touch.",
                "category": "electronics",
                "price": 58990.0,
                "currency": "INR",
                "stock": 16,
                "rating": 4.9,
                "specs": {
                    "display": "7.4-inch 90Hz HDR OLED (1280x800, 1000 nits peak HDR)",
                    "processor": "6nm AMD APU (Zen 2 4c/8t + 8 RDNA 2 CUs)",
                    "storage": "512GB NVMe SSD with high-speed microSD slot",
                    "battery": "50Wh battery (3-12 hours of gameplay)",
                    "wireless": "Tri-band Wi-Fi 6E + Bluetooth 5.3"
                }
            },
            {
                "id": "prod_lenovo_legion_pro5",
                "merchant_id": "merchant_002",
                "name": "Lenovo Legion Pro 5 Gen 9 AMD Ryzen 7 7745HX RTX 4060 16GB 1TB SSD Gaming Laptop",
                "brand": "Lenovo",
                "description": "AMD Ryzen 7 7745HX 8-core processor, NVIDIA GeForce RTX 4060 8GB GDDR6 (140W TGP), 16-inch WQXGA 240Hz 500 nits display, Legion ColdFront 5.0 cooling.",
                "category": "electronics",
                "price": 134990.0,
                "currency": "INR",
                "stock": 14,
                "rating": 4.8,
                "specs": {
                    "processor": "AMD Ryzen 7 7745HX (8 cores / 16 threads, up to 5.1GHz)",
                    "gpu": "NVIDIA GeForce RTX 4060 8GB GDDR6 (140W Maximum TGP)",
                    "display": "16-inch WQXGA (2560x1600) IPS 240Hz 500 nits DisplayHDR 400",
                    "ram_storage": "16GB DDR5 5200MHz RAM + 1TB PCIe 4.0 NVMe SSD"
                }
            },
            # =========================================================================
            # NEW COMPREHENSIVE SEEDED PRODUCTS: ACCESSORIES (4 SKUs)
            # =========================================================================
            {
                "id": "prod_logitech_mx_brio",
                "merchant_id": "merchant_001",
                "name": "Logitech MX Brio Ultra HD 4K Streaming Webcam with HDR and AI Noise Reduction",
                "brand": "Logitech",
                "description": "Ultra HD 4K webcam with custom-designed Sony STARVIS sensor, 70% larger pixels than Brio 4K, dual beamforming noise-reducing mics, innovative Show Mode to tilt desk items.",
                "category": "accessories",
                "price": 19995.0,
                "currency": "INR",
                "stock": 30,
                "rating": 4.8,
                "specs": {
                    "resolution": "4K Ultra HD at 30fps / 1080p at 60fps",
                    "sensor": "Sony STARVIS 8.5MP sensor (70% larger pixels)",
                    "show_mode": "Physical tilt-down desk share mechanism",
                    "microphones": "Dual integrated beamforming noise-reducing mics"
                }
            },
            {
                "id": "prod_nuphy_air75_v2",
                "merchant_id": "merchant_003",
                "name": "NuPhy Air75 V2 Ultra-Slim Wireless Mechanical Keyboard (Gateron Low Profile)",
                "brand": "NuPhy",
                "description": "World's slimmest QMK/VIA low-profile mechanical keyboard, 1000Hz polling rate in 2.4G wireless mode, tri-mode connectivity (Mac/Win), hot-swappable switches, RGB side and backlights.",
                "category": "accessories",
                "price": 11990.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.9,
                "specs": {
                    "layout": "75% compact low-profile mechanical layout",
                    "polling_rate": "1000Hz wired & 2.4G wireless",
                    "firmware": "QMK/VIA open-source programmable keymap",
                    "switches": "Gateron Low Profile Mechanical Switches (Hot-swappable)"
                }
            },
            {
                "id": "prod_anker_prime_20000",
                "merchant_id": "merchant_002",
                "name": "Anker Prime 20,000mAh Power Bank (200W Output with Smart Digital Display)",
                "brand": "Anker",
                "description": "20,000mAh capacity with simultaneous 200W multi-port fast charging (dual 100W USB-C output), smart digital display showing live wattages and battery health.",
                "category": "accessories",
                "price": 11999.0,
                "currency": "INR",
                "stock": 45,
                "rating": 4.9,
                "specs": {
                    "total_output": "200W combined maximum output (100W + 100W)",
                    "capacity": "20,000mAh (72Wh airline approved)",
                    "display": "Color smart digital screen with live telemetry",
                    "recharge_time": "75 minutes full recharge via 100W input"
                }
            },
            {
                "id": "prod_caldigit_ts4_pro",
                "merchant_id": "merchant_003",
                "name": "CalDigit TS4 Thunderbolt 4 Docking Station (18 Ports, 98W Power Delivery)",
                "brand": "CalDigit",
                "description": "The ultimate Thunderbolt 4 dock featuring 18 versatile ports, 98W host charging power delivery, 2.5GbE high-speed ethernet, UHS-II SD/microSD slots, dual 6K or single 8K display support.",
                "category": "accessories",
                "price": 38990.0,
                "currency": "INR",
                "stock": 18,
                "rating": 4.9,
                "specs": {
                    "ports_count": "18 connectivity ports",
                    "power_delivery": "Up to 98W host fast pass-through charging",
                    "networking": "2.5 Gigabit Ethernet (2.5GbE)",
                    "display_support": "Single 8K 60Hz or Dual 6K 60Hz displays"
                }
            },
            # =========================================================================
            # NEW COMPREHENSIVE SEEDED PRODUCTS: DISPLAYS & MONITORS (4 SKUs)
            # =========================================================================
            {
                "id": "prod_apple_studio_display",
                "merchant_id": "merchant_003",
                "name": "Apple Studio Display 27-inch 5K Retina Display with Standard Glass",
                "brand": "Apple",
                "description": "27-inch 5K Retina display with 14.7 million pixels, 600 nits brightness, P3 wide color, 12MP Ultra Wide camera with Center Stage, studio-quality 3-mic array, six-speaker sound with Spatial Audio.",
                "category": "displays",
                "price": 159900.0,
                "currency": "INR",
                "stock": 10,
                "rating": 4.9,
                "specs": {
                    "resolution": "5120 x 2880 pixels (5K Retina) at 218 ppi",
                    "brightness": "600 nits brightness with True Tone",
                    "audio": "Six-speaker system with force-cancelling woofers + Spatial Audio",
                    "connectivity": "1x Thunderbolt 3 (96W host charge) + 3x USB-C (10Gbps)"
                }
            },
            {
                "id": "prod_dell_u3425we",
                "merchant_id": "merchant_001",
                "name": "Dell UltraSharp 34 Curved Thunderbolt Hub Monitor 120Hz IPS Black (U3425WE)",
                "brand": "Dell",
                "description": "34-inch curved WQHD IPS Black panel with 2000:1 contrast ratio, 120Hz refresh rate, Thunderbolt 4 hub with 90W PD, 2.5GbE RJ45, ComfortView Plus hardware low blue light.",
                "category": "displays",
                "price": 89900.0,
                "currency": "INR",
                "stock": 15,
                "rating": 4.9,
                "specs": {
                    "panel": "34-inch Curved (1900R) IPS Black WQHD (3440 x 1440)",
                    "refresh_rate": "120Hz variable refresh rate",
                    "contrast_ratio": "2000:1 IPS Black contrast ratio",
                    "hub": "Thunderbolt 4 (90W PD) + 2.5GbE LAN + KVM Switch"
                }
            },
            {
                "id": "prod_samsung_viewfinity_s9",
                "merchant_id": "merchant_002",
                "name": "Samsung ViewFinity S9 27-inch 5K Matte Display with 4K SlimFit Camera",
                "brand": "Samsung",
                "description": "5K resolution (5120 x 2880), 99% DCI-P3 color gamut, Matte Display reduces glare, Smart Calibration via smartphone, modular 4K SlimFit camera included, Thunderbolt 4 connectivity.",
                "category": "displays",
                "price": 99990.0,
                "currency": "INR",
                "stock": 12,
                "rating": 4.8,
                "specs": {
                    "resolution": "5K (5120 x 2880) 218 ppi",
                    "anti_glare": "Matte display surface coating",
                    "camera": "Included detachable 4K SlimFit webcam",
                    "smart_features": "Built-in Smart TV apps & AirPlay support"
                }
            },
            {
                "id": "prod_lg_ultrafine_32un880",
                "merchant_id": "merchant_001",
                "name": "LG 32-inch UltraFine 4K UHD Ergo IPS Monitor with C-Clamp Stand (32UN880-B)",
                "brand": "LG",
                "description": "31.5-inch 4K UHD IPS panel with HDR10 and DCI-P3 95%, innovative ergonomic arm with C-clamp grommet that extends, retracts, swivels, pivots, tilts, and adjusts height.",
                "category": "displays",
                "price": 44990.0,
                "currency": "INR",
                "stock": 22,
                "rating": 4.8,
                "specs": {
                    "screen": "31.5-inch 4K UHD (3840 x 2160) IPS panel",
                    "stand": "Ergo Stand (Extend/Retract 180mm, Swivel +/- 280 deg, Pivot 90 deg)",
                    "connectivity": "USB Type-C (60W PD) + 2x HDMI + DisplayPort",
                    "color_gamut": "DCI-P3 95% with HDR10"
                }
            },
            # =========================================================================
            # NEW COMPREHENSIVE SEEDED PRODUCTS: OFFICE & WORKSPACE (4 SKUs)
            # =========================================================================
            {
                "id": "prod_herman_miller_aeron",
                "merchant_id": "merchant_003",
                "name": "Herman Miller Aeron Ergonomic Task Chair with PostureFit SL (Graphite / Size B)",
                "brand": "Herman Miller",
                "description": "Benchmark ergonomic work chair featuring Pellicle 8Z breathable suspension mesh, adjustable PostureFit SL sacral/lumbar support, forward tilt and fully adjustable arms.",
                "category": "office",
                "price": 115000.0,
                "currency": "INR",
                "stock": 8,
                "rating": 5.0,
                "specs": {
                    "ergonomics": "PostureFit SL dual pad lumbar and sacral support",
                    "material": "8Z Pellicle elastomeric suspension suspension mesh",
                    "adjustability": "Forward tilt, tilt limiter, 3D fully adjustable arms",
                    "warranty": "12-Year Official Herman Miller Warranty"
                }
            },
            {
                "id": "prod_uplift_v2_standing_desk",
                "merchant_id": "merchant_001",
                "name": "UPLIFT V2 Commercial Dual-Motor Electric Standing Desk (60x30 Solid Bamboo)",
                "brand": "UPLIFT Desk",
                "description": "Commercial dual-motor 3-stage motorized sit-stand desk, solid carbonized bamboo desktop, 355 lb lifting capacity, anti-collision sensor, advanced memory digital keypad.",
                "category": "office",
                "price": 68500.0,
                "currency": "INR",
                "stock": 10,
                "rating": 4.9,
                "specs": {
                    "motors": "Dual German-engineered motors with 3-stage steel legs",
                    "weight_capacity": "355 lbs (161 kg) lifting capacity",
                    "height_range": "25.3\" to 50.9\" electronic height adjustment",
                    "desktop": "Solid 1-inch carbonized UV-cured natural bamboo"
                }
            },
            {
                "id": "prod_dyson_solarcycle_morph",
                "merchant_id": "merchant_002",
                "name": "Dyson Solarcycle Morph Intelligent LED Desk and Task Light with Heat Pipe",
                "brand": "Dyson",
                "description": "4 lights in 1: Task, Indirect, Feature, and Ambient light. Intelligent Daylight Tracking matches local sun cycle, Heat Pipe cooling maintains 60-year LED light quality.",
                "category": "office",
                "price": 41900.0,
                "currency": "INR",
                "stock": 14,
                "rating": 4.8,
                "specs": {
                    "light_modes": "Task light, Indirect ambient, Feature accent, Ambient glow",
                    "daylight_tracking": "Algorithm auto-adjusts light color and brightness based on GPS",
                    "cooling_tech": "Vacuum-sealed copper heat pipe cools LEDs for 60 years",
                    "controls": "Slide-touch dimming & Dyson Link App smart integration"
                }
            },
            {
                "id": "prod_vari_electric_standing_converter",
                "merchant_id": "merchant_001",
                "name": "Vari Electric Standing Desk Converter (36\" Dual Monitor Motorized Desktop Riser)",
                "brand": "Vari",
                "description": "Motorized sit-stand desktop converter with quiet motor, spacious two-tier design holding dual displays and full-size keyboard, smooth push-button height transition.",
                "category": "office",
                "price": 27500.0,
                "currency": "INR",
                "stock": 18,
                "rating": 4.7,
                "specs": {
                    "tier_design": "Spacious upper display surface + lower keyboard tier",
                    "lift_mechanism": "Continuous push-button motorized lift",
                    "width": "36 inches wide (accommodates dual 24\" monitors)",
                    "weight_capacity": "45 lbs (20.4 kg)"
                }
            },
            # =========================================================================
            # NEW COMPREHENSIVE SEEDED PRODUCTS: BOOKS & E-READERS (4 SKUs)
            # =========================================================================
            {
                "id": "prod_boox_note_air3_c",
                "merchant_id": "merchant_003",
                "name": "Onyx Boox Note Air3 C 10.3\" Color E-Ink Android Tablet with Stylus Pen",
                "brand": "Onyx Boox",
                "description": "10.3-inch Kaleido 3 color ePaper display, BOOX Super Refresh (BSR) GPU, magnetic Pen Plus stylus with paper-like writing feel, Android 12 with Google Play store for all reading apps.",
                "category": "books",
                "price": 49990.0,
                "currency": "INR",
                "stock": 15,
                "rating": 4.9,
                "specs": {
                    "display": "10.3-inch Kaleido 3 Color E-Ink (300 ppi B&W / 150 ppi Color)",
                    "processor_ram": "Octa-core 2.4GHz + BSR GPU, 4GB RAM, 64GB Storage + microSD",
                    "stylus": "Pen Plus magnetic stylus with 4,096 levels pressure sensitivity",
                    "os": "Android 12 with full Google Play Store support"
                }
            },
            {
                "id": "prod_kobo_libra_colour",
                "merchant_id": "merchant_002",
                "name": "Kobo Libra Colour 7-inch Waterproof Color E-Reader with Page-Turn Buttons",
                "brand": "Kobo",
                "description": "7-inch E-Ink Kaleido 3 color screen, ergonomic curved design with physical page-turn buttons, IPX8 waterproof rating, Kobo Stylus 2 compatibility for book margin notations.",
                "category": "books",
                "price": 21990.0,
                "currency": "INR",
                "stock": 25,
                "rating": 4.8,
                "specs": {
                    "screen": "7-inch E-Ink Kaleido 3 (300 ppi B&W / 150 ppi Color)",
                    "navigation": "Physical tactile page-turn buttons + touchscreen",
                    "durability": "IPX8 waterproof (2 meters depth up to 60 minutes)",
                    "storage": "32GB (holds up to 24,000 eBooks or 150 Kobo Audiobooks)"
                }
            },
            {
                "id": "prod_pocketbook_era_color",
                "merchant_id": "merchant_001",
                "name": "PocketBook Era Color 7-inch E-Reader with Built-in Speaker and SMARTlight",
                "brand": "PocketBook",
                "description": "7-inch E Ink Kaleido 3 display with optical clarity layer, side control buttons, built-in speaker for audiobooks and Text-to-Speech narration, IPX8 waterproof.",
                "category": "books",
                "price": 25990.0,
                "currency": "INR",
                "stock": 20,
                "rating": 4.7,
                "specs": {
                    "audio": "Built-in mono speaker + Bluetooth for headphones",
                    "text_to_speech": "Voice Text-to-Speech in 26 languages",
                    "screen": "7-inch E Ink Kaleido 3 color display",
                    "formats": "Native support for 25 formats without conversion (EPUB, PDF, CBZ, MOBI)"
                }
            },
            {
                "id": "prod_kindle_basic_2024",
                "merchant_id": "merchant_003",
                "name": "Amazon Kindle (11th Gen - 2024 Refresh) 6\" 300 ppi Display 16GB (Black)",
                "brand": "Amazon",
                "description": "Lightest and most compact Kindle with 300 ppi glare-free display, 25% brighter front light at max setting, 16GB storage for thousands of titles, 6 weeks battery life.",
                "category": "books",
                "price": 9999.0,
                "currency": "INR",
                "stock": 60,
                "rating": 4.6,
                "specs": {
                    "display": "6-inch glare-free 300 ppi high-resolution display",
                    "storage": "16GB storage capacity",
                    "battery_life": "Up to 6 weeks on a single charge",
                    "weight": "158 grams ultralight"
                }
            },
            # =========================================================================
            # NEW COMPREHENSIVE SEEDED PRODUCTS: WEARABLES & FITNESS TRACKERS (4 SKUs)
            # =========================================================================
            {
                "id": "prod_apple_watch_ultra_2",
                "merchant_id": "merchant_003",
                "name": "Apple Watch Ultra 2 GPS + Cellular 49mm Titanium Case with Ocean Band",
                "brand": "Apple",
                "description": "49mm aerospace-grade titanium case, brightest 3000 nits display, precision dual-frequency GPS, Action Button, 100m water resistance, EN13319 scuba dive certified.",
                "category": "wearables",
                "price": 89900.0,
                "currency": "INR",
                "stock": 12,
                "rating": 5.0,
                "specs": {
                    "case": "49mm Aerospace-grade Titanium with raised sapphire crystal edges",
                    "brightness": "3000 nits peak Always-On Retina display",
                    "gps": "Precision dual-frequency GPS (L1 & L5)",
                    "diving": "100m water resistance, depth gauge with water temperature sensor (EN13319)",
                    "battery": "36 hours normal use / up to 72 hours in Low Power Mode"
                }
            },
            {
                "id": "prod_garmin_fenix_7_pro",
                "merchant_id": "merchant_001",
                "name": "Garmin Fenix 7 Pro Sapphire Solar Multisport GPS Smartwatch with LED Flashlight",
                "brand": "Garmin",
                "description": "Scratch-resistant Power Sapphire solar charging lens, built-in multi-LED flashlight, Elevate Gen 5 heart rate sensor, Hill Score and Endurance Score, TopoActive maps.",
                "category": "wearables",
                "price": 81990.0,
                "currency": "INR",
                "stock": 15,
                "rating": 4.9,
                "specs": {
                    "battery": "Up to 22 days in smartwatch mode with solar charging",
                    "solar_lens": "Power Sapphire solar charging lens with titanium bezel",
                    "flashlight": "Built-in variable intensity LED flashlight with strobe mode",
                    "maps": "Preloaded TopoActive continental maps with Up Ahead navigation"
                }
            },
            {
                "id": "prod_whoop_4_sensor",
                "merchant_id": "merchant_002",
                "name": "WHOOP 4.0 Health & Fitness Tracker Wearable (Includes 12-Month Membership)",
                "brand": "WHOOP",
                "description": "Screen-free continuous physiological monitoring tracker measuring Strain, Recovery, and Sleep. Any-Wear technology allows wearing on wrist, bicep, or WHOOP body wear.",
                "category": "wearables",
                "price": 23900.0,
                "currency": "INR",
                "stock": 30,
                "rating": 4.7,
                "specs": {
                    "sensor_type": "5 LEDs (3 green, 1 red, 1 infrared) + 4 photodiodes",
                    "metrics": "Heart rate variability (HRV), skin temperature, blood oxygen, respiratory rate",
                    "charging": "Wireless waterproof battery pack slides onto sensor while wearing",
                    "subscription": "Includes 12 months full WHOOP health and recovery analytics"
                }
            },
            {
                "id": "prod_fitbit_charge_6_coral",
                "merchant_id": "merchant_001",
                "name": "Fitbit Charge 6 Advanced Fitness & Health Tracker (Coral Special Edition)",
                "brand": "Fitbit",
                "description": "Fitbit's most accurate heart rate tracking yet powered by Google machine learning algorithms, built-in GPS, Google Maps and Google Wallet integration, 7-day battery life.",
                "category": "wearables",
                "price": 13999.0,
                "currency": "INR",
                "stock": 45,
                "rating": 4.6,
                "specs": {
                    "sensors": "Optical heart rate tracker, EDA scan sensor for stress, ECG app",
                    "google_integrations": "Google Maps turn-by-turn directions, Google Wallet, YouTube Music controls",
                    "gps": "Built-in GPS + GLONASS",
                    "battery_life": "Up to 7 days continuous tracking"
                }
            }
        ]

        staged_products = {}
        for p_data in products_data:
            existing = staged_products.get(p_data["id"]) or db.query(Product).filter(Product.id == p_data["id"]).first()
            if not existing:
                product = Product(
                    id=p_data["id"],
                    merchant_id=p_data["merchant_id"],
                    name=p_data["name"],
                    brand=p_data.get("brand", ""),
                    description=p_data["description"],
                    category=p_data["category"],
                    price=p_data["price"],
                    currency=p_data["currency"],
                    stock=p_data["stock"],
                    rating=p_data.get("rating", 4.8)
                )
                product.specs = p_data.get("specs", {})
                staged_products[p_data["id"]] = product
                db.add(product)
            else:
                existing.merchant_id = p_data["merchant_id"]
                existing.name = p_data["name"]
                existing.brand = p_data.get("brand", "")
                existing.description = p_data["description"]
                existing.category = p_data["category"]
                existing.price = p_data["price"]
                existing.currency = p_data["currency"]
                existing.stock = p_data["stock"]
                existing.rating = p_data.get("rating", 4.8)
                existing.specs = p_data.get("specs", {})
                staged_products[p_data["id"]] = existing
        db.commit()
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    seed_database()
    print("Database successfully seeded with 135+ multi-merchant federated products.")
