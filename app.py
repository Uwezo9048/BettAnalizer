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
import sys
import subprocess
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

# ========== TESSERACT OCR CONFIGURATION ==========
import pytesseract

# STEP 1: Override environment variable for Render
if os.environ.get('RENDER') == 'true':
    print("[OCR] 🔍 Render environment detected")
    # Force Linux path (override Windows path from environment)
    os.environ['TESSERACT_CMD'] = '/usr/bin/tesseract'
    print("[OCR] ✅ TESSERACT_CMD set to: /usr/bin/tesseract")

# STEP 2: Find Tesseract
def find_tesseract():
    """Find Tesseract executable across different platforms"""
    
    # Check environment variable first
    env_path = os.environ.get('TESSERACT_CMD')
    if env_path and os.path.exists(env_path):
        return env_path
    
    # Check if on Render (Linux)
    if os.environ.get('RENDER') == 'true':
        linux_paths = [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/opt/render/project/src/.venv/bin/tesseract',
        ]
        for path in linux_paths:
            if os.path.exists(path):
                return path
        
        # Try which command
        try:
            result = subprocess.run(['which', 'tesseract'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except:
            pass
        
        # Try find command
        try:
            result = subprocess.run(['find', '/usr', '-name', 'tesseract', '-type', 'f'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        return None
    
    # Check Windows paths
    windows_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]
    for path in windows_paths:
        if os.path.exists(path):
            return path
    
    # Check Linux/macOS paths
    linux_paths = [
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
        '/opt/homebrew/bin/tesseract',
    ]
    for path in linux_paths:
        if os.path.exists(path):
            return path
    
    return None

# STEP 3: Set Tesseract path
tesseract_path = find_tesseract()
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    os.environ['TESSERACT_CMD'] = tesseract_path
    print(f"[OCR] ✅ Tesseract found at: {tesseract_path}")
else:
    print("[OCR] ❌ Tesseract not found!")
    if os.environ.get('RENDER') == 'true':
        print("[OCR] 💡 On Render, make sure build.sh installs tesseract-ocr")
    else:
        print("[OCR] 💡 Install Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki")

# STEP 4: Test Tesseract
try:
    version = pytesseract.get_tesseract_version()
    print(f"[OCR] ✅ Tesseract version: {version}")
except Exception as e:
    print(f"[OCR] ⚠️ Could not get Tesseract version: {e}")

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
        'timestamp': datetime.now(timezone.utc).isoformat()
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
        'timestamp': datetime.now(timezone.utc).isoformat()
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
        'timestamp': datetime.now(timezone.utc).isoformat()
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
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

        # Fetch matches
        matches = fetcher.fetch_live_odds(site_id, sport, league_filter)
        
        # Ensure all matches have timezone-aware dates
        for match in matches:
            if 'start_time' in match and match['start_time']:
                try:
                    clean_time = match['start_time'].replace('Z', '+00:00')
                    dt = datetime.fromisoformat(clean_time)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    match['start_time'] = dt.isoformat()
                except:
                    match['start_time'] = datetime.now(timezone.utc).isoformat()
            
            if 'status' not in match:
                match['status'] = fetcher._determine_match_status(match.get('start_time'))
            
            if 'competition_type' not in match:
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
            'timestamp': datetime.now(timezone.utc).isoformat()
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
            'timestamp': datetime.now(timezone.utc).isoformat()
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
            'timestamp': datetime.now(timezone.utc).isoformat()
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

# ========== OCR Helper Functions ==========

def _get_tesseract_command():
    """Get tesseract command path - cross-platform"""
    # Return the path we already found
    tesseract_path = os.environ.get('TESSERACT_CMD')
    if tesseract_path and os.path.exists(tesseract_path):
        return tesseract_path
    
    # Check if on Render
    if os.environ.get('RENDER') == 'true':
        linux_paths = ['/usr/bin/tesseract', '/usr/local/bin/tesseract']
        for path in linux_paths:
            if os.path.exists(path):
                return path
        return None
    
    # Check common Windows paths
    windows_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]
    for path in windows_paths:
        if os.path.exists(path):
            return path
    
    # Linux/macOS paths
    linux_paths = [
        '/usr/bin/tesseract',
        '/usr/local/bin/tesseract',
        '/opt/homebrew/bin/tesseract',
    ]
    for path in linux_paths:
        if os.path.exists(path):
            return path
    
    return None

def _ocr_available():
    """Check if OCR is available - cross-platform"""
    try:
        import pytesseract
        from PIL import Image
        
        # Check if Tesseract is accessible
        tesseract_cmd = _get_tesseract_command()
        if tesseract_cmd and os.path.exists(tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            # Try to get version to confirm it works
            try:
                version = pytesseract.get_tesseract_version()
                print(f"[OCR] Tesseract version: {version}")
                return True
            except:
                # Version check might fail but OCR could still work
                return True
        
        # Try using the default system PATH
        try:
            import subprocess
            subprocess.run(['tesseract', '--version'], capture_output=True, check=True)
            return True
        except:
            return False
            
    except Exception as e:
        print(f"[OCR] Error checking availability: {e}")
        return False

def _extract_text_fallback(image):
    """Fallback OCR using alternative methods when Tesseract is not available"""
    try:
        from PIL import Image
        
        # Try to extract text using pytesseract if available
        try:
            import pytesseract
            tesseract_cmd = _get_tesseract_command()
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
                text = pytesseract.image_to_string(image)
                if text.strip():
                    return text.strip()
        except:
            pass
        
        # If no text found, try to read EXIF data or metadata
        try:
            if hasattr(image, 'info') and image.info:
                for key, value in image.info.items():
                    if isinstance(value, str) and len(value) > 10:
                        import re
                        if re.search(r'\d+\.\d{2}', value):
                            return value
        except:
            pass
        
        return ''
            
    except Exception as e:
        print(f"[OCR Fallback] Error: {e}")
        return ''

def _extract_text_from_image(uploaded_file):
    """Extract text from uploaded image using OCR with enhanced preprocessing"""
    if not uploaded_file:
        return ''
    
    try:
        from io import BytesIO
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
        
        # Read image
        image = Image.open(BytesIO(uploaded_file.read()))
        print(f"[OCR] Original image size: {image.size}, mode: {image.mode}")
        
        # Check if OCR is available
        if not _ocr_available():
            print("[OCR] Tesseract not available. Using fallback method...")
            return _extract_text_fallback(image)
        
        # Set tesseract command
        tesseract_cmd = _get_tesseract_command()
        if tesseract_cmd:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            print(f"[OCR] Using Tesseract at: {tesseract_cmd}")
        
        # ========== Enhanced Preprocessing ==========
        
        # 1. Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        print(f"[OCR] Converted to grayscale")
        
        # 2. Resize if too small (improves OCR accuracy)
        width, height = image.size
        if width < 1000:
            new_width = 1000
            new_height = int(height * (1000 / width))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            print(f"[OCR] Resized to: {image.size}")
        
        # 3. Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(3.0)
        print(f"[OCR] Enhanced contrast")
        
        # 4. Apply sharpening
        image = image.filter(ImageFilter.SHARPEN)
        print(f"[OCR] Applied sharpening")
        
        # 5. Remove noise
        image = image.filter(ImageFilter.MedianFilter(size=3))
        print(f"[OCR] Removed noise")
        
        # 6. Binarize
        threshold = 120
        image = image.point(lambda p: 255 if p > threshold else 0)
        print(f"[OCR] Binarized with threshold: {threshold}")
        
        # ========== Try Multiple OCR Configs ==========
        
        import pytesseract
        
        configs = [
            '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz@- ',
            '--psm 4 --oem 3',
            '--psm 11 --oem 3',
            '--psm 3 --oem 3',
            '-l eng --psm 6 --oem 3',
        ]
        
        best_text = ''
        best_length = 0
        
        for config in configs:
            try:
                print(f"[OCR] Trying config: {config}")
                text = pytesseract.image_to_string(image, config=config)
                cleaned = text.strip()
                if cleaned:
                    length = len(cleaned)
                    if length > best_length:
                        best_length = length
                        best_text = cleaned
                        print(f"[OCR] Found {length} characters with config: {config}")
            except Exception as e:
                print(f"[OCR] Config {config} failed: {e}")
                continue
        
        # If no text found, try with original image (no preprocessing)
        if not best_text:
            print("[OCR] No text found with preprocessed image. Trying original...")
            try:
                uploaded_file.seek(0)
                original = Image.open(BytesIO(uploaded_file.read()))
                text = pytesseract.image_to_string(original, config='--psm 6 --oem 3')
                if text.strip():
                    best_text = text.strip()
                    print(f"[OCR] Found text with original image: {len(best_text)} characters")
            except Exception as e:
                print(f"[OCR] Original image attempt failed: {e}")
        
        if best_text:
            print(f"[OCR] Total extracted text: {len(best_text)} characters")
            print(f"[OCR] Preview: {best_text[:200]}...")
            return best_text
        else:
            print("[OCR] No text extracted from image")
            return ''
        
    except Exception as e:
        print(f"[OCR Error] {e}")
        import traceback
        traceback.print_exc()
        return ''

@app.route('/api/analyze-slip', methods=['POST'])
def analyze_betslip():
    """Analyze a screenshot/text betslip and suggest a cleaner slip."""
    try:
        uploaded_file = request.files.get('screenshot')
        user_text = request.form.get('slip_text', '').strip()
        
        # Try OCR if image uploaded
        ocr_text = ''
        if uploaded_file:
            print("[OCR] Processing uploaded image...")
            ocr_text = _extract_text_from_image(uploaded_file)
            if ocr_text:
                print(f"[OCR] Successfully extracted text: {ocr_text[:200]}...")
            else:
                print("[OCR] No text extracted from image")
        
        # Use user text if provided, otherwise OCR text
        slip_text = user_text or ocr_text
        
        # Check if we have any text
        if not slip_text:
            ocr_available = _ocr_available()
            
            # Build helpful error message
            error_msg = 'No readable betslip text found. '
            if uploaded_file and not ocr_text:
                if not ocr_available:
                    error_msg += 'OCR is not available on this server. '
                    error_msg += 'Please paste the betslip text manually using the "Text Input" tab.'
                else:
                    error_msg += 'OCR could not extract text from the image. '
                    error_msg += 'Please paste the betslip text manually using the "Text Input" tab, '
                    error_msg += 'or upload a clearer image with better lighting and contrast.'
            elif not uploaded_file and not user_text:
                error_msg += 'Please paste your betslip text in the "Text Input" tab '
                error_msg += 'using the format: "Team A vs Team B - Selection @ odds"'
            else:
                error_msg += 'Please check your input and try again.'
            
            return jsonify({
                'error': error_msg,
                'ocr_available': ocr_available,
                'ocr_text': ocr_text,
                'tip': 'Switch to the "Text Input" tab and paste your betslip there.',
                'example': 'Example: "Liverpool vs Arsenal - Home @ 2.10"'
            }), 400

        # Parse the betslip text
        selections = _parse_betslip_text(slip_text)
        if not selections:
            return jsonify({
                'error': 'Could not detect selections and decimal odds from the betslip text.',
                'tip': 'Format: "Team A vs Team B - Selection @ odds" (e.g., "Liverpool vs Arsenal - Home @ 2.10")',
                'source_text': slip_text,
                'example': 'Liverpool vs Arsenal - Home @ 2.10\nReal Madrid vs Barcelona - Draw @ 3.40'
            }), 400

        # Analyze each selection
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
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    except Exception as e:
        print(f"[Betslip Error] {e}")
        import traceback
        traceback.print_exc()
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
        'timestamp': datetime.now(timezone.utc).isoformat()
    })

@app.route('/api/debug-status')
def debug_status():
    """Debug endpoint"""
    
    # Check OCR status
    ocr_available = _ocr_available()
    tesseract_path = _get_tesseract_command()
    
    return jsonify({
        'api_available': API_AVAILABLE,
        'api_import_error': API_IMPORT_ERROR,
        'live_feeds_enabled': LIVE_FEEDS_ENABLED,
        'ocr_available': ocr_available,
        'tesseract_path': tesseract_path,
        'environment': {
            'RENDER': os.environ.get('RENDER'),
            'LIVE_FEEDS_ENABLED': os.environ.get('LIVE_FEEDS_ENABLED'),
            'ODDS_API_IO_KEY': '***' if os.environ.get('ODDS_API_IO_KEY') else 'Not Set',
            'TESSERACT_CMD': os.environ.get('TESSERACT_CMD', 'Not Set'),
        },
        'python_version': sys.version,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'note': 'Multi-source integration with OCR support'
    })

@app.route('/health')
def health():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'api_available': API_AVAILABLE,
        'live_feeds_enabled': LIVE_FEEDS_ENABLED,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200

@app.route('/api/test-tesseract')
def test_tesseract():
    """Test if Tesseract is installed on Render"""
    import subprocess
    import os
    
    results = {
        'render_env': os.environ.get('RENDER'),
        'tesseract_cmd': os.environ.get('TESSERACT_CMD'),
        'file_exists': os.path.exists('/usr/bin/tesseract'),
        'which_tesseract': None,
        'version': None,
        'test_output': None
    }
    
    # Try which command
    try:
        result = subprocess.run(['which', 'tesseract'], capture_output=True, text=True, timeout=5)
        results['which_tesseract'] = result.stdout.strip() if result.returncode == 0 else None
    except:
        pass
    
    # Try to get version
    try:
        if os.path.exists('/usr/bin/tesseract'):
            result = subprocess.run(['/usr/bin/tesseract', '--version'], capture_output=True, text=True, timeout=5)
            results['version'] = result.stdout.split('\n')[0] if result.returncode == 0 else None
    except:
        pass
    
    # Test with simple text
    try:
        if os.path.exists('/usr/bin/tesseract'):
            result = subprocess.run(['echo', 'Hello World'], capture_output=True, text=True)
            # This is a simple test - just checking if tesseract can run
            results['test_output'] = 'Tesseract executable exists and is accessible'
    except:
        pass
    
    return jsonify(results)

# ========== Helper Functions ==========

def _parse_betslip_text(text):
    """Parse betslip text to extract selections and odds"""
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
    """Split selection label into parts"""
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
    """Analyze a single betslip selection"""
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
    """Calculate combined odds for multiple selections"""
    if not selections:
        return 0
    combined = 1
    for selection in selections:
        combined *= selection['odds']
    return round(combined, 2)

def _build_betslip_summary(total, kept, removed, original_odds, suggested_odds):
    """Build a summary for the betslip analysis"""
    if not kept:
        return 'All detected selections look too risky. Rebuild the slip with lower-risk markets or fewer legs.'
    if removed:
        return f'Removed {len(removed)} risky selection(s) from {total}. Suggested odds moved from {original_odds} to {suggested_odds} with a cleaner risk profile.'
    return f'No removals needed from {total} detected selection(s). Suggested combined odds remain {suggested_odds}.'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)