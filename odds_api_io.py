"""
The Odds API Integration
Get your API key from: https://the-odds-api.com/
"""

import os
import requests
from datetime import datetime
from typing import List, Dict, Optional

class OddsAPIIO:
    """The Odds API wrapper"""
    
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
        """Get events from The Odds API"""
        if not self.client or not self.api_key:
            return []
            
        try:
            # Map sports to The Odds API keys
            sport_map = {
                'football': ['soccer_epl', 'soccer_spain_la_liga', 'soccer_germany_bundesliga'],
                'basketball': ['basketball_nba'],
                'tennis': ['tennis_atp_wimbledon'],
                'icehockey': ['icehockey_nhl'],
            }
            
            sport_keys = sport_map.get(sport.lower(), ['soccer_epl'])
            all_events = []
            
            for sport_key in sport_keys:
                url = f"{self.base_url}/sports/{sport_key}/odds"
                params = {
                    'apiKey': self.api_key,
                    'regions': 'us,uk,eu,au',
                    'markets': 'h2h,over_under',
                    'oddsFormat': 'decimal'
                }
                
                response = requests.get(url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    for game in data:
                        standardized = self._standardize_event(game, sport_key)
                        if standardized:
                            all_events.append(standardized)
                        if len(all_events) >= limit:
                            break
                elif response.status_code == 401:
                    print("❌ Invalid API key. Get one from https://the-odds-api.com/")
                    break
                elif response.status_code == 429:
                    print("⚠️ Rate limit exceeded. Try again later.")
                    break
            
            if all_events:
                print(f"[DEBUG] Found {len(all_events)} events from The Odds API")
            return all_events[:limit]
            
        except Exception as e:
            print(f"❌ Error fetching events: {e}")
            return []
    
    def _standardize_event(self, game: Dict, sport_key: str) -> Optional[Dict]:
        """Convert API response to your app's format"""
        try:
            home_team = game.get('home_team', 'Home')
            away_team = game.get('away_team', 'Away')
            
            if home_team == 'Home' or away_team == 'Away':
                return None
            
            league_map = {
                'soccer_epl': 'English Premier League',
                'soccer_spain_la_liga': 'La Liga',
                'soccer_germany_bundesliga': 'Bundesliga',
                'basketball_nba': 'NBA',
            }
            league_name = league_map.get(sport_key, sport_key.replace('_', ' ').title())
            
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
                'country': '',
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
    events = api.get_live_events('football', limit=5)
    
    if events:
        print(f"✅ Found {len(events)} events")
        for event in events[:3]:
            print(f"  - {event['home_team']} vs {event['away_team']}")
            if event.get('markets', {}).get('1X2'):
                print(f"    Odds: {event['markets']['1X2']}")
        return True
    else:
        print("❌ No events found - check your API key")
        return False


if __name__ == "__main__":
    test_odds_api_io()