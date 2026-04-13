# 📦 Importing Real Parquet Data into Procurement-Wolf

## Quick Start (2 Steps)

### Step 1: Ensure Parquet Files Are Available

Your parquet files should be in one of these locations:
- `/content/orders_v3.parquet` and `/content/order_lines-v3.parquet` (shared folder)
- `data/orders_v3.parquet` and `data/order_lines-v3.parquet` (in project)

### Step 2: Run the Importer

```bash
cd /Users/orhan/Projects/Procurement-Wolf
python data/import_data.py
```

Or directly:
```bash
python data/import_parquet.py
```

The importer auto-detects your parquet files and imports everything.

---

## What Gets Imported

### ✅ From `orders_v3.parquet`
- `order_id` → Procurement order identifier
- `vendor_name` → Extracted as unique vendors
- `award_date` → When order was awarded
- `award_value` → Final contract value
- `estimated_value` → Original estimate

**Auto-Processing:**
- Unique vendors extracted from `vendor_name`
- Vendor types inferred from order value/frequency:
  - Large: >₼2M total or avg >₼500k
  - SME: 3-10 orders
  - SME: 1-2 orders
- Primary segment guessed from order line items
- City defaults to Bakı (update manually if needed)

### ✅ From `order_lines-v3.parquet`
- `order_id` → Links to procurement orders
- `unspcs_code` → 8-digit UNSPSC code (AUTO-PARSED)
- `line_name` → Item short name
- `line_description` → Detailed description
- `unit_price` × `quantity` → AUTO-CALCULATED as `line_total`

**Automatic UNSPSC Parsing:**
```
Input:  78181507
↓ (automated)
Output: 
- Segment: 78000000
- Family:  78180000  
- Class:   78181500
- Name:    Transportation Equipment
```

---

## Example Import

```bash
$ python data/import_data.py

📦 Parquet files detected, importing...

📥 Reading Parquet files...
   ✓ Orders: 1,250 records
   ✓ Order Lines: 5,347 records

👥 Processing vendors...
   ✓ Inserted 47 vendors

📝 Processing orders...
   ✓ Inserted 1,250 orders

📦 Processing line items...
   ✓ Inserted 5,347 line items

✨ Import Complete!
   📊 47 vendors
   📝 1,250 orders
   💰 Total value: ₼623,456,789.50
```

---

## Data Flow

```
orders_v3.parquet ──┐
                    ├──→ Import Script ──→ Database
order_lines_v3.parquet──┤                    └─ App loads data
                    └─ Auto-parsing
                      UNSPSC codes
                      Vendor types
                      Line totals
```

---

## Important Notes

### 🔄 Re-importing Data
If you need to re-import, first clear old data:

```python
from data.import_parquet import clear_all_data
clear_all_data("/path/to/procurement.db")
```

Then run the importer again.

### 📍 Vendor City/Type Customization
The importer makes intelligent guesses, but you can refine them:

1. After import, connect to SQLite:
```bash
sqlite3 data/procurement.db
```

2. Update vendor info:
```sql
UPDATE vendors 
SET vendor_type = 'Large', city = 'Sumqayıt' 
WHERE vendor_name = 'Your Company';
```

### 🏢 UNSPSC Segments Supported
| Code | Segment |
|------|---------|
| 78xxxx | Transportation Equipment |
| 22xxxx | Building Materials |
| 15xxxx | Fuels & Lubricants |
| 25xxxx | Vehicles & Transportation |
| 43xxxx | IT Equipment |
| 44xxxx | Office Equipment |
| 72xxxx | Construction Services |
| 76xxxx | Industrial Cleaning |
| 80xxxx | Management Services |

---

## Using Imported Data in the App

1. **Start the app** (data auto-loads):
```bash
streamlit run app.py
```

2. **Login** with password from `user.md`

3. **Explore analytics:**
   - 💬 AI Chat - Ask questions about data
   - 📊 HHI Monitor - See vendor concentration
   - 💰 Spending - Track expenditures
   - 👥 Vendors - Analyze vendor performance
   - 🔧 SQL Playground - Custom queries

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Parquet files not found" | Ensure files are in `/content/` or `data/` folders |
| Import hangs | Check file sizes; large files may take minutes |
| Vendor names don't match HHI | Verify exact spelling in both parquet files |
| UNSPSC codes not parsed | Check format is 8-digit (pad with zeros if needed) |
| Database locked | Close the app before re-importing |

---

## Performance Tips

- **First import:** 1,000+ orders typically takes 2-5 minutes
- **Indexed queries:** After import, run this for faster analytics:
```sql
CREATE INDEX idx_vendor_id ON procurement_orders(vendor_id);
CREATE INDEX idx_order_id ON order_lines(order_id);
CREATE INDEX idx_award_date ON procurement_orders(award_date);
```

- **Clear cache** before re-launching app:
```bash
streamlit run app.py -- --clear-cache
```
