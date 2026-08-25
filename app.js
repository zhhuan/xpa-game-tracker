// ===== 全局变量 =====
let allGames = [];
let currentSearchTerm = '';
let currentSortMethod = 'default';
let currentFilteredGames = [];
let visibleGamesCount = 0;
const PAGE_SIZE = 60;
let listenersReady = false;

// ===== DOM 元素 =====
const elements = {
    gamesGrid: document.getElementById('gamesGrid'),
    loadingContainer: document.getElementById('loadingContainer'),
    errorContainer: document.getElementById('errorContainer'),
    errorMessage: document.getElementById('errorMessage'),
    retryButton: document.getElementById('retryButton'),
    searchInput: document.getElementById('searchInput'),
    searchButton: document.getElementById('searchButton'),
    sortSelect: document.getElementById('sortSelect'),
    totalGames: document.getElementById('totalGames'),
    displayedGames: document.getElementById('displayedGames'),
    lastUpdated: document.getElementById('lastUpdated'),
    noResults: document.getElementById('noResults'),
    loadMoreContainer: document.getElementById('loadMoreContainer'),
    loadMoreButton: document.getElementById('loadMoreButton'),
    resultsProgress: document.getElementById('resultsProgress')
};

// ===== 初始化应用 =====
async function init() {
    showLoading();
    
    try {
        await loadGamesData();
        setupEventListeners();
        renderGames();
        updateStats();
    } catch (error) {
        showError(error.message);
    }
}

// ===== 加载游戏数据 =====
async function loadGamesData() {
    try {
        // 优先加载带有新游戏标记的数据文件
        let response;
        let data;
        
        // 尝试加载带有标记的数据
        try {
            response = await fetch('data/games_with_new_markers.json');
            if (response.ok) {
                data = await response.json();
                if (data.games && Array.isArray(data.games)) {
                    allGames = data.games;
                    console.log(`成功加载 ${allGames.length} 个游戏（包含新游戏标记）`);
                    
                    // 更新标记时间
                    if (data.taggingDate) {
                        const date = new Date(data.taggingDate);
                        const formattedDate = date.toLocaleDateString('zh-CN', {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit'
                        });
                        elements.lastUpdated.textContent = `标记时间: ${formattedDate}`;
                    }
                    hideLoading();
                    return;
                }
            }
        } catch (e) {
            console.log('未找到标记文件，尝试加载普通数据文件');
        }
        
        // 如果标记文件不存在或格式错误，回退到普通数据文件
        response = await fetch('data/games.json');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        data = await response.json();
        
        if (!data.games || !Array.isArray(data.games)) {
            throw new Error('无效的游戏数据格式');
        }
        
        allGames = data.games;
        console.log(`成功加载 ${allGames.length} 个游戏`);
        
        // 更新最后更新时间
        if (data.lastUpdated) {
            const date = new Date(data.lastUpdated);
            const formattedDate = date.toLocaleDateString('zh-CN', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            });
            elements.lastUpdated.textContent = formattedDate;
        }
        
        hideLoading();
        
    } catch (error) {
        console.error('加载游戏数据失败:', error);
        hideLoading();
        throw new Error('无法加载游戏数据，请确保已运行数据爬取脚本');
    }
}

// ===== 设置事件监听器 =====
function setupEventListeners() {
    if (listenersReady) return;
    listenersReady = true;
    // 搜索输入框实时搜索
    elements.searchInput.addEventListener('input', debounce(handleSearch, 300));
    
    // 搜索按钮点击
    elements.searchButton.addEventListener('click', handleSearch);
    
    // 回车键搜索
    elements.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });
    
    // 排序选择变化
    elements.sortSelect.addEventListener('change', handleSort);
    
    // 重试按钮
    elements.retryButton.addEventListener('click', () => {
        hideError();
        showLoading();
        init();
    });

    elements.loadMoreButton.addEventListener('click', showMoreGames);
}

// ===== 搜索处理 =====
function handleSearch() {
    currentSearchTerm = elements.searchInput.value.trim().toLowerCase();
    visibleGamesCount = 0;
    renderGames();
    updateStats();
}

// ===== 排序处理 =====
function handleSort() {
    currentSortMethod = elements.sortSelect.value;
    visibleGamesCount = 0;
    renderGames();
    updateStats();
}

