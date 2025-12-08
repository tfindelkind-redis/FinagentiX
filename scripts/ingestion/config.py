"""Configuration for stock data ingestion"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class IngestionConfig:
    """Configuration for stock data ingestion"""
    
    tickers: List[str] = field(default_factory=lambda: [
        # Tech
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
        # Finance
        'JPM', 'BAC', 'WFC', 'GS', 'MS',
        # Consumer
        'WMT', 'HD', 'NKE', 'SBUX', 'MCD',
        # Healthcare
        'JNJ', 'UNH', 'PFE', 'ABBV',
        # Industrial
        'BA', 'CAT', 'GE',
        # Energy
        'XOM', 'CVX',
        # Crypto-related
        'COIN', 'MSTR'
    ])
    
    # Time periods
    period: str = '1y'
    interval: str = '1d'
    
    # Paths
    output_dir: str = 'data/raw/stock_data'
    log_dir: str = 'logs'
    
    # Retry configuration
    max_retries: int = 5
    retry_delays: List[int] = field(default_factory=lambda: [2, 4, 8, 16, 32, 60])
    
    # Rate limiting
    rate_limit_delay: float = 1.0
    
    # Validation thresholds
    validation_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'min_completeness': 0.9,
        'max_null_percent': 0.05,
        'min_records': 200
    })
    
    def __post_init__(self):
        if not self.tickers:
            raise ValueError("Tickers list cannot be empty")


def get_default_config() -> IngestionConfig:
    """Get default ingestion configuration"""
    return IngestionConfig()
