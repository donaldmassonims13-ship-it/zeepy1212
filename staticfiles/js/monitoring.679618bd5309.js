document.addEventListener('DOMContentLoaded', function () {
    const STORAGE_KEY = 'zeepyScooterState';
    const TEN_MINUTES_MS = 10 * 60 * 1000;
    const safeZones = [
        { minLat: 30.8527, maxLat: 31.1458, minLon: 121.5294, maxLon: 121.8569 }, { minLat: 31.6277, maxLat: 31.7317, minLon: 121.3721, maxLon: 121.5054 },
        { minLat: 30.7371, maxLat: 31.1247, minLon: 121.0419, maxLon: 121.4003 }, { minLat: 31.2251, maxLat: 31.4123, minLon: 120.4064, maxLon: 120.6728 },
        { minLat: 31.2028, maxLat: 31.4105, minLon: 120.9464, maxLon: 121.4902 }
    ];

    function generateInitialLocation() {
        const zone = safeZones[Math.floor(Math.random() * safeZones.length)];
        return { lat: Math.random() * (zone.maxLat - zone.minLat) + zone.minLat, lon: Math.random() * (zone.maxLon - zone.minLon) + zone.minLon };
    }

    function getScooterState() {
        let state = JSON.parse(localStorage.getItem(STORAGE_KEY));
        if (!state || state.scooters.length !== window.userScooterCount) {
            state = { scooters: [], lastStatusUpdate: Date.now() };
            for (let i = 0; i < window.userScooterCount; i++) {
                const loc = generateInitialLocation();
                state.scooters.push({ id: i, lat: loc.lat, lon: loc.lon, isActive: Math.random() > 0.3, angle: Math.random() * 2 * Math.PI });
            }
            localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
        }
        return state;
    }

    const scooterState = getScooterState();
    const allScooters = scooterState.scooters;

    if (allScooters.length === 0) {
        L.map('map').setView([31.10, 121.24], 10).addLayer(L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { attribution: '&copy; OSM &copy; CARTO' }));
        return;
    }

    const map = L.map('map').setView([31.2, 121.5], 11);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { attribution: '&copy; OSM &copy; CARTO', maxZoom: 20 }).addTo(map);

    const markersLayer = L.layerGroup(); // Используем простую группу для управления видимостью
    
    allScooters.forEach(scooter => {
        const icon = L.divIcon({ className: 'leaflet-div-icon', html: `<div class="pulsating-dot ${scooter.isActive ? 'status-active' : 'status-idle'}"></div>`, iconSize: [16, 16], iconAnchor: [8, 8] });
        const marker = L.marker([scooter.lat, scooter.lon], { icon });
        marker.bindPopup(`<b>Самокат #${scooter.id + 1}</b>`);
        scooter.marker = marker;
        markersLayer.addLayer(marker);
    });
    map.addLayer(markersLayer);
    
    function isInsideSafeZone(lat, lon) { return safeZones.some(z => lat >= z.minLat && lat <= z.maxLat && lon >= z.minLon && lon <= z.maxLon); }

    function updateScooterPositions() {
        allScooters.forEach(scooter => {
            if (!scooter.isActive) return;
            scooter.angle += (Math.random() - 0.5) * 0.5;
            const newLat = scooter.lat + Math.sin(scooter.angle) * 0.00012;
            const newLon = scooter.lon + Math.cos(scooter.angle) * 0.00012;
            if (isInsideSafeZone(newLat, newLon)) {
                scooter.lat = newLat; scooter.lon = newLon;
                scooter.marker.setLatLng([newLat, newLon]);
            } else { scooter.angle += Math.PI; }
        });
        const stateToSave = {
            scooters: allScooters.map(s => ({ id: s.id, lat: s.lat, lon: s.lon, isActive: s.isActive, angle: s.angle })),
            lastStatusUpdate: scooterState.lastStatusUpdate
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
    }

    function checkAndUpdateStatuses() {
        if (Date.now() - scooterState.lastStatusUpdate > TEN_MINUTES_MS) {
            allScooters.forEach(s => {
                s.isActive = Math.random() > 0.3;
                s.marker.setIcon(L.divIcon({ className: 'leaflet-div-icon', html: `<div class="pulsating-dot ${s.isActive ? 'status-active' : 'status-idle'}"></div>`, iconSize: [16, 16], iconAnchor: [8, 8] }));
            });
            scooterState.lastStatusUpdate = Date.now();
        }
    }
    
    // --- НОВАЯ ЛОГИКА: Поиск и фильтрация ---
    const searchInput = document.getElementById('search-input');
    const statusFilter = document.getElementById('status-filter');

  function applyFilters() {
        const filterValue = statusFilter.value;

        // Теперь мы всегда перебираем ПОЛНЫЙ список всех самокатов
        allScooters.forEach(scooter => {
            const marker = scooter.marker;
            let shouldBeVisible = true; // По умолчанию считаем, что самокат должен быть виден

            // Проверяем, соответствует ли самокат фильтру
            if (filterValue === 'active' && !scooter.isActive) {
                shouldBeVisible = false;
            }
            if (filterValue === 'idle' && scooter.isActive) {
                shouldBeVisible = false;
            }
            // Если фильтр 'all', shouldBeVisible всегда останется true

            // Применяем решение
            if (shouldBeVisible) {
                // Если самокат должен быть виден, но его нет на слое, добавляем
                if (!markersLayer.hasLayer(marker)) {
                    markersLayer.addLayer(marker);
                }
            } else {
                // Если самокат не должен быть виден, но он есть на слое, убираем
                if (markersLayer.hasLayer(marker)) {
                    markersLayer.removeLayer(marker);
                }
            }
        });
    }

    searchInput.addEventListener('input', (e) => {
        const searchId = parseInt(e.target.value.replace('#', '')) - 1;
        const scooter = allScooters.find(s => s.id === searchId);
        if (scooter && scooter.marker) {
            map.flyTo([scooter.lat, scooter.lon], 18); // Плавный перелет к маркеру
            scooter.marker.openPopup();
        }
    });

    statusFilter.addEventListener('change', applyFilters);

    // --- НОВАЯ ЛОГИКА: Управление баннером ---
    const infoBanner = document.getElementById('info-banner');
    const closeBannerBtn = document.getElementById('close-banner-btn');
    closeBannerBtn.addEventListener('click', () => {
        infoBanner.style.transform = 'translateY(100%)';
    });

    // Запуск таймеров и начальная фильтрация
    setInterval(updateScooterPositions, 2000);
    setInterval(checkAndUpdateStatuses, 60 * 1000);
    checkAndUpdateStatuses();
    applyFilters();
});