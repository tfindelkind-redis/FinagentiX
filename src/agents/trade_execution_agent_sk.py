"""
Trade Execution Agent for Semantic Kernel
ChatCompletionAgent specializing in trade execution and order management
"""

import asyncio
from typing import Dict, Any, List, Optional
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.contents import ChatMessageContent, AuthorRole
import sys
import os
from datetime import datetime
import uuid

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sk_config import get_kernel, get_redis_client


class TradeExecutionAgentSK:
    """
    Trade Execution Agent using Microsoft Semantic Kernel
    
    Handles trade execution, order management, and execution simulation.
    In a production system, this would integrate with broker APIs.
    """
    
    def __init__(self, kernel=None, redis_client=None):
        """
        Initialize Trade Execution Agent
        
        Args:
            kernel: Semantic Kernel instance (uses default if None)
            redis_client: Redis client (uses default if None)
        """
        # Use provided or default kernel/redis
        self.kernel = kernel or get_kernel()
        self.redis_client = redis_client or get_redis_client()
        
        # Define agent instructions
        instructions = """You are a Trade Execution Agent specializing in order management 
and trade execution.

Your capabilities include:
- Create and validate trade orders
- Simulate order execution
- Manage order lifecycle (pending, filled, cancelled)
- Calculate execution costs and slippage
- Provide execution quality analysis
- Track order status and confirmations

When handling trade execution:
1. Validate all order parameters before execution
2. Check for reasonable price limits
3. Assess market conditions for execution timing
4. Calculate expected costs (commission, slippage)
5. Provide clear confirmation of executed trades
6. Track order status and provide updates
7. Alert on unusual execution conditions
8. Ensure compliance with position sizing rules

Order types supported:
- Market orders: Execute at current market price
- Limit orders: Execute only at specified price or better
- Stop-loss orders: Trigger when price reaches stop level

Always:
- Validate order parameters before execution
- Provide clear execution confirmations
- Calculate and disclose all costs
- Track order history
- Never execute without proper validation
- Provide execution quality metrics
- Warn about potential execution risks
"""
        
        # Create ChatCompletionAgent
        self.agent = ChatCompletionAgent(
            kernel=self.kernel,
            name="TradeExecutionAgent",
            instructions=instructions
        )
    
    async def analyze(self, query: str) -> str:
        """
        Analyze using natural language query
        
        Args:
            query: Natural language question about trade execution
        
        Returns:
            Analysis result as string
        """
        try:
            # Create chat history
            history = [
                ChatMessageContent(
                    role=AuthorRole.USER,
                    content=query
                )
            ]
            
            # Invoke agent
            response = ""
            async for message in self.agent.invoke(history):
                if message.role == AuthorRole.ASSISTANT:
                    response += message.content
            
            return response
            
        except Exception as e:
            return f"Error during analysis: {str(e)}"
    
    async def create_order(
        self,
        ticker: str,
        action: str,
        quantity: int,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create a trade order
        
        Args:
            ticker: Stock ticker symbol
            action: "BUY" or "SELL"
            quantity: Number of shares
            order_type: "market", "limit", or "stop"
            limit_price: Limit price for limit orders
            stop_price: Stop price for stop orders
        
        Returns:
            Dictionary with order details
        """
        try:
            # Validate parameters
            if action not in ["BUY", "SELL"]:
                return {
                    "success": False,
                    "error": "Action must be BUY or SELL"
                }
            
            if quantity <= 0:
                return {
                    "success": False,
                    "error": "Quantity must be positive"
                }
            
            if order_type not in ["market", "limit", "stop"]:
                return {
                    "success": False,
                    "error": "Order type must be market, limit, or stop"
                }
            
            if order_type == "limit" and not limit_price:
                return {
                    "success": False,
                    "error": "Limit price required for limit orders"
                }
            
            if order_type == "stop" and not stop_price:
                return {
                    "success": False,
                    "error": "Stop price required for stop orders"
                }
            
            # Get current market price
            key = f"stock:{ticker.upper()}:close"
            end_ts = int(datetime.now().timestamp() * 1000)
            start_ts = end_ts - (24 * 60 * 60 * 1000)
            
            try:
                result = self.redis.execute_command("TS.RANGE", key, start_ts, end_ts)
                current_price = float(result[-1][1]) if result else 100.0
            except:
                current_price = 100.0  # Default if price unavailable
            
            # Generate order ID
            order_id = str(uuid.uuid4())[:8]
            
            # Calculate estimated costs
            commission = 0.00  # $0 commission (typical for modern brokers)
            estimated_slippage = current_price * 0.001  # 0.1% slippage estimate
            
            if order_type == "market":
                execution_price = current_price + (estimated_slippage if action == "BUY" else -estimated_slippage)
            elif order_type == "limit":
                execution_price = limit_price
            else:  # stop
                execution_price = stop_price
            
            total_cost = (execution_price * quantity) + commission
            
            # Create order record
            order = {
                "order_id": order_id,
                "ticker": ticker.upper(),
                "action": action,
                "quantity": quantity,
                "order_type": order_type,
                "limit_price": limit_price,
                "stop_price": stop_price,
                "current_market_price": round(current_price, 2),
                "estimated_execution_price": round(execution_price, 2),
                "estimated_total_cost": round(total_cost, 2),
                "commission": commission,
                "estimated_slippage": round(estimated_slippage, 2),
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "success": True
            }
            
            # Store order in Redis
            order_key = f"order:{order_id}"
            self.redis.hset(order_key, mapping={k: str(v) for k, v in order.items()})
            
            return {
                **order,
                "message": f"Order created: {action} {quantity} {ticker} @ {order_type} (ID: {order_id})"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error creating order: {str(e)}"
            }
    
    async def execute_order(
        self,
        order_id: str
    ) -> Dict[str, Any]:
        """
        Execute a pending order (simulation)
        
        Args:
            order_id: Order identifier
        
        Returns:
            Dictionary with execution details
        """
        try:
            # Retrieve order from Redis
            order_key = f"order:{order_id}"
            order_data = self.redis.hgetall(order_key)
            
            if not order_data:
                return {
                    "success": False,
                    "error": f"Order {order_id} not found"
                }
            
            # Convert bytes to strings
            order = {k.decode('utf-8'): v.decode('utf-8') for k, v in order_data.items()}
            
            # Check if already executed
            if order.get("status") != "pending":
                return {
                    "success": False,
                    "error": f"Order {order_id} is not pending (status: {order.get('status')})"
                }
            
            # Simulate execution
            ticker = order.get("ticker")
            action = order.get("action")
            quantity = int(order.get("quantity", 0))
            order_type = order.get("order_type")
            
            # Get current price for execution
            key = f"stock:{ticker}:close"
            end_ts = int(datetime.now().timestamp() * 1000)
            start_ts = end_ts - (24 * 60 * 60 * 1000)
            
            try:
                result = self.redis.execute_command("TS.RANGE", key, start_ts, end_ts)
                execution_price = float(result[-1][1]) if result else float(order.get("estimated_execution_price", 100))
            except:
                execution_price = float(order.get("estimated_execution_price", 100))
            
            # Apply slippage simulation
            if order_type == "market":
                slippage = execution_price * 0.001
                execution_price = execution_price + (slippage if action == "BUY" else -slippage)
            
            # Calculate totals
            total_amount = execution_price * quantity
            commission = 0.00
            total_cost = total_amount + commission
            
            # Update order status
            execution_data = {
                "status": "filled",
                "execution_price": str(round(execution_price, 2)),
                "total_amount": str(round(total_amount, 2)),
                "total_cost": str(round(total_cost, 2)),
                "executed_at": datetime.now().isoformat()
            }
            
            self.redis.hset(order_key, mapping=execution_data)
            
            # Update portfolio if it's a BUY order
            if action == "BUY":
                portfolio_key = "portfolio:default:positions"
                existing = self.redis.hget(portfolio_key, ticker)
                
                if existing:
                    existing_data = eval(existing.decode('utf-8'))
                    new_shares = existing_data['shares'] + quantity
                    new_cost_basis = ((existing_data['shares'] * existing_data['cost_basis']) + 
                                     (quantity * execution_price)) / new_shares
                    
                    self.redis.hset(portfolio_key, ticker, str({
                        'shares': new_shares,
                        'cost_basis': new_cost_basis
                    }))
                else:
                    self.redis.hset(portfolio_key, ticker, str({
                        'shares': quantity,
                        'cost_basis': execution_price
                    }))
            
            return {
                "order_id": order_id,
                "ticker": ticker,
                "action": action,
                "quantity": quantity,
                "execution_price": round(execution_price, 2),
                "total_cost": round(total_cost, 2),
                "commission": commission,
                "status": "filled",
                "executed_at": execution_data["executed_at"],
                "success": True,
                "message": f"Order executed: {action} {quantity} {ticker} @ ${execution_price:.2f} (Total: ${total_cost:.2f})"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error executing order: {str(e)}"
            }
    
    async def get_order_status(
        self,
        order_id: str
    ) -> Dict[str, Any]:
        """
        Get status of an order
        
        Args:
            order_id: Order identifier
        
        Returns:
            Dictionary with order status
        """
        try:
            # Retrieve order from Redis
            order_key = f"order:{order_id}"
            order_data = self.redis.hgetall(order_key)
            
            if not order_data:
                return {
                    "success": False,
                    "error": f"Order {order_id} not found"
                }
            
            # Convert bytes to strings and return
            order = {k.decode('utf-8'): v.decode('utf-8') for k, v in order_data.items()}
            
            return {
                **order,
                "success": True,
                "message": f"Order {order_id}: {order.get('status')}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error getting order status: {str(e)}"
            }
    
    async def cancel_order(
        self,
        order_id: str
    ) -> Dict[str, Any]:
        """
        Cancel a pending order
        
        Args:
            order_id: Order identifier
        
        Returns:
            Dictionary with cancellation result
        """
        try:
            # Retrieve order
            order_key = f"order:{order_id}"
            order_data = self.redis.hgetall(order_key)
            
            if not order_data:
                return {
                    "success": False,
                    "error": f"Order {order_id} not found"
                }
            
            order = {k.decode('utf-8'): v.decode('utf-8') for k, v in order_data.items()}
            
            # Check if can be cancelled
            if order.get("status") != "pending":
                return {
                    "success": False,
                    "error": f"Cannot cancel order in status: {order.get('status')}"
                }
            
            # Update status
            self.redis.hset(order_key, "status", "cancelled")
            self.redis.hset(order_key, "cancelled_at", datetime.now().isoformat())
            
            return {
                "order_id": order_id,
                "status": "cancelled",
                "success": True,
                "message": f"Order {order_id} cancelled successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Error cancelling order: {str(e)}"
            }
    
    async def close(self):
        """Cleanup resources"""
        try:
            if hasattr(self.redis_client, 'close'):
                self.redis_client.close()
        except Exception:
            pass


# Example usage and testing
if __name__ == "__main__":
    async def test_agent():
        """Test the Trade Execution Agent"""
        print("Testing Trade Execution Agent with Semantic Kernel...\n")
        
        # Create agent
        agent = TradeExecutionAgentSK()
        
        # Test 1: Natural language query
        print("Test 1: Ask about order types")
        response = await agent.analyze("What's the difference between market and limit orders?")
        print(f"Response: {response}\n")
        
        # Test 2: Create market order
        print("Test 2: Create market buy order for AAPL")
        order = await agent.create_order("AAPL", "BUY", 10, "market")
        print(f"Result: {order.get('message')}")
        order_id = order.get("order_id")
        print(f"Order ID: {order_id}\n")
        
        # Test 3: Execute order
        if order_id:
            print("Test 3: Execute the order")
            execution = await agent.execute_order(order_id)
            print(f"Result: {execution.get('message')}\n")
        
        # Test 4: Check order status
        if order_id:
            print("Test 4: Check order status")
            status = await agent.get_order_status(order_id)
            print(f"Status: {status.get('message')}\n")
        
        # Test 5: Create and cancel limit order
        print("Test 5: Create limit order and cancel it")
        limit_order = await agent.create_order("MSFT", "BUY", 5, "limit", limit_price=350.00)
        print(f"Created: {limit_order.get('message')}")
        
        limit_order_id = limit_order.get("order_id")
        if limit_order_id:
            cancel = await agent.cancel_order(limit_order_id)
            print(f"Cancelled: {cancel.get('message')}\n")
        
        print("✅ All tests completed!")
        
        # Cleanup
        await agent.close()
    
    # Run tests
    asyncio.run(test_agent())
