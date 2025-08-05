// Weather functionality for Chatterbox Golf League
function loadWeatherForecast(nextTuesdayDate, elementId = 'weather-content') {
    const latitude = 42.12;
    const longitude = -86.45;
    
    // Weather descriptions
    const weatherCodes = {
        0: { desc: 'Clear', class: 'text-warning' },
        1: { desc: 'Mainly clear', class: 'text-warning' },
        2: { desc: 'Partly cloudy', class: 'text-muted' },
        3: { desc: 'Overcast', class: 'text-muted' },
        45: { desc: 'Foggy', class: 'text-muted' },
        48: { desc: 'Foggy', class: 'text-muted' },
        51: { desc: 'Light drizzle', class: 'text-info' },
        53: { desc: 'Drizzle', class: 'text-info' },
        55: { desc: 'Heavy drizzle', class: 'text-info' },
        56: { desc: 'Freezing drizzle', class: 'text-info' },
        57: { desc: 'Heavy freezing drizzle', class: 'text-info' },
        61: { desc: 'Light rain', class: 'text-info' },
        63: { desc: 'Rain', class: 'text-info' },
        65: { desc: 'Heavy rain', class: 'text-info' },
        66: { desc: 'Freezing rain', class: 'text-info' },
        67: { desc: 'Heavy freezing rain', class: 'text-info' },
        71: { desc: 'Light snow', class: 'text-info' },
        73: { desc: 'Snow', class: 'text-info' },
        75: { desc: 'Heavy snow', class: 'text-info' },
        77: { desc: 'Snow grains', class: 'text-info' },
        80: { desc: 'Light showers', class: 'text-info' },
        81: { desc: 'Showers', class: 'text-info' },
        82: { desc: 'Heavy showers', class: 'text-info' },
        85: { desc: 'Light snow showers', class: 'text-info' },
        86: { desc: 'Heavy snow showers', class: 'text-info' },
        95: { desc: 'Thunderstorm', class: 'text-danger' },
        96: { desc: 'Thunderstorm w/ hail', class: 'text-danger' },
        99: { desc: 'Severe thunderstorm', class: 'text-danger' }
    };

    function displayWeather(data) {
        const days = data.daily;
        const idx = days.time.findIndex(date => date === nextTuesdayDate);
        if (idx === -1) {
            document.getElementById(elementId).innerHTML = '<div class="text-warning small mb-2">No forecast available for the next league day.</div>';
            return;
        }
        
        const code = days.weathercode[idx];
        const weatherInfo = weatherCodes[code] || { desc: 'Unknown', class: 'text-muted' };
        const maxTemp = Math.round(days.temperature_2m_max[idx]);
        const minTemp = Math.round(days.temperature_2m_min[idx]);
        const precip = days.precipitation_sum[idx];
        
                 const html = `
             <div class="text-center">
                 <div class="mb-2" style="font-size:1.5rem;">
                     ${maxTemp}&deg; / ${minTemp}&deg;F
                 </div>
                 <div class="mb-2 ${weatherInfo.class} fw-bold">${weatherInfo.desc}</div>
                 <div class="small text-muted">
                     ${precip > 0 ? `Precipitation: ${precip} in` : 'No precipitation expected'}
                 </div>
             </div>
         `;
        document.getElementById(elementId).innerHTML = html;
    }

    function handleWeatherError() {
        document.getElementById(elementId).innerHTML = `
            <div class="text-center">
                <div class="text-danger mb-2">
                    <i class="fas fa-exclamation-triangle"></i> Could not load weather data
                </div>
                <div class="small text-muted">
                    Please check <a href="https://weather.com" target="_blank">weather.com</a> for current conditions
                </div>
            </div>
        `;
    }

    // Fetch weather data with timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

    const apiUrl = `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode&temperature_unit=fahrenheit&timezone=America/Detroit`;

    fetch(apiUrl, { signal: controller.signal })
        .then(response => {
            clearTimeout(timeoutId);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            displayWeather(data);
        })
        .catch(error => {
            clearTimeout(timeoutId);
            console.error('Weather API error:', error);
            handleWeatherError();
        });
} 