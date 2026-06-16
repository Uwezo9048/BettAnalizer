/**
 * BetAnalyzer - Main Application
 * Handles UI interactions, API calls, and real-time updates
 */

// ============================================
// State Management
// ============================================

const AppState = {
    currentSite: 'sportybet',
    currentSport: 'football',
    currentLeague: null,
    matches: [],
    valueBets: [],
    isLoading: false,
    autoRefresh: false,
    refreshInterval: null,
    selectedMatch: null
};

// ============================================
// DOM References
// ============================================

const DOM = {
    // Selectors
    siteSelect: document.getElementById('site-select'),
    sportSelect: document.getElementById('sport-select'),
    leagueSelect: document.getElementById('league-select'),
    
    // Buttons
    refreshBtn: document.getElementById('refresh-btn'),
    analyzeAllBtn: document.getElementById('analyze-all-btn'),
    autoRefreshToggle: document.getElementById('auto-refresh-toggle'),
    
    // Containers
    matchesContainer: document.getElementById('matches-container'),
    statsContainer: document.getElementById('stats-container'),
    aiSelectionContainer: document.getElementById('ai-selection-container'),
    analysisResults: document.getElementById('analysis-results'),
    
    // Status
    liveStatus: document.getElementById('live-status'),
    statusDot: document.getElementById('status-dot'),
    matchCount: document.getElementById('match-count'),
    valueBetCount: document.getElementById('value-bet-count'),
    liveCount: document.getElementById('live-count'),
    upcomingCount: document.getElementById('upcoming-count'),
    valueBadge: document.getElementById('value-badge'),
    matchBadge: document.getElementById('match-badge'),
    
    // Manual Entry
    manualHome: document.getElementById('manual-home'),
    manualAway: document.getElementById('manual-away'),
    manualMarket: document.getElementById('manual-market'),
    manualOutcome: document.getElementById('manual-outcome'),
    manualOdds: document.getElementById('manual-odds'),
    manualPredictBtn: document.getElementById('manual-predict-btn'),
    manualResults: document.getElementById('manual-results'),
    
    // Betslip
    slipInput: document.getElementById('slip-input'),
    slipAnalyzeBtn: document.getElementById('slip-analyze-btn'),
    slipClearBtn: document.getElementById('slip-clear-btn'),
    slipResults: document.getElementById('slip-results'),
    
    // Toast
    toast: document.getElementById('toast'),
    
    // Loading
    loadingOverlay: document.getElementById('loading-overlay')
};

// ============================================
// Toast Notifications
// ============================================

function showToast(message, type = 'info', title = '') {
    const toast = DOM.toast;
    if (!toast) return;
    
    toast.className = 'toast';
    toast.classList.add(type);
    
    const titleEl = toast.querySelector('.toast-title');
    const msgEl = toast.querySelector('.toast-message');
    
    if (titleEl) titleEl.textContent = title || type.toUpperCase();
    if (msgEl) msgEl.textContent = message;
    
    toast.classList.add('show');
    
    clearTimeout(toast._hideTimeout);
    toast._hideTimeout = setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
}

// ============================================
// Loading State
// ============================================

function setLoading(isLoading) {
    AppState.isLoading = isLoading;
    if (DOM.loadingOverlay) {
        DOM.loadingOverlay.style.display = isLoading ? 'flex' : 'none';
    }
    if (DOM.refreshBtn) {
        DOM.refreshBtn.disabled = isLoading;
        DOM.refreshBtn.textContent = isLoading ? '⏳ Loading...' : '🔄 Refresh Odds';
    }
}

// ============================================
// Filter Functions
// ============================================

function getMatchStatus(match) {
    if (!match.status) {
        if (match.start_time) {
            try {
                const start = new Date(match.start_time);
                const now = new Date();
                const diff = start - now;
                if (diff < 0 && diff > -7200000) {
                    return 'Live';
                } else if (diff < 0) {
                    return 'Finished';
                } else if (diff < 3600000) {
                    return 'Live';
                } else {
                    return 'Upcoming';
                }
            } catch {
                return 'Upcoming';
            }
        }
        return 'Upcoming';
    }
    return match.status;
}

function isFinished(match) {
    const status = getMatchStatus(match);
    return status.toLowerCase() === 'finished';
}

// ============================================
// API Calls
// ============================================

