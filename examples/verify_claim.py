"""
Example: Single Claim Verification

This example demonstrates how to verify a single claim using VeriGov AI.
It shows basic usage of the verification system with official government sources.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from verigov.main import VeriGovApp


def main():
    """Verify a single claim example."""
    
    print("="*60)
    print("VeriGov AI - Single Claim Verification Example")
    print("="*60)
    
    # Initialize the application
    print("\n1. Initializing VeriGov AI system...")
    app = VeriGovApp()
    
    # Define the claim to verify
    claim = "The federal minimum wage in the United States is $7.25 per hour"
    
    # Define sources to check (optional)
    sources = [
        "https://www.dol.gov/agencies/whd/minimum-wage",
        "https://www.congress.gov/bill"
    ]
    
    print(f"\n2. Verifying claim:")
    print(f"   '{claim}'")
    print(f"\n3. Checking sources:")
    for source in sources:
        print(f"   - {source}")
    
    # Verify the claim
    print("\n4. Running verification...")
    result = app.verify_claim(claim, sources)
    
    # Display results
    print("\n" + "="*60)
    print("VERIFICATION RESULT")
    print("="*60)
    print(f"Claim: {result.get('claim')}")
    print(f"Status: {result.get('status')}")
    
    if 'confidence' in result:
        print(f"Confidence Score: {result.get('confidence')}%")
    
    if 'explanation' in result:
        print(f"\nExplanation:")
        print(f"  {result.get('explanation')}")
    
    if 'sources' in result and result['sources']:
        print(f"\nSupporting Sources:")
        for source in result['sources']:
            print(f"  - {source}")
    
    if 'error' in result:
        print(f"\nError: {result.get('error')}")
    
    print("="*60)
    
    # Export audit log
    print("\n5. Exporting audit log...")
    app.export_audit_log("verification_audit.json")
    print("   Audit log saved to: verification_audit.json")
    
    print("\n✓ Example complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExample interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
