// Global state
let currentSite = 'sportybet';
let currentMatches = [];
let supportedSites = [];

// DOM Elements
const siteSearchInput = document.getElementById('siteSearchInput');
const siteDropdown = document.getElementById('siteDropdown');
const dropdownItems = document.getElementById('dropdownItems');
const selectedSiteDisplay = document.getElementById('selectedSiteDisplay');
const liveStatusText = document.getElementById('liveStatusText');
const siteInfoText = document.getElementById('siteInfoText');
const refreshBtn = document.getElementById('refreshBtn');
const matchesContainer = document.getElementById('matchesContainer');
const matchesSourceText = document.getElementById('matchesSourceText');
const matchesCountDisplay = document.getElementById('matchesCountDisplay');
const matchesCount = document.getElementById('matchesCount');
const valueBetsCount = document.getElementById('valueBetsCount');
const aiSelectionPanel = document.getElementById('aiSelectionPanel');
const analyzeAllBtn = document.getElementById('analyzeAllBtn');
const globalResults = document.getElementById('globalResults');
const globalResultsContainer = document.getElementById('globalResultsContainer');
const apiStatusBadge = document.getElementById('apiStatusBadge');

// Manual entry elements
const manualHomeTeam = document.getElementById('manualHomeTeam');
const manualAwayTeam = document.getElementById('manualAwayTeam');
const manualMarket = document.getElementById('manualMarket');
const manualOutcome = document.getElementById('manualOutcome');
const manualOdds = document.getElementById('manualOdds');
const manualPredictBtn = document.getElementById('manualPredictBtn');
const manualResult = document.getElementById('manualResult');

// Site data with gradients and colors
const siteGradients = {
    'sportybet': 'gradient-sporty',
    'bet9ja': 'gradient-bet9ja',
    '22bet': 'gradient-purple',
    'paripesa': 'gradient-green',
    'nairabet': 'gradient-purple',
    'betking': 'gradient-green'
};

const siteFlags = {
    'sportybet': '🇰🇪',
    'bet9ja': '🇳🇬',
    '22bet': '🌍',
    'paripesa': '🇰🇪',
    'nairabet': '🇳🇬',
    'betking': '🇳🇬'
};

// Initialize
async function init() {
    await checkAPIStatus();
    await loadSupportedSites();
    await loadMatches();
    setupEventListeners();
}

// Check API status
async function checkAPIStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.oddsafrica_api_available) {
            apiStatusBadge.innerHTML = '<span class="w-2 h-2 bg-green-500 rounded-full live-indicator"></span> Live API Active';
            apiStatusBadge.classList.add('gradient-green');
            apiStatusBadge.classList.remove('bg-gray-700');
        } else {
            apiStatusBadge.innerHTML = '<span class="w-2 h-2 bg-yellow-500 rounded-full"></span> Demo Mode (Install API)';
        }
    } catch (error) {
        console.error('Status check failed:', error);
    }
}

// Load supported sites
async function loadSupportedSites() {
    try {
        const response = await fetch('/api/sites');
        const data = await response.json();
        supportedSites = data.sites;
        renderDropdown(supportedSites);
    } catch (error) {
        console.error('Error loading sites:', error);
    }
}

// Render dropdown
function renderDropdown(sites) {
    dropdownItems.innerHTML = sites.map(site => `
        <div onclick="selectSite('${site.id}')" 
            class="site-dropdown px-4 py-3 hover:bg-gray-700 cursor-pointer flex items-center justify-between border-b border-gray-700 last:border-0">
            <div class="flex items-center gap-3">
                <span class="text-2xl">${site.flag || '🌍'}</span>
                <div>
                    <div class="font-semibold">${site.name}</div>
                    <div class="text-xs text-gray-400">${site.country}</div>
                </div>
            </div>
            ${site.is_default ? '<span class="text-xs bg-purple-600 px-2 py-1 rounded-full">Default</span>' : ''}
        </div>
    `).join('');
}

