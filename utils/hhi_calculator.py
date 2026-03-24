"""
HHI (Herfindahl-Hirschman Index) calculation utilities.
Provides functions for calculating and analyzing market concentration.
"""

import sqlite3
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class HHIResult:
    """Container for HHI calculation results."""
    hhi_value: float
    concentration_level: str
    vendor_count: int
    total_value: float
    top_vendors: List[Tuple[str, float, float]]  # (name, value, share%)
    
    @property
    def risk_emoji(self) -> str:
        if self.concentration_level == "low":
            return "🟢"
        elif self.concentration_level == "medium":
            return "🟡"
        return "🔴"
    
    @property
    def risk_color(self) -> str:
        if self.concentration_level == "low":
            return "#22c55e"  # green
        elif self.concentration_level == "medium":
            return "#eab308"  # yellow
        return "#ef4444"  # red


def classify_hhi(hhi: float) -> str:
    """Classify HHI value into concentration level."""
    if hhi < 1500:
        return "low"
    elif hhi < 2500:
        return "medium"
    return "high"


def calculate_hhi_from_shares(shares: List[float]) -> float:
    """
    Calculate HHI from a list of market shares.
    Shares should be in percentage form (0-100).
    """
    return sum(s ** 2 for s in shares)


def calculate_hhi_overall(conn: sqlite3.Connection) -> HHIResult:
    """Calculate overall HHI across all procurement."""
    query = """
        SELECT 
            v.vendor_name,
            SUM(po.award_value) as total_value
        FROM procurement_orders po
        JOIN vendors v ON po.vendor_id = v.vendor_id
        GROUP BY v.vendor_id
        ORDER BY total_value DESC
    """
    
    df = pd.read_sql_query(query, conn)
    
    if df.empty:
        return HHIResult(0, "low", 0, 0, [])
    
    total = df['total_value'].sum()
    df['share'] = df['total_value'] * 100 / total
    
    hhi = calculate_hhi_from_shares(df['share'].tolist())
    
    top_vendors = [
        (row['vendor_name'], row['total_value'], row['share'])
        for _, row in df.head(5).iterrows()
    ]
    
    return HHIResult(
        hhi_value=round(hhi, 2),
        concentration_level=classify_hhi(hhi),
        vendor_count=len(df),
        total_value=total,
        top_vendors=top_vendors
    )


def calculate_hhi_by_segment(conn: sqlite3.Connection, segment_code: str) -> HHIResult:
    """Calculate HHI for a specific UNSPSC segment."""
    query = """
        SELECT 
            v.vendor_name,
            SUM(ol.line_total) as total_value
        FROM order_lines ol
        JOIN procurement_orders po ON ol.order_id = po.order_id
        JOIN vendors v ON po.vendor_id = v.vendor_id
        WHERE ol.segment_code = ?
        GROUP BY v.vendor_id
        ORDER BY total_value DESC
    """
    
    df = pd.read_sql_query(query, conn, params=[segment_code])
    
    if df.empty:
        return HHIResult(0, "low", 0, 0, [])
    
    total = df['total_value'].sum()
    df['share'] = df['total_value'] * 100 / total
    
    hhi = calculate_hhi_from_shares(df['share'].tolist())
    
    top_vendors = [
        (row['vendor_name'], row['total_value'], row['share'])
        for _, row in df.head(5).iterrows()
    ]
    
    return HHIResult(
        hhi_value=round(hhi, 2),
        concentration_level=classify_hhi(hhi),
        vendor_count=len(df),
        total_value=total,
        top_vendors=top_vendors
    )


def get_all_segments_hhi(conn: sqlite3.Connection) -> pd.DataFrame:
    """Get HHI for all segments."""
    query = """
        SELECT DISTINCT ol.segment_code, c.name as segment_name
        FROM order_lines ol
        LEFT JOIN categories c ON ol.segment_code = c.code
        WHERE ol.segment_code IS NOT NULL
    """
    
    segments_df = pd.read_sql_query(query, conn)
    
    results = []
    for _, row in segments_df.iterrows():
        hhi_result = calculate_hhi_by_segment(conn, row['segment_code'])
        results.append({
            'segment_code': row['segment_code'],
            'segment_name': row['segment_name'] or row['segment_code'],
            'hhi_value': hhi_result.hhi_value,
            'concentration_level': hhi_result.concentration_level,
            'vendor_count': hhi_result.vendor_count,
            'total_value': hhi_result.total_value,
            'top_vendor': hhi_result.top_vendors[0][0] if hhi_result.top_vendors else "N/A",
            'top_vendor_share': hhi_result.top_vendors[0][2] if hhi_result.top_vendors else 0
        })
    
    return pd.DataFrame(results).sort_values('hhi_value', ascending=False)


