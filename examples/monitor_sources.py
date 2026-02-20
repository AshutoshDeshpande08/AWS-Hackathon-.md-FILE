"""
Example: Continuous Source Monitoring

This example demonstrates how to continuously monitor government sources
for changes, updates, and policy modifications.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from verigov.main import VeriGovApp


def main():
    """Monitor sources for changes example."""
    
    print("="*60)
    print("VeriGov AI - Continuous Source Monitoring Example")
    print("="*60)
    
    # Initialize the application
    print("\n1. Initializing VeriGov AI system...")
    app = VeriGovApp()
    
    # Define sources to monitor
    sources = [
        "https://www.whitehouse.gov/briefing-room/",
        "https://www.congress.gov/",
        "https://www.regulations.gov/"
    ]
    
    print(f"\n2. Monitoring {len(sources)} government sources:")
    for source in sources:
        print(f"   - {source}")
    
    # Set monitoring interval (in seconds)
    interval = 300  # Check every 5 minutes
    
    print(f"\n3. Monitoring interval: {interval} seconds ({interval//60} minutes)")
    print("\n4. Starting continuous monitoring...")
    print("   Press Ctrl+C to stop\n")
    print("="*60)
    
    try:
        # Start monitoring
        app.monitor_sources(sources, interval)
    
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("Monitoring stopped by user")
        print("="*60)
        
        # Show monitoring summary
        print("\n5. Generating monitoring summary...")
        
        # Get all changes from audit log
        changes = app.audit_log.query_logs({
            'event_type': 'change_detected'
        })
        
        print(f"\nTotal changes detected: {len(changes)}")
        
        if changes:
            print("\nRecent changes:")
            for entry in changes[-5:]:  # Show last 5 changes
                details = entry.details
                print(f"\n  Source: {details.get('source_url')}")
                print(f"  Type: {details.get('change_type')}")
                print(f"  Impact: {details.get('impact_level')}")
                print(f"  Summary: {details.get('summary')}")
                print(f"  Time: {entry.timestamp}")
        
        # Export audit log
        print("\n6. Exporting audit log...")
        app.export_audit_log("monitoring_audit.json")
        print("   Audit log saved to: monitoring_audit.json")
        
        print("\n✓ Example complete!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
