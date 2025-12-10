# How FinagentiX Works

A simple explanation of how the AI-powered financial trading assistant operates.

---

## 🗂️ Data Setup (One-Time Batch Load)

### Step 1: Load Stock Market Data
**What:** Download 1 year of historical price data (OHLCV) for 20-30 stocks from Yahoo Finance  
**Why:** Agents need historical trends to analyze patterns and make predictions  
**Storage:** Redis TimeSeries - optimized for fast time-based queries

### Step 2: Load News Articles
**What:** Fetch 200-500 recent financial news articles from NewsAPI  
**Why:** Agents need current market sentiment and events affecting stock prices  
**Storage:** Azure Storage (Blob) + Redis (metadata) - cost-effective for large text

### Step 3: Load SEC Filings
**What:** Download 5-10 recent company filings (10-K, 10-Q) from SEC EDGAR  
**Why:** Agents need official company financials and disclosures for analysis  
**Storage:** Azure Storage (Blob) + Redis (metadata) - compliance documents are large

### Step 4: Generate Embeddings
**What:** Convert all text (news + filings) into vector embeddings using Azure OpenAI  
**Why:** Enables semantic search - find relevant information by meaning, not just keywords  
**Storage:** Redis HNSW vectors - ultra-fast similarity search

### Step 5: Create Feature Store
**What:** Calculate technical indicators (moving averages, RSI, volatility) using Featureform  
**Why:** Pre-computed features speed up agent decision-making  
**Storage:** Redis (online store) via Featureform - instant feature lookup by ticker + timestamp  
**Status:** ✅ Featureform deployed and ready (West US 3)

---

## 💬 User Asks a Question

**Example:** *"Should I invest in AAPL? What are the risks?"*

---

## 🤖 What Happens Next

### Step 1: Semantic Cache Check (Full Response)
**What:** Convert query to embedding and search for similar past questions in Redis  
**Why:** If we answered this exact question before, return cached response instantly  
**Storage:** Redis HNSW vectors - similarity threshold 0.92+  
**Savings:** 30-70% LLM cost reduction (avoids ALL downstream processing)  
**Result:** Cache hit → return answer immediately | Cache miss → continue to Step 2

### Step 2: Contextual Memory Lookup
**What:** Load user's conversation history and preferences from Redis  
**Why:** Understand context - user's risk tolerance, portfolio, past interactions  
**Storage:** Redis JSON (user profile) + Hashes (session data)  
**Example:** User previously said "I'm conservative" → influences recommendations

### Step 3: Semantic Routing (Workflow Decision Shortcut)
**What:** Check if this type of question has a cached **workflow routing** in Redis  
**Cache Hit:** Route directly to known workflow (skip orchestrator reasoning!)  
- Example: "Should I buy AAPL?" → matches pattern → **Investment Analysis Workflow**  
- Workflow includes: Market Data Agent + Risk Agent + Sentiment Agent + Fundamental Agent  
- **Result:** Go directly to Step 5 with pre-determined agent list (skip Step 4 orchestrator)  
**Cache Miss:** New type of question → needs orchestrator to decide which workflow/agents  
- **Result:** Continue to Step 4  
**Why:** Router shortcuts the "which workflow?" decision - avoids orchestrator's LLM reasoning  
**Storage:** Redis Hashes (query patterns → workflow names → agent lists)

### Step 4: Orchestrator Agent (Only if Routing Cache Miss)
**What:** LLM makes expensive reasoning call to determine workflow strategy  

**The Orchestrator's Reasoning Process (LLM Call):**
1. **Analyzes user intent:** "What is the user really asking?"
   - Example: "Compare AAPL vs TSLA for 5-year horizon considering ESG factors"
   - Intent: Long-term comparative investment analysis with sustainability factors

2. **Determines required information:** "What data do we need?"
   - Stock price trends (5 years historical)
   - Financial fundamentals (revenue, profit, growth)
   - Risk metrics (volatility, beta)
   - ESG scores and sustainability reports
   - News sentiment on both companies

