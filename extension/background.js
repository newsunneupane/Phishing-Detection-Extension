const API_BASE_URL = 'https://your-project.vercel.app';
const CACHE_KEY = 'phishing_cache';
const MAX_CACHE_SIZE = 50;

// Listen for tab updates
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url && tab.url.startsWith('http')) {
        checkUrl(tab.url, tabId);
    }
});

/**
 * Optimized checkUrl function with caching
 */
async function checkUrl(url, tabId) {
    if (!url || url.includes(API_BASE_URL.split('://')[1])) return;

    try {
        // 1. Check Cache first to save memory and network
        const cache = await getCache();
        if (cache[url]) {
            processResult(cache[url], tabId, url);
            return;
        }

        // 2. Fetch from server
        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        
        if (!response.ok) return;

        const data = await response.json();
        
        // 3. Update Cache
        await updateCache(url, data);

        // 4. Process
        processResult(data, tabId, url);

    } catch (error) {
        console.error(`[CONN ERROR]`, error.message);
    }
}

/**
 * Handles the logic based on server/cache result
 */
function processResult(data, tabId, url) {
    if (data.source === 'database' && data.warning) {
        chrome.action.setBadgeText({ text: '!!!', tabId: tabId });
        chrome.action.setBadgeBackgroundColor({ color: '#FF0000', tabId: tabId });
        injectWarningBanner(tabId, data.label);
    } else if (data.source === 'ml_model') {
        injectVotePrompt(tabId, url, data.label, API_BASE_URL);
    } else {
        chrome.action.setBadgeText({ text: '', tabId: tabId });
    }
}

// --- Helper Functions for Memory Efficiency ---

async function getCache() {
    const result = await chrome.storage.local.get(CACHE_KEY);
    return result[CACHE_KEY] || {};
}

async function updateCache(url, data) {
    const cache = await getCache();
    cache[url] = data;
    
    // Maintain size limit
    const keys = Object.keys(cache);
    if (keys.length > MAX_CACHE_SIZE) {
        delete cache[keys[0]];
    }
    
    await chrome.storage.local.set({ [CACHE_KEY]: cache });
}

function injectWarningBanner(tabId, label) {
    chrome.scripting.executeScript({
        target: { tabId: tabId },
        func: (label) => {
            if (document.getElementById('phishing-warning-banner')) return;
            const div = document.createElement('div');
            div.id = 'phishing-warning-banner';
            div.style.cssText = 'position:fixed;top:0;left:0;width:100%;background:#e74c3c;color:white;text-align:center;padding:15px;font-weight:bold;z-index:9999999;font-family:Arial;';
            div.innerHTML = `⚠️ WARNING: This site is ${label}. <button onclick="this.parentElement.remove()" style="margin-left:15px;cursor:pointer;">Close</button>`;
            document.body.prepend(div);
        },
        args: [label]
    }).catch(() => {});
}

function injectVotePrompt(tabId, url, mlPrediction, apiBaseUrl) {
    chrome.scripting.executeScript({
        target: { tabId: tabId },
        func: (url, mlPrediction, apiBaseUrl) => {
            if (document.getElementById('phishing-vote-prompt')) return;
            const div = document.createElement('div');
            div.id = 'phishing-vote-prompt';
            div.style.cssText = 'position:fixed;bottom:20px;right:20px;width:280px;background:white;border:2px solid #3498db;border-radius:10px;padding:15px;box-shadow:0 4px 15px rgba(0,0,0,0.3);z-index:9999999;font-family:Arial;color:#333;display:none;';
            div.innerHTML = `
                <div style="font-weight:bold;margin-bottom:8px;font-size:14px;">Before you go... Is this site phishing?</div>
                <div style="font-size:11px;color:#666;margin-bottom:10px;">ML Prediction: <b>${mlPrediction}</b></div>
                <input type="range" id="v-slider" min="0" max="100" value="50" style="width:100%;">
                <div style="display:flex;justify-content:space-between;font-size:11px;margin:5px 0 10px;">
                    <span>Safe</span> <b id="v-val">50%</b> <span>Phishing</span>
                </div>
                <button id="v-sub" style="width:100%;background:#3498db;color:white;border:none;padding:8px;border-radius:5px;cursor:pointer;font-weight:bold;">Submit Vote</button>
                <div id="v-close" style="text-align:center;font-size:11px;margin-top:8px;cursor:pointer;color:#999;">No thanks</div>
            `;
            document.body.appendChild(div);
            const slider = document.getElementById('v-slider');
            const display = document.getElementById('v-val');
            slider.oninput = () => display.textContent = slider.value + '%';
            document.addEventListener('mouseleave', (e) => {
                if (e.clientY < 10) div.style.display = 'block';
            });
            document.getElementById('v-sub').onclick = async () => {
                const percent = parseInt(slider.value);
                let vote = percent > 70 ? 'phishing' : (percent > 30 ? 'potential phishing' : 'legitimate');
                try {
                    await fetch(`${apiBaseUrl}/feedback`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url: url, vote: vote, percentage: percent })
                    });
                    div.innerHTML = '<div style="text-align:center;color:#2ecc71;font-weight:bold;padding:10px;">Vote Recorded!</div>';
                    setTimeout(() => div.remove(), 1500);
                } catch (e) {}
            };
            document.getElementById('v-close').onclick = () => div.remove();
        },
        args: [url, mlPrediction, apiBaseUrl]
    }).catch(() => {});
}
