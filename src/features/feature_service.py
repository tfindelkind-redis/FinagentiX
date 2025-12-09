"""
Feature Service - Interface to Featureform feature store

Provides high-level API for retrieving pre-computed features
from Redis-backed Featureform store.
"""

from typing import List, Dict, Optional, Any
import redis
import json
from datetime import datetime
from src.agents.config import get_config
from src.features.featureform_config import (
    get_feature_key,
    get_feature_ttl,
    get_all_features,
    get_feature_metadata
)


class FeatureService:
    """Service for accessing Featureform features from Redis."""
    
    def __init__(self):
        """Initialize feature service with Redis client."""
        config = get_config()
        self.redis_client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            password=config.redis.password,
            ssl=config.redis.ssl,
            decode_responses=True
        )
    
    def get_feature(
        self,
        ticker: str,
        feature_name: str,
        default: Any = None
    ) -> Optional[float]:
        """
        Get a single feature value for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            feature_name: Name of the feature (e.g., "sma_20")
            default: Default value if feature not found
            
        Returns:
            Feature value (float) or default if not found
        """
        try:
            key = get_feature_key(ticker, feature_name)
            value = self.redis_client.get(key)
            
            if value is None:
                return default
            
            # Try to parse as float
            try:
                return float(value)
            except (ValueError, TypeError):
                # If it's a JSON object (e.g., MACD with multiple values)
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
                    
        except Exception as e:
            print(f"Error getting feature {feature_name} for {ticker}: {e}")
            return default
    
    def get_features_batch(
        self,
        ticker: str,
        feature_names: List[str]
    ) -> Dict[str, Any]:
        """
        Get multiple features for a ticker in a single call.
        
        Args:
            ticker: Stock ticker symbol
            feature_names: List of feature names
            
        Returns:
            Dict mapping feature names to values
        """
        results = {}
        
        # Note: Cannot use pipeline with Redis Cluster (different hash slots)
        # Use individual GET commands instead
        for feature_name in feature_names:
            try:
                key = get_feature_key(ticker, feature_name)
                value = self.redis_client.get(key)
                
                if value is not None:
                    try:
                        results[feature_name] = float(value)
                    except (ValueError, TypeError):
                        try:
                            results[feature_name] = json.loads(value)
                        except json.JSONDecodeError:
                            results[feature_name] = value
                else:
                    results[feature_name] = None
                    
            except Exception as e:
                print(f"Error getting feature {feature_name} for {ticker}: {e}")
                results[feature_name] = None
        
        return results
    
    def get_all_technical_indicators(self, ticker: str) -> Dict[str, float]:
        """Get all technical indicators for a ticker."""
        from src.features.featureform_config import TECHNICAL_INDICATORS
        feature_names = [f["name"] for f in TECHNICAL_INDICATORS]
        return self.get_features_batch(ticker, feature_names)
    
    def get_all_risk_metrics(self, ticker: str) -> Dict[str, float]:
        """Get all risk metrics for a ticker."""
        from src.features.featureform_config import RISK_METRICS
        feature_names = [f["name"] for f in RISK_METRICS]
        return self.get_features_batch(ticker, feature_names)
    
    def get_all_valuation_metrics(self, ticker: str) -> Dict[str, float]:
        """Get all valuation metrics for a ticker."""
        from src.features.featureform_config import VALUATION_METRICS
        feature_names = [f["name"] for f in VALUATION_METRICS]
        return self.get_features_batch(ticker, feature_names)
    
    def feature_exists(self, ticker: str, feature_name: str) -> bool:
        """
        Check if a feature exists for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            feature_name: Name of the feature
            
        Returns:
            True if feature exists, False otherwise
        """
        try:
            key = get_feature_key(ticker, feature_name)
            return self.redis_client.exists(key) > 0
        except Exception:
            return False
    
    def get_feature_metadata(self, ticker: str, feature_name: str) -> Dict:
        """
        Get metadata about a feature including last updated time.
        
        Args:
            ticker: Stock ticker symbol
            feature_name: Name of the feature
            
        Returns:
            Dict with metadata (value, ttl, last_updated)
        """
        try:
            key = get_feature_key(ticker, feature_name)
            value = self.redis_client.get(key)
            ttl = self.redis_client.ttl(key)
            
            return {
                "ticker": ticker,
                "feature_name": feature_name,
                "value": float(value) if value else None,
                "ttl": ttl if ttl > 0 else None,
                "exists": value is not None,
                "key": key
            }
        except Exception as e:
            return {
                "ticker": ticker,
                "feature_name": feature_name,
                "value": None,
                "ttl": None,
                "exists": False,
                "error": str(e)
            }
    
    def list_available_features(self, ticker: str) -> List[str]:
        """
        List all available features for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            List of feature names that exist for this ticker
        """
        available = []
        all_features = get_all_features()
        
        # Note: Cannot use pipeline with Redis Cluster (different hash slots)
        # Use individual EXISTS commands instead
        for feature_name in all_features:
            try:
                key = get_feature_key(ticker, feature_name)
                if self.redis_client.exists(key):
                    available.append(feature_name)
            except Exception as e:
                continue
        
        return available


# Convenience functions for module-level access
_service = None

def _get_service() -> FeatureService:
    """Get or create singleton feature service."""
    global _service
    if _service is None:
        _service = FeatureService()
    return _service


def get_feature(ticker: str, feature_name: str, default: Any = None) -> Optional[float]:
    """Get a single feature value (module-level convenience function)."""
    return _get_service().get_feature(ticker, feature_name, default)


def get_features_batch(ticker: str, feature_names: List[str]) -> Dict[str, Any]:
    """Get multiple features (module-level convenience function)."""
    return _get_service().get_features_batch(ticker, feature_names)


def feature_exists(ticker: str, feature_name: str) -> bool:
    """Check if feature exists (module-level convenience function)."""
    return _get_service().feature_exists(ticker, feature_name)
