"""
Odds-API.io Integration
Get your API key from: https://odds-api.io/
Provides real-time odds, value bet detection, and arbitrage opportunities
"""

import os
import requests
from datetime import datetime
from typing import List, Dict, Optional

# Try different import paths for the SDK
try:
    from odds_api_io import OddsAPIClient
    SDK_AVAILABLE = True
    print("✅ Odds-API.io SDK loaded successfully")
except ImportError:
    try:
        from odds_api import OddsAPIClient
        SDK_AVAILABLE = True
        print("✅ Odds-API.io SDK loaded successfully (alternate import)")
    except ImportError:
        SDK_AVAILABLE = False
        print("⚠️ Odds-API.io SDK not installed. Run: pip install odds-api-io")

class OddsAPIIO:
    """
    Wrapper for Odds-API.io with real odds, value bet detection, and arbitrage
    API Key: Get from https://odds-api.io/
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('ODDS_API_IO_KEY', '')
        self.client = None
        self.base_url = "https://api.odds-api.io/v1"
        self._init_client()
        
    def _init_client(self):
        """Initialize the Odds-API.io client"""
        if not SDK_AVAILABLE:
            print("❌ Odds-API.io SDK not available")
            return
            
        if not self.api_key:
            print("⚠️ No Odds-API.io API key found. Get one from https://odds-api.io/")
            return
            
        try:
            # Try different initialization methods
            try:
                self.client = OddsAPIClient(api_key=self.api_key)
            except TypeError:
                try:
                    self.client = OddsAPIClient(self.api_key)
                except Exception:
                    # Fallback to direct REST API
                    self.client = self._create_rest_client()
            
            if self.client:
                print("✅ Odds-API.io client initialized successfully")
            else:
                print("❌ Failed to initialize Odds-API.io client")
        except Exception as e:
            print(f"❌ Failed to initialize Odds-API.io client: {e}")
            # Fallback to REST API
            self.client = self._create_rest_client()
    
    def _create_rest_client(self):
        """Create a REST-based client as fallback"""
        return {
            'type': 'rest',
            'api_key': self.api_key,
            'base_url': self.base_url
        }
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make a REST API request (fallback method)"""
        if not self.api_key:
            return None
            
        url = f"{self.base_url}/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                print("❌ Invalid Odds-API.io API key")
                return None
            elif response.status_code == 429:
                print("⚠️ Odds-API.io rate limit exceeded")
                return None
            else:
                print(f"❌ Odds-API.io error: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Odds-API.io request failed: {e}")
            return None
    
    def get_live_events(self, sport: str = "soccer", limit: int = 30) -> List[Dict]:
        """
        Get live events with odds from Odds-API.io
        
        Args:
            sport: Sport name (soccer, basketball, tennis, etc.)
            limit: Maximum number of events to return
        
        Returns:
            List of events with odds in a standardized format
        """
        if not self.client:
            print("❌ Odds-API.io client not initialized")
            return []
            
        try:
            # Map sport names to Odds-API.io format
            sport_map = {
                'football': 'soccer',
                'soccer': 'soccer',
                'basketball': 'basketball',
                'tennis': 'tennis',
                'icehockey': 'ice_hockey',
                'baseball': 'baseball',
                'volleyball': 'volleyball',
                'darts': 'darts',
            }
            api_sport = sport_map.get(sport.lower(), 'soccer')
            
            events = []
            
            # Try SDK method first
            if hasattr(self.client, 'get_live_events'):
                try:
                    response = self.client.get_live_events(sport=api_sport)
                    if response:
                        events = response.get('data', []) or response.get('events', [])
                except Exception as e:
                    print(f"[DEBUG] SDK get_live_events failed: {e}")
            
            # Fallback: Try get_events with live filter
            if not events and hasattr(self.client, 'get_events'):
                try:
                    response = self.client.get_events(sport=api_sport, live=True)
                    if response:
                        events = response.get('data', []) or response.get('events', [])
                except Exception as e:
                    print(f"[DEBUG] SDK get_events failed: {e}")
            
            # Fallback: Try get_odds
            if not events and hasattr(self.client, 'get_odds'):
                try:
                    response = self.client.get_odds(sport=api_sport)
                    if response:
                        events = response.get('data', []) or response.get('events', [])
                except Exception as e:
                    print(f"[DEBUG] SDK get_odds failed: {e}")
            
            # Final fallback: REST API
            if not events:
                print("[DEBUG] Trying REST API fallback...")
                params = {'sport': api_sport, 'limit': limit}
                response = self._make_request('events', params)
                if response:
                    events = response.get('data', []) or response.get('events', [])
            
            if not events:
                print(f"[DEBUG] No events found for {sport}")
                return []
            
            # Standardize the events
            standardized = []
            for event in events[:limit]:
                standardized_event = self._standardize_event(event)
                if standardized_event:
                    standardized.append(standardized_event)
            
            print(f"[DEBUG] Found {len(standardized)} events from Odds-API.io")
            return standardized
            
        except Exception as e:
            print(f"❌ Error fetching live events: {e}")
            return []
    
    def get_value_bets(self, bookmaker: str = None, limit: int = 20) -> List[Dict]:
        """
        Get value bet recommendations from Odds-API.io
        """
        if not self.client:
            return []
            
        try:
            bets = []
            
            # Try SDK method first
            if hasattr(self.client, 'get_value_bets'):
                try:
                    params = {'bookmaker': bookmaker} if bookmaker else {}
                    response = self.client.get_value_bets(**params)
                    if response:
                        bets = response.get('data', []) or response.get('bets', [])
                except Exception as e:
                    print(f"[DEBUG] SDK get_value_bets failed: {e}")
            
            # Fallback: Try get_arbitrage_bets with value flag
            if not bets and hasattr(self.client, 'get_arbitrage_bets'):
                try:
                    params = {'bookmaker': bookmaker} if bookmaker else {}
                    response = self.client.get_arbitrage_bets(**params)
                    if response:
                        all_bets = response.get('data', []) or response.get('bets', [])
                        # Filter for value bets (positive edge)
                        bets = [b for b in all_bets if b.get('edge', 0) > 0]
                except Exception as e:
                    print(f"[DEBUG] SDK get_arbitrage_bets failed: {e}")
            
            # Final fallback: REST API
            if not bets:
                print("[DEBUG] Trying REST API for value bets...")
                params = {'bookmaker': bookmaker, 'limit': limit} if bookmaker else {'limit': limit}
                response = self._make_request('value-bets', params)
                if response:
                    bets = response.get('data', []) or response.get('bets', [])
            
            if not bets:
                # Calculate value bets from events as fallback
                events = self.get_live_events(limit=30)
                if events:
                    bets = self._calculate_value_bets(events, bookmaker, limit)
                else:
                    return []
            
            return self._standardize_value_bets(bets[:limit])
            
        except Exception as e:
            print(f"❌ Error fetching value bets: {e}")
            return []
    
    def get_arbitrage_opportunities(self, bookmakers: str = "bet365,pinnacle", limit: int = 10) -> List[Dict]:
        """
        Get arbitrage opportunities from Odds-API.io
        """
        if not self.client:
            return []
            
        try:
            opportunities = []
            
            # Try SDK method first
            if hasattr(self.client, 'get_arbitrage_bets'):
                try:
                    response = self.client.get_arbitrage_bets(bookmakers=bookmakers)
                    if response:
                        opportunities = response.get('data', []) or response.get('opportunities', [])
                except Exception as e:
                    print(f"[DEBUG] SDK get_arbitrage_bets failed: {e}")
            
            # Fallback: REST API
            if not opportunities:
                print("[DEBUG] Trying REST API for arbitrage...")
                params = {'bookmakers': bookmakers, 'limit': limit}
                response = self._make_request('arbitrage', params)
                if response:
                    opportunities = response.get('data', []) or response.get('opportunities', [])
            
            if not opportunities:
                # Calculate arbitrage from events as fallback
                events = self.get_live_events(limit=30)
                if events:
                    opportunities = self._calculate_arbitrage(events, bookmakers, limit)
                else:
                    return []
            
            return self._standardize_arbitrage(opportunities[:limit])
            
        except Exception as e:
            print(f"❌ Error fetching arbitrage opportunities: {e}")
            return []
    
    def _standardize_event(self, event: Dict) -> Dict:
        """Standardize an event for your app's format"""
        try:
            # Extract team names
            home_team = (
                event.get('home_team') or 
                event.get('homeTeam') or 
                event.get('home', 'Home')
            )
            away_team = (
                event.get('away_team') or 
                event.get('awayTeam') or 
                event.get('away', 'Away')
            )
            
            # Skip if no valid team names
            if home_team == 'Home' or away_team == 'Away' or not home_team or not away_team:
                return None
            
            # Extract markets
            markets = {}
            
            # Try different market formats
            odds_data = event.get('odds') or event.get('bookmakers') or event.get('markets') or {}
            
            if isinstance(odds_data, list):
                for bookmaker in odds_data:
                    for market in bookmaker.get('markets', []):
                        market_name = market.get('name') or market.get('key', '1X2')
                        outcomes = {}
                        for outcome in market.get('outcomes', []):
                            label = outcome.get('name') or outcome.get('label', '')
                            price = outcome.get('price') or outcome.get('odds', 0)
                            if label and price > 0:
                                outcomes[label] = price
                        
                        if outcomes:
                            market_key = self._normalize_market_name(market_name)
                            if market_key not in markets:
                                markets[market_key] = outcomes
            
            elif isinstance(odds_data, dict):
                for market_name, outcomes in odds_data.items():
                    if isinstance(outcomes, dict):
                        market_key = self._normalize_market_name(market_name)
                        markets[market_key] = outcomes
                    elif isinstance(outcomes, list):
                        for outcome in outcomes:
                            label = outcome.get('name', '')
                            price = outcome.get('price', 0)
                            if label and price > 0:
                                market_key = self._normalize_market_name(market_name)
                                if market_key not in markets:
                                    markets[market_key] = {}
                                markets[market_key][label] = price
            
            # If no markets found, return None
            if not markets or not markets.get('1X2'):
                return None
            
            return {
                'id': event.get('id') or abs(hash(f"{home_team}_{away_team}")) % 1000000,
                'home_team': home_team,
                'away_team': away_team,
                'league': event.get('league') or event.get('competition') or 'Unknown League',
                'country': event.get('country') or event.get('region') or '',
                'markets': markets,
                'site': 'odds-api-io',
                'live': event.get('live', False) or event.get('in_play', False),
                'start_time': event.get('commence_time') or event.get('start_time'),
                'from_api': True,
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"[DEBUG] Error standardizing event: {e}")
            return None
    
    def _normalize_market_name(self, market_name: str) -> str:
        """Normalize market names to app format"""
        market_lower = market_name.lower()
        if '1x2' in market_lower or 'moneyline' in market_lower or 'match winner' in market_lower:
            return '1X2'
        elif 'over/under' in market_lower or 'total' in market_lower or 'ou' in market_lower:
            return 'Over/Under'
        elif 'both teams to score' in market_lower or 'gg' in market_lower or 'btts' in market_lower:
            return 'GG/NG'
        elif 'double chance' in market_lower:
            return 'Double Chance'
        elif 'handicap' in market_lower or 'spread' in market_lower:
            return 'Handicap'
        else:
            return market_name
    
    def _standardize_value_bets(self, bets: List[Dict]) -> List[Dict]:
        """Standardize value bets"""
        standardized = []
        for bet in bets[:20]:
            try:
                standardized.append({
                    'id': bet.get('id', abs(hash(str(bet))) % 1000000),
                    'match': bet.get('event', {}).get('name', 'Unknown Match'),
                    'home_team': bet.get('event', {}).get('home_team', 'Home'),
                    'away_team': bet.get('event', {}).get('away_team', 'Away'),
                    'league': bet.get('event', {}).get('league', 'Unknown'),
                    'market': bet.get('market', '1X2'),
                    'outcome': bet.get('outcome', ''),
                    'bookmaker_odds': bet.get('bookmaker_odds', 0),
                    'fair_odds': bet.get('fair_odds', 0),
                    'value_edge': round(bet.get('value_edge', 0) or bet.get('edge', 0), 1),
                    'confidence': bet.get('confidence', 50),
                    'recommendation': bet.get('recommendation', ''),
                    'stake': bet.get('stake', 0),
                    'from_api': True,
                    'source': 'odds-api-io',
                    'last_updated': datetime.now().isoformat()
                })
            except Exception as e:
                print(f"[DEBUG] Error standardizing value bet: {e}")
        return standardized
    
    def _standardize_arbitrage(self, opportunities: List[Dict]) -> List[Dict]:
        """Standardize arbitrage opportunities"""
        standardized = []
        for opp in opportunities[:10]:
            try:
                standardized.append({
                    'id': opp.get('id', abs(hash(str(opp))) % 1000000),
                    'match': opp.get('event', {}).get('name', 'Unknown'),
                    'home_team': opp.get('event', {}).get('home_team', 'Home'),
                    'away_team': opp.get('event', {}).get('away_team', 'Away'),
                    'league': opp.get('event', {}).get('league', 'Unknown'),
                    'market': opp.get('market', '1X2'),
                    'arbitrage_percentage': round(opp.get('arbitrage_percentage', 0) or opp.get('arb_percentage', 0), 2),
                    'bookmakers': opp.get('bookmakers', []),
                    'outcomes': opp.get('outcomes', []),
                    'total_stake': opp.get('total_stake', 0),
                    'guaranteed_return': opp.get('guaranteed_return', 0),
                    'from_api': True,
                    'source': 'odds-api-io',
                    'last_updated': datetime.now().isoformat()
                })
            except Exception as e:
                print(f"[DEBUG] Error standardizing arbitrage: {e}")
        return standardized
    
    def _calculate_value_bets(self, events, bookmaker=None, limit=20):
        """Calculate value bets from events (fallback)"""
        value_bets = []
        for event in events:
            markets = event.get('markets', {})
            for market_name, outcomes in markets.items():
                for outcome, odds in outcomes.items():
                    if odds > 0 and isinstance(odds, (int, float)):
                        # Simple value calculation with margin adjustment
                        implied_prob = 1 / odds
                        # Assume 5% bookmaker margin
                        true_prob = implied_prob * 0.95
                        edge = (true_prob * odds - 1) * 100
                        
                        if edge > 3:  # Only include positive value
                            value_bets.append({
                                'id': abs(hash(f"{event['home_team']}_{outcome}_{market_name}")) % 1000000,
                                'match': f"{event['home_team']} vs {event['away_team']}",
                                'home_team': event['home_team'],
                                'away_team': event['away_team'],
                                'league': event.get('league', 'Unknown'),
                                'market': market_name,
                                'outcome': outcome,
                                'bookmaker_odds': odds,
                                'fair_odds': round(1 / true_prob, 2),
                                'value_edge': round(edge, 1),
                                'confidence': min(90, 50 + edge),
                                'recommendation': '🔥 Strong Value' if edge > 10 else '✅ Good Value',
                                'stake': round((edge / 100) * 10, 2),
                                'from_api': True,
                                'source': 'odds-api-io-calculated',
                                'last_updated': datetime.now().isoformat()
                            })
        value_bets.sort(key=lambda x: x['value_edge'], reverse=True)
        return value_bets[:limit]
    
    def _calculate_arbitrage(self, events, bookmakers, limit=10):
        """Calculate arbitrage opportunities (fallback)"""
        arb_opps = []
        for event in events:
            markets = event.get('markets', {})
            for market_name, outcomes in markets.items():
                if len(outcomes) >= 2:
                    # Check if arbitrage exists
                    total_implied = sum(1/odds for odds in outcomes.values() if isinstance(odds, (int, float)) and odds > 0)
                    if total_implied < 0.98:  # Arbitrage opportunity
                        arb_opps.append({
                            'id': abs(hash(f"{event['home_team']}_{market_name}_arb")) % 1000000,
                            'match': f"{event['home_team']} vs {event['away_team']}",
                            'home_team': event['home_team'],
                            'away_team': event['away_team'],
                            'league': event.get('league', 'Unknown'),
                            'market': market_name,
                            'arbitrage_percentage': round((1 - total_implied) * 100, 1),
                            'bookmakers': ['Multiple Bookmakers'],
                            'outcomes': list(outcomes.keys()),
                            'total_stake': 100,
                            'guaranteed_return': round(100 / total_implied, 2),
                            'from_api': True,
                            'source': 'odds-api-io-calculated',
                            'last_updated': datetime.now().isoformat()
                        })
        return arb_opps[:limit]


