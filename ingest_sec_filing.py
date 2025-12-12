#!/usr/bin/env python3
"""
SEC Filing Ingestion Script

Helper script to download and ingest SEC filings into the document store.

Usage:
    # Ingest a single filing
    python ingest_sec_filing.py --ticker AAPL --doc-type 10-K --year 2023
    
    # Ingest from local file
    python ingest_sec_filing.py --file path/to/filing.txt --ticker AAPL --doc-type 10-K
    
    # Ingest from URL
    python ingest_sec_filing.py --url "https://www.sec.gov/..." --ticker AAPL --doc-type 10-K
"""

import asyncio
import argparse
import httpx
from pathlib import Path
from datetime import datetime


API_URL = "http://localhost:8000"


async def ingest_from_file(
    file_path: str,
    ticker: str,
    doc_type: str,
    company: str = "",
    filing_date: str = "",
):
    """Ingest a filing from local file"""
    
    # Read file
    content = Path(file_path).read_text(encoding="utf-8")
    
    # Prepare metadata
    title = f"{ticker} {doc_type}"
    if filing_date:
        title += f" ({filing_date})"
    
    # Send to API
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_URL}/api/documents/ingest",
                json={
                    "content": content,
                    "title": title,
                    "source": "SEC",
                    "doc_type": doc_type,
                    "ticker": ticker,
                    "company": company,
                    "filing_date": filing_date,
                },
                timeout=120.0,  # 2 minutes for large documents
            )
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ Successfully ingested {data['message']}")
            print(f"   Document: {title}")
            print(f"   Chunks: {len(data['chunk_ids'])}")
            
        except httpx.HTTPError as e:
            print(f"❌ Error: {e}")
            if hasattr(e, 'response'):
                print(f"   Response: {e.response.text}")


async def ingest_from_url(
    url: str,
    ticker: str,
    doc_type: str,
    company: str = "",
    filing_date: str = "",
):
    """Download and ingest a filing from URL"""
    
    print(f"Downloading from {url}...")
    
    async with httpx.AsyncClient() as client:
        try:
            # Download document
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()
            content = response.text
            
            print(f"Downloaded {len(content)} characters")
            
            # Prepare metadata
            title = f"{ticker} {doc_type}"
            if filing_date:
                title += f" ({filing_date})"
            
            # Ingest
            response = await client.post(
                f"{API_URL}/api/documents/ingest",
                json={
                    "content": content,
                    "title": title,
                    "source": "SEC",
                    "doc_type": doc_type,
                    "ticker": ticker,
                    "company": company,
                    "filing_date": filing_date,
                    "url": url,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ Successfully ingested {data['message']}")
            print(f"   Document: {title}")
            print(f"   Chunks: {len(data['chunk_ids'])}")
            
        except httpx.HTTPError as e:
            print(f"❌ Error: {e}")


async def ingest_sample_document(ticker: str):
    """Ingest a sample document for testing"""
    
    content = f"""
# {ticker} Annual Report - Sample Document

## Business Overview
{ticker} is a leading technology company focused on innovation and customer satisfaction.
The company operates in multiple segments including cloud computing, software development,
and hardware manufacturing.

## Financial Highlights
- Revenue: $100B (up 15% YoY)
- Operating Income: $30B (up 20% YoY)
- Net Income: $25B (up 18% YoY)
- Cash and Equivalents: $50B

## Risk Factors
The company faces various risks including:
- Market competition from major players
- Regulatory changes in key markets
- Supply chain disruptions
- Cybersecurity threats
- Economic downturns

## Future Outlook
Management expects continued growth driven by:
- Strong demand for cloud services
- New product launches in AI and ML
- Expansion into emerging markets
- Strategic acquisitions and partnerships

## Conclusion
The company remains well-positioned for long-term growth with strong fundamentals,
innovative products, and a loyal customer base.
"""
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_URL}/api/documents/ingest",
                json={
                    "content": content,
                    "title": f"{ticker} 10-K Sample",
                    "source": "SEC",
                    "doc_type": "10-K",
                    "ticker": ticker,
                    "company": f"{ticker} Inc.",
                    "filing_date": datetime.now().strftime("%Y-%m-%d"),
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ Successfully ingested sample document")
            print(f"   Chunks: {len(data['chunk_ids'])}")
            print(f"\nYou can now test with:")
            print(f"   python cli.py")
            print(f"   > /ask")
            print(f"   > What are the risk factors for {ticker}?")
            
        except httpx.HTTPError as e:
            print(f"❌ Error: {e}")


async def main():
    parser = argparse.ArgumentParser(description="Ingest SEC filings into document store")
    
    parser.add_argument("--ticker", required=True, help="Stock ticker symbol")
    parser.add_argument("--doc-type", default="10-K", help="Document type (10-K, 10-Q, 8-K)")
    parser.add_argument("--company", default="", help="Company name")
    parser.add_argument("--filing-date", default="", help="Filing date (YYYY-MM-DD)")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--file", help="Path to local filing file")
    group.add_argument("--url", help="URL to download filing")
    group.add_argument("--sample", action="store_true", help="Ingest a sample document for testing")
    
    args = parser.parse_args()
    
    if args.sample:
        await ingest_sample_document(args.ticker)
    elif args.file:
        await ingest_from_file(
            args.file,
            args.ticker,
            args.doc_type,
            args.company,
            args.filing_date,
        )
    elif args.url:
        await ingest_from_url(
            args.url,
            args.ticker,
            args.doc_type,
            args.company,
            args.filing_date,
        )
    else:
        print("❌ Error: Must specify --file, --url, or --sample")
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
