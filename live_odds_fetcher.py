"""
Live Odds Fetcher for Supported Betting Sites
Uses OddsAfrica-API for real-time data from:
- SportyBet (Default)
- Bet9ja
- 22bet
- Paripesa
- Nairabet
- Betking
"""

import json
import os
import queue
import sys
import threading
import time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

_live_feeds_setting = os.environ.get("LIVE_FEEDS_ENABLED", "1").strip().lower()
LIVE_FEEDS_ENABLED = os.environ.get("RENDER") == "true" or _live_feeds_setting in {"1", "true", "yes", "on"}
API_IMPORT_ERROR = None

# Supported betting sites with live feed capability
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

# Try to import OddsAfrica-API
try:
    local_api_path = os.path.join(os.path.dirname(__file__), "OddsAfrica-API")
    if os.path.isdir(local_api_path) and local_api_path not in sys.path:
        sys.path.insert(0, local_api_path)

    from engine.bookie_models.sportybet_model import SportyBet
    from engine.bookie_models.betnaija_model import bet9ja as Bet9ja
    from engine.bookie_models.bet22_model import bet22 as TwentyTwoBet
    from engine.bookie_models.paripesa_model import Paripesa
    from engine.bookie_models.nairabet_model import nairabet as Nairabet
    from engine.bookie_models.betking_model import betking as BetKing
    
    API_AVAILABLE = True
    
    # Initialize API instances
    API_INSTANCES = {
        "sportybet": SportyBet(),
        "bet9ja": Bet9ja(),
        "22bet": TwentyTwoBet(),
        "paripesa": Paripesa(),
        "nairabet": Nairabet(),
        "betking": BetKing()
    }
    print("OddsAfrica-API loaded - Live feeds available for all sites.")
    
except ImportError as e:
    API_IMPORT_ERROR = str(e)
    print(f"OddsAfrica-API not available: {e}")
    print("   Install with: pip install git+https://github.com/PeterEkwere/OddsAfrica-API.git")
    API_AVAILABLE = False
    API_INSTANCES = {}


