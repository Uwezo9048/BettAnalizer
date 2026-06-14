"""
AI Sports Betting Analysis Engine
Calculates value bets, expected value, and Kelly stakes
"""

from collections import defaultdict

class BettingAI:
    """AI that analyzes betting markets and selects the best value bets"""
    
    def __init__(self):
        self.team_stats = {}
        self.market_history = defaultdict(list)
        
    def calculate_implied_probability(self, odds):
        """Convert decimal odds to implied probability"""
        if odds and odds > 0:
            return 1.0 / odds
        return 0
    
    def calculate_true_probability(self, odds, market_type="1X2"):
        """Calculate true probability using statistical models"""
        implied_prob = self.calculate_implied_probability(odds)
        
        # Adjust for bookmaker margin based on odds range
        if odds < 1.5:
            margin_adj = 0.92
        elif odds < 2.5:
            margin_adj = 0.94
        elif odds < 4.0:
            margin_adj = 0.96
        else:
            margin_adj = 0.98
        
        # Market-specific adjustments
        market_adjustments = {
            "1X2": 1.02,
            "Over/Under": 0.97,
            "GG/NG": 0.96,
            "Double Chance": 0.98,
            "Handicap": 0.99
        }
        
        market_adj = market_adjustments.get(market_type, 0.95)
        true_prob = implied_prob * margin_adj * market_adj
        
        return min(0.95, max(0.01, true_prob))
    
    def calculate_value_score(self, odds, true_probability):
        """Calculate expected value (EV) for a bet"""
        if odds <= 0 or true_probability <= 0:
            return 0
        return (true_probability * odds) - 1
    
    def calculate_kelly_stake(self, odds, true_probability, bankroll=1000, kelly_fraction=0.25):
        """Calculate optimal stake using Kelly Criterion"""
        if odds <= 1 or true_probability <= 0:
            return 0
        
        b = odds - 1
        p = true_probability
        q = 1 - p
        
        if b <= 0:
            return 0
        
        kelly_pct = (p * b - q) / b
        stake_pct = max(0, kelly_pct * kelly_fraction)
        stake_pct = min(stake_pct, 0.05)  # Cap at 5% of bankroll
        
        return stake_pct * bankroll
    
    def analyze_match(self, match_data):
        """Analyze all markets for a match and return AI-selected best bets"""
        results = []
        home_team = match_data.get('home_team', 'Home')
        away_team = match_data.get('away_team', 'Away')
        
        markets = match_data.get('markets', {})
        
        for market_name, outcomes in markets.items():
            if not isinstance(outcomes, dict):
                continue
                
            market_type = self._detect_market_type(market_name)
            
            for outcome, odds in outcomes.items():
                if not odds or odds <= 0:
                    continue
                
                true_prob = self.calculate_true_probability(odds, market_type)
                value_score = self.calculate_value_score(odds, true_prob)
                value_pct = value_score * 100
                
                confidence = self._get_confidence(value_pct, odds)
                stake = self.calculate_kelly_stake(odds, true_prob) if value_pct > 0 else 0
                
                results.append({
                    'market': market_name,
                    'outcome': outcome,
                    'odds': odds,
                    'implied_probability': round(self.calculate_implied_probability(odds) * 100, 1),
                    'true_probability': round(true_prob * 100, 1),
                    'value_edge': round(value_pct, 1),
                    'confidence': confidence,
                    'suggested_stake': round(stake, 2),
                    'recommendation': self._get_recommendation(value_pct),
                    'market_type': market_type
                })
        
        # Sort by value edge (highest first)
        results.sort(key=lambda x: x['value_edge'], reverse=True)
        
        positive_bets = [b for b in results if b['value_edge'] > 2.0]
        ai_selection = positive_bets[0] if positive_bets else (results[0] if results else None)
        
        return {
            'match': f"{home_team} vs {away_team}",
            'total_markets': len(results),
            'value_bets_count': len(positive_bets),
            'ai_selection': ai_selection,
            'all_value_bets': results[:20]
        }
    
    def _detect_market_type(self, market_name):
        """Detect market type from name"""
        market_lower = market_name.lower()
        if '1x2' in market_lower or 'match winner' in market_lower:
            return '1X2'
        elif 'over/under' in market_lower:
            return 'Over/Under'
        elif 'gg/ng' in market_lower or 'both teams' in market_lower:
            return 'GG/NG'
        elif 'double chance' in market_lower:
            return 'Double Chance'
        elif 'handicap' in market_lower:
            return 'Handicap'
        else:
            return 'Other'
    
    def _get_confidence(self, value_pct, odds):
        """Calculate confidence score (0-100)"""
        base = 50
        value_boost = min(30, value_pct * 2)
        
        if odds < 1.3:
            confidence = 80
        elif odds > 10:
            confidence = 30
        else:
            confidence = base + max(0, value_boost)
        
        return min(95, max(5, round(confidence)))
    
    def _get_recommendation(self, value_pct):
        """Generate recommendation text"""
        if value_pct > 15:
            return "🔥 STRONG VALUE - High confidence bet recommended"
        elif value_pct > 10:
            return "✅ GOOD VALUE - Recommended bet"
        elif value_pct > 5:
            return "📈 MODERATE VALUE - Consider betting"
        elif value_pct > 2:
            return "⚠️ SMALL VALUE - Low stake only"
        else:
            return "📊 FAIR MARKET - No significant value detected"


# Global instance
_ai = None

def get_ai():
    global _ai
    if _ai is None:
        _ai = BettingAI()
    return _ai