def calculate_hhi_trend(conn: sqlite3.Connection, scope_type: str = 'overall', 
                        scope_value: str = 'all', months: int = 12) -> pd.DataFrame:
    """Calculate HHI trend over time (monthly)."""
    
    if scope_type == 'overall':
        query = """
            SELECT 
                strftime('%Y-%m', po.award_date) as month,
                v.vendor_name,
                SUM(po.award_value) as total_value
            FROM procurement_orders po
            JOIN vendors v ON po.vendor_id = v.vendor_id
            GROUP BY month, v.vendor_id
            ORDER BY month
        """
        df = pd.read_sql_query(query, conn)
    else:
        query = """
            SELECT 
                strftime('%Y-%m', po.award_date) as month,
                v.vendor_name,
                SUM(ol.line_total) as total_value
            FROM order_lines ol
            JOIN procurement_orders po ON ol.order_id = po.order_id
            JOIN vendors v ON po.vendor_id = v.vendor_id
            WHERE ol.segment_code = ?
            GROUP BY month, v.vendor_id
            ORDER BY month
        """
        df = pd.read_sql_query(query, conn, params=[scope_value])
    
    if df.empty:
        return pd.DataFrame()
    
    # Calculate HHI for each month
    results = []
    for month in df['month'].unique():
        month_data = df[df['month'] == month]
        total = month_data['total_value'].sum()
        shares = (month_data['total_value'] * 100 / total).tolist()
        hhi = calculate_hhi_from_shares(shares)
        
        results.append({
            'month': month,
            'hhi_value': round(hhi, 2),
            'concentration_level': classify_hhi(hhi),
            'vendor_count': len(month_data),
            'total_value': total
        })
    
    return pd.DataFrame(results)


def get_vendor_market_share(conn: sqlite3.Connection, vendor_name: str) -> Dict:
    """Get detailed market share analysis for a specific vendor."""
    
    # Overall share
    overall_query = """
        SELECT 
            SUM(CASE WHEN v.vendor_name = ? THEN po.award_value ELSE 0 END) as vendor_total,
            SUM(po.award_value) as market_total
        FROM procurement_orders po
        JOIN vendors v ON po.vendor_id = v.vendor_id
    """
    
    df = pd.read_sql_query(overall_query, conn, params=[vendor_name])
    overall_share = df['vendor_total'].iloc[0] * 100 / df['market_total'].iloc[0] if df['market_total'].iloc[0] > 0 else 0
    
    # Share by segment
    segment_query = """
        SELECT 
            ol.segment_code,
            c.name as segment_name,
            SUM(CASE WHEN v.vendor_name = ? THEN ol.line_total ELSE 0 END) as vendor_total,
            SUM(ol.line_total) as segment_total
        FROM order_lines ol
        JOIN procurement_orders po ON ol.order_id = po.order_id
        JOIN vendors v ON po.vendor_id = v.vendor_id
        LEFT JOIN categories c ON ol.segment_code = c.code
        GROUP BY ol.segment_code
        HAVING vendor_total > 0
        ORDER BY vendor_total DESC
    """
    
    segments_df = pd.read_sql_query(segment_query, conn, params=[vendor_name])
    segments_df['share'] = segments_df['vendor_total'] * 100 / segments_df['segment_total']
    
    return {
        'vendor_name': vendor_name,
        'overall_share': round(overall_share, 2),
        'total_value': df['vendor_total'].iloc[0],
        'segments': segments_df.to_dict('records')
    }


def simulate_hhi_without_vendor(conn: sqlite3.Connection, vendor_name: str, 
                                 segment_code: Optional[str] = None) -> Tuple[float, float]:
    """
    Simulate what HHI would be without a specific vendor.
    Returns (current_hhi, simulated_hhi).
    """
    
    if segment_code:
        query = """
            SELECT 
                v.vendor_name,
                SUM(ol.line_total) as total_value
            FROM order_lines ol
            JOIN procurement_orders po ON ol.order_id = po.order_id
            JOIN vendors v ON po.vendor_id = v.vendor_id
            WHERE ol.segment_code = ?
            GROUP BY v.vendor_id
        """
        df = pd.read_sql_query(query, conn, params=[segment_code])
    else:
        query = """
            SELECT 
                v.vendor_name,
                SUM(po.award_value) as total_value
            FROM procurement_orders po
            JOIN vendors v ON po.vendor_id = v.vendor_id
            GROUP BY v.vendor_id
        """
        df = pd.read_sql_query(query, conn)
    
    if df.empty:
        return 0, 0
    
    # Current HHI
    total = df['total_value'].sum()
    shares = (df['total_value'] * 100 / total).tolist()
    current_hhi = calculate_hhi_from_shares(shares)
    
    # Simulated HHI without vendor
    df_without = df[df['vendor_name'] != vendor_name]
    if df_without.empty:
        return round(current_hhi, 2), 0
    
    total_without = df_without['total_value'].sum()
    shares_without = (df_without['total_value'] * 100 / total_without).tolist()
    simulated_hhi = calculate_hhi_from_shares(shares_without)
    
    return round(current_hhi, 2), round(simulated_hhi, 2)
