# VeriGov AI - Usage Examples

This directory contains example scripts demonstrating how to use VeriGov AI for various verification tasks.

## Prerequisites

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env and add your Grok API key
   ```

## Examples

### 1. Single Claim Verification (`verify_claim.py`)

Demonstrates how to verify a single claim against official government sources.

**Usage:**
```bash
python examples/verify_claim.py
```

**What it does:**
- Initializes the VeriGov AI system
- Verifies a sample claim about federal minimum wage
- Displays verification results with confidence scores
- Exports audit log

**Output:**
- Console output with verification results
- `verification_audit.json` - Audit log of the verification process

---

### 2. Continuous Source Monitoring (`monitor_sources.py`)

Shows how to continuously monitor government sources for changes and updates.

**Usage:**
```bash
python examples/monitor_sources.py
```

**What it does:**
- Monitors multiple government websites
- Detects policy changes, updates, and modifications
- Generates real-time alerts for detected changes
- Tracks version history

**Output:**
- Real-time console alerts for changes
- `monitoring_audit.json` - Complete monitoring history

**Note:** Press `Ctrl+C` to stop monitoring and see the summary.

---

### 3. Batch Verification & Report Generation (`generate_report.py`)

Demonstrates batch verification of multiple claims and report generation.

**Usage:**
```bash
python examples/generate_report.py
```

**What it does:**
- Verifies multiple claims in batch
- Generates comprehensive verification reports
- Creates both JSON and Markdown outputs
- Provides summary statistics

**Output:**
- `verification_results.json` - Structured verification data
- `verification_report.md` - Human-readable report
- `report_audit.json` - Audit trail

---

## Using the CLI

VeriGov AI also provides a command-line interface for direct usage:

### Verify a Single Claim
```bash
python -m verigov.main verify "The minimum wage is $15/hour"
```

### Verify with Specific Sources
```bash
python -m verigov.main verify "Policy X was updated" \
  --sources https://example.gov/policy
```

### Batch Verification
```bash
# Create a file with claims (one per line)
echo "Claim 1" > claims.txt
echo "Claim 2" >> claims.txt

# Run batch verification
python -m verigov.main batch claims.txt --output results.json
```

### Monitor Sources
```bash
python -m verigov.main monitor \
  --sources https://example.gov/policy \
  --interval 3600
```

### Interactive Mode
```bash
python -m verigov.main interactive
```

In interactive mode, you can:
- Type `verify <claim>` to verify claims
- Type `audit` to see audit log summary
- Type `help` for available commands
- Type `quit` to exit

### Export Audit Log
```bash
python -m verigov.main export-audit audit_log.json
```

---

## Customization

You can modify the examples to:

1. **Use different sources:**
   ```python
   sources = [
       "https://your-gov-source.gov/",
       "https://another-source.gov/"
   ]
   ```

2. **Adjust monitoring intervals:**
   ```python
   interval = 1800  # Check every 30 minutes
   ```

3. **Verify your own claims:**
   ```python
   claims = [
       "Your claim here",
       "Another claim"
   ]
   ```

4. **Customize report format:**
   Edit the `generate_markdown_report()` function in `generate_report.py`

---

## Troubleshooting

### "Intelligence layer initialization failed"
- Check that your Grok API key is set in `.env`
- Verify the API key is valid
- The system will run in limited mode without AI verification

### "Source not in whitelist"
- Add the source to `config/whitelist.json`
- Ensure the source passes SSL validation
- Check that the domain is a valid government source

### "Network error"
- Check your internet connection
- Verify the source URL is accessible
- Some government sites may have rate limiting

---

## Next Steps

- Review the [main README](../README.md) for system architecture
- Check the [configuration guide](../docs/configuration.md) for advanced setup
- See the [API documentation](../docs/api.md) for programmatic usage

---

## Support

For issues or questions:
1. Check the main documentation
2. Review the audit logs for detailed error information
3. Ensure all dependencies are installed correctly
