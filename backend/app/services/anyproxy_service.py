"""
AnyProxy Integration Service for Python

This module provides a Python interface to AnyProxy, allowing you to intercept,
inspect, and modify HTTP/HTTPS traffic directly from your Python application.
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from urllib.parse import urlparse

import aiohttp
from pydantic import BaseModel, Field


@dataclass
class ProxyConfig:
    """Configuration for AnyProxy instance"""
    port: int = 8001
    web_interface_port: int = 8002
    rule_file: Optional[str] = None
    intercept_https: bool = False
    silent: bool = False
    throttle: Optional[int] = None  # in kb/s
    ws_intercept: bool = False
    ignore_unauthorized_ssl: bool = True


@dataclass
class RequestInfo:
    """Information about intercepted request"""
    id: str
    url: str
    method: str
    headers: Dict[str, str]
    body: Optional[str] = None
    timestamp: float = time.time()


@dataclass
class ResponseInfo:
    """Information about intercepted response"""
    id: str
    status_code: int
    headers: Dict[str, str]
    body: Optional[str] = None
    timestamp: float = time.time()


class AnyProxyRule(BaseModel):
    """Base class for AnyProxy rules"""
    summary: str = Field(default="Custom AnyProxy rule", description="Summary of the rule")
    
    class Config:
        arbitrary_types_allowed = True


class AnyProxyService:
    """
    Python wrapper for AnyProxy functionality
    Allows integration of AnyProxy's HTTP/HTTPS proxy capabilities into Python applications
    """
    
    def __init__(self, config: ProxyConfig = None):
        self.config = config or ProxyConfig()
        self.process = None
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        self.anyproxy_path = Path("c:/Users/Mina/Desktop/lmina/backend/anyproxy-master")
        self._request_handlers: List[Callable[[RequestInfo], Any]] = []
        self._response_handlers: List[Callable[[ResponseInfo], Any]] = []
        
    def add_request_handler(self, handler: Callable[[RequestInfo], Any]):
        """Add a handler for intercepted requests"""
        self._request_handlers.append(handler)
        
    def add_response_handler(self, handler: Callable[[ResponseInfo], Any]):
        """Add a handler for intercepted responses"""
        self._response_handlers.append(handler)
        
    async def start(self):
        """Start the AnyProxy server"""
        try:
            # Check if Node.js is available
            result = await asyncio.create_subprocess_exec(
                "node", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, _ = await result.communicate()
            
            if result.returncode != 0:
                raise RuntimeError("Node.js is not installed or not in PATH")
                
            # Build the command to start AnyProxy
            cmd = [
                "node",
                str(self.anyproxy_path / "bin" / "anyproxy"),
                "--port", str(self.config.port)
            ]
            
            if self.config.web_interface_port:
                cmd.extend(["--web", str(self.config.web_interface_port)])
                
            if self.config.rule_file:
                cmd.extend(["--rule", self.config.rule_file])
                
            if self.config.intercept_https:
                cmd.append("--intercept")
                
            if self.config.silent:
                cmd.append("--silent")
                
            if self.config.throttle:
                cmd.extend(["--throttle", str(self.config.throttle)])
                
            if self.config.ws_intercept:
                cmd.append("--ws-intercept")
                
            if self.config.ignore_unauthorized_ssl:
                cmd.append("--ignore-unauthorized-ssl")
            
            # Start the AnyProxy process
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.anyproxy_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait a bit for the server to start
            await asyncio.sleep(2)
            
            # Check if the process is still running
            if self.process.returncode is not None:
                stdout, stderr = await self.process.communicate()
                raise RuntimeError(f"AnyProxy failed to start: {stderr.decode()}")
            
            self.is_running = True
            self.logger.info(f"AnyProxy started on port {self.config.port}")
            
            # Start monitoring the process
            asyncio.create_task(self._monitor_process())
            
        except Exception as e:
            self.logger.error(f"Failed to start AnyProxy: {e}")
            raise
    
    async def _monitor_process(self):
        """Monitor the AnyProxy process and handle shutdown"""
        if self.process:
            await self.process.wait()
            self.is_running = False
            self.logger.info("AnyProxy process terminated")
    
    async def stop(self):
        """Stop the AnyProxy server"""
        if self.process and self.process.returncode is None:
            try:
                # Try graceful shutdown first
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if it doesn't terminate gracefully
                    self.process.kill()
                    await self.process.wait()
            except ProcessLookupError:
                pass  # Process already terminated
            finally:
                self.is_running = False
                self.logger.info("AnyProxy stopped")
    
    def get_proxy_url(self) -> str:
        """Get the proxy URL for this instance"""
        return f"http://127.0.0.1:{self.config.port}"
    
    def get_web_interface_url(self) -> Optional[str]:
        """Get the web interface URL if enabled"""
        if self.config.web_interface_port:
            return f"http://127.0.0.1:{self.config.web_interface_port}"
        return None
    
    async def get_request_data(self, request_id: str) -> Optional[Dict]:
        """Get detailed information about a specific request from AnyProxy's recorder"""
        if not self.config.web_interface_port:
            return None
            
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://127.0.0.1:{self.config.web_interface_port}/record/{request_id}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            self.logger.error(f"Failed to get request data: {e}")
        
        return None
    
    async def get_recent_requests(self, limit: int = 10) -> List[Dict]:
        """Get recent requests from AnyProxy's recorder"""
        if not self.config.web_interface_port:
            return []
            
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://127.0.0.1:{self.config.web_interface_port}/records"
                params = {"limit": limit}
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            self.logger.error(f"Failed to get recent requests: {e}")
        
        return []
    
    async def clear_requests(self):
        """Clear the request history in AnyProxy"""
        if not self.config.web_interface_port:
            return
            
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://127.0.0.1:{self.config.web_interface_port}/clear"
                async with session.get(url) as response:
                    return response.status == 200
        except Exception as e:
            self.logger.error(f"Failed to clear requests: {e}")
        
        return False


