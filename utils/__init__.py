# Utils package
from .hhi_calculator import (
    HHIResult,
    calculate_hhi_overall,
    calculate_hhi_by_segment,
    get_all_segments_hhi,
    calculate_hhi_trend,
    get_vendor_market_share,
    simulate_hhi_without_vendor,
    classify_hhi
)
from .vanna_integration import ProcurementVanna, SimpleQueryExecutor
