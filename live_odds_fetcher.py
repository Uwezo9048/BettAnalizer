"""
Live Odds Fetcher for Supported Betting Sites
Uses Odds-API.io as primary source with SportyBet fallback
"""

import json
import os
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

_live_feeds_setting = os.environ.get("LIVE_FEEDS_ENABLED", "1").strip().lower()
LIVE_FEEDS_ENABLED = os.environ.get("RENDER") == "true" or _live_feeds_setting in {"1", "true", "yes", "on"}

# Disable OddsAfrica-API
API_AVAILABLE = False
API_INSTANCES = {}
API_IMPORT_ERROR = "OddsAfrica-API disabled - using Odds-API.io + SportyBet"

# Supported betting sites
SUPPORTED_LIVE_SITES = {
    "sportybet": {
        "name": "SportyBet",
        "country": "Kenya",
        "flag": "🇰🇪",
        "is_default": True,
        "api_key": "sportybet"
    },
    "bet9ja": {
        "name": "Bet9ja",
        "country": "Nigeria",
        "flag": "🇳🇬",
        "is_default": False,
        "api_key": "bet9ja"
    },
    "22bet": {
        "name": "22Bet",
        "country": "International",
        "flag": "🌍",
        "is_default": False,
        "api_key": "22bet"
    },
    "paripesa": {
        "name": "Paripesa",
        "country": "Kenya",
        "flag": "🇰🇪",
        "is_default": False,
        "api_key": "paripesa"
    },
    "nairabet": {
        "name": "Nairabet",
        "country": "Nigeria",
        "flag": "🇳🇬",
        "is_default": False,
        "api_key": "nairabet"
    },
    "betking": {
        "name": "BetKing",
        "country": "Nigeria",
        "flag": "🇳🇬",
        "is_default": False,
        "api_key": "betking"
    }
}

SUPPORTED_SPORTS = {
    "football": {"name": "Football", "icon": "⚽", "live_feed": True},
    "basketball": {"name": "Basketball", "icon": "🏀", "live_feed": True},
    "tennis": {"name": "Tennis", "icon": "🎾", "live_feed": True},
    "volleyball": {"name": "Volleyball", "icon": "🏐", "live_feed": True},
    "icehockey": {"name": "Ice Hockey", "icon": "🏒", "live_feed": True},
    "darts": {"name": "Darts", "icon": "🎯", "live_feed": True},
}

SPORTYBET_SPORT_IDS = {
    "football": "sr:sport:1",
    "basketball": "sr:sport:2",
    "tennis": "sr:sport:5",
    "volleyball": "sr:sport:23",
    "icehockey": "sr:sport:4",
    "darts": "sr:sport:22",
}

print("ℹ️  Running with Odds-API.io + SportyBet")


