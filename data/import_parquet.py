"""
Import real procurement data from Parquet files into the database.
Handles actual data structure with UNSPSC code parsing and vendor extraction.
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime
import json

# UNSPSC Segment mappings for common 8-digit codes
UNSPSC_SEGMENTS = {
    # Format: "78000000" -> (segment_code, segment_name)
    "78": ("78000000", "Transportation Equipment"),
    "22": ("22000000", "Building and Construction Materials"),
    "15": ("15000000", "Fuels and Lubricants"),
    "25": ("25000000", "Vehicles and Transportation"),
    "43": ("43000000", "IT Equipment and Services"),
    "44": ("44000000", "Office Equipment and Supplies"),
    "72": ("72000000", "Building and Construction Services"),
    "76": ("76000000", "Industrial Cleaning Services"),
    "80": ("80000000", "Management and Business Services"),
}


def parse_unspsc_code(code: str):
    """
    Parse 8-digit UNSPSC code into segment, family, and class levels.
    
    Example: 78181507 -> segment: 78000000, family: 78180000, class: 78181500
    """
    code_str = str(code).strip()
    
    if len(code_str) < 8:
        code_str = code_str.ljust(8, '0')
    
    # Extract levels
    segment_code = code_str[:2] + "000000"  # First 2 digits
    family_code = code_str[:4] + "0000"      # First 4 digits
    class_code = code_str[:6] + "00"         # First 6 digits
    
    # Get segment name
    segment_prefix = code_str[:2]
    if segment_prefix in UNSPSC_SEGMENTS:
        segment_name = UNSPSC_SEGMENTS[segment_prefix][1]
    else:
        segment_name = f"UNSPSC Segment {segment_prefix}"
    
    return {
        "segment_code": segment_code,
        "family_code": family_code,
        "class_code": class_code,
        "segment_name": segment_name,
        "unspsc_code": code_str
    }


def infer_vendor_type(total_award_value: float, order_count: int):
    """Infer vendor type based on order value and frequency."""
    avg_order_value = total_award_value / order_count if order_count > 0 else 0
    
    if total_award_value > 2000000 or avg_order_value > 500000:
        return "Large"
    elif order_count > 10:
        return "Large"
    elif order_count >= 3:
        return "SME"
    else:
        return "SME"


def import_from_parquet(db_path: str, parquet_orders: str = None, parquet_lines: str = None):
    """
    Import data from Parquet files into the database.
    
    Args:
        db_path: Path to SQLite database
        parquet_orders: Path to orders_v3.parquet (auto-detects if None)
        parquet_lines: Path to order_lines-v3.parquet (auto-detects if None)
    """
    
    data_dir = os.path.dirname(db_path)
    
    # Auto-detect parquet files
    if not parquet_orders:
        # Check common locations
        common_paths = [
            "/content/orders_v3.parquet",
            os.path.join(data_dir, "orders_v3.parquet"),
            os.path.join(data_dir, "../orders_v3.parquet"),
        ]
        for path in common_paths:
            if os.path.exists(path):
                parquet_orders = path
                print(f"✓ Found orders file: {path}")
                break
    
    if not parquet_lines:
        common_paths = [
            "/content/order_lines-v3.parquet",
            os.path.join(data_dir, "order_lines-v3.parquet"),
            os.path.join(data_dir, "../order_lines-v3.parquet"),
        ]
        for path in common_paths:
            if os.path.exists(path):
                parquet_lines = path
                print(f"✓ Found order lines file: {path}")
                break
    
    if not parquet_orders or not parquet_lines:
        print("❌ Parquet files not found!")
        print(f"   Looking for: orders_v3.parquet and order_lines-v3.parquet")
        print(f"   Tried: {data_dir} and /content/")
        return False
    
    try:
        # Read parquet files
        print("\n📥 Reading Parquet files...")
        orders_df = pd.read_parquet(parquet_orders)
        lines_df = pd.read_parquet(parquet_lines)
        
        print(f"   ✓ Orders: {len(orders_df)} records")
        print(f"   ✓ Order Lines: {len(lines_df)} records")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Step 1: Extract unique vendors from orders
        print("\n👥 Processing vendors...")
        unique_vendors = orders_df['vendor_name'].unique()
        
        # Calculate vendor metrics for type inference
        vendor_stats = {}
        for vendor in unique_vendors:
            vendor_orders = orders_df[orders_df['vendor_name'] == vendor]
            total_value = vendor_orders['award_value'].sum()
            order_count = len(vendor_orders)
            vendor_stats[vendor] = {
                'total_value': total_value,
                'order_count': order_count,
                'avg_order': total_value / order_count if order_count > 0 else 0
            }
        
        # Insert vendors (auto-detect type based on order statistics)
        vendor_id_map = {}
        for vendor_name in unique_vendors:
            stats = vendor_stats[vendor_name]
            vendor_type = infer_vendor_type(stats['total_value'], stats['order_count'])
            
            # Try to infer city from vendor name (heuristic)
            city = "Bakı"  # Default
            if "Sumqayıt" in vendor_name:
                city = "Sumqayıt"
            elif "Gəncə" in vendor_name:
                city = "Gəncə"
            
            # Try to infer segment from order lines
            segment_code = "76000000"  # Default
            vendor_lines = lines_df[lines_df['order_id'].isin(
                orders_df[orders_df['vendor_name'] == vendor_name]['order_id']
            )]
            if len(vendor_lines) > 0:
                # Get most common segment
                parsed = parse_unspsc_code(vendor_lines['unspcs_code'].iloc[0])
                segment_code = parsed['segment_code']
            
            cursor.execute("""
                INSERT INTO vendors (vendor_name, vendor_type, registration_date, primary_segment, city)
                VALUES (?, ?, ?, ?, ?)
            """, (
                vendor_name,
                vendor_type,
                datetime(2020, 1, 1).strftime("%Y-%m-%d"),
                segment_code,
                city
            ))
            
            vendor_id_map[vendor_name] = cursor.lastrowid
        
        conn.commit()
        print(f"   ✓ Inserted {len(unique_vendors)} vendors")
        
        # Step 2: Insert procurement orders
        print("\n📝 Processing orders...")
        for _, row in orders_df.iterrows():
            vendor_id = vendor_id_map[row['vendor_name']]
            
            cursor.execute("""
                INSERT INTO procurement_orders (vendor_id, award_date, award_value, estimated_value)
                VALUES (?, ?, ?, ?)
            """, (
                vendor_id,
                row['award_date'],
                float(row['award_value']),
                float(row['estimated_value'])
            ))
        
        conn.commit()
        print(f"   ✓ Inserted {len(orders_df)} orders")
        
        # Step 3: Insert order line items
        print("\n📦 Processing line items...")
        
        # Get mapping of order_id to database order_id
        cursor.execute("SELECT order_id FROM procurement_orders WHERE order_id IN (SELECT order_id FROM procurement_orders)")
        db_order_ids = {row[0]: row[0] for row in cursor.fetchall()}
        
        for _, row in lines_df.iterrows():
            order_id = row['order_id']
            
            # Parse UNSPSC code
            unspsc_info = parse_unspsc_code(row['unspcs_code'])
            
            # Calculate line total
            line_total = float(row['unit_price']) * float(row['quantity'])
            
            cursor.execute("""
                INSERT INTO order_lines 
                (order_id, line_name, line_description, unit_price, quantity, 
                 segment_code, family_code, class_code, unspsc_code, line_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                row['line_name'][:100] if len(str(row['line_name'])) > 100 else row['line_name'],
                row['line_description'][:255] if len(str(row['line_description'])) > 255 else row['line_description'],
                float(row['unit_price']),
                float(row['quantity']),
                unspsc_info['segment_code'],
                unspsc_info['family_code'],
                unspsc_info['class_code'],
                unspsc_info['unspsc_code'],
                line_total
            ))
        
        conn.commit()
        print(f"   ✓ Inserted {len(lines_df)} line items")
        
        # Summary
        cursor.execute("SELECT COUNT(*) FROM vendors")
        vendor_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM procurement_orders")
        order_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(award_value) FROM procurement_orders")
        total_value = cursor.fetchone()[0] or 0
        
        conn.close()
        
        print(f"\n✨ Import Complete!")
        print(f"   📊 {vendor_count} vendors")
        print(f"   📝 {order_count} orders")
        print(f"   💰 Total value: ₼{total_value:,.2f}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during import: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def clear_all_data(db_path: str):
    """Clear all imported data (keep schema). Use with caution!"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Delete data in reverse order (foreign key constraints)
    cursor.execute("DELETE FROM order_lines")
    cursor.execute("DELETE FROM procurement_orders")
    cursor.execute("DELETE FROM vendors")
    
    conn.commit()
    conn.close()
    print("🗑️ All data cleared")


if __name__ == "__main__":
    db_path = os.path.join(os.path.dirname(__file__), "procurement.db")
    
    # Check if database exists
    if not os.path.exists(db_path):
        print("❌ Database not found. Run the app first to create it.")
        print(f"   Expected at: {db_path}")
    else:
        import_from_parquet(db_path)
