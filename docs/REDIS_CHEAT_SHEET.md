# Redis Cheat Sheet: General & AI Use Cases

> **Comprehensive reference for Redis capabilities, legacy comparisons, and real-world success stories**

---

## 📖 How to Read This Guide

Each use case follows a consistent structure to help you understand both **what Redis stores** and **why legacy systems struggle**:

| Section | Icon | Description |
|---------|------|-------------|
| **📦 What's Stored in Redis** | `redis` code block | Actual Redis commands and data structures |
| **🗄️ What's Stored in Legacy DB** | `sql` code block with tables | How the same data looks in PostgreSQL/MySQL |
| **💡 Key Difference** | Callout box | Summary of why Redis is better |
| **Why Legacy is Slow** | Comparison table | Side-by-side performance/complexity comparison |
| **🏆 Customer Success** | Case study | Real companies, real results |

### Legend for Data Examples

```
┌─────────────────────────────────────────────────────────────────┐
│  📦 REDIS                    │  🗄️ LEGACY DATABASE              │
├─────────────────────────────────────────────────────────────────┤
│                              │                                   │
│  Key-value in RAM            │  Rows in table on disk            │
│  O(1) access                 │  Index lookup + disk I/O          │
│  Native TTL expiration       │  Cron jobs for cleanup            │
│  Atomic operations           │  Transactions with locks          │
│                              │                                   │
│  SET key "value" EX 3600     │  INSERT INTO table (...)          │
│  < 1ms                       │  5-50ms                           │
│                              │                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Table of Contents
1. [Why Redis? The Core Advantage](#why-redis-the-core-advantage)
2. [General Redis Use Cases](#general-redis-use-cases) (1-16)
   - Caching, Sessions, Leaderboards, Time-Series, Messaging, Rate Limiting
   - Deduplication, Full-Text Search, Fraud Detection, Geospatial
   - Distributed Locks, Job Queues, RDI (CDC), Inventory, Auth Tokens, Data Ingest
3. [Redis for AI Use Cases](#redis-for-ai-use-cases) (17-21)
   - Semantic Caching, Vector Search/RAG, Semantic Router, Agent Memory, Feature Store
4. [Performance Benchmarks](#performance-benchmarks)
5. [Customer Success Stories](#customer-success-stories)
6. [Quick Reference Tables](#quick-reference-tables)

### 📊 Use Case Quick Navigator

| # | Use Case | Data Structure | Legacy Pain Point |
|---|----------|----------------|-------------------|
| 1 | 🚀 Caching | String, Hash | Slow DB queries |
| 2 | 📊 Sessions | Hash + TTL | DB polling, cleanup jobs |
| 3 | 🏆 Leaderboards | Sorted Set | O(N) rank queries |
| 4 | ⏱️ Time-Series | TimeSeries | GROUP BY aggregations |
| 5 | 📨 Messaging | Streams, Pub/Sub | DB polling, no push |
| 6 | 🔐 Rate Limiting | String + INCR | Lock contention |
| 7 | 🔍 Deduplication | Bloom Filter | Huge lookup tables |
| 8 | 🔎 Full-Text Search | RediSearch | Elasticsearch sync |
| 9 | 🚨 Fraud Detection | Multi-structure | Batch processing |
| 10 | 📍 Geospatial | GEO | Haversine calculations |
| 11 | 🔐 Distributed Locks | SET NX PX | DB transactions |
| 12 | 📋 Job Queues | List, Stream | Polling, no priorities |
| 13 | 🔄 RDI (CDC) | Auto-sync | Cache-aside staleness |
| 14 | 📦 Inventory | Hash + Geo | ATP lag |
| 15 | 🔐 Auth Tokens | String + TTL | Token table bloat |
| 16 | 📡 Fast Data Ingest | Streams | Throughput limits |
| **AI Use Cases** |||
| 17 | 🧠 Semantic Cache | Vector + Hash | Exact-match only |
| 18 | 🔎 Vector/RAG | HNSW Vector | Multi-system complexity |
| 19 | 🛣️ Semantic Router | Vector | Regex maintenance |
| 20 | 🧠 Agent Memory | List + Vector | No semantic recall |
| 21 | 📊 Feature Store | Hash | Training/serving skew |

---

## Why Redis? The Core Advantage

### In-Memory Architecture
Redis stores all data in RAM, enabling **sub-millisecond latency** compared to disk-based databases that require I/O operations.

| Metric | Redis | Traditional DB | Difference |
|--------|-------|----------------|------------|
| Read Latency | < 1ms | 5-50ms | 50-500x faster |
| Write Latency | < 1ms | 10-100ms | 100-1000x faster |
| Throughput | 200M ops/sec | 10K-100K ops/sec | 2000x higher |

### Why Disk-Based Databases Are Slow
```
Traditional Database Request Flow:
┌─────────┐    ┌──────────┐    ┌────────────┐    ┌──────────┐
│ Request │───▶│ Network  │───▶│ Disk I/O   │───▶│ Response │
└─────────┘    └──────────┘    │ (5-15ms)   │    └──────────┘
                               │ + Query    │
                               │ Planning   │
                               │ (1-5ms)    │
                               │ + Index    │
                               │ Lookup     │
                               │ (1-10ms)   │
                               └────────────┘
                               
Redis Request Flow:
┌─────────┐    ┌──────────┐    ┌────────────┐    ┌──────────┐
│ Request │───▶│ Network  │───▶│ RAM Access │───▶│ Response │
└─────────┘    └──────────┘    │ (<0.1ms)   │    └──────────┘
                               └────────────┘   
```

---

## General Redis Use Cases

### 1. 🚀 Caching (Cache-Aside Pattern)

| Aspect | Description |
|--------|-------------|
| **What it does** | Stores frequently accessed data in memory to reduce database load and speed up response times |
| **How Redis does it** | Application checks Redis first; on miss, fetches from DB and stores in Redis with TTL expiration |
| **Data Structures** | Strings (GET/SET), Hashes (HGET/HSET) |

#### 📦 What's Actually Stored in Redis
```redis
# Product cache (String - JSON serialized)
SET product:12345 '{"id":12345,"name":"Wireless Mouse","price":29.99,"stock":150}' EX 3600

# User profile cache (Hash - field-level access)
HSET user:789:profile 
     name "John Doe" 
     email "john@example.com" 
     tier "premium" 
     last_login "2024-01-15T10:30:00Z"
EXPIRE user:789:profile 1800

# API response cache (String with TTL)
SET api:weather:NYC '{"temp":72,"condition":"sunny","humidity":45}' EX 300

# Query result cache
SET query:products:electronics:page1 '[{"id":1,"name":"TV"},{"id":2,"name":"Phone"}]' EX 600
```

#### 🗄️ What's Stored in Legacy Database (PostgreSQL/MySQL)
```sql
-- Products table (disk-based, requires I/O on every read)
┌─────────────────────────────────────────────────────────────────┐
│                        products                                  │
├────────┬─────────────────┬─────────┬───────┬───────────────────┤
│ id     │ name            │ price   │ stock │ updated_at        │
├────────┼─────────────────┼─────────┼───────┼───────────────────┤
│ 12345  │ Wireless Mouse  │ 29.99   │ 150   │ 2024-01-15 10:00  │
│ 12346  │ USB Keyboard    │ 49.99   │ 75    │ 2024-01-15 09:30  │
│ 12347  │ Monitor Stand   │ 89.99   │ 200   │ 2024-01-14 15:00  │
└────────┴─────────────────┴─────────┴───────┴───────────────────┘

-- User profiles table
┌────────────────────────────────────────────────────────────────────────────┐
│                           user_profiles                                     │
├─────────┬───────────┬─────────────────────┬──────────┬────────────────────┤
│ user_id │ name      │ email               │ tier     │ last_login         │
├─────────┼───────────┼─────────────────────┼──────────┼────────────────────┤
│ 789     │ John Doe  │ john@example.com    │ premium  │ 2024-01-15 10:30   │
│ 790     │ Jane Smith│ jane@example.com    │ basic    │ 2024-01-15 08:15   │
└─────────┴───────────┴─────────────────────┴──────────┴────────────────────┘

-- ⚠️ Problem: Every SELECT requires disk I/O + index lookup
SELECT * FROM products WHERE id = 12345;  -- 5-50ms
```

> **💡 Key Difference:** Redis stores the same data in RAM with O(1) access. No disk I/O, no query planning, no index traversal.

#### Legacy Approach: Direct Database Queries
```
User Request → Application → SQL Database (10-100ms) → Response
                            ↓
                      Disk I/O + Query Planning + Index Scan
```

#### Redis Approach: Cache Layer
```
User Request → Application → Redis (< 1ms) → Response
                   ↓ (cache miss only)
              SQL Database
```

#### Why Legacy is Slow/Complicated
| Problem | Legacy (SQL Direct) | Redis Solution |
|---------|---------------------|----------------|
| Latency | 10-100ms per query | < 1ms per query |
| DB Load | Every request hits DB | 80-95% cache hit rate |
| Scaling | Expensive vertical scaling | Horizontal sharding |
| Complexity | Query optimization needed | Simple key-value |

#### 🏆 Customer Success: DoorDash
- **38% decrease in Redis latencies** for ML model serving
- **<1ms per feature read** for real-time recommendations

---

### 2. 📊 Session Management

| Aspect | Description |
|--------|-------------|
| **What it does** | Stores user session data (login state, preferences, cart) with automatic expiration |
| **How Redis does it** | Session ID as key, JSON/Hash as value, TTL for auto-cleanup |
| **Data Structures** | Hashes (user data), Strings (session tokens) |

#### 📦 What's Actually Stored in Redis
```redis
# User session (Hash structure)
HSET session:abc123def456
     user_id "12345"
     username "johndoe"
     email "john@example.com"
     role "admin"
     login_time "2024-01-15T09:00:00Z"
     last_activity "2024-01-15T10:45:00Z"
     ip_address "192.168.1.100"
     user_agent "Mozilla/5.0..."
     preferences '{"theme":"dark","language":"en"}'
EXPIRE session:abc123def456 3600  # 1 hour TTL

# Shopping cart (Hash)
HSET cart:session:abc123def456
     item:SKU001 '{"qty":2,"price":29.99,"name":"Widget"}'
     item:SKU002 '{"qty":1,"price":99.99,"name":"Gadget"}'
     coupon_code "SAVE20"
     subtotal "159.97"
EXPIRE cart:session:abc123def456 86400  # 24 hour TTL

# CSRF token (String with short TTL)
SET csrf:abc123def456 "x7k9m2p4" EX 900  # 15 minutes

# Remember-me token (String)
SET remember:user:12345 "longLivedToken789" EX 2592000  # 30 days
```

#### 🗄️ What's Stored in Legacy Database (PostgreSQL/MySQL)
```sql
-- Sessions table (every page load = database query)
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                    sessions                                             │
├──────────────────┬─────────┬───────────────────────────────────────────────────────────┤
│ session_id       │ user_id │ data (BLOB/JSON)                                          │
├──────────────────┼─────────┼───────────────────────────────────────────────────────────┤
│ abc123def456     │ 12345   │ {"username":"johndoe","role":"admin","prefs":{...}}       │
│ xyz789ghi012     │ 67890   │ {"username":"janesmith","role":"user","prefs":{...}}      │
└──────────────────┴─────────┴───────────────────────────────────────────────────────────┘
│ expires_at       │ last_accessed     │ ip_address      │ user_agent                    │
├──────────────────┼───────────────────┼─────────────────┼───────────────────────────────┤
│ 2024-01-15 11:00 │ 2024-01-15 10:45  │ 192.168.1.100   │ Mozilla/5.0...                │
│ 2024-01-15 12:00 │ 2024-01-15 11:30  │ 10.0.0.50       │ Chrome/120...                 │
└──────────────────┴───────────────────┴─────────────────┴───────────────────────────────┘

-- Shopping carts table (separate table, requires JOIN)
┌─────────────────────────────────────────────────────────────────────────────┐
│                              shopping_carts                                  │
├──────────────────┬──────────┬─────┬─────────┬───────────────────────────────┤
│ session_id       │ sku      │ qty │ price   │ added_at                      │
├──────────────────┼──────────┼─────┼─────────┼───────────────────────────────┤
│ abc123def456     │ SKU001   │ 2   │ 29.99   │ 2024-01-15 10:30:00           │
│ abc123def456     │ SKU002   │ 1   │ 99.99   │ 2024-01-15 10:35:00           │
│ xyz789ghi012     │ SKU003   │ 3   │ 15.00   │ 2024-01-15 11:00:00           │
└──────────────────┴──────────┴─────┴─────────┴───────────────────────────────┘

