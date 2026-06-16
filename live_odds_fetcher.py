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

import requests
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

SUPPORTED_SPORTS = {
    "football": {"name": "Football", "icon": "FB", "live_feed": True},
    "basketball": {"name": "Basketball", "icon": "BB", "live_feed": True},
    "tennis": {"name": "Tennis", "icon": "TN", "live_feed": False},
    "volleyball": {"name": "Volleyball", "icon": "VB", "live_feed": True},
    "icehockey": {"name": "Ice Hockey", "icon": "IH", "live_feed": True},
    "darts": {"name": "Darts", "icon": "DT", "live_feed": True},
    "baseball": {"name": "Baseball", "icon": "BA", "live_feed": False},
    "american_football": {"name": "American Football", "icon": "AF", "live_feed": False},
    "cricket": {"name": "Cricket", "icon": "CR", "live_feed": False},
    "mma": {"name": "MMA", "icon": "MM", "live_feed": False},
    "badminton": {"name": "Badminton", "icon": "BD", "live_feed": False},
    "beach_volleyball": {"name": "Beach Volleyball", "icon": "BV", "live_feed": False},
    "futsal": {"name": "Futsal", "icon": "FS", "live_feed": False},
    "rugby": {"name": "Rugby", "icon": "RG", "live_feed": False},
    "snooker": {"name": "Snooker", "icon": "SN", "live_feed": False},
    "counter_strike": {"name": "Counter-Strike", "icon": "CS", "live_feed": False},
    "dota_2": {"name": "Dota 2", "icon": "D2", "live_feed": False},
    "league_of_legends": {"name": "League of Legends", "icon": "LL", "live_feed": False},
}