// Select site from dropdown
async function selectSite(siteId) {
    currentSite = siteId;
    const site = supportedSites.find(s => s.id === siteId);
    
    if (site) {
        // Update display
        const gradientClass = siteGradients[siteId] || 'gradient-sporty';
        selectedSiteDisplay.className = `mt-4 p-3 rounded-lg ${gradientClass}`;
        selectedSiteDisplay.innerHTML = `
            <div class="flex justify-between items-center">
                <div>
                    <span class="text-2xl mr-2">${site.flag || '🌍'}</span>
                    <span class="font-bold">${site.name}</span>
                    ${site.is_default ? '<span class="text-xs ml-2 opacity-80">Default</span>' : ''}
                </div>
                <div class="flex items-center gap-2">
                    <span class="w-2 h-2 bg-green-500 rounded-full live-indicator"></span>
                    <span class="text-sm" id="liveStatusText">Live Feed Active</span>
                </div>
            </div>
        `;
        
        siteInfoText.innerHTML = `💡 ${site.name} provides live odds via OddsAfrica-API`;
    }
    
    // Close dropdown
    siteDropdown.classList.add('hidden');
    siteSearchInput.value = site?.name || '';
    
    // Load matches for new site
    await loadMatches();
}

// Load matches from selected site
async function loadMatches() {
    matchesContainer.innerHTML = '<div class="p-8 text-center"><div class="loading-spinner"></div><p class="text-gray-400 mt-2">Fetching live odds...</p></div>';
    
    try {
        const response = await fetch('/api/matches', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ site: currentSite, sport: 'football' })
        });
        
        const data = await response.json();
        
        if (data.error) {
            matchesContainer.innerHTML = `<div class="p-8 text-center text-red-400">Error: ${data.error}</div>`;
            return;
        }
        
        currentMatches = data.matches;
        matchesCountDisplay.textContent = currentMatches.length;
        matchesCount.textContent = `${currentMatches.length} matches`;
        
        const liveStatus = data.is_live_data ? 'LIVE ODDS' : 'Sample Data';
        const liveIcon = data.is_live_data ? '🟢' : '🟡';
        matchesSourceText.innerHTML = `${data.site_name} ${data.site_flag} • ${liveIcon} ${liveStatus}`;
        
        renderMatches(currentMatches);
        
        // Auto-analyze all matches
        await analyzeAllMatches();
        
    } catch (error) {
        console.error('Error loading matches:', error);
        matchesContainer.innerHTML = `<div class="p-8 text-center text-red-400">Failed to load matches: ${error.message}</div>`;
    }
}

// Render matches
function renderMatches(matches) {
    if (!matches.length) {
        matchesContainer.innerHTML = '<div class="p-8 text-center text-gray-400">No matches available at this time</div>';
        return;
    }
    
    matchesContainer.innerHTML = matches.map(match => `
        <div class="match-card p-4 hover:bg-gray-700/50" onclick="analyzeMatch(${JSON.stringify(match).replace(/"/g, '&quot;')})">
            <div class="flex justify-between items-start mb-3">
                <div>
                    <div class="font-bold text-lg">${escapeHtml(match.home_team)} vs ${escapeHtml(match.away_team)}</div>
                    <div class="text-xs text-gray-400">${escapeHtml(match.league || match.country || 'Football')}</div>
                </div>
                ${match.live ? '<div class="bg-red-600/80 text-white text-xs px-2 py-1 rounded-full live-indicator">LIVE</div>' : ''}
                ${match.sample ? '<div class="bg-yellow-600/50 text-white text-xs px-2 py-1 rounded-full">Sample</div>' : ''}
            </div>
            <div class="grid grid-cols-3 gap-2 text-center text-sm">
                ${renderMarketOdds(match.markets, '1X2', '1X2')}
                ${renderMarketOdds(match.markets, 'Over/Under', 'O/U')}
                ${renderMarketOdds(match.markets, 'GG/NG', 'GG/NG')}
            </div>
            <div class="mt-3 text-xs text-purple-400 text-center">
                🤖 Click for AI analysis →
            </div>
        </div>
    `).join('');
}

// Render market odds helper
function renderMarketOdds(markets, marketName, displayName) {
    const market = markets[marketName];
    if (!market) return `<div class="bg-gray-700 rounded p-2"><div class="text-gray-400">${displayName}</div><div class="text-xs">-</div></div>`;
    
    let oddsHtml = '';
    if (marketName === '1X2') {
        oddsHtml = `${market.Home || '-'} | ${market.Draw || '-'} | ${market.Away || '-'}`;
    } else if (marketName === 'GG/NG') {
        oddsHtml = `Y:${market.Yes || '-'} | N:${market.No || '-'}`;
    } else {
        const entries = Object.entries(market).slice(0, 2);
        oddsHtml = entries.map(([k, v]) => `${k}:${v}`).join(' | ');
    }
    
    return `<div class="bg-gray-700 rounded p-2"><div class="text-gray-400">${displayName}</div><div class="font-mono text-xs">${oddsHtml}</div></div>`;
}

