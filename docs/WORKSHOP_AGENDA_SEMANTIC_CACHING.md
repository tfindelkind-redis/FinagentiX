# Redis for AI Workshop
## Semantic Caching, Vector Search & AI-Powered Use Cases

---

**Meeting Type:** Technical Discovery & Exploration Workshop  
**Duration:** 2.5 - 3 hours  
**Attendees:** Head of Infrastructure, DevOps Engineers, Redis Team  

---

## Workshop Objectives

1. Explore Redis AI capabilities in Azure Managed Redis (AMR)
2. Deep dive into Semantic Caching for LLM cost reduction
3. Understand Semantic Routing for AI agent orchestration
4. Learn Vector Search / RAG patterns for knowledge retrieval
5. Discover Agent Memory architecture for conversational AI
6. Identify applicable use cases for your organization
7. Discuss HSM integration requirements and security considerations

---

## Agenda

### 1. Introductions & Context Setting (15 min)
- Team introductions and roles
- Workshop goals and expected outcomes
- Current AI/LLM landscape and challenges
- Why Redis for AI? (performance, simplicity, unified platform)

---

### 2. Current State Discovery (20 min)

#### AI/LLM Infrastructure
- [ ] Current LLM providers (Azure OpenAI, OpenAI, Anthropic, other)
- [ ] Models in use (GPT-4o, GPT-4, embeddings)
- [ ] Estimated query volumes (daily/monthly)
- [ ] Current caching strategy for LLM responses (if any)
- [ ] Latency and cost concerns
- [ ] Rate limiting challenges experienced

#### Existing Redis Usage
- [ ] Current Redis deployment (ACRE, AMR, other)
- [ ] Existing use cases (caching, sessions, etc.)
- [ ] Familiarity with Redis data structures

#### AI Application Landscape
- [ ] Chatbots / Conversational AI
- [ ] RAG / Knowledge retrieval systems
- [ ] AI-powered search
- [ ] Agent-based workflows
- [ ] ML inference pipelines

---

### 3. Semantic Caching Deep Dive (45 min)

> **Business Problem:** LLM APIs are expensive. GPT-4o costs $2.50/1M input + $10/1M output tokens.  
> At 100K queries/day = $15K-$30K/month. Most queries are semantically similar!

#### The Problem (10 min)
| Metric | Without Cache | The Challenge |
|--------|--------------|---------------|
| LLM Cost/1000 queries | $0.50-$2.00 | Paying repeatedly for similar questions |
| Response Time | 2-10 seconds | Users waiting for every LLM call |
| Rate Limits | Constant battles | Azure OpenAI throttling |

#### How Semantic Caching Works (15 min)
```
Traditional Cache:          Semantic Cache:
"What is AAPL price?" ─────→ MISS        "What is AAPL price?" ─────→ MISS (first time)
"what is aapl price?" ─────→ MISS        "what is aapl price?" ─────→ HIT! (similar)
"AAPL stock price?"   ─────→ MISS        "AAPL stock price?"   ─────→ HIT! (similar)
                                         "How much is Apple?"  ─────→ HIT! (semantically same)
```

- Query → Embedding → Vector Similarity Search
- Threshold tuning (0.90-0.95 typical)
- Cache structure in Redis

#### What's Stored in Redis
```redis
# Cached LLM response with embedding
HSET llm:cache:abc123
     query "What is the current price of Apple stock?"
     response "As of today, Apple (AAPL) is trading at $185.50..."
     model "gpt-4o"
     tokens_used 450
     embedding "\x00\x01\x02..."  # 1536-dim vector (binary)
     created_at "2024-01-15T10:00:00Z"
     ttl 3600

# Vector index for semantic matching
FT.CREATE llm_cache_idx ON HASH PREFIX 1 llm:cache:
    SCHEMA embedding VECTOR HNSW 6 DIM 1536 DISTANCE_METRIC COSINE
```

#### ROI & Impact - Per Cache Layer (10 min)

> **Scenario:** 3M monthly queries at 10K users × 10 queries/day

##### Semantic Cache (Full Response Caching)
| Metric | Calculation | Value |
|--------|-------------|-------|
| Hit Rate (typical) | Depends on query patterns | 40-60% |
| Queries Saved | 3M × 50% hit rate | 1,500,000 |
| Cost Per LLM Call | GPT-4o pricing | $0.0069 |
| **Monthly Savings** | 1.5M × $0.0069 | **$10,350/mo** |