// ===== 渲染游戏 =====
function renderGames() {
    // 过滤游戏
    currentFilteredGames = allGames.filter(game => {
        if (!currentSearchTerm) return true;
        
        const name = game.title || game.name ? (game.title || game.name).toLowerCase() : '';
        return name.includes(currentSearchTerm);
    });
    
    // 排序游戏 - 无论是否有搜索词，都应该应用当前排序方法
    currentFilteredGames = sortGames(currentFilteredGames);

    if (visibleGamesCount === 0) visibleGamesCount = PAGE_SIZE;
    const gamesToRender = currentFilteredGames.slice(0, visibleGamesCount);
    
    // 清空当前显示
    elements.gamesGrid.innerHTML = '';
    
    // 显示无结果提示
    if (currentFilteredGames.length === 0) {
        elements.noResults.style.display = 'block';
        elements.loadMoreContainer.hidden = true;
        updateStats();
        return;
    } else {
        elements.noResults.style.display = 'none';
    }
    
    // 渲染游戏卡片
    const fragment = document.createDocumentFragment();
    gamesToRender.forEach(game => {
        const gameCard = createGameCard(game);
        fragment.appendChild(gameCard);
    });
    elements.gamesGrid.appendChild(fragment);
    updateLoadMoreState();
}

function showMoreGames() {
    visibleGamesCount += PAGE_SIZE;
    renderGames();
    updateStats();
}

function updateLoadMoreState() {
    const shown = Math.min(visibleGamesCount, currentFilteredGames.length);
    const hasMore = shown < currentFilteredGames.length;
    elements.loadMoreContainer.hidden = currentFilteredGames.length === 0;
    elements.loadMoreButton.hidden = !hasMore;
    elements.resultsProgress.textContent = `已显示 ${shown} / ${currentFilteredGames.length} 个游戏`;
}

// ===== 游戏排序函数 =====
function sortGames(games) {
    const sortedGames = [...games]; // 创建副本避免修改原数组
    
    switch (currentSortMethod) {
        case 'date-desc':
            return sortedGames.sort((a, b) => {
                const dateA = a.releaseDate ? new Date(a.releaseDate) : new Date('9999-12-31');
                const dateB = b.releaseDate ? new Date(b.releaseDate) : new Date('9999-12-31');
                return dateB - dateA; // 新到旧
            });
            
        case 'date-asc':
            return sortedGames.sort((a, b) => {
                const dateA = a.releaseDate ? new Date(a.releaseDate) : new Date('1970-01-01');
                const dateB = b.releaseDate ? new Date(b.releaseDate) : new Date('1970-01-01');
                return dateA - dateB; // 旧到新
            });
            
        case 'name':
            return sortedGames.sort((a, b) => {
                const nameA = (a.title || a.name || '').toLowerCase();
                const nameB = (b.title || b.name || '').toLowerCase();
                return nameA.localeCompare(nameB);
            });
            
        case 'rating':
            return sortedGames.sort((a, b) => {
                const ratingA = a.rating || 0;
                const ratingB = b.rating || 0;
                return ratingB - ratingA; // 高到低
            });
            
        case 'default':
        default:
            // 默认排序：保持数据文件（Xbox API）的原始顺序，只稳定前置新游戏。
            return sortedGames.sort((a, b) => {
                const aIsNew = a.isNew || false;
                const bIsNew = b.isNew || false;

                if (aIsNew && !bIsNew) return -1;
                if (!aIsNew && bIsNew) return 1;
                return 0;
            });
    }
}

