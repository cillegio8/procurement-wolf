"""
Spending Dashboard Component.
Displays procurement spending analysis, trends, and vendor performance.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3


def render_spending_dashboard(db_path: str):
    """Render the main spending dashboard."""
    
    conn = sqlite3.connect(db_path)
    
    st.header("💰 Procurement Spending Dashboard")
    
    # Key metrics
    metrics_query = """
        SELECT 
            COUNT(DISTINCT order_id) as total_orders,
            COUNT(DISTINCT vendor_id) as total_vendors,
            SUM(award_value) as total_spending,
            AVG(award_value) as avg_order_value
        FROM procurement_orders
    """
    metrics = pd.read_sql_query(metrics_query, conn).iloc[0]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Orders", f"{int(metrics['total_orders']):,}")
    
    with col2:
        st.metric("Active Vendors", f"{int(metrics['total_vendors']):,}")
    
    with col3:
        st.metric("Total Spending", f"₼{metrics['total_spending']:,.0f}")
    
    with col4:
        st.metric("Avg Order Value", f"₼{metrics['avg_order_value']:,.0f}")
    
    st.divider()
    
    # Spending by vendor (Top 10)
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top 10 Vendors by Spending")
        
        vendor_spending_query = """
            SELECT v.vendor_name, SUM(po.award_value) as total_spending
            FROM procurement_orders po
            JOIN vendors v ON po.vendor_id = v.vendor_id
            GROUP BY v.vendor_id
            ORDER BY total_spending DESC
            LIMIT 10
        """
        vendor_spending = pd.read_sql_query(vendor_spending_query, conn)
        
        fig = px.bar(
            vendor_spending,
            y='vendor_name',
            x='total_spending',
            orientation='h',
            labels={'vendor_name': '', 'total_spending': 'Total Spending (₼)'},
            color='total_spending',
            color_continuous_scale='Blues'
        )
        fig.update_layout(
            height=400,
            showlegend=False,
            yaxis={'categoryorder': 'total ascending'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 Spending by Category")
        
        category_spending_query = """
            SELECT c.name as category, ol.segment_code,
                   SUM(ol.line_total) as total_spending
            FROM order_lines ol
            LEFT JOIN categories c ON ol.segment_code = c.code
            GROUP BY ol.segment_code
            ORDER BY total_spending DESC
        """
        category_spending = pd.read_sql_query(category_spending_query, conn)
        
        fig = px.pie(
            category_spending,
            values='total_spending',
            names='category',
            title='',
            hole=0.4
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Monthly spending trend
    st.subheader("📈 Monthly Spending Trend")
    
    monthly_query = """
        SELECT 
            strftime('%Y-%m', award_date) as month,
            SUM(award_value) as total_spending,
            COUNT(order_id) as order_count,
            AVG(award_value) as avg_value
        FROM procurement_orders
        GROUP BY month
        ORDER BY month
    """
    monthly_df = pd.read_sql_query(monthly_query, conn)
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Monthly Spending', 'Order Count'),
        specs=[[{"type": "scatter"}, {"type": "bar"}]]
    )
    
    fig.add_trace(
        go.Scatter(
            x=monthly_df['month'],
            y=monthly_df['total_spending'],
            mode='lines+markers',
            name='Spending',
            line=dict(color='#3b82f6', width=2),
            fill='tozeroy'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=monthly_df['month'],
            y=monthly_df['order_count'],
            name='Orders',
            marker_color='#10b981'
        ),
        row=1, col=2
    )
    
    fig.update_layout(height=350, showlegend=False)
    fig.update_xaxes(tickangle=45)
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Estimated vs Actual Analysis
    st.subheader("📉 Budget Variance Analysis")
    
    variance_query = """
        SELECT 
            v.vendor_name,
            SUM(po.estimated_value) as total_estimated,
            SUM(po.award_value) as total_actual,
            SUM(po.award_value) - SUM(po.estimated_value) as variance,
            (SUM(po.award_value) - SUM(po.estimated_value)) * 100.0 / 
                NULLIF(SUM(po.estimated_value), 0) as variance_pct
        FROM procurement_orders po
        JOIN vendors v ON po.vendor_id = v.vendor_id
        GROUP BY v.vendor_id
        HAVING ABS(variance_pct) > 1
        ORDER BY ABS(variance) DESC
        LIMIT 15
    """
    variance_df = pd.read_sql_query(variance_query, conn)
    
    if not variance_df.empty:
        fig = go.Figure()
        
        # Add estimated bars
        fig.add_trace(go.Bar(
            name='Estimated',
            x=variance_df['vendor_name'],
            y=variance_df['total_estimated'],
            marker_color='#94a3b8'
        ))
        
        # Add actual bars
        fig.add_trace(go.Bar(
            name='Actual',
            x=variance_df['vendor_name'],
            y=variance_df['total_actual'],
            marker_color='#3b82f6'
        ))
        
        fig.update_layout(
            barmode='group',
            xaxis_tickangle=-45,
            height=450,
            legend=dict(orientation='h', yanchor='bottom', y=1.02)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Variance table
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔺 Over Budget (Actual > Estimated)**")
            over_budget = variance_df[variance_df['variance'] > 0].head(5)
            if not over_budget.empty:
                over_budget['Variance'] = over_budget['variance'].apply(lambda x: f"+₼{x:,.0f}")
                over_budget['%'] = over_budget['variance_pct'].apply(lambda x: f"+{x:.1f}%")
                st.dataframe(
                    over_budget[['vendor_name', 'Variance', '%']].rename(
                        columns={'vendor_name': 'Vendor'}
                    ),
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No vendors over budget")
        
        with col2:
            st.markdown("**🔻 Under Budget (Actual < Estimated)**")
            under_budget = variance_df[variance_df['variance'] < 0].head(5)
            if not under_budget.empty:
                under_budget['Variance'] = under_budget['variance'].apply(lambda x: f"₼{x:,.0f}")
                under_budget['%'] = under_budget['variance_pct'].apply(lambda x: f"{x:.1f}%")
                st.dataframe(
                    under_budget[['vendor_name', 'Variance', '%']].rename(
                        columns={'vendor_name': 'Vendor'}
                    ),
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No vendors under budget")
    
    conn.close()


def render_vendor_analysis(db_path: str):
    """Render detailed vendor analysis page."""
    
    conn = sqlite3.connect(db_path)
    
    st.header("👥 Vendor Analysis")
    
    # Vendor selector
    vendors_query = """
        SELECT v.vendor_id, v.vendor_name, v.vendor_type, v.city,
               COUNT(po.order_id) as order_count,
               SUM(po.award_value) as total_value
        FROM vendors v
        LEFT JOIN procurement_orders po ON v.vendor_id = po.vendor_id
        GROUP BY v.vendor_id
        ORDER BY total_value DESC
    """
    vendors_df = pd.read_sql_query(vendors_query, conn)
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        vendor_types = ['All'] + vendors_df['vendor_type'].unique().tolist()
        selected_type = st.selectbox("Vendor Type", vendor_types)
    
    with col2:
        cities = ['All'] + vendors_df['city'].dropna().unique().tolist()
        selected_city = st.selectbox("City", cities)
    
    with col3:
        min_orders = st.number_input("Minimum Orders", min_value=0, value=0)
    
    # Apply filters
    filtered_df = vendors_df.copy()
    if selected_type != 'All':
        filtered_df = filtered_df[filtered_df['vendor_type'] == selected_type]
    if selected_city != 'All':
        filtered_df = filtered_df[filtered_df['city'] == selected_city]
    if min_orders > 0:
        filtered_df = filtered_df[filtered_df['order_count'] >= min_orders]
    
    st.divider()
    
    # Vendor overview
    st.subheader(f"📋 Vendors ({len(filtered_df)} total)")
    
    # Distribution by type
    col1, col2 = st.columns(2)
    
    with col1:
        type_dist = filtered_df.groupby('vendor_type').agg({
            'vendor_id': 'count',
            'total_value': 'sum'
        }).reset_index()
        type_dist.columns = ['Type', 'Count', 'Total Value']
        
        fig = px.pie(
            type_dist,
            values='Count',
            names='Type',
            title='Vendors by Type',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        city_dist = filtered_df.groupby('city').size().reset_index(name='count')
        city_dist = city_dist.nlargest(8, 'count')
        
        fig = px.bar(
            city_dist,
            x='city',
            y='count',
            title='Vendors by City (Top 8)',
            labels={'city': 'City', 'count': 'Number of Vendors'},
            color='count',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # Vendor table
    st.subheader("📊 Vendor Details")
    
    display_df = filtered_df.copy()
    display_df['Total Value'] = display_df['total_value'].apply(lambda x: f"₼{x:,.0f}" if pd.notna(x) else "₼0")
    display_df = display_df[['vendor_name', 'vendor_type', 'city', 'order_count', 'Total Value']]
    display_df.columns = ['Vendor Name', 'Type', 'City', 'Orders', 'Total Value']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Single vendor deep dive
    st.divider()
    st.subheader("🔍 Vendor Deep Dive")
    
    selected_vendor = st.selectbox(
        "Select a vendor for detailed analysis:",
        filtered_df['vendor_name'].tolist()
    )
    
    if selected_vendor:
        # Get vendor details
        vendor_orders_query = """
            SELECT po.order_id, po.award_date, po.estimated_value, po.award_value,
                   ol.line_name, ol.line_total, c.name as category
            FROM procurement_orders po
            JOIN vendors v ON po.vendor_id = v.vendor_id
            JOIN order_lines ol ON po.order_id = ol.order_id
            LEFT JOIN categories c ON ol.segment_code = c.code
            WHERE v.vendor_name = ?
            ORDER BY po.award_date DESC
        """
        vendor_orders = pd.read_sql_query(vendor_orders_query, conn, params=[selected_vendor])
        
        if not vendor_orders.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Orders", vendor_orders['order_id'].nunique())
            
            with col2:
                st.metric("Total Value", f"₼{vendor_orders['line_total'].sum():,.0f}")
            
            with col3:
                categories = vendor_orders['category'].nunique()
                st.metric("Categories Served", categories)
            
            # Orders over time
            orders_by_date = vendor_orders.groupby('award_date')['line_total'].sum().reset_index()
            
            fig = px.line(
                orders_by_date,
                x='award_date',
                y='line_total',
                title=f'Order History for {selected_vendor}',
                labels={'award_date': 'Date', 'line_total': 'Order Value (₼)'},
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Category breakdown
            category_breakdown = vendor_orders.groupby('category')['line_total'].sum().reset_index()
            category_breakdown = category_breakdown.sort_values('line_total', ascending=False)
            
            fig = px.bar(
                category_breakdown,
                x='category',
                y='line_total',
                title='Spending by Category',
                labels={'category': 'Category', 'line_total': 'Value (₼)'}
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    
    conn.close()