-- ⚠️ Problems:
-- 1. Every page load requires: SELECT * FROM sessions WHERE session_id = ?
-- 2. Cart requires: SELECT * FROM shopping_carts WHERE session_id = ?
-- 3. Must manually delete expired sessions with cron job:
--    DELETE FROM sessions WHERE expires_at < NOW();  -- Can lock table!
```

> **💡 Key Difference:** Redis combines session + cart in one namespace with automatic TTL expiration. No cleanup jobs needed.

#### Legacy Approach: Database Sessions
```
Each Page Load:
1. Query: SELECT * FROM sessions WHERE id = ?  (5-20ms)
2. Deserialize session data                     (1-2ms)
3. Update last_accessed timestamp               (5-10ms)
─────────────────────────────────────────────────────────
Total: 11-32ms per page load
```

#### Redis Approach
```
Each Page Load:
1. HGETALL session:{id}                         (< 0.5ms)
2. EXPIRE session:{id} 3600                     (< 0.1ms)
─────────────────────────────────────────────────────────
Total: < 1ms per page load
```

#### Why Legacy is Slow/Complicated
| Problem | Legacy (DB Sessions) | Redis Solution |
|---------|----------------------|----------------|
| Latency | 11-32ms per page | < 1ms per page |
| Lock Contention | Session table locks | Lock-free operations |
| Cleanup | Cron jobs to purge expired | Automatic TTL expiration |
| Serialization | Complex ORM mapping | Native Hash support |

---

### 3. 🏆 Real-Time Leaderboards

| Aspect | Description |
|--------|-------------|
| **What it does** | Maintains ranked lists of players/users with instant updates and range queries |
| **How Redis does it** | Sorted Sets (ZSET) with O(log N) insert/update and O(log N + M) range queries |
| **Data Structures** | Sorted Sets (ZADD, ZRANK, ZRANGE, ZINCRBY) |

#### 📦 What's Actually Stored in Redis
```redis
# Global leaderboard (Sorted Set: member → score)
ZADD leaderboard:global 15000 "player:alice"
ZADD leaderboard:global 14500 "player:bob"  
ZADD leaderboard:global 14200 "player:charlie"
ZADD leaderboard:global 13800 "player:diana"

# Result: leaderboard:global
#   "player:alice"   → 15000 (rank #1)
#   "player:bob"     → 14500 (rank #2)
#   "player:charlie" → 14200 (rank #3)
#   "player:diana"   → 13800 (rank #4)

# Weekly leaderboard (separate sorted set)
ZADD leaderboard:week:2024-03 5000 "player:alice"
ZADD leaderboard:week:2024-03 5200 "player:bob"

# Player metadata (Hash - linked by player ID)
HSET player:alice username "Alice123" avatar "alice.png" country "US" level 42

# Tournament leaderboard
ZADD tournament:summer2024 2500 "team:dragons"
ZADD tournament:summer2024 2400 "team:phoenix"
```

#### 🗄️ What's Stored in Legacy Database (PostgreSQL/MySQL)
```sql
-- Players table with score column
┌───────────────────────────────────────────────────────────────────────────┐
│                              players                                       │
├─────────┬───────────┬────────┬─────────────────┬────────────┬─────────────┤
│ id      │ username  │ score  │ avatar          │ country    │ level       │
├─────────┼───────────┼────────┼─────────────────┼────────────┼─────────────┤
│ 1       │ Alice123  │ 15000  │ alice.png       │ US         │ 42          │
│ 2       │ Bob99     │ 14500  │ bob.png         │ UK         │ 38          │
│ 3       │ Charlie   │ 14200  │ charlie.png     │ DE         │ 35          │
│ ...     │ ...       │ ...    │ ...             │ ...        │ ...         │
│ 1000000 │ Player999 │ 100    │ default.png     │ JP         │ 1           │
└─────────┴───────────┴────────┴─────────────────┴────────────┴─────────────┘

-- ⚠️ To get player's rank (requires scanning ALL rows):
SELECT COUNT(*) + 1 AS rank 
FROM players 
WHERE score > (SELECT score FROM players WHERE username = 'Bob99');
-- With 1M players: 500ms - 2 seconds!

-- ⚠️ To get top 10 (requires sorting entire table):
SELECT * FROM players ORDER BY score DESC LIMIT 10;
-- Even with index: 50-200ms for millions of rows

-- ⚠️ To update score and recalculate rank:
UPDATE players SET score = score + 50 WHERE id = 2;
-- Then re-query to get new rank... another 500ms+
```

> **💡 Key Difference:** Redis Sorted Set maintains rank order automatically. `ZRANK` is O(log N), not O(N). Updating score with `ZINCRBY` atomically re-ranks.

#### Legacy Approach: SQL Ranking
```sql
-- Get leaderboard position (full table scan required)
SELECT COUNT(*) + 1 AS rank 
FROM players 
WHERE score > (SELECT score FROM players WHERE id = ?);

-- Get top 10 (requires sorting millions of rows)
SELECT * FROM players ORDER BY score DESC LIMIT 10;
```

#### Redis Approach
```redis
ZADD leaderboard 1500 "player:123"     -- Add/update score
ZRANK leaderboard "player:123"          -- Get rank instantly
ZREVRANGE leaderboard 0 9 WITHSCORES   -- Top 10 instantly
ZINCRBY leaderboard 50 "player:123"    -- Increment score
```

#### Why Legacy is Slow/Complicated
| Problem | Legacy (SQL) | Redis Solution |
|---------|--------------|----------------|
| Update Rank | O(N) - full scan | O(log N) |
| Get Rank | O(N) - COUNT query | O(1) |
| Top N | O(N log N) - full sort | O(log N + M) |
| Concurrent Updates | Lock contention | Atomic operations |
| Millions of Users | 500ms+ latency | < 1ms latency |

#### 🏆 Customer Success: MrQ Gaming
- **Scaled personalized gaming experiences** to millions of players
- **Real-time rank updates** without database bottlenecks

---

### 4. ⏱️ Time-Series Data (RedisTimeSeries)

| Aspect | Description |
|--------|-------------|
| **What it does** | Stores and queries time-stamped data (metrics, IoT, financial OHLCV) with automatic downsampling |
| **How Redis does it** | RedisTimeSeries module with compaction rules, aggregations, and range queries |
| **Commands** | TS.ADD, TS.RANGE, TS.MRANGE, TS.CREATERULE |

#### 📦 What's Actually Stored in Redis
```redis
# Sensor temperature readings with labels (TimeSeries)
TS.CREATE sensor:temp:floor1
    RETENTION 86400000
    DUPLICATE_POLICY LAST
    LABELS location "floor1" type "temperature" unit "celsius"

TS.ADD sensor:temp:floor1 * 22.5
# → Stored: timestamp=1705312800000, value=22.5

# Multiple readings per second for high-frequency data
TS.ADD sensor:temp:floor1 1705312800001 22.6
TS.ADD sensor:temp:floor1 1705312800002 22.7
TS.ADD sensor:temp:floor1 1705312800003 22.5

# Stock ticker price history (financial time-series)
TS.CREATE ticker:AAPL:price
    RETENTION 604800000
    LABELS symbol "AAPL" market "nasdaq"

TS.ADD ticker:AAPL:price * 185.50
TS.ADD ticker:AAPL:price * 185.75
TS.ADD ticker:AAPL:price * 185.60

# Automatic downsampling rule (1-min averages)
TS.CREATERULE sensor:temp:floor1 sensor:temp:floor1:1min
    AGGREGATION avg 60000

# Query with aggregation (no GROUP BY needed!)
TS.RANGE sensor:temp:floor1 - + AGGREGATION avg 60000

# Server metrics (CPU, memory, network)
TS.ADD metrics:cpu:server1 * 45.2
TS.ADD metrics:memory:server1 * 78.5
TS.ADD metrics:network:server1 * 1024567
```

#### 🗄️ What's Stored in Legacy Database (PostgreSQL/InfluxDB)
```sql
-- Traditional time-series table (bloats quickly!)
┌────────────────────────────────────────────────────────────────────────────────┐
│                              sensor_readings                                    │
├─────────┬───────────────────────────┬─────────┬──────────┬─────────┬───────────┤
│ id      │ timestamp                 │ sensor  │ location │ value   │ unit      │
├─────────┼───────────────────────────┼─────────┼──────────┼─────────┼───────────┤
│ 1       │ 2024-01-15 10:00:00.001   │ temp-1  │ floor1   │ 22.5    │ celsius   │
│ 2       │ 2024-01-15 10:00:00.002   │ temp-1  │ floor1   │ 22.6    │ celsius   │
│ 3       │ 2024-01-15 10:00:00.003   │ temp-1  │ floor1   │ 22.7    │ celsius   │
│ ...     │ ...                       │ ...     │ ...      │ ...     │ ...       │
│ 86400000│ 2024-01-16 10:00:00.000   │ temp-1  │ floor1   │ 23.1    │ celsius   │
└─────────┴───────────────────────────┴─────────┴──────────┴─────────┴───────────┘
-- ⚠️ 1 reading/ms = 86.4M rows/day per sensor!

-- Aggregation query (expensive GROUP BY):
SELECT 
    DATE_TRUNC('minute', timestamp) AS bucket,
    AVG(value) AS avg_temp
FROM sensor_readings
WHERE sensor = 'temp-1' 
    AND timestamp BETWEEN '2024-01-15 10:00:00' AND '2024-01-15 11:00:00'
GROUP BY DATE_TRUNC('minute', timestamp)
ORDER BY bucket;
-- ⚠️ Full scan of millions of rows: 2-10 seconds!

-- Must run scheduled jobs for downsampling:
INSERT INTO sensor_readings_hourly 
SELECT DATE_TRUNC('hour', timestamp), sensor, AVG(value)
FROM sensor_readings
GROUP BY 1, 2;
-- ⚠️ ETL complexity, data freshness lag
```

> **💡 Key Difference:** RedisTimeSeries stores data in compressed chunks with automatic downsampling rules. No ETL jobs, instant aggregation queries.

#### Legacy Approach: SQL Time-Series
```sql
-- Insert metric (requires index maintenance)
INSERT INTO metrics (timestamp, value, sensor_id) VALUES (NOW(), 23.5, 'temp-1');

-- Query last hour with 1-minute aggregation (expensive!)
SELECT 
  DATE_TRUNC('minute', timestamp) as bucket,
  AVG(value) as avg_value
FROM metrics 
WHERE sensor_id = 'temp-1' 
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY DATE_TRUNC('minute', timestamp)
ORDER BY bucket;
```

#### Redis TimeSeries Approach
```redis
TS.ADD sensor:temp-1 * 23.5                          -- Auto-timestamp
TS.RANGE sensor:temp-1 - + AGGREGATION avg 60000   -- 1-min aggregates
TS.CREATERULE sensor:temp-1 sensor:temp-1:hourly AGGREGATION avg 3600000
```

#### Why Legacy is Slow/Complicated
| Problem | Legacy (SQL) | Redis TimeSeries |
|---------|--------------|------------------|
| Insert Rate | ~10K/sec with indexes | 100K+/sec |
| Aggregation Query | Full scan + GROUP BY | Pre-computed |
| Storage Efficiency | Rows + indexes bloat | Compressed chunks |
| Downsampling | ETL jobs needed | Automatic compaction |
| Data Retention | Manual cleanup | Auto-expiration rules |

---

### 5. 📨 Real-Time Messaging (Pub/Sub & Streams)

| Aspect | Description |
|--------|-------------|
| **What it does** | Enables real-time communication between services with guaranteed delivery and consumer groups |
| **How Redis does it** | Pub/Sub for fire-and-forget, Streams for persistent message queues |
| **Data Structures** | Pub/Sub (PUBLISH/SUBSCRIBE), Streams (XADD/XREAD/XREADGROUP) |

#### 📦 What's Actually Stored in Redis
```redis
# Stream entry (persistent, ordered log)
XADD orders:new * 
     order_id "ORD-12345"
     customer_id "CUST-789"
     product "widget-pro"
     quantity "5"
     total "149.95"
     status "pending"

# Result: 1705312800123-0 → {order_id: "ORD-12345", ...}

# Chat room stream (real-time messaging)
XADD chat:room:123 *
     user_id "user:456"
     username "johndoe"
     message "Hello everyone!"
     type "text"

# Notification stream (multi-tenant)
XADD notifications:user:789 *
     type "order_shipped"
     title "Your order is on the way!"
     data '{"tracking":"1Z999AA1"}'
     read "false"

# Consumer group for parallel processing
XGROUP CREATE orders:new order_processors $ MKSTREAM

# Pub/Sub channel (ephemeral, fire-and-forget)
PUBLISH events:price_update '{"symbol":"AAPL","price":185.50}'
PUBLISH events:alerts '{"type":"fraud","account":"ACC-123"}'

