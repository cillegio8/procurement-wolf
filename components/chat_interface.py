"""
Chat interface component for natural language queries.
"""

import streamlit as st
import pandas as pd
from typing import Optional
import sqlite3


def render_chat_interface(vanna_instance, db_path: str):
    """Render the chat interface for NL queries."""
    
    st.header("💬 Ask Questions in Natural Language")
    
    # Instructions
    with st.expander("ℹ️ How to use", expanded=False):
        st.markdown("""
        Ask questions about procurement data in plain English (or Azerbaijani). Examples:
        
        - "What is the total spending by vendor?"
        - "Show me the HHI concentration by segment"
        - "Which categories have high concentration risk?"
        - "Compare estimated vs actual award values"
        - "Top 10 vendors by order count"
        """)
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sql" in message:
                with st.expander("View SQL"):
                    st.code(message["sql"], language="sql")
            if "dataframe" in message and message["dataframe"] is not None:
                st.dataframe(message["dataframe"], use_container_width=True)
    
    # Suggested questions
    if not st.session_state.messages:
        st.subheader("🎯 Suggested Questions")
        suggested = vanna_instance.get_suggested_questions()
        
        cols = st.columns(2)
        for i, question in enumerate(suggested[:6]):
            with cols[i % 2]:
                if st.button(question, key=f"suggest_{i}", use_container_width=True):
                    process_question(question, vanna_instance)
                    st.rerun()
    
    # Chat input
    if prompt := st.chat_input("Ask a question about procurement data..."):
        process_question(prompt, vanna_instance)
        st.rerun()


def process_question(question: str, vanna_instance):
    """Process a user question and generate response."""
    
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })
    
    # Generate SQL and execute
    sql, df, error = vanna_instance.ask(question)
    
    if error:
        response = f"❌ {error}"
        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })
    else:
        # Generate natural language response
        response = generate_response(question, df)
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": response,
            "sql": sql,
            "dataframe": df
        })


def generate_response(question: str, df: pd.DataFrame) -> str:
    """Generate a natural language response based on query results."""
    
    if df.empty:
        return "No results found for your query."
    
    question_lower = question.lower()
    
    # Total spending
    if 'total' in question_lower and 'spend' in question_lower:
        if 'vendor' in question_lower:
            # Safely access vendor spending data
            if len(df) > 0 and len(df.columns) >= 2:
                top_vendor = df.iloc[0]
                vendor_name = top_vendor.iloc[0]
                vendor_spend = top_vendor.iloc[1]
                return f"📊 Found {len(df)} vendors. Top spender: **{vendor_name}** with **₼{vendor_spend:,.2f}**"
            else:
                return f"📊 Found {len(df)} vendors. Top spender details unavailable."
        else:
            if len(df) > 0 and len(df.columns) > 0:
                total = df.iloc[0, 0]
                return f"💰 Total spending: **₼{total:,.2f}**"
            else:
                return "💰 Unable to calculate total spending from query results."
    
    # HHI / Concentration
    if 'hhi' in question_lower or 'concentration' in question_lower:
        high_conc = pd.DataFrame()
        if 'concentration_level' in df.columns:
            high_conc = df[df['concentration_level'] == 'high']
        elif 'concentration' in df.columns:
            high_conc = df[df['concentration'] == 'high']
        
        if len(high_conc) > 0:
            return f"⚠️ Found **{len(high_conc)}** segments with high concentration (HHI > 2500). Review recommended."
        else:
            return f"📊 Analyzed {len(df)} segments. Concentration levels vary - see details below."
    
    # Vendor queries
    if 'vendor' in question_lower:
        return f"👥 Found **{len(df)}** vendors matching your criteria."
    
    # Order queries
    if 'order' in question_lower:
        return f"📋 Found **{len(df)}** orders matching your criteria."
    
    # Default response
    return f"✅ Query returned **{len(df)}** results."


def render_sql_playground(db_path: str):
    """Render a SQL playground for direct queries."""
    
    st.header("🔧 SQL Playground")
    
    # Show schema
    with st.expander("📋 Database Schema"):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            st.markdown(f"**{table_name}**")
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            col_data = pd.DataFrame(columns, columns=['cid', 'name', 'type', 'notnull', 'default', 'pk'])
            st.dataframe(col_data[['name', 'type', 'pk']], use_container_width=True, hide_index=True)
        
        conn.close()
    
    # SQL input
    sql_query = st.text_area(
        "Enter SQL query:",
        height=150,
        placeholder="SELECT * FROM vendors LIMIT 10"
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        execute = st.button("▶️ Execute", type="primary")
    
    if execute and sql_query:
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query(sql_query, conn)
            conn.close()
            
            st.success(f"Query returned {len(df)} rows")
            st.dataframe(df, use_container_width=True)
            
            # Download option
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Download CSV",
                csv,
                "query_results.csv",
                "text/csv"
            )
            
        except Exception as e:
            st.error(f"Query error: {e}")
