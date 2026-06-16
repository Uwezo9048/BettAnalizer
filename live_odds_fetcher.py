"""
Live Odds Fetcher for Supported Betting Sites
Uses Odds-API.io as primary source with SportyBet fallback and sample data
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

# Disable OddsAfrica-API completely to avoid dependency issues
API_AVAILABLE = False
API_INSTANCES = {}
API_IMPORT_ERROR = "OddsAfrica-API disabled - using Odds-API.io + SportyBet + sample data"

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

print("ℹ️  Running with Odds-API.io + SportyBet + sample data")


class LiveOddsFetcher:
    """Fetches live odds from multiple sources: Odds-API.io, SportyBet, and sample data"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 60  # seconds
        self.live_fetch_timeout = 10
        self._odds_api_io = None
        
    def _get_odds_api_io(self):
        """Lazy load Odds-API.io client"""
        if self._odds_api_io is None:
            try:
                # Try different import paths
                try:
                    from odds_api_io import OddsAPIIO
                except ImportError:
                    try:
                        from odds_api import OddsAPIIO
                    except ImportError:
                        from odds_api_io import OddsAPIIO
                
                self._odds_api_io = OddsAPIIO()
                if self._odds_api_io.client:
                    print("[DEBUG] Odds-API.io client initialized")
                else:
                    print("[DEBUG] Odds-API.io client not available - check API key")
                    self._odds_api_io = False
            except ImportError:
                print("[DEBUG] Odds-API.io module not available")
                self._odds_api_io = False
            except Exception as e:
                print(f"[DEBUG] Error initializing Odds-API.io: {e}")
                self._odds_api_io = False
        return self._odds_api_io
    
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
        Fetch live odds - tries multiple sources in order:
        1. Odds-API.io (real odds with value detection)
        2. SportyBet direct API
        3. Sample data (fallback)
        
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
        
        # TRY 1: Odds-API.io (primary source)
        try:
            print("[DEBUG] Trying Odds-API.io...")
            api = self._get_odds_api_io()
            if api and api.client:
                matches = api.get_live_events(sport, limit=30)
                if matches:
                    print(f"[DEBUG] ✅ Found {len(matches)} matches from Odds-API.io")
                    self.cache[cache_key] = (time.time(), matches)
                    return matches
                else:
                    print("[DEBUG] Odds-API.io returned no matches")
        except Exception as e:
            print(f"[DEBUG] Odds-API.io failed: {e}")
        
        # TRY 2: SportyBet direct API
        try:
            print("[DEBUG] Trying SportyBet direct API...")
            matches = self._fetch_sportybet_direct(sport)
            if matches and not self._is_sample_data(matches):
                print(f"[DEBUG] ✅ Found {len(matches)} real matches from SportyBet")
                self.cache[cache_key] = (time.time(), matches)
                return matches
            elif matches:
                print("[DEBUG] SportyBet returned SRL data, trying fallback...")
        except Exception as e:
            print(f"[DEBUG] SportyBet direct API failed: {e}")
        
        # FALLBACK: Sample data
        print(f"[DEBUG] Using sample data for {site_id}")
        sample_data = self._get_sample_data(site_id)
        self.cache[cache_key] = (time.time(), sample_data)
        return sample_data

    def fetch_value_bets(self, bookmaker: str = None, limit: int = 20):
        """
        Fetch value bet recommendations from Odds-API.io
        
        Args:
            bookmaker: Specific bookmaker to check (e.g., 'bet365', 'pinnacle')
            limit: Maximum number of value bets to return
        
        Returns:
            List of value bet opportunities
        """
        try:
            api = self._get_odds_api_io()
            if api and api.client:
                return api.get_value_bets(bookmaker, limit)
        except Exception as e:
            print(f"[DEBUG] Error fetching value bets: {e}")
        return []

    def fetch_arbitrage_opportunities(self, bookmakers: str = "bet365,pinnacle", limit: int = 10):
        """
        Fetch arbitrage opportunities from Odds-API.io
        
        Args:
            bookmakers: Comma-separated list of bookmakers
            limit: Maximum number of opportunities to return
        
        Returns:
            List of arbitrage opportunities
        """
        try:
            api = self._get_odds_api_io()
            if api and api.client:
                return api.get_arbitrage_opportunities(bookmakers, limit)
        except Exception as e:
            print(f"[DEBUG] Error fetching arbitrage opportunities: {e}")
        return []

    def _fetch_sportybet_direct(self, sport):
        """Fetch SportyBet Kenya events directly - Updated endpoints"""
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
        
        # Try different SportyBet API endpoints - remove the broken one
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
                print(f"[DEBUG] Trying SportyBet endpoint: {endpoint}")
                response = requests.get(
                    endpoint, 
                    headers=headers, 
                    params=params, 
                    timeout=self.live_fetch_timeout
                )
                response.raise_for_status()
                payload = response.json()
                
                if payload.get("bizCode") != 10000:
                    print(f"[DEBUG] SportyBet API returned bizCode: {payload.get('bizCode')}")
                    continue

                for tournament in payload.get("data") or []:
                    tournament_name = tournament.get("name") or ""
                    
                    # Skip SRL leagues
                    if any(keyword in tournament_name.lower() 
                           for keyword in ["srl", "simulated", "virtual"]):
                        continue
                    
                    for event in tournament.get("events") or []:
                        # Skip SRL events
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

    def _is_sample_data(self, matches):
        """Check if matches are sample/SRL data"""
        if not matches:
            return True
        
        for match in matches[:3]:
            league = match.get('league', '').lower()
            home = match.get('home_team', '').lower()
            away = match.get('away_team', '').lower()
            
            if any(keyword in league or keyword in home or keyword in away 
                   for keyword in ['srl', 'simulated', 'virtual', 'sample']):
                return True
        
        return False

    def _get_sample_data(self, site_id):
        """Return realistic sample data with many leagues and matches"""
        site_info = SUPPORTED_LIVE_SITES.get(site_id, {})
        site_name = site_info.get("name", site_id)
        now = datetime.now().isoformat()
        
        return [
            # English Premier League
            {
                "id": 1,
                "home_team": "Liverpool",
                "away_team": "Arsenal",
                "league": "English Premier League",
                "country": "England",
                "markets": {
                    "1X2": {"Home": 2.10, "Draw": 3.40, "Away": 3.20},
                    "Over/Under": {"Over 2.5": 1.80, "Under 2.5": 2.00},
                    "GG/NG": {"Yes": 1.70, "No": 2.10}
                },
                "site": site_id,
                "live": False,
                "sample": True,
                "last_updated": now,
                "note": f"Demo data for {site_name}"
            },
            {
                "id": 2,
                "home_team": "Manchester City",
                "away_team": "Chelsea",
                "league": "English Premier League",
                "country": "England",
                "markets": {
                    "1X2": {"Home": 1.65, "Draw": 3.80, "Away": 4.50},
                    "Over/Under": {"Over 2.5": 1.70, "Under 2.5": 2.10},
                    "GG/NG": {"Yes": 1.80, "No": 1.95}
                },
                "site": site_id,
                "live": False,
                "sample": True,
                "last_updated": now
            },
            {
                "id": 3,
                "home_team": "Manchester United",
                "away_team": "Tottenham",
                "league": "English Premier League",
                "country": "England",
                "markets": {
                    "1X2": {"Home": 2.20, "Draw": 3.50, "Away": 2.90},
                    "Over/Under": {"Over 2.5": 1.85, "Under 2.5": 1.95},
                    "GG/NG": {"Yes": 1.60, "No": 2.20}
                },
                "site": site_id,
                "live": False,
                "sample": True,
                "last_updated": now
            },
            # La Liga
            {
                "id": 4,
                "home_team": "Real Madrid",
                "away_team": "Atletico Madrid",
                "league": "La Liga",
                "country": "Spain",
                "markets": {
                    "1X2": {"Home": 1.85, "Draw": 3.60, "Away": 4.00},
                    "Over/Under": {"Over 2.5": 1.90, "Under 2.5": 1.90},
                    "GG/NG": {"Yes": 1.80, "No": 1.95}
                },
                "site": site_id,
                "live": False,
                "sample": True,
                "last_updated": now
            },
            {
                "id": 5,
                "home_team": "Barcelona",
                "away_team": "Real Sociedad",
                "league": "La Liga",
                "country": "Spain",
                "markets": {
                    "1X2": {"Home": 1.50, "Draw": 4.20, "Away": 5.50},
                    "Over/Under": {"Over 2.5": 1.75, "Under 2.5": 2.05},
                    "GG/NG": {"Yes": 1.70, "No": 2.10}
                },
                "site": site_id,
                "live": False,
                "sample": True,
                "last_updated": now
            },
            # Bundesliga
            {
                "id": 6,
                "home_team": "Bayern Munich",
                "away_team": "Borussia Dortmund",
                "league": "Bundesliga",
                "country": "Germany",
                "markets": {
                    "1X2": {"Home": 1.60, "Draw": 4.20, "Away": 4.80},
                    "Over/Under": {"Over 3.5": 1.85, "Under 3.5": 1.95},
                    "GG/NG": {"Yes": 1.55, "No": 2.35}
                },
                "site": site_id,
                "live": False,
                "sample": True,
                "last_updated": now
            },
            {
                "id": 7,
                "home_team": "RB Leipzig",
                "away_team": "Bayer Leverkusen",
                "league": "Bundesliga",
                "country": "Germany",
                "markets": {
                    "1X2": {"Home": 2.30, "Draw": 3.60, "Away": 2.70},
                    "Over/Under": {"Over 2.5": 1.80, "Under 2.5": 2.00},
                    "GG/NG": {"Yes": 1.65, "No": 2.15}
                },
                "site": site_id,
                "live": False,
                "sample": True,
                "last_updated": now
            },
            # Serie A
            {
                "id": 8,
                "home_team": "AC Milan",
                "away_team": "Inter Milan",
                "league": "Serie A",
                "country": "Italy",
                "markets": {
                    "1X2": {"Home": 2.60, "Draw": 3.30, "Away": 2.50},
                    "Over/Under": {"Over 2.5": 2.00, "Under 2.5": 1.80},
                    "GG/NG": {"Yes": 1.75, "No": 2.00}
                },
                "site": site_id,
                "live": False,
                "sample": True,
                "last_updated": now
            },
            {
                "id": 9,
                "home_team": "Juventus",
                "away_team": "Napoli",
                "league": "Serie A",
                "country": "Italy",
                "markets": {
                    "1X2": {"Home": 2.10, "Draw": 3.40, "Away": 3.20},
                    "Over/Under": {"Over 2.5": 1.90, "Under 2.5": 1.90},
                    "GG/NG": {"Yes": 1.80, "No": 1.95}
                },
                "site": site_id,
                "live": False,
                "sample": True,
                "last_updated": now
            },
            # Ligue 1
            {
                "id": 10,
                "home_team": "PSG",
                "away_team": "Marseille",
                "league": "Ligue 1",
                "country": "France",
                "markets": {
                    "1X2": {"Home": 1.45, "Draw": 4.50, "Away": 6.00},
                    "Over/Under": {"Over 2.5": 1.60, "Under 2.5": 2.25},
                    "GG/NG": {"Yes": 1.65, "No": 2.15}
                },
                "site": site_id,
                "live": False,
                "sample": True,
                "last_updated": now
            },
            {
                "id": 11,
                "home_team": "Lyon",
                "away_team": "Monaco",
                "league": "Ligue 1",
                "country": "France",
                "markets": {
                    "1X2": {"Home": 2.05, "Draw": 3.60, "Away": 3.20},
                    "Over/Under": {"Over 2.5": 1.85, "Under 2.5": 1.95},
                    "GG/NG": {"Yes": 1.70, "No": 2.05}
                },
                "site": site_id,
                "live": False,
                "sample": True,
                "last_updated": now
            }
        ]


# Global fetcher instance
_fetcher = None

def get_fetcher():
    global _fetcher
    if _fetcher is None:
        _fetcher = LiveOddsFetcher()
    return _fetcher