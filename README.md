# VeriGov AI - Official-Source-Only Verification Platform

VeriGov AI is an official-source-only verification platform that collects information exclusively from verified government sources, validates claims through AI-powered fact-checking using the Grok API, and delivers authenticated, structured intelligence with complete traceability.

## Project Structure

```
verigov-ai/
├── src/
│   └── verigov/
│       ├── __init__.py
│       ├── collection/          # Data collection from government sources
│       │   └── __init__.py
│       ├── config/              # Configuration management
│       │   └── __init__.py
│       ├── dashboard/           # Verification dashboard
│       │   └── __init__.py
│       ├── infrastructure/      # Audit log and utilities
│       │   └── __init__.py
│       ├── monitoring/          # Change detection
│       │   └── __init__.py
│       ├── output/              # Output generation and citations
│       │   └── __init__.py
│       ├── pipeline/            # Verification pipeline orchestration
│       │   └── __init__.py
│       └── verification/        # Fact verification and intelligence
│           └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── unit/                    # Unit tests
│   │   └── __init__.py
│   ├── property/                # Property-based tests
│   │   └── __init__.py
│   └── integration/             # Integration tests
│       └── __init__.py
├── config/                      # Configuration files
│   └── __init__.py
├── .env.example                 # Environment variable template
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and configure your API keys:
   ```bash
   cp .env.example .env
   ```

## Configuration

Edit the `.env` file with your configuration:

- `GROK_API_KEY`: Your Grok API key for AI-powered verification
- `GROK_API_URL`: Grok API endpoint (default: https://api.x.ai/v1)
- Additional government API credentials as needed

See `.env.example` for all available configuration options.

## Architecture

VeriGov AI follows a modular pipeline architecture:

**Collect → Verify → Structure → Deliver**

### Key Components

1. **Source Collection**: Whitelist-based data collection from verified government sources
2. **Verification Engine**: AI-powered claim validation with confidence scoring
3. **Intelligence Layer**: Semantic analysis using Grok API
4. **Change Detection**: Real-time monitoring of policy updates
5. **Output Generation**: Structured intelligence with transparent citations
6. **Verification Dashboard**: User-friendly interface with clear status indicators

## Development

Run tests:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=src/verigov
```

## License

[Add your license here]