// Analyze a specific match
async function analyzeMatch(match) {
    aiSelectionPanel.innerHTML = '<div class="text-center py-8"><div class="loading-spinner"></div><p class="text-gray-400 mt-2">AI analyzing odds...</p></div>';
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ match: match })
        });
        
        const data = await response.json();
        
        if (data.error) {
            aiSelectionPanel.innerHTML = `<div class="text-red-400 text-center py-8">Error: ${data.error}</div>`;
            return;
        }
        
        renderAISelection(data.analysis);
        
    } catch (error) {
        console.error('Analysis error:', error);
        aiSelectionPanel.innerHTML = `<div class="text-red-400 text-center py-8">Analysis failed</div>`;
    }
}

// Render AI selection
function renderAISelection(analysis) {
    if (!analysis.ai_selection) {
        aiSelectionPanel.innerHTML = `
            <div class="text-center py-6">
                <div class="text-yellow-400 mb-2">⚠️ No significant value bets found</div>
                <div class="text-sm text-gray-400">Try other markets or wait for odds movement</div>
            </div>
        `;
        return;
    }
    
    const bet = analysis.ai_selection;
    
    aiSelectionPanel.innerHTML = `
        <div class="space-y-4">
            <div class="text-center">
                <div class="text-gray-400 text-sm">${analysis.match}</div>
                <div class="text-2xl font-bold text-green-400 mt-1">${bet.outcome}</div>
                <div class="text-3xl font-bold my-2">${bet.odds}</div>
                <div class="inline-block px-3 py-1 rounded-full text-sm ${bet.value_edge > 10 ? 'bg-green-600' : bet.value_edge > 5 ? 'bg-yellow-600' : 'bg-blue-600'}">
                    ${bet.value_edge > 0 ? '+' : ''}${bet.value_edge}% Edge
                </div>
            </div>
            <div class="grid grid-cols-2 gap-3 text-sm">
                <div class="bg-gray-700 rounded p-2 text-center">
                    <div class="text-gray-400">Market</div>
                    <div class="font-semibold">${bet.market}</div>
                </div>
                <div class="bg-gray-700 rounded p-2 text-center">
                    <div class="text-gray-400">Confidence</div>
                    <div class="font-semibold text-yellow-400">${bet.confidence}%</div>
                </div>
                <div class="bg-gray-700 rounded p-2 text-center">
                    <div class="text-gray-400">True Probability</div>
                    <div>${bet.true_probability}%</div>
                </div>
                <div class="bg-gray-700 rounded p-2 text-center">
                    <div class="text-gray-400">Suggested Stake</div>
                    <div class="font-mono">KES ${bet.suggested_stake}</div>
                </div>
            </div>
            <div class="text-xs text-gray-400 text-center p-2 bg-gray-700 rounded">
                ${bet.recommendation}
            </div>
            ${analysis.all_value_bets.length > 1 ? `
                <div class="border-t border-gray-700 pt-3 mt-2">
                    <div class="text-xs text-gray-400 mb-2">📊 Other opportunities:</div>
                    <div class="space-y-1">
                        ${analysis.all_value_bets.slice(1, 4).map(b => `
                            <div class="flex justify-between text-xs">
                                <span>${b.market} - ${b.outcome}</span>
                                <span class="${b.value_edge > 0 ? 'text-green-400' : 'text-red-400'}">${b.value_edge > 0 ? '+' : ''}${b.value_edge}%</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

// Analyze all matches
async function analyzeAllMatches() {
    if (!currentMatches.length) return;
    
    globalResults.classList.remove('hidden');
    globalResultsContainer.innerHTML = '<div class="text-center py-8"><div class="loading-spinner"></div><p class="text-gray-400 mt-2">AI scanning all matches...</p></div>';
    
    try {
        const siteName = supportedSites.find(s => s.id === currentSite)?.name || currentSite;
        
        const response = await fetch('/api/analyze-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                matches: currentMatches,
                site_name: siteName
            })
        });
        
        const data = await response.json();
        
        valueBetsCount.textContent = data.total_value_bets || 0;
        
        if (data.top_bets && data.top_bets.length) {
            globalResultsContainer.innerHTML = `
                <div class="grid grid-cols-1 gap-3">
                    ${data.top_bets.map((bet, idx) => `
                        <div class="bg-gray-700 rounded-lg p-3">
                            <div class="flex justify-between items-start">
                                <div>
                                    <div class="font-semibold text-sm">${bet.match_name}</div>
                                    <div class="text-xs text-gray-400">${bet.market} - ${bet.outcome}</div>
                                    <div class="text-lg font-bold text-green-400 mt-1">${bet.odds}</div>
                                </div>
                                <div class="text-right">
                                    <div class="text-2xl font-bold ${bet.value_edge > 0 ? 'text-green-400' : 'text-red-400'}">
                                        ${bet.value_edge > 0 ? '+' : ''}${bet.value_edge}%
                                    </div>
                                    <div class="text-xs text-gray-400">Edge</div>
                                </div>
                            </div>
                            <div class="mt-2 text-xs text-gray-400">${bet.recommendation}</div>
                        </div>
                    `).join('')}
                </div>
                <div class="mt-4 text-xs text-center text-gray-500">
                    Based on ${data.total_matches} matches from ${data.site}
                </div>
            `;
        } else {
            globalResultsContainer.innerHTML = '<div class="text-center py-8 text-gray-400">No value bets found in current matches</div>';
        }
        
    } catch (error) {
        console.error('Error analyzing all matches:', error);
        globalResultsContainer.innerHTML = '<div class="text-center py-8 text-red-400">Analysis failed</div>';
    }
}

// Manual prediction
manualPredictBtn.addEventListener('click', async () => {
    const homeTeam = manualHomeTeam.value || 'Home';
    const awayTeam = manualAwayTeam.value || 'Away';
    const market = manualMarket.value;
    const outcome = manualOutcome.value;
    const odds = parseFloat(manualOdds.value);
    
    if (!outcome) {
        alert('Please enter outcome');
        return;
    }
    
    if (!odds || odds < 1.01) {
        alert('Please enter valid odds');
        return;
    }
    
    manualResult.classList.remove('hidden');
    manualResult.innerHTML = '<div class="loading-spinner" style="width:20px;height:20px"></div><p class="text-xs mt-1">AI analyzing...</p>';
    
    try {
        const response = await fetch('/api/custom-predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                home_team: homeTeam,
                away_team: awayTeam,
                market: market,
                outcome: outcome,
                odds: odds
            })
        });
        
        const data = await response.json();
        
        manualResult.innerHTML = `
            <div class="space-y-2">
                <div class="font-bold text-sm">${data.ai_prediction}</div>
                <div class="grid grid-cols-2 gap-2 text-xs">
                    <div>Implied Prob:</div>
                    <div class="font-mono">${data.implied_probability}%</div>
                    <div>AI True Prob:</div>
                    <div class="font-mono ${data.value_edge > 5 ? 'text-green-400' : 'text-yellow-400'}">${data.true_probability}%</div>
                    <div>Value Edge:</div>
                    <div class="font-mono ${data.value_edge > 5 ? 'text-green-400' : 'text-yellow-400'}">${data.value_edge > 0 ? '+' : ''}${data.value_edge}%</div>
                    <div>Confidence:</div>
                    <div class="font-mono">${data.confidence}%</div>
                </div>
                ${data.suggested_stake > 0 ? `<div class="text-xs text-green-400">Suggested stake: KES ${data.suggested_stake}</div>` : ''}
                <div class="text-xs text-gray-400">${data.recommendation}</div>
            </div>
        `;
        
    } catch (error) {
        manualResult.innerHTML = `<div class="text-red-400 text-xs">Error: ${error.message}</div>`;
    }
});

// Setup event listeners
function setupEventListeners() {
    // Dropdown toggle
    siteSearchInput.addEventListener('click', () => {
        siteDropdown.classList.toggle('hidden');
    });
    
    // Filter dropdown items on search
    siteSearchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const filtered = supportedSites.filter(site => 
            site.name.toLowerCase().includes(query) || 
            site.country.toLowerCase().includes(query)
        );
        renderDropdown(filtered);
        siteDropdown.classList.remove('hidden');
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!siteSearchInput.contains(e.target) && !siteDropdown.contains(e.target)) {
            siteDropdown.classList.add('hidden');
        }
    });
    
    // Refresh button
    refreshBtn.addEventListener('click', loadMatches);
    
    // Analyze all button
    analyzeAllBtn.addEventListener('click', analyzeAllMatches);
}

// Helper: Escape HTML
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// Make functions globally available
window.selectSite = selectSite;
window.analyzeMatch = analyzeMatch;

// Start the app
init();
