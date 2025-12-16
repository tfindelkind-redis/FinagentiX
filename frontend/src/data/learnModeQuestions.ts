/**
 * Learn Mode Questions - Curated queries to showcase Redis AI capabilities
 * Each question demonstrates specific agents and Redis patterns
 */

export interface LearnModeQuestion {
  id: string;
  question: string;
  category: 'investment' | 'portfolio' | 'market' | 'technical' | 'risk' | 'news' | 'quick';
  agentsInvolved: string[];
  redisPatterns: string[];
  description: string;
  expectedBenefits: string[];
  difficulty: 'beginner' | 'intermediate' | 'advanced';
}

export const LEARN_MODE_QUESTIONS: LearnModeQuestion[] = [
  // Quick Quote - Simplest query, great for caching demo
  {
    id: 'quick-1',
    question: "What's the current price of AAPL?",
    category: 'quick',
    agentsInvolved: ['Market Data Agent'],
    redisPatterns: ['Semantic Cache', 'Tool Cache'],
    description: 'Simple price lookup - perfect for demonstrating semantic caching. Try asking this twice to see the cache hit!',
    expectedBenefits: [
      'Second query returns in <10ms (vs 500ms+)',
      '137x cheaper on cache hit',
      'Similar queries also hit cache ("Apple stock price?")',
    ],
    difficulty: 'beginner',
  },
  {
    id: 'quick-2',
    question: "What's Tesla's stock price today?",
    category: 'quick',
    agentsInvolved: ['Market Data Agent'],
    redisPatterns: ['Semantic Cache', 'Tool Cache'],
    description: 'Another price query - try variations like "TSLA price" or "How much is Tesla stock?" to see semantic similarity matching.',
    expectedBenefits: [
      'Semantic cache matches similar phrasing',
      'Tool cache stores the API response',
      'Near-instant response on repeat queries',
    ],
    difficulty: 'beginner',
  },

  // Investment Analysis - Multi-agent showcase
  {
    id: 'invest-1',
    question: 'Should I invest in NVDA? Give me a comprehensive analysis.',
    category: 'investment',
    agentsInvolved: ['Market Data Agent', 'Technical Analysis Agent', 'Risk Assessment Agent', 'Sentiment Agent'],
    redisPatterns: ['Semantic Cache', 'Semantic Routing', 'Tool Cache', 'Contextual Memory'],
    description: 'Full investment analysis using 4 agents running in parallel. This showcases the orchestrator routing to the Investment Analysis workflow.',
    expectedBenefits: [
      'Semantic router bypasses expensive orchestrator LLM call',
      '4 agents execute concurrently (not sequentially)',
      'Each agent\'s tools are cached for reuse',
      'Results synthesized into actionable recommendation',
    ],
    difficulty: 'intermediate',
  },
  {
    id: 'invest-2',
    question: 'Analyze Microsoft stock for long-term investment potential.',
    category: 'investment',
    agentsInvolved: ['Market Data Agent', 'Technical Analysis Agent', 'Risk Assessment Agent', 'Sentiment Agent'],
    redisPatterns: ['Semantic Cache', 'Semantic Routing', 'Tool Cache'],
    description: 'Investment analysis for a different ticker. Notice how the workflow is recognized instantly via semantic routing.',
    expectedBenefits: [
      'Route matched in <5ms via vector similarity',
      'Parallel agent execution saves 60%+ time',
      'Tool cache reduces API calls',
    ],
    difficulty: 'intermediate',
  },

  // Technical Analysis - Pattern recognition
  {
    id: 'tech-1',
    question: 'What do the technical indicators say about AAPL? Show me RSI, MACD, and Bollinger Bands.',
    category: 'technical',
    agentsInvolved: ['Market Data Agent', 'Technical Analysis Agent'],
    redisPatterns: ['Tool Cache', 'Semantic Cache'],
    description: 'Deep technical analysis with multiple indicators. The Tool Cache stores expensive calculations for reuse.',
    expectedBenefits: [
      'RSI, MACD calculations cached for 5 minutes',
      'Subsequent queries reuse cached indicators',
      '70%+ cost savings on repeated technical queries',
    ],
    difficulty: 'intermediate',
  },
  {
    id: 'tech-2',
    question: 'Is GOOGL showing any bullish or bearish patterns?',
    category: 'technical',
    agentsInvolved: ['Technical Analysis Agent'],
    redisPatterns: ['Semantic Routing', 'Tool Cache'],
    description: 'Pattern recognition query. Watch how the semantic router identifies this as a technical analysis request.',
    expectedBenefits: [
      'Direct routing to Technical Analysis workflow',
      'Pattern detection algorithms cached',
      'Fast response via semantic similarity',
    ],
    difficulty: 'intermediate',
  },

  // Risk Assessment - Portfolio safety
  {
    id: 'risk-1',
    question: 'How risky is investing in AMD? Calculate VaR and show me the risk metrics.',
    category: 'risk',
    agentsInvolved: ['Risk Assessment Agent', 'Market Data Agent'],
    redisPatterns: ['Tool Cache', 'Semantic Cache', 'Contextual Memory'],
    description: 'Risk analysis with Value-at-Risk calculation. Complex calculations are cached for efficiency.',
    expectedBenefits: [
      'VaR calculation results cached',
      'Historical volatility data reused',
      'Risk metrics stored in contextual memory',
    ],
    difficulty: 'advanced',
  },
  {
    id: 'risk-2',
    question: "What's the beta and volatility of AMZN compared to the market?",
    category: 'risk',
    agentsInvolved: ['Risk Assessment Agent'],
    redisPatterns: ['Tool Cache', 'Semantic Routing'],
    description: 'Comparative risk metrics query. Shows how specialized calculations benefit from caching.',
    expectedBenefits: [
      'Beta calculations are computation-intensive',
      'Tool Cache stores results for 5+ minutes',
      'Similar risk queries benefit from cache',
    ],
    difficulty: 'advanced',
  },

  // Portfolio Review - User context
  {
    id: 'portfolio-1',
    question: 'Review my portfolio performance and suggest rebalancing.',
    category: 'portfolio',
    agentsInvolved: ['Portfolio Management Agent', 'Risk Assessment Agent'],
    redisPatterns: ['Contextual Memory', 'Semantic Cache', 'Workflow Persistence'],
    description: 'Portfolio analysis with personalization. Contextual Memory stores your preferences and holdings across sessions.',
    expectedBenefits: [
      'User preferences remembered across sessions',
      'Portfolio state persisted in Redis',
      'Recommendations personalized to your risk profile',
    ],
    difficulty: 'advanced',
  },
  {
    id: 'portfolio-2',
    question: 'What allocation changes would reduce my portfolio risk?',
    category: 'portfolio',
    agentsInvolved: ['Portfolio Management Agent', 'Risk Assessment Agent'],
    redisPatterns: ['Contextual Memory', 'Tool Cache'],
    description: 'Optimization query using your stored portfolio context. Shows how memory persists.',
    expectedBenefits: [
      'Contextual Memory recalls your holdings',
      'No need to re-specify your portfolio',
      'Builds on previous conversation context',
    ],
    difficulty: 'advanced',
  },

  // Market Research - News & RAG
  {
    id: 'market-1',
    question: "What's happening in the tech sector today?",
    category: 'market',
    agentsInvolved: ['Market Data Agent', 'Sentiment Agent', 'News Research Agent'],
    redisPatterns: ['Document Store (RAG)', 'Semantic Cache', 'Tool Cache'],
    description: 'Market overview using multiple data sources. The Document Store enables RAG search over news articles.',
    expectedBenefits: [
      'RAG retrieves relevant news in <10ms',
      'Vector search across 120+ news articles',
      'Sentiment analysis cached per ticker',
    ],
    difficulty: 'beginner',
  },
  {
    id: 'market-2',
    question: 'What are analysts saying about the semiconductor industry?',
    category: 'market',
    agentsInvolved: ['News Research Agent', 'Sentiment Agent'],
    redisPatterns: ['Document Store (RAG)', 'Semantic Cache'],
    description: 'Industry research using RAG. Vector search finds relevant documents across SEC filings and news.',
    expectedBenefits: [
      'Searches 326+ SEC filing chunks',
      'Vector similarity finds relevant passages',
      'Sub-10ms retrieval time',
    ],
    difficulty: 'intermediate',
  },

  // News & Sentiment - Real-time analysis
  {
    id: 'news-1',
    question: 'What is the current market sentiment for Apple based on recent news?',
    category: 'news',
    agentsInvolved: ['Sentiment Agent', 'News Research Agent'],
    redisPatterns: ['Document Store (RAG)', 'Semantic Cache', 'Tool Cache'],
    description: 'Sentiment analysis combining news and social signals. RAG retrieves relevant news for analysis.',
    expectedBenefits: [
      'News sentiment scores cached',
      'RAG finds relevant articles instantly',
      'Combined sentiment from multiple sources',
    ],
    difficulty: 'intermediate',
  },
  {
    id: 'news-2',
    question: 'Find recent SEC filings mentioning AI investments for major tech companies.',
    category: 'news',
    agentsInvolved: ['News Research Agent'],
    redisPatterns: ['Document Store (RAG)', 'Semantic Cache'],
    description: 'SEC filing search using vector similarity. This showcases the RAG pipeline with embedded documents.',
    expectedBenefits: [
      'Vector search across 10K/10Q filings',
      '3072-dimensional embeddings for accuracy',
      'Relevant passages ranked by similarity',
    ],
    difficulty: 'advanced',
  },

  // Cache demonstration queries
  {
    id: 'cache-demo-1',
    question: "What's Apple's current stock price?",
    category: 'quick',
    agentsInvolved: ['Market Data Agent'],
    redisPatterns: ['Semantic Cache'],
    description: '🎯 CACHE DEMO: Ask this first, then ask "AAPL price" or "Apple stock price" to see semantic cache matching similar queries!',
    expectedBenefits: [
      'First query: ~500-2000ms (LLM call)',
      'Second query: <10ms (cache hit)',
      'Similarity matching finds equivalent queries',
    ],
    difficulty: 'beginner',
  },
  {
    id: 'cache-demo-2',
    question: 'Give me a technical analysis of MSFT with RSI and MACD.',
    category: 'technical',
    agentsInvolved: ['Technical Analysis Agent'],
    redisPatterns: ['Semantic Cache', 'Tool Cache'],
    description: '🎯 CACHE DEMO: Run twice to see how both the final response AND individual tool outputs are cached.',
    expectedBenefits: [
      'Response-level caching (Semantic Cache)',
      'Tool-level caching (RSI, MACD calculations)',
      'Double layer of cost savings',
    ],
    difficulty: 'beginner',
  },
];

