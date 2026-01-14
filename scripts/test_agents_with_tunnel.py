#!/usr/bin/env python3
"""
FinagentiX Agent Testing Script with SSH Tunnel

This script:
1. Sets up SSH tunnel to the debug VM for Azure OpenAI access
2. Tests all agents with sample questions
3. Saves questions and responses to a JSON/Markdown file for review

Usage:
    python scripts/test_agents_with_tunnel.py
    python scripts/test_agents_with_tunnel.py --output results.json
    python scripts/test_agents_with_tunnel.py --skip-tunnel  # If tunnel is already running
"""

import os
import sys
import json
import subprocess
import time
import socket
import argparse
from datetime import datetime
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Configuration
TUNNEL_CONFIG = {
    "vm_user": "azureuser",
    "vm_ip": "4.227.91.227",
    "remote_host": "openai-3ae172dc9e9da.openai.azure.com",
    "remote_port": 443,
    "local_port": 8443,
}

# Test questions for each agent
TEST_CASES = {
    "MarketDataAgent": [
        "What is the current stock price and trading volume for AAPL?",
        "Show me the market data for Microsoft (MSFT)",
        "Get the latest stock information for Tesla",
    ],
    "NewsSentimentAgent": [
        "What is the current news sentiment for NVDA?",
        "Analyze recent news about Amazon stock",
        "What are the latest headlines affecting Google stock?",
    ],
    "RiskAssessmentAgent": [
        "What is the risk assessment for investing in AMZN?",
        "Analyze the volatility and risk factors for Apple stock",
        "Evaluate the risk profile of TSLA",
    ],
    "FundamentalAnalysisAgent": [
        "What are the fundamental metrics for AAPL including P/E ratio?",
        "Analyze the financial health of Microsoft",
        "What is the earnings outlook for Amazon?",
    ],
    "RouterAgent": [
        "I want to know about Apple stock",
        "What's happening with Tesla?",
        "Tell me about the risks of investing in NVIDIA",
    ],
    "SynthesisAgent": [
        "Give me a comprehensive analysis of AAPL",
        "Synthesize all available information about Microsoft stock",
        "Provide a complete investment summary for Amazon",
    ],
    "OrchestratorAgent": [
        "Should I invest in Apple right now? Give me a complete analysis.",
        "I have $10,000 to invest. What do you think about MSFT?",
        "Compare the investment potential of NVDA vs AMD",
    ],
}


