document.addEventListener('DOMContentLoaded', async () => {
    const urlElement = document.getElementById('current-url');
    const statusMsg = document.getElementById('status-msg');
    const slider = document.getElementById('popup-slider');
    const sliderVal = document.getElementById('popup-slider-val');

    slider.oninput = () => sliderVal.textContent = slider.value + '%';

    // Get current tab's URL
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const currentUrl = tab.url;
    urlElement.textContent = currentUrl;

    const vote = async (label) => {
        const percentage = parseInt(slider.value);
        statusMsg.textContent = 'Sending feedback...';
        try {
            const response = await fetch('http://127.0.0.1:5001/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    url: currentUrl, 
                    vote: label,
                    percentage: percentage 
                })
            });
            const data = await response.json();
            statusMsg.textContent = data.message;
        } catch (error) {
            console.error('Error sending feedback:', error);
            statusMsg.textContent = 'Error: Make sure the backend server is running.';
        }
    };

    document.getElementById('btn-phishing').addEventListener('click', () => vote('phishing'));
    document.getElementById('btn-potential').addEventListener('click', () => vote('potential phishing'));
    document.getElementById('btn-legitimate').addEventListener('click', () => vote('legitimate'));
});
