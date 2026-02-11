document.addEventListener('DOMContentLoaded', function () {
    // --- CSRF Token for Django POST requests ---
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');

    // --- Скрипт для мобильного меню ---
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    const iconOpen = document.getElementById('icon-open');
    const iconClose = document.getElementById('icon-close');

    if (mobileMenuButton) {
        mobileMenuButton.addEventListener('click', () => {
            mobileMenu.classList.toggle('hidden');
            iconOpen.classList.toggle('hidden');
            iconClose.classList.toggle('hidden');
        });
    }

    // --- ЛОГИКА СИМУЛЯЦИИ ---

    let shanghaiRoutes = null; // Глобальная переменная для хранения маршрутов
    const simulations = new Map(); // Хранилище для управления состоянием симуляций

    // 1. Функция для загрузки маршрутов
    async function fetchRoutes() {
        if (shanghaiRoutes) return shanghaiRoutes;
        try {
            const response = await fetch("/static/data/shanghai_routes.json");
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const geojsonData = await response.json();
            if (!geojsonData.features || geojsonData.features.length === 0) {
                throw new Error("Файл маршрутов пуст или имеет неверный формат GeoJSON.");
            }
            shanghaiRoutes = geojsonData.features;
            console.log("📦 Загружено маршрутов:", shanghaiRoutes.length);
            return shanghaiRoutes;
        } catch (error) {
            console.error("🚨 Ошибка при загрузке маршрутов:", error);
            return null;
        }
    }

    // 2. Функция для выбора случайного маршрута
    function getRandomRoute(routes) {
        if (!routes || routes.length === 0) return null;
        const randomIndex = Math.floor(Math.random() * routes.length);
        // GeoJSON coordinates are [lng, lat], Leaflet needs [lat, lng]
        const coordinates = routes[randomIndex].geometry.coordinates.map(coord => [coord[1], coord[0]]);
        return coordinates;
    }

    // 3. Функция для расчета дистанции
    function calculateRouteDistance(route) {
        let totalDistance = 0;
        for (let i = 0; i < route.length - 1; i++) {
            totalDistance += L.latLng(route[i]).distanceTo(L.latLng(route[i + 1]));
        }
        return totalDistance / 1000; // в км
    }

    // 4. Функция для запуска симуляции
    function startSimulation(card, allRoutes) {
        const scooterId = card.dataset.scooterId;
        if (simulations.has(scooterId) && simulations.get(scooterId).isRunning) {
            console.warn(`Симуляция для самоката ${scooterId} уже запущена.`);
            return;
        }

        const route = getRandomRoute(allRoutes);
        if (!route) {
            alert("Не удалось выбрать маршрут. Попробуйте еще раз.");
            return;
        }

        // Прячем кнопку "Старт", показываем прогресс
        const startButton = card.querySelector('.start-button');
        const claimButton = card.querySelector('.claim-button');
        startButton.style.display = 'none';
        claimButton.disabled = true;
        claimButton.textContent = 'В пути...';

        const mapContainer = document.getElementById(`map-${scooterId}`);
        mapContainer.innerHTML = ""; // Очищаем контейнер карты
        const map = L.map(mapContainer, {
            center: route[0],
            zoom: 14,
            zoomControl: false,
            dragging: false,
            scrollWheelZoom: false,
        });
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png').addTo(map);

        const scooterIcon = L.divIcon({ className: 'scooter-icon', iconSize: [12, 12] });
        const scooterMarker = L.marker(route[0], { icon: scooterIcon }).addTo(map);
        const routePolyline = L.polyline([], { color: '#39FF14', weight: 3, opacity: 0.6 }).addTo(map);

        const distance = calculateRouteDistance(route);
        const durationInSeconds = (distance / 15) * 3600; // Средняя скорость 15 км/ч
        const profitAmount = (durationInSeconds / 60) * 0.10;

        const simulationState = {
            isRunning: true,
            animationFrameId: null,
            map: map,
            marker: scooterMarker,
            polyline: routePolyline,
            route: route,
            totalDistance: distance,
            totalDuration: durationInSeconds,
            totalProfit: profitAmount,
        };
        simulations.set(scooterId, simulationState);

        let startTime = Date.now();
        const simulationDurationMs = 30000; // 30 секунд на всю симуляцию

        function animate() {
            const elapsedTime = Date.now() - startTime;
            const progress = Math.min(elapsedTime / simulationDurationMs, 1);

            const routeIndex = Math.floor(progress * (route.length - 1));
            const currentPath = route.slice(0, routeIndex + 1);
            
            scooterMarker.setLatLng(route[routeIndex]);
            routePolyline.setLatLngs(currentPath);
            map.panTo(route[routeIndex], { animate: true, duration: 0.1 });

            card.querySelector('.stat-distance').textContent = `${(distance * progress).toFixed(1)} км`;
            card.querySelector('.stat-duration').textContent = `${Math.floor((durationInSeconds * progress) / 60)} мин`;
            card.querySelector('.stat-profit-amount').textContent = `€ ${(profitAmount * progress).toFixed(2)}`;
            card.querySelector('.progress-bar').style.width = `${progress * 100}%`;

            if (progress < 1) {
                simulationState.animationFrameId = requestAnimationFrame(animate);
            } else {
                simulationState.isRunning = false;
                claimButton.disabled = false;
                claimButton.textContent = 'Забрать прибыль';
            }
        }
        animate();
    }
    
    // 5. Функция сброса карточки в начальное состояние
    function resetCard(card) {
        const scooterId = card.dataset.scooterId;
        const simulation = simulations.get(scooterId);
        if (simulation) {
            if (simulation.animationFrameId) {
                cancelAnimationFrame(simulation.animationFrameId);
            }
            if (simulation.map) {
                simulation.map.remove();
            }
            simulations.delete(scooterId);
        }
        
        card.querySelector('.stat-distance').textContent = '-- км';
        card.querySelector('.stat-duration').textContent = '-- мин';
        card.querySelector('.stat-profit-amount').textContent = '€ --';
        card.querySelector('.progress-bar').style.width = '0%';
        card.querySelector('.claim-button').disabled = true;
        card.querySelector('.claim-button').textContent = 'Забрать прибыль';
        card.querySelector('.start-button').style.display = 'block';
    }

    // 6. Функция сбора прибыли
    async function handleClaim(button, scooterId) {
        const simulation = simulations.get(scooterId);
        if (!simulation || simulation.isRunning) return;

        button.disabled = true;
        button.textContent = 'Обработка...';
        try {
            const response = await fetch('/api/claim_profit/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
                body: JSON.stringify({ scooter_id: scooterId, profit_amount: simulation.totalProfit })
            });
            if (!response.ok) throw new Error((await response.json()).message || 'Ошибка сервера');
            
            const result = await response.json();
            const mainBalanceEl = document.getElementById('main-balance-display');
            if(mainBalanceEl) mainBalanceEl.textContent = `$${result.new_balance.toFixed(2)}`;
            
            // Сброс карточки для нового старта
            resetCard(button.closest('.scooter-card'));

        } catch (error) {
            console.error("Ошибка при сборе прибыли:", error);
            alert(error.message);
            button.disabled = false;
            button.textContent = 'Забрать прибыль';
        }
    }

    // 7. Основная функция инициализации
    async function initializePage() {
        const allRoutes = await fetchRoutes();
        if (!allRoutes) {
            alert("Не удалось загрузить данные для симуляции. Пожалуйста, обновите страницу.");
            return;
        }

        document.querySelectorAll('.scooter-card').forEach(card => {
            const scooterId = card.dataset.scooterId;
            const startButton = card.querySelector('.start-button');
            const claimButton = card.querySelector('.claim-button');
            
            resetCard(card); // Приводим все карточки в начальное состояние

            startButton.addEventListener('click', () => startSimulation(card, allRoutes));
            claimButton.addEventListener('click', () => handleClaim(claimButton, scooterId));
        });
    }

    // Запускаем весь процесс
    initializePage();
});