# Stream consumer pending entries (for recovery)
XPENDING orders:new order_processors
# → Shows which messages are being processed by which consumer
```

#### 🗄️ What's Stored in Legacy Database (PostgreSQL/MySQL)
```sql
-- Message queue table (polling nightmare!)
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                    message_queue                                          │
├─────────┬───────────────┬───────────────────────────────────────────────┬────────────────┤
│ id      │ channel       │ message (JSON)                                │ created_at     │
├─────────┼───────────────┼───────────────────────────────────────────────┼────────────────┤
│ 1       │ orders        │ {"order_id":"ORD-12345","total":149.95}       │ 10:00:00.001   │
│ 2       │ orders        │ {"order_id":"ORD-12346","total":299.99}       │ 10:00:00.050   │
│ 3       │ notifications │ {"type":"alert","msg":"Low stock"}            │ 10:00:00.100   │
└─────────┴───────────────┴───────────────────────────────────────────────┴────────────────┘
│ processed │ processed_by  │ processed_at    │ retry_count │ error_message              │
├───────────┼───────────────┼─────────────────┼─────────────┼────────────────────────────┤
│ false     │ NULL          │ NULL            │ 0           │ NULL                       │
│ true      │ worker-1      │ 10:00:00.150    │ 0           │ NULL                       │
│ false     │ worker-2      │ NULL            │ 2           │ Timeout on attempt 2       │
└───────────┴───────────────┴─────────────────┴─────────────┴────────────────────────────┘

-- ⚠️ Consumer must poll continuously:
WHILE true DO
    SELECT * FROM message_queue 
    WHERE channel = 'orders' AND processed = false
    ORDER BY created_at LIMIT 10
    FOR UPDATE SKIP LOCKED;  -- Lock rows to prevent double-processing
    
    -- Process messages...
    
    UPDATE message_queue SET processed = true WHERE id IN (...);
    
    SLEEP(0.1);  -- 100ms polling interval = 100ms minimum latency!
END;

-- ⚠️ Dead letter handling requires manual logic
-- ⚠️ Consumer groups require custom implementation
-- ⚠️ Table grows unbounded until you run cleanup jobs
```

> **💡 Key Difference:** Redis Streams push messages instantly (no polling), have built-in consumer groups, automatic message acknowledgment, and don't require cleanup.

#### Legacy Approach: Database Polling
```
Producer:
INSERT INTO message_queue (channel, message, created_at) VALUES (?, ?, NOW());

Consumer (polling every 100ms):
SELECT * FROM message_queue WHERE channel = ? AND processed = false ORDER BY created_at LIMIT 10;
UPDATE message_queue SET processed = true WHERE id IN (...);
```

#### Redis Streams Approach
```redis
XADD orders * customer_id 123 item "widget" qty 5    -- Produce
XREADGROUP GROUP workers consumer-1 BLOCK 0 STREAMS orders >  -- Consume
XACK orders workers 1526569495631-0                   -- Acknowledge
```

#### Why Legacy is Slow/Complicated
| Problem | Legacy (DB Polling) | Redis Streams |
|---------|---------------------|---------------|
| Latency | 100ms polling interval | Instant push |
| DB Load | Continuous queries | Zero polling |
| Delivery Guarantee | Complex transactions | Built-in ACK |
| Consumer Groups | Custom implementation | Native support |
| Message Backpressure | Table bloat | Auto-trimming |

---

### 6. 🔐 Rate Limiting

| Aspect | Description |
|--------|-------------|
| **What it does** | Controls API request rates per user/IP to prevent abuse and ensure fair usage |
| **How Redis does it** | Atomic counters with TTL, or sliding window with Sorted Sets |
| **Data Structures** | Strings (INCR + EXPIRE), Sorted Sets (sliding window) |

#### 📦 What's Actually Stored in Redis
```redis
# Simple counter per minute (String with TTL)
SET ratelimit:api:user:123:1705312800 "45" EX 60
# → User 123 has made 45 requests in current window

# API key rate limit counter
INCR ratelimit:apikey:sk_live_abc123
# → Returns current count, first call sets to 1
EXPIRE ratelimit:apikey:sk_live_abc123 60
# → Auto-expires after 60 seconds

# Sliding window rate limit (Sorted Set)
# Store each request timestamp as member, timestamp as score
ZADD ratelimit:sliding:user:123 1705312800.123 "req:uuid-abc"
ZADD ratelimit:sliding:user:123 1705312800.456 "req:uuid-def"
ZADD ratelimit:sliding:user:123 1705312800.789 "req:uuid-ghi"

# Count requests in last 60 seconds
ZCOUNT ratelimit:sliding:user:123 1705312740 1705312800
# → Returns 3

# Remove old entries
ZREMRANGEBYSCORE ratelimit:sliding:user:123 0 1705312740

# IP-based rate limit with quota info (Hash)
HSET ratelimit:ip:192.168.1.1
     requests 250
     limit 1000
     window_start "1705312800"
     blocked "false"
EXPIRE ratelimit:ip:192.168.1.1 3600

# Distributed rate limit (multiple API instances)
# Using Lua script for atomicity across cluster
```

#### 🗄️ What's Stored in Legacy Database (PostgreSQL/MySQL)
```sql
-- Rate limits table
┌──────────────────────────────────────────────────────────────────────────────┐
│                                rate_limits                                    │
├─────────┬────────────────────┬─────────┬───────┬───────────────────────────┤
│ user_id │ window_start       │ count   │ limit │ blocked_until             │
├─────────┼────────────────────┼─────────┼───────┼───────────────────────────┤
│ 123     │ 2024-01-15 10:00   │ 45      │ 100   │ NULL                      │
│ 456     │ 2024-01-15 10:00   │ 101     │ 100   │ 2024-01-15 10:05:00       │
│ 789     │ 2024-01-15 10:00   │ 23      │ 100   │ NULL                      │
│ 123     │ 2024-01-15 09:00   │ 87      │ 100   │ NULL                      │ ← old window
│ 456     │ 2024-01-15 09:00   │ 92      │ 100   │ NULL                      │ ← old window
└─────────┴────────────────────┴─────────┴───────┴───────────────────────────┘

-- ⚠️ Each request requires transactional read-modify-write:
BEGIN TRANSACTION;
    SELECT count FROM rate_limits 
    WHERE user_id = 123 AND window_start = '2024-01-15 10:00'
    FOR UPDATE;  -- Lock row!
    
    -- If count < limit:
    UPDATE rate_limits SET count = count + 1 
    WHERE user_id = 123 AND window_start = '2024-01-15 10:00';
COMMIT;
-- ⚠️ 5-20ms per request, locks cause contention at high traffic!

-- ⚠️ Must clean up old windows periodically:
DELETE FROM rate_limits WHERE window_start < NOW() - INTERVAL '1 hour';
-- Can lock table during high traffic!

-- ⚠️ Sliding window requires storing every request:
┌────────────────────────────────────────────────────────────┐
│                      request_log                            │
├─────────┬───────────────────────────┬──────────────────────┤
│ user_id │ timestamp                 │ endpoint             │
├─────────┼───────────────────────────┼──────────────────────┤
│ 123     │ 2024-01-15 10:00:00.123   │ /api/orders          │
│ 123     │ 2024-01-15 10:00:00.456   │ /api/products        │
│ 123     │ 2024-01-15 10:00:00.789   │ /api/orders          │
└─────────┴───────────────────────────┴──────────────────────┘
-- Millions of rows per day!
```

> **💡 Key Difference:** Redis INCR is atomic and lock-free. TTL auto-expires old data. No cleanup jobs needed.

#### Legacy Approach: Database Counters
```sql
-- Check and increment (requires transaction)
BEGIN;
SELECT count FROM rate_limits WHERE user_id = ? AND window_start = ?;
-- If under limit:
UPDATE rate_limits SET count = count + 1 WHERE user_id = ? AND window_start = ?;
COMMIT;
```

#### Redis Approach (Sliding Window)
```redis
-- Atomic check and increment
local key = "ratelimit:" .. user_id
local current = redis.call("INCR", key)
if current == 1 then redis.call("EXPIRE", key, 60) end
return current <= 100
```

#### Why Legacy is Slow/Complicated
| Problem | Legacy (SQL) | Redis Solution |
|---------|--------------|----------------|
| Atomicity | Requires transactions | Native atomic ops |
| Latency | 5-20ms per check | < 0.5ms per check |
| Cleanup | Cron jobs | Automatic TTL |
| Distributed | Complex locking | Single-threaded atomic |

---

### 7. 🔍 Deduplication (RedisBloom)

| Aspect | Description |
|--------|-------------|
| **What it does** | Prevents duplicate processing of events/messages with memory-efficient probabilistic data structures |
| **How Redis does it** | Bloom Filters for "definitely not seen" checks, Cuckoo Filters for deletable entries |
| **Commands** | BF.ADD, BF.EXISTS, CF.ADD, CF.EXISTS |

#### 📦 What's Actually Stored in Redis
```redis
# Bloom Filter for message deduplication
# (probabilistic, ~10 bits per element)
BF.RESERVE seen_messages 0.001 10000000
# → Reserve filter for 10M items with 0.1% false positive rate

BF.ADD seen_messages "msg:order:12345"
BF.ADD seen_messages "msg:order:12346"
BF.ADD seen_messages "msg:payment:789"

# Check before processing
BF.EXISTS seen_messages "msg:order:12345"
# → 1 (probably seen, don't process again)
BF.EXISTS seen_messages "msg:order:99999"
# → 0 (definitely not seen, safe to process)

# Cuckoo Filter (supports deletion)
CF.RESERVE unique_visitors 1000000

CF.ADD unique_visitors "user:123:2024-01-15"
CF.ADD unique_visitors "user:456:2024-01-15"
CF.DEL unique_visitors "user:123:2024-01-15"  # Deletable!

# Email deduplication (prevent double-sends)
BF.ADD emails_sent "campaign:jan:user:12345"
BF.EXISTS emails_sent "campaign:jan:user:12345"
# → 1 (already sent, skip)

# Event stream deduplication (idempotency)
BF.MADD event_ids 
     "evt:abc123" 
     "evt:def456" 
     "evt:ghi789"
# → Bulk add for batch processing

# Storage comparison:
# Bloom Filter: 10M items = ~12 MB
# SQL Table: 10M items = ~500 MB (with indexes)
```

#### Legacy Approach: Database Lookup
```sql
-- Check if message was processed
SELECT 1 FROM processed_messages WHERE message_id = ?;
-- If not found, insert
INSERT INTO processed_messages (message_id, processed_at) VALUES (?, NOW());
```

#### Redis Bloom Filter Approach
```redis
BF.ADD seen_messages "msg:abc123"   -- Add to filter (O(k) - k hash functions)
BF.EXISTS seen_messages "msg:xyz"    -- Check existence (O(k))
```

#### Why Legacy is Slow/Complicated
| Problem | Legacy (SQL) | Redis Bloom |
|---------|--------------|-------------|
| Memory per Entry | 50-100 bytes | ~10 bits |
| 1B Entries Storage | 50-100 GB | ~1.2 GB |
| Lookup Time | Index scan (1-5ms) | O(k) hashes (< 0.1ms) |
| Index Maintenance | Expensive | None |

---

### 8. 🔎 Full-Text Search (RediSearch)

| Aspect | Description |
|--------|-------------|
| **What it does** | Real-time full-text search with scoring, faceting, autocomplete, and fuzzy matching |
| **How Redis does it** | RediSearch module with inverted indexes, stemming, phonetic matching, and field weighting |
| **Commands** | FT.CREATE, FT.SEARCH, FT.AGGREGATE, FT.SUGADD |

#### 📦 What's Actually Stored in Redis
```redis
# Product documents (Hash - automatically indexed)
HSET product:1001
     name "Wireless Bluetooth Headphones"
     description "Premium noise-cancelling over-ear headphones"
     price 149.99
     category "electronics"
     brand "SoundMax"
     stock 250
     rating 4.7

HSET product:1002
     name "Wireless Gaming Mouse"
     description "RGB gaming mouse with 16000 DPI"
     price 79.99
     category "electronics"
     brand "GamePro"
     stock 500
     rating 4.5

# Search index definition (stored as metadata)
FT.CREATE products ON HASH PREFIX 1 product:
    SCHEMA 
        name TEXT WEIGHT 5.0 SORTABLE
        description TEXT
        price NUMERIC SORTABLE
        category TAG
        brand TAG
        rating NUMERIC SORTABLE

# Autocomplete suggestions (separate suggestion dictionary)
FT.SUGADD product_suggestions "wireless headphones" 100
FT.SUGADD product_suggestions "wireless mouse" 95
FT.SUGADD product_suggestions "wireless keyboard" 85

# Get suggestions as user types
FT.SUGGET product_suggestions "wire" FUZZY MAX 5
# → ["wireless headphones", "wireless mouse", "wireless keyboard"]
```

#### 🗄️ What's Stored in Legacy Systems (SQL + Elasticsearch)
```sql
-- Products table (PostgreSQL/MySQL)
┌────────────────────────────────────────────────────────────────────────────────────┐
│                                    products                                         │
├─────────┬────────────────────────────────┬───────────────────────────────┬─────────┤
│ id      │ name                           │ description                   │ price   │
├─────────┼────────────────────────────────┼───────────────────────────────┼─────────┤
│ 1001    │ Wireless Bluetooth Headphones  │ Premium noise-cancelling...   │ 149.99  │
│ 1002    │ Wireless Gaming Mouse          │ RGB gaming mouse with...      │ 79.99   │
│ 1003    │ Wired USB Keyboard             │ Mechanical keyboard...        │ 89.99   │
└─────────┴────────────────────────────────┴───────────────────────────────┴─────────┘

