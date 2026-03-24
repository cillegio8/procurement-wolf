"""
Generate sample procurement database with realistic Azerbaijani vendor data.
Creates SQLite database with vendors, orders, and HHI snapshots.
"""

import sqlite3
import random
from datetime import datetime, timedelta
import os

# Seed for reproducibility
random.seed(42)

# UNSPSC Categories with realistic segments
CATEGORIES = {
    "76000000": {
        "name": "Industrial Cleaning Services",
        "families": {
            "76120000": {
                "name": "Building cleaning services",
                "classes": {
                    "76122300": "Road cleaning services",
                    "76122400": "Street maintenance services"
                }
            }
        }
    },
    "22000000": {
        "name": "Building and Construction Materials",
        "families": {
            "22100000": {
                "name": "Concrete and cement and plaster",
                "classes": {
                    "22101600": "Asphalt and bituminous products",
                    "22101700": "Concrete and mortars"
                }
            },
            "22110000": {
                "name": "Structural materials",
                "classes": {
                    "22111500": "Structural metal products",
                    "22111600": "Construction stone"
                }
            }
        }
    },
    "15000000": {
        "name": "Fuels and Lubricants",
        "families": {
            "15100000": {
                "name": "Fuels",
                "classes": {
                    "15101500": "Petroleum and distillates",
                    "15101600": "Fuel oils"
                }
            }
        }
    },
    "43000000": {
        "name": "IT Equipment and Services",
        "families": {
            "43210000": {
                "name": "Computer equipment",
                "classes": {
                    "43211500": "Computers",
                    "43211600": "Computer accessories"
                }
            },
            "43230000": {
                "name": "Software",
                "classes": {
                    "43231500": "Business software",
                    "43231600": "Operating systems"
                }
            }
        }
    },
    "44000000": {
        "name": "Office Equipment and Supplies",
        "families": {
            "44120000": {
                "name": "Office supplies",
                "classes": {
                    "44121500": "Writing instruments",
                    "44121600": "Paper products"
                }
            }
        }
    },
    "25000000": {
        "name": "Vehicles and Transportation",
        "families": {
            "25100000": {
                "name": "Motor vehicles",
                "classes": {
                    "25101500": "Passenger vehicles",
                    "25101600": "Commercial vehicles"
                }
            }
        }
    },
    "72000000": {
        "name": "Building and Construction Services",
        "families": {
            "72100000": {
                "name": "Building construction services",
                "classes": {
                    "72101500": "Commercial building construction",
                    "72101600": "Residential building construction"
                }
            },
            "72140000": {
                "name": "Heavy construction services",
                "classes": {
                    "72141100": "Highway construction",
                    "72141200": "Bridge construction"
                }
            }
        }
    },
    "80000000": {
        "name": "Management and Business Services",
        "families": {
            "80100000": {
                "name": "Management advisory services",
                "classes": {
                    "80101500": "Business consulting",
                    "80101600": "Project management"
                }
            }
        }
    }
}