async function apiFetch(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ error: 'Unknown error' }));
            throw new Error(error.error || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        showToast(error.message || 'Failed to fetch data', 'error', 'API Error');
        throw error;
    }
}

async function fetchSites() {
    try {
        const data = await apiFetch('/api/sites');
        return data.sites || [];
    } catch (error) {
        return [];
    }
}

async function fetchSports(site) {
    try {
        const data = await apiFetch(`/api/sports?site=${site}`);
        return data.sports || [];
    } catch (error) {
        return [];
    }
}

async function fetchLeagues(site, sport) {
    try {
        const data = await apiFetch(`/api/leagues?site=${site}&sport=${sport}`);
        return data.leagues || [];
    } catch (error) {
        return [];
    }
}

async function fetchMatches(site, sport, league = null) {
    try {
        setLoading(true);
        const data = await apiFetch('/api/matches', {
            method: 'POST',
            body: JSON.stringify({
                site: site,
                sport: sport,
                league: league
            })
        });
        
        AppState.matches = data.matches || [];
        return data;
    } catch (error) {
        AppState.matches = [];
        return { matches: [], count: 0 };
    } finally {
        setLoading(false);
    }
}

async function analyzeAllMatches(matches, siteName) {
    try {
        const data = await apiFetch('/api/analyze-all', {
            method: 'POST',
            body: JSON.stringify({
                matches: matches,
                site_name: siteName
            })
        });
        return data;
    } catch (error) {
        showToast('Failed to analyze matches', 'error', 'Analysis Error');
        return null;
    }
}

async function analyzeMatch(match) {
    try {
        const data = await apiFetch('/api/analyze', {
            method: 'POST',
            body: JSON.stringify({ match: match })
        });
        return data.analysis || null;
    } catch (error) {
        showToast('Failed to analyze match', 'error', 'Analysis Error');
        return null;
    }
}

async function customPredict(home, away, market, outcome, odds) {
    try {
        const data = await apiFetch('/api/custom-predict', {
            method: 'POST',
            body: JSON.stringify({
                home_team: home,
                away_team: away,
                market: market,
                outcome: outcome,
                odds: parseFloat(odds)
            })
        });
        return data;
    } catch (error) {
        showToast('Prediction failed', 'error', 'Error');
        return null;
    }
}

async function analyzeSlip(text) {
    try {
        const formData = new FormData();
        formData.append('slip_text', text);
        
        const response = await fetch('/api/analyze-slip', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Slip analysis failed');
        }
        
        return await response.json();
    } catch (error) {
        showToast(error.message, 'error', 'Slip Analysis Error');
        return null;
    }
}

// ============================================
// UI Rendering
// ============================================