-- ⚠️ Full-text search with LIKE (terrible performance):
SELECT * FROM products 
WHERE name LIKE '%wireless%' OR description LIKE '%wireless%';
-- Full table scan: 100ms - 5 seconds on large tables!

-- ⚠️ With PostgreSQL full-text (better, but complex):
SELECT * FROM products 
WHERE to_tsvector('english', name || ' ' || description) @@ to_tsquery('wireless');
-- Requires: CREATE INDEX idx_fts ON products USING GIN(to_tsvector('english', name || ' ' || description));
-- Still 10-50ms, no fuzzy matching, complex syntax
```

```json
// Elasticsearch document (separate system to maintain!)
{
  "_index": "products",
  "_id": "1001",
  "_source": {
    "name": "Wireless Bluetooth Headphones",
    "description": "Premium noise-cancelling over-ear headphones",
    "price": 149.99,
    "category": "electronics",
    "brand": "SoundMax"
  }
}

// ⚠️ Data sync problem:
// 1. Product updated in PostgreSQL
// 2. CDC pipeline picks up change (100ms - 5 sec delay)
// 3. Elasticsearch indexes document (50ms - 500ms)
// 4. User searches - might see stale data!

// ⚠️ Operational overhead:
// - Elasticsearch cluster (3+ nodes for HA)
// - Kibana for monitoring
// - Logstash/Debezium for CDC
// - Separate backup strategy
```

> **💡 Key Difference:** RediSearch indexes data in-place (same system as cache/sessions). Zero sync lag, single system to maintain.

#### How It Works
```redis
# Create search index
FT.CREATE products ON HASH PREFIX 1 product: 
  SCHEMA name TEXT WEIGHT 5.0 
         description TEXT 
         price NUMERIC SORTABLE
         category TAG

# Search with filters
FT.SEARCH products "@name:wireless @category:{electronics} @price:[0 100]"
  SORTBY price ASC
  LIMIT 0 10
```

#### Legacy Approach: SQL LIKE + Elasticsearch
```sql
-- SQL: Slow full table scan
SELECT * FROM products WHERE name LIKE '%wireless%' AND category = 'electronics';

-- Or: Maintain separate Elasticsearch cluster
-- Problem: Data sync lag, operational complexity
```

#### Why Legacy is Slow/Complicated
| Problem | SQL LIKE | Elasticsearch | RediSearch |
|---------|----------|---------------|------------|
| Query Speed | Full scan (100ms+) | 10-50ms | < 5ms |
| Real-time Index | Not possible | Near real-time | Instant |
| Operational Cost | Low | High (cluster mgmt) | Low (built-in) |
| Data Sync | N/A | CDC pipeline needed | Automatic |
| Autocomplete | Custom implementation | Additional config | Native FT.SUGADD |
| Faceted Search | Complex GROUP BY | Aggregations | FT.AGGREGATE |

#### Features Comparison
| Feature | SQL | Elasticsearch | RediSearch |
|---------|-----|---------------|------------|
| Fuzzy Matching | ❌ | ✅ | ✅ |
| Stemming | ❌ | ✅ | ✅ |
| Phonetic Search | ❌ | ✅ | ✅ |
| Numeric Ranges | ✅ | ✅ | ✅ |
| Geo Filters | Limited | ✅ | ✅ |
| Vector Search | ❌ | ❌ | ✅ |
| Sub-ms Latency | ❌ | ❌ | ✅ |

---

### 9. 🚨 Real-Time Fraud Detection

| Aspect | Description |
|--------|-------------|
| **What it does** | Detects fraudulent transactions in real-time by analyzing patterns, velocity, and anomalies |
| **How Redis does it** | Combination of rate limiting, pattern matching, ML feature serving, and Bloom filters |
| **Components** | Sorted Sets (velocity), Streams (event log), Bloom (known bad actors), ML features |

#### 📦 What's Actually Stored in Redis
```redis
# Transaction velocity tracking (Sorted Set: score = timestamp)
ZADD transactions:card:1234 1705312800 "txn:abc123"
ZADD transactions:card:1234 1705312900 "txn:def456"
ZADD transactions:card:1234 1705313000 "txn:ghi789"
# → Enables: "How many transactions in last hour?"

# Known bad actors blocklist (Bloom Filter)
BF.ADD blocklist:cards "4111111111111111"
BF.ADD blocklist:ips "192.168.1.100"
BF.ADD blocklist:devices "device:fingerprint:xyz"

# User risk profile (Hash)
HSET user:123:fraud_features
     risk_score "0.23"
     avg_transaction "85.50"
     max_transaction "500.00"
     typical_location "NYC"
     known_devices "3"
     velocity_24h "12"
     last_fraud_check "2024-01-15T10:00:00Z"

# Recent transaction patterns (for anomaly detection)
LPUSH user:123:recent_txns '{"amount":45.99,"merchant":"Amazon","time":"10:00"}'
LTRIM user:123:recent_txns 0 49  # Keep last 50

# Fraud event log (Stream - audit trail)
XADD fraud:events:2024-01-15 *
     txn_id "txn:abc123"
     card_id "1234"
     amount "2500.00"
     decision "BLOCKED"
     reason "velocity_exceeded"
     rule_id "RULE-007"
     confidence "0.95"

# Real-time fraud alerts (Pub/Sub)
PUBLISH fraud:alerts:high '{"card":"1234","reason":"impossible_travel"}'

# Device fingerprint reputation (Sorted Set by trust score)
ZADD device:reputation 0.95 "device:abc123"  # Trusted
ZADD device:reputation 0.15 "device:xyz789"  # Suspicious
```

#### 🗄️ What's Stored in Legacy Database (PostgreSQL/Oracle)
```sql
-- Transaction history table
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                    transactions                                           │
├───────────┬──────────────┬────────────────────────┬─────────┬──────────┬─────────────────┤
│ txn_id    │ card_number  │ timestamp              │ amount  │ merchant │ location        │
├───────────┼──────────────┼────────────────────────┼─────────┼──────────┼─────────────────┤
│ abc123    │ 1234****5678 │ 2024-01-15 10:00:00    │ 45.99   │ Amazon   │ NYC             │
│ def456    │ 1234****5678 │ 2024-01-15 10:01:40    │ 299.99  │ BestBuy  │ NYC             │
│ ghi789    │ 1234****5678 │ 2024-01-15 10:03:20    │ 2500.00 │ Jewelry  │ Miami           │ ← Suspicious!
└───────────┴──────────────┴────────────────────────┴─────────┴──────────┴─────────────────┘

-- ⚠️ Velocity check (count transactions in last hour):
SELECT COUNT(*) FROM transactions 
WHERE card_number = '1234****5678' 
  AND timestamp > NOW() - INTERVAL '1 hour';
-- Index scan: 50-200ms per transaction!
-- At 1000 TPS: 50-200 seconds of DB time per second! 💥

-- Blocklist table (instead of Bloom filter)
┌───────────────────────────────────────────────────────┐
│                    blocklist                           │
├────────────────────────────┬──────────────┬───────────┤
│ value                      │ type         │ reason    │
├────────────────────────────┼──────────────┼───────────┤
│ 4111111111111111           │ card         │ stolen    │
│ 192.168.1.100              │ ip           │ bot       │
│ device:fingerprint:xyz     │ device       │ fraud     │
└────────────────────────────┴──────────────┴───────────┘
-- ⚠️ Lookup: SELECT 1 FROM blocklist WHERE value = ?
-- With 10M entries: 1-5ms per lookup (indexed)
-- Bloom filter: < 0.1ms, 40x less memory!

-- User risk features (computed in batch, stale!)
┌───────────────────────────────────────────────────────────────────────┐
│                        user_risk_profiles                              │
├─────────┬────────────┬──────────────┬─────────────────────────────────┤
│ user_id │ risk_score │ avg_txn_amt  │ computed_at                     │
├─────────┼────────────┼──────────────┼─────────────────────────────────┤
│ 123     │ 0.23       │ 85.50        │ 2024-01-15 00:00:00 (12h ago!)  │
│ 456     │ 0.78       │ 1250.00      │ 2024-01-15 00:00:00             │
└─────────┴────────────┴──────────────┴─────────────────────────────────┘
-- ⚠️ Features computed nightly in batch - fraud happens in real-time!
```

> **💡 Key Difference:** Redis enables **sub-5ms fraud decisions** using Bloom filters (blocklist), Sorted Sets (velocity), and real-time ML features. Legacy batch systems detect fraud hours/days after it happens.

#### How It Works
```
Transaction arrives:
1. Check Bloom Filter: Is card/IP on blocklist?        (< 0.1ms)
2. Check Velocity: How many transactions in last hour? (< 0.5ms)
   → ZCOUNT transactions:card:1234 (now-3600) (now)
3. Get ML Features: User risk profile, device fingerprint (< 1ms)
   → HMGET user:123:features risk_score device_trust avg_amount
4. Check Anomaly: Is amount > 3x user's average?       (computed)
5. Decision: Allow / Block / Review                     (< 0.1ms)
────────────────────────────────────────────────────────────────
Total: < 5ms (vs. 100-500ms with traditional DB)
```

#### Redis Implementation
```redis
# Track transaction velocity (sliding window)
ZADD transactions:card:1234 {timestamp} {txn_id}
ZREMRANGEBYSCORE transactions:card:1234 0 {timestamp-3600}
ZCARD transactions:card:1234  # Count in last hour

# Check against blocklist (Bloom Filter)
BF.EXISTS blocklist:cards "1234-5678-9012-3456"

# Get user risk features
HMGET user:123:features risk_score avg_txn_amount device_fingerprints

# Log event for audit (Streams)
XADD fraud:events * card_id 1234 decision BLOCKED reason "velocity"
```

#### Legacy Approach: Batch Processing + SQL
```sql
-- Check velocity (expensive!)
SELECT COUNT(*) FROM transactions 
WHERE card_id = '1234' AND timestamp > NOW() - INTERVAL '1 hour';

-- Check blocklist (table scan or slow join)
SELECT 1 FROM blocklist WHERE card_number = '1234-5678-9012-3456';

-- Get user profile (another query)
SELECT * FROM user_profiles WHERE user_id = 123;
```

#### Why Legacy is Slow/Complicated
| Problem | Legacy (SQL/Batch) | Redis Real-Time |
|---------|--------------------| ----------------|
| Decision Latency | 100-500ms | < 5ms |
| Velocity Checks | Expensive COUNT(*) | O(log N) ZCOUNT |
| Blocklist Lookup | Index scan | O(k) Bloom filter |
| Pattern Detection | Batch (hourly/daily) | Real-time |
| Scale | DB bottleneck | Horizontal scaling |
| Fraud Window | Hours to detect | Milliseconds |

#### 🏆 Customer Success: TransNexus
- **95% reduction** in fraud detection time
- **20ms** average call processing (robocall prevention)
- **Hundreds of millions** of keys in production
- "Redis is the number-one most important database"

---

### 10. 📍 Geospatial Queries

| Aspect | Description |
|--------|-------------|
| **What it does** | Stores locations and finds nearby points within radius, distance calculations |
| **How Redis does it** | GEO commands using Sorted Sets with geohash encoding |
| **Commands** | GEOADD, GEORADIUS, GEODIST, GEOPOS, GEOSEARCH |

#### 📦 What's Actually Stored in Redis
```redis
# Store locations (GEO - internally uses Sorted Set with geohash)
GEOADD stores:NYC -74.0060 40.7128 "store:manhattan-soho"
GEOADD stores:NYC -73.9857 40.7484 "store:midtown"
GEOADD stores:NYC -73.9654 40.7829 "store:upper-east"

# Driver/delivery locations (real-time updates)
GEOADD drivers:active -74.0000 40.7200 "driver:123"
GEOADD drivers:active -73.9900 40.7300 "driver:456"
GEOADD drivers:active -73.9800 40.7400 "driver:789"
EXPIRE drivers:active 60  # Auto-expire if no update

# Store details with location (Hash + Geo)
HSET store:manhattan-soho
     name "SoHo Flagship Store"
     address "123 Broadway, NY"
     phone "212-555-0100"
     hours "9AM-9PM"
     inventory_zone "zone-a"
GEOADD stores:all -74.0060 40.7128 "store:manhattan-soho"

# Delivery zone polygon (approximated with multiple points)
GEOADD delivery:zone:downtown 
    -74.010 40.710 "corner-sw"
    -74.000 40.710 "corner-se"
    -74.000 40.720 "corner-ne"
    -74.010 40.720 "corner-nw"

