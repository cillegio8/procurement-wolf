"""
HHI (Herfindahl-Hirschman Index) Dashboard Component.
Displays market concentration analysis and alerts.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
from typing import Optional
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.hhi_calculator import (
    calculate_hhi_overall,
    calculate_hhi_by_segment,
    get_all_segments_hhi,
    calculate_hhi_trend,
    get_vendor_market_share,
    simulate_hhi_without_vendor,
    HHIResult
)


def render_hhi_dashboard(db_path: str):
    """Render the HHI concentration dashboard."""
    
    conn = sqlite3.connect(db_path)
    
    st.header("📊 Market Concentration Monitor (HHI)")
    
    # HHI explanation
    with st.expander("ℹ️ What is HHI?"):
        st.markdown("""
        The **Herfindahl-Hirschman Index (HHI)** measures market concentration by summing 
        the squares of market shares of all participants.
        
        **Formula:** HHI = Σ (Market Share %)²
        
        | HHI Range | Classification | Risk Level |
        |-----------|---------------|------------|
        | < 1,500 | Competitive | 🟢 Low |
        | 1,500 - 2,500 | Moderate Concentration | 🟡 Medium |
        | > 2,500 | Highly Concentrated | 🔴 High |
        
        **Higher HHI indicates:**
        - Less competition
        - Higher vendor dependency risk
        - Potential pricing power by dominant vendors
        """)
    
    # Overall HHI Card
    overall_hhi = calculate_hhi_overall(conn)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Overall HHI",
            f"{overall_hhi.hhi_value:,.0f}",
            delta=None,
            help="Market concentration across all procurement"
        )
        st.markdown(f"**{overall_hhi.risk_emoji} {overall_hhi.concentration_level.title()}** concentration")
    
    with col2:
        st.metric(
            "Active Vendors",
            overall_hhi.vendor_count,
            help="Number of vendors with procurement activity"
        )
    
    with col3:
        st.metric(
            "Total Value",
            f"₼{overall_hhi.total_value:,.0f}",
            help="Total procurement value"
        )
    
    with col4:
        if overall_hhi.top_vendors:
            top = overall_hhi.top_vendors[0]
            st.metric(
                "Top Vendor Share",
                f"{top[2]:.1f}%",
                help=f"{top[0]}"
            )
    
    st.divider()
    
    # HHI by Segment
    st.subheader("📈 Concentration by Segment")
    
    segments_df = get_all_segments_hhi(conn)
    
    if not segments_df.empty:
        # Color-coded bar chart
        fig = px.bar(
            segments_df,
            x='segment_name',
            y='hhi_value',
            color='concentration_level',
            color_discrete_map={
                'low': '#22c55e',
                'medium': '#eab308',
                'high': '#ef4444'
            },
            labels={
                'segment_name': 'Segment',
                'hhi_value': 'HHI Value',
                'concentration_level': 'Concentration'
            },
            title='HHI by UNSPSC Segment'
        )
        
        # Add threshold lines
        fig.add_hline(y=1500, line_dash="dash", line_color="orange", 
                      annotation_text="Moderate threshold (1,500)")
        fig.add_hline(y=2500, line_dash="dash", line_color="red", 
                      annotation_text="High threshold (2,500)")
        
        fig.update_layout(
            xaxis_tickangle=-45,
            showlegend=True,
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed table
        st.subheader("📋 Segment Details")
        
        # Format the dataframe for display
        display_df = segments_df.copy()
        display_df['Risk'] = display_df['concentration_level'].map({
            'low': '🟢 Low',
            'medium': '🟡 Medium',
            'high': '🔴 High'
        })
        display_df['Total Value'] = display_df['total_value'].apply(lambda x: f"₼{x:,.0f}")
        display_df['Top Vendor Share'] = display_df['top_vendor_share'].apply(lambda x: f"{x:.1f}%")
        display_df['HHI'] = display_df['hhi_value'].apply(lambda x: f"{x:,.0f}")
        
        st.dataframe(
            display_df[['segment_name', 'HHI', 'Risk', 'vendor_count', 'top_vendor', 'Top Vendor Share', 'Total Value']].rename(
                columns={
                    'segment_name': 'Segment',
                    'vendor_count': 'Vendors',
                    'top_vendor': 'Top Vendor'
                }
            ),
            use_container_width=True,
            hide_index=True
        )
    
    st.divider()
    
    # Risk Alerts
    st.subheader("⚠️ Concentration Risk Alerts")
    
    high_risk = segments_df[segments_df['concentration_level'] == 'high'] if not segments_df.empty else pd.DataFrame()
    medium_risk = segments_df[segments_df['concentration_level'] == 'medium'] if not segments_df.empty else pd.DataFrame()
    
    if len(high_risk) > 0:
        for _, row in high_risk.iterrows():
            st.error(f"""
            **🔴 HIGH RISK: {row['segment_name']}**  
            HHI: {row['hhi_value']:,.0f} | Top Vendor: {row['top_vendor']} ({row['top_vendor_share']:.1f}%)  
            *Consider diversifying vendor base for this category.*
            """)
    
    if len(medium_risk) > 0:
        for _, row in medium_risk.iterrows():
            st.warning(f"""
            **🟡 MODERATE RISK: {row['segment_name']}**  
            HHI: {row['hhi_value']:,.0f} | Top Vendor: {row['top_vendor']} ({row['top_vendor_share']:.1f}%)  
            *Monitor for increasing concentration.*
            """)
    
    if len(high_risk) == 0 and len(medium_risk) == 0:
        st.success("✅ No concentration risks detected. All segments are competitive.")
    
    st.divider()
    
    # Vendor Impact Analysis
    st.subheader("🎯 Vendor Impact Analysis")
    
    # Get all vendors
    vendors_query = """
        SELECT DISTINCT v.vendor_name
        FROM vendors v
        JOIN procurement_orders po ON v.vendor_id = po.vendor_id
        ORDER BY v.vendor_name
    """
    vendors_df = pd.read_sql_query(vendors_query, conn)
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        selected_vendor = st.selectbox(
            "Select vendor to analyze:",
            vendors_df['vendor_name'].tolist() if not vendors_df.empty else []
        )
    
    if selected_vendor:
        vendor_share = get_vendor_market_share(conn, selected_vendor)
        current_hhi, simulated_hhi = simulate_hhi_without_vendor(conn, selected_vendor)
        
        with col2:
            st.metric(
                f"Impact of Removing {selected_vendor[:20]}...",
                f"HHI: {current_hhi:,.0f} → {simulated_hhi:,.0f}",
                delta=f"{simulated_hhi - current_hhi:,.0f}",
                delta_color="inverse"
            )
        
        # Vendor details
        st.markdown(f"**Overall Market Share:** {vendor_share['overall_share']:.1f}%")
        st.markdown(f"**Total Contract Value:** ₼{vendor_share['total_value']:,.0f}")
        
        if vendor_share['segments']:
            st.markdown("**Share by Segment:**")
            
            segments_data = pd.DataFrame(vendor_share['segments'])
            
            fig = px.bar(
                segments_data,
                x='segment_name',
                y='share',
                title=f'{selected_vendor} Market Share by Segment',
                labels={'share': 'Market Share (%)', 'segment_name': 'Segment'},
                color='share',
                color_continuous_scale='Blues'
            )
            fig.update_layout(xaxis_tickangle=-45, height=400)
            
            st.plotly_chart(fig, use_container_width=True)
    
    conn.close()


def render_hhi_trends(db_path: str):
    """Render HHI trend analysis."""
    
    conn = sqlite3.connect(db_path)
    
    st.header("📈 HHI Trends Over Time")
    
    # Overall trend
    overall_trend = calculate_hhi_trend(conn, 'overall', 'all')
    
    if not overall_trend.empty:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=overall_trend['month'],
            y=overall_trend['hhi_value'],
            mode='lines+markers',
            name='Overall HHI',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=8)
        ))
        
        # Add threshold zones
        fig.add_hrect(y0=0, y1=1500, fillcolor="green", opacity=0.1, line_width=0)
        fig.add_hrect(y0=1500, y1=2500, fillcolor="yellow", opacity=0.1, line_width=0)
        fig.add_hrect(y0=2500, y1=10000, fillcolor="red", opacity=0.1, line_width=0)
        
        fig.update_layout(
            title='Overall HHI Trend',
            xaxis_title='Month',
            yaxis_title='HHI Value',
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Trend statistics
        if len(overall_trend) > 1:
            first_hhi = overall_trend['hhi_value'].iloc[0]
            last_hhi = overall_trend['hhi_value'].iloc[-1]
            change = last_hhi - first_hhi
            pct_change = (change / first_hhi) * 100 if first_hhi > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Starting HHI", f"{first_hhi:,.0f}")
            
            with col2:
                st.metric("Current HHI", f"{last_hhi:,.0f}")
            
            with col3:
                st.metric(
                    "Change",
                    f"{change:+,.0f}",
                    delta=f"{pct_change:+.1f}%",
                    delta_color="inverse"
                )
    
    # Segment trends
    st.subheader("📊 Segment-Level Trends")
    
    segments_query = """
        SELECT DISTINCT ol.segment_code, c.name as segment_name
        FROM order_lines ol
        LEFT JOIN categories c ON ol.segment_code = c.code
        WHERE ol.segment_code IS NOT NULL
    """
    segments_df = pd.read_sql_query(segments_query, conn)
    
    selected_segment = st.selectbox(
        "Select segment:",
        segments_df['segment_code'].tolist() if not segments_df.empty else [],
        format_func=lambda x: f"{x} - {segments_df[segments_df['segment_code'] == x]['segment_name'].iloc[0]}" if not segments_df.empty else x
    )
    
    if selected_segment:
        segment_trend = calculate_hhi_trend(conn, 'segment', selected_segment)
        
        if not segment_trend.empty:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=segment_trend['month'],
                y=segment_trend['hhi_value'],
                mode='lines+markers',
                name='Segment HHI',
                fill='tozeroy',
                line=dict(color='#8b5cf6', width=2)
            ))
            
            fig.add_hline(y=1500, line_dash="dash", line_color="orange")
            fig.add_hline(y=2500, line_dash="dash", line_color="red")
            
            fig.update_layout(
                title=f'HHI Trend for {selected_segment}',
                xaxis_title='Month',
                yaxis_title='HHI Value',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    conn.close()
