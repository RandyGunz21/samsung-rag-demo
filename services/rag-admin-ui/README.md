# RAG Admin Manager UI

Web-based administrative dashboard for managing, testing, and querying the RAG system.

## Features

- **Ground Truth Management**: Create and manage test datasets with queries and expected documents
- **Evaluation Runner**: Test RAG quality with NDCG, MAP, MRR metrics
- **Results Visualization**: View aggregate metrics, k-value trends, and per-query drill-down
- **Data Upload**: Upload documents for RAG ingestion
- **Query Interface**: Test different retrieval methods (basic, multi-query, hybrid)

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui (Radix UI + Tailwind)
- **Charts**: Recharts
- **State Management**: Zustand
- **Forms**: React Hook Form + Zod
- **Tables**: TanStack Table v8

## Getting Started

### Prerequisites

- Node.js 20+ and npm
- RAG Service running on http://localhost:8000
- RAG-tester Service running on http://localhost:8001

### Installation

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
services/rag-admin-ui/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Dashboard
│   ├── evaluation/        # Evaluation pages
│   ├── data/              # Data management pages
│   ├── query/             # Query interface
│   └── api/               # API proxy routes
├── components/            # React components
│   ├── ui/                # shadcn/ui components
│   ├── layout/            # Layout components
│   ├── evaluation/        # Evaluation components
│   └── ...
├── lib/                   # Utilities and helpers
│   ├── api/               # API clients
│   ├── stores/            # Zustand stores
│   ├── types/             # TypeScript types
│   └── utils.ts           # Utility functions
└── public/                # Static assets
```

## Development

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linter
npm run lint
```

## Environment Variables

Create a `.env.local` file:

```bash
NEXT_PUBLIC_RAG_SERVICE_URL=http://localhost:8000
NEXT_PUBLIC_TESTER_SERVICE_URL=http://localhost:8001
```

## API Integration

The application integrates with two backend services:

1. **RAG Service** (port 8000): Document ingestion and retrieval
2. **RAG-tester Service** (port 8001): Evaluation and testing

API calls are proxied through Next.js API routes to handle CORS and environment variables.

## License

ISC
