"""
Vanna AI integration for natural language to SQL conversion.
This module provides text-to-SQL capabilities for the procurement database.
"""

import os
import sqlite3
from typing import Optional, Tuple, List, Dict, Any
import pandas as pd

# Try to import vanna, provide fallback if not available
try:
    from vanna.openai import OpenAI_Chat
    from vanna.chromadb import ChromaDB_VectorStore
    VANNA_AVAILABLE = True
except ImportError:
    VANNA_AVAILABLE = False


class ProcurementVanna:
    """
    Vanna AI wrapper for procurement database queries.
    Falls back to pattern matching if Vanna is not available.
    """
    
    def __init__(self, db_path: str, api_key: Optional[str] = None):
        self.db_path = db_path
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.vanna = None
        self.is_trained = False
        
        # Initialize Vanna if available and API key is provided
        if VANNA_AVAILABLE and self.api_key:
            self._init_vanna()
        
        # Pattern-based fallback queries
        self._init_patterns()
    
    def _init_vanna(self):
        """Initialize Vanna with OpenAI and ChromaDB."""
        try:
            class MyVanna(ChromaDB_VectorStore, OpenAI_Chat):
                def __init__(self, config=None):
                    ChromaDB_VectorStore.__init__(self, config=config)
                    OpenAI_Chat.__init__(self, config=config)
            
            self.vanna = MyVanna(config={
                'api_key': self.api_key,
                'model': 'gpt-4o-mini'
            })
            
            # Connect to SQLite database
            self.vanna.connect_to_sqlite(self.db_path)
            
        except Exception as e:
            print(f"Warning: Could not initialize Vanna: {e}")
            self.vanna = None
    
    def _init_patterns(self):
        """Initialize pattern-based query templates."""
        self.patterns = {
            # Spending queries
            "total spending": """
                SELECT SUM(award_value) as total_spending 
                FROM procurement_orders
            """,
            "spending by vendor": """
                SELECT v.vendor_name, SUM(po.award_value) as total_spending
                FROM procurement_orders po
                JOIN vendors v ON po.vendor_id = v.vendor_id
                GROUP BY v.vendor_id
                ORDER BY total_spending DESC
            """,
            "top vendors": """
                SELECT v.vendor_name, SUM(po.award_value) as total_spending,
                       COUNT(po.order_id) as order_count
                FROM procurement_orders po
                JOIN vendors v ON po.vendor_id = v.vendor_id
                GROUP BY v.vendor_id
                ORDER BY total_spending DESC
                LIMIT 10
            """,
            "spending by category": """
                SELECT c.name as category, ol.segment_code,
                       SUM(ol.line_total) as total_spending
                FROM order_lines ol
                LEFT JOIN categories c ON ol.segment_code = c.code
                GROUP BY ol.segment_code
                ORDER BY total_spending DESC
            """,
            "spending by month": """
                SELECT strftime('%Y-%m', award_date) as month,
                       SUM(award_value) as total_spending,
                       COUNT(order_id) as order_count
                FROM procurement_orders
                GROUP BY month
                ORDER BY month
            """,
            
            # HHI queries
            "hhi": """
                SELECT scope_type, scope_value, hhi_value, 
                       concentration_level, top_vendor_name, top_vendor_share
                FROM hhi_snapshots
                ORDER BY hhi_value DESC
            """,
            "concentration": """
                SELECT scope_value as segment, hhi_value, concentration_level,
                       top_vendor_name, top_vendor_share, vendor_count
                FROM hhi_snapshots
                WHERE scope_type = 'segment'
                ORDER BY hhi_value DESC
            """,
            "high concentration": """
                SELECT scope_value as segment, hhi_value, concentration_level,
                       top_vendor_name, top_vendor_share
                FROM hhi_snapshots
                WHERE concentration_level = 'high'
                ORDER BY hhi_value DESC
            """,
            
            # Variance queries
            "variance": """
                SELECT v.vendor_name,
                       SUM(po.estimated_value) as total_estimated,
                       SUM(po.award_value) as total_actual,
                       SUM(po.award_value) - SUM(po.estimated_value) as variance,
                       (SUM(po.award_value) - SUM(po.estimated_value)) * 100.0 / 
                            NULLIF(SUM(po.estimated_value), 0) as variance_pct
                FROM procurement_orders po
                JOIN vendors v ON po.vendor_id = v.vendor_id
                GROUP BY v.vendor_id
                ORDER BY ABS(variance) DESC
            """,
            "estimated vs actual": """
                SELECT v.vendor_name,
                       po.estimated_value,
                       po.award_value,
                       po.award_value - po.estimated_value as difference
                FROM procurement_orders po
                JOIN vendors v ON po.vendor_id = v.vendor_id
                ORDER BY ABS(difference) DESC
                LIMIT 20
            """,
            
            # Vendor queries
            "all vendors": """
                SELECT vendor_name, vendor_type, city, primary_segment
                FROM vendors
                ORDER BY vendor_name
            """,
            "vendor count": """
                SELECT COUNT(*) as vendor_count FROM vendors
            """,
            "vendors by type": """
                SELECT vendor_type, COUNT(*) as count
                FROM vendors
                GROUP BY vendor_type
            """,
            "vendors by city": """
                SELECT city, COUNT(*) as vendor_count
                FROM vendors
                GROUP BY city
                ORDER BY vendor_count DESC
            """,
            
            # Order queries
            "recent orders": """
                SELECT po.order_id, v.vendor_name, po.award_value, po.award_date
                FROM procurement_orders po
                JOIN vendors v ON po.vendor_id = v.vendor_id
                ORDER BY po.award_date DESC
                LIMIT 20
            """,
            "largest orders": """
                SELECT po.order_id, v.vendor_name, po.award_value, po.award_date
                FROM procurement_orders po
                JOIN vendors v ON po.vendor_id = v.vendor_id
                ORDER BY po.award_value DESC
                LIMIT 20
            """,
            "order count": """
                SELECT COUNT(*) as total_orders FROM procurement_orders
            """,
            
            # Category/segment queries
            "categories": """
                SELECT code, level, name
                FROM categories
                ORDER BY level, code
            """,
            "spending by segment": """
                SELECT c.name as segment_name, ol.segment_code,
                       SUM(ol.line_total) as total_value,
                       COUNT(DISTINCT ol.order_id) as order_count
                FROM order_lines ol
                LEFT JOIN categories c ON ol.segment_code = c.code
                GROUP BY ol.segment_code
                ORDER BY total_value DESC
            """
        }
    
    def train(self):
        """Train Vanna on the procurement database schema."""
        if not self.vanna:
            return False
        
        try:
            # Add DDL statements
            ddl_statements = [
                """
                CREATE TABLE vendors (
                    vendor_id INTEGER PRIMARY KEY,
                    vendor_name TEXT NOT NULL,
                    vendor_type TEXT NOT NULL,  -- SME, Large, State
                    registration_date DATE,
                    primary_segment TEXT,  -- UNSPSC segment code
                    city TEXT
                )
                """,
                """
                CREATE TABLE procurement_orders (
                    order_id INTEGER PRIMARY KEY,
                    vendor_id INTEGER REFERENCES vendors(vendor_id),
                    estimated_value REAL,  -- Pre-award estimate
                    award_value REAL,  -- Actual contract value
                    award_date DATETIME
                )
                """,
                """
                CREATE TABLE order_lines (
                    line_id INTEGER PRIMARY KEY,
                    order_id INTEGER REFERENCES procurement_orders(order_id),
                    unspsc_code TEXT,  -- Product classification code
                    line_name TEXT,  -- Item description
                    line_description TEXT,  -- Location or details
                    unit_price REAL,
                    quantity REAL,
                    line_total REAL,
                    segment_code TEXT,  -- UNSPSC segment (first 8 digits)
                    family_code TEXT,  -- UNSPSC family
                    class_code TEXT  -- UNSPSC class
                )
                """,
                """
                CREATE TABLE hhi_snapshots (
                    snapshot_id INTEGER PRIMARY KEY,
                    calculation_date DATE,
                    scope_type TEXT,  -- 'overall' or 'segment'
                    scope_value TEXT,  -- 'all' or segment code
                    hhi_value REAL,  -- Herfindahl-Hirschman Index
                    top_vendor_share REAL,  -- Market share of top vendor (%)
                    top_vendor_name TEXT,
                    vendor_count INTEGER,
                    total_value REAL,
                    concentration_level TEXT  -- 'low', 'medium', 'high'
                )
                """
            ]
            
            for ddl in ddl_statements:
                self.vanna.train(ddl=ddl)
            
            # Add documentation
            documentation = [
                "HHI (Herfindahl-Hirschman Index) measures market concentration. Below 1500 is competitive (low), 1500-2500 is moderate (medium), above 2500 is concentrated (high).",
                "UNSPSC codes are hierarchical product classifications. Segments are the top level (76000000), families are second level (76120000), classes are third level (76122300).",
                "Vendor types include SME (Small and Medium Enterprise), Large (large corporations), and State (government-owned entities).",
                "The variance between estimated_value and award_value shows how accurate procurement estimates are.",
                "Use orders_view for queries that need combined order and line item data."
            ]
            
            for doc in documentation:
                self.vanna.train(documentation=doc)
            
            # Add example queries
            example_queries = [
                ("What is the total spending by vendor?", 
                 "SELECT v.vendor_name, SUM(po.award_value) FROM procurement_orders po JOIN vendors v ON po.vendor_id = v.vendor_id GROUP BY v.vendor_id ORDER BY 2 DESC"),
                ("Show HHI concentration by segment",
                 "SELECT scope_value, hhi_value, concentration_level FROM hhi_snapshots WHERE scope_type = 'segment' ORDER BY hhi_value DESC"),
                ("Which vendors have high market concentration?",
                 "SELECT top_vendor_name, scope_value, hhi_value, top_vendor_share FROM hhi_snapshots WHERE concentration_level = 'high'"),
                ("Compare estimated vs actual values",
                 "SELECT v.vendor_name, SUM(po.estimated_value) as estimated, SUM(po.award_value) as actual, SUM(po.award_value) - SUM(po.estimated_value) as variance FROM procurement_orders po JOIN vendors v ON po.vendor_id = v.vendor_id GROUP BY v.vendor_id")
            ]
            
            for question, sql in example_queries:
                self.vanna.train(question=question, sql=sql)
            
            self.is_trained = True
            return True
            
        except Exception as e:
            print(f"Training error: {e}")
            return False
    
    def _match_pattern(self, question: str) -> Optional[str]:
        """Match question to a pattern-based query."""
        question_lower = question.lower()
        
        # Check each pattern
        for pattern, sql in self.patterns.items():
            keywords = pattern.split()
            if all(kw in question_lower for kw in keywords):
                return sql
        
        # Default fallback
        return None
    
    def ask(self, question: str) -> Tuple[str, pd.DataFrame, Optional[str]]:
        """
        Convert natural language question to SQL and execute.
        
        Returns:
            Tuple of (sql_query, results_dataframe, error_message)
        """
        sql = None
        error = None
        
        # Try Vanna first if available and trained
        if self.vanna and self.is_trained:
            try:
                sql = self.vanna.generate_sql(question)
            except Exception as e:
                error = f"Vanna error: {e}"
        
        # Fall back to pattern matching
        if not sql:
            sql = self._match_pattern(question)
        
        if not sql:
            # Ultimate fallback - try to understand the intent
            if any(word in question.lower() for word in ['vendor', 'supplier']):
                sql = self.patterns["spending by vendor"]
            elif 'hhi' in question.lower() or 'concentration' in question.lower():
                sql = self.patterns["concentration"]
            elif 'spend' in question.lower() or 'value' in question.lower():
                sql = self.patterns["spending by category"]
            else:
                return "", pd.DataFrame(), "Could not understand the question. Try asking about vendors, spending, HHI, or concentration."
        
        # Execute the query
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(sql, conn)
            conn.close()
            return sql, df, None
        except Exception as e:
            return sql, pd.DataFrame(), f"Query execution error: {e}"
    
    def get_suggested_questions(self) -> List[str]:
        """Return list of suggested questions for the user."""
        return [
            "What is the total spending by vendor?",
            "Show me the top 10 vendors by award value",
            "Which categories have high concentration risk?",
            "What is the HHI for each segment?",
            "Compare estimated vs actual award values",
            "Show spending by month",
            "Which vendors are based in Baku?",
            "What are the largest orders?",
            "Show me the spending by category",
            "How many vendors are there by type?"
        ]


# Simple query executor for when Vanna is not configured
class SimpleQueryExecutor:
    """Direct SQL query executor without NL processing."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def execute(self, sql: str) -> Tuple[pd.DataFrame, Optional[str]]:
        """Execute SQL query and return results."""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(sql, conn)
            conn.close()
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)
    
    def get_schema(self) -> str:
        """Get database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        schema = []
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            col_defs = [f"  {col[1]} {col[2]}" for col in columns]
            schema.append(f"{table_name}:\n" + "\n".join(col_defs))
        
        conn.close()
        return "\n\n".join(schema)
