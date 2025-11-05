# Grafana Integration

This module provides integration with Grafana to extract panel names and queries from dashboard panel URLs.

## Features

- Parse Grafana panel URLs to extract dashboard UID and panel ID
- Fetch dashboard data using Grafana HTTP API
- Extract panel information including:
  - Panel title/name
  - Panel type
  - Data source
  - Queries (Prometheus, SQL, or generic)
  - Dashboard template variables (all variables and variables used in the panel)
  - Variable usage detection in queries
  - Additional metadata
- **AI-powered Service Identification**: Use Cursor Agent AI to automatically identify which service a panel belongs to based on its metrics, queries, and variables

## Installation

Install the required dependency:

```bash
pip install requests
```

Or install all dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Running Example Scripts

The integration includes several example scripts you can run:

1. **Basic Panel Information Extraction** (`grafana_integration.py`):
   ```bash
   python3 grafana_integration.py
   ```
   This script fetches panel information from a Grafana URL and displays:
   - Dashboard title and UID
   - Panel ID, title, and type
   - Data source information
   - All queries associated with the panel
   - Dashboard variables used in the panel

2. **Service Identification Example** (`example_service_identification.py`):
   ```bash
   # Run with default example URL
   python3 example_service_identification.py
   
   # Or pass a custom panel URL
   python3 example_service_identification.py "https://grafana-k8s-ci.myntra.com/d/xyz?viewPanel=123"
   ```
   This demonstrates the complete workflow: extracting panel info and identifying which service it belongs to using AI.

3. **Variable Testing** (`test_grafana_variables.py`):
   ```bash
   python3 test_grafana_variables.py
   ```
   This script tests variable detection and extraction functionality.

### Configuration

Before running the scripts, make sure to set up your `.env` file:

```bash
GRAFANA_BASE_URL=http://grafana-k8s-ci.myntra.com
GRAFANA_API_TOKEN=your-service-account-token
CURSOR_API_URL=http://localhost:9000
```

All scripts will automatically load these environment variables using `dotenv`.

## Grafana API Authentication