class AnyProxyRuleBuilder:
    """Helper class to build custom AnyProxy rules in JavaScript"""
    
    @staticmethod
    def create_modify_response_rule(
        target_urls: List[str], 
        modify_func: str,
        summary: str = "Custom response modification rule"
    ) -> str:
        """
        Create a JavaScript rule that modifies responses for specific URLs
        
        Args:
            target_urls: List of URLs or URL patterns to modify
            modify_func: JavaScript function code that modifies the response
            summary: Rule summary
        """
        rule_template = f'''
module.exports = {{
  summary: '{summary}',

  *beforeSendResponse(requestDetail, responseDetail) {{
    const url = requestDetail.url;
    
    // Check if this URL matches our target patterns
    const shouldModify = [
      {', '.join([f"'{url}'" for url in target_urls])}
    ].some(pattern => url.includes(pattern));
    
    if (shouldModify) {{
      const newResponse = responseDetail.response;
      
      // Apply the modification function
      {modify_func}
      
      return {{
        response: newResponse
      }};
    }}
    
    return null;
  }}
}};
'''
        return rule_template.strip()
    
    @staticmethod
    def create_intercept_request_rule(
        target_urls: List[str],
        intercept_func: str,
        summary: str = "Custom request interception rule"
    ) -> str:
        """
        Create a JavaScript rule that intercepts requests for specific URLs
        
        Args:
            target_urls: List of URLs or URL patterns to intercept
            intercept_func: JavaScript function code that handles the request
            summary: Rule summary
        """
        rule_template = f'''
module.exports = {{
  summary: '{summary}',

  *beforeSendRequest(requestDetail) {{
    const url = requestDetail.url;
    
    // Check if this URL matches our target patterns
    const shouldIntercept = [
      {', '.join([f"'{url}'" for url in target_urls])}
    ].some(pattern => url.includes(pattern));
    
    if (shouldIntercept) {{
      // Apply the interception function
      {intercept_func}
    }}
    
    return null;
  }}
}};
'''
        return rule_template.strip()


# Predefined rules for common use cases
class CommonAnyProxyRules:
    """Common predefined AnyProxy rules for typical use cases"""
    
    @staticmethod
    def block_ads_rule() -> str:
        """Rule to block common ad domains"""
        return AnyProxyRuleBuilder.create_intercept_request_rule(
            target_urls=["doubleclick.net", "googlesyndication.com", "googleadservices.com"],
            intercept_func="""
      return {
        protocol: 'http',
        requestData: Buffer.from(''),
        requestOptions: {
          hostname: '127.0.0.1',
          port: 80,
          path: '/',
          method: 'GET',
          headers: {}
        }
      };
            """,
            summary="Block advertisement requests"
        )
    
    @staticmethod
    def modify_user_agent_rule(new_user_agent: str) -> str:
        """Rule to modify user agent in requests"""
        return AnyProxyRuleBuilder.create_intercept_request_rule(
            target_urls=[""],
            intercept_func=f"""
      requestDetail.requestOptions.headers['User-Agent'] = '{new_user_agent}';
      return requestDetail;
            """,
            summary=f"Modify User-Agent to {new_user_agent}"
        )
    
    @staticmethod
    def capture_video_streams_rule() -> str:
        """Rule to capture and log video stream URLs"""
        return AnyProxyRuleBuilder.create_intercept_request_rule(
            target_urls=[".m3u8", ".mpd", ".mp4"],
            intercept_func="""
      console.log('Video stream captured:', requestDetail.url);
      // You can add custom logic here to save the URL or process it
      return null;
            """,
            summary="Capture video stream requests"
        )


async def create_temp_rule_file(rule_content: str) -> str:
    """Create a temporary rule file for AnyProxy"""
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(rule_content)
        return f.name


# Example usage function
async def example_usage():
    """Example of how to use the AnyProxy service"""
    # Create a configuration
    config = ProxyConfig(
        port=8003,
        web_interface_port=8004,
        intercept_https=True,
        ignore_unauthorized_ssl=True
    )
    
    # Create the service
    proxy_service = AnyProxyService(config)
    
    try:
        # Start the proxy
        await proxy_service.start()
        print(f"Proxy running at: {proxy_service.get_proxy_url()}")
        
        # You can now use this proxy in your requests
        # For example, with httpx:
        # import httpx
        # async with httpx.AsyncClient(proxies=proxy_service.get_proxy_url()) as client:
        #     response = await client.get("https://httpbin.org/headers")
        #     print(response.text)
        
        # Wait for some requests to be intercepted
        await asyncio.sleep(10)
        
        # Get recent requests
        recent_requests = await proxy_service.get_recent_requests(limit=5)
        print(f"Captured {len(recent_requests)} requests")
        
    finally:
        # Always stop the proxy when done
        await proxy_service.stop()


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_usage())