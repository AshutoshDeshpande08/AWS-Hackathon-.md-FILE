"""
Example: Generate Verification Report

This example demonstrates how to verify multiple claims and generate
a comprehensive report with verification results.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from verigov.main import VeriGovApp


def generate_markdown_report(results, output_file="verification_report.md"):
    """Generate a markdown report from verification results."""
    
    with open(output_file, 'w') as f:
        # Header
        f.write("# VeriGov AI - Verification Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Total Claims Verified:** {len(results)}\n\n")
        
        # Summary statistics
        verified = sum(1 for r in results if r.get('status') == 'VERIFIED')
        partially = sum(1 for r in results if r.get('status') == 'PARTIALLY_VERIFIED')
        incorrect = sum(1 for r in results if r.get('status') == 'INCORRECT')
        unverified = sum(1 for r in results if r.get('status') == 'UNVERIFIED')
        
        f.write("## Summary\n\n")
        f.write(f"- ✓ Verified: {verified}\n")
        f.write(f"- ⚠ Partially Verified: {partially}\n")
        f.write(f"- ✗ Incorrect: {incorrect}\n")
        f.write(f"- ? Unverified: {unverified}\n\n")
        
        # Detailed results
        f.write("## Detailed Results\n\n")
        
        for i, result in enumerate(results, 1):
            status = result.get('status', 'UNKNOWN')
            
            # Status icon
            icon = {
                'VERIFIED': '✓',
                'PARTIALLY_VERIFIED': '⚠',
                'INCORRECT': '✗',
                'UNVERIFIED': '?'
            }.get(status, '?')
            
            f.write(f"### {i}. {icon} {status}\n\n")
            f.write(f"**Claim:** {result.get('claim')}\n\n")
            
            if 'confidence' in result:
                f.write(f"**Confidence Score:** {result.get('confidence')}%\n\n")
            
            if 'explanation' in result:
                f.write(f"**Explanation:** {result.get('explanation')}\n\n")
            
            if 'sources' in result and result['sources']:
                f.write("**Sources:**\n")
                for source in result['sources']:
                    f.write(f"- {source}\n")
                f.write("\n")
            
            if 'error' in result:
                f.write(f"**Error:** {result.get('error')}\n\n")
            
            f.write("---\n\n")
        
        # Footer
        f.write("## About VeriGov AI\n\n")
        f.write("VeriGov AI is a government information verification system that ")
        f.write("cross-references claims against official government sources using ")
        f.write("AI-powered semantic analysis.\n")


def main():
    """Generate verification report example."""
    
    print("="*60)
    print("VeriGov AI - Report Generation Example")
    print("="*60)
    
    # Initialize the application
    print("\n1. Initializing VeriGov AI system...")
    app = VeriGovApp()
    
    # Define claims to verify
    claims = [
        "The federal minimum wage is $7.25 per hour",
        "Social Security benefits are adjusted annually for inflation",
        "The Affordable Care Act was passed in 2010",
        "Medicare covers all prescription drugs at no cost",
        "The voting age in the United States is 18"
    ]
    
    # Define sources
    sources = [
        "https://www.dol.gov/",
        "https://www.ssa.gov/",
        "https://www.healthcare.gov/",
        "https://www.medicare.gov/",
        "https://www.usa.gov/"
    ]
    
    print(f"\n2. Verifying {len(claims)} claims...")
    print("\nClaims to verify:")
    for i, claim in enumerate(claims, 1):
        print(f"   {i}. {claim}")
    
    # Verify all claims
    print("\n3. Running batch verification...")
    results = app.verify_batch(claims, sources)
    
    # Display summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    verified = sum(1 for r in results if r.get('status') == 'VERIFIED')
    partially = sum(1 for r in results if r.get('status') == 'PARTIALLY_VERIFIED')
    incorrect = sum(1 for r in results if r.get('status') == 'INCORRECT')
    unverified = sum(1 for r in results if r.get('status') == 'UNVERIFIED')
    
    print(f"\nTotal Claims: {len(results)}")
    print(f"✓ Verified: {verified}")
    print(f"⚠ Partially Verified: {partially}")
    print(f"✗ Incorrect: {incorrect}")
    print(f"? Unverified: {unverified}")
    
    # Show individual results
    print("\n" + "="*60)
    print("INDIVIDUAL RESULTS")
    print("="*60)
    
    for i, result in enumerate(results, 1):
        status = result.get('status', 'UNKNOWN')
        icon = {
            'VERIFIED': '✓',
            'PARTIALLY_VERIFIED': '⚠',
            'INCORRECT': '✗',
            'UNVERIFIED': '?'
        }.get(status, '?')
        
        print(f"\n{i}. {icon} {status}")
        print(f"   Claim: {result.get('claim')}")
        if 'confidence' in result:
            print(f"   Confidence: {result.get('confidence')}%")
    
    # Save results
    print("\n" + "="*60)
    print("SAVING RESULTS")
    print("="*60)
    
    # Save JSON
    print("\n4. Saving JSON results...")
    with open("verification_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    print("   ✓ Saved to: verification_results.json")
    
    # Generate markdown report
    print("\n5. Generating markdown report...")
    generate_markdown_report(results, "verification_report.md")
    print("   ✓ Saved to: verification_report.md")
    
    # Export audit log
    print("\n6. Exporting audit log...")
    app.export_audit_log("report_audit.json")
    print("   ✓ Saved to: report_audit.json")
    
    print("\n" + "="*60)
    print("✓ Report generation complete!")
    print("="*60)
    print("\nGenerated files:")
    print("  - verification_results.json (JSON data)")
    print("  - verification_report.md (Markdown report)")
    print("  - report_audit.json (Audit log)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExample interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
