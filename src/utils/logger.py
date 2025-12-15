"""
Centralized Logging Configuration for FinagentiX
Provides structured logging with configurable levels and formatting
"""

import os
import logging
import sys
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    # Emoji prefixes
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨'
    }
    
    def format(self, record):
        """Format log record with colors and emojis"""
        # Add color
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            record.emoji = self.EMOJIS.get(levelname, '')
        
        return super().format(record)


def setup_logger(
    name: str,
    level: Optional[str] = None,
    enable_colors: bool = True
) -> logging.Logger:
    """
    Set up a logger with consistent formatting
    
    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, uses LOG_LEVEL env var or defaults to INFO
        enable_colors: Whether to use colored output
    
    Returns:
        Configured logger instance
    """
    # Get log level from environment or parameter
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level, logging.INFO))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level, logging.INFO))
    
    # Create formatter
    if enable_colors and sys.stdout.isatty():
        formatter = ColoredFormatter(
            '%(emoji)s %(levelname)s [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        formatter = logging.Formatter(
            '%(levelname)s [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger for a module
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return setup_logger(name)


# Agent-specific debug utilities
class AgentDebugger:
    """Helper class for agent debugging"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = get_logger(f"agent.{agent_name}")
        self.debug_enabled = os.getenv("DEBUG_AGENTS", "false").lower() == "true"
    
    def log_query(self, query: str):
        """Log incoming query"""
        if self.debug_enabled:
            self.logger.debug(f"📥 Query received: {query}")
    
    def log_response(self, response: str):
        """Log agent response"""
        if self.debug_enabled:
            self.logger.debug(f"📤 Response: {response[:200]}...")
    
    def log_tool_call(self, tool_name: str, args: dict):
        """Log tool/function call"""
        if self.debug_enabled:
            self.logger.debug(f"🔧 Tool called: {tool_name} with args: {args}")
    
    def log_tool_result(self, tool_name: str, result: any):
        """Log tool result"""
        if self.debug_enabled:
            result_str = str(result)[:200]
            self.logger.debug(f"🔧 Tool result from {tool_name}: {result_str}...")
    
    def log_error(self, error: Exception):
        """Log error with full traceback in debug mode"""
        if self.debug_enabled:
            self.logger.error(f"💥 Error: {error}", exc_info=True)
        else:
            self.logger.error(f"💥 Error: {error}")
    
    def log_metric(self, metric_name: str, value: any):
        """Log performance metric"""
        if self.debug_enabled:
            self.logger.debug(f"📊 {metric_name}: {value}")
    
    def log_config(self, config: dict):
        """Log configuration"""
        if self.debug_enabled:
            self.logger.debug(f"⚙️ Configuration: {config}")


# Workflow debugging
class WorkflowDebugger:
    """Helper class for workflow debugging"""
    
    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name
        self.logger = get_logger(f"workflow.{workflow_name}")
        self.debug_enabled = os.getenv("DEBUG_WORKFLOWS", "false").lower() == "true"
    
    def log_step(self, step_name: str, details: str = ""):
        """Log workflow step"""
        if self.debug_enabled:
            msg = f"🔄 Step: {step_name}"
            if details:
                msg += f" - {details}"
            self.logger.debug(msg)
    
    def log_decision(self, decision: str, reason: str = ""):
        """Log routing/orchestration decision"""
        if self.debug_enabled:
            msg = f"🎯 Decision: {decision}"
            if reason:
                msg += f" - Reason: {reason}"
            self.logger.info(msg)
    
    def log_cache_hit(self, query: str):
        """Log cache hit"""
        if self.debug_enabled:
            self.logger.info(f"💾 Cache hit for: {query[:100]}...")
    
    def log_cache_miss(self, query: str):
        """Log cache miss"""
        if self.debug_enabled:
            self.logger.debug(f"💨 Cache miss for: {query[:100]}...")

    def log_error(self, error: Exception):
        """Log workflow error"""
        if self.debug_enabled:
            self.logger.error(f"💥 Error: {error}", exc_info=True)
        else:
            self.logger.error(f"💥 Error: {error}")

    def log_metric(self, metric_name: str, value: any):
        """Log workflow metric"""
        if self.debug_enabled:
            self.logger.debug(f"📊 {metric_name}: {value}")

    def log_config(self, config: dict):
        """Log workflow configuration details"""
        if self.debug_enabled:
            self.logger.debug(f"⚙️ Configuration: {config}")


# Azure/SK debugging
class SKDebugger:
    """Helper class for Semantic Kernel debugging"""
    
    def __init__(self, component_name: str = "sk"):
        self.component_name = component_name
        self.logger = get_logger(f"sk.{component_name}")
        self.debug_enabled = os.getenv("DEBUG_SK", "false").lower() == "true"
    
    def log_kernel_creation(self, deployment: str, endpoint: str):
        """Log kernel creation"""
        if self.debug_enabled:
            self.logger.info(f"🔧 Creating kernel with deployment: {deployment}")
            self.logger.debug(f"🔧 Endpoint: {endpoint}")
    
    def log_agent_creation(self, agent_name: str, instructions_length: int):
        """Log agent creation"""
        if self.debug_enabled:
            self.logger.info(f"🤖 Creating agent: {agent_name}")
            self.logger.debug(f"📝 Instructions length: {instructions_length} chars")
    
    def log_api_call(self, model: str, messages_count: int):
        """Log API call"""
        if self.debug_enabled:
            self.logger.debug(f"🌐 API call to {model} with {messages_count} messages")
    
    def log_api_response(self, tokens_used: int, cost: float):
        """Log API response"""
        if self.debug_enabled:
            self.logger.debug(f"📊 Response: {tokens_used} tokens, ${cost:.4f} cost")
    
    def log_plugin_registration(self, plugin_name: str, functions_count: int):
        """Log plugin registration"""
        if self.debug_enabled:
            self.logger.info(f"🔌 Registered plugin: {plugin_name} ({functions_count} functions)")

    def log_config(self, config: dict):
        """Log Semantic Kernel configuration"""
        if self.debug_enabled:
            self.logger.debug(f"⚙️ Configuration: {config}")


# Example usage documentation
"""
USAGE EXAMPLES:

1. In main.py or any module:
   ```python
   from src.utils.logger import get_logger
   
   logger = get_logger(__name__)
   logger.info("Application started")
   logger.debug("Debug information")
   logger.error("Error occurred")
   ```

2. In agents:
   ```python
   from src.utils.logger import AgentDebugger
   
   debugger = AgentDebugger("MarketDataAgent")
   debugger.log_query(query)
   debugger.log_tool_call("get_stock_price", {"ticker": "AAPL"})
   debugger.log_response(response)
   ```

3. In workflows:
   ```python
   from src.utils.logger import WorkflowDebugger
   
   debugger = WorkflowDebugger("SequentialOrchestration")
   debugger.log_decision("sequential", "Query matches simple pattern")
   debugger.log_cache_hit(query)
   ```

4. In SK config:
   ```python
   from src.utils.logger import SKDebugger
   
   debugger = SKDebugger("config")
   debugger.log_kernel_creation(deployment, endpoint)
   debugger.log_agent_creation(agent_name, len(instructions))
   ```

ENVIRONMENT VARIABLES:

- LOG_LEVEL: Set global log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  Example: LOG_LEVEL=DEBUG

- DEBUG_AGENTS: Enable detailed agent debugging (true/false)
  Example: DEBUG_AGENTS=true

- DEBUG_WORKFLOWS: Enable workflow debugging (true/false)
  Example: DEBUG_WORKFLOWS=true

- DEBUG_SK: Enable Semantic Kernel debugging (true/false)
  Example: DEBUG_SK=true

QUICK SETUP:

Add to .env file:
```
# Logging configuration
LOG_LEVEL=INFO
DEBUG_AGENTS=false
DEBUG_WORKFLOWS=false
DEBUG_SK=false
```

For development/debugging:
```
# Logging Configuration
LOG_LEVEL=DEBUG
DEBUG_AGENTS=true
DEBUG_WORKFLOWS=true
DEBUG_SK=true
```

"""