// Group questions by category for UI
export const QUESTION_CATEGORIES = {
  quick: {
    label: '⚡ Quick Quotes',
    description: 'Simple price lookups - great for cache demos',
    color: '#10b981',
  },
  investment: {
    label: '📊 Investment Analysis',
    description: 'Multi-agent comprehensive analysis',
    color: '#3b82f6',
  },
  technical: {
    label: '📈 Technical Analysis',
    description: 'Indicators, patterns, and signals',
    color: '#8b5cf6',
  },
  risk: {
    label: '⚠️ Risk Assessment',
    description: 'VaR, volatility, and risk metrics',
    color: '#f59e0b',
  },
  portfolio: {
    label: '💼 Portfolio Review',
    description: 'Personalized portfolio analysis',
    color: '#ec4899',
  },
  market: {
    label: '🌍 Market Research',
    description: 'Sector and market overview',
    color: '#06b6d4',
  },
  news: {
    label: '📰 News & Sentiment',
    description: 'News analysis and SEC filings',
    color: '#84cc16',
  },
};

// Agent explanations for the AgentsTab
export const AGENT_EXPLANATIONS: Record<string, {
  name: string;
  role: string;
  redisIntegration: string;
  benefits: string[];
}> = {
  'Market Data Agent': {
    name: 'Market Data Agent',
    role: 'Fetches real-time and historical price data, volume, and basic metrics.',
    redisIntegration: 'Uses Tool Cache to store API responses (price data, OHLCV) for 1-5 minutes, reducing external API calls by 60%+.',
    benefits: [
      'Tool Cache eliminates redundant API calls',
      'Sub-second response for cached data',
      'Reduces rate limit issues with data providers',
    ],
  },
  'Technical Analysis Agent': {
    name: 'Technical Analysis Agent',
    role: 'Calculates technical indicators (RSI, MACD, Bollinger Bands) and identifies chart patterns.',
    redisIntegration: 'Computation-heavy indicators are cached in Tool Cache. Results reused across similar queries.',
    benefits: [
      'RSI/MACD calculations cached for 5 minutes',
      'Pattern detection results reused',
      '70% reduction in compute time',
    ],
  },
  'Risk Assessment Agent': {
    name: 'Risk Assessment Agent',
    role: 'Calculates Value-at-Risk (VaR), beta, volatility, Sharpe ratio, and other risk metrics.',
    redisIntegration: 'Complex statistical calculations stored in Tool Cache. Historical volatility data cached for efficiency.',
    benefits: [
      'VaR calculations are CPU-intensive',
      'Caching saves significant compute',
      'Risk metrics consistent across queries',
    ],
  },
  'Sentiment Agent': {
    name: 'Sentiment Analysis Agent',
    role: 'Analyzes news and social media sentiment for stocks and sectors.',
    redisIntegration: 'Sentiment scores cached per ticker. RAG retrieves relevant news for analysis.',
    benefits: [
      'Sentiment scores cached per ticker',
      'News retrieval via vector search',
      'Aggregated sentiment from multiple sources',
    ],
  },
  'Portfolio Management Agent': {
    name: 'Portfolio Management Agent',
    role: 'Tracks positions, calculates allocation, and suggests rebalancing strategies.',
    redisIntegration: 'User portfolio stored in Contextual Memory. Positions persist across sessions.',
    benefits: [
      'Portfolio state persists in Redis',
      'No need to re-enter holdings',
      'Personalized recommendations',
    ],
  },
  'News Research Agent': {
    name: 'News & Research Agent',
    role: 'Searches SEC filings and news using RAG (Retrieval-Augmented Generation).',
    redisIntegration: 'Document Store holds 326+ SEC chunks and 120+ news articles with vector embeddings.',
    benefits: [
      'Vector search in <10ms',
      'Semantic similarity ranking',
      'Context-aware document retrieval',
    ],
  },
  'Orchestrator Agent': {
    name: 'Orchestrator Agent',
    role: 'Routes queries to appropriate workflows and coordinates multi-agent execution.',
    redisIntegration: 'Semantic Router uses vector similarity to bypass LLM routing decisions. Workflow state persisted.',
    benefits: [
      'Route matching in <5ms',
      'Avoids expensive LLM orchestration call',
      'Workflow state persists for recovery',
    ],
  },
};