def test_odds_api_io():
    """Test the Odds-API.io integration"""
    api = OddsAPIIO()
    
    if not api.client:
        print("\n❌ Odds-API.io client not available. Make sure:")
        print("  1. Install: pip install odds-api-io")
        print("  2. Set ODDS_API_IO_KEY in .env or pass it directly")
        return False
    
    print("\n🔍 Testing Odds-API.io...")
    
    # Test 1: Get live events
    print("\n📊 Fetching live events...")
    events = api.get_live_events('soccer', limit=5)
    if events:
        print(f"✅ Found {len(events)} live events")
        for event in events[:3]:
            print(f"  - {event['home_team']} vs {event['away_team']}")
            if event.get('markets', {}).get('1X2'):
                odds = event['markets']['1X2']
                print(f"    Odds: Home={odds.get('Home', 'N/A')}, Draw={odds.get('Draw', 'N/A')}, Away={odds.get('Away', 'N/A')}")
    else:
        print("❌ No live events found")
    
    # Test 2: Get value bets
    print("\n💎 Fetching value bets...")
    value_bets = api.get_value_bets(limit=5)
    if value_bets:
        print(f"✅ Found {len(value_bets)} value bets")
        for bet in value_bets[:3]:
            print(f"  - {bet['match']}: {bet['outcome']} @ {bet['bookmaker_odds']} (Edge: {bet['value_edge']}%)")
    else:
        print("❌ No value bets found")
    
    return True


if __name__ == "__main__":
    test_odds_api_io()