##### Router Cache (Agent Routing)
| Metric | Calculation | Value |
|--------|-------------|-------|
| Hit Rate (typical) | Similar queries use same agent | 30-50% |
| Routing Calls Saved | 3M × 40% hit rate | 1,200,000 |
| Cost Per Routing Call | Smaller LLM call | $0.0008 |
| **Monthly Savings** | 1.2M × $0.0008 | **$960/mo** |

##### Tool Cache (External API Results)
| Metric | Calculation | Value |
|--------|-------------|-------|
| Hit Rate (typical) | TTL-based, varies by data freshness | 20-40% |
| API Calls Saved | 3M × 30% hit rate | 900,000 |
| Cost Per API Call | Varies | ~$0.0001 |
| **Monthly Savings** | 900K × $0.0001 | **$90/mo** |

##### Combined Savings (Single Redis Instance)
| Cache Layer | Monthly Savings |
|-------------|-----------------|
| Semantic Cache | $10,350 |
| Router Cache | $960 |
| Tool Cache | $90 |
| **Total** | **$11,400/mo** |

#### 🏆 Customer Success: Mangoes.ai Healthcare
- Faster healthcare voice assistant with semantic caching
- Reduced LLM costs while maintaining response quality

#### Live Demo (10 min)
- Show semantic caching in action
- Demonstrate cost savings visualization
- Cache hit/miss patterns

---

### 4. Semantic Routing (30 min)

> **Business Problem:** Rule-based intent routing is fragile. Regex breaks with paraphrases.  
> "AAPL stock price" routes correctly, but "How much is Apple trading at?" fails.

#### The Problem
```python
# Legacy: Fragile regex routing
if "weather" in query.lower():
    return WeatherHandler()
elif "stock" in query.lower() or "price" in query.lower():
    return StockHandler()
# ❌ "AAPL quote" → MISS (no "stock" keyword)
# ❌ "How much is Microsoft?" → MISS
```

#### How Semantic Routing Works
```
Pre-defined Routes with Examples:
┌─────────────────────────────────────────────────────────┐
│ Route: "stock_price"                                    │
│ Examples: ["AAPL price", "What's Tesla trading at?",   │
│            "How much is Microsoft stock?"]              │
│ Handler: StockPriceAgent                               │
└─────────────────────────────────────────────────────────┘

User Query: "How much is Google?"
→ Embed query
→ Find nearest route (stock_price: 0.94 similarity)
→ Route to StockPriceAgent ✅
```

#### What's Stored in Redis
```redis
# Route definitions with example embeddings
HSET route:stock:001
     route_name "stock_price"
     example "AAPL stock price"
     handler "StockPriceAgent"
     embedding "\x00\x01..."

HSET route:stock:002
     route_name "stock_price"
     example "How much is Tesla trading at"
     handler "StockPriceAgent"
     embedding "\x00\x02..."

# Vector index for route matching
FT.CREATE routes_idx ON HASH PREFIX 1 route:
    SCHEMA 
        route_name TAG
        handler TAG
        embedding VECTOR HNSW 6 DIM 1536 DISTANCE_METRIC COSINE

# Match incoming query to best route
FT.SEARCH routes_idx "*=>[KNN 1 @embedding $query_vec]"
```

#### Why Semantic > Rules
| Query | Rule-Based | Semantic Router |
|-------|------------|-----------------|
| "AAPL stock price" | ✅ Hit | ✅ Hit |
| "AAPL quote" | ❌ MISS | ✅ Hit |
| "How much is Microsoft?" | ❌ MISS | ✅ Hit |
| "What's the weather?" | ✅ Hit | ✅ Hit |
| "Is it gonna rain?" | ❌ MISS | ✅ Hit |

#### Use Cases
- Multi-agent AI systems (route to specialist agents)
- Intent classification for chatbots
- Dynamic workflow routing
- Multilingual support (add examples in any language)

---

### ☕ Break (10 min)

---

### 5. Vector Search / RAG (35 min)

> **Business Problem:** LLMs hallucinate. RAG grounds responses in real documents.  
> But traditional RAG needs 3+ systems: PostgreSQL + Pinecone + Elasticsearch = complexity & latency.