3. **Selects agents:** "Which specialized agents can provide this?"
   - Market Data Agent (price trends, technical analysis)
   - Fundamental Analysis Agent (financial statements)
   - Risk Assessment Agent (volatility, risk metrics)
   - Sentiment Agent (news analysis)
   - *Note:* Need to run for BOTH AAPL and TSLA

4. **Plans execution order:** "What sequence makes sense?"
   - Parallel: Market Data + Fundamental + Risk + Sentiment (both stocks)
   - Sequential: Compare results → synthesize recommendation

5. **Creates workflow plan:** JSON structure with agent list, parameters, dependencies

**Why This Is Expensive:** This reasoning requires 1-2 LLM calls (200-500 tokens)

**Cache Result:** Store mapping: "comparative 5-year investment ESG" → [Workflow Plan]

**Future Similar Questions:** "Compare MSFT vs GOOGL long-term ESG" → Cache hit! Skip this entire reasoning step

**Output:** Workflow execution plan → proceed to Step 5 with agent list
**What:** Search Redis vectors for relevant SEC filings, news articles, research reports  
**Why:** Find context documents to ground LLM response in real data  
**Storage:** Redis HNSW vectors for 10-K filings, news articles  
**Result:** Top 5 relevant documents retrieved in <10ms

### Step 5: Market Data Agent Executes (Multiple Tools!)
**Agent Goal:** Analyze AAPL market trends  

**Tool 1: "Get Stock Price"**
- **Tool Caching Check:** AAPL prices cached in last hour?  
- **Cache Hit:** Return cached prices (no API call!)  
- **Cache Miss:** Call yfinance API → cache in Redis  

**Tool 2: "Calculate Moving Averages"**
- **Tool Caching Check:** AAPL 50-day/200-day MA cached?  
- **Cache Hit:** Return cached calculation  
- **Cache Miss:** Compute → cache in Redis  

**Tool 3: "Get Trading Volume"**
- **Tool Caching Check:** AAPL volume data cached?  
- **Cache Hit:** Return cached volume  
- **Cache Miss:** Fetch → cache in Redis  

**Why:** Single agent uses multiple tools - each tool call is cached independently  
**Output:** "AAPL up 15% this quarter, showing strong upward momentum, volume increasing"

### Step 6: News Sentiment Agent - Tool: "Search News"
**What:** Agent needs AAPL-related news articles  
**Tool Caching Check:** Semantic search in Redis vectors for cached news summaries  
- **Cache Hit:** Return cached news analysis (no web scraping needed!)  
- **Cache Miss:** Fetch from NewsAPI → process → cache in Redis  
**Why:** Summarizing 5-10 webpages would be very expensive LLM operations  
**Output:** "Recent news 70% positive - new product launch announced"

### Step 7: RAG - Tool: "Search SEC Filings"
**What:** Agent needs AAPL financial statements  
**VectorDB Search:** Redis HNSW vectors find relevant 10-K sections  
**Tool Caching:** Cached document embeddings and summaries  
**Why:** No need to re-process and re-embed documents every time  
**Output:** Retrieved relevant sections in <10ms

### Step 8: Risk Assessment Agent - Tool: "Calculate Volatility"
**What:** Agent needs AAPL risk metrics  
**Tool Caching Check:** Volatility calculations cached from Featureform + Redis  
- **Cache Hit:** Return pre-computed features (no recalculation!)  
- **Cache Miss:** Calculate from time-series data → cache result  
**Output:** "AAPL volatility: Medium (±3% daily avg)"

### Step 9: Fundamental Analysis Agent - Tool: "Analyze Financials"
**What:** Agent analyzes retrieved SEC filing data  
**Tool Caching:** Financial ratios and analysis cached in Redis  
**Output:** "Strong balance sheet, P/E ratio 25, revenue growth 8%"

### Step 10: Orchestrator Synthesizes Results
**What:** Collect all agent outputs and prepare for LLM synthesis  
**Why:** Each agent ran independently, now combine their findings  
**Note:** Every tool call above was cached - massive savings!

### Step 11: LLM Synthesis (Azure OpenAI GPT-4)
**What:** All agent findings + retrieved documents sent to GPT-4 for final answer  
**Why:** Generate comprehensive, accurate answer grounded in real financial data  
**How:** Context from Redis + GPT-4 = no hallucinations, factual response

