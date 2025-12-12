# FinagentiX Frontend

Modern React + TypeScript dashboard for visualizing AI agent execution metrics.

## 🚀 Features

- **Real-time Chat Interface**: Interactive chat with AI financial assistant
- **Comprehensive Metrics Dashboard**: 60+ metrics tracked across 4 tabs
  - **Overview**: High-level summary with key metrics
  - **Agents**: Detailed agent execution breakdown with tool usage
  - **Timeline**: Visual execution timeline with events
  - **Costs**: Token usage, cost analysis, and baseline comparisons
- **Dark Theme UI**: Modern, clean design system
- **Type-Safe**: Full TypeScript coverage matching backend Pydantic models
- **Efficient Data Fetching**: TanStack Query for caching and state management

## 📋 Prerequisites

Install Node.js (v18 or higher):

```bash
# Using Homebrew on macOS
brew install node

# Verify installation
node --version
npm --version
```

## 🔧 Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

## 🏃 Development

```bash
# Start development server (port 3000)
npm run dev

# The app will be available at http://localhost:3000
# API calls are proxied to http://localhost:8000
```

**Important**: Make sure the backend server is running on port 8000 before starting the frontend.

## 🏗️ Build

```bash
# Type check
npm run type-check

# Lint code
npm run lint

# Build for production
npm run build

# Preview production build
npm run preview
```

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── ChatPanel.tsx    # Chat interface with message list
│   │   ├── MetricsPanel.tsx # Metrics dashboard with tabs
│   │   ├── Header.tsx       # App header
│   │   ├── Message.tsx      # Individual chat message
│   │   ├── MessageList.tsx  # Message list container
│   │   └── metrics/         # Metric tab components
│   │       ├── OverviewTab.tsx
│   │       ├── AgentsTab.tsx
│   │       ├── TimelineTab.tsx
│   │       └── CostsTab.tsx
│   ├── types/
│   │   └── api.ts          # TypeScript type definitions
│   ├── lib/
│   │   └── api.ts          # API client
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # React entry point
│   └── index.css           # Global styles + design system
├── package.json
├── tsconfig.json
├── vite.config.ts
└── index.html
```

## 🎨 Design System

The app uses a comprehensive design system with:

- **Colors**: Dark theme with slate/blue palette
- **Status Colors**: Success (green), Warning (amber), Error (red), Info (blue)
- **Cost Indicators**: Low (green), Medium (amber), High (red)
- **Performance Indicators**: Excellent (emerald), Good (blue), Poor (red)
- **Spacing Scale**: xs (4px) to xl (32px)
- **Typography**: Inter font family with responsive sizing
- **Custom Scrollbars**: Styled for dark theme

## 🔌 API Integration

The frontend communicates with the backend API through a type-safe client:

```typescript
import { api } from '@/lib/api'

// Execute query with enhanced metrics
const response = await api.query.executeEnhanced({
  query: 'What is the stock price of AAPL?',
  user_id: sessionId,
})

// Get metrics summary
const summary = await api.metrics.getSummary()
```

All API types match the backend Pydantic models exactly, ensuring type safety across the stack.

## 📊 Metrics Displayed

### Overview Tab
- Total execution time (with LLM/tool breakdown)
- Total cost (with baseline comparison)
- Cache hit rate
- Token usage (input/output/cached)
- Workflow summary
- Cost breakdown by agent

### Agents Tab
- Agent execution table with:
  - Agent name and model
  - Duration
  - Token counts (input/output/cached)
  - Cost
  - Tool invocations (expandable)
  - Success/error status

### Timeline Tab
- Event-by-event execution timeline
- Event types (agent_start, agent_end, tool_start, tool_end, cache_hit, cache_miss)
- Timestamps (HH:mm:ss.SSS)
- Durations
- Metadata (expandable)

### Costs Tab
- Total cost with large display
- Baseline comparison with percentage and trend
- Token cost breakdown (input/output/cache read/cache write)
- Cost by agent with progress bars
- Potential savings from caching

## 🔧 Configuration

### Environment Variables

Create a `.env` file (optional):

```env
VITE_API_URL=http://localhost:8000
```

Default API URL is `http://localhost:8000` if not specified.

### Vite Proxy

The dev server proxies `/api/*` requests to the backend:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

## 🧪 Testing

Currently, the frontend focuses on the core dashboard implementation. Testing infrastructure can be added using:

- **Vitest** for unit tests
- **React Testing Library** for component tests
- **Playwright** for E2E tests

## 🚀 Deployment

### Production Build

```bash
npm run build
```

This creates optimized static files in the `dist/` directory that can be served by any static file server.

### Serve Options

```bash
# Using Python
python3 -m http.server --directory dist 3000

# Using serve
npx serve dist -l 3000

# Using nginx (recommended for production)
# Configure nginx to serve dist/ and proxy /api to backend
```

## 📝 Development Notes

### Layout

- **40/60 Split**: Chat panel (40%) | Metrics panel (60%)
- **Responsive**: Stacks vertically on smaller screens (< 1024px)
- **Full Height**: Uses viewport height for immersive experience

### Data Flow

1. User types query in ChatPanel
2. ChatPanel calls `api.query.executeEnhanced()`
3. Response with 60+ metrics received
4. ChatPanel updates message list
5. ChatPanel calls `onResponseReceived(response)`
6. MetricsPanel receives response and displays metrics

### State Management

- **Local State**: Component state for UI interactions
- **TanStack Query**: Server state management with:
  - 5-minute stale time
  - 1 retry on failure
  - No refetch on window focus

## 🐛 Troubleshooting

### TypeScript Errors

If you see TypeScript errors:

```bash
# Clean install
rm -rf node_modules package-lock.json
npm install
```

### API Connection Issues

1. Verify backend is running: `curl http://localhost:8000/health`
2. Check Vite proxy config in `vite.config.ts`
3. Inspect browser console for CORS errors

### Build Errors

```bash
# Type check only
npm run type-check

# Fix common issues
npm run lint
```

## 📚 Technology Stack

- **React 18.3.1**: UI framework
- **TypeScript 5.6.2**: Type safety
- **Vite 5.4.8**: Build tool and dev server
- **TanStack Query 5.56.2**: Server state management
- **Recharts 2.12.7**: Charts (future use)
- **Lucide React 0.446.0**: Icon library
- **date-fns 4.1.0**: Date formatting
- **clsx 2.1.1**: Conditional class names

## 🎯 Next Steps

### Immediate
1. Install Node.js and npm
2. Run `npm install`
3. Start backend on port 8000
4. Run `npm run dev`
5. Open http://localhost:3000

### Future Enhancements
- [ ] Real-time streaming responses
- [ ] Export metrics as CSV/JSON
- [ ] Custom metric filters
- [ ] Historical session comparison
- [ ] Chart visualizations for timeline and costs
- [ ] Keyboard shortcuts
- [ ] Dark/light theme toggle
- [ ] Responsive mobile optimization

## 📄 License

Same as main FinagentiX project.
