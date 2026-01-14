#!/bin/bash
set -e

# Upload local data to Azure Storage
# This script uploads SEC filings, news articles, and stock data from the local data/ directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-rg-finagentix-dev}"

echo "=========================================="
echo "📤 FinagentiX - Data Upload"
echo "=========================================="

# Get storage account name
STORAGE_ACCOUNT=$(az storage account list -g "$AZURE_RESOURCE_GROUP" --query "[0].name" -o tsv 2>/dev/null)

if [ -z "$STORAGE_ACCOUNT" ]; then
    echo "❌ No storage account found in resource group $AZURE_RESOURCE_GROUP"
    exit 1
fi

echo "📦 Storage Account: $STORAGE_ACCOUNT"

# Get storage key
STORAGE_KEY=$(az storage account keys list -g "$AZURE_RESOURCE_GROUP" -n "$STORAGE_ACCOUNT" --query "[0].value" -o tsv)

# Check if local data exists
DATA_DIR="$PROJECT_ROOT/data/raw"
if [ ! -d "$DATA_DIR" ]; then
    echo "❌ Data directory not found: $DATA_DIR"
    echo "   Please ensure the data/raw directory exists with SEC filings and news data"
    exit 1
fi

# Create containers if they don't exist
echo ""
echo "📁 Creating storage containers..."
for container in "sec-filings" "news-articles" "stock-data"; do
    az storage container create \
        --name "$container" \
        --account-name "$STORAGE_ACCOUNT" \
        --account-key "$STORAGE_KEY" \
        --fail-on-exist 2>/dev/null || true
done

# Upload SEC filings
if [ -d "$DATA_DIR/sec_filings" ]; then
    echo ""
    echo "📄 Uploading SEC filings..."
    
    total_files=$(find "$DATA_DIR/sec_filings" -type f | wc -l | tr -d ' ')
    uploaded=0
    
    for ticker_dir in "$DATA_DIR/sec_filings"/*/; do
        if [ -d "$ticker_dir" ]; then
            ticker=$(basename "$ticker_dir")
            
            # Upload all files for this ticker
            az storage blob upload-batch \
                --destination "sec-filings" \
                --source "$ticker_dir" \
                --destination-path "$ticker" \
                --account-name "$STORAGE_ACCOUNT" \
                --account-key "$STORAGE_KEY" \
                --overwrite true \
                --only-show-errors 2>/dev/null
            
            uploaded=$((uploaded + $(find "$ticker_dir" -type f | wc -l)))
            echo "   ✅ $ticker ($uploaded/$total_files files)"
        fi
    done
    echo "   📄 Uploaded $uploaded SEC filing files"
else
    echo "⚠️  No SEC filings found in $DATA_DIR/sec_filings"
fi

# Upload news articles
if [ -d "$DATA_DIR/news_articles" ]; then
    echo ""
    echo "📰 Uploading news articles..."
    
    total_files=$(find "$DATA_DIR/news_articles" -type f -name "*.parquet" | wc -l | tr -d ' ')
    uploaded=0
    
    for ticker_dir in "$DATA_DIR/news_articles"/*/; do
        if [ -d "$ticker_dir" ]; then
            ticker=$(basename "$ticker_dir")
            
            # Upload all parquet files for this ticker
            for file in "$ticker_dir"*.parquet; do
                if [ -f "$file" ]; then
                    az storage blob upload \
                        --container-name "news-articles" \
                        --file "$file" \
                        --name "$ticker/$(basename "$file")" \
                        --account-name "$STORAGE_ACCOUNT" \
                        --account-key "$STORAGE_KEY" \
                        --overwrite true \
                        --only-show-errors 2>/dev/null
                    
                    uploaded=$((uploaded + 1))
                    printf "\r   📰 Uploaded $uploaded/$total_files news files"
                fi
            done
        fi
    done
    echo ""
    echo "   📰 Uploaded $uploaded news article files"
else
    echo "⚠️  No news articles found in $DATA_DIR/news_articles"
fi

# Upload stock data
if [ -d "$DATA_DIR/stock_data" ]; then
    echo ""
    echo "📈 Uploading stock data..."
    
    total_files=$(find "$DATA_DIR/stock_data" -type f | wc -l | tr -d ' ')
    uploaded=0
    
    az storage blob upload-batch \
        --destination "stock-data" \
        --source "$DATA_DIR/stock_data" \
        --account-name "$STORAGE_ACCOUNT" \
        --account-key "$STORAGE_KEY" \
        --overwrite true \
        --only-show-errors 2>/dev/null
    
    uploaded=$(find "$DATA_DIR/stock_data" -type f | wc -l | tr -d ' ')
    echo "   📈 Uploaded $uploaded stock data files"
else
    echo "⚠️  No stock data found in $DATA_DIR/stock_data"
fi

echo ""
echo "=========================================="
echo "✅ Data Upload Complete!"
echo "=========================================="

# Show container contents summary
echo ""
echo "📊 Storage Contents:"
for container in "sec-filings" "news-articles" "stock-data"; do
    count=$(az storage blob list \
        --container-name "$container" \
        --account-name "$STORAGE_ACCOUNT" \
        --account-key "$STORAGE_KEY" \
        --query "length(@)" -o tsv 2>/dev/null || echo "0")
    echo "   $container: $count blobs"
done
