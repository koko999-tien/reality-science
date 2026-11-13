# REALITY SCIENCE — Frontend Application (`frontend/`)

## Architecture
The web application runs in **Zone 1 (Public Edge / Presentation)**:
- **Framework**: Next.js 15+ App Router with React 19, TypeScript, and Tailwind CSS.
- **Scientific Viewer**: KaTeX-rendered mathematical equations, interactive AST visualizer, and dimensional unit inspector.
- **Zero Database Invariant**: The frontend communicates solely over HTTP REST with the Zone 2 FastAPI backend via `NEXT_PUBLIC_API_URL`. It has zero database connectivity and zero internal secrets.