function renderMatches(matches) {
    const container = DOM.matchesContainer;
    if (!container) return;
    
    const filteredMatches = matches ? matches.filter(m => !isFinished(m)) : [];
    const liveMatches = filteredMatches.filter(m => getMatchStatus(m).toLowerCase() === 'live');
    const upcomingMatches = filteredMatches.filter(m => getMatchStatus(m).toLowerCase() === 'upcoming');
    
    if (filteredMatches.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="text-align: center; padding: 60px 20px; color: #6a8aaa;">
                <div style="font-size: 48px; margin-bottom: 16px;">🎯</div>
                <div style="font-size: 20px; font-weight: 600; color: #e8edf5;">No Live or Upcoming Matches</div>
                <div style="margin-top: 8px;">All matches are finished or no matches are scheduled.</div>
                <div style="margin-top: 16px;">
                    <button class="btn btn-primary" onclick="handleRefresh()">🔄 Refresh Odds</button>
                </div>
            </div>
        `;
        return;
    }
    
    const sortedMatches = [...liveMatches, ...upcomingMatches];
    
    let html = '';
    
    if (liveMatches.length > 0) {
        html += `
            <div style="margin: 16px 0 8px 0; display: flex; align-items: center; gap: 10px;">
                <span style="background: #ff1744; width: 10px; height: 10px; border-radius: 50%; display: inline-block; animation: pulse-dot 1s infinite;"></span>
                <span style="font-weight: 600; color: #ff1744;">🔴 LIVE (${liveMatches.length})</span>
            </div>
            <div class="matches-grid">`;
        
        liveMatches.forEach(match => {
            html += renderMatchCard(match);
        });
        
        html += `</div>`;
    }
    
    if (upcomingMatches.length > 0) {
        html += `
            <div style="margin: 24px 0 8px 0; display: flex; align-items: center; gap: 10px;">
                <span style="background: #ffab00; width: 10px; height: 10px; border-radius: 50%; display: inline-block;"></span>
                <span style="font-weight: 600; color: #ffab00;">📅 UPCOMING (${upcomingMatches.length})</span>
            </div>
            <div class="matches-grid">`;
        
        upcomingMatches.forEach(match => {
            html += renderMatchCard(match);
        });
        
        html += `</div>`;
    }
    
    container.innerHTML = html;
    
    container.querySelectorAll('.analyze-match-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const matchId = parseInt(btn.dataset.matchId);
            const match = AppState.matches.find(m => m.id === matchId);
            if (match) {
                await handleMatchAnalysis(match);
            }
        });
    });
    
    renderStats(filteredMatches, liveMatches, upcomingMatches);
}

function renderMatchCard(match) {
    const status = getMatchStatus(match);
    const statusClass = status.toLowerCase();
    const competitionType = match.competition_type || 'Domestic League';
    const compClass = competitionType.toLowerCase().replace(/[^a-z0-9-]/g, '-');
    const startTime = match.start_time ? formatDate(match.start_time) : 'Date TBD';
    
    let marketsHtml = '';
    if (match.markets) {
        for (const [marketName, outcomes] of Object.entries(match.markets)) {
            if (typeof outcomes === 'object' && outcomes !== null) {
                const oddsHtml = Object.entries(outcomes)
                    .filter(([_, value]) => value > 0)
                    .map(([label, value]) => `
                        <div class="odd-item">
                            <span class="label">${label}</span>
                            <span class="value">${value.toFixed(2)}</span>
                        </div>
                    `).join('');
                
                if (oddsHtml) {
                    marketsHtml += `
                        <div class="market">
                            <div class="market-name">${marketName}</div>
                            <div class="odds">${oddsHtml}</div>
                        </div>
                    `;
                }
            }
        }
    }
    
    return `
        <div class="match-card" data-match-id="${match.id}">
            <span class="status-badge ${statusClass}">${status}</span>
            
            <div class="match-header">
                <div class="match-teams">
                    ${match.home_team} <span class="vs">vs</span> ${match.away_team}
                </div>
            </div>
            
            <div class="match-league">
                ${match.league || 'Unknown League'}
                <span class="competition-badge competition-${compClass}">${competitionType}</span>
            </div>
            
            <div class="match-meta">
                <span class="status">
                    <span class="dot ${statusClass}"></span>
                    ${status}
                </span>
                <span class="date-time">📅 ${startTime}</span>
            </div>
            
            ${marketsHtml ? `<div class="markets">${marketsHtml}</div>` : ''}
            
            <div class="match-actions">
                <button class="btn btn-primary analyze-match-btn" data-match-id="${match.id}">
                    🤖 AI Analysis
                </button>
            </div>
        </div>
    `;
}

function renderStats(matches, liveMatches, upcomingMatches) {
    const total = matches?.length || 0;
    const live = liveMatches?.length || 0;
    const upcoming = upcomingMatches?.length || 0;
    
    if (DOM.matchCount) DOM.matchCount.textContent = total;
    if (DOM.valueBetCount) DOM.valueBetCount.textContent = total;
    if (DOM.liveCount) DOM.liveCount.textContent = live;
    if (DOM.upcomingCount) DOM.upcomingCount.textContent = upcoming;
    if (DOM.valueBadge) DOM.valueBadge.textContent = total;
    if (DOM.matchBadge) DOM.matchBadge.textContent = `${total} matches (${live} live)`;
}

function renderAISelection(analysis) {
    const container = DOM.aiSelectionContainer;
    if (!container) return;
    
    if (!analysis || !analysis.ai_selection) {
        container.innerHTML = `
            <div class="title">
                <span class="ai-icon">🧠</span>
                AI Selection
            </div>
            <div class="content">
                Select a match and click <span class="highlight">"AI Analysis"</span> to see the best value bet.
            </div>
        `;
        return;
    }
    
    const bet = analysis.ai_selection;
    container.innerHTML = `
        <div class="title">
            <span class="ai-icon">🧠</span>
            AI Selection
        </div>
        <div class="content" style="flex-direction: column; text-align: left; align-items: flex-start; gap: 8px;">
            <div><span class="highlight">Match:</span> ${analysis.match}</div>
            <div><span class="highlight">Market:</span> ${bet.market}</div>
            <div><span class="highlight">Outcome:</span> ${bet.outcome}</div>
            <div><span class="highlight">Odds:</span> ${bet.odds}</div>
            <div><span class="highlight">Value Edge:</span> <span class="${bet.value_edge > 5 ? 'text-success' : 'text-warning'}">${bet.value_edge}%</span></div>
            <div><span class="highlight">Confidence:</span> ${bet.confidence}%</div>
            <div><span class="highlight">Suggested Stake:</span> $${bet.suggested_stake}</div>
            <div><span class="highlight">Recommendation:</span> ${bet.recommendation}</div>
        </div>
    `;
}

function renderAnalysisResults(analysis) {
    const container = DOM.analysisResults;
    if (!container) return;
    
    if (!analysis) {
        container.classList.remove('visible');
        return;
    }
    
    container.classList.add('visible');
    
    let html = `
        <h3>🔍 Analysis: ${analysis.match}</h3>
        <div class="result-item">
            <span class="key">Total Markets</span>
            <span class="value">${analysis.total_markets}</span>
        </div>
        <div class="result-item">
            <span class="key">Value Bets Found</span>
            <span class="value positive">${analysis.value_bets_count}</span>
        </div>
    `;
    
    if (analysis.ai_selection) {
        const bet = analysis.ai_selection;
        html += `
            <div class="result-item" style="border-top: 2px solid #2a3a5a; margin-top: 8px; padding-top: 12px;">
                <span class="key">🏆 Best Bet</span>
                <span class="value positive">${bet.outcome} @ ${bet.odds}</span>
            </div>
            <div class="result-item">
                <span class="key">Value Edge</span>
                <span class="value ${bet.value_edge > 5 ? 'positive' : 'neutral'}">${bet.value_edge}%</span>
            </div>
            <div class="result-item">
                <span class="key">Confidence</span>
                <span class="value">${bet.confidence}%</span>
            </div>
            <div class="result-item">
                <span class="key">Suggested Stake</span>
                <span class="value">$${bet.suggested_stake}</span>
            </div>
            <div class="result-item">
                <span class="key">Recommendation</span>
                <span class="value ${bet.value_edge > 5 ? 'positive' : 'neutral'}">${bet.recommendation}</span>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

// ============================================
// Betslip Results Display - Detailed
// ============================================

function displaySlipResults(result) {
    const container = DOM.slipResults;
    if (!container) return;
    
    if (!result || result.error) {
        container.innerHTML = `
            <div style="color: #ff1744; padding: 12px; text-align: center;">
                ❌ ${result?.error || 'Analysis failed'}
            </div>
        `;
        container.classList.add('visible');
        return;
    }
    
    let html = '';
    
    // OCR text if available
    if (result.ocr_text) {
        html += `
            <div style="background: #141b2b; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                <div style="color: #6a8aaa; font-size: 12px; margin-bottom: 4px;">📝 Detected Text:</div>
                <div style="color: #e8edf5; font-size: 13px; white-space: pre-wrap; font-family: monospace;">${result.ocr_text}</div>
            </div>
        `;
    }
    
    // Stats cards
    if (result.total_selections) {
        html += `
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; margin-bottom: 12px;">
                <div style="background: #141b2b; padding: 10px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 20px; font-weight: 700; color: #e8edf5;">${result.total_selections}</div>
                    <div style="font-size: 11px; color: #6a8aaa;">Total</div>
                </div>
                <div style="background: #141b2b; padding: 10px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 20px; font-weight: 700; color: #00c853;">${result.kept_count}</div>
                    <div style="font-size: 11px; color: #6a8aaa;">Kept ✅</div>
                </div>
                <div style="background: #141b2b; padding: 10px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 20px; font-weight: 700; color: #ff1744;">${result.removed_count}</div>
                    <div style="font-size: 11px; color: #6a8aaa;">Removed ❌</div>
                </div>
                <div style="background: #141b2b; padding: 10px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 20px; font-weight: 700; color: #ffab00;">${result.average_confidence || 0}%</div>
                    <div style="font-size: 11px; color: #6a8aaa;">Confidence</div>
                </div>
            </div>
        `;
        
        // Kept Selections - Show in detail
        if (result.kept && result.kept.length > 0) {
            html += `
                <div style="margin-top: 12px; background: #0a1a0a; border: 1px solid #00c853; border-radius: 8px; padding: 12px;">
                    <div style="color: #00c853; font-weight: 600; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                        ✅ KEPT SELECTIONS (${result.kept.length})
                        <span style="font-size: 11px; color: #6a8aaa; font-weight: 400;">- These are good bets to keep</span>
                    </div>
                    ${result.kept.map((sel, i) => `
                        <div style="background: #0d1a0d; padding: 10px 14px; border-radius: 6px; margin-bottom: 6px; border-left: 3px solid #00c853;">
                            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                                <span style="font-weight: 500; color: #e8edf5;">${sel.match || sel.selection || 'Unknown Match'}</span>
                                <span style="color: #00c853; font-weight: 600;">${sel.odds || 'N/A'}</span>
                            </div>
                            <div style="display: flex; gap: 16px; font-size: 12px; color: #6a8aaa; margin-top: 4px; flex-wrap: wrap;">
                                <span>Market: ${sel.market || 'N/A'}</span>
                                <span>Confidence: ${sel.confidence || 0}%</span>
                                <span>Value Edge: ${sel.value_edge || 0}%</span>
                                <span>Stake: $${sel.suggested_stake || 0}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        // Removed Selections - Show in detail with reasons
        if (result.removed && result.removed.length > 0) {
            html += `
                <div style="margin-top: 12px; background: #1a0a0a; border: 1px solid #ff1744; border-radius: 8px; padding: 12px;">
                    <div style="color: #ff1744; font-weight: 600; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                        ❌ REMOVED SELECTIONS (${result.removed.length})
                        <span style="font-size: 11px; color: #6a8aaa; font-weight: 400;">- Risky bets to avoid</span>
                    </div>
                    ${result.removed.map((sel, i) => `
                        <div style="background: #1a0d0d; padding: 10px 14px; border-radius: 6px; margin-bottom: 6px; border-left: 3px solid #ff1744;">
                            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                                <span style="font-weight: 500; color: #e8edf5;">${sel.match || sel.selection || 'Unknown Match'}</span>
                                <span style="color: #ff6b6b; font-weight: 600;">${sel.odds || 'N/A'}</span>
                            </div>
                            <div style="display: flex; gap: 16px; font-size: 12px; color: #6a8aaa; margin-top: 4px; flex-wrap: wrap;">
                                <span>Market: ${sel.market || 'N/A'}</span>
                                <span>Confidence: ${sel.confidence || 0}%</span>
                                <span>Value Edge: ${sel.value_edge || 0}%</span>
                                <span style="color: #ff6b6b;">⚠️ Reason: ${sel.reason || 'Too risky'}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        // Odds comparison
        html += `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px;">
                <div style="background: #141b2b; padding: 12px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 11px; color: #6a8aaa;">Original Combined Odds</div>
                    <div style="font-size: 22px; font-weight: 700; color: #ff6b6b;">${result.original_combined_odds}</div>
                </div>
                <div style="background: #141b2b; padding: 12px; border-radius: 8px; text-align: center; border: 1px solid #00c853;">
                    <div style="font-size: 11px; color: #6a8aaa;">Suggested Combined Odds</div>
                    <div style="font-size: 22px; font-weight: 700; color: #00c853;">${result.suggested_combined_odds}</div>
                </div>
            </div>
        `;
        
        // Summary
        if (result.summary) {
            html += `
                <div style="margin-top: 12px; background: #0d1422; border: 1px solid #2a3a5a; border-radius: 8px; padding: 12px;">
                    <div style="color: #ffab00; font-weight: 600; margin-bottom: 4px;">📌 Summary</div>
                    <div style="color: #8aaccc; font-size: 14px;">${result.summary}</div>
                </div>
            `;
        }
    }
    
    container.innerHTML = html;
    container.classList.add('visible');
}

// ============================================
// Date Formatting
// ============================================

function formatDate(dateStr) {
    try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return 'Date TBD';
        
        const now = new Date();
        const diff = date - now;
        
        if (diff < 0) {
            return `📅 ${date.toLocaleDateString()} ${date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}`;
        }
        
        if (diff < 24 * 60 * 60 * 1000) {
            const hours = Math.floor(diff / (60 * 60 * 1000));
            if (hours < 1) {
                const minutes = Math.floor(diff / (60 * 1000));
                return `⏰ ${minutes}m from now`;
            }
            return `⏰ ${hours}h from now`;
        }
        
        const days = Math.floor(diff / (24 * 60 * 60 * 1000));
        if (days < 7) {
            return `📅 ${date.toLocaleDateString('en-US', {weekday: 'short'})} ${date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}`;
        }
        
        return `📅 ${date.toLocaleDateString()} ${date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}`;
    } catch {
        return 'Date TBD';
    }
}

// ============================================
// Event Handlers
// ============================================

async function handleRefresh() {
    const site = AppState.currentSite;
    const sport = AppState.currentSport;
    const league = AppState.currentLeague;
    
    try {
        const data = await fetchMatches(site, sport, league);
        renderMatches(data.matches);
        
        const live = data.matches?.filter(m => getMatchStatus(m).toLowerCase() === 'live') || [];
        const upcoming = data.matches?.filter(m => getMatchStatus(m).toLowerCase() === 'upcoming') || [];
        const total = live.length + upcoming.length;
        
        showToast(`Found ${total} live/upcoming matches`, 'success', 'Refreshed');
    } catch (error) {
        showToast('Failed to refresh matches', 'error', 'Refresh Error');
    }
}

async function handleSiteChange() {
    const site = DOM.siteSelect.value;
    AppState.currentSite = site;
    
    const sports = await fetchSports(site);
    if (DOM.sportSelect) {
        DOM.sportSelect.innerHTML = sports.map(s => 
            `<option value="${s.id}">${s.name} ${s.live_feed ? '🔴' : ''}</option>`
        ).join('');
    }
    
    const sport = AppState.currentSport;
    const leagues = await fetchLeagues(site, sport);
    if (DOM.leagueSelect) {
        DOM.leagueSelect.innerHTML = `
            <option value="">All Leagues</option>
            ${leagues.map(l => 
                `<option value="${l.key}">${l.name} (${l.region})</option>`
            ).join('')}
        `;
    }
    
    await handleRefresh();
}

async function handleSportChange() {
    const sport = DOM.sportSelect.value;
    AppState.currentSport = sport;
    
    const site = AppState.currentSite;
    const leagues = await fetchLeagues(site, sport);
    if (DOM.leagueSelect) {
        DOM.leagueSelect.innerHTML = `
            <option value="">All Leagues</option>
            ${leagues.map(l => 
                `<option value="${l.key}">${l.name} (${l.region})</option>`
            ).join('')}
        `;
    }
    
    await handleRefresh();
}

async function handleLeagueChange() {
    AppState.currentLeague = DOM.leagueSelect.value || null;
    await handleRefresh();
}

async function handleMatchAnalysis(match) {
    try {
        showToast('Analyzing match...', 'info', 'AI Analysis');
        const analysis = await analyzeMatch(match);
        if (analysis) {
            renderAISelection(analysis);
            renderAnalysisResults(analysis);
            showToast('Analysis complete!', 'success', 'AI Analysis');
        }
    } catch (error) {
        showToast('Analysis failed', 'error', 'AI Analysis');
    }
}

async function handleAnalyzeAll() {
    const matches = AppState.matches;
    if (!matches || matches.length === 0) {
        showToast('No matches to analyze', 'error', 'Analysis Error');
        return;
    }
    
    const activeMatches = matches.filter(m => !isFinished(m));
    if (activeMatches.length === 0) {
        showToast('No live or upcoming matches to analyze', 'error', 'Analysis Error');
        return;
    }
    
    try {
        setLoading(true);
        const siteName = DOM.siteSelect.options[DOM.siteSelect.selectedIndex]?.text || 'Unknown';
        const results = await analyzeAllMatches(activeMatches, siteName);
        
        if (results) {
            if (DOM.valueBetCount) DOM.valueBetCount.textContent = results.total_value_bets || 0;
            
            showToast(`Found ${results.total_value_bets} value bets!`, 'success', 'Analysis Complete');
            
            if (results.top_bets && results.top_bets.length > 0) {
                const topBet = results.top_bets[0];
                DOM.aiSelectionContainer.innerHTML = `
                    <div class="title">
                        <span class="ai-icon">🏆</span>
                        Top Value Bet
                    </div>
                    <div class="content" style="flex-direction: column; text-align: left; align-items: flex-start; gap: 8px;">
                        <div><span class="highlight">Match:</span> ${topBet.match_name}</div>
                        <div><span class="highlight">Market:</span> ${topBet.market}</div>
                        <div><span class="highlight">Outcome:</span> ${topBet.outcome}</div>
                        <div><span class="highlight">Odds:</span> ${topBet.odds}</div>
                        <div><span class="highlight">Value Edge:</span> <span class="${topBet.value_edge > 5 ? 'text-success' : 'text-warning'}">${topBet.value_edge}%</span></div>
                        <div><span class="highlight">Confidence:</span> ${topBet.confidence}%</div>
                        <div><span class="highlight">Suggested Stake:</span> $${topBet.suggested_stake}</div>
                        <div><span class="highlight">Recommendation:</span> ${topBet.recommendation}</div>
                    </div>
                `;
            }
        }
    } catch (error) {
        showToast('Failed to analyze matches', 'error', 'Analysis Error');
    } finally {
        setLoading(false);
    }
}

async function handleCustomPredict() {
    const home = DOM.manualHome?.value?.trim() || 'Home';
    const away = DOM.manualAway?.value?.trim() || 'Away';
    const market = DOM.manualMarket?.value || '1X2';
    const outcome = DOM.manualOutcome?.value?.trim() || '';
    const odds = parseFloat(DOM.manualOdds?.value);
    
    if (!outcome) {
        showToast('Please enter an outcome (e.g., Home, Draw, Away)', 'error', 'Missing Field');
        return;
    }
    
    if (isNaN(odds) || odds <= 0) {
        showToast('Please enter valid odds (e.g., 2.50)', 'error', 'Invalid Odds');
        return;
    }
    
    try {
        setLoading(true);
        const result = await customPredict(home, away, market, outcome, odds);
        
        if (result) {
            const container = DOM.manualResults;
            if (container) {
                container.innerHTML = `
                    <div class="result-item"><span class="key">Match</span><span class="value">${result.match}</span></div>
                    <div class="result-item"><span class="key">Market</span><span class="value">${result.market}</span></div>
                    <div class="result-item"><span class="key">Outcome</span><span class="value">${result.outcome}</span></div>
                    <div class="result-item"><span class="key">Odds</span><span class="value">${result.odds}</span></div>
                    <div class="result-item"><span class="key">Implied Probability</span><span class="value">${result.implied_probability}%</span></div>
                    <div class="result-item"><span class="key">True Probability</span><span class="value">${result.true_probability}%</span></div>
                    <div class="result-item"><span class="key">Value Edge</span><span class="value ${result.value_edge > 5 ? 'positive' : result.value_edge > 2 ? 'neutral' : 'negative'}">${result.value_edge}%</span></div>
                    <div class="result-item"><span class="key">Confidence</span><span class="value">${result.confidence}%</span></div>
                    <div class="result-item"><span class="key">Suggested Stake</span><span class="value">$${result.suggested_stake}</span></div>
                    <div class="result-item" style="border-top: 2px solid #2a3a5a; margin-top: 8px; padding-top: 12px;">
                        <span class="key">AI Prediction</span>
                        <span class="value">${result.ai_prediction}</span>
                    </div>
                    <div class="result-item">
                        <span class="key">Recommendation</span>
                        <span class="value ${result.value_edge > 5 ? 'positive' : result.value_edge > 2 ? 'neutral' : 'negative'}">${result.recommendation}</span>
                    </div>
                `;
                container.classList.add('visible');
            }
            showToast('Prediction complete!', 'success', 'Manual Prediction');
        }
    } catch (error) {
        showToast('Prediction failed', 'error', 'Error');
    } finally {
        setLoading(false);
    }
}

async function handleSlipAnalysis() {
    const text = DOM.slipInput?.value?.trim();
    if (!text) {
        showToast('Please paste your betslip text', 'error', 'Missing Input');
        return;
    }
    
    try {
        setLoading(true);
        const result = await analyzeSlip(text);
        if (result) {
            displaySlipResults(result);
            showToast('Betslip analysis complete!', 'success', 'Betslip Analysis');
        }
    } catch (error) {
        showToast('Betslip analysis failed', 'error', 'Error');
    } finally {
        setLoading(false);
    }
}

function clearSlip() {
    if (DOM.slipInput) DOM.slipInput.value = '';
    if (DOM.slipResults) {
        DOM.slipResults.innerHTML = '';
        DOM.slipResults.classList.remove('visible');
    }
    showToast('Cleared', 'info', 'Betslip');
}

// ============================================
// Auto-Refresh
// ============================================

function toggleAutoRefresh() {
    AppState.autoRefresh = !AppState.autoRefresh;
    
    if (AppState.autoRefresh) {
        if (DOM.autoRefreshToggle) {
            DOM.autoRefreshToggle.textContent = '⏸️ Auto-Refresh On';
            DOM.autoRefreshToggle.classList.add('btn-success');
        }
        AppState.refreshInterval = setInterval(handleRefresh, 60000);
        showToast('Auto-refresh enabled (every 60s)', 'info', 'Auto-Refresh');
    } else {
        if (DOM.autoRefreshToggle) {
            DOM.autoRefreshToggle.textContent = '▶️ Auto-Refresh Off';
            DOM.autoRefreshToggle.classList.remove('btn-success');
        }
        clearInterval(AppState.refreshInterval);
        showToast('Auto-refresh disabled', 'info', 'Auto-Refresh');
    }
}

// ============================================
// Betslip Tab Switching
// ============================================

function initBetslipTabs() {
    const tabs = document.querySelectorAll('.slip-tab');
    if (!tabs.length) return;
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            tabs.forEach(t => {
                t.classList.remove('active', 'btn-primary');
                t.classList.add('btn-secondary');
            });
            this.classList.add('active', 'btn-primary');
            this.classList.remove('btn-secondary');
            
            const tabName = this.dataset.tab;
            document.querySelectorAll('.slip-tab-content').forEach(content => {
                content.style.display = 'none';
            });
            const target = document.getElementById(`slip-${tabName}-tab`);
            if (target) target.style.display = 'block';
        });
    });
}

