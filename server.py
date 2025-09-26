#!/usr/bin/env python3
"""
Polygon Market Data MCP Server

This server provides market data capabilities through Polygon.io API
using the official MCP Python SDK.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import aiohttp
from dotenv import load_dotenv

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Load environment variables
load_dotenv()

# Configuration
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
if not POLYGON_API_KEY:
    raise ValueError("POLYGON_API_KEY environment variable is required")

BASE_URL = "https://api.polygon.io"


class PolygonMCPServer:
    """MCP Server for Polygon.io market data API"""

    def __init__(self):
        self.server = Server(
            name="polygon-market-data",
            version="1.0.0"
        )
        self._register_handlers()

    def _register_handlers(self):
        """Register tool handlers with the MCP server"""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available tools"""
            return [
                Tool(
                    name="get_stock_quote",
                    description="Get real-time stock quote with comprehensive market data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Stock ticker symbol (e.g., AAPL, GOOGL)"
                            }
                        },
                        "required": ["symbol"]
                    }
                ),
                Tool(
                    name="get_market_status",
                    description="Get current market status and hours",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="search_stocks",
                    description="Search for stocks by ticker symbol or company name",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (ticker or company name)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results (default 10)",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_stock_news",
                    description="Get latest news articles for a stock",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Stock ticker symbol"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of articles to return (default 5)",
                                "default": 5
                            }
                        },
                        "required": ["symbol"]
                    }
                ),
                Tool(
                    name="get_aggregates",
                    description="Get historical price aggregates (bars/candles) for a stock",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Stock ticker symbol"
                            },
                            "timespan": {
                                "type": "string",
                                "description": "Size of time window (minute, hour, day, week, month, quarter, year)",
                                "default": "day"
                            },
                            "from_date": {
                                "type": "string",
                                "description": "Start date (YYYY-MM-DD format)"
                            },
                            "to_date": {
                                "type": "string",
                                "description": "End date (YYYY-MM-DD format)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results",
                                "default": 30
                            }
                        },
                        "required": ["symbol"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Execute a tool with the given arguments"""

            try:
                if name == "get_stock_quote":
                    result = await self._get_stock_quote(arguments["symbol"])
                elif name == "get_market_status":
                    result = await self._get_market_status()
                elif name == "search_stocks":
                    result = await self._search_stocks(
                        arguments["query"],
                        arguments.get("limit", 10)
                    )
                elif name == "get_stock_news":
                    result = await self._get_stock_news(
                        arguments["symbol"],
                        arguments.get("limit", 5)
                    )
                elif name == "get_aggregates":
                    result = await self._get_aggregates(
                        arguments["symbol"],
                        arguments.get("timespan", "day"),
                        arguments.get("from_date"),
                        arguments.get("to_date"),
                        arguments.get("limit", 30)
                    )
                else:
                    result = {"error": f"Unknown tool: {name}"}

                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]

    async def _polygon_request(self, endpoint: str, params: Dict[str, Any] = {}) -> Dict[str, Any]:
        """Make authenticated request to Polygon API"""
        params["apiKey"] = POLYGON_API_KEY

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}{endpoint}", params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Polygon API error: {response.status} - {error_text}")
                return await response.json()

    async def _get_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """Get real-time stock quote"""
        symbol = symbol.upper()

        try:
            quote_data = await self._polygon_request(f"/v2/aggs/ticker/{symbol}/prev")

            if quote_data.get("status") != "OK" or not quote_data.get("results"):
                return {"error": f"No data available for symbol {symbol}"}

            result = quote_data["results"][0]
            open_price = result.get("o", 0)
            close_price = result.get("c", 0)
            price_change = close_price - open_price if open_price else 0
            price_change_percent = (price_change / open_price * 100) if open_price else 0

            return {
                "symbol": symbol,
                "price": close_price,
                "open": open_price,
                "high": result.get("h"),
                "low": result.get("l"),
                "close": close_price,
                "volume": result.get("v"),
                "vwap": result.get("vw"),
                "timestamp": datetime.fromtimestamp(result.get("t", 0) / 1000).isoformat(),
                "change": round(price_change, 2),
                "changePercent": round(price_change_percent, 2)
            }
        except Exception as e:
            return {"error": str(e), "symbol": symbol}

    async def _get_market_status(self) -> Dict[str, Any]:
        """Get current market status"""
        try:
            status_data = await self._polygon_request("/v1/marketstatus/now")

            return {
                "market": status_data.get("market", "unknown"),
                "serverTime": status_data.get("serverTime", ""),
                "exchanges": {
                    "nyse": status_data.get("exchanges", {}).get("nyse", "unknown"),
                    "nasdaq": status_data.get("exchanges", {}).get("nasdaq", "unknown")
                },
                "currencies": {
                    "crypto": status_data.get("currencies", {}).get("crypto", "unknown"),
                    "fx": status_data.get("currencies", {}).get("fx", "unknown")
                }
            }
        except Exception as e:
            return {"error": str(e)}

    async def _search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for stocks"""
        try:
            search_data = await self._polygon_request("/v3/reference/tickers", {
                "search": query,
                "limit": limit,
                "active": "true",
                "type": "CS"
            })

            results = []
            for ticker in search_data.get("results", []):
                results.append({
                    "symbol": ticker.get("ticker"),
                    "name": ticker.get("name"),
                    "market": ticker.get("market"),
                    "locale": ticker.get("locale"),
                    "type": ticker.get("type"),
                    "currency": ticker.get("currency_name")
                })

            return results
        except Exception as e:
            return [{"error": str(e)}]

    async def _get_stock_news(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get stock news"""
        symbol = symbol.upper()

        try:
            news_data = await self._polygon_request("/v2/reference/news", {
                "ticker": symbol,
                "limit": limit,
                "sort": "published_utc",
                "order": "desc"
            })

            articles = []
            for article in news_data.get("results", []):
                articles.append({
                    "title": article.get("title"),
                    "summary": article.get("description"),
                    "publisher": article.get("publisher", {}).get("name"),
                    "publishedAt": article.get("published_utc"),
                    "url": article.get("article_url"),
                    "imageUrl": article.get("image_url"),
                    "tickers": article.get("tickers", [])
                })

            return articles
        except Exception as e:
            return [{"error": str(e)}]

    async def _get_aggregates(
        self,
        symbol: str,
        timespan: str = "day",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 30
    ) -> Dict[str, Any]:
        """Get historical price aggregates"""
        symbol = symbol.upper()

        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")
        if not from_date:
            from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        try:
            agg_data = await self._polygon_request(
                f"/v2/aggs/ticker/{symbol}/range/1/{timespan}/{from_date}/{to_date}",
                {"limit": limit, "sort": "desc"}
            )

            if agg_data.get("status") != "OK":
                return {"error": f"Failed to get data for {symbol}"}

            bars = []
            for bar in agg_data.get("results", []):
                bars.append({
                    "timestamp": datetime.fromtimestamp(bar.get("t", 0) / 1000).isoformat(),
                    "open": bar.get("o"),
                    "high": bar.get("h"),
                    "low": bar.get("l"),
                    "close": bar.get("c"),
                    "volume": bar.get("v"),
                    "vwap": bar.get("vw"),
                    "transactions": bar.get("n")
                })

            return {
                "symbol": symbol,
                "timespan": timespan,
                "from": from_date,
                "to": to_date,
                "resultsCount": len(bars),
                "bars": bars
            }
        except Exception as e:
            return {"error": str(e), "symbol": symbol}

    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point"""
    server = PolygonMCPServer()
    await server.run()


def run():
    """Synchronous entry point"""
    asyncio.run(main())


if __name__ == "__main__":
    run()