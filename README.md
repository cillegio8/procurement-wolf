# ProcureInsight AI 📊

**AI-Powered Procurement Business Intelligence Platform**

A comprehensive Streamlit application for procurement analytics featuring:
- 💬 **Text-to-SQL Chat** - Ask questions in natural language
- 📊 **HHI Monitor** - Track market concentration risks (Herfindahl-Hirschman Index)
- 💰 **Spending Dashboard** - Analyze procurement patterns and vendor performance
- 👥 **Vendor Analysis** - Deep-dive into vendor metrics and trends

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# Clone/download the project
cd procure_insight

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 📁 Project Structure

```
procure_insight/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── data/
│   ├── generate_database.py  # Sample data generator
│   └── procurement.db        # SQLite database (auto-generated)
├── components/
│   ├── __init__.py
│   ├── chat_interface.py     # NL query chat interface
│   ├── hhi_dashboard.py      # HHI concentration monitor
│   └── spending_dashboard.py # Spending analytics
└── utils/
    ├── __init__.py
    ├── hhi_calculator.py     # HHI calculation utilities
    └── vanna_integration.py  # Text-to-SQL engine
```

---

## 📊 Features

### 1. AI Chat Interface
Ask questions in plain language (English or Azerbaijani):
- "What is the total spending by vendor?"
- "Show me the HHI concentration by segment"
- "Which categories have high concentration risk?"
- "Top 10 vendors by order count"

### 2. HHI Market Concentration Monitor

The **Herfindahl-Hirschman Index** measures market concentration:

| HHI Range | Classification | Risk Level |
|-----------|---------------|------------|
| < 1,500 | Competitive | 🟢 Low |
| 1,500 - 2,500 | Moderate | 🟡 Medium |
| > 2,500 | Highly Concentrated | 🔴 High |

**Features:**
- Overall market HHI
- Segment-level analysis
- Risk alerts and recommendations
- Vendor impact simulation
- Historical trends

### 3. Spending Dashboard
- Total spending metrics
- Top vendors analysis
- Category breakdown
- Monthly trends
- Budget variance analysis (Estimated vs Actual)

### 4. Vendor Analysis
- Filterable vendor list
- Type and city distribution
- Individual vendor deep-dive
- Order history and patterns

---

## 🗃️ Database Schema

### Tables

**vendors**
- vendor_id, vendor_name, vendor_type (SME/Large/State)
- city, primary_segment, registration_date

**procurement_orders**
- order_id, vendor_id, estimated_value, award_value, award_date

**order_lines**
- line_id, order_id, unspsc_code, line_name
- unit_price, quantity, line_total
- segment_code, family_code, class_code

**hhi_snapshots**
- snapshot_id, calculation_date, scope_type, scope_value
- hhi_value, concentration_level, top_vendor_share

---

## 🏢 Sample Data

The database includes **45 Azerbaijani vendors** across **8 UNSPSC segments**:
- Road Construction & Infrastructure
- Building Materials
- Fuels & Lubricants
- IT Equipment & Services
- Office Supplies
- Vehicles & Transportation
- Construction Services
- Management & Consulting

Currency: **AZN (₼)**

---

## 🔧 Configuration

### Optional: Enable Vanna AI (Advanced NL-to-SQL)

For enhanced natural language processing, add your OpenAI API key:

```bash
export OPENAI_API_KEY="your-key-here"
```

Without an API key, the app uses pattern-based query matching.

---

## 📝 Example Queries

### Spending Analysis
```
"What is the total spending by vendor?"
"Show spending by category"
"Monthly spending trend"
```

### HHI Analysis
```
"What is the current HHI?"
"Which segments have high concentration?"
"Show concentration risk alerts"
```

### Vendor Analysis
```
"List all vendors by type"
"Vendors in Baku"
"Top vendors by order count"
```

---

## 📄 License

MIT License - Feel free to use and modify.

---

## 🤝 Contributing

Contributions welcome! Please submit issues and pull requests.

---

Built with ❤️ using Streamlit, Plotly, and Python