This integration uses [Grafana Service Account tokens](https://grafana.com/docs/grafana/latest/developers/http_api/#service-account-token) for authentication.

### Creating a Service Account Token

1. Navigate to **Administration** → **Users and access** → **Service Accounts**
2. Create a new service account or select an existing one
3. Generate a new token
4. Copy the token (format: `glsa_...`)

### Using the Token

The token is passed in the `Authorization` header:

```http
Authorization: Bearer <your-grafana-service-account-token>
```

**Note:** Set the token in your `.env` file as `GRAFANA_API_TOKEN`. All example scripts automatically load it using `dotenv`.

## Panel URL Format

The integration supports Grafana panel URLs in the following format:

```
http://<grafana-host>/d/<dashboard-uid>?orgId=<org-id>&viewPanel=<panel-id>
```

Example:
```
http://grafana-k8s-ci.myntra.com/d/fRBY-tz7a?orgId=1&viewPanel=172
```

Where:
- `fRBY-tz7a` - Dashboard UID
- `1` - Organization ID (optional)
- `172` - Panel ID

## API Response Structure

The `get_panel_info_from_url()` method returns a dictionary with the following structure:

```json
{
  "panel_id": 172,
  "panel_title": "CPU Usage",
  "panel_type": "graph",
  "datasource": "Prometheus",
  "targets": [
    {
      "ref_id": "A",
      "datasource": "Prometheus",
      "query": "rate(cpu_usage{namespace=\"$namespace\", pod=\"$pod\"}[5m])",
      "query_type": "prometheus",
      "raw_query": "rate(cpu_usage{namespace=\"$namespace\", pod=\"$pod\"}[5m])",
      "legend_format": "{{instance}}",
      "interval": "30s",
      "variables_used": ["namespace", "pod"]
    }
  ],
  "variables_used_in_panel": ["namespace", "pod"],
  "variables_used_definitions": [
    {
      "name": "namespace",
      "type": "query",
      "label": "Namespace",
      "current": {
        "text": "production",
        "value": "production"
      },
      "query": "label_values(kube_namespace_labels, namespace)",
      "datasource": "Prometheus",
      "multi": false,
      "includeAll": false,
      "hide": 0
    },
    {
      "name": "pod",
      "type": "query",
      "label": "Pod",
      "current": {
        "text": "my-app-pod",
        "value": "my-app-pod"
      },
      "query": "label_values(kube_pod_info{namespace=\"$namespace\"}, pod)",
      "datasource": "Prometheus",
      "multi": true,
      "includeAll": true,
      "hide": 0
    }
  ],
  "dashboard_variables": [
    {
      "name": "namespace",
      "type": "query",
      "label": "Namespace",
      "current": {"text": "production", "value": "production"},
      "query": "label_values(kube_namespace_labels, namespace)",
      "datasource": "Prometheus",
      "multi": false,
      "includeAll": false,
      "hide": 0
    },
    {
      "name": "pod",
      "type": "query",
      "label": "Pod",
      "current": {"text": "my-app-pod", "value": "my-app-pod"},
      "query": "label_values(kube_pod_info{namespace=\"$namespace\"}, pod)",
      "datasource": "Prometheus",
      "multi": true,
      "includeAll": true,
      "hide": 0
    },
    {
      "name": "interval",
      "type": "interval",
      "label": null,
      "current": {"text": "5m", "value": "5m"},
      "query": "1m,5m,10m,30m,1h",
      "datasource": null,
      "multi": false,
      "includeAll": false,
      "hide": 0
    }
  ],
  "dashboard_uid": "fRBY-tz7a",
  "dashboard_title": "System Metrics",
  "url": "http://grafana-k8s-ci.myntra.com/d/fRBY-tz7a?orgId=1&viewPanel=172"
}
```

## Dashboard Variables

The integration automatically extracts and identifies dashboard template variables:

### Variable Detection

The module:
1. Extracts all dashboard-level template variables
2. Identifies which variables are used in the panel's queries
3. Detects variable references in both query strings and legend formats
4. Provides full variable definitions including current values

### Variable Reference Formats

Variables in Grafana can be referenced as:
- `$varname` - Simple variable reference
- `${varname}` - Braced variable reference (recommended for complex scenarios)

### Variable Types Supported

- **Query**: Dynamic variables populated from data source queries
- **Custom**: User-defined static values
- **Interval**: Time interval selections
- **Datasource**: Data source selectors
- **Constant**: Fixed values
- **Text box**: Free-text input
- **Ad hoc filters**: Dynamic key-value filters

### Accessing Variable Information

See `test_grafana_variables.py` for a complete example of how to access variable information. The script demonstrates:
- Extracting all dashboard variables
- Identifying variables used in a specific panel
- Getting full variable definitions
- Query-level variable usage analysis

Run it with:
```bash
python3 test_grafana_variables.py
```

## Supported Query Types

The integration can extract queries from various data sources:

- **Prometheus**: Queries in the `expr` field
- **SQL**: Queries in the `rawSql` field  
- **Generic**: Queries in the `query` field

## Error Handling

The client raises `ValueError` exceptions for common errors:

- Invalid panel URL format
- Dashboard not found (404)
- Authentication failed (401)
- Access denied (403)
- Panel not found in dashboard

Example error handling:

All example scripts include proper error handling. Check `grafana_integration.py`, `example_service_identification.py`, or `test_grafana_variables.py` for examples.

## Advanced Usage

### Custom Organization ID

The org ID is automatically extracted from the URL parameter. See `grafana_integration.py` for implementation details.

### Extracting Specific Information

See the example scripts for how to extract specific information from panel data:
- `grafana_integration.py` - Basic panel information extraction
- `example_service_identification.py` - Complete workflow example
- `test_grafana_variables.py` - Variable extraction and analysis

### Pretty Printing

The `format_panel_info()` helper function is used in `grafana_integration.py`. Run it to see formatted output:
```bash
python3 grafana_integration.py
```

## AI-Powered Service Identification

The integration includes an AI-powered feature that uses Cursor Agent to automatically identify which service a panel belongs to.

### How It Works

The `identify_service_from_panel()` function:
1. Takes the extracted panel information
2. Builds a detailed prompt with panel metrics, queries, and variables
3. Calls the Cursor API with the `gemini-2.5-flash` model (fast and accurate)
4. Analyzes the panel context to determine the service
5. Returns the identified service with confidence level and reasoning

### Usage

Run the example script to see service identification in action:

```bash
python3 example_service_identification.py
```

Or pass a custom panel URL:

```bash
python3 example_service_identification.py "https://grafana-k8s-ci.myntra.com/d/xyz?viewPanel=123"
```

The script will:
1. Extract panel information from the Grafana URL
2. Identify which service the panel belongs to using AI
3. Display the service, confidence level, and reasoning

See `example_service_identification.py` for the complete implementation.

### Service Identification Response

The function returns a dictionary with:
- `service`: Identified service name (e.g., 'oms', 'awh', 'crs')
- `confidence`: Confidence level ('high', 'medium', or 'low')
- `reasoning`: Explanation of why this service was identified
- `raw_response`: Full AI response
- `session_id`: Cursor API session ID
- `model_used`: Model that was used for identification

Run `example_service_identification.py` to see the response format in action.

### Supported Services

The function supports identifying panels for these services (can be customized):
- **oms**: Order Management System - handles order processing, fulfillment
- **awh**: Assign Warehouse - handles warehouse assignment, inventory
- **crs**: Customer Relationship Service - handles customer data, support

### Prerequisites

For service identification to work, you need:
1. **Cursor API Server running**: Start with `python main.py`
2. **CURSOR_API_KEY set**: Required for Cursor Agent to work
3. **Network access**: To reach both Grafana and Cursor API

## Integration with Main API

You can integrate this with the existing FastAPI server. See the source code in `grafana_integration.py` for the `GrafanaClient` class API and `identify_service_from_panel()` function signatures.

## References

- [Grafana HTTP API Documentation](https://grafana.com/docs/grafana/latest/developers/http_api/)
- [Service Account Token Authentication](https://grafana.com/docs/grafana/latest/developers/http_api/#service-account-token)
- [Dashboard HTTP API](https://grafana.com/docs/grafana/latest/developers/http_api/dashboard/)

## License

Same as the parent project.

