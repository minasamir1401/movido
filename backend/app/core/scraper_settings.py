
import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger("scraper_settings")

class ScraperSettings:
    """
    Dynamic scraper configuration manager.
    Allows enabling/disabling different content sources from Dashboard.
    """
    def __init__(self, config_file: str = "scraper_config.json"):
        self.config_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "..", "..", "cache", 
            config_file
        )
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file or create defaults"""
        default_settings = {
            "larooza_enabled": True,
            "arabseed_enabled": True,
            "anime4up_enabled": True,
            "fallback_mode": True,  # Auto-fallback if primary fails
            "merge_results": True,  # Merge results from multiple sources
            "primary_source": "larooza",  # Primary source for details
            "last_modified": None
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    default_settings.update(loaded)
                    logger.info(f"Loaded scraper settings from {self.config_file}")
            except Exception as e:
                logger.error(f"Error loading scraper settings: {e}")
        else:
            # Create config file with defaults
            self._save_settings(default_settings)
            logger.info(f"Created default scraper settings at {self.config_file}")
        
        return default_settings
    
    def _save_settings(self, settings: Dict[str, Any] = None):
        """Save settings to JSON file"""
        if settings is None:
            settings = self.settings
        
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved scraper settings to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving scraper settings: {e}")
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """Update settings and save to file"""
        import time
        self.settings.update(new_settings)
        self.settings["last_modified"] = time.time()
        self._save_settings()
        logger.info(f"Updated scraper settings: {new_settings}")
    
    def is_enabled(self, source: str) -> bool:
        """Check if a scraper source is enabled"""
        key = f"{source}_enabled"
        return self.settings.get(key, False)
    
    def get_enabled_sources(self) -> list:
        """Get list of all enabled sources"""
        sources = []
        for key in ["larooza", "arabseed", "anime4up"]:
            if self.is_enabled(key):
                sources.append(key)
        return sources
    
    def get_primary_source(self) -> str:
        """Get the primary source"""
        return self.settings.get("primary_source", "larooza")
    
    def is_fallback_enabled(self) -> bool:
        """Check if fallback mode is enabled"""
        return self.settings.get("fallback_mode", True)
    
    def should_merge_results(self) -> bool:
        """Check if results should be merged from multiple sources"""
        return self.settings.get("merge_results", True)
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all current settings"""
        return self.settings.copy()

# Global instance
scraper_settings = ScraperSettings()