# User's saved locations
GEOADD user:123:locations -74.0050 40.7130 "home"
GEOADD user:123:locations -73.9850 40.7480 "work"
GEOADD user:123:locations -73.9700 40.7600 "gym"
```

#### How It Works
```redis
# Add locations
GEOADD restaurants -122.4194 37.7749 "pizza-palace"
GEOADD restaurants -122.4089 37.7837 "burger-barn"
GEOADD restaurants -122.4058 37.7879 "sushi-spot"

# Find restaurants within 2km of user
GEOSEARCH restaurants FROMMEMBER "user-location" BYRADIUS 2 km ASC COUNT 10

# Calculate distance
GEODIST restaurants "pizza-palace" "burger-barn" km
```

#### Legacy Approach: SQL with Haversine
```sql
-- Complex and slow Haversine formula
SELECT *, 
  (6371 * acos(cos(radians(37.7749)) * cos(radians(lat)) 
  * cos(radians(lng) - radians(-122.4194)) 
  + sin(radians(37.7749)) * sin(radians(lat)))) AS distance
FROM restaurants
HAVING distance < 2
ORDER BY distance
LIMIT 10;

-- Or: PostGIS extension (additional complexity)
SELECT * FROM restaurants 
WHERE ST_DWithin(location, ST_MakePoint(-122.4194, 37.7749)::geography, 2000);
```

#### Why Legacy is Slow/Complicated
| Problem | SQL Haversine | PostGIS | Redis GEO |
|---------|---------------|---------|-----------|
| Query Syntax | Complex formula | Extension required | Simple commands |
| Index Type | B-tree (poor for geo) | GiST (specialized) | Geohash (built-in) |
| Latency | 50-200ms | 10-50ms | < 1ms |
| Radius Search | Full calculation | Optimized | O(log N) |
| Setup | None | Extension install | Built-in |
| Real-time Updates | Transaction overhead | Similar | Instant |

#### Use Cases
- 🚗 Ride-sharing: Find nearby drivers
- 🍕 Food delivery: Restaurants in range
- 🏪 Retail: Store locator
- 📱 Social: Friends nearby
- 🚚 Logistics: Fleet tracking

---

### 11. 🔐 Distributed Locks & Coordination

| Aspect | Description |
|--------|-------------|
| **What it does** | Coordinates access to shared resources across distributed systems, prevents race conditions |
| **How Redis does it** | Atomic SET with NX (not exists) and PX (expiration), or Redlock algorithm |
| **Commands** | SET key value NX PX milliseconds, EVAL (Lua scripts) |

#### 📦 What's Actually Stored in Redis
```redis
# Distributed lock (String with NX + PX)
SET lock:order:ORD-12345 "worker:abc:1705312800" NX PX 30000
# → Key: lock identifier
# → Value: unique owner ID (for safe release)
# → NX: Only set if not exists
# → PX 30000: Auto-expire in 30 seconds (prevents deadlocks)

# Multiple resource locks
SET lock:inventory:SKU-789 "worker:xyz:1705312801" NX PX 10000
SET lock:payment:TXN-456 "worker:def:1705312802" NX PX 60000
SET lock:document:DOC-123 "user:john:1705312803" NX PX 300000

# Lock with metadata (Hash - for debugging)
HSET lock:meta:order:ORD-12345
     owner "worker:abc"
     acquired_at "2024-01-15T10:00:00Z"
     purpose "process_payment"
     ttl_ms "30000"
SET lock:order:ORD-12345 "worker:abc" NX PX 30000

# Redlock (distributed lock across multiple Redis nodes)
# Same key set on 3+ independent Redis instances:
SET lock:critical:123 "uuid:abc123" NX PX 30000  # Node 1
SET lock:critical:123 "uuid:abc123" NX PX 30000  # Node 2
SET lock:critical:123 "uuid:abc123" NX PX 30000  # Node 3
# Lock acquired if majority (2+) succeed

# Semaphore (limited concurrent access)
ZADD semaphore:api:expensive 1705312800 "request:123"
ZADD semaphore:api:expensive 1705312801 "request:456"
# Allow max 5 concurrent, check with ZCARD
```

#### How It Works
```redis
# Acquire lock (atomic)
SET lock:resource:123 {unique_id} NX PX 30000
# Returns OK if acquired, nil if already locked

# Release lock (only if we own it - Lua script)
EVAL "if redis.call('get',KEYS[1]) == ARGV[1] then 
        return redis.call('del',KEYS[1]) 
      else return 0 end" 
     1 lock:resource:123 {unique_id}
```

#### Legacy Approach: Database Locking
```sql
-- Pessimistic locking (blocks other transactions)
SELECT * FROM resources WHERE id = 123 FOR UPDATE;
-- Do work...
COMMIT;

-- Or: Optimistic locking with version
UPDATE resources SET data = ?, version = version + 1 
WHERE id = 123 AND version = ?;
```

#### Why Legacy is Slow/Complicated
| Problem | DB Locks | Zookeeper | Redis Locks |
|---------|----------|-----------|-------------|
| Latency | 5-50ms | 10-20ms | < 1ms |
| Setup Complexity | Low | High (cluster) | Low |
| Deadlock Risk | High | Low | Low (TTL) |
| Cross-Service | Limited | Native | Native |
| Auto-Expiration | Manual | Session-based | Native TTL |
| Throughput | ~1K/sec | ~10K/sec | ~100K/sec |

#### Use Cases
- 💳 Payment processing: Prevent double-charge
- 📦 Inventory: Reserve stock atomically
- 🔄 Job scheduling: Single execution guarantee
- 📝 Document editing: Exclusive access
- 🎫 Ticketing: Prevent overselling

---

### 12. 📋 Job Queues & Background Processing

| Aspect | Description |
|--------|-------------|
| **What it does** | Manages background task execution with priorities, retries, and delayed jobs |
| **How Redis does it** | Lists (simple FIFO), Sorted Sets (delayed/priority), Streams (consumer groups) |
| **Patterns** | BRPOP (blocking pop), ZADD (delayed jobs), XREADGROUP (consumer groups) |

#### 📦 What's Actually Stored in Redis
```redis
# Simple job queue (List - FIFO)
LPUSH jobs:email 
    '{"id":"job:001","type":"welcome_email","to":"user@example.com","subject":"Welcome!"}'
LPUSH jobs:email 
    '{"id":"job:002","type":"password_reset","to":"user2@example.com","token":"abc123"}'

# Priority queue (Sorted Set: score = priority, lower = more urgent)
ZADD jobs:priority 1 '{"id":"job:003","type":"fraud_alert","urgent":true}'
ZADD jobs:priority 5 '{"id":"job:004","type":"weekly_report"}'
ZADD jobs:priority 10 '{"id":"job:005","type":"cleanup"}'

# Delayed jobs (Sorted Set: score = execution timestamp)
ZADD jobs:delayed 1705399200 '{"id":"job:006","type":"reminder","user":"123"}'
ZADD jobs:delayed 1705402800 '{"id":"job:007","type":"subscription_renewal"}'
# → job:006 runs at 10:00, job:007 runs at 11:00

# Job with full metadata (Hash)
HSET job:meta:001
     id "job:001"
     type "send_email"
     status "pending"
     created_at "2024-01-15T10:00:00Z"
     retry_count "0"
     max_retries "3"
     payload '{"to":"user@example.com","template":"welcome"}'

# Processing queue (reliable queue pattern)
BRPOPLPUSH jobs:pending jobs:processing 0
# → Atomically moves job from pending to processing

# Failed jobs (for retry or manual review)
LPUSH jobs:failed '{"id":"job:008","error":"SMTP timeout","attempts":3}'

# Job progress tracking
HSET job:progress:001 
     total "100"
     completed "45"
     status "processing"
     current_item "item:46"
```

#### How It Works
```redis
# Simple queue (FIFO)
LPUSH jobs:email '{"to":"user@example.com","subject":"Welcome"}'
BRPOP jobs:email 0  # Worker blocks until job available

# Priority queue (Sorted Set)
ZADD jobs:priority 1 '{"type":"critical","data":"..."}' # Priority 1 (highest)
ZADD jobs:priority 5 '{"type":"normal","data":"..."}'   # Priority 5
BZPOPMIN jobs:priority 0  # Get highest priority job

# Delayed jobs (future execution)
ZADD jobs:delayed {future_timestamp} '{"type":"reminder",...}'
# Worker: ZRANGEBYSCORE jobs:delayed 0 {now} LIMIT 0 1
```

#### Legacy Approach: Database Polling
```sql
-- Poll for jobs (inefficient)
SELECT * FROM jobs WHERE status = 'pending' ORDER BY priority LIMIT 1 FOR UPDATE;
UPDATE jobs SET status = 'processing', worker_id = ? WHERE id = ?;
-- Process...
UPDATE jobs SET status = 'completed' WHERE id = ?;
```

#### Why Legacy is Slow/Complicated
| Problem | DB Polling | RabbitMQ/SQS | Redis Queues |
|---------|------------|--------------|--------------|
| Latency | Polling interval | ~10ms | < 1ms |
| DB Load | Constant queries | None | None |
| Priority Queues | Complex queries | Limited | Native (ZSET) |
| Delayed Jobs | Scheduled queries | Limited | Native (ZADD) |
| Setup | Simple | Complex | Simple |
| Cost | DB resources | Service cost | In-memory |
| Reliability | Transaction overhead | Built-in | Streams + ACK |

#### Popular Libraries Built on Redis
- **Sidekiq** (Ruby): Background job processing
- **Celery** (Python): Distributed task queue
- **Bull** (Node.js): Premium job queue
- **RQ** (Python): Simple job queue

---

### 13. 🔄 Redis Data Integration (RDI) - CDC

| Aspect | Description |
|--------|-------------|
| **What it does** | Automatically syncs data from primary databases to Redis using Change Data Capture (CDC) |
| **How Redis does it** | Captures changes from source DB (Oracle, PostgreSQL, MySQL, MongoDB), transforms, and ingests into Redis |
| **Key Benefit** | Eliminates cache misses and stale data - cache is always "hot" |

#### 📦 What's Actually Stored in Redis
```redis
# RDI automatically transforms and syncs database tables to Redis Hashes
# Source: PostgreSQL table "customers"
# Target: Redis Hash

# Before RDI: Manual cache-aside (stale data risk)
# After RDI: Automatic sync within milliseconds

# Customer record (synced from Oracle/PostgreSQL)
HSET customer:12345
     id "12345"
     name "John Doe"
     email "john@example.com"
     account_type "premium"
     balance "15000.00"
     last_transaction "2024-01-15T14:30:00Z"

# Product catalog (synced from MySQL)
HSET product:SKU-789
     sku "SKU-789"
     name "Wireless Headphones"
     price "149.99"
     stock "250"
     category "electronics"

# Account authorization (synced from core banking)
HSET account:auth:ACC-001
     account_id "ACC-001"
     owner_id "12345"
     permissions "read,write,transfer"
     daily_limit "10000"
     status "active"
```

#### How RDI Works
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Source DB      │     │      RDI        │     │     Redis       │
│  (Oracle/PG/    │────▶│  - Capture CDC  │────▶│  (Always Hot)   │
│   MySQL/Mongo)  │     │  - Transform    │     │                 │
│                 │     │  - Filter       │     │  sub-ms reads   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
      │                                                │
      │ UPDATE customers SET balance = 5000            │
      │ WHERE id = 12345;                              │
      │                                                │
      └──────────── Captured & synced ─────────────────┘
                    in near real-time
```

#### Legacy Approach: Cache-Aside (Manual)
```python
# Problem 1: Cold cache - first request is SLOW
def get_customer(id):
    cached = redis.get(f"customer:{id}")
    if cached:
        return cached  # HIT: fast
    else:
        data = db.query("SELECT * FROM customers WHERE id = ?", id)
        redis.set(f"customer:{id}", data, ex=3600)  # MISS: slow + stale risk
        return data

# Problem 2: Stale data after DB update
db.execute("UPDATE customers SET balance = 5000 WHERE id = 12345")
# Cache still has old value until TTL expires!
```

#### Why Legacy is Slow/Complicated
| Problem | Cache-Aside (Manual) | Redis Data Integration |
|---------|----------------------|------------------------|
| Cold Cache | First request = slow DB query | Pre-fetched, always hot |
| Stale Data | TTL-based, can be stale | Real-time sync via CDC |
| DB Updates | Cache not updated | Automatic sync |
| Implementation | Custom code per table | Declarative config |
| Multiple DBs | Separate pipelines | Unified RDI |
| Consistency | Eventual (TTL-based) | Near real-time |

#### 🏆 Customer Success: Axis Bank
- **4.25x faster response time** with RDI vs. direct DB queries
- **10 million daily users** with stable performance
- **$82,000 saved** by reducing redundant data storage
- **76% faster** overall system performance

---

### 14. 📦 Real-Time Inventory Management

| Aspect | Description |
|--------|-------------|
| **What it does** | Tracks inventory positions across stores/warehouses with real-time updates and geo search |
| **How Redis does it** | Hashes (product data), Sorted Sets (stock levels), Geo (store locations), Search (queries) |
| **Key Features** | ATP (Available-to-Promise), store locator, stock alerts |

