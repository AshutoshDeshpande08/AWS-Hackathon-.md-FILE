"""
VeriGov AI - Main Application Entry Point

Command-line interface for running the government information verification system.
Supports single claim verification, batch processing, and continuous monitoring.

Requirements: 12.1, 12.5
"""

import argparse
import sys
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from verigov.config.api_configuration import APIConfiguration
from verigov.collection.source_collector import SourceCollector
from verigov.collection.source_whitelist import SourceWhitelist
from verigov.verification.intelligence_layer import IntelligenceLayer
from verigov.verification.fact_verification_engine import FactVerificationEngine
from verigov.monitoring.change_detector import ChangeDetector
from verigov.infrastructure.audit_log import AuditLog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VeriGovApp:
    """Main application class for VeriGov AI system."""
    
    def __init__(self, config_source: str = "env"):
        """
        Initialize VeriGov application with all components.
        
        Args:
            config_source: Configuration source ("env" or "file")
        """
        logger.info("Initializing VeriGov AI system...")
        
        # Initialize core components
        self.config = APIConfiguration(config_source=config_source)
        self.audit_log = AuditLog()
        self.whitelist = SourceWhitelist(whitelist_file="config/whitelist.json")
        self.source_collector = SourceCollector(
            whitelist=self.whitelist,
            audit_log=self.audit_log
        )
        
        # Initialize verification components
        try:
            self.intelligence_layer = IntelligenceLayer(api_config=self.config)
            self.verification_engine = FactVerificationEngine(
                intelligence_layer=self.intelligence_layer,
                audit_log=self.audit_log
            )
        except Exception as e:
            logger.warning(f"Intelligence layer initialization failed: {e}")
            logger.warning("Running in limited mode without AI verification")
            self.intelligence_layer = None
            self.verification_engine = None
        
        # Initialize monitoring
        self.change_detector = ChangeDetector(
            source_collector=self.source_collector,
            audit_log=self.audit_log
        )
        
        logger.info("VeriGov AI system initialized successfully")
    
    def verify_claim(
        self,
        claim: str,
        sources: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Verify a single claim against official sources.
        
        Args:
            claim: The claim to verify
            sources: Optional list of source URLs to check
            
        Returns:
            Verification result dictionary
        """
        logger.info(f"Verifying claim: {claim}")
        
        if not self.verification_engine:
            return {
                "error": "Verification engine not available",
                "claim": claim,
                "status": "UNVERIFIED"
            }
        
        # Collect data from sources
        collected_data = []
        if sources:
            for source_url in sources:
                try:
                    data = self.source_collector.collect_from_source(source_url)
                    if data:
                        collected_data.append(data)
                except Exception as e:
                    logger.error(f"Failed to collect from {source_url}: {e}")
        
        # Verify the claim
        try:
            result = self.verification_engine.verify_claim(claim, collected_data)
            
            return {
                "claim": claim,
                "status": result.status.value,
                "confidence": result.confidence_score,
                "reasoning": result.reasoning,
                "sources": [s for s in result.supporting_sources],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {
                "error": str(e),
                "claim": claim,
                "status": "UNVERIFIED"
            }
    
    def verify_batch(
        self,
        claims: List[str],
        sources: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Verify multiple claims in batch.
        
        Args:
            claims: List of claims to verify
            sources: Optional list of source URLs
            
        Returns:
            List of verification results
        """
        logger.info(f"Batch verification of {len(claims)} claims")
        
        results = []
        for i, claim in enumerate(claims, 1):
            logger.info(f"Processing claim {i}/{len(claims)}")
            result = self.verify_claim(claim, sources)
            results.append(result)
        
        return results
    
    def monitor_sources(
        self,
        source_urls: List[str],
        interval: int = 3600
    ) -> None:
        """
        Continuously monitor sources for changes.
        
        Args:
            source_urls: List of source URLs to monitor
            interval: Monitoring interval in seconds
        """
        logger.info(f"Starting continuous monitoring of {len(source_urls)} sources")
        logger.info(f"Monitoring interval: {interval} seconds")
        
        try:
            import time
            while True:
                changes = self.change_detector.monitor_all_sources(source_urls)
                
                if changes:
                    logger.info(f"Detected {len(changes)} changes")
                    for change in changes:
                        print(f"\n{'='*60}")
                        print(f"CHANGE DETECTED: {change.source_url}")
                        print(f"Type: {change.change_type.value}")
                        print(f"Impact: {change.impact_level.value}")
                        print(f"Summary: {change.summary}")
                        print(f"{'='*60}\n")
                else:
                    logger.info("No changes detected")
                
                logger.info(f"Waiting {interval} seconds until next check...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
    
    def export_audit_log(self, filepath: str) -> None:
        """
        Export audit log to file.
        
        Args:
            filepath: Path to export file
        """
        logger.info(f"Exporting audit log to {filepath}")
        self.audit_log.export_to_json(filepath)
        logger.info("Audit log exported successfully")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="VeriGov AI - Government Information Verification System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify a single claim
  python -m verigov.main verify "The minimum wage is $15/hour"
  
  # Verify with specific sources
  python -m verigov.main verify "Policy X was updated" --sources https://example.gov/policy
  
  # Batch verification from file
  python -m verigov.main batch claims.txt --sources sources.txt
  
  # Monitor sources for changes
  python -m verigov.main monitor --sources https://example.gov/policy --interval 3600
  
  # Export audit log
  python -m verigov.main export-audit audit_log.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify a single claim')
    verify_parser.add_argument('claim', help='Claim to verify')
    verify_parser.add_argument(
        '--sources',
        nargs='+',
        help='Source URLs to check'
    )
    verify_parser.add_argument(
        '--output',
        help='Output file for results (JSON)'
    )
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Verify multiple claims')
    batch_parser.add_argument('claims_file', help='File containing claims (one per line)')
    batch_parser.add_argument(
        '--sources',
        help='File containing source URLs (one per line)'
    )
    batch_parser.add_argument(
        '--output',
        help='Output file for results (JSON)',
        required=True
    )
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Monitor sources for changes')
    monitor_parser.add_argument(
        '--sources',
        nargs='+',
        required=True,
        help='Source URLs to monitor'
    )
    monitor_parser.add_argument(
        '--interval',
        type=int,
        default=3600,
        help='Monitoring interval in seconds (default: 3600)'
    )
    
    # Export audit log command
    export_parser = subparsers.add_parser('export-audit', help='Export audit log')
    export_parser.add_argument('output', help='Output file path')
    
    # Interactive mode
    subparsers.add_parser('interactive', help='Start interactive mode')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize application
    try:
        app = VeriGovApp()
    except Exception as e:
        logger.error(f"Failed to initialize VeriGov: {e}")
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == 'verify':
            result = app.verify_claim(args.claim, args.sources)
            
            # Print result
            print(f"\n{'='*60}")
            print(f"VERIFICATION RESULT")
            print(f"{'='*60}")
            print(f"Claim: {result.get('claim')}")
            print(f"Status: {result.get('status')}")
            if 'confidence' in result:
                print(f"Confidence: {result.get('confidence')}%")
            if 'reasoning' in result:
                print(f"Reasoning: {result.get('reasoning')}")
            if 'sources' in result and result['sources']:
                print(f"Sources: {', '.join(result['sources'])}")
            if 'error' in result:
                print(f"Error: {result.get('error')}")
            print(f"{'='*60}\n")
            
            # Save to file if requested
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2)
                logger.info(f"Result saved to {args.output}")
        
        elif args.command == 'batch':
            # Read claims
            with open(args.claims_file, 'r') as f:
                claims = [line.strip() for line in f if line.strip()]
            
            # Read sources if provided
            sources = None
            if args.sources:
                with open(args.sources, 'r') as f:
                    sources = [line.strip() for line in f if line.strip()]
            
            # Verify batch
            results = app.verify_batch(claims, sources)
            
            # Save results
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Batch verification complete. Results saved to {args.output}")
            
            # Print summary
            verified = sum(1 for r in results if r.get('status') == 'VERIFIED')
            print(f"\nBatch Summary:")
            print(f"Total claims: {len(results)}")
            print(f"Verified: {verified}")
            print(f"Results saved to: {args.output}")
        
        elif args.command == 'monitor':
            app.monitor_sources(args.sources, args.interval)
        
        elif args.command == 'export-audit':
            app.export_audit_log(args.output)
        
        elif args.command == 'interactive':
            print("\n" + "="*60)
            print("VeriGov AI - Interactive Mode")
            print("="*60)
            print("Type 'help' for commands, 'quit' to exit\n")
            
            while True:
                try:
                    user_input = input("verigov> ").strip()
                    
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("Goodbye!")
                        break
                    
                    if user_input.lower() == 'help':
                        print("\nAvailable commands:")
                        print("  verify <claim>  - Verify a claim")
                        print("  audit          - Show audit log summary")
                        print("  help           - Show this help")
                        print("  quit           - Exit interactive mode\n")
                        continue
                    
                    if user_input.lower().startswith('verify '):
                        claim = user_input[7:].strip()
                        result = app.verify_claim(claim)
                        print(f"\nStatus: {result.get('status')}")
                        if 'confidence' in result:
                            print(f"Confidence: {result.get('confidence')}%")
                        if 'reasoning' in result:
                            print(f"Reasoning: {result.get('reasoning')}\n")
                        continue
                    
                    if user_input.lower() == 'audit':
                        entries = app.audit_log.get_all_entries()
                        print(f"\nAudit Log: {len(entries)} entries")
                        if entries:
                            print(f"Latest: {entries[-1].event_type} at {entries[-1].timestamp}\n")
                        continue
                    
                    print(f"Unknown command: {user_input}")
                    print("Type 'help' for available commands\n")
                    
                except KeyboardInterrupt:
                    print("\nUse 'quit' to exit")
                except Exception as e:
                    print(f"Error: {e}\n")
    
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
