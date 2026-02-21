# 🏛️ VeriGov AI - Government Information Verification System

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-155%20passing-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-64%25-yellow.svg)](htmlcov/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> An AI-powered verification platform that validates government information claims against official sources with complete traceability and transparency.

## 🎯 Overview

VeriGov AI is an official-source-only verification platform designed to combat misinformation by:
- ✅ Collecting data exclusively from verified government sources
- 🤖 Validating claims through AI-powered semantic analysis (Grok API)
- 📊 Providing confidence scores and transparent explanations
- 🔍 Monitoring sources for real-time policy changes
- 📝 Generating comprehensive audit trails

**Built for the AWS Hackathon** | **Powered by Grok AI**

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Grok API key ([Get one here](https://x.ai/))
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/shreyashirkar25-rgb/vigro.git
cd vigro

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROK_API_KEY
```

### First Verification

```bash
# Verify a claim
python -m verigov.main verify "The federal minimum wage is $7.25 per hour"

# Interactive mode
python -m verigov.main interactive
```

---

## 💡 Features

### 🔐 Whitelist-Based Source Collection
- Only verified government domains (.gov, official APIs)
- SSL certificate validation
- Manual approval workflow for new sources
- Audit logging for all collection attempts

### 🧠 AI-Powered Verification
- Semantic claim analysis using Grok API
- Multi-source cross-verification
- Confidence scoring (0-100 scale)
- Timeline-based validation
- Entity extraction (people, organizations, dates, policies)

### 📡 Real-Time Monitoring
- Continuous source monitoring
- Policy change detection
- Conflict identification across sources
- Version history tracking
- Impact level assessment (High/Medium/Low)

### 📋 Comprehensive Audit Trail
- Immutable append-only logging
- Complete traceability of all operations
- Query and filtering capabilities
- Export functionality (JSON)

### 🎨 Multiple Output Formats
- JSON structured data
- Markdown reports
- Console-friendly displays
- Citation generation with source mapping

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     VeriGov AI Pipeline                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────┐
        │   1. COLLECT (Source Collector)      │
        │   • Whitelist validation             │
        │   • SSL verification                 │
        │   • Metadata extraction              │
        └──────────────┬───────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────────┐
        │   2. VERIFY (Verification Engine)    │
        │   • Intelligence Layer (Grok AI)     │
        │   • Semantic analysis                │
        │   • Confidence scoring               │
        │   • Multi-source validation          │
        └──────────────┬───────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────────┐
        │   3. MONITOR (Change Detector)       │
        │   • Policy change detection          │
        │   • Conflict identification          │
        │   • Version tracking                 │
        └──────────────┬───────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────────┐
        │   4. DELIVER (Output Generation)     │
        │   • Structured reports               │
        │   • Citations                        │
        │   • Audit logs                       │
        └──────────────────────────────────────┘
```

---

## 📖 Usage Examples

### CLI Commands

#### Verify a Single Claim
```bash
python -m verigov.main verify "Social Security benefits are adjusted annually for inflation"
```

#### Verify with Specific Sources
```bash
python -m verigov.main verify "The Affordable Care Act was passed in 2010" \
  --sources https://www.healthcare.gov/ https://www.congress.gov/
```

#### Batch Verification
```bash
# Create claims file
echo "Claim 1: The minimum wage is $7.25" > claims.txt
echo "Claim 2: Medicare covers prescription drugs" >> claims.txt

# Run batch verification
python -m verigov.main batch claims.txt --output results.json
```

#### Monitor Sources for Changes
```bash
python -m verigov.main monitor \
  --sources https://www.whitehouse.gov/briefing-room/ \
  --interval 3600
```

#### Interactive Mode
```bash
python -m verigov.main interactive

verigov> verify The voting age is 18
Status: VERIFIED
Confidence: 95%
Explanation: Confirmed by official government sources...

verigov> audit
Audit Log: 42 entries
Latest: verification at 2026-02-20 19:30:15

verigov> quit
```

### Python API

```python
from verigov.main import VeriGovApp

# Initialize
app = VeriGovApp()

# Verify a claim
result = app.verify_claim(
    claim="The federal minimum wage is $7.25 per hour",
    sources=["https://www.dol.gov/agencies/whd/minimum-wage"]
)

print(f"Status: {result['status']}")
print(f"Confidence: {result['confidence']}%")
print(f"Explanation: {result['explanation']}")

# Batch verification
claims = [
    "Claim 1",
    "Claim 2",
    "Claim 3"
]
results = app.verify_batch(claims)

# Export audit log
app.export_audit_log("audit.json")
```

### Example Scripts

Three complete examples are provided in the `examples/` directory:

1. **`verify_claim.py`** - Single claim verification
2. **`monitor_sources.py`** - Continuous source monitoring
3. **`generate_report.py`** - Batch verification with report generation

```bash
# Run examples
python examples/verify_claim.py
python examples/monitor_sources.py
python examples/generate_report.py
```

See [examples/README.md](examples/README.md) for detailed documentation.

---

## 🧪 Testing

VeriGov AI includes a comprehensive test suite with 155 tests and 64% code coverage.

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src/verigov --cov-report=html

# Run specific test file
pytest tests/unit/test_fact_verification_engine.py

# Run with verbose output
pytest -v
```

### Test Coverage by Module
- ✅ Audit Log: 100%
- ✅ API Configuration: 97%
- ✅ Fact Verification Engine: 90%
- ✅ Intelligence Layer: 78%
- ✅ Change Detector: 68%

---

## 📁 Project Structure

```
vigro/
├── src/verigov/              # Main source code
│   ├── collection/           # Source collection & whitelist
│   ├── config/               # API configuration
│   ├── infrastructure/       # Audit logging
│   ├── monitoring/           # Change detection
│   ├── verification/         # Fact verification & AI
│   ├── output/               # Output generation (planned)
│   ├── dashboard/            # Dashboard (planned)
│   ├── pipeline/             # Pipeline orchestration (planned)
│   └── main.py               # CLI application
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── property/             # Property-based tests
│   └── integration/          # Integration tests
├── examples/                 # Usage examples
│   ├── verify_claim.py
│   ├── monitor_sources.py
│   ├── generate_report.py
│   └── README.md
├── config/                   # Configuration files
│   └── whitelist.json        # Approved government sources
├── .env.example              # Environment template
├── requirements.txt          # Dependencies
├── setup.py                  # Package setup
└── README.md                 # This file
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Grok API Configuration
GROK_API_KEY=your_grok_api_key_here
GROK_API_URL=https://api.groq.com/openai/v1

# Logging Configuration
LOG_LEVEL=INFO
AUDIT_LOG_PATH=logs/audit.log

# Source Collection Configuration
COLLECTION_TIMEOUT=30
MAX_RETRIES=3
RETRY_BACKOFF_FACTOR=2

# Verification Configuration
MIN_CONFIDENCE_THRESHOLD=50
ENABLE_MULTI_AUTHORITY_VERIFICATION=true

# Change Detection Configuration
MONITORING_INTERVAL=3600
ENABLE_REAL_TIME_ALERTS=true
```

### Whitelist Configuration

Add approved government sources to `config/whitelist.json`:

```json
{
  "sources": [
    {
      "domain": "whitehouse.gov",
      "name": "The White House",
      "approved_by": "admin",
      "approved_date": "2026-02-20"
    }
  ]
}
```

---

## 🔒 Security Features

- ✅ Whitelist-only source collection
- ✅ SSL certificate validation
- ✅ API key encryption in environment variables
- ✅ Immutable audit logging
- ✅ No credentials in logs or outputs
- ✅ Input validation and sanitization

---

## 🛠️ Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -r requirements.txt

# Install package in editable mode
pip install -e .

# Run tests
pytest

# Generate coverage report
pytest --cov=src/verigov --cov-report=html
open htmlcov/index.html
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
pylint src/

# Type checking
mypy src/
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Grok AI** for providing the semantic analysis API
- **AWS** for hosting the hackathon
- **Python Community** for excellent libraries and tools

---

## 📧 Contact

**Project Maintainer:** Shreyash Shirkar  
**GitHub:** [@shreyashirkar25-rgb](https://github.com/shreyashirkar25-rgb)  
**Repository:** [vigro](https://github.com/shreyashirkar25-rgb/vigro)

---

## 🎯 Roadmap

- [ ] Web dashboard interface
- [ ] Real-time WebSocket notifications
- [ ] Multi-language support
- [ ] Advanced visualization tools
- [ ] API rate limiting and caching
- [ ] Docker containerization
- [ ] Cloud deployment (AWS)

---

**Built with ❤️ for transparent government information verification**
