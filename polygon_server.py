#!/usr/bin/env python3
"""Polygon Market Data MCP Server

This server provides market data capabilities through Polygon.io API
for use with Claude Desktop and other MCP-compatible clients.
"""

import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import aiohttp
from fastmcp import FastMCP

# Initialize the FastMCP server
mcp = FastMCP("polygon-market-data")

# Load API key from environment
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
if not POLYGON_API_KEY:
    raise ValueError("POLYGON_API_KEY environment variable is required")

BASE_URL = "https://api.polygon.io"

async def polygon_request(endpoint: str, params: Dict[str, Any] = {}) -> Dict[str, Any]:
    """Make authenticated request to Polygon API"""
    params["apiKey"] = POLYGON_API_KEY

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}{endpoint}", params=params) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Polygon API error: {response.status} - {error_text}")
            return await response.json()

@mcp.tool()
async def get_stock_quote(symbol: str) -> Dict[str, Any]:
    """Get real-time stock quote with comprehensive market data

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "GOOGL")

    Returns:
        Detailed quote information including price, volume, and change metrics
    """
    symbol = symbol.upper()

    try:
        # Get latest quote
        quote_data = await polygon_request(f"/v2/aggs/ticker/{symbol}/prev")

        if quote_data.get("status") != "OK" or not quote_data.get("results"):
            return {"error": f"No data available for symbol {symbol}"}

        result = quote_data["results"][0]

        # Calculate price change and percentage
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
            "changePercent": round(price_change_percent, 2),
            "marketCap": None,  # Would need additional API call
            "52weekHigh": None,
            "52weekLow": None
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}

@mcp.tool()
async def get_market_status() -> Dict[str, Any]:
    """Get current market status and hours

    Returns:
        Market status including whether markets are open, next open/close times
    """
    try:
        status_data = await polygon_request("/v1/marketstatus/now")

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

@mcp.tool()
async def search_stocks(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search for stocks by ticker symbol or company name

    Args:
        query: Search query (ticker or company name)
        limit: Maximum number of results (default 10)

    Returns:
        List of matching stocks with symbol and name
    """
    try:
        search_data = await polygon_request("/v3/reference/tickers", {
            "search": query,
            "limit": limit,
            "active": "true",
            "type": "CS"  # Common Stock
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

@mcp.tool()
async def get_stock_news(symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Get latest news articles for a stock

    Args:
        symbol: Stock ticker symbol
        limit: Number of articles to return (default 5)

    Returns:
        List of news articles with title, summary, and metadata
    """
    symbol = symbol.upper()

    try:
        news_data = await polygon_request("/v2/reference/news", {
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

@mcp.tool()
async def get_aggregates(
    symbol: str,
    timespan: str = "day",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 30
) -> Dict[str, Any]:
    """Get historical price aggregates (bars/candles) for a stock

    Args:
        symbol: Stock ticker symbol
        timespan: Size of time window (minute, hour, day, week, month, quarter, year)
        from_date: Start date (YYYY-MM-DD format)
        to_date: End date (YYYY-MM-DD format)
        limit: Maximum number of results

    Returns:
        Historical price data with OHLCV information
    """
    symbol = symbol.upper()

    # Default date range if not provided
    if not to_date:
        to_date = datetime.now().strftime("%Y-%m-%d")
    if not from_date:
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    try:
        agg_data = await polygon_request(
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

if __name__ == "__main__":
    # Run the server
    import uvicorn
    uvicorn.run(
        "polygon_server:mcp",
        host="127.0.0.1",
        port=8000,
        reload=True
    )