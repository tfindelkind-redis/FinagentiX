#!/usr/bin/env python3
"""Clear cached responses for Microsoft-related queries"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import redis

def main():
    host = os.getenv('REDIS_HOST')
    port = int(os.getenv('REDIS_PORT', 10000))
    password = os.getenv('REDIS_PASSWORD')

    print(f"Connecting to {host}:{port}...")

    r = redis.Redis(
        host=host,
        port=port,
        password=password,
        ssl=True,
        decode_responses=True
    )

    # Search for cached responses related to Microsoft
    print("Searching for semantic_cache entries...")
    keys = list(r.scan_iter('semantic_cache:*', count=1000))
    print(f"Found {len(keys)} total semantic cache keys")

    microsoft_keys = []
    for key in keys:
        try:
            data = r.hgetall(key)
            query = data.get('query', '')
            response = data.get('response', '')
            
            # Check for Microsoft-related queries with bad responses
            if 'microsoft' in query.lower() or 'msft' in query.lower():
                microsoft_keys.append(key)
                print(f"\nKey: {key}")
                print(f"  Query: {query}")
                print(f"  Response: {response[:150]}...")
                
                # Delete if it has the bad "please provide a ticker" response
                if 'please provide a stock ticker' in response.lower():
                    print(f"  -> DELETING (bad cached response)")
                    r.delete(key)
        except Exception as e:
            print(f"Error processing {key}: {e}")

    print(f"\nProcessed {len(microsoft_keys)} Microsoft-related cache entries")

if __name__ == "__main__":
    main()