class LiveOddsFetcher:
    """Fetches live odds from Odds-API.io and SportyBet"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 60  # seconds
        self.live_fetch_timeout = 10
        self._odds_api_io = None
        
    
    
    def get_supported_sites(self):
        """Return list of sites with live feed capability"""
        sites = []
        for key, site in SUPPORTED_LIVE_SITES.items():
            sites.append({
                "id": key,
                "name": site["name"],
                "country": site["country"],
                "flag": site["flag"],
                "is_default": site.get("is_default", False),
                "live_feed": LIVE_FEEDS_ENABLED
            })
        return sites

    def get_supported_sports(self, site_id="sportybet"):
        """Return all visible sports categories"""
        sports = []
        for key, sport in SUPPORTED_SPORTS.items():
            sports.append({
                "id": key,
                "name": sport["name"],
                "icon": sport["icon"],
                "enabled": True,
                "live_feed": True,
                "stored_count": 0
            })
        return sports
    
    def fetch_live_odds(self, site_id, sport="football"):
        """
        Fetch live odds - tries Odds-API.io first, then SportyBet
        
        Args:
            site_id: Site identifier (sportybet, bet9ja, etc.)
            sport: Sport type (default: football)
        
        Returns:
            List of matches with live odds
        """
        # Check cache
        cache_key = f"{site_id}_{sport}"
        if cache_key in self.cache:
            cache_time, cache_data = self.cache[cache_key]
            if (time.time() - cache_time) < self.cache_duration:
                return cache_data
        
        if sport not in SUPPORTED_SPORTS:
            return []

        print(f"[DEBUG] Fetching odds for {site_id} - {sport}")
        
        # TRY 1: Odds-API.io (REAL ODDS - Primary)
        try:
            print("[DEBUG] Trying Odds-API.io...")
            api = self._get_odds_api_io()
            if api and api.client:
                matches = api.get_live_events(sport, limit=30)
                if matches and len(matches) > 0:
                    print(f"[DEBUG] ✅ Found {len(matches)} REAL matches from Odds-API.io")
                    # Remove sample flag if present
                    for match in matches:
                        match['sample'] = False
                        match['from_api'] = True
                    self.cache[cache_key] = (time.time(), matches)
                    return matches
                else:
                    print("[DEBUG] Odds-API.io returned no matches")
        except Exception as e:
            print(f"[DEBUG] Odds-API.io failed: {e}")
        
        # TRY 2: SportyBet direct API (for African bookmaker odds)
        try:
            print("[DEBUG] Trying SportyBet direct API...")
            matches = self._fetch_sportybet_direct(sport)
            if matches and len(matches) > 0 and not self._is_srl_data(matches):
                print(f"[DEBUG] ✅ Found {len(matches)} REAL matches from SportyBet")
                self.cache[cache_key] = (time.time(), matches)
                return matches
        except Exception as e:
            print(f"[DEBUG] SportyBet direct API failed: {e}")
        
        # No real matches found - return empty list
        print(f"[DEBUG] ❌ No real matches found for {site_id}")
        return []

    def fetch_value_bets(self, bookmaker: str = None, limit: int = 20):
        """Fetch value bet recommendations from Odds-API.io"""
        try:
            api = self._get_odds_api_io()
            if api and api.client:
                return api.get_value_bets(bookmaker, limit)
        except Exception as e:
            print(f"[DEBUG] Error fetching value bets: {e}")
        return []

    def fetch_arbitrage_opportunities(self, bookmakers: str = "bet365,pinnacle", limit: int = 10):
        """Fetch arbitrage opportunities from Odds-API.io"""
        try:
            api = self._get_odds_api_io()
            if api and api.client:
                return api.get_arbitrage_opportunities(bookmakers, limit)
        except Exception as e:
            print(f"[DEBUG] Error fetching arbitrage opportunities: {e}")
        return []

    def _fetch_sportybet_direct(self, sport):
        """Fetch SportyBet Kenya events directly"""
        sport_id = SPORTYBET_SPORT_IDS.get(sport)
        if not sport_id:
            return []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.sportybet.com/ke/sport/football/",
            "Clientid": "web",
            "Platform": "web",
            "Operid": "1",
        }
        
        endpoints = [
            "https://www.sportybet.com/api/ke/factsCenter/liveOrPrematchEvents",
            "https://www.sportybet.com/api/ke/factsCenter/importantEvents",
        ]
        
        params = {
            "sportId": sport_id, 
            "productId": 3
        }
        
        events_by_id = {}

        for endpoint in endpoints:
            try:
                response = requests.get(
                    endpoint, 
                    headers=headers, 
                    params=params, 
                    timeout=self.live_fetch_timeout
                )
                response.raise_for_status()
                payload = response.json()
                
                if payload.get("bizCode") != 10000:
                    continue

                for tournament in payload.get("data") or []:
                    tournament_name = tournament.get("name") or ""
                    
                    # Skip simulated leagues
                    if any(keyword in tournament_name.lower() 
                           for keyword in ["srl", "simulated", "virtual"]):
                        continue
                    
                    for event in tournament.get("events") or []:
                        # Skip simulated events
                        if "SRL" in event.get("homeTeamName", "") or "SRL" in event.get("awayTeamName", ""):
                            continue
                        
                        parsed = self._parse_sportybet_event(event, tournament_name)
                        if parsed:
                            events_by_id[parsed["id"]] = parsed
                            
            except Exception as e:
                print(f"[DEBUG] Error fetching from {endpoint}: {e}")
                continue

        matches = list(events_by_id.values())
        print(f"[DEBUG] Found {len(matches)} matches from SportyBet")
        return matches[:50]

    def _parse_sportybet_event(self, event, tournament_name):
        """Parse a SportyBet event into standard format"""
        structured_markets = {}

        for market in event.get("markets") or []:
            market_name = market.get("name") or ""
            outcomes = market.get("outcomes") or []
            active_outcomes = [
                outcome for outcome in outcomes
                if outcome.get("isActive", 1) == 1 and outcome.get("odds") not in (None, "")
            ]
            if not active_outcomes:
                continue

            if market.get("id") == "1" or market_name == "1X2":
                structured_markets["1X2"] = {}
                for outcome in active_outcomes:
                    label = outcome.get("desc", "")
                    if label in ["Home", "Draw", "Away"]:
                        structured_markets["1X2"][label] = float(outcome.get("odds", 0))
            
            elif "Over/Under" in market_name and "Over/Under" not in structured_markets:
                structured_markets["Over/Under"] = {}
                for outcome in active_outcomes[:2]:
                    label = outcome.get("desc", "")
                    if label:
                        structured_markets["Over/Under"][label] = float(outcome.get("odds", 0))
            
            elif ("Both Teams to Score" in market_name or market_name == "GG/NG") and "GG/NG" not in structured_markets:
                structured_markets["GG/NG"] = {}
                for outcome in active_outcomes:
                    label = outcome.get("desc", "")
                    if label in ["Yes", "No"]:
                        structured_markets["GG/NG"][label] = float(outcome.get("odds", 0))

        if not structured_markets:
            return None

        return {
            "id": event.get("eventId") or abs(hash(str(event))) % 1000000,
            "home_team": event.get("homeTeamName") or "Home",
            "away_team": event.get("awayTeamName") or "Away",
            "league": tournament_name,
            "country": "Kenya",
            "markets": structured_markets,
            "site": "sportybet",
            "live": False,
            "last_updated": datetime.now().isoformat(),
        }

    def _is_srl_data(self, matches):
        """Check if matches are SRL data"""
        if not matches:
            return True
        
        for match in matches[:3]:
            league = match.get('league', '').lower()
            home = match.get('home_team', '').lower()
            away = match.get('away_team', '').lower()
            
            if any(keyword in league or keyword in home or keyword in away 
                   for keyword in ['srl', 'simulated', 'virtual']):
                return True
        
        return False


# Global fetcher instance
_fetcher = None

def get_fetcher():
    global _fetcher
    if _fetcher is None:
        _fetcher = LiveOddsFetcher()
    return _fetcher