class TunnelManager:
    """Manages SSH tunnel to Azure OpenAI via debug VM"""
    
    def __init__(self, config: dict):
        self.config = config
        self.process = None
    
    def is_port_in_use(self) -> bool:
        """Check if local port is already in use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', self.config['local_port'])) == 0
    
    def start(self) -> bool:
        """Start SSH tunnel"""
        if self.is_port_in_use():
            print(f"✓ Port {self.config['local_port']} already in use - tunnel may be running")
            return True
        
        print(f"Starting SSH tunnel to {self.config['vm_ip']}...")
        
        cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-L", f"{self.config['local_port']}:{self.config['remote_host']}:{self.config['remote_port']}",
            "-N", f"{self.config['vm_user']}@{self.config['vm_ip']}"
        ]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            
            # Wait for tunnel to establish
            for i in range(10):
                time.sleep(1)
                if self.is_port_in_use():
                    print(f"✓ SSH tunnel established on localhost:{self.config['local_port']}")
                    return True
                print(f"  Waiting for tunnel... ({i+1}/10)")
            
            print("✗ Failed to establish tunnel within timeout")
            return False
            
        except Exception as e:
            print(f"✗ Failed to start tunnel: {e}")
            return False
    
    def stop(self):
        """Stop SSH tunnel"""
        if self.process:
            print("Stopping SSH tunnel...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("✓ Tunnel stopped")


def load_env():
    """Load environment variables from .env file"""
    env_file = PROJECT_ROOT / ".env"
    env_vars = {}
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
                    os.environ[key] = value
        print("✓ Loaded environment from .env")
    return env_vars


def get_agent_module_name(agent_name: str) -> str:
    """Convert agent class name to module name"""
    mappings = {
        "MarketDataAgent": "market_data_agent",
        "NewsSentimentAgent": "news_sentiment_agent",
        "RiskAssessmentAgent": "risk_assessment_agent",
        "FundamentalAnalysisAgent": "fundamental_analysis_agent",
        "RouterAgent": "router_agent",
        "SynthesisAgent": "synthesis_agent",
        "OrchestratorAgent": "orchestrator_agent",
    }
    return mappings.get(agent_name, agent_name.lower())


def test_agent_via_subprocess(agent_name: str, question: str, tunnel_port: int) -> dict:
    """
    Test an agent by running it in a subprocess to avoid import conflicts.
    Returns dict with response, status, and timing info.
    """
    
    module_name = get_agent_module_name(agent_name)
    
    # Create test script to run in subprocess
    test_script = f'''
import sys
import os
import warnings
import urllib3

# Suppress warnings
warnings.filterwarnings('ignore')
urllib3.disable_warnings()

# Set up path
sys.path.insert(0, "{PROJECT_ROOT}")

# Load env
env_file = "{PROJECT_ROOT}/.env"
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Override endpoint to use tunnel
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://localhost:{tunnel_port}/'
os.environ['AZURE_OPENAI_USE_TUNNEL'] = 'true'

# Need to patch httpx to disable SSL verification before imports
import httpx
_original_client_init = httpx.Client.__init__
def _patched_client_init(self, *args, **kwargs):
    kwargs['verify'] = False
    return _original_client_init(self, *args, **kwargs)
httpx.Client.__init__ = _patched_client_init

_original_async_client_init = httpx.AsyncClient.__init__
def _patched_async_client_init(self, *args, **kwargs):
    kwargs['verify'] = False
    return _original_async_client_init(self, *args, **kwargs)
httpx.AsyncClient.__init__ = _patched_async_client_init

# Now import agent
import asyncio
from src.agents.{module_name} import {agent_name}

# Run agent
try:
    agent = {agent_name}()
    question = """{question.replace('"', '\\"')}"""
    
    if hasattr(agent, 'run'):
        result = agent.run(question)
        if asyncio.iscoroutine(result):
            result = asyncio.get_event_loop().run_until_complete(result)
    elif hasattr(agent, 'invoke'):
        result = agent.invoke(question)
    elif hasattr(agent, 'process'):
        result = agent.process(question)
    else:
        result = "ERROR: No run/invoke/process method found"
    
    print("SUCCESS:", str(result))
except Exception as e:
    import traceback
    print("ERROR:", str(e))
    traceback.print_exc()
'''
    
    start_time = time.time()
    
    try:
        # Run in subprocess with timeout
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(PROJECT_ROOT),
            env={**os.environ}
        )
        
        elapsed = time.time() - start_time
        output = result.stdout.strip()
        stderr = result.stderr.strip()
        
        if output.startswith("SUCCESS:"):
            response = output[8:].strip()
            return {
                "status": "success",
                "response": response,
                "elapsed_seconds": round(elapsed, 2),
                "response_length": len(response)
            }
        else:
            return {
                "status": "error",
                "error": output + "\n" + stderr if stderr else output,
                "elapsed_seconds": round(elapsed, 2)
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": "Timeout after 120 seconds",
            "elapsed_seconds": 120
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "elapsed_seconds": time.time() - start_time
        }


def run_agent_tests(agents_to_test: list, tunnel_port: int, output_file: str):
    """Run tests for all specified agents"""
    
    results = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "tunnel_endpoint": f"https://localhost:{tunnel_port}/",
            "project": "FinagentiX",
        },
        "agents": {}
    }
    
    print(f"\n{'#'*60}")
    print(f"# FinagentiX Agent Testing - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# Testing {len(agents_to_test)} agents")
    print(f"{'#'*60}")
    
    for agent_name in agents_to_test:
        if agent_name not in TEST_CASES:
            print(f"\n⚠️  Unknown agent: {agent_name}")
            continue
            
        questions = TEST_CASES[agent_name]
        
        print(f"\n{'='*60}")
        print(f"Testing {agent_name}")
        print('='*60)
        
        agent_results = {
            "agent_name": agent_name,
            "tests": [],
            "summary": {
                "total": len(questions),
                "passed": 0,
                "failed": 0,
            }
        }
        
        for i, question in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] Question: {question}")
            
            result = test_agent_via_subprocess(agent_name, question, tunnel_port)
            result["question"] = question
            result["timestamp"] = datetime.now().isoformat()
            
            if result["status"] == "success":
                agent_results["summary"]["passed"] += 1
                preview = result["response"][:200] + "..." if len(result["response"]) > 200 else result["response"]
                print(f"✓ Response ({result['elapsed_seconds']}s, {result['response_length']} chars): {preview}")
            else:
                agent_results["summary"]["failed"] += 1
                print(f"✗ Error: {result.get('error', 'Unknown error')[:100]}")
            
            agent_results["tests"].append(result)
        
        results["agents"][agent_name] = agent_results
    
    # Calculate totals
    total_tests = sum(a["summary"]["total"] for a in results["agents"].values())
    total_passed = sum(a["summary"]["passed"] for a in results["agents"].values())
    total_failed = sum(a["summary"]["failed"] for a in results["agents"].values())
    
    results["summary"] = {
        "total_agents": len(results["agents"]),
        "total_tests": total_tests,
        "passed": total_passed,
        "failed": total_failed,
        "success_rate": f"{(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "N/A"
    }
    
    # Save results
    save_results(results, output_file)
    print_summary(results)
    
    return results


def save_results(results: dict, output_file: str):
    """Save results to JSON and Markdown files"""
    # Ensure directory exists
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    # Save JSON
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ JSON results saved to: {output_file}")
    
    # Save Markdown
    md_file = output_file.replace('.json', '.md')
    with open(md_file, 'w') as f:
        f.write("# FinagentiX Agent Test Results\n\n")
        f.write(f"**Generated:** {results['metadata']['timestamp']}\n\n")
        f.write(f"**Tunnel Endpoint:** `{results['metadata']['tunnel_endpoint']}`\n\n")
        
        # Summary
        if "summary" in results:
            s = results["summary"]
            f.write("## Summary\n\n")
            f.write(f"| Metric | Value |\n")
            f.write(f"|--------|-------|\n")
            f.write(f"| Agents Tested | {s['total_agents']} |\n")
            f.write(f"| Total Tests | {s['total_tests']} |\n")
            f.write(f"| Passed | {s['passed']} |\n")
            f.write(f"| Failed | {s['failed']} |\n")
            f.write(f"| Success Rate | {s['success_rate']} |\n\n")
        
        f.write("---\n\n")
        
        # Agent Details
        for agent_name, agent_data in results["agents"].items():
            f.write(f"## {agent_name}\n\n")
            
            if "error" in agent_data:
                f.write(f"**Error:** {agent_data['error']}\n\n")
                continue
            
            summary = agent_data.get("summary", {})
            f.write(f"**Results:** {summary.get('passed', 0)}/{summary.get('total', 0)} passed\n\n")
            
            for i, test in enumerate(agent_data.get("tests", []), 1):
                status = "✅" if test.get("status") == "success" else "❌"
                f.write(f"### Test {i} {status}\n\n")
                f.write(f"**Question:** {test.get('question', 'N/A')}\n\n")
                
                if test.get("status") == "success":
                    elapsed = test.get("elapsed_seconds", 0)
                    length = test.get("response_length", 0)
                    f.write(f"**Response Time:** {elapsed}s | **Length:** {length} chars\n\n")
                    f.write("**Response:**\n\n")
                    f.write("```\n")
                    f.write(test.get("response", "No response"))
                    f.write("\n```\n\n")
                else:
                    f.write(f"**Error:** {test.get('error', 'Unknown error')}\n\n")
            
            f.write("---\n\n")
    
    print(f"✓ Markdown results saved to: {md_file}")


def print_summary(results: dict):
    """Print test summary to console"""
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    
    for agent_name, agent_data in results["agents"].items():
        summary = agent_data.get("summary", {})
        passed = summary.get("passed", 0)
        total = summary.get("total", 0)
        status = "✓" if passed == total else "✗"
        print(f"{status} {agent_name}: {passed}/{total} tests passed")
    
    if "summary" in results:
        s = results["summary"]
        print(f"\nOVERALL: {s['passed']}/{s['total_tests']} tests passed ({s['success_rate']})")


def main():
    parser = argparse.ArgumentParser(
        description="Test FinagentiX agents with SSH tunnel to Azure OpenAI"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(PROJECT_ROOT / "test_results" / f"agent_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"),
        help="Output file for test results (JSON)"
    )
    parser.add_argument(
        "--skip-tunnel",
        action="store_true",
        help="Skip tunnel setup (use if tunnel is already running)"
    )
    parser.add_argument(
        "--agents",
        nargs="+",
        help="Specific agents to test (default: all)"
    )
    parser.add_argument(
        "--tunnel-port",
        type=int,
        default=8443,
        help="Local port for SSH tunnel (default: 8443)"
    )
    
    args = parser.parse_args()
    
    # Update tunnel config
    TUNNEL_CONFIG["local_port"] = args.tunnel_port
    
    # Load environment
    load_env()
    
    tunnel = None
    
    try:
        # Setup tunnel if needed
        if not args.skip_tunnel:
            tunnel = TunnelManager(TUNNEL_CONFIG)
            if not tunnel.start():
                print("\n❌ Failed to establish SSH tunnel. Exiting.")
                sys.exit(1)
        else:
            # Check if tunnel is actually running
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', args.tunnel_port)) != 0:
                    print(f"\n⚠️  Warning: No service on port {args.tunnel_port}. Tunnel may not be running.")
        
        # Determine agents to test
        agents_to_test = args.agents or list(TEST_CASES.keys())
        
        # Run tests
        run_agent_tests(agents_to_test, args.tunnel_port, args.output)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        if tunnel:
            tunnel.stop()


if __name__ == "__main__":
    main()