#### 📦 What's Actually Stored in Redis
```redis
# Product inventory by location (Hash)
HSET inventory:SKU-123:store:NYC
     sku "SKU-123"
     product_name "Wireless Mouse"
     quantity 45
     reserved 5
     available 40
     last_updated "2024-01-15T10:00:00Z"
     reorder_point 20

# Stock levels for alerting (Sorted Set: store → quantity)
ZADD stock:SKU-123 45 "store:NYC" 120 "store:LA" 0 "store:CHI"

# Store locations for geo search (Geo)
GEOADD stores -74.0060 40.7128 "store:NYC"
GEOADD stores -118.2437 34.0522 "store:LA"
GEOADD stores -87.6298 41.8781 "store:CHI"

# Real-time available-to-promise (ATP)
HSET atp:SKU-123
     total_stock 165
     total_reserved 12
     available_to_promise 153
     backorder_qty 0

# Reservation hold (with TTL - auto-release if not purchased)
SET reservation:SKU-123:cart:ABC "5" EX 900  # 15 min hold
```

#### Why Legacy is Slow/Complicated
| Problem | Legacy (ERP/SQL) | Redis Inventory |
|---------|------------------|-----------------|
| Stock Check | 50-200ms query | < 1ms lookup |
| Geo Search | Complex joins | Native GEOSEARCH |
| Real-time Updates | Batch processing | Instant sync |
| Reservation Holds | Manual cleanup | TTL auto-release |
| Multi-channel | Sync lag | Active-Active |

#### 🏆 Customer Success: Ulta Beauty
- **Sub-millisecond** inventory lookups
- **Omnichannel consistency** across web, mobile, stores
- "We are able to provide accurate inventory information to our customers"

---

### 15. 🔐 Authentication Token Storage

| Aspect | Description |
|--------|-------------|
| **What it does** | Stores JWT/OAuth tokens, refresh tokens, and API keys with automatic expiration |
| **How Redis does it** | Strings with TTL for tokens, Hashes for token metadata, Sets for token revocation |
| **Key Benefit** | Sub-millisecond auth checks, automatic cleanup, instant revocation |

#### 📦 What's Actually Stored in Redis
```redis
# Access token (short-lived)
SET token:access:eyJhbGc... 
    '{"user_id":"12345","scope":"read write","iat":1705312800}'
    EX 3600  # 1 hour

# Refresh token (long-lived)
SET token:refresh:abc123xyz
    '{"user_id":"12345","device":"iPhone-14","issued":"2024-01-15"}'
    EX 2592000  # 30 days

# User's active sessions (Set - for "logout all devices")
SADD user:12345:sessions "session:abc" "session:def" "session:ghi"

# Token blacklist (for immediate revocation)
SADD tokens:revoked "eyJhbGciOiJIUzI1..." "oldToken123..."
EXPIRE tokens:revoked 86400  # Keep for 24h then auto-cleanup

# API key with rate limit info (Hash)
HSET apikey:sk_live_abc123
     owner_id "company:789"
     name "Production API Key"
     created "2024-01-01"
     rate_limit 1000
     current_usage 42
EXPIRE apikey:sk_live_abc123 31536000  # 1 year

# OAuth state (CSRF protection, short TTL)
SET oauth:state:xyz789 '{"redirect":"/dashboard","provider":"google"}' EX 300
```

#### Why Legacy is Slow/Complicated
| Problem | Legacy (SQL) | Redis Tokens |
|---------|--------------|--------------|
| Token Validation | 5-20ms DB query | < 0.5ms |
| Revocation | Table scan | O(1) Set check |
| Cleanup | Scheduled jobs | Automatic TTL |
| Scaling | DB bottleneck | Horizontal sharding |
| Logout All | Complex UPDATE | SMEMBERS + DEL |

---

### 16. 📡 Fast Data Ingest (IoT/Streaming)

| Aspect | Description |
|--------|-------------|
| **What it does** | Captures high-velocity data streams (IoT sensors, logs, events) at millions of ops/sec |
| **How Redis does it** | Streams (persistent log), Pub/Sub (broadcast), Lists (queue), TimeSeries (metrics) |
| **Throughput** | 200M+ operations/second |

#### 📦 What's Actually Stored in Redis
```redis
# IoT sensor data (Stream - persistent, ordered)
XADD sensors:temperature:floor1 *
     sensor_id "temp-001"
     value 72.5
     unit "F"
     timestamp "2024-01-15T10:30:00.123Z"
     
# Result: Stream entry with auto-generated ID
# 1705312200123-0 → {sensor_id: "temp-001", value: "72.5", ...}

# Real-time metrics (TimeSeries)
TS.ADD metrics:cpu:server1 * 45.2
TS.ADD metrics:cpu:server1 * 67.8
TS.ADD metrics:memory:server1 * 78.5

# Event log (Stream with consumer groups)
XADD events:orders *
     event_type "order_placed"
     order_id "ORD-12345"
     customer_id "CUST-789"
     total "299.99"
     items '[{"sku":"ABC","qty":2}]'

# Consumer group for parallel processing
XGROUP CREATE events:orders processors $ MKSTREAM
XREADGROUP GROUP processors worker-1 STREAMS events:orders >

# High-frequency ticker data (Pub/Sub for real-time)
PUBLISH ticker:AAPL '{"price":185.50,"volume":1000,"time":"10:30:01.456"}'

# Batch ingest queue (List)
LPUSH ingest:batch '{"sensor":"001","readings":[72.1,72.3,72.5]}'
```

#### Why Legacy is Slow/Complicated
| Problem | Legacy (Kafka/DB) | Redis Ingest |
|---------|-------------------|--------------|
| Latency | 10-50ms | < 1ms |
| Setup | Complex cluster | Simple |
| Throughput | ~100K/sec | 1M+/sec per node |
| Consumer Groups | Native | Native (Streams) |
| Time-Series | Separate DB | Built-in module |

---

## Redis for AI Use Cases

### 17. 🧠 Semantic Caching (LangCache)

| Aspect | Description |
|--------|-------------|
| **What it does** | Caches LLM responses based on semantic similarity, not exact matches. Returns cached answers for semantically similar questions |
| **How Redis does it** | Stores query embeddings + responses, uses vector search to find similar cached queries |
| **Components** | Embedding model, Vector index (HNSW/FLAT), Similarity threshold |

#### 📦 What's Actually Stored in Redis
```redis
# Semantic cache entry (Hash + Vector)
HSET llm:cache:entry:001
     query "What is the capital of France?"
     response "The capital of France is Paris..."
     model "gpt-4"
     tokens_used 150
     created_at "2024-01-15T10:00:00Z"
     embedding "\x00\x01\x02..."  # 1536-dim vector (binary)

# Vector index for similarity search
FT.CREATE llm_cache_idx ON HASH PREFIX 1 llm:cache:entry:
    SCHEMA 
        query TEXT
        embedding VECTOR HNSW 6 DIM 1536 DISTANCE_METRIC COSINE
```

#### How It Works
```
1. User asks: "What's the weather like today?"
2. Generate embedding vector [0.12, -0.45, 0.78, ...]
3. Search Redis for similar embeddings (cosine similarity > 0.95)
4. If found: Return cached response (< 5ms)
5. If not found: Call LLM ($$$), cache response + embedding
```

#### Legacy Approach: Exact-Match Caching
```python
# Legacy: Only works for EXACT same question
cache_key = hash("What's the weather like today?")
cached = redis.get(cache_key)  # Miss for "How's the weather?"
```

#### Why Legacy Fails
| Problem | Exact-Match Cache | Semantic Cache |
|---------|-------------------|----------------|
| "What's the weather?" vs "How's the weather?" | MISS ❌ | HIT ✅ |
| Spelling variations | MISS ❌ | HIT ✅ |
| Paraphrased questions | MISS ❌ | HIT ✅ |
| Cache Hit Rate | ~20-30% | ~70-90% |
| LLM API Costs | High | 70-90% reduction |

#### Performance Impact
| Metric | Without Semantic Cache | With Redis Semantic Cache |
|--------|------------------------|---------------------------|
| Response Time | 2-10 seconds | < 100ms (15x faster) |
| API Cost per 1000 queries | $0.50-2.00 | $0.05-0.30 |
| Cache Hit Rate | 20-30% | 70-90% |

#### 🏆 Customer Success: Mangoes.ai Healthcare
- **Faster healthcare voice assistant** with LangCache semantic caching
- **Reduced LLM costs** while maintaining response quality

---

### 18. 🔎 Vector Search / RAG (Retrieval-Augmented Generation)

| Aspect | Description |
|--------|-------------|
| **What it does** | Finds semantically similar documents to augment LLM context with relevant knowledge |
| **How Redis does it** | HNSW or FLAT vector indexes with hybrid search (vector + metadata filters) |
| **Commands** | FT.CREATE (index), FT.SEARCH (hybrid query) |

#### 📦 What's Actually Stored in Redis
```redis
# Document chunks with embeddings (Hash + Vector)
HSET doc:chunk:001
     doc_id "10K-2024-Q1"
     chunk_id "001"
     text "Revenue for Q1 2024 was $45.2B, up 12% YoY..."
     source "sec_filings/aapl_10k.pdf"
     page 42
     embedding "\x00\x01\x02..."  # 1536-dim vector (binary)

HSET doc:chunk:002
     doc_id "10K-2024-Q1"
     chunk_id "002"
     text "Operating expenses increased by 8% primarily..."
     source "sec_filings/aapl_10k.pdf"
     page 43
     embedding "\x00\x03\x04..."

# Vector index for semantic search + metadata filtering
FT.CREATE docs_idx ON HASH PREFIX 1 doc:chunk:
    SCHEMA 
        text TEXT
        source TAG
        page NUMERIC
        embedding VECTOR HNSW 6 DIM 1536 DISTANCE_METRIC COSINE

# Hybrid search: semantic + filter by source
FT.SEARCH docs_idx 
    "(@source:{sec_filings*})=>[KNN 5 @embedding $query_vec AS score]"
    PARAMS 2 query_vec "\x00\x01\x02..."
    RETURN 3 text source score
    SORTBY score
```

#### 🗄️ What's Stored in Legacy Systems (PostgreSQL + Pinecone/Milvus)
```sql
-- PostgreSQL: Documents table (no vector support or slow pgvector)
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                    document_chunks                                      │
├───────────┬────────────┬────────────────────────────────────────┬────────┬─────────────┤
│ chunk_id  │ doc_id     │ text                                   │ source │ page        │
├───────────┼────────────┼────────────────────────────────────────┼────────┼─────────────┤
│ 001       │ 10K-2024   │ Revenue for Q1 2024 was $45.2B...      │ aapl.pdf│ 42         │
│ 002       │ 10K-2024   │ Operating expenses increased by 8%... │ aapl.pdf│ 43         │
└───────────┴────────────┴────────────────────────────────────────┴────────┴─────────────┘

-- ⚠️ PostgreSQL with pgvector (slower than Redis):
CREATE TABLE document_embeddings (
    chunk_id TEXT PRIMARY KEY,
    embedding vector(1536)
);
CREATE INDEX ON document_embeddings USING ivfflat (embedding vector_cosine_ops);

SELECT chunk_id, 1 - (embedding <=> $query_vector) AS similarity
FROM document_embeddings
ORDER BY embedding <=> $query_vector
LIMIT 5;
-- ⚠️ 10-100ms per query (vs. <1ms Redis)
-- ⚠️ IVF index needs re-training as data grows
```

```json
// Pinecone/Milvus: Separate vector database
{
  "id": "chunk:001",
  "values": [0.12, -0.45, 0.78, ...],  // 1536 dimensions
  "metadata": {
    "doc_id": "10K-2024-Q1",
    "source": "sec_filings/aapl_10k.pdf",
    "page": 42
  }
}

// ⚠️ Problems with separate vector DB:
// 1. Text stored in PostgreSQL, vectors in Pinecone = 2 systems!
// 2. Must sync data between systems
// 3. Query requires: Pinecone → get IDs → PostgreSQL → get text
// 4. Double the infrastructure cost
// 5. Consistency issues when one system updates before other
```

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     Legacy RAG Architecture (3+ systems!)                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌──────────┐      ┌──────────────┐      ┌──────────────┐                     │
│   │ PostgreSQL│      │   Pinecone   │      │ Elasticsearch│                     │
│   │ (documents)│←───→│  (vectors)   │←───→│   (search)   │                     │
│   └──────────┘      └──────────────┘      └──────────────┘                     │
│        ↑                   ↑                     ↑                              │
│        │                   │                     │                              │
│        └───────────────────┼─────────────────────┘                              │
│                            │                                                     │
│                     ┌──────────────┐                                            │
│                     │   CDC/Sync   │  ← Must keep all systems in sync!          │
│                     │   Pipeline   │                                            │
│                     └──────────────┘                                            │
│                                                                                  │
│   ⚠️ Latency: 50-200ms (multi-hop)                                              │
│   ⚠️ Complexity: 3+ systems to maintain                                         │
│   ⚠️ Cost: $$$$ for multiple managed services                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       Redis RAG Architecture (1 system!)                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│                          ┌──────────────────────┐                               │
│                          │        Redis         │                               │
│                          │  ┌────────────────┐  │                               │
│                          │  │ Hash: text +   │  │                               │
│                          │  │ metadata       │  │                               │
│                          │  ├────────────────┤  │                               │
│                          │  │ Vector: HNSW   │  │                               │
│                          │  │ embeddings     │  │                               │
│                          │  ├────────────────┤  │                               │
│                          │  │ FT.SEARCH:     │  │                               │
│                          │  │ hybrid queries │  │                               │
│                          │  └────────────────┘  │                               │
│                          └──────────────────────┘                               │
│                                                                                  │
│   ✅ Latency: <1ms (single hop)                                                 │
│   ✅ Complexity: 1 system                                                        │
│   ✅ Cost: Single Redis cluster                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

