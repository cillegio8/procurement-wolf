"""
Import real procurement data from CSV or Parquet files into the database.

Supports:
1. Parquet files (preferred, auto-detects):
   - orders_v3.parquet
   - order_lines-v3.parquet
   
2. CSV files as fallback:
   - vendors.csv
   - procurement_orders.csv  
   - order_lines.csv
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime

def import_from_csv(db_path: str):
    """Import data from CSV files into the database."""
    
    data_dir = os.path.dirname(db_path)
    
    # Check which files exist
    vendors_csv = os.path.join(data_dir, "vendors.csv")
    orders_csv = os.path.join(data_dir, "procurement_orders.csv")
    lines_csv = os.path.join(data_dir, "order_lines.csv")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Import vendors
    if os.path.exists(vendors_csv):
        print("📥 Importing vendors...")
        vendors_df = pd.read_csv(vendors_csv)
        
        for _, row in vendors_df.iterrows():
            cursor.execute("""
                INSERT INTO vendors (vendor_name, vendor_type, registration_date, primary_segment, city)
                VALUES (?, ?, ?, ?, ?)
            """, (
                row.get('vendor_name', ''),
                row.get('vendor_type', ''),
                row.get('registration_date', datetime.now().strftime("%Y-%m-%d")),
                row.get('primary_segment', '76000000'),
                row.get('city', 'Bakı')
            ))
        
        conn.commit()
        print(f"✅ Imported {len(vendors_df)} vendors")
    
    # Import procurement orders
    if os.path.exists(orders_csv):
        print("📥 Importing procurement orders...")
        orders_df = pd.read_csv(orders_csv)
        
        for _, row in orders_df.iterrows():
            # Get vendor_id from vendor_name
            vendor_name = row.get('vendor_name', '')
            cursor.execute("SELECT vendor_id FROM vendors WHERE vendor_name = ?", (vendor_name,))
            result = cursor.fetchone()
            
            if result:
                vendor_id = result[0]
                cursor.execute("""
                    INSERT INTO procurement_orders (vendor_id, award_date, award_value, estimated_value)
                    VALUES (?, ?, ?, ?)
                """, (
                    vendor_id,
                    row.get('award_date', datetime.now().strftime("%Y-%m-%d")),
                    row.get('award_value', 0),
                    row.get('estimated_value', 0)
                ))
            else:
                print(f"⚠️ Vendor '{vendor_name}' not found, skipping order")
        
        conn.commit()
        print(f"✅ Imported {len(orders_df)} orders")
    
    # Import order line items
    if os.path.exists(lines_csv):
        print("📥 Importing order line items...")
        lines_df = pd.read_csv(lines_csv)
        
        for _, row in lines_df.iterrows():
            cursor.execute("""
                INSERT INTO order_lines 
                (order_id, line_name, line_description, unit_price, quantity, 
                 segment_code, family_code, class_code, unspsc_code, line_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(row.get('order_id', 0)),
                row.get('line_name', ''),
                row.get('line_description', ''),
                float(row.get('unit_price', 0)),
                float(row.get('quantity', 0)),
                row.get('segment_code', ''),
                row.get('family_code', ''),
                row.get('class_code', ''),
                row.get('unspsc_code', ''),
                float(row.get('unit_price', 0)) * float(row.get('quantity', 0))
            ))
        
        conn.commit()
        print(f"✅ Imported {len(lines_df)} line items")
    
    conn.close()
    print("\n✨ Data import complete!")


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
    else:
        # Try parquet import first
        parquet_files_found = False
        data_dir = os.path.dirname(db_path)
        
        # Check for parquet files in common locations
        parquet_locations = ["/content/", data_dir, os.path.dirname(db_path) + "/../"]
        parquet_orders = None
        parquet_lines = None
        
        for loc in parquet_locations:
            orders_path = os.path.join(loc, "orders_v3.parquet")
            lines_path = os.path.join(loc, "order_lines-v3.parquet")
            
            if os.path.exists(orders_path) and os.path.exists(lines_path):
                parquet_orders = orders_path
                parquet_lines = lines_path
                parquet_files_found = True
                break
        
        if parquet_files_found:
            print("📦 Parquet files detected, importing...")
            from import_parquet import import_from_parquet
            import_from_parquet(db_path, parquet_orders, parquet_lines)
        else:
            print("📄 Using CSV import...")
            import_from_csv(db_path)
