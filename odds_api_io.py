"""
Odds-API.io Integration
Get your API key from: https://odds-api.io/
Provides real-time odds, value bet detection, and arbitrage opportunities
"""

import os
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
    """Wrapper for Odds-API.io with value bet detection"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('ODDS_API_IO_KEY', '')
        self.client = None
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
                # Some versions use a different init
                self.client = OddsAPIClient(self.api_key)
            
            if self.client:
                print("✅ Odds-API.io client initialized successfully")
            else:
                print("❌ Failed to initialize Odds-API.io client")
        except Exception as e:
            print(f"❌ Failed to initialize Odds-API.io client: {e}")
    
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
            # Try different API methods
            try:
                # Try get_live_events first
                response = self.client.get_live_events(sport=sport)
            except AttributeError:
                try:
                    # Try get_events
                    response = self.client.get_events(sport=sport, live=True)
                except AttributeError:
                    # Try get_odds
                    response = self.client.get_odds(sport=sport)
            
            # Parse response based on format
            if response:
                # Different response formats
                if isinstance(response, dict):
                    events = response.get('data', []) or response.get('events', []) or response.get('results', [])
                elif isinstance(response, list):
                    events = response
                else:
                    events = []
                
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
            else:
                print(f"[DEBUG] No response from Odds-API.io")
                return []
            
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
            # Try different methods
            try:
                if bookmaker:
                    response = self.client.get_value_bets(bookmaker=bookmaker)
                else:
                    response = self.client.get_value_bets()
            except AttributeError:
                # Fallback: get value bets from events
                events = self.get_live_events(limit=30)
                if events:
                    return self._calculate_value_bets(events, bookmaker, limit)
                return []
            
            if response:
                if isinstance(response, dict):
                    bets = response.get('data', []) or response.get('bets', []) or response.get('value_bets', [])
                elif isinstance(response, list):
                    bets = response
                else:
                    bets = []
                
                return self._standardize_value_bets(bets[:limit])
            return []
            
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
            # Try different methods
            try:
                response = self.client.get_arbitrage_bets(bookmakers=bookmakers)
            except AttributeError:
                # Fallback: calculate from events
                events = self.get_live_events(limit=30)
                if events:
                    return self._calculate_arbitrage(events, bookmakers, limit)
                return []
            
            if response:
                if isinstance(response, dict):
                    opportunities = response.get('data', []) or response.get('opportunities', [])
                elif isinstance(response, list):
                    opportunities = response
                else:
                    opportunities = []
                
                return self._standardize_arbitrage(opportunities[:limit])
            return []
            
        except Exception as e:
            print(f"❌ Error fetching arbitrage opportunities: {e}")
            return []
    
    def _standardize_event(self, event: Dict) -> Dict:
        """Standardize an event for your app's format"""
        try:
            # Extract team names
            home_team = event.get('home_team') or event.get('homeTeam') or event.get('home', 'Home')
            away_team = event.get('away_team') or event.get('awayTeam') or event.get('away', 'Away')
            
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
                            if '1x2' in market_name.lower() or 'match winner' in market_name.lower():
                                markets['1X2'] = outcomes
                            elif 'over/under' in market_name.lower() or 'total' in market_name.lower():
                                markets['Over/Under'] = outcomes
                            elif 'both teams to score' in market_name.lower() or 'gg' in market_name.lower():
                                markets['GG/NG'] = outcomes
                            elif 'double chance' in market_name.lower():
                                markets['Double Chance'] = outcomes
                            elif not markets:
                                markets[market_name] = outcomes
            
            elif isinstance(odds_data, dict):
                for market_name, outcomes in odds_data.items():
                    if isinstance(outcomes, dict):
                        markets[market_name] = outcomes
                    elif isinstance(outcomes, list):
                        for outcome in outcomes:
                            label = outcome.get('name', '')
                            price = outcome.get('price', 0)
                            if label and price > 0:
                                if market_name not in markets:
                                    markets[market_name] = {}
                                markets[market_name][label] = price
            
            if not markets:
                return None
            
            return {
                'id': event.get('id') or abs(hash(f"{home_team}_{away_team}")) % 1000000,
                'home_team': home_team,
                'away_team': away_team,
                'league': event.get('league') or event.get('competition') or 'Unknown League',
                'country': event.get('country') or '',
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
                    'value_edge': bet.get('value_edge', 0) or bet.get('edge', 0),
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
                    'arbitrage_percentage': opp.get('arbitrage_percentage', 0) or opp.get('arb_percentage', 0),
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
                    if odds > 0:
                        # Simple value calculation
                        implied_prob = 1 / odds
                        true_prob = implied_prob * 0.95  # Adjust for margin
                        edge = (true_prob * odds - 1) * 100
                        
                        if edge > 5:
                            value_bets.append({
                                'id': abs(hash(f"{event['home_team']}_{outcome}")) % 1000000,
                                'match': f"{event['home_team']} vs {event['away_team']}",
                                'home_team': event['home_team'],
                                'away_team': event['away_team'],
                                'league': event.get('league', 'Unknown'),
                                'market': market_name,
                                'outcome': outcome,
                                'bookmaker_odds': odds,
                                'fair_odds': 1 / true_prob,
                                'value_edge': round(edge, 1),
                                'confidence': min(90, 50 + edge),
                                'recommendation': '✅ Value bet detected' if edge > 10 else '📈 Moderate value',
                                'stake': round((edge / 100) * 10, 2),
                                'from_api': True,
                                'source': 'odds-api-io-calculated',
                                'last_updated': datetime.now().isoformat()
                            })
        return value_bets[:limit]
    
    def _calculate_arbitrage(self, events, bookmakers, limit=10):
        """Calculate arbitrage opportunities (fallback)"""
        # Simple arbitrage detection across bookmakers
        arb_opps = []
        for event in events:
            markets = event.get('markets', {})
            for market_name, outcomes in markets.items():
                if len(outcomes) >= 2:
                    # Check if any arbitrage exists
                    total_implied = sum(1/odds for odds in outcomes.values() if odds > 0)
                    if total_implied < 0.95:  # Arbitrage opportunity
                        arb_opps.append({
                            'id': abs(hash(f"{event['home_team']}_{market_name}_arb")) % 1000000,
                            'match': f"{event['home_team']} vs {event['away_team']}",
                            'home_team': event['home_team'],
                            'away_team': event['away_team'],
                            'league': event.get('league', 'Unknown'),
                            'market': market_name,
                            'arbitrage_percentage': round((1 - total_implied) * 100, 1),
                            'bookmakers': ['Multiple'],
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