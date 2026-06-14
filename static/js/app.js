let currentSite = 'sportybet';
let currentMatches = [];
let supportedSites = [];

const siteSearchInput = document.getElementById('siteSearchInput');
const siteGrid = document.getElementById('siteGrid');
const selectedSiteDisplay = document.getElementById('selectedSiteDisplay');
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

const manualHomeTeam = document.getElementById('manualHomeTeam');
const manualAwayTeam = document.getElementById('manualAwayTeam');
const manualMarket = document.getElementById('manualMarket');
const manualOutcome = document.getElementById('manualOutcome');
const manualOdds = document.getElementById('manualOdds');
const manualPredictBtn = document.getElementById('manualPredictBtn');
const manualResult = document.getElementById('manualResult');

const siteGradients = {
    sportybet: 'gradient-sporty',
    bet9ja: 'gradient-bet9ja',
    '22bet': 'gradient-purple',
    paripesa: 'gradient-green',
    nairabet: 'gradient-purple',
    betking: 'gradient-green'
};

async function init() {
    setupEventListeners();
    await checkAPIStatus();
    await loadSupportedSites();
    await loadMatches();
}

async function checkAPIStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        if (data.live_feeds_active) {
            apiStatusBadge.innerHTML = '<span class="w-2 h-2 bg-green-500 rounded-full live-indicator"></span> Live Feeds Active';
            apiStatusBadge.className = 'status-pill gradient-green';
        } else if (!data.live_feeds_enabled) {
            apiStatusBadge.innerHTML = '<span class="w-2 h-2 bg-yellow-500 rounded-full"></span> Demo Mode';
            apiStatusBadge.className = 'status-pill bg-gray-800';
        } else if (data.oddsafrica_api_available) {
            apiStatusBadge.innerHTML = '<span class="w-2 h-2 bg-yellow-500 rounded-full"></span> Live Feeds Disabled';
            apiStatusBadge.className = 'status-pill bg-gray-800';
        } else {
            apiStatusBadge.innerHTML = '<span class="w-2 h-2 bg-red-500 rounded-full"></span> API Not Installed';
            apiStatusBadge.className = 'status-pill bg-gray-800';
        }
    } catch (error) {
        console.error('Status check failed:', error);
        apiStatusBadge.innerHTML = '<span class="w-2 h-2 bg-red-500 rounded-full"></span> Server Error';
    }
}

async function loadSupportedSites() {
    try {
        const response = await fetch('/api/sites');
        const data = await response.json();
        supportedSites = data.sites || [];
        renderSites(supportedSites);
        updateSelectedSiteDisplay();
    } catch (error) {
        console.error('Error loading sites:', error);
        siteGrid.innerHTML = '<div class="text-sm text-red-300">Could not load betting sites.</div>';
    }
}

function renderSites(sites) {
    if (!siteGrid) return;

    if (!sites.length) {
        siteGrid.innerHTML = '<div class="text-sm text-gray-400">No matching sites found.</div>';
        return;
    }

    siteGrid.innerHTML = sites.map(site => `
        <button type="button" onclick="selectSite('${site.id}')"
            class="site-card ${site.id === currentSite ? 'active' : ''}">
            <span>
                <span class="site-card-name">${escapeHtml(site.name)}</span>
                <span class="site-card-country">${escapeHtml(site.country)}</span>
            </span>
            ${site.is_default ? '<span class="site-card-badge">Default</span>' : ''}
        </button>
    `).join('');
}

async function selectSite(siteId) {
    currentSite = siteId;
    const site = supportedSites.find(item => item.id === siteId);
    siteSearchInput.value = site?.name || '';
    updateSelectedSiteDisplay();
    renderSites(supportedSites);
    await loadMatches();
}

