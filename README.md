# Polygon Market Data MCP Server

A Model Context Protocol (MCP) server that provides real-time market data through the Polygon.io API. This server enables Claude Desktop and other MCP clients to access comprehensive stock market information.

## Features

- **Real-time Stock Quotes** - Get current prices, volume, and change metrics
- **Market Status** - Check if markets are open/closed
- **Stock Search** - Find stocks by ticker symbol or company name
- **News Feed** - Latest news articles for any stock
- **Historical Data** - Price aggregates for technical analysis

## Installation

1. Clone this repository:
```bash
git clone https://github.com/YOUR_USERNAME/polygon-mcp-server.git
cd polygon-mcp-server
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your API key:
```bash
cp .env.example .env
# Edit .env and add your Polygon API key
```

Get your free API key from [Polygon.io](https://polygon.io/dashboard/api-keys)

## Configuration for Claude Desktop

Add this to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "polygon-market-data": {
      "command": "python",
      "args": ["/path/to/polygon-mcp-server/polygon_server.py"],
      "env": {
        "POLYGON_API_KEY": "your_polygon_api_key_here"
      }
    }
  }
}
```

## Available Tools

### `get_stock_quote`
Get real-time quote for any stock symbol
```python
get_stock_quote(symbol="AAPL")
```

### `get_market_status`
Check current market hours and status
```python
get_market_status()
```

### `search_stocks`
Search for stocks by ticker or company name
```python
search_stocks(query="Tesla", limit=5)
```

### `get_stock_news`
Get latest news articles for a stock
```python
get_stock_news(symbol="TSLA", limit=10)
```

### `get_aggregates`
Get historical price data
```python
get_aggregates(symbol="GOOGL", timespan="day", from_date="2024-01-01", to_date="2024-01-31")
```

## Development

Run the server locally:
```bash
python polygon_server.py
```

Test with FastMCP inspector:
```bash
fastmcp dev polygon_server.py
```

## Requirements

- Python 3.8+
- Polygon.io API key (free tier available)
- Dependencies listed in requirements.txt

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please use the GitHub Issues page.