// Redis pattern explanations for the TimelineTab
export const REDIS_PATTERN_EXPLANATIONS: Record<string, {
  name: string;
  description: string;
  howItWorks: string;
  benefit: string;
  icon: string;
}> = {
  'semantic_cache': {
    name: 'Semantic Cache',
    description: 'Caches LLM responses and matches semantically similar queries.',
    howItWorks: 'Query is embedded using text-embedding-3-large. Vector similarity search (HNSW) finds cached responses for similar queries (>95% similarity).',
    benefit: '137x cheaper and <10ms vs 500-2000ms for LLM calls. 30-70% cost savings overall.',
    icon: '🧠',
  },
  'semantic_routing': {
    name: 'Semantic Router',
    description: 'Routes queries to workflows using vector similarity instead of LLM.',
    howItWorks: 'Query embedding compared against route embeddings. Best matching route selected in <5ms without LLM call.',
    benefit: 'Bypasses expensive orchestrator LLM decision. Routes in milliseconds, not seconds.',
    icon: '🎯',
  },
  'tool_cache': {
    name: 'Tool Cache',
    description: 'Caches individual tool/function outputs for reuse.',
    howItWorks: 'Tool inputs hashed to create cache key. Results stored with configurable TTL (1-5 minutes).',
    benefit: 'Eliminates redundant API calls and calculations. 60%+ reduction in external calls.',
    icon: '🔧',
  },
  'contextual_memory': {
    name: 'Contextual Memory',
    description: 'Stores user preferences, conversation history, and session state.',
    howItWorks: 'Redis Hashes store user profiles. Conversation history in sorted sets. Enables personalization.',
    benefit: 'Context persists across sessions. Personalized recommendations. No re-authentication needed.',
    icon: '💾',
  },
  'document_store': {
    name: 'Document Store (RAG)',
    description: 'Vector index for SEC filings and news articles enabling semantic search.',
    howItWorks: 'Documents chunked and embedded. RediSearch HNSW index enables K-NN vector search.',
    benefit: 'Sub-10ms retrieval. Semantic understanding of queries. 326 SEC + 120 news documents indexed.',
    icon: '📚',
  },
  'workflow_persistence': {
    name: 'Workflow Persistence',
    description: 'Stores workflow execution state for recovery and audit.',
    howItWorks: 'Workflow checkpoints stored in Redis. Enables resume on failure and execution audit.',
    benefit: 'Fault tolerance. Execution history. Debugging support.',
    icon: '📋',
  },
};
