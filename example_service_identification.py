#!/usr/bin/env python3
"""
Example: Complete workflow for Grafana panel analysis and service identification.

This script demonstrates:
1. Extracting panel information from a Grafana URL
2. Identifying which service the panel belongs to using AI (Cursor Agent)
"""

from grafana_integration import GrafanaClient, identify_service_from_panel, format_panel_info
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


def analyze_grafana_panel(panel_url: str, possible_services: list[str]):
    """
    Complete workflow: Extract panel info and identify service.
    
    Args:
        panel_url: Grafana panel URL
        possible_services: List of possible service names
    """
    # Configuration
    GRAFANA_BASE_URL = os.getenv("GRAFANA_BASE_URL", "http://grafana-k8s-ci.myntra.com")
    GRAFANA_API_TOKEN = os.getenv("GRAFANA_API_TOKEN")
    CURSOR_API_URL = os.getenv("CURSOR_API_URL", "http://localhost:9000")
    
    if not GRAFANA_API_TOKEN:
        print("❌ Error: GRAFANA_API_TOKEN not found in environment variables.")
        print("   Please set it in your .env file: GRAFANA_API_TOKEN=your_token_here")
        return None
    
    print("="*80)
    print("GRAFANA PANEL ANALYSIS AND SERVICE IDENTIFICATION")
    print("="*80)
    print(f"\nPanel URL: {panel_url}")
    print(f"Possible Services: {', '.join(possible_services)}")
    print()
    
    # Step 1: Extract panel information
    print("STEP 1: Extracting panel information from Grafana...")
    print("-" * 80)
    
    try:
        client = GrafanaClient(GRAFANA_BASE_URL, GRAFANA_API_TOKEN)
        panel_info = client.get_panel_info_from_url(panel_url)
        
        print(f"✅ Successfully extracted panel information")
        print(f"\nPanel Details:")
        print(f"  Dashboard: {panel_info['dashboard_title']}")
        print(f"  Panel: {panel_info['panel_title']}")
        print(f"  Type: {panel_info['panel_type']}")
        print(f"  Queries: {len(panel_info.get('targets', []))}")
        print(f"  Variables used: {len(panel_info.get('variables_used_in_panel', []))}")
        
        if panel_info.get('variables_used_in_panel'):
            print(f"    - {', '.join(panel_info['variables_used_in_panel'])}")
        
    except Exception as e:
        print(f"❌ Failed to extract panel information: {e}")
        return None
    
    # Step 2: Identify service using AI
    print("\n" + "="*80)
    print("STEP 2: Identifying service using Cursor AI (gemini-2.5-flash)...")
    print("-" * 80)
    
    try:
        service_result = identify_service_from_panel(
            panel_info,
            possible_services,
            cursor_api_url=CURSOR_API_URL,
            model="auto"
        )
        
        print(f"✅ Service identification completed\n")
        print(f"🎯 Identified Service: {service_result['service'].upper()}")
        print(f"   Confidence Level: {service_result['confidence']}")
        print(f"\n📝 Reasoning:")
        # Word wrap the reasoning
        reasoning = service_result['reasoning']
        words = reasoning.split()
        line = "   "
        for word in words:
            if len(line) + len(word) + 1 > 78:
                print(line)
                line = "   " + word
            else:
                line += (" " if line != "   " else "") + word
        if line != "   ":
            print(line)
        
        print(f"\n   Model: {service_result.get('model_used', 'N/A')}")
        
        return {
            'panel_info': panel_info,
            'service_result': service_result
        }
        
    except Exception as e:
        print(f"❌ Service identification failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure the Cursor API server is running: python main.py")
        print("  2. Check that the server is accessible at http://localhost:9000")
        print("  3. Verify the CURSOR_API_KEY environment variable is set")
        return None


def main():
    """Main entry point."""
    # Example panel URLs
    EXAMPLE_PANELS = [
        "https://grafana-k8s-ci.myntra.com/d/icutU1eVk/oms-prometheus?orgId=1&from=now-30m&to=now&viewPanel=102",
        # Add more example URLs here
    ]
    
    POSSIBLE_SERVICES = ["oms", "awh", "crs"]
    
    # Use command-line argument if provided
    if len(sys.argv) > 1:
        panel_url = sys.argv[1]
    else:
        panel_url = EXAMPLE_PANELS[0]
        print("(Using default example URL. You can pass a custom URL as argument.)")
        print()
    
    # Run analysis
    result = analyze_grafana_panel(panel_url, POSSIBLE_SERVICES)
    
    if result:
        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)
        print(f"✅ Success! Panel belongs to: {result['service_result']['service'].upper()}")
    else:
        print("\n" + "="*80)
        print("ANALYSIS FAILED")
        print("="*80)
        print("❌ Could not complete the analysis. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

