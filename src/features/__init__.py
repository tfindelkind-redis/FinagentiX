"""
Feature Store Module

Redis-backed feature store for pre-computed technical indicators,
risk metrics, and valuation ratios.

This implements a feature store pattern similar to Featureform but
using Redis directly for Python 3.13 compatibility.
"""

from src.features.featureform_config import (
    get_all_features,
    get_feature_metadata,
    get_feature_key,
    get_feature_ttl,
    TECHNICAL_INDICATORS,
    RISK_METRICS,
    VALUATION_METRICS
)

from src.features.feature_service import (
    FeatureService,
    get_feature,
    get_features_batch,
    feature_exists
)

__all__ = [
    # Configuration
    "get_all_features",
    "get_feature_metadata",
    "get_feature_key",
    "get_feature_ttl",
    "TECHNICAL_INDICATORS",
    "RISK_METRICS",
    "VALUATION_METRICS",
    
    # Service
    "FeatureService",
    "get_feature",
    "get_features_batch",
    "feature_exists"
]