function updateSelectedSiteDisplay() {
    const site = supportedSites.find(item => item.id === currentSite) || {
        id: 'sportybet',
        name: 'SportyBet',
        is_default: true,
        live_feed: false
    };

    const gradientClass = siteGradients[site.id] || 'gradient-purple';
    selectedSiteDisplay.className = `selected-site mt-5 ${gradientClass}`;
    selectedSiteDisplay.innerHTML = `
        <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
            <div>
                <span class="font-bold">${escapeHtml(site.name)}</span>
                ${site.is_default ? '<span class="text-xs ml-2 opacity-80">Default</span>' : ''}
            </div>
            <div class="flex items-center gap-2">
                <span class="w-2 h-2 bg-green-500 rounded-full live-indicator"></span>
                <span class="text-sm">${site.live_feed ? 'Ready' : 'Demo Mode'}</span>
            </div>
        </div>
    `;
    siteInfoText.textContent = `${site.name} selected.`;
}

async function loadMatches() {
    matchesContainer.innerHTML = '<div class="p-8 text-center"><div class="loading-spinner"></div><p class="text-gray-400 mt-2">Fetching odds...</p></div>';

    try {
        const response = await fetch('/api/matches', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ site: currentSite, sport: 'football' })
        });
        const data = await response.json();

        if (data.error) {
            matchesContainer.innerHTML = `<div class="p-8 text-center text-red-300">Error: ${escapeHtml(data.error)}</div>`;
            return;
        }

        currentMatches = data.matches || [];
        matchesCountDisplay.textContent = currentMatches.length;
        matchesCount.textContent = `${currentMatches.length} matches`;
        matchesSourceText.textContent = `${data.site_name} - ${data.is_live_data ? 'Live odds' : 'Sample data'}`;

        renderMatches(currentMatches);
        await analyzeAllMatches();
    } catch (error) {
        console.error('Error loading matches:', error);
        matchesContainer.innerHTML = `<div class="p-8 text-center text-red-300">Failed to load matches: ${escapeHtml(error.message)}</div>`;
    }
}

function renderMatches(matches) {
    if (!matches.length) {
        matchesContainer.innerHTML = '<div class="p-8 text-center text-gray-400">No matches available at this time.</div>';
        return;
    }

    matchesContainer.innerHTML = matches.map(match => `
        <button type="button" class="match-card block w-full text-left p-4 hover:bg-gray-800/80"
            onclick="analyzeMatch(${encodeForInlineJson(match)})">
            <div class="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2 mb-3">
                <div>
                    <div class="font-bold text-lg">${escapeHtml(match.home_team)} vs ${escapeHtml(match.away_team)}</div>
                    <div class="text-xs text-gray-400">${escapeHtml(match.league || match.country || 'Football')}</div>
                </div>
                <div class="flex gap-2">
                    ${match.live ? '<span class="bg-red-600/80 text-white text-xs px-2 py-1 rounded-full live-indicator">LIVE</span>' : ''}
                    ${match.sample ? '<span class="bg-yellow-600/60 text-white text-xs px-2 py-1 rounded-full">Sample</span>' : ''}
                </div>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-2 text-center text-sm">
                ${renderMarketOdds(match.markets, '1X2', '1X2')}
                ${renderMarketOdds(match.markets, 'Over/Under', 'O/U')}
                ${renderMarketOdds(match.markets, 'GG/NG', 'GG/NG')}
            </div>
            <div class="mt-3 text-xs text-purple-300 text-center">Click for AI analysis</div>
        </button>
    `).join('');
}

function renderMarketOdds(markets, marketName, displayName) {
    const market = markets?.[marketName];
    if (!market) {
        return `<div class="bg-gray-800 rounded p-2"><div class="text-gray-400">${displayName}</div><div class="text-xs">-</div></div>`;
    }

    let oddsHtml = '';
    if (marketName === '1X2') {
        oddsHtml = `${market.Home || '-'} | ${market.Draw || '-'} | ${market.Away || '-'}`;
    } else if (marketName === 'GG/NG') {
        oddsHtml = `Y:${market.Yes || '-'} | N:${market.No || '-'}`;
    } else {
        oddsHtml = Object.entries(market).slice(0, 2).map(([key, value]) => `${key}:${value}`).join(' | ');
    }

    return `<div class="bg-gray-800 rounded p-2"><div class="text-gray-400">${displayName}</div><div class="font-mono text-xs">${escapeHtml(oddsHtml)}</div></div>`;
}

