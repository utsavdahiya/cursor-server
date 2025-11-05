# Grafana Service Identification - Quick Start

This guide shows you how to use AI to automatically identify which service a Grafana panel belongs to.

## Prerequisites

1. **Start the Cursor API Server**:
   ```bash
   # Make sure CURSOR_API_KEY is set in your environment or .env file
   export CURSOR_API_KEY="your-key-here"
   
   # Start the API server
   python main.py
   ```

2. **Verify the server is running**:
   ```bash
   curl http://localhost:9000/api/health
   ```

## Quick Example

Run the example script:

```bash
python3 example_service_identification.py
```

Or with a custom panel URL:

```bash
python3 example_service_identification.py "https://grafana-k8s-ci.myntra.com/d/icutU1eVk/oms-prometheus?orgId=1&viewPanel=102"
```

The script will:
1. Extract panel information from Grafana
2. Identify which service the panel belongs to using AI
3. Display the service, confidence level, and reasoning

See `example_service_identification.py` for the complete code implementation.

## Run the Complete Demo

```bash
# Run the main example (extracts panel info + identifies service)
python grafana_integration.py

# Or run the standalone example
python example_service_identification.py

# You can also pass a custom panel URL
python example_service_identification.py "https://grafana-k8s-ci.myntra.com/d/xyz?viewPanel=123"
```

## What Gets Analyzed?

The AI analyzes:
- ✅ Panel title and dashboard context
- ✅ Prometheus/SQL queries and metric names
- ✅ Query labels and filters
- ✅ Dashboard variables and their usage
- ✅ Legend formats

## Example Output

```
================================================================================
STEP 1: Fetching Panel Information from Grafana
================================================================================
URL: https://grafana-k8s-ci.myntra.com/d/icutU1eVk/oms-prometheus?...

Dashboard: OMS Prometheus (icutU1eVk)
Panel ID: 102
Panel Title: Order Processing Rate
Panel Type: graph

Queries (1):
  Query #1:
    Ref ID: A
    Type: prometheus
    Query: rate(oms_orders_processed_total{namespace="$namespace"}[5m])
    Variables used: namespace

================================================================================
STEP 2: Identifying Service using Cursor AI (gemini-2.5-flash)
================================================================================
Possible services: oms, awh, crs

✅ Service Identified: OMS
   Confidence: high

   Reasoning:
   The panel monitors OMS-specific metrics including order processing rates,
   uses the oms_orders_processed_total metric, and is from the OMS Prometheus
   dashboard. All indicators strongly point to the Order Management System.

   Model used: gemini-2.5-flash
```

## Supported Services

- **oms**: Order Management System - order processing, fulfillment
- **awh**: Assign Warehouse - warehouse assignment, inventory
- **crs**: Customer Relationship Service - customer data, support

You can customize the service list and descriptions in the code.

## Troubleshooting

### "Failed to connect to Cursor API"
- Make sure the Cursor API server is running: `python main.py`
- Check the server is accessible: `curl http://localhost:9000/api/health` (default port is 9000, or check your PORT environment variable)

### "Authentication failed" (Grafana)
- Verify your Grafana API token is valid
- Check you have permissions to access the dashboard

### "cursor-agent CLI not found"
- Install cursor-agent: `curl https://cursor.com/install -fsS | bash`
- Make sure `CURSOR_API_KEY` environment variable is set

## API Integration

You can integrate this into your own FastAPI/Flask app. See the source code in `grafana_integration.py` for:
- `GrafanaClient` class - for interacting with Grafana API
- `identify_service_from_panel()` function - for AI-powered service identification

The example scripts show how to use these functions in practice.

## Documentation

For complete documentation, see:
- `GRAFANA_INTEGRATION.md` - Full integration guide
- `grafana_integration.py` - Source code with docstrings
- `example_service_identification.py` - Complete workflow example

## License

Same as parent project.


