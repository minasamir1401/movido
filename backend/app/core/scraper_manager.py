"""
Scraper Manager - Smart Fallback System
Manages multiple scrapers with automatic failover
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import httpx

logger = logging.getLogger("scraper_manager")

class ScraperStatus:
    """Track scraper health and availability"""
    def __init__(self, name: str, url: str, enabled: bool = True, priority: int = 1):
        self.name = name
        self.url = url
        self.enabled = enabled
        self.priority = priority
        self.is_online = True
        self.last_check = None
        self.error_count = 0
        self.success_count = 0
        self.response_time = 0
        
    def to_dict(self):
        return {
            "name": self.name,
            "url": self.url,
            "enabled": self.enabled,
            "priority": self.priority,
            "is_online": self.is_online,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "response_time": self.response_time,
            "health_score": self.get_health_score()
        }
    
    def get_health_score(self) -> float:
        """Calculate health score (0-100)"""
        total = self.success_count + self.error_count
        if total == 0:
            return 100.0
        success_rate = (self.success_count / total) * 100
        # Factor in response time (penalize slow responses)
        time_penalty = min(self.response_time / 10, 20)  # Max 20 point penalty
        return max(0, success_rate - time_penalty)


class ScraperManager:
    """
    Manages multiple scrapers with automatic failover
    """
    def __init__(self):
        self.scrapers: Dict[str, ScraperStatus] = {}
        self._init_scrapers()
        
    def _init_scrapers(self):
        """Initialize available scrapers"""
        # Arabic Content Scrapers (Movies & Series)
        self.scrapers["larooza"] = ScraperStatus(
            name="Larooza",
            url="https://q.larozavideo.net",
            enabled=True,
            priority=1  # Primary
        )
        
        self.scrapers["mycima"] = ScraperStatus(
            name="ArabSeed",
            url="https://m2.arabseed.one",
            enabled=True,
            priority=2  # Fallback
        )
        
        # Anime Scrapers
        self.scrapers["anime4up"] = ScraperStatus(
            name="Anime4Up",
            url="https://4r.2qk9x7b.shop",
            enabled=True,
            priority=1
        )
        
        self.scrapers["animerco"] = ScraperStatus(
            name="AnimeRCO",
            url="https://animerco.com",
            enabled=True,
            priority=2
        )
    
    async def check_scraper_health(self, scraper_name: str) -> bool:
        """Check if a scraper is online and responsive"""
        if scraper_name not in self.scrapers:
            return False
            
        scraper = self.scrapers[scraper_name]
        
        try:
            start_time = asyncio.get_event_loop().time()
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                response = await client.get(scraper.url, follow_redirects=True)
                end_time = asyncio.get_event_loop().time()
                
                scraper.response_time = (end_time - start_time) * 1000  # ms
                scraper.last_check = datetime.now()
                
                if response.status_code == 200:
                    scraper.is_online = True
                    scraper.success_count += 1
                    scraper.error_count = max(0, scraper.error_count - 1)  # Decay errors
                    return True
                else:
                    scraper.is_online = False
                    scraper.error_count += 1
                    return False
                    
        except Exception as e:
            logger.error(f"Health check failed for {scraper_name}: {e}")
            scraper.is_online = False
            scraper.error_count += 1
            scraper.last_check = datetime.now()
            return False
    
    async def check_all_scrapers(self):
        """Check health of all enabled scrapers"""
        tasks = []
        for name, scraper in self.scrapers.items():
            if scraper.enabled:
                tasks.append(self.check_scraper_health(name))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_available_scrapers(self, content_type: str = "arabic") -> List[str]:
        """
        Get list of available scrapers sorted by priority
        
        Args:
            content_type: "arabic" for movies/series, "anime" for anime
        """
        if content_type == "arabic":
            scraper_names = ["larooza", "mycima"]
        elif content_type == "anime":
            scraper_names = ["anime4up", "animerco"]
        else:
            scraper_names = list(self.scrapers.keys())
        
        # Filter enabled and online scrapers
        available = [
            name for name in scraper_names
            if name in self.scrapers 
            and self.scrapers[name].enabled 
            and self.scrapers[name].is_online
        ]
        
        # Sort by priority (lower number = higher priority)
        available.sort(key=lambda x: self.scrapers[x].priority)
        
        return available
    
    def get_primary_scraper(self, content_type: str = "arabic") -> Optional[str]:
        """Get the primary (highest priority) available scraper"""
        available = self.get_available_scrapers(content_type)
        return available[0] if available else None
    
    def get_fallback_scraper(self, failed_scraper: str, content_type: str = "arabic") -> Optional[str]:
        """Get the next available scraper after a failure"""
        available = self.get_available_scrapers(content_type)
        
        # Remove the failed scraper from the list
        available = [s for s in available if s != failed_scraper]
        
        return available[0] if available else None
    
    def set_scraper_enabled(self, scraper_name: str, enabled: bool):
        """Enable or disable a scraper"""
        if scraper_name in self.scrapers:
            self.scrapers[scraper_name].enabled = enabled
            logger.info(f"Scraper {scraper_name} {'enabled' if enabled else 'disabled'}")
    
    def set_scraper_priority(self, scraper_name: str, priority: int):
        """Set scraper priority (1 = highest)"""
        if scraper_name in self.scrapers:
            self.scrapers[scraper_name].priority = priority
            logger.info(f"Scraper {scraper_name} priority set to {priority}")
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all scrapers"""
        return {
            name: scraper.to_dict() 
            for name, scraper in self.scrapers.items()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics"""
        total = len(self.scrapers)
        enabled = sum(1 for s in self.scrapers.values() if s.enabled)
        online = sum(1 for s in self.scrapers.values() if s.is_online and s.enabled)
        
        return {
            "total_scrapers": total,
            "enabled_scrapers": enabled,
            "online_scrapers": online,
            "offline_scrapers": enabled - online,
            "health_percentage": (online / enabled * 100) if enabled > 0 else 0
        }


# Global instance
scraper_manager = ScraperManager()