> **💡 Key Difference:** Redis combines document storage, vector indexing, and hybrid search in ONE system. No sync pipelines, no multi-hop queries, <1ms latency.

#### How It Works
```
1. User asks: "What are the company's revenue projections?"
2. Embed question → vector [0.23, -0.56, ...]
3. Redis vector search finds top-k similar document chunks
4. Inject documents into LLM prompt as context
5. LLM generates accurate, grounded response
```

#### Legacy Approach: Keyword Search + Elasticsearch
```
# Problems:
- "revenue projections" won't find "financial forecast"
- No semantic understanding
- Complex BM25 tuning required
- Separate vector DB + document store needed
```

#### Why Legacy is Slow/Complicated
| Problem | Elasticsearch + pgvector | Redis Vector |
|---------|--------------------------|--------------|
| Setup Complexity | 2+ systems to maintain | Single system |
| Latency | 10-50ms | < 1ms |
| Hybrid Search | Complex query DSL | Native filter support |
| Real-time Updates | Near-real-time | Instant |
| Memory Efficiency | Disk-based indexes | In-memory HNSW |

#### Benchmark Results (vs. Competitors)
| Database | QPS (Queries/sec) | Latency (ms) |
|----------|-------------------|--------------|
| **Redis** | **62% higher than #2** | **< 1ms** |
| Qdrant | 3.4x slower | 4x higher |
| Milvus | 3.3x slower | 4.67x higher |
| Weaviate | 1.7x slower | 1.71x higher |
| PostgreSQL pgvector | 9.5x slower | 9.7x higher |
| MongoDB Atlas | 11x slower | 14.2x higher |

#### 🏆 Customer Success: Relevance AI
- **99.5% faster** with Redis-powered vector search
- Enabled real-time semantic search at scale

---

### 19. 🛣️ Semantic Router

| Aspect | Description |
|--------|-------------|
| **What it does** | Routes user requests to appropriate AI agents/handlers based on intent similarity |
| **How Redis does it** | Pre-embedded route examples, vector similarity to match incoming queries to routes |

#### 📦 What's Actually Stored in Redis
```redis
# Route definitions with example embeddings (Hash + Vector)
HSET route:greeting:001
     route_name "greeting"
     example "hi"
     handler "GreetingAgent"
     embedding "\x00\x01..."

HSET route:greeting:002
     route_name "greeting"
     example "hello there"
     handler "GreetingAgent"
     embedding "\x00\x02..."

HSET route:weather:001
     route_name "weather"
     example "what's the weather like"
     handler "WeatherAgent"
     embedding "\x00\x03..."

HSET route:stock:001
     route_name "stock_price"
     example "AAPL stock price"
     handler "StockPriceAgent"
     embedding "\x00\x04..."

HSET route:stock:002
     route_name "stock_price"
     example "how much is Tesla trading at"
     handler "StockPriceAgent"
     embedding "\x00\x05..."

# Vector index for route matching
FT.CREATE routes_idx ON HASH PREFIX 1 route:
    SCHEMA 
        route_name TAG
        handler TAG
        embedding VECTOR HNSW 6 DIM 1536 DISTANCE_METRIC COSINE

# Find best matching route for user query
FT.SEARCH routes_idx 
    "*=>[KNN 1 @embedding $query_vec AS score]"
    PARAMS 2 query_vec "\x00\x06..."  # "How much is MSFT?"
    RETURN 2 route_name handler
# → route_name: "stock_price", handler: "StockPriceAgent"
```

#### How It Works
```
Routes defined:
- "greeting" → examples: ["hi", "hello", "hey there"]
- "weather" → examples: ["what's the weather", "is it raining"]
- "stock_price" → examples: ["AAPL price", "what's Tesla trading at"]

User says: "How much is Microsoft stock?"
→ Embed query → Find nearest route → "stock_price" (0.94 similarity)
→ Route to StockPriceAgent
```

#### Legacy Approach: Rule-Based Routing
```python
# Fragile regex/keyword matching
if "weather" in query.lower():
    return WeatherHandler()
elif "stock" in query.lower() or "price" in query.lower():
    return StockHandler()
else:
    return DefaultHandler()
```

#### Why Legacy Fails
| Problem | Rule-Based Routing | Semantic Router |
|---------|--------------------| ----------------|
| "AAPL quote" | MISS (no "stock" keyword) | Routes to stock_price ✅ |
| "Is it gonna rain?" | MISS (no "weather" keyword) | Routes to weather ✅ |
| Maintenance | Endless regex updates | Add example sentences |
| New Languages | Complete rewrite | Just add examples |

---

### 20. 🧠 Agent Memory (Contextual Memory)

| Aspect | Description |
|--------|-------------|
| **What it does** | Stores and retrieves conversation history and long-term memories for AI agents |
| **How Redis does it** | Combination of Lists (recent history), Hashes (user profiles), Vector search (semantic recall) |

#### 📦 What's Actually Stored in Redis
```redis
# Short-term memory: Recent conversation (List)
LPUSH conversation:session:abc123 
    '{"role":"user","content":"What is my portfolio value?","ts":"10:00:00"}'
LPUSH conversation:session:abc123 
    '{"role":"assistant","content":"Your portfolio is worth $125,430...","ts":"10:00:02"}'
LPUSH conversation:session:abc123 
    '{"role":"user","content":"Show me AAPL performance","ts":"10:00:15"}'
LTRIM conversation:session:abc123 0 19  # Keep last 20 messages
EXPIRE conversation:session:abc123 3600  # Session expires in 1 hour

# Long-term memory: User preferences (Hash)
HSET user:12345:profile
     name "John Doe"
     language "en"
     timezone "America/New_York"
     response_style "concise"
     risk_tolerance "moderate"
     favorite_stocks "AAPL,MSFT,GOOGL"
     last_session "2024-01-15T10:00:00Z"

# Semantic memory: Important facts with embeddings (Hash + Vector)
HSET memory:user:12345:001
     fact "User prefers receiving alerts before market open"
     source "conversation:2024-01-10"
     importance "high"
     embedding "\x00\x01..."

HSET memory:user:12345:002
     fact "User is interested in renewable energy stocks"
     source "conversation:2024-01-12"
     importance "medium"
     embedding "\x00\x02..."

# Memory index for semantic recall
FT.CREATE memory_idx ON HASH PREFIX 1 memory:user:12345:
    SCHEMA 
        fact TEXT
        importance TAG
        embedding VECTOR HNSW 6 DIM 1536 DISTANCE_METRIC COSINE

# Episodic memory: Session summaries (Sorted Set by timestamp)
ZADD user:12345:sessions 1705312800 
    '{"id":"session:abc","summary":"Discussed portfolio rebalancing","topics":["portfolio","rebalancing"]}'
```

#### Memory Architecture
```
Short-term Memory (Lists):
LPUSH conversation:{session_id} "User: Hello" "AI: Hi there!"
LTRIM conversation:{session_id} 0 19  # Keep last 20 messages

Long-term Memory (Vectors + Metadata):
Store important facts with embeddings for semantic retrieval
"User prefers formal responses" → embed → store with metadata

User Profile (Hashes):
HSET user:{id} name "John" preferences "formal" last_topic "finance"
```

#### Legacy Approach: SQL-Based Memory
```sql
-- Conversation history
SELECT * FROM messages 
WHERE session_id = ? 
ORDER BY created_at DESC 
LIMIT 20;

-- Semantic memory recall? Not possible without separate vector DB!
```

#### Why Legacy is Slow/Complicated
| Problem | SQL-Based | Redis Memory |
|---------|-----------|--------------|
| Recent History | Query + sort (5-20ms) | LRANGE (< 0.5ms) |
| Semantic Recall | Not possible | Vector search built-in |
| Profile Updates | Transaction needed | Atomic HSET |
| TTL/Expiration | Cron job cleanup | Native TTL |
| Multi-modal | Multiple tables/joins | Single namespace |

---

### 21. 📊 Feature Store (Real-Time ML Features)

| Aspect | Description |
|--------|-------------|
| **What it does** | Serves pre-computed ML features with sub-millisecond latency for real-time inference |
| **How Redis does it** | Features stored as Hashes, retrieved in batch with MGET/HMGET, versioned with prefixes |

#### 📦 What's Actually Stored in Redis
```redis
# User features for recommendation model (Hash)
HSET user:123:features
     age 32
     account_tenure_days 730
     purchase_count_30d 12
     avg_order_value 85.50
     category_pref_electronics 0.65
     category_pref_fashion 0.25
     category_pref_home 0.10
     risk_score 0.23
     last_updated "2024-01-15T10:00:00Z"

# Product features for ranking model (Hash)
HSET product:SKU-789:features
     price 149.99
     avg_rating 4.7
     review_count 1250
     conversion_rate 0.045
     inventory_level 500
     days_since_launch 90
     return_rate 0.02

# Feature versioning with prefixes
HSET features:v2:user:123
     purchase_velocity 2.5
     engagement_score 0.78
     churn_probability 0.12

# Batch feature retrieval for ML inference
HMGET user:123:features age purchase_count_30d risk_score
# → ["32", "12", "0.23"] in < 1ms

# Multiple entities at once
MGET user:123:features user:456:features user:789:features

# Feature freshness tracking (Sorted Set)
ZADD features:last_updated 1705312800 "user:123"
ZADD features:last_updated 1705312805 "user:456"
# → Identify stale features needing refresh

# Real-time feature aggregation (counter)
INCR user:123:page_views_today
INCRBY user:123:session_duration_ms 5000
```

#### 🗄️ What's Stored in Legacy Systems (Data Warehouse + Feature Platform)
```sql
-- PostgreSQL/Snowflake: User features table (batch updated)
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    user_features                                            │
├─────────┬─────┬─────────────────┬──────────────────┬───────────────────────┬───────────────┤
│ user_id │ age │ account_tenure  │ purchase_count_30d│ avg_order_value      │ computed_at   │
├─────────┼─────┼─────────────────┼──────────────────┼───────────────────────┼───────────────┤
│ 123     │ 32  │ 730             │ 12               │ 85.50                 │ 2024-01-15 00:00│ ← 10h stale!
│ 456     │ 28  │ 365             │ 8                │ 120.00                │ 2024-01-15 00:00│
│ 789     │ 45  │ 1095            │ 25               │ 65.00                 │ 2024-01-15 00:00│
└─────────┴─────┴─────────────────┴──────────────────┴───────────────────────┴───────────────┘

-- ⚠️ Problem 1: Features computed in batch (nightly/hourly)
-- User made 5 purchases today, but feature still shows yesterday's count!

-- ⚠️ Problem 2: On-the-fly computation is slow
SELECT 
    u.user_id,
    u.age,
    DATEDIFF(NOW(), u.created_at) as account_tenure,
    COUNT(o.id) as purchase_count_30d,
    AVG(o.total) as avg_order_value
FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id 
    AND o.created_at > NOW() - INTERVAL '30 days'
WHERE u.user_id = 123
GROUP BY u.user_id, u.age, u.created_at;
-- ⚠️ 50-500ms per inference request! At 1000 QPS = impossible!

-- ⚠️ Problem 3: Training/Serving skew
-- Training uses batch pipeline (feature_store.user_features_v1)
-- Serving uses real-time query (different SQL, different results!)
-- Model accuracy degrades due to inconsistent features
```

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                    Legacy ML Feature Architecture                                            │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                                │
│  │   Spark/     │────▶│  Snowflake/  │────▶│  Feature     │                                │
│  │   Airflow    │     │  BigQuery    │     │  Platform    │                                │
│  │  (nightly)   │     │  (warehouse) │     │  (Feast/etc) │                                │
│  └──────────────┘     └──────────────┘     └──────────────┘                                │
│         │                    │                    │                                         │
│         │                    │                    ▼                                         │
│         │                    │            ┌──────────────┐                                 │
│         │                    └───────────▶│  PostgreSQL  │◀─ Model serving                 │
│         │                                 │   (online)   │   reads from here               │
│         │                                 └──────────────┘                                 │
│         │                                        │                                          │
│         ▼                                        ▼                                          │
│  ⚠️ Batch lag: 1-24 hours          ⚠️ Query latency: 50-500ms                              │
│  ⚠️ Training/serving skew          ⚠️ DB becomes bottleneck                                │
│                                                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                    Redis Feature Store Architecture                                          │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  ┌──────────────┐     ┌──────────────────────────────────────┐                             │
│  │   Spark/     │     │              Redis                    │                             │
│  │   Flink      │────▶│  ┌─────────────────────────────────┐ │                             │
│  │ (real-time)  │     │  │ HSET user:123:features          │ │◀─ Model reads               │
│  └──────────────┘     │  │      age 32                     │ │   in <1ms                   │
│                       │  │      purchase_count 12          │ │                             │
│  ┌──────────────┐     │  │      risk_score 0.23            │ │                             │
│  │   App        │────▶│  └─────────────────────────────────┘ │                             │
│  │  (events)    │     │                                      │                             │
│  └──────────────┘     │  ✅ Real-time updates                │                             │
│                       │  ✅ <1ms reads (HMGET)               │                             │
│                       │  ✅ Same features for train/serve   │                             │
│                       └──────────────────────────────────────┘                             │
│                                                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