async function analyzeMatch(match) {
    aiSelectionPanel.innerHTML = '<div class="text-center py-8"><div class="loading-spinner"></div><p class="text-gray-400 mt-2">AI analyzing odds...</p></div>';

    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ match })
        });
        const data = await response.json();

        if (data.error) {
            aiSelectionPanel.innerHTML = `<div class="text-red-300 text-center py-8">Error: ${escapeHtml(data.error)}</div>`;
            return;
        }

        renderAISelection(data.analysis);
    } catch (error) {
        console.error('Analysis error:', error);
        aiSelectionPanel.innerHTML = '<div class="text-red-300 text-center py-8">Analysis failed.</div>';
    }
}

function renderAISelection(analysis) {
    if (!analysis.ai_selection) {
        aiSelectionPanel.innerHTML = `
            <div class="text-center py-6">
                <div class="text-yellow-300 mb-2">No significant value bets found</div>
                <div class="text-sm text-gray-400">Try another match or enter odds manually.</div>
            </div>
        `;
        return;
    }

    const bet = analysis.ai_selection;
    aiSelectionPanel.innerHTML = `
        <div class="space-y-4">
            <div class="text-center">
                <div class="text-gray-400 text-sm">${escapeHtml(analysis.match)}</div>
                <div class="text-2xl font-bold text-green-300 mt-1">${escapeHtml(bet.outcome)}</div>
                <div class="text-3xl font-bold my-2">${bet.odds}</div>
                <div class="inline-block px-3 py-1 rounded-full text-sm ${bet.value_edge > 10 ? 'bg-green-600' : bet.value_edge > 5 ? 'bg-yellow-600' : 'bg-blue-600'}">
                    ${bet.value_edge > 0 ? '+' : ''}${bet.value_edge}% Edge
                </div>
            </div>
            <div class="grid grid-cols-2 gap-3 text-sm">
                ${metricBox('Market', bet.market)}
                ${metricBox('Confidence', `${bet.confidence}%`, 'text-yellow-300')}
                ${metricBox('True Probability', `${bet.true_probability}%`)}
                ${metricBox('Suggested Stake', `KES ${bet.suggested_stake}`)}
            </div>
            <div class="text-xs text-gray-400 text-center p-2 bg-gray-800 rounded">${escapeHtml(bet.recommendation)}</div>
            ${renderOtherBets(analysis.all_value_bets)}
        </div>
    `;
}

function metricBox(label, value, valueClass = '') {
    return `
        <div class="bg-gray-800 rounded p-2 text-center">
            <div class="text-gray-400">${label}</div>
            <div class="font-semibold ${valueClass}">${escapeHtml(String(value))}</div>
        </div>
    `;
}