### Step 12: Store Full Response in Semantic Cache
**What:** Final answer + query embedding stored in Redis HNSW vectors  
**Why:** Next similar question (0.92+ similarity) gets instant response from Step 1  
**Duration:** 1 hour cache for market data, 24 hours for fundamental analysis  
**Impact:** This is where the 30-70% cost savings comes from!

### Step 13: Update Contextual Memory
**What:** User's question, preferences, and interaction saved in Redis  
**Why:** Future conversations are personalized (remembers risk tolerance, interests, portfolio)  
**Storage:** Redis JSON - flexible conversation history

### Step 14: Return Answer to User
**What:** Formatted response delivered via API  
**Why:** User gets AI-powered investment insights in seconds  
**Result:** "Yes, AAPL shows strong growth potential. Risk: Medium. Recent news positive. Consider: High P/E ratio, diversify portfolio."

---

## 🔄 Behind the Scenes: Three Layers of Caching

### 1. Semantic Cache (Step 1) - Full Response Caching
**When:** Before any processing starts  
**What:** Cache entire final answer to similar questions  
**Savings:** 30-70% cost reduction - avoids ALL downstream work  
**Example:** "Should I buy AAPL?" cached → "Is AAPL a good investment?" returns cached answer  
**Storage:** Redis HNSW vectors (query embeddings + responses)

### 2. Semantic Router (Step 3) - Decision Caching
**When:** During request analysis  
**What:** Cache routing decisions to avoid LLM reasoning  
**Savings:** Every routing decision would be an LLM call - now cached  
**Example:** "Buy AAPL?" → Investment workflow (cached route, no LLM call)  
**Storage:** Redis Hashes (query patterns → workflow routes)

### 3. Tool Caching (Steps 5-9) - Individual Tool Output Caching
**When:** During agent execution  
**What:** Cache every tool call result (API calls, calculations, web scraping)  
**Savings:** 20-40x fewer LLM calls - one agent flow can have 20-40 tool calls!  
**Examples:**  
- Stock price API call → cached 5 minutes  
- News article summaries → cached 1 hour  
- Financial calculations → cached 24 hours  
- Document embeddings → cached permanently  
**Storage:** Redis Hashes (tool name + params → output)

### Additional Redis Coordination:
- **Agent State Tracking:** Each agent's progress stored (Redis Hash)
- **Dead Letter Queue:** Failed operations logged for retry (Redis List)
- **Rate Limiting:** API call tracking to stay within limits (Redis Sorted Set)
- **Contextual Memory:** User preferences and history (Redis JSON)

---

## 📊 Example Flow Diagram

```
User Question: "Should I invest in AAPL?"
        ↓
Orchestrator Agent
        ↓
┌───────┴───────┬──────────┬──────────┬──────────┐
↓               ↓          ↓          ↓          ↓
Market Data   News      Risk      Fundamental  GPT-4
Agent      Sentiment  Assessment   Analysis   Synthesis
   ↓            ↓          ↓          ↓          ↓
Redis       Redis      Redis      Redis      Redis
TimeSeries  Vectors    Features   Vectors    Cache
   ↓            ↓          ↓          ↓          ↓
└───────┬───────┴──────────┴──────────┴──────────┘
        ↓
  Final Answer: "Yes, AAPL shows strong growth potential.
                 Risk: Medium. Recent news positive.
                 Consider: High P/E ratio, diversify portfolio."
```

---

## ⚡ Why It's Fast

1. **Pre-computed Features:** Technical indicators calculated during setup, not on-demand
2. **Vector Search:** Redis HNSW finds relevant data in <10ms (vs. scanning everything)
3. **Caching Everywhere:** Embeddings, API results, agent outputs all cached
4. **In-Memory Data:** Redis keeps hot data in RAM - no disk latency
5. **Parallel Agent Execution:** Multiple agents work simultaneously using Redis pub/sub

---

## 💰 Why It's Cost-Effective

