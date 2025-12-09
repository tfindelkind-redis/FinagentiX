"""
Featureform Feature Definitions for FinagentiX

Defines all features, transformations, and training sets.
This file is applied to Featureform server using: featureform apply definitions.py
"""

import featureform as ff
import os
from typing import List

# ============================================================================
# PROVIDERS - Register Azure Redis and data sources
# ============================================================================

# Register Azure Redis Enterprise as online store (feature serving)
redis = ff.register_redis(
    name="azure-redis",
    description="Azure Redis Enterprise for online feature serving",
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT", 10000)),
    password=os.getenv("REDIS_PASSWORD"),
    db=0
)

# Register Redis as offline store (using Redis as both offline and online)
# In production, you might use Azure SQL or Synapse for offline store
redis_offline = ff.register_redis(
    name="azure-redis-offline",
    description="Azure Redis Enterprise for offline feature computation",
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT", 10000)),
    password=os.getenv("REDIS_PASSWORD"),
    db=1  # Different database for offline
)

# ============================================================================
# SOURCES - Register existing data in Redis TimeSeries
# ============================================================================

# Register stock price data source (Redis TimeSeries)
@redis_offline.sql_transformation()
def stock_prices():
    """
    Stock price data from Redis TimeSeries.
    This is a placeholder - actual implementation will query TimeSeries directly.
    """
    return """
    SELECT 
        ticker as entity_id,
        timestamp,
        close_price,
        volume,
        open_price,
        high_price,
        low_price
    FROM stock_timeseries
    """

# ============================================================================
# ENTITIES - Define entity types
# ============================================================================

@ff.entity
class Stock:
    """Stock ticker entity"""
    pass

# ============================================================================
# FEATURES - Technical Indicators
# ============================================================================

@redis_offline.sql_transformation()
def sma_20_transformation():
    """Calculate 20-day Simple Moving Average"""
    return """
    SELECT 
        ticker as entity_id,
        timestamp,
        AVG(close_price) OVER (
            PARTITION BY ticker 
            ORDER BY timestamp 
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) as sma_20
    FROM stock_timeseries
    """

@redis_offline.sql_transformation()
def sma_50_transformation():
    """Calculate 50-day Simple Moving Average"""
    return """
    SELECT 
        ticker as entity_id,
        timestamp,
        AVG(close_price) OVER (
            PARTITION BY ticker 
            ORDER BY timestamp 
            ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
        ) as sma_50
    FROM stock_timeseries
    """

@redis_offline.sql_transformation()
def sma_200_transformation():
    """Calculate 200-day Simple Moving Average"""
    return """
    SELECT 
        ticker as entity_id,
        timestamp,
        AVG(close_price) OVER (
            PARTITION BY ticker 
            ORDER BY timestamp 
            ROWS BETWEEN 199 PRECEDING AND CURRENT ROW
        ) as sma_200
    FROM stock_timeseries
    """

# Register features on Stock entity
@ff.entity
class Stock:
    # Technical Indicators
    sma_20 = ff.Feature(
        sma_20_transformation[["entity_id", "sma_20", "timestamp"]],
        type=ff.Float32,
        inference_store=redis,
        description="20-day Simple Moving Average"
    )
    
    sma_50 = ff.Feature(
        sma_50_transformation[["entity_id", "sma_50", "timestamp"]],
        type=ff.Float32,
        inference_store=redis,
        description="50-day Simple Moving Average"
    )
    
    sma_200 = ff.Feature(
        sma_200_transformation[["entity_id", "sma_200", "timestamp"]],
        type=ff.Float32,
        inference_store=redis,
        description="200-day Simple Moving Average"
    )

# ============================================================================
# FEATURES - Risk Metrics (computed via Python transformations)
# ============================================================================

@redis_offline.df_transformation(
    inputs=[("stock_prices", "default")],
    variant="default"
)
def volatility_30d(stock_prices):
    """Calculate 30-day annualized volatility"""
    import pandas as pd
    import numpy as np
    
    stock_prices = stock_prices.sort_values(['entity_id', 'timestamp'])
    stock_prices['returns'] = stock_prices.groupby('entity_id')['close_price'].pct_change()
    
    volatility = stock_prices.groupby('entity_id')['returns'].apply(
        lambda x: x.rolling(window=30).std() * np.sqrt(252)
    ).reset_index()
    
    return volatility[['entity_id', 'returns']].rename(columns={'returns': 'volatility_30d'})

@ff.entity
class Stock:
    volatility_30d = ff.Feature(
        volatility_30d[["entity_id", "volatility_30d"]],
        type=ff.Float32,
        inference_store=redis,
        description="30-day annualized volatility"
    )

# ============================================================================
# TRAINING SETS - For ML model training
# ============================================================================

# Example: Training set for price prediction model
ff.register_training_set(
    name="price_prediction",
    description="Training set for stock price prediction model",
    label=("close_price", "default"),
    features=[
        ("sma_20", "default"),
        ("sma_50", "default"),
        ("sma_200", "default"),
        ("volatility_30d", "default")
    ]
)

# ============================================================================
# FEATURE SETS - Grouped features for agent queries
# ============================================================================

# Technical indicators feature set
technical_indicators = [
    ("sma_20", "default"),
    ("sma_50", "default"),
    ("sma_200", "default")
]

# Risk metrics feature set
risk_metrics = [
    ("volatility_30d", "default")
]
