"""
Free odds API using The Odds API
Get your API key from: https://the-odds-api.com/
"""

import requests
import os
from datetime import datetime

class OddsAPI:
    def __init__(self, api_key=None):
        # Use the provided API key or get from environment
        self.api_key = api_key or os.environ.get('ODDS_API_KEY', 'e98edf583797db76766c0942f078efdb')
        self.base_url = "https://api.the-odds-api.com/v4"
        
    def get_sports(self):
        """Get list of available sports"""
        if not self.api_key:
            return None
            
        try:
            url = f"{self.base_url}/sports"
            params = {'apiKey': self.api_key}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                sports = response.json()
                print(f"✅ Available sports: {len(sports)}")
                for sport in sports[:10]:
                    print(f"  - {sport.get('key')}: {sport.get('title')}")
                return sports
            else:
                print(f"❌ Error getting sports: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def fetch_matches(self, sport_key="soccer_epl", region="us"):
        """
        Fetch matches and odds using correct sport key
        
        Valid sport keys: soccer_epl, soccer_spain_la_liga, soccer_germany_bundesliga,
        soccer_italy_serie_a, soccer_france_ligue_one, soccer_uefa_champs_league,
        basketball_nba, americanfootball_nfl, icehockey_nhl, tennis_atp_wimbledon
        """
        if not self.api_key or self.api_key == 'e98edf583797db76766c0942f078efdb':
            print("⚠️ Using default API key. It may not work. Get your own from https://the-odds-api.com/")
            
        try:
            # Use the sport key directly
            valid_sports = [
                'soccer_epl', 'soccer_spain_la_liga', 'soccer_germany_bundesliga',
                'soccer_italy_serie_a', 'soccer_france_ligue_one', 'soccer_uefa_champs_league',
                'basketball_nba', 'americanfootball_nfl', 'icehockey_nhl', 'tennis_atp_wimbledon'
            ]
            
            if sport_key not in valid_sports:
                # Try to map common names
                sport_map = {
                    'soccer': 'soccer_epl',
                    'football': 'soccer_epl',
                    'epl': 'soccer_epl',
                    'premier league': 'soccer_epl',
                    'la liga': 'soccer_spain_la_liga',
                    'bundesliga': 'soccer_germany_bundesliga',
                    'serie a': 'soccer_italy_serie_a',
                    'ligue 1': 'soccer_france_ligue_one',
                    'champions league': 'soccer_uefa_champs_league',
                    'basketball': 'basketball_nba',
                    'nba': 'basketball_nba',
                    'tennis': 'tennis_atp_wimbledon',
                    'nfl': 'americanfootball_nfl',
                    'nhl': 'icehockey_nhl',
                }
                sport_key = sport_map.get(sport_key.lower(), 'soccer_epl')
            
            url = f"{self.base_url}/sports/{sport_key}/odds"
            params = {
                'apiKey': self.api_key,
                'regions': 'us,uk,eu,au',
                'markets': 'h2h,over_under',
                'oddsFormat': 'decimal'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if not data:
                    return []
                matches = self._parse_response(data, sport_key)
                return matches
            elif response.status_code == 422:
                print(f"❌ Sport '{sport_key}' not found in The Odds API")
                print("   Try one of these: soccer_epl, soccer_spain_la_liga, soccer_germany_bundesliga")
                return None
            elif response.status_code == 401:
                print("❌ Invalid API key. Get one from https://the-odds-api.com/")
                return None
            else:
                return None
            
        except Exception as e:
            print(f"❌ Error fetching odds: {e}")
            return None
    
    def _parse_response(self, data, sport_key):
        """Parse API response into your app's format"""
        matches = []
        
        league_map = {
            'soccer_epl': 'English Premier League',
            'soccer_spain_la_liga': 'La Liga',
            'soccer_germany_bundesliga': 'Bundesliga',
            'soccer_italy_serie_a': 'Serie A',
            'soccer_france_ligue_one': 'Ligue 1',
            'soccer_uefa_champs_league': 'UEFA Champions League',
            'basketball_nba': 'NBA',
            'americanfootball_nfl': 'NFL',
            'icehockey_nhl': 'NHL',
            'tennis_atp_wimbledon': 'Tennis',
        }
        
        league_name = league_map.get(sport_key, sport_key.replace('_', ' ').title())
        
        for game in data[:30]:
            home = game.get('home_team', 'Home')
            away = game.get('away_team', 'Away')
            
            if not home or not away or home == 'Home' or away == 'Away':
                continue
                
            markets = {}
            
            # Get 1X2 odds
            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market.get('key') == 'h2h':
                        h2h = {}
                        for outcome in market.get('outcomes', []):
                            name = outcome.get('name', '')
                            price = outcome.get('price', 0)
                            if name and price and price > 0:
                                h2h[name] = price
                        if h2h:
                            markets['1X2'] = h2h
                        break
                if markets:
                    break
            
            # Get Over/Under odds
            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    if market.get('key') == 'over_under' and 'Over/Under' not in markets:
                        ou = {}
                        for outcome in market.get('outcomes', []):
                            name = outcome.get('description', outcome.get('name', ''))
                            price = outcome.get('price', 0)
                            if name and price and price > 0:
                                ou[name] = price
                        if ou:
                            markets['Over/Under'] = ou
                        break
                if 'Over/Under' in markets:
                    break
            
            if markets.get('1X2'):
                matches.append({
                    'id': abs(hash(f"{home}_{away}_{league_name}")) % 1000000,
                    'home_team': home,
                    'away_team': away,
                    'league': league_name,
                    'country': game.get('sport_title', league_name),
                    'markets': markets,
                    'site': 'the_odds_api',
                    'live': False,
                    'from_api': True,
                    'last_updated': datetime.now().isoformat()
                })
        
        return matches


def test_api():
    """Test if the API is working"""
    api = OddsAPI()
    
    print("\n🔍 Testing API connection...")
    
    # Try each sport key
    sports_to_try = [
        'soccer_epl',
        'soccer_spain_la_liga', 
        'soccer_germany_bundesliga',
        'soccer_italy_serie_a',
        'basketball_nba'
    ]
    
    total_matches = 0
    for sport_key in sports_to_try:
        print(f"\n📊 Trying {sport_key}...")
        matches = api.fetch_matches(sport_key)
        if matches and len(matches) > 0:
            print(f"✅ Found {len(matches)} matches!")
            total_matches += len(matches)
            if total_matches >= 5:
                print("\n📋 Sample matches:")
                for i, match in enumerate(matches[:3]):
                    print(f"  {i+1}. {match['home_team']} vs {match['away_team']}")
                    print(f"     League: {match['league']}")
                    if match['markets'].get('1X2'):
                        print(f"     Odds: {match['markets']['1X2']}")
                return True
        else:
            print(f"❌ No matches found for {sport_key}")
    
    if total_matches == 0:
        print("\n❌ No matches found for any sport.")
        print("\n💡 Your API key might be invalid or expired.")
        print("   Get a new free key from: https://the-odds-api.com/")
        return False
    
    return True


if __name__ == "__main__":
    test_api()