#### The Problem: Multi-System RAG
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ PostgreSQL  │◄──►│  Pinecone   │◄──►│Elasticsearch│
│ (documents) │    │  (vectors)  │    │  (search)   │
└─────────────┘    └─────────────┘    └─────────────┘
       ⚠️ 3 systems to maintain
       ⚠️ Sync pipelines required
       ⚠️ 50-200ms multi-hop latency
```

#### Redis: Unified RAG Architecture
```
┌────────────────────────────────────┐
│             Redis                  │
│  ┌──────────────────────────────┐ │
│  │ Documents + Vectors + Search │ │
│  │ ALL IN ONE SYSTEM            │ │
│  └──────────────────────────────┘ │
│     ✅ Single system              │
│     ✅ <1ms hybrid queries        │
│     ✅ No sync needed             │
└────────────────────────────────────┘
```

#### What's Stored in Redis
```redis
# Document chunks with embeddings
HSET doc:chunk:001
     doc_id "10K-2024-Q1"
     text "Revenue for Q1 2024 was $45.2B, up 12% YoY..."
     source "sec_filings/aapl_10k.pdf"
     page 42
     embedding "\x00\x01\x02..."  # 1536-dim vector

# Vector index with hybrid search
FT.CREATE docs_idx ON HASH PREFIX 1 doc:chunk:
    SCHEMA 
        text TEXT
        source TAG
        page NUMERIC
        embedding VECTOR HNSW 6 DIM 1536 DISTANCE_METRIC COSINE

# Semantic search + metadata filtering
FT.SEARCH docs_idx 
    "(@source:{sec_filings*})=>[KNN 5 @embedding $query_vec]"
```

#### RAG Flow
```
1. User: "What are Apple's revenue projections?"
2. Embed question → vector
3. Redis vector search → find relevant document chunks
4. Inject documents into LLM prompt as context
5. LLM generates grounded, accurate response
```

#### Benchmark: Redis vs. Alternatives
| Database | QPS | Latency |
|----------|-----|---------|
| **Redis** | **Baseline** | **< 1ms** |
| Qdrant | 3.4x slower | 4x higher |
| Milvus | 3.3x slower | 4.67x higher |
| PostgreSQL pgvector | 9.5x slower | 9.7x higher |

#### 🏆 Customer Success: Relevance AI
- **99.5% faster** with Redis-powered vector search
- Enabled real-time semantic search at scale

---

### 6. Agent Memory (25 min)

> **Business Problem:** AI agents are stateless. They forget conversation context.  
> SQL JOINs for history = 5-20ms. No semantic recall from past conversations.

#### Memory Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Memory in Redis                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Short-term Memory (Lists):                                 │
│  └─ Recent conversation messages (LPUSH, LTRIM)            │
│                                                             │
│  Long-term Memory (Hashes):                                 │
│  └─ User preferences, profiles, persistent facts           │
│                                                             │
│  Semantic Memory (Vectors):                                 │
│  └─ Important facts with embeddings for recall             │
│     "User prefers formal responses" → searchable           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### What's Stored in Redis
```redis
# Short-term: Recent conversation (auto-expiring)
LPUSH conversation:session:abc123 
    '{"role":"user","content":"What is my portfolio value?"}'
LTRIM conversation:session:abc123 0 19  # Keep last 20
EXPIRE conversation:session:abc123 3600  # 1 hour TTL

# Long-term: User profile
HSET user:12345:profile
     name "John Doe"
     response_style "concise"
     risk_tolerance "moderate"
     favorite_stocks "AAPL,MSFT,GOOGL"

# Semantic: Searchable facts
HSET memory:user:12345:001
     fact "User prefers alerts before market open"
     importance "high"
     embedding "\x00\x01..."

