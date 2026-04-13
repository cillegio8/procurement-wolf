"""
Data import component for Streamlit app.
Allows users to upload and import parquet files directly from the UI.
"""

import streamlit as st
import os
import tempfile
from io import BytesIO


def render_data_import():
    """Render the data import interface."""
    
    st.markdown('<h1 class="main-header">📥 Import Data</h1>', unsafe_allow_html=True)
    st.markdown("### Upload And Import Procurement Data")
    
    st.divider()
    
    # Introduction
    with st.info():
        st.markdown("""
        Upload your procurement data files to import into the system.
        
        **Supported formats:**
        - 🔹 **Parquet files** (recommended): `orders_v3.parquet` and `order_lines-v3.parquet`
        - 📄 **CSV files**: `vendors.csv`, `procurement_orders.csv`, `order_lines.csv`
        """)
    
    # Tabs for different import methods
    tab1, tab2, tab3 = st.tabs(["📦 Parquet Import", "📄 CSV Import", "ℹ️ Format Guide"])
    
    # ===== TAB 1: PARQUET IMPORT =====
    with tab1:
        st.subheader("Parquet File Upload")
        st.markdown("Upload your parquet files from your procurement system.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            orders_file = st.file_uploader(
                "Orders File (orders_v3.parquet)",
                type=["parquet"],
                key="orders_parquet"
            )
        
        with col2:
            lines_file = st.file_uploader(
                "Order Lines File (order_lines-v3.parquet)",
                type=["parquet"],
                key="lines_parquet"
            )
        
        if st.button("🚀 Import Parquet Data", type="primary", use_container_width=True):
            if orders_file is None or lines_file is None:
                st.error("❌ Please upload both files")
            else:
                import_parquet_files(orders_file, lines_file)
    
    # ===== TAB 2: CSV IMPORT =====
    with tab2:
        st.subheader("CSV File Upload")
        st.markdown("Upload CSV files for vendors, orders, and line items.")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            vendors_file = st.file_uploader(
                "Vendors (vendors.csv)",
                type=["csv"],
                key="vendors_csv"
            )
        
        with col2:
            orders_file = st.file_uploader(
                "Orders (procurement_orders.csv)",
                type=["csv"],
                key="orders_csv"
            )
        
        with col3:
            lines_file = st.file_uploader(
                "Line Items (order_lines.csv)",
                type=["csv"],
                key="lines_csv"
            )
        
        if st.button("🚀 Import CSV Data", type="primary", use_container_width=True):
            import_csv_files(vendors_file, orders_file, lines_file)
    
    # ===== TAB 3: FORMAT GUIDE =====
    with tab3:
        st.subheader("Data Format Guide")
        
        format_info = """
        ### 📦 Parquet Files
        
        **orders_v3.parquet:**
        - `order_id` - Unique order identifier
        - `vendor_name` - Vendor/supplier name  
        - `award_date` - Order award date
        - `award_value` - Final contract value
        - `estimated_value` - Original estimated value
        
        **order_lines-v3.parquet:**
        - `order_id` - Links to orders file
        - `unspcs_code` - 8-digit UNSPSC code (e.g., 78181507)
        - `line_name` - Item short name
        - `line_description` - Detailed description
        - `unit_price` - Unit cost
        - `quantity` - Quantity ordered
        
        ---
        
        ### 📄 CSV Files
        
        **vendors.csv:**
        ```
        vendor_name,vendor_type,primary_segment,city,registration_date
        Your Company,Large,76000000,Bakı,2023-01-15
        ```
        
        **procurement_orders.csv:**
        ```
        order_id,vendor_name,award_date,award_value,estimated_value
        1,Your Company,2025-01-10,50000,60000
        ```
        
        **order_lines.csv:**
        ```
        order_id,line_name,line_description,unit_price,quantity,segment_code,family_code,class_code,unspsc_code
        1,Asfalt,Asfalt qarışığı,500,100,22000000,22100000,22101600,ASPH001
        ```
        """
        st.markdown(format_info)
    
    st.divider()
    
    # Data status
    st.subheader("📊 Current Data Status")
    
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "../data/procurement.db")
    
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM vendors")
            vendor_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM procurement_orders")
            order_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM order_lines")
            line_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(award_value) FROM procurement_orders")
            total_value = cursor.fetchone()[0] or 0
            
            conn.close()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Vendors", vendor_count)
            
            with col2:
                st.metric("Orders", order_count)
            
            with col3:
                st.metric("Line Items", line_count)
            
            with col4:
                st.metric("Total Value", f"₼{total_value:,.0f}")
            
            if vendor_count > 0:
                if st.button("🗑️ Clear All Data", help="Delete all imported data"):
                    if st.session_state.get("confirm_clear"):
                        clear_database(db_path)
                    else:
                        st.session_state.confirm_clear = True
                        st.warning("⚠️ This will delete all data. Click the button again to confirm.")
        
        except Exception as e:
            st.error(f"Error accessing database: {str(e)}")


