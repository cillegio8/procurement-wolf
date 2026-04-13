"""
ProcureInsight AI - Business Intelligence Platform
Main Streamlit Application

Features:
- Text-to-SQL chat interface using Vanna AI
- HHI (Herfindahl-Hirschman Index) market concentration analysis
- Procurement spending dashboards
- Vendor analysis and performance tracking
"""

import streamlit as st
import sqlite3
import os
import sys
import re

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from components.chat_interface import render_chat_interface, render_sql_playground
from components.hhi_dashboard import render_hhi_dashboard, render_hhi_trends
from components.spending_dashboard import render_spending_dashboard, render_vendor_analysis
from components.data_import import render_data_import
from utils.vanna_integration import ProcurementVanna

# Page configuration
st.set_page_config(
    page_title="ProcureInsight AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    /* Metric cards */
    [data-testid="metric-container"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        padding: 1rem;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #f8fafc;
    }
    
    /* Success/warning/error messages */
    .stAlert {
        border-radius: 0.5rem;
    }
    
    /* Tables */
    .dataframe {
        font-size: 0.9rem;
    }
    
    /* Chat messages */
    [data-testid="stChatMessage"] {
        border-radius: 0.5rem;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "procurement.db")


def load_password():
    """Load password from user.md file."""
    user_md_path = os.path.join(os.path.dirname(__file__), "user.md")
    if os.path.exists(user_md_path):
        with open(user_md_path, 'r') as f:
            content = f.read()
            # Extract password from markdown format "password: <value>"
            match = re.search(r'password:\s*(\S+)', content)
            if match:
                return match.group(1)
    return None


def check_authentication():
    """Check if user is authenticated. Returns True if authenticated, False otherwise."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        # Show login page
        st.set_page_config(
            page_title="ProcureInsight AI - Login",
            page_icon="📊",
            layout="centered"
        )
        
        st.markdown('<h1 style="text-align: center; font-size: 2.5rem; margin-bottom: 2rem;">🔐 ProcureInsight</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; font-size: 1.2rem; color: #666;">Sign in to continue</p>', unsafe_allow_html=True)
        
        st.divider()
        
        # Password input
        password_input = st.text_input("Password", type="password", placeholder="Enter password")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("Sign In", use_container_width=True):
                correct_password = load_password()
                if password_input == correct_password:
                    st.session_state.authenticated = True
                    st.success("✅ Authentication successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid password")
        
        st.stop()
    
    return True



def check_database():
    """Check if database exists, create if not."""
    if not os.path.exists(DB_PATH):
        st.warning("⚠️ Database not found. Generating sample data...")
        
        # Run database generator
        from data.generate_database import create_database
        create_database(DB_PATH)
        
        st.success("✅ Database created successfully!")
        st.rerun()
    
    return True


def init_vanna():
    """Initialize Vanna AI instance."""
    if "vanna" not in st.session_state:
        st.session_state.vanna = ProcurementVanna(DB_PATH)
    return st.session_state.vanna


def main():
    """Main application entry point."""
    
    # Check authentication first
    check_authentication()
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown('<p class="main-header">📊 ProcureInsight</p>', unsafe_allow_html=True)
        st.markdown("**AI-Powered Procurement Analytics**")
        st.divider()
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True, key="logout"):
            st.session_state.authenticated = False
            st.rerun()
        
        st.divider()
        
        # Navigation
        page = st.radio(
            "Navigation",
            [
                "🏠 Overview",
                "💬 AI Chat",
                "📊 HHI Monitor",
                "💰 Spending",
                "👥 Vendors",
                "🔧 SQL Playground",
                "📥 Import Data"
            ],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # Database info
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM vendors")
            vendor_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM procurement_orders")
            order_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(award_value) FROM procurement_orders")
            total_value = cursor.fetchone()[0] or 0
            
            conn.close()
            
            st.markdown("**📁 Database Info**")
            st.markdown(f"- Vendors: **{vendor_count}**")
            st.markdown(f"- Orders: **{order_count}**")
            st.markdown(f"- Value: **₼{total_value:,.0f}**")
        
        st.divider()
        
        # Help section
        with st.expander("ℹ️ Help"):
            st.markdown("""
            **ProcureInsight AI** helps you analyze procurement data using natural language.
            
            **Features:**
            - 💬 Ask questions in plain English
            - 📊 Monitor market concentration (HHI)
            - 💰 Track spending patterns
            - 👥 Analyze vendor performance
            
            **HHI Thresholds:**
            - 🟢 < 1,500: Competitive
            - 🟡 1,500-2,500: Moderate
            - 🔴 > 2,500: High concentration
            """)
    
    # Check database
    if not check_database():
        return
    
    # Initialize Vanna
    vanna = init_vanna()
    
    # Render selected page
    if page == "🏠 Overview":
        render_overview(DB_PATH)
    
    elif page == "💬 AI Chat":
        render_chat_interface(vanna, DB_PATH)
    
    elif page == "📊 HHI Monitor":
        tab1, tab2 = st.tabs(["📊 Current Status", "📈 Trends"])
        
        with tab1:
            render_hhi_dashboard(DB_PATH)
        
        with tab2:
            render_hhi_trends(DB_PATH)
    
    elif page == "💰 Spending":
        render_spending_dashboard(DB_PATH)
    
    elif page == "👥 Vendors":
        render_vendor_analysis(DB_PATH)
    
    elif page == "🔧 SQL Playground":
        render_sql_playground(DB_PATH)
    
    elif page == "📥 Import Data":
        render_data_import()


def render_overview(db_path: str):
    """Render the overview/home page."""
    
    st.markdown('<h1 class="main-header">ProcureInsight AI</h1>', unsafe_allow_html=True)
    st.markdown("### AI-Powered Procurement Intelligence Platform")
    
    st.divider()
    
    # Key metrics row
    conn = sqlite3.connect(db_path)
    
    # Get metrics
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM vendors")
    vendor_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*), SUM(award_value), AVG(award_value) FROM procurement_orders")
    order_stats = cursor.fetchone()
    
    cursor.execute("SELECT hhi_value, concentration_level FROM hhi_snapshots WHERE scope_type = 'overall'")
    hhi_row = cursor.fetchone()
    overall_hhi = hhi_row[0] if hhi_row else 0
    hhi_level = hhi_row[1] if hhi_row else "unknown"
    
    cursor.execute("SELECT COUNT(*) FROM hhi_snapshots WHERE concentration_level = 'high' AND scope_type = 'segment'")
    high_risk_count = cursor.fetchone()[0]
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Spending",
            f"₼{order_stats[1]:,.0f}" if order_stats[1] else "₼0",
            help="Total procurement value"
        )
    
    with col2:
        st.metric(
            "Active Vendors",
            vendor_count,
            help="Number of registered vendors"
        )
    
    with col3:
        hhi_emoji = "🟢" if hhi_level == "low" else ("🟡" if hhi_level == "medium" else "🔴")
        st.metric(
            "Overall HHI",
            f"{overall_hhi:,.0f} {hhi_emoji}",
            help="Herfindahl-Hirschman Index"
        )
    
    with col4:
        st.metric(
            "High Risk Segments",
            high_risk_count,
            help="Segments with HHI > 2,500"
        )
    
    st.divider()
    
    # Quick actions
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚀 Quick Actions")
        
        st.markdown("""
        <div style="background: #f0f9ff; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
            <h4>💬 Ask a Question</h4>
            <p>Use natural language to query procurement data. Try: "What is the HHI for each segment?"</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background: #fef3c7; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
            <h4>📊 Monitor Concentration</h4>
            <p>Track HHI levels to identify vendor dependency risks before they become problems.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background: #dcfce7; padding: 1rem; border-radius: 0.5rem;">
            <h4>📈 Analyze Trends</h4>
            <p>View spending patterns, vendor performance, and budget variance over time.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("⚠️ Alerts & Insights")
        
        # Get high concentration segments
        cursor.execute("""
            SELECT scope_value, hhi_value, top_vendor_name, top_vendor_share 
            FROM hhi_snapshots 
            WHERE concentration_level = 'high' AND scope_type = 'segment'
            ORDER BY hhi_value DESC
            LIMIT 3
        """)
        high_risk = cursor.fetchall()
        
        if high_risk:
            for segment, hhi, vendor, share in high_risk:
                # Get segment name
                cursor.execute("SELECT name FROM categories WHERE code = ?", (segment,))
                name_row = cursor.fetchone()
                segment_name = name_row[0] if name_row else segment
                
                st.error(f"""
                **🔴 High Concentration: {segment_name}**  
                HHI: {hhi:,.0f} | {vendor}: {share:.1f}% market share
                """)
        
        # Get moderate concentration
        cursor.execute("""
            SELECT scope_value, hhi_value, top_vendor_name 
            FROM hhi_snapshots 
            WHERE concentration_level = 'medium' AND scope_type = 'segment'
            ORDER BY hhi_value DESC
            LIMIT 2
        """)
        medium_risk = cursor.fetchall()
        
        if medium_risk:
            for segment, hhi, vendor in medium_risk:
                cursor.execute("SELECT name FROM categories WHERE code = ?", (segment,))
                name_row = cursor.fetchone()
                segment_name = name_row[0] if name_row else segment
                
                st.warning(f"""
                **🟡 Moderate Concentration: {segment_name}**  
                HHI: {hhi:,.0f} | Monitor vendor {vendor}
                """)
        
        if not high_risk and not medium_risk:
            st.success("✅ All segments show healthy competition levels")
    
    st.divider()
    
    # Recent activity
    st.subheader("📋 Recent Procurement Activity")
    
    recent_query = """
        SELECT po.order_id, v.vendor_name, po.award_value, po.award_date,
               c.name as category
        FROM procurement_orders po
        JOIN vendors v ON po.vendor_id = v.vendor_id
        JOIN order_lines ol ON po.order_id = ol.order_id
        LEFT JOIN categories c ON ol.segment_code = c.code
        GROUP BY po.order_id
        ORDER BY po.award_date DESC
        LIMIT 10
    """
    import pandas as pd
    recent_df = pd.read_sql_query(recent_query, conn)
    
    if not recent_df.empty:
        recent_df['award_date'] = pd.to_datetime(recent_df['award_date']).dt.strftime('%Y-%m-%d')
        recent_df['award_value'] = recent_df['award_value'].apply(lambda x: f"₼{x:,.0f}")
        recent_df.columns = ['Order ID', 'Vendor', 'Value', 'Date', 'Category']
        
        st.dataframe(recent_df, use_container_width=True, hide_index=True)
    
    conn.close()


if __name__ == "__main__":
    main()