# Recall relevant memories for current context
FT.SEARCH memory_idx "*=>[KNN 3 @embedding $query_vec]"
```

#### Why Redis > SQL for Agent Memory
| Operation | SQL | Redis |
|-----------|-----|-------|
| Get recent 20 messages | 5-20ms | <0.5ms |
| Update user profile | Transaction | Atomic HSET |
| Semantic recall | ❌ Not possible | Built-in vectors |
| Session expiration | Cron job | Native TTL |

---

### 7. Additional Use Cases Overview (15 min)

#### Quick Reference: Redis for AI

> **Note:** All three AI caches (Semantic, Router, Tool) run on a **single Azure Managed Redis instance** for simplicity and cost efficiency.

| Use Case | What It Does | Redis Advantage | Typical Savings |
|----------|--------------|-----------------|-----------------|
| **Semantic Cache** | Cache full LLM responses by meaning | Skip entire LLM call | 40-60% of LLM costs |
| **Router Cache** | Cache agent routing decisions | Skip routing LLM call | 30-50% of routing costs |
| **Tool Cache** | Cache external API results (TTL) | Skip API calls | Varies by API |
| **Vector Search / RAG** | Ground LLM in real documents | Single system, <1ms | - |
| **Agent Memory** | Remember conversations | Semantic recall built-in | - |
| **Feature Store** | Real-time ML features | <1ms serving, no skew | - |

#### Beyond AI: Foundational Use Cases

| Use Case | Complexity | Time to Value |
|----------|------------|---------------|
| 🟢 Caching | Simple | Hours |
| 🟢 Sessions | Simple | Hours |
| 🟢 Rate Limiting | Simple | Hours |
| 🟡 Job Queues | Medium | 1-3 days |
| 🟡 Leaderboards | Medium | 1-3 days |
| 🟡 Pub/Sub & Streams | Medium | 1-3 days |

#### Discussion
- [ ] Which AI use cases resonate most?
- [ ] Any upcoming projects involving AI/ML?
- [ ] Current challenges with LLM costs or latency?

---

### 8. Security & HSM Integration (20 min)

#### AMR Security Model
- Encryption at rest (Azure-managed or CMK)
- Encryption in transit (TLS 1.2+)
- Azure AD authentication
- Role-Based Access Control (RBAC)
- Private Link / VNet integration

#### HSM Integration
- Azure Key Vault integration
- Customer-Managed Keys (CMK)
- Hardware Security Module options
- Key rotation policies
- BYOK support

#### Compliance
- SOC 2 Type II
- HIPAA
- PCI DSS
- ISO 27001

#### Questions
- [ ] Current key management approach?
- [ ] Specific compliance requirements?
- [ ] Data classification policies?

---

### 9. Next Steps & Action Items (15 min)

#### Immediate Actions
- [ ] Share workshop notes and materials
- [ ] Provide Redis for AI documentation
- [ ] Share code samples (Python, .NET)

#### Short-term (1-2 weeks)
- [ ] Identify pilot use case (semantic caching recommended as quick win)
- [ ] Initial AMR sizing and cost estimate
- [ ] POC scope definition
- [ ] Security assessment kickoff

#### Medium-term (1-2 months)
- [ ] POC implementation
- [ ] Performance benchmarking
- [ ] Production planning

#### Follow-up Sessions
- [ ] Hands-on technical workshop
- [ ] Architecture design review
- [ ] POC results discussion

---

## Pre-Workshop Preparation

Please prepare:

1. **LLM usage details:**
   - Current providers and models
   - Query volumes (daily/monthly)
   - Cost breakdown if available
   
2. **AI/ML project roadmap:**
   - Upcoming AI initiatives
   - Current pain points
   
3. **Questions for Redis team:**
   - Technical questions
   - Use case validation

---

## Resources to Share Post-Workshop

### Redis for AI
- Semantic Caching implementation guide
- Vector Search / RAG quickstart
- Semantic Router examples
- Agent Memory patterns

### Code Samples
- Python (LangChain, LlamaIndex integration)
- .NET (Semantic Kernel integration)
- Reference architectures

### AMR Documentation
- Azure Managed Redis overview
- Security best practices
- Sizing guide

---

## Contact Information

**Redis Team:**  
- [Your Name] - [Role]
- [Technical Contact] - Solutions Architect

**Customer Team:**  
- Head of Infrastructure - [Name]
- DevOps Engineer 1 - [Name]
- DevOps Engineer 2 - [Name]

---

## Parking Lot

*Topics for follow-up:*

1. _____________________________________
2. _____________________________________
3. _____________________________________

---

*Agenda is flexible based on discussion flow.*

**Total Time: ~2.5 - 3 hours** (including break)
