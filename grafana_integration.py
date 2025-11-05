#!/usr/bin/env python3
"""
Grafana Integration Module
Extracts panel name and query from a Grafana dashboard panel link.

Example panel link: http://grafana-k8s-ci.myntra.com/d/fRBY-tz7a?orgId=1&viewPanel=172
"""

import re
import json
import logging
import os
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional, Tuple, List
import requests
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('grafana_integration.log')
    ]
)
logger = logging.getLogger(__name__)


class GrafanaClient:
    """Client for interacting with Grafana HTTP API."""
    
    def __init__(self, base_url: str, api_token: str):
        """
        Initialize Grafana client.
        
        Args:
            base_url: Base URL of Grafana instance (e.g., http://grafana-k8s-ci.myntra.com)
            api_token: Service account API token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def parse_panel_url(self, panel_url: str) -> Tuple[str, str, Optional[str]]:
        """
        Parse Grafana panel URL to extract dashboard UID, panel ID, and org ID.
        
        Args:
            panel_url: Full Grafana panel URL
            
        Returns:
            Tuple of (dashboard_uid, panel_id, org_id)
            
        Example:
            http://grafana-k8s-ci.myntra.com/d/fRBY-tz7a?orgId=1&viewPanel=172
            Returns: ('fRBY-tz7a', '172', '1')
        """
        logger.debug(f"Parsing panel URL: {panel_url}")
        parsed = urlparse(panel_url)
        
        # Extract dashboard UID from path (e.g., /d/fRBY-tz7a)
        path_match = re.search(r'/d/([^/?]+)', parsed.path)
        if not path_match:
            logger.error(f"Could not extract dashboard UID from URL: {panel_url}")
            raise ValueError(f"Could not extract dashboard UID from URL: {panel_url}")
        
        dashboard_uid = path_match.group(1)
        logger.debug(f"Extracted dashboard UID: {dashboard_uid}")
        
        # Extract query parameters
        query_params = parse_qs(parsed.query)
        
        # Extract panel ID from viewPanel parameter
        panel_id = query_params.get('viewPanel', [None])[0]
        if not panel_id:
            logger.error(f"No viewPanel parameter found in URL: {panel_url}")
            raise ValueError(f"No viewPanel parameter found in URL: {panel_url}")
        
        # Extract org ID (optional)
        org_id = query_params.get('orgId', [None])[0]
        
        logger.info(f"Parsed URL - Dashboard: {dashboard_uid}, Panel: {panel_id}, Org: {org_id}")
        return dashboard_uid, panel_id, org_id
    
    def get_dashboard(self, dashboard_uid: str, org_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch dashboard data from Grafana API.
        
        Args:
            dashboard_uid: Dashboard UID
            org_id: Optional organization ID
            
        Returns:
            Dashboard data as dictionary
        """
        url = f"{self.base_url}/api/dashboards/uid/{dashboard_uid}"
        logger.info(f"Fetching dashboard: {dashboard_uid} from {self.base_url}")
        
        headers = self.headers.copy()
        if org_id:
            headers['X-Grafana-Org-Id'] = org_id
            logger.debug(f"Using org ID: {org_id}")
        
        try:
            response = requests.get(url, headers=headers)
            logger.debug(f"API response status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}", exc_info=True)
            raise ValueError(f"Failed to connect to Grafana: {str(e)}")
        
        if response.status_code == 404:
            logger.error(f"Dashboard not found: {dashboard_uid}")
            raise ValueError(f"Dashboard not found: {dashboard_uid}")
        elif response.status_code == 401:
            logger.error("Authentication failed")
            raise ValueError("Authentication failed. Please check your API token.")
        elif response.status_code == 403:
            logger.error("Access denied")
            raise ValueError("Access denied. Please check your permissions.")
        elif response.status_code != 200:
            logger.error(f"API error: {response.status_code} - {response.text}")
            raise ValueError(f"Failed to fetch dashboard: {response.status_code} - {response.text}")
        
        logger.info(f"Successfully fetched dashboard: {dashboard_uid}")
        return response.json()
    
    def find_panel_by_id(self, dashboard_data: Dict[str, Any], panel_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a panel in dashboard data by its ID.
        
        Args:
            dashboard_data: Dashboard data from API
            panel_id: Panel ID to find
            
        Returns:
            Panel data if found, None otherwise
        """
        logger.debug(f"Searching for panel ID: {panel_id}")
        dashboard = dashboard_data.get('dashboard', {})
        panels = dashboard.get('panels', [])
        logger.debug(f"Dashboard has {len(panels)} top-level panels")
        
        panel_id_int = int(panel_id)
        
        # Search through panels (including nested panels in rows)
        def search_panels(panel_list, depth=0):
            logger.debug(f"Searching {len(panel_list)} panels at depth {depth}")
            for panel in panel_list:
                if panel.get('id') == panel_id_int:
                    logger.info(f"Found panel {panel_id} at depth {depth}")
                    return panel
                
                # Check for nested panels (e.g., in row panels)
                if panel.get('type') == 'row' and 'panels' in panel:
                    nested_result = search_panels(panel['panels'], depth + 1)
                    if nested_result:
                        return nested_result
                
                # Check for panels property
                if 'panels' in panel:
                    nested_result = search_panels(panel['panels'], depth + 1)
                    if nested_result:
                        return nested_result
            
            return None
        
        result = search_panels(panels)
        if not result:
            logger.warning(f"Panel {panel_id} not found in dashboard")
        return result
    
    def extract_dashboard_variables(self, dashboard_data: Dict[str, Any]) -> list[Dict[str, Any]]:
        """
        Extract dashboard template variables.
        
        Args:
            dashboard_data: Dashboard data from API
            
        Returns:
            List of variable definitions
        """
        dashboard = dashboard_data.get('dashboard', {})
        templating = dashboard.get('templating', {})
        variables = templating.get('list', [])
        
        logger.info(f"Found {len(variables)} dashboard variables")
        
        variable_info = []
        for var in variables:
            var_data = {
                'name': var.get('name'),
                'type': var.get('type'),
                'label': var.get('label'),
                'current': var.get('current'),
                'query': var.get('query'),
                'datasource': var.get('datasource'),
                'multi': var.get('multi', False),
                'includeAll': var.get('includeAll', False),
                'hide': var.get('hide', 0),
                'options': var.get('options', [])
            }
            
            # For query variables, include more details
            if var.get('type') == 'query':
                var_data['refresh'] = var.get('refresh')
                var_data['regex'] = var.get('regex')
                
            logger.debug(f"Variable: {var_data['name']} (type: {var_data['type']})")
            variable_info.append(var_data)
        
        return variable_info
    
    def find_variables_in_query(self, query_string: str) -> list[str]:
        """
        Find variable references in a query string.
        Variables in Grafana are referenced as $varname or ${varname}
        
        Args:
            query_string: Query string to search
            
        Returns:
            List of variable names found in the query
        """
        if not query_string:
            return []
        
        # Match $varname or ${varname} patterns
        pattern = r'\$\{?(\w+)\}?'
        matches = re.findall(pattern, str(query_string))
        
        # Remove duplicates and common built-in variables
        built_in_vars = {'__interval', '__interval_ms', '__from', '__to', '__range', '__rate_interval'}
        variables = list(set(matches) - built_in_vars)
        
        return variables
    
    def extract_panel_info(self, panel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract panel name and queries from panel data.
        
        Args:
            panel_data: Panel data from dashboard
            
        Returns:
            Dictionary containing panel information
        """
        panel_id = panel_data.get('id')
        panel_title = panel_data.get('title', 'Untitled Panel')
        logger.info(f"Extracting info for panel: {panel_title} (ID: {panel_id})")
        
        info = {
            'panel_id': panel_id,
            'panel_title': panel_title,
            'panel_type': panel_data.get('type', 'unknown'),
            'datasource': panel_data.get('datasource'),
            'targets': []
        }
        
        logger.debug(f"Panel type: {info['panel_type']}")
        
        # Extract queries/targets
        targets = panel_data.get('targets', [])
        logger.debug(f"Found {len(targets)} targets")
        
        all_variables_used = set()
        
        for idx, target in enumerate(targets, 1):
            target_info = {
                'ref_id': target.get('refId'),
                'datasource': target.get('datasource'),
                'query': None,
                'raw_query': target.get('expr') or target.get('query') or target.get('rawSql')
            }
            
            # Try to extract query based on datasource type
            if 'expr' in target:  # Prometheus
                target_info['query'] = target['expr']
                target_info['query_type'] = 'prometheus'
                logger.debug(f"Target {idx}: Prometheus query")
            elif 'query' in target:  # Generic query
                target_info['query'] = target['query']
                target_info['query_type'] = 'generic'
                logger.debug(f"Target {idx}: Generic query")
            elif 'rawSql' in target:  # SQL
                target_info['query'] = target['rawSql']
                target_info['query_type'] = 'sql'
                logger.debug(f"Target {idx}: SQL query")
            else:
                logger.warning(f"Target {idx}: Unknown query type")
            
            # Find variables used in this query
            variables_in_query = self.find_variables_in_query(target_info['query'])
            target_info['variables_used'] = variables_in_query
            all_variables_used.update(variables_in_query)
            
            # Include additional target properties
            target_info['legend_format'] = target.get('legendFormat')
            target_info['interval'] = target.get('interval')
            
            # Also check for variables in legend format
            if target_info['legend_format']:
                variables_in_legend = self.find_variables_in_query(target_info['legend_format'])
                all_variables_used.update(variables_in_legend)
            
            info['targets'].append(target_info)
        
        # Add list of all variables used in this panel
        info['variables_used_in_panel'] = sorted(list(all_variables_used))
        
        logger.info(f"Successfully extracted info for panel {panel_id} with {len(info['targets'])} queries and {len(all_variables_used)} variables")
        return info
    
    def get_panel_info_from_url(self, panel_url: str) -> Dict[str, Any]:
        """
        Main method to extract panel name and query from a panel URL.
        
        Args:
            panel_url: Full Grafana panel URL
            
        Returns:
            Dictionary containing panel information including name, queries, and variables
            
        Example:
            >>> client = GrafanaClient('http://grafana.example.com', 'token')
            >>> info = client.get_panel_info_from_url('http://grafana.example.com/d/xyz?viewPanel=5')
            >>> print(info['panel_title'])
            >>> print(info['targets'][0]['query'])
            >>> print(info['dashboard_variables'])
        """
        logger.info(f"Starting panel info extraction from URL: {panel_url}")
        
        # Parse URL to extract identifiers
        dashboard_uid, panel_id, org_id = self.parse_panel_url(panel_url)
        
        # Fetch dashboard data
        dashboard_data = self.get_dashboard(dashboard_uid, org_id)
        
        # Find the specific panel
        panel_data = self.find_panel_by_id(dashboard_data, panel_id)
        
        if not panel_data:
            error_msg = f"Panel with ID {panel_id} not found in dashboard {dashboard_uid}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Extract panel information
        panel_info = self.extract_panel_info(panel_data)
        
        # Extract dashboard variables
        dashboard_variables = self.extract_dashboard_variables(dashboard_data)
        panel_info['dashboard_variables'] = dashboard_variables
        
        # Filter to only variables used in this panel
        variables_used = panel_info.get('variables_used_in_panel', [])
        panel_info['variables_used_definitions'] = [
            var for var in dashboard_variables 
            if var['name'] in variables_used
        ]
        
        # Add metadata
        dashboard_title = dashboard_data.get('dashboard', {}).get('title', 'Unknown')
        panel_info['dashboard_uid'] = dashboard_uid
        panel_info['dashboard_title'] = dashboard_title
        panel_info['url'] = panel_url
        
        logger.info(f"Successfully extracted panel info: {panel_info['panel_title']} from {dashboard_title} with {len(dashboard_variables)} dashboard variables")
        return panel_info


def identify_service_from_panel(
    panel_info: Dict[str, Any],
    possible_services: List[str],
    cursor_api_url: str = "http://localhost:9000",
    model: str = "gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Use Cursor Agent AI to identify which service a panel belongs to.
    
    Args:
        panel_info: Panel information dictionary from get_panel_info_from_url()
        possible_services: List of possible service names (e.g., ['oms', 'awh', 'crs'])
        cursor_api_url: Base URL of the Cursor API server
        model: Model to use for inference (default: gemini-2.5-flash)
        
    Returns:
        Dictionary containing:
        - service: The identified service name
        - confidence: Confidence level (if available)
        - reasoning: Explanation of why this service was identified
        - raw_response: Full response from the AI
        
    Example:
        >>> panel_info = client.get_panel_info_from_url(panel_url)
        >>> result = identify_service_from_panel(panel_info, ['oms', 'awh', 'crs'])
        >>> print(f"Service: {result['service']}")
        >>> print(f"Reasoning: {result['reasoning']}")
    """
    logger.info(f"Identifying service for panel: {panel_info['panel_title']}")
    logger.debug(f"Possible services: {possible_services}")
    
    # Build the prompt with panel information
    prompt_parts = [
        "# Service Identification Task",
        "",
        f"Analyze the following Grafana panel and determine which service it belongs to.",
        f"",
        f"## Panel Information",
        f"- **Dashboard**: {panel_info.get('dashboard_title')}",
        f"- **Panel Title**: {panel_info.get('panel_title')}",
        f"- **Panel Type**: {panel_info.get('panel_type')}",
        f"- **Datasource**: {panel_info.get('datasource')}",
        "",
        f"## Queries",
    ]
    
    # Add query information
    for idx, target in enumerate(panel_info.get('targets', []), 1):
        prompt_parts.append(f"\n### Query {idx} (Ref: {target.get('ref_id')})")
        prompt_parts.append(f"- **Type**: {target.get('query_type', 'unknown')}")
        if target.get('query'):
            prompt_parts.append(f"- **Query**: `{target['query']}`")
        if target.get('legend_format'):
            prompt_parts.append(f"- **Legend Format**: `{target['legend_format']}`")
        if target.get('variables_used'):
            prompt_parts.append(f"- **Variables Used**: {', '.join(target['variables_used'])}")
    
    # Add variable information if available
    if panel_info.get('variables_used_in_panel'):
        prompt_parts.append("\n## Dashboard Variables Used")
        for var in panel_info.get('variables_used_definitions', []):
            prompt_parts.append(f"\n### ${var['name']}")
            prompt_parts.append(f"- **Type**: {var['type']}")
            if var.get('query'):
                prompt_parts.append(f"- **Query**: `{var['query']}`")
            if var.get('current'):
                prompt_parts.append(f"- **Current Value**: {var['current'].get('value', 'N/A')}")
    
    prompt_parts.extend([
        "",
        f"## Possible Services",
        f"The panel must belong to ONE of these services:",
    ])
    
    # Add service descriptions
    service_descriptions = {
        'oms': 'OMS (Order Management System) - handles order processing, order lifecycle, order fulfillment',
        'awh': 'AWH (Assign Warehouse) - handles warehouse assignment, inventory allocation, warehouse selection',
        'crs': 'CRS (Customer Relationship Service) - handles customer data, customer interactions, customer support'
    }
    
    for service in possible_services:
        desc = service_descriptions.get(service.lower(), f"{service} service")
        prompt_parts.append(f"- **{service}**: {desc}")
    
    prompt_parts.extend([
        "",
        "## Instructions",
        "Based on the panel title, queries, metrics, labels, and variables:",
        "1. Identify which service this panel most likely belongs to",
        "2. Provide your reasoning based on:",
        "   - Metric names and patterns",
        "   - Variable names",
        "   - Query labels and filters",
        "   - Panel title and dashboard context",
        "3. Be confident in your decision",
        "",
        "## Response Format",
        "Respond in JSON format:",
        "```json",
        "{",
        '  "service": "service_name",',
        '  "confidence": "high|medium|low",',
        '  "reasoning": "Explanation of why this service was identified"',
        "}",
        "```",
        "",
        "Only respond with the JSON object, nothing else."
    ])
    
    prompt = "\n".join(prompt_parts)
    logger.debug(f"Prompt length: {len(prompt)} characters")
    
    # Make request to Cursor API
    api_endpoint = f"{cursor_api_url.rstrip('/')}/api/chat"
    
    payload = {
        "message": prompt,
        "model": model,
        "session_id": None  # Use a new session each time
    }
    
    logger.info(f"Calling Cursor API at {api_endpoint} with model {model}")
    
    try:
        response = requests.post(
            api_endpoint,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        
        if response.status_code != 200:
            logger.error(f"Cursor API error: {response.status_code} - {response.text}")
            raise ValueError(f"Cursor API request failed: {response.status_code} - {response.text}")
        
        api_response = response.json()
        ai_response = api_response.get('response', '')
        
        logger.info(f"Received response from Cursor API (length: {len(ai_response)} chars)")
        logger.debug(f"Raw AI response: {ai_response[:500]}...")
        
        # Parse the JSON response from AI
        # Extract JSON from markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', ai_response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{[\s\S]*"service"[\s\S]*\}', ai_response)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = ai_response
        
        try:
            parsed_result = json.loads(json_str)
            service = parsed_result.get('service', '').lower()
            confidence = parsed_result.get('confidence', 'unknown')
            reasoning = parsed_result.get('reasoning', '')
            
            logger.info(f"Identified service: {service} (confidence: {confidence})")
            
            # Validate that the identified service is in the possible services list
            if service not in [s.lower() for s in possible_services]:
                logger.warning(f"AI identified service '{service}' not in possible services: {possible_services}")
            
            return {
                'service': service,
                'confidence': confidence,
                'reasoning': reasoning,
                'raw_response': ai_response,
                'session_id': api_response.get('session_id'),
                'model_used': api_response.get('model')
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Attempted to parse: {json_str}")
            
            # Fallback: try to extract service name from text
            for service in possible_services:
                if service.lower() in ai_response.lower():
                    logger.info(f"Fallback: found service '{service}' in response text")
                    return {
                        'service': service.lower(),
                        'confidence': 'low',
                        'reasoning': 'Extracted from text response (JSON parsing failed)',
                        'raw_response': ai_response,
                        'session_id': api_response.get('session_id'),
                        'model_used': api_response.get('model')
                    }
            
            raise ValueError(f"Could not parse service identification from AI response: {ai_response[:200]}")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to Cursor API: {e}", exc_info=True)
        raise ValueError(f"Failed to connect to Cursor API at {api_endpoint}: {str(e)}")





def format_panel_info(panel_info: Dict[str, Any]) -> str:
    """
    Format panel information as a human-readable string.
    
    Args:
        panel_info: Panel information dictionary
        
    Returns:
        Formatted string
    """
    lines = [
        f"Dashboard: {panel_info.get('dashboard_title')} ({panel_info.get('dashboard_uid')})",
        f"Panel ID: {panel_info.get('panel_id')}",
        f"Panel Title: {panel_info.get('panel_title')}",
        f"Panel Type: {panel_info.get('panel_type')}",
        ""
    ]
    
    if panel_info.get('datasource'):
        lines.append(f"Datasource: {panel_info.get('datasource')}")
        lines.append("")
    
    # Display queries
    targets = panel_info.get('targets', [])
    if targets:
        lines.append(f"Queries ({len(targets)}):")
        for i, target in enumerate(targets, 1):
            lines.append(f"\n  Query #{i}:")
            lines.append(f"    Ref ID: {target.get('ref_id')}")
            if target.get('query_type'):
                lines.append(f"    Type: {target.get('query_type')}")
            if target.get('query'):
                lines.append(f"    Query: {target.get('query')}")
            if target.get('legend_format'):
                lines.append(f"    Legend: {target.get('legend_format')}")
            if target.get('variables_used'):
                lines.append(f"    Variables used: {', '.join(target['variables_used'])}")
    else:
        lines.append("No queries found.")
    
    lines.append("")
    
    # Display variables used in this panel
    variables_used = panel_info.get('variables_used_in_panel', [])
    if variables_used:
        lines.append(f"Variables Used in Panel ({len(variables_used)}):")
        variables_used_defs = panel_info.get('variables_used_definitions', [])
        for var in variables_used_defs:
            lines.append(f"\n  Variable: ${var['name']}")
            lines.append(f"    Type: {var['type']}")
            if var.get('label'):
                lines.append(f"    Label: {var['label']}")
            if var.get('current'):
                current_val = var['current'].get('value', 'N/A')
                lines.append(f"    Current value: {current_val}")
            if var.get('query'):
                lines.append(f"    Query: {var['query']}")
            if var.get('datasource'):
                lines.append(f"    Datasource: {var['datasource']}")
            lines.append(f"    Multi-select: {var.get('multi', False)}")
    
    lines.append("")
    
    # Display all dashboard variables
    dashboard_vars = panel_info.get('dashboard_variables', [])
    if dashboard_vars:
        lines.append(f"All Dashboard Variables ({len(dashboard_vars)}):")
        for var in dashboard_vars:
            var_name = var['name']
            var_type = var['type']
            is_used = var_name in variables_used
            used_marker = " [USED]" if is_used else ""
            lines.append(f"  - ${var_name} (type: {var_type}){used_marker}")
    
    return "\n".join(lines)


def main():
    """
    Example usage of the Grafana integration with service identification.
    """
    logger.info("Starting Grafana integration example")
    
    # Configuration
    GRAFANA_BASE_URL = os.getenv("GRAFANA_BASE_URL", "http://grafana-k8s-ci.myntra.com")
    GRAFANA_API_TOKEN = os.getenv("GRAFANA_API_TOKEN")
    EXAMPLE_PANEL_URL = "https://grafana-k8s-ci.myntra.com/d/icutU1eVk/oms-prometheus?orgId=1&from=now-30m&to=now&viewPanel=102"
    CURSOR_API_URL = os.getenv("CURSOR_API_URL", "http://localhost:9000")
    POSSIBLE_SERVICES = ["oms", "awh", "crs"]
    
    if not GRAFANA_API_TOKEN:
        logger.error("GRAFANA_API_TOKEN not found in environment variables. Please set it in .env file.")
        raise ValueError("GRAFANA_API_TOKEN is required. Please set it in your .env file.")
    
    logger.info(f"Grafana URL: {GRAFANA_BASE_URL}")
    logger.debug(f"Example panel URL: {EXAMPLE_PANEL_URL}")
    
    # Create client
    client = GrafanaClient(GRAFANA_BASE_URL, GRAFANA_API_TOKEN)
    
    try:
        print("="*80)
        print("STEP 1: Fetching Panel Information from Grafana")
        print("="*80)
        print(f"URL: {EXAMPLE_PANEL_URL}\n")
        
        # Get panel info
        panel_info = client.get_panel_info_from_url(EXAMPLE_PANEL_URL)
        
        # Print formatted output
        print(format_panel_info(panel_info))
        
        logger.info("Panel information retrieval completed successfully")
        
        # Identify service using AI
        print("\n" + "="*80)
        print("STEP 2: Identifying Service using Cursor AI (gemini-2.5-flash)")
        print("="*80)
        print(f"Possible services: {', '.join(POSSIBLE_SERVICES)}\n")
        
        try:
            service_result = identify_service_from_panel(
                panel_info,
                POSSIBLE_SERVICES,
                cursor_api_url=CURSOR_API_URL,
                model="gemini-2.5-flash"
            )
            
            print(f"✅ Service Identified: {service_result['service'].upper()}")
            print(f"   Confidence: {service_result['confidence']}")
            print(f"\n   Reasoning:")
            print(f"   {service_result['reasoning']}")
            print(f"\n   Model used: {service_result.get('model_used', 'N/A')}")
            
            logger.info(f"Service identification completed: {service_result['service']}")
            
        except Exception as e:
            logger.error(f"Service identification failed: {e}", exc_info=True)
            print(f"❌ Service identification failed: {e}")
            print("\nNote: Make sure the Cursor API server is running at http://localhost:9000")
            print("You can start it with: python main.py")
        
        # Print raw JSON for debugging
        print("\n" + "="*80)
        print("Raw Panel JSON (summary):")
        print("="*80)
        summary = {
            'panel_title': panel_info['panel_title'],
            'dashboard_title': panel_info['dashboard_title'],
            'panel_type': panel_info['panel_type'],
            'query_count': len(panel_info.get('targets', [])),
            'variables_used': panel_info.get('variables_used_in_panel', [])
        }
        print(json.dumps(summary, indent=2))
        
    except Exception as e:
        logger.error(f"Failed to fetch panel information: {e}", exc_info=True)
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