# Sample vendors with Azerbaijani names
VENDORS = [
    # Road Construction & Infrastructure (dominant players)
    {"name": "ATF MƏHDUD MƏSULİYYƏTLİ CƏMİYYƏTİ", "type": "Large", "primary_segment": "76000000", "city": "Bakı", "weight": 3.5},
    {"name": "Yol Tikinti LLC", "type": "Large", "primary_segment": "72000000", "city": "Bakı", "weight": 2.8},
    {"name": "Asfalt Plus MMC", "type": "SME", "primary_segment": "22000000", "city": "Sumqayıt", "weight": 1.5},
    {"name": "İnfrastruktur Qrup MMC", "type": "Large", "primary_segment": "72000000", "city": "Bakı", "weight": 2.2},
    {"name": "Körpü Tikinti AZ", "type": "SME", "primary_segment": "72000000", "city": "Gəncə", "weight": 1.0},
    
    # Building Materials
    {"name": "Qum-Çınqıl Təchizat MMC", "type": "SME", "primary_segment": "22000000", "city": "Bakı", "weight": 1.8},
    {"name": "Beton Sənaye MMC", "type": "Large", "primary_segment": "22000000", "city": "Gəncə", "weight": 2.5},
    {"name": "Metal Konstruksiya AZ", "type": "SME", "primary_segment": "22000000", "city": "Bakı", "weight": 1.2},
    {"name": "Daş-Qum İstehsalat", "type": "SME", "primary_segment": "22000000", "city": "Şəki", "weight": 0.9},
    {"name": "Tikinti Materialları Plus", "type": "SME", "primary_segment": "22000000", "city": "Lənkəran", "weight": 0.8},
    {"name": "Sement Zavodu AZ", "type": "Large", "primary_segment": "22000000", "city": "Qaradağ", "weight": 2.0},
    
    # Fuels & Energy (high concentration)
    {"name": "SOCAR Təchizat", "type": "State", "primary_segment": "15000000", "city": "Bakı", "weight": 5.0},
    {"name": "Azneft Supply LLC", "type": "Large", "primary_segment": "15000000", "city": "Bakı", "weight": 2.5},
    {"name": "Petrol Plus MMC", "type": "SME", "primary_segment": "15000000", "city": "Sumqayıt", "weight": 0.8},
    {"name": "Enerji Resursları MMC", "type": "SME", "primary_segment": "15000000", "city": "Bakı", "weight": 0.6},
    
    # IT Equipment & Services
    {"name": "TechAz Solutions", "type": "SME", "primary_segment": "43000000", "city": "Bakı", "weight": 1.5},
    {"name": "Digital Baku MMC", "type": "SME", "primary_segment": "43000000", "city": "Bakı", "weight": 1.3},
    {"name": "İnfoTech Azərbaycan", "type": "Large", "primary_segment": "43000000", "city": "Bakı", "weight": 2.0},
    {"name": "Kompüter Dünyası", "type": "SME", "primary_segment": "43000000", "city": "Gəncə", "weight": 0.9},
    {"name": "Soft Solutions AZ", "type": "SME", "primary_segment": "43000000", "city": "Bakı", "weight": 1.1},
    {"name": "Network Systems LLC", "type": "SME", "primary_segment": "43000000", "city": "Bakı", "weight": 0.8},
    
    # Office Supplies (competitive market)
    {"name": "Ofis Təchizat MMC", "type": "SME", "primary_segment": "44000000", "city": "Bakı", "weight": 1.2},
    {"name": "Kağız Dünyası", "type": "SME", "primary_segment": "44000000", "city": "Bakı", "weight": 1.0},
    {"name": "Stationery Plus AZ", "type": "SME", "primary_segment": "44000000", "city": "Sumqayıt", "weight": 0.9},
    {"name": "Ofis Mebel Marketi", "type": "SME", "primary_segment": "44000000", "city": "Bakı", "weight": 0.8},
    {"name": "Büro Ləvazimatları", "type": "SME", "primary_segment": "44000000", "city": "Gəncə", "weight": 0.7},
    {"name": "Print Solutions MMC", "type": "SME", "primary_segment": "44000000", "city": "Bakı", "weight": 0.6},
    
    # Vehicles & Transportation
    {"name": "AvtoAz Dealership", "type": "Large", "primary_segment": "25000000", "city": "Bakı", "weight": 2.2},
    {"name": "Nəqliyyat Vasitələri MMC", "type": "SME", "primary_segment": "25000000", "city": "Bakı", "weight": 1.5},
    {"name": "Truck Center AZ", "type": "SME", "primary_segment": "25000000", "city": "Sumqayıt", "weight": 1.0},
    {"name": "Avtomobil Servisi Plus", "type": "SME", "primary_segment": "25000000", "city": "Gəncə", "weight": 0.8},
    
    # Construction Services
    {"name": "Tikinti Xidmətləri AZ", "type": "Large", "primary_segment": "72000000", "city": "Bakı", "weight": 2.0},
    {"name": "BuildCo Azerbaijan", "type": "Large", "primary_segment": "72000000", "city": "Bakı", "weight": 1.8},
    {"name": "Əsas Tikinti MMC", "type": "SME", "primary_segment": "72000000", "city": "Mingəçevir", "weight": 1.2},
    {"name": "Urban Development LLC", "type": "SME", "primary_segment": "72000000", "city": "Bakı", "weight": 1.0},
    {"name": "Mənzil Tikintisi", "type": "SME", "primary_segment": "72000000", "city": "Şəki", "weight": 0.7},
    
    # Management & Consulting
    {"name": "Biznes Məsləhət MMC", "type": "SME", "primary_segment": "80000000", "city": "Bakı", "weight": 1.5},
    {"name": "Konsaltinq AZ", "type": "SME", "primary_segment": "80000000", "city": "Bakı", "weight": 1.2},
    {"name": "Layihə İdarəetmə LLC", "type": "SME", "primary_segment": "80000000", "city": "Bakı", "weight": 1.0},
    {"name": "Strategic Partners AZ", "type": "SME", "primary_segment": "80000000", "city": "Bakı", "weight": 0.9},
    
    # Additional diverse vendors
    {"name": "Xəzər Logistics", "type": "Large", "primary_segment": "25000000", "city": "Bakı", "weight": 1.8},
    {"name": "Təmizlik Xidmətləri MMC", "type": "SME", "primary_segment": "76000000", "city": "Bakı", "weight": 1.2},
    {"name": "Eco Clean AZ", "type": "SME", "primary_segment": "76000000", "city": "Sumqayıt", "weight": 0.9},
    {"name": "Industrial Services LLC", "type": "SME", "primary_segment": "76000000", "city": "Bakı", "weight": 0.8},
    {"name": "Abşeron Tikinti", "type": "SME", "primary_segment": "72000000", "city": "Bakı", "weight": 1.1},
]

