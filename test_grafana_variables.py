#!/usr/bin/env python3
"""
Test script to demonstrate Grafana variable extraction functionality.
"""

from grafana_integration import GrafanaClient, format_panel_info
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


def test_variable_detection():
    """Test the variable detection functionality."""
    print("=" * 80)
    print("Testing Variable Detection")
    print("=" * 80)
    
    # Configuration
    GRAFANA_BASE_URL = os.getenv("GRAFANA_BASE_URL", "http://grafana-k8s-ci.myntra.com")
    GRAFANA_API_TOKEN = os.getenv("GRAFANA_API_TOKEN")
    
    if not GRAFANA_API_TOKEN:
        print("❌ Error: GRAFANA_API_TOKEN not found in environment variables.")
        print("   Please set it in your .env file: GRAFANA_API_TOKEN=your_token_here")
        return False
    
    # Test with the actual panel URL
    PANEL_URL = "https://grafana-k8s-ci.myntra.com/d/icutU1eVk/oms-prometheus?orgId=1&from=now-30m&to=now&viewPanel=102"
    
    # Create client
    client = GrafanaClient(GRAFANA_BASE_URL, GRAFANA_API_TOKEN)
    
    try:
        print(f"\nFetching panel information from:")
        print(f"  {PANEL_URL}\n")
        
        # Get panel info
        panel_info = client.get_panel_info_from_url(PANEL_URL)
        
        # Print formatted output
        print("\n" + "=" * 80)
        print("FORMATTED OUTPUT")
        print("=" * 80)
        print(format_panel_info(panel_info))
        
        # Print variable-specific information
        print("\n" + "=" * 80)
        print("VARIABLE ANALYSIS")
        print("=" * 80)
        
        all_vars = panel_info.get('dashboard_variables', [])
        used_vars = panel_info.get('variables_used_in_panel', [])
        
        print(f"\nTotal dashboard variables: {len(all_vars)}")
        print(f"Variables used in this panel: {len(used_vars)}")
        
        if used_vars:
            print(f"\nUsed variables: {', '.join(used_vars)}")
            
            print("\nVariable details:")
            for var in panel_info.get('variables_used_definitions', []):
                print(f"\n  ${var['name']}:")
                print(f"    Type: {var['type']}")
                if var.get('current'):
                    print(f"    Current: {var['current'].get('value', 'N/A')}")
                if var.get('query'):
                    print(f"    Query: {var['query'][:80]}{'...' if len(str(var['query'])) > 80 else ''}")
        
        # Query-level variable usage
        print("\n" + "=" * 80)
        print("QUERY-LEVEL VARIABLE USAGE")
        print("=" * 80)
        
        for idx, target in enumerate(panel_info.get('targets', []), 1):
            print(f"\nQuery #{idx} (Ref: {target['ref_id']}):")
            print(f"  Type: {target.get('query_type', 'unknown')}")
            if target.get('variables_used'):
                print(f"  Variables used: {', '.join(target['variables_used'])}")
            else:
                print("  Variables used: None")
            if target.get('query'):
                query_preview = str(target['query'])[:100]
                print(f"  Query: {query_preview}{'...' if len(str(target['query'])) > 100 else ''}")
        
        # Print raw JSON for debugging
        print("\n" + "=" * 80)
        print("RAW JSON OUTPUT (truncated)")
        print("=" * 80)
        
        # Create a truncated version for display
        truncated_info = {
            'panel_id': panel_info['panel_id'],
            'panel_title': panel_info['panel_title'],
            'dashboard_title': panel_info['dashboard_title'],
            'variables_used_in_panel': panel_info.get('variables_used_in_panel', []),
            'total_dashboard_variables': len(panel_info.get('dashboard_variables', [])),
            'total_queries': len(panel_info.get('targets', []))
        }
        print(json.dumps(truncated_info, indent=2))
        
        print("\n" + "=" * 80)
        print("TEST COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_variable_parsing():
    """Test the variable parsing regex."""
    print("\n" + "=" * 80)
    print("Testing Variable Pattern Matching")
    print("=" * 80)
    
    client = GrafanaClient("http://example.com", "fake-token")
    
    test_queries = [
        "rate(cpu_usage{namespace=\"$namespace\"}[5m])",
        "sum by (pod) (container_memory_usage{pod=~\"$pod\", namespace=\"${namespace}\"})",
        "SELECT * FROM table WHERE id = $id AND name = ${name}",
        "metric{label=\"value\"}",  # No variables
        "avg(metric{env=\"$env\", dc=\"$datacenter\", interval=\"$__interval\"})",
    ]
    
    for query in test_queries:
        variables = client.find_variables_in_query(query)
        print(f"\nQuery: {query}")
        print(f"Variables found: {variables if variables else 'None'}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Test variable pattern matching
    test_variable_parsing()
    
    # Test full integration (requires network access and valid token)
    print("\n\n")
    test_variable_detection()


