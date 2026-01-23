#!/usr/bin/env python3
"""Check cosine similarity between two queries"""

import os
import numpy as np
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv('AZURE_OPENAI_API_KEY'),
    api_version='2024-02-01',
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
)

query1 = 'Analyze Microsoft'
query2 = 'Analyze Microsoft stock for long-term investment potential'

print(f'Generating embeddings...')

resp1 = client.embeddings.create(input=query1, model='text-embedding-3-large')
resp2 = client.embeddings.create(input=query2, model='text-embedding-3-large')

emb1 = np.array(resp1.data[0].embedding)
emb2 = np.array(resp2.data[0].embedding)

similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

print()
print(f'Query 1: "{query1}"')
print(f'Query 2: "{query2}"')
print()
print(f'Cosine Similarity: {similarity:.4f} ({similarity*100:.2f}%)')
print(f'Cache Threshold:   0.9200 (92.00%)')
print()
if similarity >= 0.92:
    print('✅ Would be a CACHE HIT (similarity >= threshold)')
else:
    print(f'❌ CACHE MISS (similarity {similarity:.4f} < threshold 0.92)')
    print(f'   Gap: {(0.92 - similarity)*100:.2f}% below threshold')
