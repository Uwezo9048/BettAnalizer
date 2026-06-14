"""
AI Sports Betting Assistant - Live Feeds from Supported Sites
Sites with live feed: SportyBet, Bet9ja, 22bet, Paripesa, Nairabet, Betking
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

from betting_ai import get_ai
from live_odds_fetcher import get_fetcher, SUPPORTED_LIVE_SITES, API_AVAILABLE

ai = get_ai()
fetcher = get_fetcher()

# ========== Routes ==========

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/api/sites')
def get_supported_sites():
    """Get all sites with live feed capability"""
    sites = fetcher.get_supported_sites()
    return jsonify({
        'sites': sites,
        'default': 'sportybet',
        'live_api_available': API_AVAILABLE,
        'count': len(sites),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/matches', methods=['POST'])
def get_matches():
    """Fetch live matches and odds from selected site"""
    try:
        data = request.json
        site_id = data.get('site', 'sportybet')
        sport = data.get('sport', 'football')
        
        # Validate site
        if site_id not in SUPPORTED_LIVE_SITES:
            return jsonify({'error': f'Unsupported site: {site_id}'}), 400
        
        matches = fetcher.fetch_live_odds(site_id, sport)
        site_info = SUPPORTED_LIVE_SITES[site_id]
        
        return jsonify({
            'site': site_id,
            'site_name': site_info['name'],
            'site_flag': site_info['flag'],
            'matches': matches,
            'count': len(matches),
            'is_live_data': API_AVAILABLE and not (matches and matches[0].get('sample', False)),
            'api_available': API_AVAILABLE,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze_match():
    """Analyze a specific match using AI"""
    try:
        data = request.json
        match = data.get('match')
        
        if not match:
            return jsonify({'error': 'Match data required'}), 400
        
        analysis = ai.analyze_match(match)
        
        return jsonify({
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-all', methods=['POST'])
def analyze_all_matches():
    """Analyze all matches and return best value bets"""
    try:
        data = request.json
        matches = data.get('matches', [])
        site_name = data.get('site_name', 'Unknown')
        
        all_bets = []
        for match in matches:
            analysis = ai.analyze_match(match)
            if analysis['ai_selection']:
                bet = analysis['ai_selection']
                bet['match_name'] = analysis['match']
                bet['home_team'] = match.get('home_team')
                bet['away_team'] = match.get('away_team')
                bet['league'] = match.get('league', '')
                all_bets.append(bet)
        
        # Sort by value edge
        all_bets.sort(key=lambda x: x['value_edge'], reverse=True)
        
        return jsonify({
            'site': site_name,
            'total_matches': len(matches),
            'total_value_bets': len(all_bets),
            'top_bets': all_bets[:15],
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/custom-predict', methods=['POST'])
def custom_predict():
    """Predict using manually entered odds"""
    try:
        data = request.json
        home_team = data.get('home_team', 'Home')
        away_team = data.get('away_team', 'Away')
        market = data.get('market', '1X2')
        outcome = data.get('outcome', '')
        odds = data.get('odds', 0)
        
        if odds <= 0:
            return jsonify({'error': 'Invalid odds'}), 400
        
        implied_prob = ai.calculate_implied_probability(odds)
        true_prob = ai.calculate_true_probability(odds, market)
        value_edge = (true_prob * odds - 1) * 100
        stake = ai.calculate_kelly_stake(odds, true_prob) if value_edge > 0 else 0
        confidence = ai._get_confidence(value_edge, odds)
        
        # Generate prediction text
        if value_edge > 10:
            prediction = f"🔥 STRONG VALUE - AI predicts {outcome} has significant value at {odds}"
        elif value_edge > 5:
            prediction = f"✅ GOOD VALUE - AI recommends {outcome} at {odds}"
        elif value_edge > 2:
            prediction = f"📈 MODERATE VALUE - {outcome} shows some value at {odds}"
        else:
            prediction = f"📊 FAIR MARKET - {outcome} is fairly priced at {odds}"
        
        return jsonify({
            'match': f"{home_team} vs {away_team}",
            'market': market,
            'outcome': outcome,
            'odds': odds,
            'implied_probability': round(implied_prob * 100, 1),
            'true_probability': round(true_prob * 100, 1),
            'value_edge': round(value_edge, 1),
            'confidence': confidence,
            'suggested_stake': round(stake, 2),
            'ai_prediction': prediction,
            'recommendation': ai._get_recommendation(value_edge)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def api_status():
    """Check API status"""
    return jsonify({
        'oddsafrica_api_available': API_AVAILABLE,
        'supported_sites': list(SUPPORTED_LIVE_SITES.keys()),
        'live_feeds_active': API_AVAILABLE,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)