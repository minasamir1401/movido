from fastapi import APIRouter
from scraper.matches import matches_scraper

router = APIRouter()

@router.get("/matches")
async def get_matches():
    """
    Get list of today's football matches.
    """
    matches = await matches_scraper.fetch_matches()
    # Fallback mock data if scraper returns empty (due to protection), just for visualization demo
    if not matches:
        return [
            {
                "team_home": "Real Madrid",
                "team_away": "Barcelona", 
                "time": "22:00",
                "status": "Tonight",
                "logo_home": "https://upload.wikimedia.org/wikipedia/en/thumb/5/56/Real_Madrid_CF.svg/1200px-Real_Madrid_CF.svg.png",
                "logo_away": "https://upload.wikimedia.org/wikipedia/en/thumb/4/47/FC_Barcelona_%28crest%29.svg/1200px-FC_Barcelona_%28crest%29.svg.png",
                "score": "0 - 0"
            },
            {
                "team_home": "Liverpool",
                "team_away": "Man City",
                "time": "18:30", 
                "status": "Live",
                "logo_home": "https://upload.wikimedia.org/wikipedia/en/thumb/0/0c/Liverpool_FC.svg/1200px-Liverpool_FC.svg.png",
                "logo_away": "https://upload.wikimedia.org/wikipedia/en/thumb/e/eb/Manchester_City_FC_badge.svg/1200px-Manchester_City_FC_badge.svg.png",
                "score": "2 - 1"
            }
        ]
    return matches