# Line items for different categories
LINE_ITEMS = {
    "76000000": [
        ("Sökülmüş asfalt tullantıları daşınması", 2.5, 5.0, "ton"),
        ("Küçə təmizliyi xidmətləri", 150, 300, "km"),
        ("Sənaye təmizlik xidmətləri", 500, 1500, "saat"),
        ("Tullantı daşınması xidmətləri", 80, 200, "reis"),
    ],
    "22000000": [
        ("Sıx iri-dənəvər AB tipli qaynar asfalt-beton qarışığı", 7.5, 12.0, "ton"),
        ("40-70 mm fraksiyalı qırmadaş", 2.0, 4.0, "ton"),
        ("M-400 markalı sement", 85, 120, "ton"),
        ("Qum-çınqıl qarışığı", 15, 30, "m³"),
        ("Metal armatur d=12mm", 450, 650, "ton"),
        ("Beton blokları", 8, 15, "ədəd"),
    ],
    "15000000": [
        ("Aİ-95 benzin", 1.2, 1.5, "litr"),
        ("Dizel yanacağı", 1.0, 1.3, "litr"),
        ("Motor yağı", 8, 15, "litr"),
        ("Hidravlik maye", 12, 20, "litr"),
    ],
    "43000000": [
        ("Masaüstü kompüter", 800, 2000, "ədəd"),
        ("Noutbuk", 1200, 3500, "ədəd"),
        ("Monitor 24 düym", 250, 450, "ədəd"),
        ("Printer lazer", 350, 800, "ədəd"),
        ("Server avadanlığı", 5000, 25000, "ədəd"),
        ("Şəbəkə avadanlığı", 200, 1500, "ədəd"),
    ],
    "44000000": [
        ("A4 kağız (500 vərəq)", 8, 15, "qablaşdırma"),
        ("Qələm dəsti", 5, 12, "dəst"),
        ("Papka A4", 2, 5, "ədəd"),
        ("Toner kartric", 45, 120, "ədəd"),
        ("Ofis stulu", 150, 400, "ədəd"),
        ("İş masası", 200, 600, "ədəd"),
    ],
    "25000000": [
        ("Minik avtomobili", 25000, 60000, "ədəd"),
        ("Yük avtomobili", 45000, 120000, "ədəd"),
        ("Mikroavtobus", 35000, 80000, "ədəd"),
        ("Xüsusi texnika", 80000, 250000, "ədəd"),
    ],
    "72000000": [
        ("Yol tikintisi işləri", 50, 150, "m²"),
        ("Bina tikintisi işləri", 300, 800, "m²"),
        ("Körpü tikintisi", 100000, 500000, "layihə"),
        ("Abadlıq işləri", 25, 75, "m²"),
        ("Fasad işləri", 40, 100, "m²"),
    ],
    "80000000": [
        ("Biznes konsaltinq xidmətləri", 2000, 10000, "saat"),
        ("Layihə idarəetməsi", 5000, 25000, "ay"),
        ("Audit xidmətləri", 3000, 15000, "layihə"),
        ("Strateji planlaşdırma", 8000, 30000, "layihə"),
    ],
}