def import_parquet_files(orders_file, lines_file):
    """Import parquet files into the database."""
    
    import pandas as pd
    import sqlite3
    import sys
    
    db_path = os.path.join(os.path.dirname(__file__), "../data/procurement.db")
    
    try:
        with st.spinner("📥 Reading parquet files..."):
            orders_df = pd.read_parquet(orders_file)
            lines_df = pd.read_parquet(lines_file)
            
            st.success(f"✓ Loaded {len(orders_df)} orders and {len(lines_df)} line items")
        
        with st.spinner("⚙️ Processing data..."):
            # Import using the parquet import function
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../data"))
            from import_parquet import import_from_parquet, parse_unspsc_code
            
            # Write temp files
            with tempfile.TemporaryDirectory() as tmpdir:
                orders_path = os.path.join(tmpdir, "orders_v3.parquet")
                lines_path = os.path.join(tmpdir, "order_lines-v3.parquet")
                
                orders_file.seek(0)
                with open(orders_path, "wb") as f:
                    f.write(orders_file.read())
                
                lines_file.seek(0)
                with open(lines_path, "wb") as f:
                    f.write(lines_file.read())
                
                # Run import
                success = import_from_parquet(db_path, orders_path, lines_path)
        
        if success:
            st.success("✨ Import completed successfully!")
            st.balloons()
            st.rerun()
        else:
            st.error("❌ Import failed. Check the logs above.")
    
    except Exception as e:
        st.error(f"❌ Error during import: {str(e)}")
        import traceback
        st.code(traceback.format_exc(), language="python")


def import_csv_files(vendors_file, orders_file, lines_file):
    """Import CSV files into the database."""
    
    import pandas as pd
    import sqlite3
    
    db_path = os.path.join(os.path.dirname(__file__), "../data/procurement.db")
    
    if not vendors_file or not orders_file or not lines_file:
        st.error("❌ Please upload all three CSV files")
        return
    
    try:
        with st.spinner("📥 Reading CSV files..."):
            vendors_df = pd.read_csv(vendors_file)
            orders_df = pd.read_csv(orders_file)
            lines_df = pd.read_csv(lines_file)
            
            st.success(f"✓ Loaded {len(vendors_df)} vendors, {len(orders_df)} orders, {len(lines_df)} line items")
        
        with st.spinner("⚙️ Processing data..."):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Import vendors
            vendor_id_map = {}
            for _, row in vendors_df.iterrows():
                cursor.execute("""
                    INSERT INTO vendors (vendor_name, vendor_type, registration_date, primary_segment, city)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    row.get('vendor_name', ''),
                    row.get('vendor_type', 'SME'),
                    row.get('registration_date', '2023-01-01'),
                    row.get('primary_segment', '76000000'),
                    row.get('city', 'Bakı')
                ))
                vendor_id_map[row['vendor_name']] = cursor.lastrowid
            
            conn.commit()
            st.success(f"✓ Imported {len(vendors_df)} vendors")
            
            # Import orders
            for _, row in orders_df.iterrows():
                vendor_id = vendor_id_map.get(row['vendor_name'])
                if vendor_id:
                    cursor.execute("""
                        INSERT INTO procurement_orders (vendor_id, award_date, award_value, estimated_value)
                        VALUES (?, ?, ?, ?)
                    """, (
                        vendor_id,
                        row.get('award_date'),
                        float(row.get('award_value', 0)),
                        float(row.get('estimated_value', 0))
                    ))
            
            conn.commit()
            st.success(f"✓ Imported {len(orders_df)} orders")
            
            # Import line items
            for _, row in lines_df.iterrows():
                cursor.execute("""
                    INSERT INTO order_lines 
                    (order_id, line_name, line_description, unit_price, quantity, 
                     segment_code, family_code, class_code, unspsc_code, line_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(row.get('order_id')),
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
            conn.close()
        
        st.success("✨ Import completed successfully!")
        st.balloons()
        st.rerun()
    
    except Exception as e:
        st.error(f"❌ Error during import: {str(e)}")
        import traceback
        st.code(traceback.format_exc(), language="python")


def clear_database(db_path: str):
    """Clear all data from the database."""
    
    import sqlite3
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM order_lines")
        cursor.execute("DELETE FROM procurement_orders")
        cursor.execute("DELETE FROM vendors")
        
        conn.commit()
        conn.close()
        
        st.success("✅ Database cleared successfully!")
        st.session_state.confirm_clear = False
        st.rerun()
    
    except Exception as e:
        st.error(f"❌ Error clearing database: {str(e)}")
