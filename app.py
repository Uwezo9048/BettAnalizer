"""
AI Sports Betting Assistant - Multi-Sport & Multi-League Integration
Supports: World Cup, AFCON, Premier League, La Liga, Bundesliga, Serie A,
Champions League, Cricket, Basketball, Tennis, and more
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import re
import shutil
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

from betting_ai import get_ai
from live_odds_fetcher import (
    get_fetcher,
    SUPPORTED_LIVE_SITES,
    SUPPORTED_SPORTS,
    API_AVAILABLE,
    API_IMPORT_ERROR,
    LIVE_FEEDS_ENABLED,
)

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

@app.route('/api/sports')
def get_supported_sports():
    """Get all visible sports categories"""
    site_id = request.args.get('site', 'sportybet')
    if site_id not in SUPPORTED_LIVE_SITES:
        return jsonify({'error': f'Unsupported site: {site_id}'}), 400

    sports = fetcher.get_supported_sports(site_id)
    return jsonify({
        'sports': sports,
        'default': 'football',
        'count': len(sports),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/leagues')
def get_supported_leagues():
    """Get all available leagues/competitions"""
    site_id = request.args.get('site', 'sportybet')
    sport = request.args.get('sport', 'football')
    
    leagues = fetcher.get_supported_leagues(site_id, sport)
    return jsonify({
        'leagues': leagues,
        'count': len(leagues),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/matches', methods=['POST'])
def get_matches():
    """Fetch live matches and odds from selected site"""
    try:
        data = request.json
        site_id = data.get('site', 'sportybet')
        sport = data.get('sport', 'football')
        league_filter = data.get('league', None)
        
        # Validate site
        if site_id not in SUPPORTED_LIVE_SITES:
            return jsonify({'error': f'Unsupported site: {site_id}'}), 400

        if sport not in SUPPORTED_SPORTS:
            return jsonify({'error': f'Unsupported sport: {sport}'}), 400

        site_info = SUPPORTED_LIVE_SITES[site_id]
        sport_info = SUPPORTED_SPORTS[sport]

        if not sport_info.get('live_feed'):
            return jsonify({
                'site': site_id,
                'site_name': site_info['name'],
                'site_flag': site_info['flag'],
                'sport': sport,
                'sport_name': sport_info['name'],
                'matches': [],
                'count': 0,
                'is_live_data': False,
                'is_real_odds': False,
                'data_source': 'unsupported',
                'api_available': API_AVAILABLE and LIVE_FEEDS_ENABLED,
                'message': f"{sport_info['name']} feed is not connected yet.",
                'timestamp': datetime.now().isoformat()
            })

        # Fetch matches
        matches = fetcher.fetch_live_odds(site_id, sport, league_filter)
        
        # Add match dates and times
        for match in matches:
            if 'start_time' not in match or not match['start_time']:
                # Generate a realistic date for upcoming matches
                import random
                from datetime import timedelta
                days_ahead = random.randint(0, 14)
                hours = random.randint(10, 22)
                minutes = random.choice([0, 15, 30, 45])
                match['start_time'] = (datetime.now() + timedelta(days=days_ahead, hours=hours, minutes=minutes)).isoformat()
                
                # Add match status
                if days_ahead == 0:
                    match['status'] = 'Live' if random.random() > 0.7 else 'Upcoming'
                else:
                    match['status'] = 'Upcoming'
            else:
                # Determine status based on start time
                start = datetime.fromisoformat(match['start_time'].replace('Z', '+00:00'))
                if start < datetime.now(timezone.utc):
                    match['status'] = 'Finished' if random.random() > 0.3 else 'Live'
                elif start < datetime.now(timezone.utc) + timedelta(hours=1):
                    match['status'] = 'Live'
                else:
                    match['status'] = 'Upcoming'
            
            # Add competition type
            match['competition_type'] = fetcher._get_competition_type(match.get('league', ''))
        
        # Filter by league if specified
        if league_filter:
            matches = [m for m in matches if m.get('league', '').lower() == league_filter.lower()]
        
        first_match = matches[0] if matches else {}
        is_sample_data = bool(first_match.get('sample', False))
        is_from_api = bool(first_match.get('from_api', False))
        data_source = 'live' if not is_sample_data and not is_from_api else 'api' if is_from_api else 'sample'
        
        return jsonify({
            'site': site_id,
            'site_name': site_info['name'],
            'site_flag': site_info['flag'],
            'sport': sport,
            'sport_name': sport_info['name'],
            'matches': matches,
            'count': len(matches),
            'is_live_data': not is_sample_data,
            'is_real_odds': not is_sample_data,
            'data_source': data_source,
            'api_available': API_AVAILABLE and LIVE_FEEDS_ENABLED,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"[ERROR] /api/matches: {e}")
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
                bet['competition_type'] = match.get('competition_type', '')
                bet['start_time'] = match.get('start_time', '')
                bet['status'] = match.get('status', '')
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

@app.route('/api/analyze-slip', methods=['POST'])
def analyze_betslip():
    """Analyze a screenshot/text betslip and suggest a cleaner slip."""
    try:
        uploaded_file = request.files.get('screenshot')
        user_text = request.form.get('slip_text', '').strip()
        ocr_text = _extract_text_from_image(uploaded_file) if uploaded_file else ''
        slip_text = user_text or ocr_text

        if not slip_text:
            return jsonify({
                'error': 'No readable betslip text found. OCR is optional on this server, so paste or type the betslip lines and try again.',
                'ocr_available': _ocr_available(),
                'ocr_text': ocr_text
            }), 400

        selections = _parse_betslip_text(slip_text)
        if not selections:
            return jsonify({
                'error': 'Could not detect selections and decimal odds from the betslip text.',
                'ocr_available': _ocr_available(),
                'ocr_text': ocr_text
            }), 400

        analyzed = [_analyze_slip_selection(selection) for selection in selections]
        kept = [selection for selection in analyzed if selection['decision'] == 'keep']
        removed = [selection for selection in analyzed if selection['decision'] == 'remove']

        original_odds = _combined_odds(analyzed)
        suggested_odds = _combined_odds(kept)
        average_confidence = round(sum(item['confidence'] for item in kept) / len(kept), 1) if kept else 0

        return jsonify({
            'ocr_available': _ocr_available(),
            'ocr_text': ocr_text,
            'source_text': slip_text,
            'total_selections': len(analyzed),
            'kept_count': len(kept),
            'removed_count': len(removed),
            'original_combined_odds': original_odds,
            'suggested_combined_odds': suggested_odds,
            'average_confidence': average_confidence,
            'kept': kept,
            'removed': removed,
            'all_selections': analyzed,
            'summary': _build_betslip_summary(len(analyzed), kept, removed, original_odds, suggested_odds),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status')
def api_status():
    """Check API status"""
    return jsonify({
        'oddsafrica_api_available': API_AVAILABLE,
        'oddsafrica_api_error': API_IMPORT_ERROR,
        'live_feeds_enabled': LIVE_FEEDS_ENABLED,
        'supported_sites': list(SUPPORTED_LIVE_SITES.keys()),
        'supported_sports': list(SUPPORTED_SPORTS.keys()),
        'live_feeds_active': LIVE_FEEDS_ENABLED,
        'data_source': 'multi_source_integration',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/debug-status')
def debug_status():
    """Debug endpoint"""
    import sys
    
    return jsonify({
        'api_available': API_AVAILABLE,
        'api_import_error': API_IMPORT_ERROR,
        'live_feeds_enabled': LIVE_FEEDS_ENABLED,
        'environment': {
            'RENDER': os.environ.get('RENDER'),
            'LIVE_FEEDS_ENABLED': os.environ.get('LIVE_FEEDS_ENABLED'),
            'ODDS_API_IO_KEY': '***' if os.environ.get('ODDS_API_IO_KEY') else 'Not Set',
        },
        'python_version': sys.version,
        'timestamp': datetime.now().isoformat(),
        'note': 'Multi-source integration with match dates and multiple competitions'
    })

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'api_available': API_AVAILABLE,
        'live_feeds_enabled': LIVE_FEEDS_ENABLED,
        'timestamp': datetime.now().isoformat()
    }), 200

# ========== Helper Functions ==========

def _ocr_available():
    try:
        import pytesseract
        from PIL import Image
        return True
    except Exception:
        return False

def _extract_text_from_image(uploaded_file):
    if not uploaded_file or not _ocr_available():
        return ''

    try:
        from io import BytesIO
        import pytesseract
        from PIL import Image
        image = Image.open(BytesIO(uploaded_file.read()))
        return pytesseract.image_to_string(image).strip()
    except Exception as e:
        print(f"Betslip OCR failed: {e}")
        return ''

def _parse_betslip_text(text):
    selections = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    odds_pattern = re.compile(r'(?<!\d)([1-9]\d{0,2}\.\d{2})(?!\d)')
    compact_odds_pattern = re.compile(r'(?<!\d)([1-9]\d{2})(?!\d)\s*$')

    for index, line in enumerate(lines):
        matches = odds_pattern.findall(line)
        compact_match = None if matches else compact_odds_pattern.search(line)
        if not matches and not compact_match:
            continue

        odds_text = matches[-1] if matches else f"{compact_match.group(1)[0]}.{compact_match.group(1)[1:]}"
        odds = float(odds_text)
        if odds < 1.01 or odds > 1000:
            continue

        line_without_odds = odds_pattern.sub('', line)
        if compact_match:
            line_without_odds = compact_odds_pattern.sub('', line_without_odds)
        line_without_odds = line_without_odds.strip(' -|:')
        context = []
        if index > 0 and not odds_pattern.search(lines[index - 1]):
            context.append(lines[index - 1])
        if line_without_odds:
            context.append(line_without_odds)

        label = ' - '.join(context).strip(' -|:') or f'Selection {len(selections) + 1}'
        selection, market, match_name = _split_selection_label(label)
        selections.append({
            'match': match_name,
            'selection': selection,
            'market': market,
            'odds': odds
        })

    return selections

def _split_selection_label(label):
    cleaned = re.sub(r'\s+', ' ', label).strip()
    market = 'Betslip Selection'

    known_markets = ['1X2', 'Match Winner', 'Double Chance', 'Over/Under', 'Both Teams To Score', 'GG/NG', 'Handicap']
    for known_market in known_markets:
        if known_market.lower() in cleaned.lower():
            market = known_market
            break

    separators = [' - ', ' | ', ': ']
    parts = [cleaned]
    for separator in separators:
        if separator in cleaned:
            parts = [part.strip() for part in cleaned.split(separator) if part.strip()]
            break

    if len(parts) >= 2:
        match_name = parts[0]
        selection = parts[-1]
    else:
        match_name = cleaned
        selection = cleaned

    return selection, market, match_name

def _analyze_slip_selection(selection):
    odds = selection['odds']
    market = selection.get('market', 'Betslip Selection')
    market_type = ai._detect_market_type(market)
    true_probability = ai.calculate_true_probability(odds, market_type)
    implied_probability = ai.calculate_implied_probability(odds)
    value_edge = ai.calculate_value_score(odds, true_probability) * 100
    losing_probability = (1 - true_probability) * 100
    confidence = ai._get_confidence(value_edge, odds)

    remove_reasons = []
    if losing_probability >= 55:
        remove_reasons.append('high losing probability')
    if confidence < 45:
        remove_reasons.append('low confidence')

    decision = 'remove' if remove_reasons else 'keep'

    return {
        **selection,
        'implied_probability': round(implied_probability * 100, 1),
        'true_probability': round(true_probability * 100, 1),
        'losing_probability': round(losing_probability, 1),
        'value_edge': round(value_edge, 1),
        'confidence': confidence,
        'decision': decision,
        'reason': ', '.join(remove_reasons) if remove_reasons else 'acceptable risk profile',
        'suggested_stake': round(ai.calculate_kelly_stake(odds, true_probability), 2) if decision == 'keep' else 0
    }

def _combined_odds(selections):
    if not selections:
        return 0
    combined = 1
    for selection in selections:
        combined *= selection['odds']
    return round(combined, 2)

def _build_betslip_summary(total, kept, removed, original_odds, suggested_odds):
    if not kept:
        return 'All detected selections look too risky. Rebuild the slip with lower-risk markets or fewer legs.'
    if removed:
        return f'Removed {len(removed)} risky selection(s) from {total}. Suggested odds moved from {original_odds} to {suggested_odds} with a cleaner risk profile.'
    return f'No removals needed from {total} detected selection(s). Suggested combined odds remain {suggested_odds}.'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)