# Street/location names for descriptions
LOCATIONS = [
    "M.Ə.Rəsulzadə küçəsi", "Sönməz Məmmədov küçəsi", "Şıxəli Qurbanov küçəsi",
    "Çəmənli küçəsi", "Nərimanov prospekti", "Azadlıq prospekti",
    "Bakıxanov küçəsi", "Xətai rayonu", "Nəsimi rayonu", "Yasamal rayonu",
    "Sabunçu rayonu", "Binəqədi rayonu", "Suraxanı rayonu", "Qaradağ rayonu",
    "Nizami küçəsi", "28 May küçəsi", "İstiqlaliyyət küçəsi", "Tarqovu şossesi",
    "Sumqayıt şəhəri", "Gəncə şəhəri", "Mingəçevir şəhəri", "Şəki şəhəri",
]


def create_database(db_path: str):
    """Create and populate the procurement database."""
    
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.executescript("""
        -- Vendors table
        CREATE TABLE vendors (
            vendor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_name TEXT NOT NULL,
            vendor_type TEXT NOT NULL,
            registration_date DATE,
            primary_segment TEXT,
            city TEXT
        );
        
        -- UNSPSC Categories reference
        CREATE TABLE categories (
            code TEXT PRIMARY KEY,
            level TEXT NOT NULL,
            name TEXT NOT NULL,
            parent_code TEXT
        );
        
        -- Procurement orders
        CREATE TABLE procurement_orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER,
            estimated_value REAL,
            award_value REAL,
            award_date DATETIME,
            FOREIGN KEY (vendor_id) REFERENCES vendors(vendor_id)
        );
        
        -- Order line items
        CREATE TABLE order_lines (
            line_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            unspsc_code TEXT,
            line_name TEXT,
            line_description TEXT,
            unit_price REAL,
            quantity REAL,
            line_total REAL,
            segment_code TEXT,
            family_code TEXT,
            class_code TEXT,
            FOREIGN KEY (order_id) REFERENCES procurement_orders(order_id)
        );
        
        -- HHI snapshots for performance
        CREATE TABLE hhi_snapshots (
            snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            calculation_date DATE,
            scope_type TEXT,
            scope_value TEXT,
            hhi_value REAL,
            top_vendor_share REAL,
            top_vendor_name TEXT,
            vendor_count INTEGER,
            total_value REAL,
            concentration_level TEXT
        );
        
        -- Create view for easy querying (matches original data format)
        CREATE VIEW orders_view AS
        SELECT 
            po.order_id,
            po.estimated_value,
            po.award_date,
            po.award_value,
            v.vendor_name,
            ol.unspsc_code,
            ol.line_name,
            ol.line_description,
            ol.unit_price,
            ol.quantity,
            ol.segment_code as Segment,
            ol.family_code as Family,
            ol.class_code as Class,
            ol.line_total
        FROM procurement_orders po
        JOIN vendors v ON po.vendor_id = v.vendor_id
        JOIN order_lines ol ON po.order_id = ol.order_id;
    """)
    
    # Insert vendors
    for vendor in VENDORS:
        reg_date = datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1500))
        cursor.execute("""
            INSERT INTO vendors (vendor_name, vendor_type, registration_date, primary_segment, city)
            VALUES (?, ?, ?, ?, ?)
        """, (vendor["name"], vendor["type"], reg_date.strftime("%Y-%m-%d"), 
              vendor["primary_segment"], vendor["city"]))
    
    # Insert categories
    for seg_code, seg_data in CATEGORIES.items():
        cursor.execute("INSERT INTO categories VALUES (?, 'Segment', ?, NULL)",
                      (seg_code, seg_data["name"]))
        for fam_code, fam_data in seg_data["families"].items():
            cursor.execute("INSERT INTO categories VALUES (?, 'Family', ?, ?)",
                          (fam_code, fam_data["name"], seg_code))
            for class_code, class_name in fam_data["classes"].items():
                cursor.execute("INSERT INTO categories VALUES (?, 'Class', ?, ?)",
                              (class_code, class_name, fam_code))
    
    # Generate orders
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 10, 31)
    
    vendor_weights = {v["name"]: v["weight"] for v in VENDORS}
    vendor_segments = {v["name"]: v["primary_segment"] for v in VENDORS}
    
    # Get vendor IDs
    cursor.execute("SELECT vendor_id, vendor_name FROM vendors")
    vendor_ids = {name: vid for vid, name in cursor.fetchall()}
    
    order_count = 0
    target_orders = 500
    
    while order_count < target_orders:
        # Select vendor weighted by market power
        vendor_name = random.choices(
            list(vendor_weights.keys()),
            weights=list(vendor_weights.values())
        )[0]
        vendor_id = vendor_ids[vendor_name]
        primary_segment = vendor_segments[vendor_name]
        
        # Sometimes vendors work in adjacent segments
        if random.random() < 0.3:
            segment = random.choice(list(CATEGORIES.keys()))
        else:
            segment = primary_segment
        
        # Generate order
        days_offset = random.randint(0, (end_date - start_date).days)
        award_date = start_date + timedelta(days=days_offset)
        
        # Generate 1-5 line items per order
        num_lines = random.randint(1, 5)
        line_items_pool = LINE_ITEMS.get(segment, LINE_ITEMS["22000000"])
        
        total_value = 0
        lines_data = []
        
        for _ in range(num_lines):
            item = random.choice(line_items_pool)
            line_name, min_price, max_price, unit = item
            
            unit_price = round(random.uniform(min_price, max_price), 2)
            quantity = random.randint(10, 5000)
            line_total = round(unit_price * quantity, 2)
            total_value += line_total
            
            # Get a random class code from this segment
            seg_data = CATEGORIES.get(segment, list(CATEGORIES.values())[0])
            family = random.choice(list(seg_data["families"].keys()))
            family_data = seg_data["families"][family]
            class_code = random.choice(list(family_data["classes"].keys()))
            
            location = random.choice(LOCATIONS)
            
            lines_data.append({
                "unspsc_code": class_code,
                "line_name": line_name,
                "line_description": location,
                "unit_price": unit_price,
                "quantity": quantity,
                "line_total": line_total,
                "segment_code": segment,
                "family_code": family,
                "class_code": class_code
            })
        
        # Estimated value is usually close to award value
        variance = random.uniform(-0.05, 0.08)
        estimated_value = round(total_value * (1 + variance), 2)
        
        # Insert order
        cursor.execute("""
            INSERT INTO procurement_orders (vendor_id, estimated_value, award_value, award_date)
            VALUES (?, ?, ?, ?)
        """, (vendor_id, estimated_value, total_value, award_date.strftime("%Y-%m-%d %H:%M:%S")))
        
        order_id = cursor.lastrowid
        
        # Insert line items
        for line in lines_data:
            cursor.execute("""
                INSERT INTO order_lines (order_id, unspsc_code, line_name, line_description,
                                        unit_price, quantity, line_total, segment_code, family_code, class_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (order_id, line["unspsc_code"], line["line_name"], line["line_description"],
                  line["unit_price"], line["quantity"], line["line_total"],
                  line["segment_code"], line["family_code"], line["class_code"]))
        
        order_count += 1
    
    # Calculate and store HHI snapshots
    calculate_hhi_snapshots(cursor)
    
    conn.commit()
    conn.close()
    
    print(f"Database created: {db_path}")
    print(f"  - {len(VENDORS)} vendors")
    print(f"  - {order_count} orders")


def calculate_hhi_snapshots(cursor):
    """Calculate HHI for different scopes and store as snapshots."""
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Overall HHI
    cursor.execute("""
        SELECT 
            v.vendor_name,
            SUM(po.award_value) as total,
            SUM(po.award_value) * 100.0 / (SELECT SUM(award_value) FROM procurement_orders) as share
        FROM procurement_orders po
        JOIN vendors v ON po.vendor_id = v.vendor_id
        GROUP BY v.vendor_id
        ORDER BY total DESC
    """)
    
    results = cursor.fetchall()
    hhi = sum(row[2] ** 2 for row in results)
    top_vendor = results[0] if results else ("N/A", 0, 0)
    total_value = sum(row[1] for row in results)
    
    concentration = "low" if hhi < 1500 else ("medium" if hhi < 2500 else "high")
    
    cursor.execute("""
        INSERT INTO hhi_snapshots (calculation_date, scope_type, scope_value, hhi_value,
                                   top_vendor_share, top_vendor_name, vendor_count, total_value, concentration_level)
        VALUES (?, 'overall', 'all', ?, ?, ?, ?, ?, ?)
    """, (today, round(hhi, 2), round(top_vendor[2], 2), top_vendor[0], len(results), total_value, concentration))
    
    # HHI by segment
    cursor.execute("SELECT DISTINCT segment_code FROM order_lines WHERE segment_code IS NOT NULL")
    segments = [row[0] for row in cursor.fetchall()]
    
    for segment in segments:
        cursor.execute("""
            SELECT 
                v.vendor_name,
                SUM(ol.line_total) as total
            FROM order_lines ol
            JOIN procurement_orders po ON ol.order_id = po.order_id
            JOIN vendors v ON po.vendor_id = v.vendor_id
            WHERE ol.segment_code = ?
            GROUP BY v.vendor_id
            ORDER BY total DESC
        """, (segment,))
        
        results = cursor.fetchall()
        if not results:
            continue
            
        total_segment = sum(row[1] for row in results)
        shares = [(row[0], row[1] * 100 / total_segment) for row in results]
        hhi = sum(share[1] ** 2 for share in shares)
        top_vendor = shares[0] if shares else ("N/A", 0)
        
        concentration = "low" if hhi < 1500 else ("medium" if hhi < 2500 else "high")
        
        cursor.execute("""
            INSERT INTO hhi_snapshots (calculation_date, scope_type, scope_value, hhi_value,
                                       top_vendor_share, top_vendor_name, vendor_count, total_value, concentration_level)
            VALUES (?, 'segment', ?, ?, ?, ?, ?, ?, ?)
        """, (today, segment, round(hhi, 2), round(top_vendor[1], 2), top_vendor[0], 
              len(results), total_segment, concentration))


if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(__file__), "procurement.db")
    create_database(db_path)
