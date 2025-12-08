"""Data validation for stock market data"""
import pandas as pd
import hashlib
from typing import Dict, Tuple, List
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    record_count: int
    completeness_score: float
    null_percentage: float
    date_range: Tuple[str, str]
    issues: List[str]
    checksum: str

class DataValidator:
    """Validate downloaded stock data"""
    
    def __init__(self, min_records: int, max_null_pct: float, 
                 min_completeness: float):
        self.min_records = min_records
        self.max_null_pct = max_null_pct
        self.min_completeness = min_completeness
    
    def validate(self, df: pd.DataFrame, ticker: str) -> ValidationResult:
        """Comprehensive validation of stock data"""
        issues = []
        
        # Handle MultiIndex columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df = df.droplevel(1, axis=1) if df.columns.nlevels > 1 else df
        
        # 1. Check record count
        record_count = len(df)
        if record_count < self.min_records:
            issues.append(
                f"Insufficient records: {record_count} < {self.min_records}"
            )
        
        # 2. Check for required columns
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            issues.append(f"Missing columns: {missing_cols}")
            # Cannot continue validation without required columns
            return ValidationResult(
                is_valid=False,
                record_count=record_count,
                completeness_score=0.0,
                null_percentage=100.0,
                date_range=('', ''),
                issues=issues,
                checksum=''
            )
        
        # 3. Check for nulls
        total_cells = len(df) * len(required_cols)
        null_cells = df[required_cols].isnull().sum().sum()
        null_percentage = (null_cells / total_cells) * 100 if total_cells > 0 else 0
        
        if null_percentage > self.max_null_pct * 100:
            issues.append(
                f"Too many nulls: {null_percentage:.2f}% > "
                f"{self.max_null_pct * 100}%"
            )
        
        # 4. Check data quality
        completeness_score = self._calculate_completeness(df)
        if completeness_score < self.min_completeness:
            issues.append(
                f"Low completeness: {completeness_score:.2f} < "
                f"{self.min_completeness}"
            )
        
        # 5. Check date range
        if len(df) > 0:
            date_range = (
                df.index[0].strftime('%Y-%m-%d'),
                df.index[-1].strftime('%Y-%m-%d')
            )
        else:
            date_range = ('', '')
            issues.append("Empty dataframe")
        
        # 6. Validate OHLC relationships
        ohlc_issues = self._validate_ohlc(df)
        issues.extend(ohlc_issues)
        
        # 7. Check for extreme values (potential data errors)
        extreme_issues = self._check_extreme_values(df, ticker)
        issues.extend(extreme_issues)
        
        # 8. Calculate checksum
        checksum = self._calculate_checksum(df)
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            record_count=record_count,
            completeness_score=completeness_score,
            null_percentage=null_percentage,
            date_range=date_range,
            issues=issues,
            checksum=checksum
        )
    
    def _calculate_completeness(self, df: pd.DataFrame) -> float:
        """Calculate data completeness score (0-1)"""
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        total_cells = len(df) * len(required_cols)
        if total_cells == 0:
            return 0.0
        valid_cells = df[required_cols].notna().sum().sum()
        return valid_cells / total_cells
    
    def _validate_ohlc(self, df: pd.DataFrame) -> List[str]:
        """Validate OHLC price relationships"""
        issues = []
        
        if len(df) == 0:
            return issues
        
        # High should be >= Low
        high_low_check = df['High'] < df['Low']
        if high_low_check.any():
            invalid_count = high_low_check.sum()
            issues.append(f"{invalid_count} rows where High < Low")
        
        # High should be >= Open and Close
        high_open_check = df['High'] < df['Open']
        high_close_check = df['High'] < df['Close']
        if high_open_check.any() or high_close_check.any():
            issues.append("High < Open or Close in some rows")
        
        # Low should be <= Open and Close
        low_open_check = df['Low'] > df['Open']
        low_close_check = df['Low'] > df['Close']
        if low_open_check.any() or low_close_check.any():
            issues.append("Low > Open or Close in some rows")
        
        return issues
    
    def _check_extreme_values(self, df: pd.DataFrame, ticker: str) -> List[str]:
        """Check for extreme/suspicious values"""
        issues = []
        
        if len(df) == 0:
            return issues
        
        # Check for zero or negative prices
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            if (df[col] <= 0).any():
                issues.append(f"Zero or negative values in {col}")
        
        # Check for extreme price changes (>50% in one day)
        df_copy = df.copy()
        df_copy['price_change'] = df_copy['Close'].pct_change()
        extreme_changes = df_copy[abs(df_copy['price_change']) > 0.5]
        if len(extreme_changes) > 0:
            issues.append(
                f"Warning: {len(extreme_changes)} days with >50% price change"
            )
        
        return issues
    
    def _calculate_checksum(self, df: pd.DataFrame) -> str:
        """Calculate MD5 checksum of data"""
        data_str = df.to_csv(index=True)
        return hashlib.md5(data_str.encode()).hexdigest()