// ===== 创建游戏卡片 =====
function createGameCard(game) {
    const card = document.createElement('div');
    card.className = 'game-card';
    
    // 检查是否为新游戏
    const isNewGame = game.isNew || false;
    if (isNewGame) {
        card.classList.add('new-game');
    }
    
    // 图片 URL 或占位符
    const placeholderImage = 'https://placehold.co/400x400/1a1a1a/107c10?text=No+Image';
    const imageUrl = game.image || placeholderImage;
    
    // 游戏名称
    const gameName = game.title || game.name || '未知游戏';
    
    // 发布日期
    const releaseDate = game.releaseDate ? formatDate(game.releaseDate) : '未知';
    
    // 评分
    const rating = Number(game.rating) || 0;
    const ratingStars = generateRatingStars(rating);
    
    // 分类
    const categories = game.categories && Array.isArray(game.categories) ? game.categories.slice(0, 2) : [];
    const categoriesHtml = categories.length > 0 
        ? `<div class="game-categories">${categories.map(cat => `<span class="category-tag">${escapeHtml(cat)}</span>`).join('')}</div>`
        : '';
    
    // 开发商
    const developer = game.developerName || game.developer ? `<p class="game-developer"><small>开发商: ${escapeHtml(game.developerName || game.developer)}</small></p>` : '';
    
    // 发行商
    const publisher = game.publisherName || game.publisher ? `<p class="game-publisher"><small>发行商: ${escapeHtml(game.publisherName || game.publisher)}</small></p>` : '';
    
    // 价格
    const price = game.price ? formatPrice(game.price, game.currency) : '';
    
    // 游戏链接 - 生成正确的商店URL格式
    const gameUrl = buildGameUrl(game);
    
    card.innerHTML = `
        <img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(gameName)}" class="game-image" loading="lazy" decoding="async">
        <div class="game-content">
            <h3 class="game-title">
                ${escapeHtml(gameName)}
                ${isNewGame ? '<span class="new-badge">新</span>' : ''}
            </h3>
            <div class="game-rating">${ratingStars} <span class="rating-number">${rating.toFixed(1)}</span></div>
            ${categoriesHtml}
            ${developer}
            ${publisher}
            <div class="game-info">
                <span class="game-date">发布: ${releaseDate}</span>
                ${price ? `<span class="game-price">${price}</span>` : ''}
                ${gameUrl !== '#' ? `<a href="${gameUrl}" target="_blank" rel="noopener noreferrer" class="game-link">查看详情</a>` : ''}
            </div>
        </div>
    `;

    const image = card.querySelector('.game-image');
    image.addEventListener('error', () => {
        if (image.src !== placeholderImage) image.src = placeholderImage;
    }, { once: true });
    
    // 点击卡片打开链接
    if (gameUrl !== '#') {
        card.tabIndex = 0;
        card.setAttribute('role', 'link');
        card.setAttribute('aria-label', `查看 ${gameName} 的详情`);
        card.addEventListener('click', (e) => {
            // 如果点击的是链接按钮，不要阻止默认行为
            if (e.target.classList.contains('game-link')) return;
            window.open(gameUrl, '_blank');
        });
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                window.open(gameUrl, '_blank', 'noopener,noreferrer');
            }
        });
    }
    
    return card;
}

function buildGameUrl(game) {
    if (!game.url) return '#';
    try {
        const url = new URL(game.url, 'https://www.xbox.com');
        if (!['https:', 'http:'].includes(url.protocol)) return '#';
        if (!url.pathname.includes('/games/store/')) {
            url.pathname = url.pathname.replace('/games/', '/games/store/');
        }
        if (game.productId && !url.pathname.toLowerCase().endsWith(`/${String(game.productId).toLowerCase()}`)) {
            url.pathname = `${url.pathname.replace(/\/$/, '')}/${game.productId}`;
        }
        return url.href;
    } catch {
        return '#';
    }
}

// ===== 格式化日期 =====
function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        if (Number.isNaN(date.getTime())) return dateString;
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    } catch (error) {
        return dateString;
    }
}

// ===== 生成评分星星 =====
function generateRatingStars(rating) {
    const maxStars = 5;
    let stars = '';
    for (let i = 1; i <= maxStars; i++) {
        if (i <= Math.floor(rating)) {
            stars += '★';
        } else if (i - 0.5 <= rating) {
            stars += '½';
        } else {
            stars += '☆';
        }
    }
    return stars;
}

// ===== 格式化价格 =====
function formatPrice(price, currency = 'USD') {
    const symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'CNY': '¥'
    };
    const symbol = symbols[currency] || currency + ' ';
    const amount = Number(price);
    return Number.isFinite(amount) ? symbol + amount.toFixed(2) : '';
}

// ===== HTML转义 =====
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== 更新统计信息 =====
function updateStats() {
    elements.totalGames.textContent = allGames.length;
    
    elements.displayedGames.textContent = currentFilteredGames.length;
}

// ===== 显示加载状态 =====
function showLoading() {
    elements.loadingContainer.style.display = 'flex';
    elements.errorContainer.style.display = 'none';
    elements.gamesGrid.style.display = 'none';
}

// ===== 隐藏加载状态 =====
function hideLoading() {
    elements.loadingContainer.style.display = 'none';
    elements.gamesGrid.style.display = 'grid';
}

// ===== 显示错误信息 =====
function showError(message) {
    elements.errorMessage.textContent = message;
    elements.errorContainer.style.display = 'block';
    elements.gamesGrid.style.display = 'none';
}

// ===== 隐藏错误信息 =====
function hideError() {
    elements.errorContainer.style.display = 'none';
}

// ===== 防抖函数 =====
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ===== 页面加载完成后初始化 =====
document.addEventListener('DOMContentLoaded', init);

// ===== 导出函数（用于调试） =====
if (typeof window !== 'undefined') {
    window.XPAApp = {
        init,
        loadGamesData,
        handleSearch,
        handleSort,
        renderGames,
        sortGames,
        allGames: () => allGames,
        currentSort: () => currentSortMethod
    };
}