class LiveOddsFetcher:
    """Fetches live odds from supported betting sites"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 30  # seconds
        self.live_fetch_timeout = 8  # seconds
    
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
                "live_feed": API_AVAILABLE and LIVE_FEEDS_ENABLED
            })
        return sites
    
    def fetch_live_odds(self, site_id, sport="football"):
        """
        Fetch live odds from specified site using OddsAfrica-API
        
        Args:
            site_id: Site identifier (sportybet, bet9ja, 22bet, paripesa, nairabet, betking)
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
        
        if not LIVE_FEEDS_ENABLED or not API_AVAILABLE or site_id not in API_INSTANCES:
            return self._get_sample_data(site_id)
        
        try:
            api_instance = API_INSTANCES[site_id]
            raw_data = self._run_with_timeout(api_instance.Get_games, sport)
            
            if not raw_data:
                stored_matches = self._get_stored_matches(site_id, sport)
                fallback_data = stored_matches or self._get_sample_data(site_id)
                self.cache[cache_key] = (time.time(), fallback_data)
                return fallback_data
            
            matches = self._parse_api_response(raw_data, site_id)
            if not matches:
                stored_matches = self._get_stored_matches(site_id, sport)
                fallback_data = stored_matches or self._get_sample_data(site_id)
                self.cache[cache_key] = (time.time(), fallback_data)
                return fallback_data
            
            # Cache results
            self.cache[cache_key] = (time.time(), matches)
            
            return matches
            
        except Exception as e:
            print(f"Error fetching from {site_id}: {e}")
            stored_matches = self._get_stored_matches(site_id, sport)
            fallback_data = stored_matches or self._get_sample_data(site_id)
            self.cache[cache_key] = (time.time(), fallback_data)
            return fallback_data

    def _run_with_timeout(self, func, *args):
        """Run slow live scrapers with a hard response deadline."""
        result_queue = queue.Queue(maxsize=1)

        def target():
            try:
                result_queue.put((True, func(*args)))
            except Exception as exc:
                result_queue.put((False, exc))

        worker = threading.Thread(target=target, daemon=True)
        worker.start()
        worker.join(self.live_fetch_timeout)

        if worker.is_alive():
            raise TimeoutError(f"Live feed timed out after {self.live_fetch_timeout}s")

        ok, result = result_queue.get()
        if ok:
            return result
        raise result
    
    def _parse_api_response(self, raw_data, site_id):
        """Parse the API response into a standardized format"""
        matches = []
        
        try:
            for country, leagues in raw_data.items():
                for league, games in leagues.items():
                    for game_name, markets in games.items():
                        # Parse team names
                        if " vs " in game_name:
                            parts = game_name.split(" vs ")
                            home_team = parts[0].strip()
                            away_team = parts[1].strip()
                        else:
                            home_team = game_name
                            away_team = "Opponent"
                        
                        # Structure markets
                        structured_markets = {}
                        
                        # 1X2 market
                        if "1X2" in markets and isinstance(markets["1X2"], dict):
                            structured_markets["1X2"] = markets["1X2"]
                        
                        # Over/Under markets
                        if "Over/Under" in markets and isinstance(markets["Over/Under"], dict):
                            structured_markets["Over/Under"] = markets["Over/Under"]
                        
                        # GG/NG (Both Teams to Score)
                        if "GG/NG" in markets and isinstance(markets["GG/NG"], dict):
                            structured_markets["GG/NG"] = markets["GG/NG"]
                        
                        # Double Chance
                        if "Double Chance" in markets and isinstance(markets["Double Chance"], dict):
                            structured_markets["Double Chance"] = markets["Double Chance"]
                        
                        # Handicap markets
                        if "Handicap 0:1" in markets and isinstance(markets["Handicap 0:1"], dict):
                            structured_markets["Handicap 0:1"] = markets["Handicap 0:1"]
                        
                        if structured_markets:
                            matches.append({
                                "id": abs(hash(f"{country}_{league}_{game_name}_{site_id}")) % 1000000,
                                "home_team": home_team,
                                "away_team": away_team,
                                "league": f"{country} - {league}" if country != league else league,
                                "country": country,
                                "markets": structured_markets,
                                "site": site_id,
                                "live": True,
                                "last_updated": datetime.now().isoformat()
                            })
            
            return matches[:50]  # Limit to 50 matches
            
        except Exception as e:
            print(f"Parse error: {e}")
            return self._get_sample_data(site_id)

    def _get_stored_matches(self, site_id, sport):
        """Load the freshest stored OddsAfrica data that contains usable matches."""
        storage_paths = [
            os.path.join(os.path.dirname(__file__), "engine", "storage_engine", "bookie_storage", sport, f"{site_id}_{sport}.json"),
            os.path.join(os.path.dirname(__file__), "OddsAfrica-API", "engine", "storage_engine", "bookie_storage", sport, f"{site_id}_{sport}.json"),
        ]
        existing_paths = [path for path in storage_paths if os.path.isfile(path)]
        existing_paths.sort(key=os.path.getmtime, reverse=True)

        for path in existing_paths:
            try:
                with open(path, "r", encoding="utf-8") as data_file:
                    stored_data = json.load(data_file)
                matches = self._parse_api_response(stored_data, site_id)
                if matches and not matches[0].get("sample"):
                    for match in matches:
                        match["live"] = False
                        match["from_storage"] = True
                        match["storage_updated_at"] = datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
                    return matches
            except Exception as e:
                print(f"Error loading stored odds from {path}: {e}")

        return []
    
    def _get_sample_data(self, site_id):
        """Return sample data if API fails (fallback)"""
        site_info = SUPPORTED_LIVE_SITES.get(site_id, {})
        site_name = site_info.get("name", site_id)
        
        return [
            {
                "id": 1,
                "home_team": "Liverpool",
                "away_team": "Manchester City",
                "league": "English Premier League",
                "country": "England",
                "markets": {
                    "1X2": {"Home": 2.40, "Draw": 3.60, "Away": 2.75},
                    "Over/Under 2.5": {"Over": 1.65, "Under": 2.20},
                    "GG/NG": {"Yes": 1.57, "No": 2.30},
                    "Double Chance": {"Home or Draw": 1.44, "Home or Away": 1.30, "Draw or Away": 1.53}
                },
                "site": site_id,
                "live": False,
                "sample": True,
                "note": f"Sample data for {site_name} - Install OddsAfrica-API for live feeds"
            },
            {
                "id": 2,
                "home_team": "Real Madrid",
                "away_team": "Barcelona",
                "league": "La Liga",
                "country": "Spain",
                "markets": {
                    "1X2": {"Home": 1.95, "Draw": 3.80, "Away": 3.50},
                    "Over/Under 2.5": {"Over": 1.70, "Under": 2.10},
                    "GG/NG": {"Yes": 1.50, "No": 2.50}
                },
                "site": site_id,
                "live": False,
                "sample": True
            },
            {
                "id": 3,
                "home_team": "Bayern Munich",
                "away_team": "Borussia Dortmund",
                "league": "Bundesliga",
                "country": "Germany",
                "markets": {
                    "1X2": {"Home": 1.55, "Draw": 4.50, "Away": 5.00},
                    "Over/Under 3.5": {"Over": 1.90, "Under": 1.90},
                    "GG/NG": {"Yes": 1.44, "No": 2.62}
                },
                "site": site_id,
                "live": False,
                "sample": True
            }
        ]


# Global fetcher instance
_fetcher = None

def get_fetcher():
    global _fetcher
    if _fetcher is None:
        _fetcher = LiveOddsFetcher()
    return _fetcher
