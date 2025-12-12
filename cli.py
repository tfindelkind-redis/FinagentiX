#!/usr/bin/env python3
"""
Simple CLI client for FinagentiX
"""

import asyncio
import sys
from typing import Optional

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

console = Console()

API_URL = "http://localhost:8000"


async def query_api(query: str, user_id: str = "cli_user", ticker: Optional[str] = None):
    """Send query to FinagentiX API"""
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_URL}/api/query",
                json={
                    "query": query,
                    "user_id": user_id,
                    "ticker": ticker,
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            console.print(f"[red]Error: {e}[/red]")
            return None


async def check_health():
    """Check API health"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/health", timeout=5.0)
            response.raise_for_status()
            data = response.json()
            
            status_color = "green" if data["status"] == "healthy" else "yellow"
            console.print(f"[{status_color}]Status: {data['status']}[/{status_color}]")
            console.print(f"Services: {data['services']}")
            return True
            
        except httpx.HTTPError:
            console.print("[red]API is not accessible. Make sure the server is running:[/red]")
            console.print("[yellow]python -m uvicorn src.api.main:app --reload[/yellow]")
            return False


async def show_stats():
    """Show API statistics"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/api/stats", timeout=5.0)
            response.raise_for_status()
            data = response.json()
            
            console.print("\n[bold]Cache Statistics:[/bold]")
            cache_stats = data.get("cache_stats", {})
            console.print(f"  Total entries: {cache_stats.get('total_entries', 0)}")
            console.print(f"  Total cache hits: {cache_stats.get('total_cache_hits', 0)}")
            console.print(f"  Tokens saved: {cache_stats.get('total_tokens_saved', 0)}")
            
            console.print("\n[bold]Router Statistics:[/bold]")
            router_stats = data.get("router_stats", {})
            console.print(f"  Total routes: {router_stats.get('total_routes', 0)}")
            console.print(f"  Total usage: {router_stats.get('total_usage', 0)}")
            
        except httpx.HTTPError as e:
            console.print(f"[red]Error fetching stats: {e}[/red]")


async def show_document_stats():
    """Show document store statistics"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/api/documents/stats", timeout=5.0)
            response.raise_for_status()
            data = response.json()
            
            console.print("\n[bold]Document Store Statistics:[/bold]")
            console.print(f"  Status: {data.get('status', 'unknown')}")
            console.print(f"  Total documents: {data.get('total_documents', 0)}")
            console.print(f"  Index: {data.get('index_name', 'N/A')}")
            console.print(f"  Embedding dimension: {data.get('embedding_dim', 0)}")
            
        except httpx.HTTPError as e:
            console.print(f"[red]Error fetching document stats: {e}[/red]")


async def ask_documents(question: str, ticker: Optional[str] = None):
    """Ask a question using RAG"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_URL}/api/documents/ask",
                json={
                    "question": question,
                    "ticker": ticker,
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Display answer
            console.print(f"\n[bold blue]Answer:[/bold blue]")
            console.print(Panel(
                Markdown(data.get("answer", "No answer")),
                border_style="blue"
            ))
            
            # Show sources
            sources = data.get("sources", [])
            if sources:
                console.print("\n[bold]Sources:[/bold]")
                for i, source in enumerate(sources, 1):
                    console.print(
                        f"{i}. {source['title']} ({source['doc_type']}, {source['filing_date'] or 'N/A'}) "
                        f"- Relevance: {int(source['relevance_score'] * 100)}%"
                    )
            
            console.print(f"\n[dim]Confidence: {data.get('confidence', 'unknown')}[/dim]")
            
        except httpx.HTTPError as e:
            console.print(f"[red]Error: {e}[/red]")


async def interactive_mode():
    """Interactive CLI mode"""
    
    console.print(Panel.fit(
        "[bold cyan]FinagentiX - AI Financial Trading Assistant[/bold cyan]\n"
        "Type your questions or commands below.\n"
        "Commands: /health, /stats, /docs, /ask, /quit",
        border_style="cyan"
    ))
    
    # Check API health first
    if not await check_health():
        return
    
    console.print()
    
    while True:
        try:
            # Get user input
            query = Prompt.ask("\n[bold green]You[/bold green]")
            
            if not query:
                continue
            
            # Handle commands
            if query == "/quit" or query == "/exit":
                console.print("[yellow]Goodbye![/yellow]")
                break
                
            elif query == "/health":
                await check_health()
                continue
                
            elif query == "/stats":
                await show_stats()
                continue
                
            elif query == "/docs":
                await show_document_stats()
                continue
                
            elif query == "/ask":
                doc_query = Prompt.ask("[bold green]Ask about documents[/bold green]")
                ticker = Prompt.ask("[dim]Ticker (optional, press Enter to skip)[/dim]", default="")
                await ask_documents(doc_query, ticker if ticker else None)
                continue
                
            elif query.startswith("/"):
                console.print(f"[red]Unknown command: {query}[/red]")
                console.print("Available commands: /health, /stats, /docs, /ask, /quit")
                continue
            
            # Send query to API
            console.print("\n[dim]Processing...[/dim]")
            
            result = await query_api(query)
            
            if result:
                # Display response
                response_text = result.get("response", "No response")
                
                console.print(f"\n[bold blue]FinagentiX:[/bold blue]")
                console.print(Panel(
                    Markdown(response_text),
                    border_style="blue"
                ))
                
                # Show metadata
                if result.get("cache_hit"):
                    console.print("[dim]✅ Cache hit (instant response)[/dim]")
                else:
                    workflow = result.get("workflow", "Unknown")
                    agents = ", ".join(result.get("agents_used", []))
                    processing_time = result.get("processing_time_ms", 0)
                    
                    console.print(f"[dim]Workflow: {workflow}[/dim]")
                    if agents:
                        console.print(f"[dim]Agents: {agents}[/dim]")
                    console.print(f"[dim]Processing time: {processing_time:.0f}ms[/dim]")
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Use /quit to exit[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


async def single_query(query: str):
    """Execute single query"""
    
    if not await check_health():
        return
    
    result = await query_api(query)
    
    if result:
        console.print(result.get("response", "No response"))


async def main():
    """Main entry point"""
    
    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        await single_query(query)
    else:
        # Interactive mode
        await interactive_mode()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
