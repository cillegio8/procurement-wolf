# 📊 Adding Real Data to Procurement-Wolf

## Quick Start

### Step 1: Prepare Your Data
You need 3 CSV files with your real procurement data:
- `vendors.csv` - Your vendors/suppliers
- `procurement_orders.csv` - Orders placed
- `order_lines.csv` - Line items in each order

### Step 2: Use Template Files
Examples are in the `data/` folder:
- `vendors_template.csv`
- `procurement_orders_template.csv` 
- `order_lines_template.csv`

Copy and rename these to match your data:
```bash
cp vendors_template.csv vendors.csv
cp procurement_orders_template.csv procurement_orders.csv
cp order_lines_template.csv order_lines.csv
```

### Step 3: Fill With Your Data
Edit the CSV files with your real data (in Excel, Google Sheets, or text editor)

### Step 4: Import Into App
#### Option A: Run Python Import Script
```bash
cd /Users/orhan/Projects/Procurement-Wolf
python data/import_data.py
```

#### Option B: Import in the App (Auto)
When you first run the app:
```bash
streamlit run app.py
```
The app checks for `vendors.csv`, `procurement_orders.csv`, and `order_lines.csv` and imports them automatically.

---

## Database Schema

### 📋 vendors.csv
```
vendor_name,vendor_type,primary_segment,city,registration_date
String,String,String,String,YYYY-MM-DD
```

**Fields:**
- `vendor_name` - Full company name (required)
- `vendor_type` - Large, SME, or State
- `primary_segment` - UNSPSC code (see segments below)
- `city` - City name
- `registration_date` - When vendor was registered

**Example:**
```
Your Company,Large,76000000,Bakı,2023-01-15
```

---

### 📝 procurement_orders.csv
```
order_id,vendor_name,award_date,award_value,estimated_value
Integer,String,YYYY-MM-DD,Number,Number
```

**Fields:**
- `order_id` - Unique order number (1, 2, 3, ...)
- `vendor_name` - Must match a vendor in vendors.csv
- `award_date` - When order was awarded
- `award_value` - Final contract value
- `estimated_value` - Original estimated value

**Example:**
```
1,Your Company,2025-01-10,50000,60000
```

---

### 🏷️ order_lines.csv
```
order_id,line_name,line_description,unit_price,quantity,segment_code,family_code,class_code,unspsc_code
Integer,String,String,Number,Number,String,String,String,String
```

**Fields:**
- `order_id` - Must match order_id in procurement_orders.csv
- `line_name` - Item name (short)
- `line_description` - Detailed description
- `unit_price` - Price per unit
- `quantity` - Number of units
- `segment_code` - UNSPSC Segment (6 digits)
- `family_code` - UNSPSC Family (8 digits)  
- `class_code` - UNSPSC Class (8 digits)
- `unspsc_code` - Custom code (optional)

**Example:**
```
1,Asfalt qarışığı,Açık asfalt qarışığı,500,100,22000000,22100000,22101600,ASPH001
1,Sement,M-400 markalı sement,90,50,22000000,22100000,22101700,CEM001
```

---

## UNSPSC Segments (Category Codes)

| Code | Segment Name | Example Products |
|------|--------------|------------------|
| 76000000 | Industrial Cleaning Services | Street cleaning, maintenance |
| 22000000 | Building Materials | Cement, concrete, asphalt |
| 15000000 | Fuels & Lubricants | Petrol, diesel, motor oil |
| 43000000 | IT Equipment & Services | Computers, servers, software |
| 44000000 | Office Equipment & Supplies | Paper, stationery, furniture |
| 25000000 | Vehicles & Transportation | Cars, trucks, buses |
| 72000000 | Construction Services | Building, roads, bridges |
| 80000000 | Management & Consulting | Consulting, project management |

---

## Example: Complete Data Set

**vendors.csv:**
```
vendor_name,vendor_type,primary_segment,city,registration_date
Road Construction Co,Large,72000000,Bakı,2022-05-10
Cement Factory LLC,Large,22000000,Gəncə,2021-08-15
Office Supply Store,SME,44000000,Bakı,2023-01-20
Tech Services AZ,SME,43000000,Bakı,2023-06-01
```

**procurement_orders.csv:**
```
order_id,vendor_name,award_date,award_value,estimated_value
1,Road Construction Co,2025-01-15,250000,300000
2,Cement Factory LLC,2025-01-18,150000,170000
3,Office Supply Store,2025-02-01,25000,30000
4,Tech Services AZ,2025-02-10,45000,50000
```

**order_lines.csv:**
```
order_id,line_name,line_description,unit_price,quantity,segment_code,family_code,class_code,unspsc_code
1,Road Construction,Highway construction work,500,400,72000000,72100000,72101500,ROAD001
2,Cement Bags,M-400 Portland cement,90,1200,22000000,22100000,22101700,CEM001
3,Paper Reams,A4 copy paper 500 sheets,8,200,44000000,44120000,44121600,PAPER001
4,Laptops,Dell Latitude business laptops,1500,15,43000000,43210000,43211500,LAP001
```

---

## Tips

✅ **Do This:**
- Keep order_id values sequential (1, 2, 3...)
- Vendor names in procurement_orders.csv must EXACTLY match vendors.csv
- Use proper UNSPSC codes for accurate HHI calculations
- Set realistic award dates (2024-2025)

❌ **Don't Do This:**
- Duplicate vendor names with different cases
- Skip required fields (leave empty if unknown)
- Use future dates beyond 2025
- Create order_lines without matching order_id

---

## Replace All Data

To clear the database and start fresh:

```python
from data.import_data import clear_all_data
clear_all_data("/Users/orhan/Projects/Procurement-Wolf/data/procurement.db")
```

Then run the import again.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Vendor names don't match | Double-check spelling in procurement_orders.csv |
| Import fails | Run `python data/import_data.py` to see detailed error |
| No data in app | Restart with `streamlit run app.py` --clear-cache |
| HHI not calculating | Verify UNSPSC segment codes are correct |