function renderOtherBets(bets = []) {
    if (bets.length <= 1) return '';

    return `
        <div class="border-t border-gray-800 pt-3 mt-2">
            <div class="text-xs text-gray-400 mb-2">Other opportunities</div>
            <div class="space-y-1">
                ${bets.slice(1, 4).map(bet => `
                    <div class="flex justify-between gap-3 text-xs">
                        <span>${escapeHtml(bet.market)} - ${escapeHtml(bet.outcome)}</span>
                        <span class="${bet.value_edge > 0 ? 'text-green-300' : 'text-red-300'}">${bet.value_edge > 0 ? '+' : ''}${bet.value_edge}%</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

async function analyzeAllMatches() {
    if (!currentMatches.length) return;

    globalResults.classList.remove('hidden');
    globalResultsContainer.innerHTML = '<div class="text-center py-8"><div class="loading-spinner"></div><p class="text-gray-400 mt-2">AI scanning matches...</p></div>';

    try {
        const siteName = supportedSites.find(site => site.id === currentSite)?.name || currentSite;
        const response = await fetch('/api/analyze-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ matches: currentMatches, site_name: siteName })
        });
        const data = await response.json();

        valueBetsCount.textContent = data.total_value_bets || 0;

        if (data.top_bets && data.top_bets.length) {
            globalResultsContainer.innerHTML = `
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
                    ${data.top_bets.map(bet => `
                        <div class="bg-gray-800 rounded-lg p-3 border border-white/5">
                            <div class="flex justify-between items-start gap-3">
                                <div>
                                    <div class="font-semibold text-sm">${escapeHtml(bet.match_name)}</div>
                                    <div class="text-xs text-gray-400">${escapeHtml(bet.market)} - ${escapeHtml(bet.outcome)}</div>
                                    <div class="text-lg font-bold text-green-300 mt-1">${bet.odds}</div>
                                </div>
                                <div class="text-right">
                                    <div class="text-2xl font-bold ${bet.value_edge > 0 ? 'text-green-300' : 'text-red-300'}">
                                        ${bet.value_edge > 0 ? '+' : ''}${bet.value_edge}%
                                    </div>
                                    <div class="text-xs text-gray-400">Edge</div>
                                </div>
                            </div>
                            <div class="mt-2 text-xs text-gray-400">${escapeHtml(bet.recommendation)}</div>
                        </div>
                    `).join('')}
                </div>
                <div class="mt-4 text-xs text-center text-gray-500">Based on ${data.total_matches} matches from ${escapeHtml(data.site)}</div>
            `;
        } else {
            globalResultsContainer.innerHTML = '<div class="text-center py-8 text-gray-400">No value bets found in current matches.</div>';
        }
    } catch (error) {
        console.error('Error analyzing all matches:', error);
        globalResultsContainer.innerHTML = '<div class="text-center py-8 text-red-300">Analysis failed.</div>';
    }
}

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
            body: JSON.stringify({ home_team: homeTeam, away_team: awayTeam, market, outcome, odds })
        });
        const data = await response.json();

        manualResult.innerHTML = `
            <div class="space-y-2">
                <div class="font-bold text-sm">${escapeHtml(data.ai_prediction)}</div>
                <div class="grid grid-cols-2 gap-2 text-xs">
                    <div>Implied Prob:</div><div class="font-mono">${data.implied_probability}%</div>
                    <div>AI True Prob:</div><div class="font-mono">${data.true_probability}%</div>
                    <div>Value Edge:</div><div class="font-mono">${data.value_edge > 0 ? '+' : ''}${data.value_edge}%</div>
                    <div>Confidence:</div><div class="font-mono">${data.confidence}%</div>
                </div>
                ${data.suggested_stake > 0 ? `<div class="text-xs text-green-300">Suggested stake: KES ${data.suggested_stake}</div>` : ''}
                <div class="text-xs text-gray-400">${escapeHtml(data.recommendation)}</div>
            </div>
        `;
    } catch (error) {
        manualResult.innerHTML = `<div class="text-red-300 text-xs">Error: ${escapeHtml(error.message)}</div>`;
    }
});

function setupEventListeners() {
    siteSearchInput.addEventListener('input', event => {
        const query = event.target.value.toLowerCase().trim();
        const filtered = supportedSites.filter(site =>
            site.name.toLowerCase().includes(query) ||
            site.country.toLowerCase().includes(query)
        );
        renderSites(filtered);
    });

    refreshBtn.addEventListener('click', loadMatches);
    analyzeAllBtn.addEventListener('click', analyzeAllMatches);
}

function encodeForInlineJson(value) {
    return JSON.stringify(value).replace(/"/g, '&quot;');
}

function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value).replace(/[&<>"']/g, char => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    }[char]));
}

window.selectSite = selectSite;
window.analyzeMatch = analyzeMatch;

init();
