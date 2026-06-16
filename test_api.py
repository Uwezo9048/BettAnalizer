"""
Simple test for The Odds API
"""

from odds_api import OddsAPI

def test():
    api = OddsAPI()
    
    print("🔍 Testing The Odds API...")
    print(f"Using API key: {api.api_key[:10]}...")
    
    # Test with EPL
    print("\n📊 Fetching English Premier League matches...")
    matches = api.fetch_matches('soccer_epl')
    
    if matches and len(matches) > 0:
        print(f"\n✅ Found {len(matches)} matches!")
        print("\n📋 Matches:")
        for i, match in enumerate(matches[:5]):
            print(f"  {i+1}. {match['home_team']} vs {match['away_team']}")
            print(f"     League: {match['league']}")
            if match['markets'].get('1X2'):
                odds = match['markets']['1X2']
                print(f"     Odds: Home={odds.get('Home', 'N/A')}, Draw={odds.get('Draw', 'N/A')}, Away={odds.get('Away', 'N/A')}")
        return True
    else:
        print("\n❌ No matches found.")
        print("\n💡 Your API key might be invalid.")
        print("   Get a new one from: https://the-odds-api.com/")
        return False

if __name__ == "__main__":
    test()