// ============================================
// Initialization
// ============================================

async function init() {
    // Load sites
    const sites = await fetchSites();
    if (DOM.siteSelect) {
        DOM.siteSelect.innerHTML = sites.map(s => 
            `<option value="${s.id}" ${s.is_default ? 'selected' : ''}>${s.flag} ${s.name}</option>`
        ).join('');
    }
    
    // Load sports
    const sports = await fetchSports(AppState.currentSite);
    if (DOM.sportSelect) {
        DOM.sportSelect.innerHTML = sports.map(s => 
            `<option value="${s.id}" ${s.id === 'football' ? 'selected' : ''}>${s.icon} ${s.name}</option>`
        ).join('');
    }
    
    // Load leagues
    const leagues = await fetchLeagues(AppState.currentSite, AppState.currentSport);
    if (DOM.leagueSelect) {
        DOM.leagueSelect.innerHTML = `
            <option value="">All Leagues</option>
            ${leagues.map(l => 
                `<option value="${l.key}">${l.name} (${l.region})</option>`
            ).join('')}
        `;
    }
    
    // Set up event listeners
    DOM.siteSelect?.addEventListener('change', handleSiteChange);
    DOM.sportSelect?.addEventListener('change', handleSportChange);
    DOM.leagueSelect?.addEventListener('change', handleLeagueChange);
    DOM.refreshBtn?.addEventListener('click', handleRefresh);
    DOM.analyzeAllBtn?.addEventListener('click', handleAnalyzeAll);
    DOM.autoRefreshToggle?.addEventListener('click', toggleAutoRefresh);
    DOM.manualPredictBtn?.addEventListener('click', handleCustomPredict);
    DOM.slipAnalyzeBtn?.addEventListener('click', handleSlipAnalysis);
    DOM.slipClearBtn?.addEventListener('click', clearSlip);
    
    // Initialize betslip tabs
    initBetslipTabs();
    
    // Load initial matches
    await handleRefresh();
    
    // Set live status
    if (DOM.liveStatus) {
        DOM.liveStatus.textContent = '✅ Live Feeds Active';
    }
    if (DOM.statusDot) {
        DOM.statusDot.className = 'status-dot live';
    }
    
    console.log('🚀 BetAnalyzer initialized!');
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);