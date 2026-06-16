"""
The Odds API Integration
Get your API key from: https://the-odds-api.com/
"""

import os
import requests
from datetime import datetime
from typing import List, Dict, Optional

class OddsAPIIO:
    """The Odds API wrapper - tries multiple leagues"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('ODDS_API_IO_KEY', '')
        self.base_url = "https://api.the-odds-api.com/v4"
        
        if not self.api_key:
            print("⚠️ No API key found. Get one from https://the-odds-api.com/")
            self.client = None
        else:
            self.client = True
            print(f"✅ The Odds API client initialized")
    
    def get_live_events(self, sport: str = "football", limit: int = 30) -> List[Dict]:
        """Get events from The Odds API - tries multiple leagues"""
        if not self.client or not self.api_key:
            return []
            
        try:
            # All available soccer leagues
            soccer_leagues = [
                'soccer_australia_aleague',
                'soccer_australia_npl_queensland',
                'soccer_australia_npl_victoria',
                'soccer_australia_npl_nsw',
                'soccer_australia_npl_south',
                'soccer_epl',
                'soccer_spain_la_liga',
                'soccer_germany_bundesliga',
                'soccer_italy_serie_a',
                'soccer_france_ligue_one',
                'soccer_uefa_champs_league',
                'soccer_usa_mls',
                'soccer_japan_j1_league',
                'soccer_south_korea_k_league1',
                'soccer_brazil_campeonato',
                'soccer_netherlands_eredivisie',
                'soccer_portugal_primeira_liga',
                'soccer_belgium_pro_league',
                'soccer_turkey_super_league',
                'soccer_sweden_allsvenskan',
                'soccer_norway_eliteserien',
                'soccer_denmark_superliga',
                'soccer_switzerland_super_league',
                'soccer_austria_bundesliga',
            ]
            
            basketball_leagues = [
                'basketball_nba',
                'basketball_euroleague',
                'basketball_spain_acb',
                'basketball_italy_serie_a',
                'basketball_germany_bbl',
            ]
            
            if sport.lower() in ['basketball']:
                leagues = basketball_leagues
            else:
                leagues = soccer_leagues
            
            all_events = []
            
            for league in leagues[:15]:  # Try first 15 leagues
                print(f"[DEBUG] Trying: {league}")
                events = self._fetch_sport(league)
                if events:
                    all_events.extend(events)
                    print(f"[DEBUG] Found {len(events)} events in {league}")
                    if len(all_events) >= limit:
                        break
            
            print(f"[DEBUG] Total events found: {len(all_events)}")
            return all_events[:limit]
            
        except Exception as e:
            print(f"❌ Error fetching events: {e}")
            return []
    
    def _fetch_sport(self, sport_key: str) -> List[Dict]:
        """Fetch a specific sport league"""
        try:
            url = f"{self.base_url}/sports/{sport_key}/odds"
            params = {
                'apiKey': self.api_key,
                'regions': 'eu,uk,us,au',
                'markets': 'h2h,over_under',
                'oddsFormat': 'decimal'
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if not data:
                    return []
                events = []
                for game in data:
                    standardized = self._standardize_event(game, sport_key)
                    if standardized:
                        events.append(standardized)
                return events
            elif response.status_code == 401:
                print("❌ Invalid API key")
                return []
            elif response.status_code == 429:
                print("⚠️ Rate limit exceeded")
                return []
            else:
                return []
                
        except Exception as e:
            print(f"[DEBUG] Error: {e}")
            return []
    
    def _standardize_event(self, game: Dict, sport_key: str) -> Optional[Dict]:
        """Convert API response to your app's format"""
        try:
            home_team = game.get('home_team', 'Home')
            away_team = game.get('away_team', 'Away')
            
            if home_team == 'Home' or away_team == 'Away':
                return None
            
            # Get league name
            league_name = sport_key.replace('_', ' ').title()
            if 'Epl' in league_name:
                league_name = 'English Premier League'
            elif 'La Liga' in league_name:
                league_name = 'La Liga'
            elif 'Bundesliga' in league_name:
                league_name = 'Bundesliga'
            
            markets = {}
            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market.get('key') == 'h2h':
                        h2h = {}
                        for outcome in market.get('outcomes', []):
                            name = outcome.get('name', '')
                            price = outcome.get('price', 0)
                            if name and price > 0:
                                h2h[name] = price
                        if h2h:
                            markets['1X2'] = h2h
                    elif market.get('key') == 'over_under' and 'Over/Under' not in markets:
                        ou = {}
                        for outcome in market.get('outcomes', []):
                            name = outcome.get('description', outcome.get('name', ''))
                            price = outcome.get('price', 0)
                            if name and price > 0:
                                ou[name] = price
                        if ou:
                            markets['Over/Under'] = ou
            
            if not markets or not markets.get('1X2'):
                return None
            
            return {
                'id': abs(hash(f"{home_team}_{away_team}_{league_name}")) % 1000000,
                'home_team': home_team,
                'away_team': away_team,
                'league': league_name,
                'country': game.get('sport_title', ''),
                'markets': markets,
                'site': 'the-odds-api',
                'live': False,
                'from_api': True,
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            return None


def test_odds_api_io():
    """Test the API integration"""
    api = OddsAPIIO()
    
    if not api.client:
        print("\n❌ API client not available. Set ODDS_API_IO_KEY in .env")
        return False
    
    print("\n🔍 Testing The Odds API...")
    events = api.get_live_events('football', limit=10)
    
    if events:
        print(f"✅ Found {len(events)} events")
        for event in events[:5]:
            print(f"  - {event['home_team']} vs {event['away_team']}")
            print(f"    League: {event['league']}")
            if event.get('markets', {}).get('1X2'):
                print(f"    Odds: {event['markets']['1X2']}")
        return True
    else:
        print("❌ No events found")
        return False


if __name__ == "__main__":
    test_odds_api_io()