# FinagentiX Demo Video Script (60 seconds)

## 🎬 Video Script

---

### **[0:00 - 0:08] INTRO - What is this app?**

**SHOW:** Landing page with chat interface

**SAY:**
> "This is FinagentiX – an AI-powered Financial Analysis Assistant that can answer questions about stocks, analyze SEC filings, and provide market insights in real-time."

---

### **[0:08 - 0:18] HOW TO USE IT - Live Example**

**ACTION:** Type a query like "Analyze Microsoft"

**SAY:**
> "Simply ask a question – like 'Analyze Microsoft' – and the AI agent analyzes your request, fetches financial data, and provides insights."

**SHOW:** Response appearing with analysis

---

### **[0:18 - 0:28] TECHNOLOGY - Semantic Kernel & Agents**

**ACTION:** Click on "Agents" tab

**SAY:**
> "Under the hood, this runs on Microsoft Semantic Kernel – part of the Microsoft Agent Framework. You can see the specialized agents here: Technical Analysis, Risk Assessment, SEC Filings, and more."

**SHOW:** Agent cards/list

---

### **[0:28 - 0:38] TIMELINE - Cache Hit in Action**

**ACTION:** Click on "Timeline" tab, point to a cache hit entry

**SAY:**
> "The Timeline shows exactly what happened. See this green entry? That's a semantic cache hit – the system recognized this as a similar question and returned the cached response in milliseconds instead of calling the LLM."

**SHOW:** Highlight the cache hit indicator (green/fast response)

---

### **[0:38 - 0:50] REDIS BENEFITS - Run Benchmark**

**ACTION:** Navigate to "Redis Benefits" tab, click "Run Benchmark" with 25 requests

**SAY:**
> "Let's see the impact at scale. I'll run a benchmark with 25 requests..."

**WAIT:** ~5 seconds for results

**SAY:**
> "62% cache hit rate! That means 62% of queries were answered from Redis cache instead of expensive LLM calls."

**SHOW:** Hit rate percentage, latency comparison

---

### **[0:50 - 0:60] COST SAVINGS - The Bottom Line**

**ACTION:** Scroll to Cost Comparison table

**SAY:**
> "And here's the bottom line: For 10,000 users, we're saving over $10,000 per month on GPT-4o – even after including the $270 monthly cost for Azure Managed Redis. That's real ROI from semantic caching."

**SHOW:** Table with "Net Savings" column highlighted

**END:** 
> "Try it yourself – link in the description!"

---

## 📋 Pre-Recording Checklist

- [ ] Clear browser cache for fresh demo
- [ ] Pre-warm the cache with 2-3 queries so Timeline has data
- [ ] Set benchmark to 25 requests
- [ ] Make sure Redis Benefits tab shows the default scenario (10,000 users)
- [ ] Test that all tabs load quickly

## 🎯 Key Points to Emphasize

1. **62% fewer LLM calls** - the headline number
2. **Microsoft Semantic Kernel** - enterprise credibility  
3. **Real-time visualization** - Timeline shows exactly what's cached
4. **$270 Redis vs $10,000+ savings** - clear ROI

## 📝 Suggested Queries for Demo

- "Analyze Microsoft"
- "What's the market sentiment for Microsoft?"
- "What's the stock price of AAPL?"

## 🔗 Demo URL

https://ca-frontend-3ae172dc9e9da.redflower-348a14ef.westus3.azurecontainerapps.io

---

## ⏱️ Timing Summary

| Section | Duration | Cumulative |
|---------|----------|------------|
| Intro | 8s | 0:08 |
| Example | 10s | 0:18 |
| Technology | 10s | 0:28 |
| Timeline | 10s | 0:38 |
| Benchmark | 12s | 0:50 |
| Savings | 10s | 1:00 |

