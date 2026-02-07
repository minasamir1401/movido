"""
Enhanced AnyProxy Integration Service for Python

This module provides a Python interface to AnyProxy, allowing you to intercept,
inspect, and modify HTTP/HTTPS traffic directly from your Python application,
with special focus on media extraction capabilities.
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import queue
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Union
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
    host: str = "127.0.0.1"


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
        self._media_capture_queue = queue.Queue()
        self._capture_thread = None
        self._stop_event = threading.Event()
        self._temp_rule_file = None
        
        # Validate AnyProxy installation
        self._validate_anyproxy_installation()
        
    def _validate_anyproxy_installation(self):
        """Validate that AnyProxy is properly installed"""
        if not self.anyproxy_path.exists():
            raise FileNotFoundError(f"AnyProxy directory not found at {self.anyproxy_path}")
            
        required_files = [
            self.anyproxy_path / "bin" / "anyproxy",
            self.anyproxy_path / "proxy.js",
            self.anyproxy_path / "package.json"
        ]
        
        for file_path in required_files:
            if not file_path.exists():
                raise FileNotFoundError(f"Required AnyProxy file not found: {file_path}")
        
        # Check if node and npm are available
        try:
            import shutil
            if not shutil.which("node"):
                raise RuntimeError("Node.js is not installed or not in PATH")
            if not shutil.which("npm"):
                self.logger.warning("npm not found, but may not be required if AnyProxy dependencies are already installed")
        except ImportError:
            raise RuntimeError("Python shutil module not available")

    def add_request_handler(self, handler: Callable[[RequestInfo], Any]):
        """Add a handler for intercepted requests"""
        self._request_handlers.append(handler)
        
    def add_response_handler(self, handler: Callable[[ResponseInfo], Any]):
        """Add a handler for intercepted responses"""
        self._response_handlers.append(handler)
        
    async def start(self):
        """Start the AnyProxy server"""
        try:
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
        return f"http://{self.config.host}:{self.config.port}"
    
    def get_web_interface_url(self) -> Optional[str]:
        """Get the web interface URL if enabled"""
        if self.config.web_interface_port:
            return f"http://{self.config.host}:{self.config.web_interface_port}"
        return None
    
    async def get_request_data(self, request_id: str) -> Optional[Dict]:
        """Get detailed information about a specific request from AnyProxy's recorder"""
        if not self.config.web_interface_port:
            return None
            
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://{self.config.host}:{self.config.web_interface_port}/record/{request_id}"
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
                url = f"http://{self.config.host}:{self.config.web_interface_port}/records"
                params = {"limit": limit}
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            self.logger.error(f"Failed to get recent requests: {e}")
        
        return []


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
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(rule_content)
        return f.name


class MediaExtractorWithProxy(AnyProxyService):
    """
    Enhanced AnyProxy service specifically designed for media extraction.
    This class provides methods to capture video streams and media content
    from intercepted HTTP/HTTPS traffic.
    """
    
    def __init__(self, config: ProxyConfig = None):
        super().__init__(config)
        self.captured_media_urls: List[Dict[str, Any]] = []
        self.captured_requests: List[Dict[str, Any]] = []
        
    async def start_with_media_capture(self, target_urls: Optional[List[str]] = None):
        """
        Start AnyProxy with media capture capabilities
        
        Args:
            target_urls: Optional list of URLs to specifically target for media capture
        """
        # Create a custom rule to capture media requests
        if target_urls is None:
            target_urls = [".m3u8", ".mpd", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"]
        
        media_capture_rule = AnyProxyRuleBuilder.create_intercept_request_rule(
            target_urls=target_urls,
            intercept_func="""
      // Capture media request information
      const mediaInfo = {
        url: requestDetail.url,
        method: requestDetail.method,
        headers: requestDetail.requestOptions.headers,
        timestamp: new Date().toISOString(),
        type: 'media'
      };
      
      // Log to console for debugging
      console.log('CAPTURED_MEDIA_URL:', JSON.stringify(mediaInfo));
      
      // Store in global array if available
      if (typeof global.mediaCaptures === 'undefined') {
        global.mediaCaptures = [];
      }
      global.mediaCaptures.push(mediaInfo);
      
      return null;
            """,
            summary="Media URL Capture Rule"
        )
        
        # Save the rule to a temporary file
        self._temp_rule_file = await create_temp_rule_file(media_capture_rule)
        self.config.rule_file = self._temp_rule_file
        
        # Start the proxy with the media capture rule
        await self.start()
    
    async def get_captured_media_urls(self) -> List[Dict[str, Any]]:
        """
        Get all captured media URLs from the proxy session
        
        Returns:
            List of dictionaries containing media URL information
        """
        if not self.config.web_interface_port:
            # Fallback to in-memory storage if web interface is not available
            return self.captured_media_urls
        
        # Get all requests and filter for media content
        all_requests = await self.get_recent_requests(limit=1000)
        media_urls = []
        
        for request in all_requests:
            url = request.get('url', '')
            path = request.get('path', '')
            
            # Check if the request is for media content
            if any(ext in url.lower() or ext in path.lower() for ext in ['.m3u8', '.mpd', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']):
                media_urls.append({
                    'url': url,
                    'method': request.get('method'),
                    'headers': request.get('reqHeader'),
                    'timestamp': request.get('startTime'),
                    'type': 'media'
                })
        
        return media_urls
    
    async def capture_media_from_url(self, target_url: str, timeout: int = 30) -> List[Dict[str, Any]]:
        """
        Capture media URLs from a specific target URL
        
        Args:
            target_url: The URL to visit and capture media from
            timeout: How long to wait for media capture in seconds
        
        Returns:
            List of captured media URLs
        """
        if not self.is_running:
            await self.start_with_media_capture()

        # Clear previous captures
        self.captured_media_urls = []

        # Make a request through the proxy to capture media
        import httpx
        proxy_url = self.get_proxy_url()
        
        async with httpx.AsyncClient(proxy=proxy_url, timeout=timeout) as client:
            try:
                response = await client.get(target_url, follow_redirects=True)
                # Wait a bit for all media requests to be captured
                await asyncio.sleep(5)
            except Exception as e:
                self.logger.error(f"Error capturing media from {target_url}: {e}")

        # Get captured media URLs
        media_urls = await self.get_captured_media_urls()

        return media_urls
    
    async def stop(self):
        """Stop the proxy and cleanup temporary files"""
        await super().stop()
        
        # Clean up temporary rule file
        if self._temp_rule_file and os.path.exists(self._temp_rule_file):
            try:
                os.unlink(self._temp_rule_file)
            except OSError:
                pass  # Ignore errors when removing temp file
        
        self._temp_rule_file = None


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