> **💡 Key Difference:** Redis serves pre-computed features in <1ms. Features update in real-time. Same data for training and serving = no skew.

#### How It Works
```
Offline Pipeline (Batch):
1. Compute features in Spark/Flink
2. Write to Redis: HSET user:123:features age 25 purchase_count 47 risk_score 0.23

Online Serving (Real-time):
1. Request: Get features for user 123
2. Redis: HMGET user:123:features age purchase_count risk_score
3. Return: [25, 47, 0.23] in < 1ms
4. Model predicts with fresh features
```

#### Legacy Approach: Database Feature Lookup
```python
# On each prediction request:
user_data = db.query("SELECT * FROM users WHERE id = ?", user_id)
transactions = db.query("SELECT * FROM transactions WHERE user_id = ?", user_id)
# Compute features on-the-fly (expensive!)
features = compute_features(user_data, transactions)  # 50-200ms
prediction = model.predict(features)
```

#### Why Legacy is Slow/Complicated
| Problem | SQL-Based Features | Redis Feature Store |
|---------|--------------------| --------------------|
| Latency | 50-200ms | < 1ms |
| Compute | On-the-fly | Pre-computed |
| Consistency | Training/serving skew | Same features everywhere |
| Versioning | Manual | Built-in with Featureform |
| Batch Retrieval | N queries | Single MGET |

#### 🏆 Customer Success: iFood (Brazil)
- **<1ms per read** for real-time recommendations
- "It's really, really fast. Plus it's a lot cheaper."

#### 🏆 Customer Success: DoorDash
- **38% decrease in Redis latencies**
- Improved ML model serving performance

---

## Performance Benchmarks

### Vector Database Comparison (Official Redis Benchmarks, 2024)

#### vs. Pure Vector Databases
| Metric | Redis | Qdrant | Milvus | Weaviate |
|--------|-------|--------|--------|----------|
| QPS (relative) | **1.0x (baseline)** | 3.4x slower | 3.3x slower | 1.7x slower |
| Latency (relative) | **1.0x (baseline)** | 4x higher | 4.67x higher | 1.71x higher |
| Indexing Time | Baseline | Faster | 2.8x slower | 3.2x slower |

#### vs. General-Purpose Databases with Vector Support
| Metric | Redis | PostgreSQL pgvector | MongoDB Atlas | OpenSearch |
|--------|-------|---------------------|---------------|------------|
| QPS (relative) | **1.0x** | 9.5x slower | 11x slower | 53x slower |
| Latency (relative) | **1.0x** | 9.7x higher | 14.2x higher | 53x higher |
| Indexing Time | Baseline | 5.5-19x slower | N/A | N/A |

---

## Customer Success Stories

### Financial Services

#### 🏦 Axis Bank (India)
| Metric | Before Redis | After Redis | Improvement |
|--------|--------------|-------------|-------------|
| Response Time | 170ms | 40ms | **76% faster** |
| Data Sync | Manual intervention | Near real-time | Automated |
| Cost Savings | - | $82,000 | Reduced records |
| Daily Users | - | 10 million | Seamless scale |

**Use Case:** Runtime Account Authorization for mobile banking
**Redis Products:** Redis Enterprise, Redis Data Integration (RDI)

---

### Telecommunications

#### 📞 TransNexus (Robocall Prevention)
| Metric | Achievement |
|--------|-------------|
| Call Processing | **20 milliseconds** per call |
| Fraud Detection | **95% reduction** in detection time |
| Scale | Hundreds of millions of Redis keys |
| Availability | Automatic failover, no downtime |

**Use Case:** Real-time call routing and fraud detection
**Quote:** "Redis is the only database we need online to perform call processing. It is the number-one most important database."

---

### E-Commerce & Delivery

#### 🍕 iFood (Brazil's #1 Food Delivery)
| Metric | Achievement |
|--------|-------------|
| Feature Serving | **< 1ms per read** |
| Use Case | Real-time ML recommendations |

**Quote:** "It's not just about putting in a food order. It's about providing an optimal experience for our customers. It's really, really fast. Plus it's a lot cheaper."

#### 🚗 DoorDash
| Metric | Achievement |
|--------|-------------|
| Latency Reduction | **38% decrease** |
| Use Case | ML model feature serving |

**Quote:** "We saw a 38% decrease in Redis latencies, helping to improve the runtime performance of serving models."

---

### AI & Healthcare

#### 🥭 Mangoes.ai (Healthcare Voice Assistant)
| Metric | Achievement |
|--------|-------------|
| Response Speed | **Faster FAQ responses** |
| Technology | LangCache semantic caching |
| Use Case | Healthcare voice assistant |

---

### Gaming

#### 🎮 MrQ (Gaming Platform)
| Metric | Achievement |
|--------|-------------|
| Scale | Millions of players |
| Use Case | Real-time personalized gaming experiences |
| Feature | Instant leaderboard updates |

---

## Quick Reference Tables

### Redis Data Structures Cheat Sheet

| Structure | Best For | Key Commands | Time Complexity |
|-----------|----------|--------------|-----------------|
| **Strings** | Caching, counters | GET, SET, INCR, EXPIRE | O(1) |
| **Hashes** | Objects, profiles | HGET, HSET, HMGET | O(1) per field |
| **Lists** | Queues, history | LPUSH, RPOP, LRANGE | O(1) push/pop |
| **Sets** | Unique items, tags | SADD, SMEMBERS, SINTER | O(1) add |
| **Sorted Sets** | Leaderboards, rankings | ZADD, ZRANK, ZRANGE | O(log N) |
| **Streams** | Message queues, logs | XADD, XREAD, XACK | O(1) |
| **HyperLogLog** | Cardinality estimation | PFADD, PFCOUNT | O(1) |

### Redis Modules Cheat Sheet

| Module | Purpose | Key Features |
|--------|---------|--------------|
| **RediSearch** | Full-text & vector search | HNSW/FLAT indexes, hybrid queries |
| **RedisTimeSeries** | Time-series data | Aggregations, compaction, downsampling |
| **RedisJSON** | JSON documents | JSONPath queries, atomic updates |
| **RedisBloom** | Probabilistic structures | Bloom filters, Cuckoo filters, Top-K |
| **RedisGraph** | Graph database | Cypher queries, shortest path |

### When to Use Redis (Decision Tree)

```
Need sub-millisecond latency? 
├─ YES → Need AI/Vector capabilities?
│        ├─ YES → Redis with RediSearch
│        └─ NO  → Need time-series?
│                 ├─ YES → Redis with RedisTimeSeries
│                 └─ NO  → Redis (core data structures)
└─ NO  → Consider traditional databases
```

### Redis vs. Alternatives Summary

| Use Case | Redis Advantage | Legacy Pain |
|----------|-----------------|-------------|
| Caching | < 1ms reads | 10-100ms DB queries |
| Session Store | Atomic ops + TTL | Lock contention + cleanup jobs |
| Leaderboards | O(log N) operations | O(N) table scans |
| Time-Series | Auto-aggregation | Complex GROUP BY |
| Pub/Sub | Instant delivery | Polling overhead |
| Rate Limiting | Atomic + auto-expire | Transaction overhead |
| Deduplication | 10 bits/entry | 100 bytes/entry |
| Full-Text Search | < 5ms | Elasticsearch sync lag |
| Fraud Detection | < 5ms decision | 100-500ms batch |
| Geospatial | O(log N) radius | Haversine full scan |
| Distributed Locks | < 1ms acquire | DB transaction locks |
| Job Queues | Blocking pop + priority | Database polling |
| Semantic Cache | 70-90% hit rate | 20-30% exact match only |
| Vector Search | 53x faster than OpenSearch | Separate systems needed |
| Semantic Router | Intent-based routing | Fragile regex rules |
| Agent Memory | Multi-modal memory | Multiple systems |
| Feature Store | < 1ms batch reads | On-the-fly computation |

---

## Summary: Why Redis Wins

### 📊 At-a-Glance: Redis vs Legacy Data Comparison

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                        REDIS                    vs.           LEGACY DATABASE            │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  SESSION STORAGE                                                                         │
│  ─────────────────────────────────────────────────────────────────────────────────────── │
│  HSET session:abc user_id 123            │  SELECT * FROM sessions WHERE id = 'abc'     │
│  EXPIRE session:abc 3600                 │  + DELETE WHERE expires_at < NOW()           │
│  ✅ < 1ms, auto-cleanup                  │  ⚠️ 10ms + cron job cleanup                  │
│                                                                                          │
│  RATE LIMITING                                                                           │
│  ─────────────────────────────────────────────────────────────────────────────────────── │
│  INCR ratelimit:user:123                 │  BEGIN; SELECT FOR UPDATE; UPDATE; COMMIT;   │
│  EXPIRE ratelimit:user:123 60            │  + scheduled DELETE of old windows           │
│  ✅ Atomic, lock-free                    │  ⚠️ Transactions, lock contention            │
│                                                                                          │
│  LEADERBOARD                                                                             │
│  ─────────────────────────────────────────────────────────────────────────────────────── │
│  ZADD board 1500 player:123              │  UPDATE players SET score = 1500             │
│  ZRANK board player:123                  │  SELECT COUNT(*) WHERE score > ...           │
│  ✅ O(log N), instant rank               │  ⚠️ O(N) table scan, 500ms+                  │
│                                                                                          │
│  MESSAGE QUEUE                                                                           │
│  ─────────────────────────────────────────────────────────────────────────────────────── │
│  XADD orders * item widget               │  INSERT INTO queue (message) VALUES (...)    │
│  XREADGROUP GROUP workers                │  WHILE true: SELECT ... FOR UPDATE; SLEEP    │
│  ✅ Push-based, instant                  │  ⚠️ Poll-based, 100ms+ latency               │
│                                                                                          │
│  DEDUPLICATION                                                                           │
│  ─────────────────────────────────────────────────────────────────────────────────────── │
│  BF.ADD seen msg:12345                   │  INSERT INTO seen_messages (id) VALUES (...)  │
│  BF.EXISTS seen msg:12345                │  SELECT 1 FROM seen_messages WHERE id = ...  │
│  ✅ 10 bits/entry, O(k) lookup           │  ⚠️ 100 bytes/entry, index lookup            │
│                                                                                          │
│  VECTOR SEARCH (AI)                                                                      │
│  ─────────────────────────────────────────────────────────────────────────────────────── │
│  FT.SEARCH idx "*=>[KNN 5 @vec $q]"      │  Pinecone query → get IDs → PostgreSQL       │
│  ✅ Single system, <1ms                  │  ⚠️ Multi-hop, 50-200ms, sync issues         │
│                                                                                          │
│  ML FEATURES                                                                             │
│  ─────────────────────────────────────────────────────────────────────────────────────── │
│  HMGET user:123:features age score       │  SELECT * FROM features WHERE user_id = 123  │
│  ✅ Pre-computed, <1ms                   │  ⚠️ Computed nightly, stale by 12-24 hours   │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### The 3 Pillars of Redis Advantage

1. **Speed**: In-memory architecture delivers sub-millisecond latency
2. **Simplicity**: Purpose-built data structures eliminate complex queries
3. **Versatility**: Single platform handles caching, vectors, time-series, and more

### Legacy Database Limitations
- **Disk I/O**: 10-100x slower than RAM access
- **Query Planning**: CPU overhead for every request
- **Lock Contention**: Concurrent access bottlenecks
- **Scaling Complexity**: Sharding requires application changes
- **Single-Purpose**: Need multiple systems for different data types

### Redis Solutions
- **In-Memory**: All data in RAM = instant access
- **Simple Operations**: O(1) and O(log N) complexity
- **Single-Threaded**: No lock contention
- **Cluster Mode**: Transparent horizontal scaling
- **Multi-Model**: One platform for all use cases

---

*Last Updated: 2025*
*Sources: redis.io, Redis official benchmarks, customer case studies*