SPORTYBET_CURRENT_SPORT_IDS = {
    "football": "sr:sport:1",
    "basketball": "sr:sport:2",
    "tennis": "sr:sport:5",
    "volleyball": "sr:sport:23",
    "icehockey": "sr:sport:4",
    "darts": "sr:sport:22",
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
        # Increase timeout for Render's slower environment
        self.live_fetch_timeout = 15 if os.environ.get("RENDER") else 8  # seconds
        
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

    def get_supported_sports(self, site_id="sportybet"):
        """Return all visible sports categories, including unsupported future categories."""
        sports = []
        for key, sport in SUPPORTED_SPORTS.items():
            enabled = bool(sport.get("live_feed"))
            sports.append({
                "id": key,
                "name": sport["name"],
                "icon": sport["icon"],
                "enabled": enabled,
                "live_feed": enabled and API_AVAILABLE and LIVE_FEEDS_ENABLED,
                "stored_count": self._count_stored_matches(site_id, key) if enabled else 0
            })
        return sports
    
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
        
        if sport not in SUPPORTED_SPORTS or not SUPPORTED_SPORTS[sport].get("live_feed"):
            return []

        # ADD DEBUG LOGGING
        print(f"[DEBUG] LIVE_FEEDS_ENABLED: {LIVE_FEEDS_ENABLED}")
        print(f"[DEBUG] API_AVAILABLE: {API_AVAILABLE}")
        print(f"[DEBUG] site_id in API_INSTANCES: {site_id in API_INSTANCES}")
        print(f"[DEBUG] RENDER env: {os.environ.get('RENDER')}")
        
        if not LIVE_FEEDS_ENABLED or not API_AVAILABLE or site_id not in API_INSTANCES:
            print(f"[DEBUG] Falling back to stored/sample data for {site_id}")
            return self._get_fallback_data(site_id, sport)
        
        try:
            if site_id == "sportybet":
                current_matches = self._fetch_current_sportybet_odds(sport)
                if current_matches:
                    # Check if they're real or SRL
                    if self._is_sample_data(current_matches):
                        print("[WARNING] Matches contain SRL - these are sample/test data!")
                        # Try alternative method using OddsAfrica-API
                        api_instance = API_INSTANCES[site_id]
                        raw_data = self._run_with_timeout(api_instance.Get_games, sport)
                        if raw_data:
                            matches = self._parse_api_response(raw_data, site_id)
                            if matches and not self._is_sample_data(matches):
                                print(f"[DEBUG] Found {len(matches)} real matches from API")
                                self.cache[cache_key] = (time.time(), matches)
                                return matches
                    else:
                        print(f"[DEBUG] Found {len(current_matches)} real SportyBet matches")
                        self.cache[cache_key] = (time.time(), current_matches)
                        return current_matches

            # Try OddsAfrica-API for other sites or as fallback
            api_instance = API_INSTANCES[site_id]
            raw_data = self._run_with_timeout(api_instance.Get_games, sport)
            
            if not raw_data:
                stored_matches = self._get_stored_matches(site_id, sport)
                fallback_data = stored_matches or self._get_fallback_data(site_id, sport)
                self.cache[cache_key] = (time.time(), fallback_data)
                return fallback_data
            
            matches = self._parse_api_response(raw_data, site_id)
            if not matches:
                stored_matches = self._get_stored_matches(site_id, sport)
                fallback_data = stored_matches or self._get_fallback_data(site_id, sport)
                self.cache[cache_key] = (time.time(), fallback_data)
                return fallback_data
            
            # Cache results
            self.cache[cache_key] = (time.time(), matches)
            return matches
            
        except Exception as e:
            print(f"Error fetching from {site_id}: {e}")
            stored_matches = self._get_stored_matches(site_id, sport)
            fallback_data = stored_matches or self._get_fallback_data(site_id, sport)
            self.cache[cache_key] = (time.time(), fallback_data)
            return fallback_data

    def _fetch_current_sportybet_odds(self, sport):
        """Fetch SportyBet Kenya events - FIXED for real matches"""
        sport_id = SPORTYBET_CURRENT_SPORT_IDS.get(sport)
        if not sport_id:
            return []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": f"https://www.sportybet.com/ke/sport/{sport}/",
            "Clientid": "web",
            "Platform": "web",
            "Operid": "1",
            "Origin": "https://www.sportybet.com",
            "Sec-Fetch-Site": "same-origin",
        }
        
        # Use the correct endpoint for live matches
        endpoints = [
            "https://www.sportybet.com/api/ke/factsCenter/liveEvents",
            "https://www.sportybet.com/api/ke/factsCenter/liveOrPrematchEvents",
        ]
        
        params = {
            "sportId": sport_id, 
            "productId": 3,
            "isLive": "true",
            "marketType": "1X2,Over/Under,GG/NG"
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
                    print(f"[DEBUG] SportyBet API error: {payload.get('message')}")
                    continue

                # Process tournaments and events
                for tournament in payload.get("data") or []:
                    tournament_name = tournament.get("name") or ""
                    category_name = tournament.get("categoryName") or ""
                    
                    # Skip SRL leagues
                    if any(keyword in tournament_name.lower() or keyword in category_name.lower() 
                           for keyword in ["srl", "simulated", "virtual"]):
                        print(f"[DEBUG] Skipping SRL: {tournament_name}")
                        continue
                    
                    for event in tournament.get("events") or []:
                        # Skip SRL events
                        if "SRL" in event.get("homeTeamName", "") or "SRL" in event.get("awayTeamName", ""):
                            continue
                        
                        parsed = self._parse_current_sportybet_event(event, tournament_name, category_name)
                        if parsed:
                            events_by_id[parsed["id"]] = parsed
                            print(f"[DEBUG] Added real match: {parsed['home_team']} vs {parsed['away_team']}")
                            
            except Exception as e:
                print(f"[DEBUG] Error fetching from {endpoint}: {e}")
                continue

        matches = list(events_by_id.values())
        print(f"[DEBUG] Total real matches found: {len(matches)}")
        return matches[:50]

    def _parse_current_sportybet_event(self, event, tournament_name, category_name):
        structured_markets = {}

        for market in event.get("markets") or []:
            market_name = market.get("name") or market.get("desc") or ""
            outcomes = market.get("outcomes") or []
            active_outcomes = [
                outcome for outcome in outcomes
                if outcome.get("isActive", 1) == 1 and outcome.get("odds") not in (None, "")
            ]
            if not active_outcomes:
                continue

            if market.get("id") == "1" or market_name == "1X2":
                structured_markets["1X2"] = self._map_named_outcomes(active_outcomes, {
                    "Home": "Home",
                    "Draw": "Draw",
                    "Away": "Away",
                })
            elif "Over/Under" in market_name and "Over/Under" not in structured_markets:
                structured_markets["Over/Under"] = {
                    outcome.get("desc", f"Option {index + 1}"): self._safe_float(outcome.get("odds"))
                    for index, outcome in enumerate(active_outcomes[:2])
                }
            elif ("Both Teams to Score" in market_name or market_name == "GG/NG") and "GG/NG" not in structured_markets:
                structured_markets["GG/NG"] = self._map_named_outcomes(active_outcomes, {
                    "Yes": "Yes",
                    "No": "No",
                })
            elif "Double Chance" in market_name and "Double Chance" not in structured_markets:
                structured_markets["Double Chance"] = {
                    outcome.get("desc", f"Option {index + 1}"): self._safe_float(outcome.get("odds"))
                    for index, outcome in enumerate(active_outcomes[:3])
                }

        if not structured_markets:
            return None

        sport_info = event.get("sport") or {}
        category = sport_info.get("category") or {}
        tournament = category.get("tournament") or {}
        league_parts = [
            category.get("name") or category_name,
            tournament.get("name") or tournament_name,
        ]
        league = " - ".join(part for part in league_parts if part)
        match_status = event.get("matchStatus") or ""
        is_live = bool(event.get("status") == 1 or match_status not in {"", "Not start"})

        return {
            "id": event.get("eventId") or event.get("gameId") or abs(hash(str(event))) % 1000000,
            "home_team": event.get("homeTeamName") or "Home",
            "away_team": event.get("awayTeamName") or "Away",
            "league": league or tournament_name,
            "country": category.get("name") or category_name or "Kenya",
            "markets": structured_markets,
            "site": "sportybet",
            "live": is_live,
            "status": match_status,
            "source": "sportybet_current_api",
            "last_updated": datetime.now().isoformat(),
        }

    def _map_named_outcomes(self, outcomes, wanted):
        mapped = {}
        for outcome in outcomes:
            label = outcome.get("desc")
            if label in wanted:
                mapped[wanted[label]] = self._safe_float(outcome.get("odds"))
        return mapped

    def _safe_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return value

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

    def _count_stored_matches(self, site_id, sport):
        try:
            return len(self._get_stored_matches(site_id, sport))
        except Exception:
            return 0

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

    def _get_fallback_data(self, site_id, sport):
        if sport == "football":
            return self._get_sample_data(site_id)
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