1. **One-Time Data Load:** Batch ingestion runs once, then deletes (Stage 3)
2. **Scale to Zero:** Agent API (Stage 4) stops when not in use - no idle costs
3. **Free APIs:** Yahoo Finance, NewsAPI, SEC EDGAR - zero data acquisition cost
4. **Efficient Caching:** Reduces Azure OpenAI API calls by 60-80%
5. **Small Dataset:** 20-30 tickers fit in Redis E5 (6GB) - lowest Enterprise tier

---

## 🔒 Why It's Secure

1. **Private Endpoints:** All Azure resources communicate over private network
2. **Internal-Only Featureform:** Container Apps configured as VNet-internal (no public access)
3. **Debug VM Access:** Dedicated VM with public IP for secure VNet access and management
4. **Redis AOF + RDB:** Data persisted every second, full backup every hour
5. **Azure Managed Identity:** No passwords stored in code (retrieved from Azure)
6. **Private DNS:** Services resolve internally, not exposed to internet

---

## 📈 What Makes It AI-Powered

- **Multi-Agent Coordination:** 7+ specialized agents work together using **Microsoft Agent Framework** (Semantic Kernel)
  - Orchestration Patterns: Sequential, Concurrent, Handoff, Group Chat, Magentic
  - Agent-to-Agent (A2A) protocol for seamless communication
  - Model Context Protocol (MCP) for tool interoperability
- **Retrieval Augmented Generation (RAG):** Answers grounded in real financial data
- **Semantic Search:** Finds relevant information by meaning, not just keywords
- **Contextual Memory:** Learns user preferences across conversations
- **Real-Time Synthesis:** Combines historical data + news + financials + AI reasoning
- **Enterprise-Grade Observability:** OpenTelemetry integration with Application Insights

---

## 🎯 The Result

Users get **instant, personalized, data-driven investment insights** powered by:
- Real financial data (not hallucinated)
- Multi-source analysis (market + news + fundamentals)
- Risk-aware recommendations
- Conversational interface
- Sub-second response times

All running on **modular, cost-optimized Azure infrastructure** that scales with demand.

---

## 🚀 Current Deployment Status

### Infrastructure: ✅ COMPLETE

**Region:** West US 3  
**Resource Group:** finagentix-dev-rg  
**Deployed Components:**

- ✅ **Redis Enterprise** (redis-3ae172dc9e9da) - Balanced_B5 with all modules
- ✅ **Featureform** (featureform-3ae172dc9e9da) - 3 replicas, internal-only access
- ✅ **Azure OpenAI** (openai-3ae172dc9e9da) - GPT-4 and embeddings
- ✅ **Storage Account** (st3ae172dc9e9da) - For SEC filings and news
- ✅ **Debug VM** (debug-vm-3ae172dc9e9da) - Ubuntu 22.04, Public IP: 4.227.91.227
- ✅ **VNet + Private Endpoints** - Complete networking infrastructure
- ✅ **Monitoring** - Log Analytics + Application Insights

### Deployment Automation: ✅ INTEGRATED

**One-Command Deployment:**
```bash
export AZURE_ENV_NAME=dev
export AZURE_LOCATION=westus3
./infra/scripts/deploy-full.sh
```

**Features:**
- Automated Featureform definitions application
- Region-flexible scripts (defaults to westus3)
- Complete cleanup/redeploy capability
- Progress tracking and error handling

### Next Steps:

1. **Apply Featureform Definitions** - Register features and entities
   ```bash
   ./infra/scripts/connect-and-apply.sh
   ```

2. **Load Market Data** - Batch load historical stock prices to Redis TimeSeries

3. **Generate Embeddings** - Create vectors for SEC filings and news articles

4. **Deploy Agents** - Implement and deploy the 7+ specialized agents

5. **Test End-to-End** - Validate the complete workflow with real queries

**Documentation:**
- Complete setup guide: [DEPLOYMENT_INTEGRATION.md](docs/DEPLOYMENT_INTEGRATION.md)
- Infrastructure details: [STAGE4_DEPLOYMENT_SUMMARY.md](docs/STAGE4_DEPLOYMENT_SUMMARY.md)
- Architecture overview: [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)
