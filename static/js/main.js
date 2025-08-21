/**
 * Dashboard Logístico - JavaScript Principal
 * Funcionalidades comuns e utilitários
 */

// Variáveis globais
let currentUser = null;
let isDataLoaded = false;

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    checkDataStatus();
});

/**
 * Inicializa a aplicação
 */
function initializeApp() {
    console.log('🚀 Inicializando Dashboard Logístico...');
    
    // Configurar Select2 globalmente
    if (typeof $ !== 'undefined') {
        $.fn.select2.defaults.set('theme', 'bootstrap-5');
        $.fn.select2.defaults.set('width', '100%');
    }
    
    // Configurar tooltips do Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Configurar popovers do Bootstrap
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

/**
 * Configura event listeners globais
 */
function setupEventListeners() {
    // Listener para mudanças de tema (se implementado)
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('change', toggleTheme);
    }
    
    // Listener para teclas de atalho
    document.addEventListener('keydown', handleKeyboardShortcuts);
    
    // Listener para mudanças de tamanho da janela
    window.addEventListener('resize', handleWindowResize);
}

/**
 * Verifica o status dos dados carregados
 */
function checkDataStatus() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                isDataLoaded = false;
                updateUIForNoData();
            } else {
                isDataLoaded = true;
                updateUIForDataLoaded();
            }
        })
        .catch(error => {
            console.error('Erro ao verificar status dos dados:', error);
            isDataLoaded = false;
            updateUIForNoData();
        });
}

/**
 * Atualiza a UI quando não há dados
 */
function updateUIForNoData() {
    // Mostrar alertas de dados não carregados
    const noDataAlerts = document.querySelectorAll('#noDataAlert');
    noDataAlerts.forEach(alert => {
        alert.classList.remove('d-none');
    });
    
    // Ocultar seções que dependem de dados
    const dataDependentSections = document.querySelectorAll('#filtrosSection, #statsSection');
    dataDependentSections.forEach(section => {
        if (section) section.style.display = 'none';
    });
    
    // Atualizar navbar
    updateNavbarForNoData();
}

/**
 * Atualiza a UI quando há dados carregados
 */
function updateUIForDataLoaded() {
    // Ocultar alertas de dados não carregados
    const noDataAlerts = document.querySelectorAll('#noDataAlert');
    noDataAlerts.forEach(alert => {
        alert.classList.add('d-none');
    });
    
    // Mostrar seções que dependem de dados
    const dataDependentSections = document.querySelectorAll('#filtrosSection, #statsSection');
    dataDependentSections.forEach(section => {
        if (section) section.style.display = 'block';
    });
    
    // Atualizar navbar
    updateNavbarForDataLoaded();
}

/**
 * Atualiza a navbar quando não há dados
 */
function updateNavbarForNoData() {
    const navbarItems = document.querySelectorAll('.navbar-nav .nav-link:not([href="/"])');
    navbarItems.forEach(item => {
        item.classList.add('disabled');
        item.style.opacity = '0.5';
        item.style.pointerEvents = 'none';
    });
}

/**
 * Atualiza a navbar quando há dados
 */
function updateNavbarForDataLoaded() {
    const navbarItems = document.querySelectorAll('.navbar-nav .nav-link');
    navbarItems.forEach(item => {
        item.classList.remove('disabled');
        item.style.opacity = '1';
        item.style.pointerEvents = 'auto';
    });
}

/**
 * Função para upload de arquivo
 */
function uploadFile() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        showToast('Por favor, selecione um arquivo', 'warning');
        return;
    }
    
    // Validar tipo de arquivo
    if (!file.name.match(/\.(xlsx|xls)$/i)) {
        showToast('Por favor, selecione um arquivo Excel (.xlsx ou .xls)', 'warning');
        return;
    }
    
    // Mostrar progresso
    const progressBar = document.getElementById('uploadProgress');
    const progressBarInner = progressBar.querySelector('.progress-bar');
    progressBar.classList.remove('d-none');
    progressBarInner.style.width = '0%';
    
    // Criar FormData
    const formData = new FormData();
    formData.append('file', file);
    
    // Fazer upload
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.message, 'success');
            
            // Fechar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('uploadModal'));
            modal.hide();
            
            // Limpar input
            fileInput.value = '';
            
            // Recarregar dados
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showToast(data.error, 'danger');
        }
    })
    .catch(error => {
        console.error('Erro no upload:', error);
        showToast('Erro ao fazer upload do arquivo', 'danger');
    })
    .finally(() => {
        // Ocultar progresso
        progressBar.classList.add('d-none');
    });
}

/**
 * Função para download do template
 */
function downloadTemplate() {
    // Criar dados de exemplo
    const templateData = [
        ['MESORREGIÃO - ORIGEM', 'MESORREGIÃO - DESTINO', 'MÊS', 'EMBARQUES'],
        ['São Paulo', 'Rio de Janeiro', '1 - 2023', '1500'],
        ['Minas Gerais', 'São Paulo', '1 - 2023', '800'],
        ['Rio de Janeiro', 'Minas Gerais', '1 - 2023', '600'],
        ['Paraná', 'São Paulo', '1 - 2023', '400'],
        ['Santa Catarina', 'Paraná', '1 - 2023', '300']
    ];
    
    // Criar CSV
    const csvContent = templateData.map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    
    // Download
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', 'template_embarques.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast('Template baixado com sucesso!', 'success');
}

/**
 * Mostra toast de notificação
 */
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remover toast após ser fechado
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

/**
 * Cria container de toasts se não existir
 */
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

/**
 * Função para alternar tema (se implementado)
 */
function toggleTheme() {
    const body = document.body;
    const currentTheme = body.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    showToast(`Tema alterado para ${newTheme === 'dark' ? 'escuro' : 'claro'}`, 'info');
}

/**
 * Manipula atalhos de teclado
 */
function handleKeyboardShortcuts(event) {
    // Ctrl/Cmd + U: Upload
    if ((event.ctrlKey || event.metaKey) && event.key === 'u') {
        event.preventDefault();
        const uploadModal = document.getElementById('uploadModal');
        if (uploadModal) {
            const modal = new bootstrap.Modal(uploadModal);
            modal.show();
        }
    }
    
    // Ctrl/Cmd + R: Refresh
    if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
        event.preventDefault();
        window.location.reload();
    }
    
    // Ctrl/Cmd + E: Export
    if ((event.ctrlKey || event.metaKey) && event.key === 'e') {
        event.preventDefault();
        const exportBtn = document.querySelector('[onclick*="export"]');
        if (exportBtn) {
            exportBtn.click();
        }
    }
}

/**
 * Manipula mudanças de tamanho da janela
 */
function handleWindowResize() {
    // Ajustar tamanho de gráficos se necessário
    const charts = document.querySelectorAll('canvas');
    charts.forEach(canvas => {
        if (canvas.chart) {
            canvas.chart.resize();
        }
    });
    
    // Ajustar mapa se necessário
    if (window.map && typeof window.map.invalidateSize === 'function') {
        setTimeout(() => {
            window.map.invalidateSize();
        }, 100);
    }
}

/**
 * Função para formatar números
 */
function formatNumber(number, locale = 'pt-BR') {
    if (typeof number !== 'number') return number;
    return number.toLocaleString(locale);
}

/**
 * Função para formatar percentuais
 */
function formatPercentage(value, total, decimals = 1) {
    if (total === 0) return '0%';
    const percentage = (value / total) * 100;
    return `${percentage.toFixed(decimals)}%`;
}

/**
 * Função para formatar datas
 */
function formatDate(dateString, format = 'short') {
    const date = new Date(dateString);
    
    switch (format) {
        case 'short':
            return date.toLocaleDateString('pt-BR');
        case 'long':
            return date.toLocaleDateString('pt-BR', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        case 'month':
            return date.toLocaleDateString('pt-BR', {
                month: 'long',
                year: 'numeric'
            });
        default:
            return date.toLocaleDateString('pt-BR');
    }
}

/**
 * Função para debounce
 */
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

/**
 * Função para throttle
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Função para validar email
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Função para validar CPF
 */
function isValidCPF(cpf) {
    cpf = cpf.replace(/[^\d]/g, '');
    
    if (cpf.length !== 11) return false;
    
    // Verificar se todos os dígitos são iguais
    if (/^(\d)\1+$/.test(cpf)) return false;
    
    // Validar primeiro dígito verificador
    let sum = 0;
    for (let i = 0; i < 9; i++) {
        sum += parseInt(cpf.charAt(i)) * (10 - i);
    }
    let remainder = 11 - (sum % 11);
    let digit1 = remainder < 2 ? 0 : remainder;
    
    // Validar segundo dígito verificador
    sum = 0;
    for (let i = 0; i < 10; i++) {
        sum += parseInt(cpf.charAt(i)) * (11 - i);
    }
    remainder = 11 - (sum % 11);
    let digit2 = remainder < 2 ? 0 : remainder;
    
    return parseInt(cpf.charAt(9)) === digit1 && parseInt(cpf.charAt(10)) === digit2;
}

/**
 * Função para copiar texto para clipboard
 */
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Texto copiado para clipboard!', 'success');
        }).catch(() => {
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

/**
 * Fallback para copiar texto
 */
function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showToast('Texto copiado para clipboard!', 'success');
    } catch (err) {
        showToast('Erro ao copiar texto', 'danger');
    }
    
    document.body.removeChild(textArea);
}

/**
 * Função para exportar dados como CSV
 */
function exportToCSV(data, filename) {
    const csvContent = data.map(row => 
        row.map(cell => `"${cell}"`).join(',')
    ).join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Função para fazer download de arquivo
 */
function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Função para mostrar loading
 */
function showLoading(element) {
    if (element) {
        element.classList.add('loading');
        element.disabled = true;
    }
}

/**
 * Função para ocultar loading
 */
function hideLoading(element) {
    if (element) {
        element.classList.remove('loading');
        element.disabled = false;
    }
}

/**
 * Função para fazer requisição HTTP
 */
async function makeRequest(url, options = {}) {
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, finalOptions);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Erro na requisição:', error);
        throw error;
    }
}

/**
 * Função para verificar se elemento está visível
 */
function isElementVisible(element) {
    if (!element) return false;
    
    const rect = element.getBoundingClientRect();
    const windowHeight = window.innerHeight || document.documentElement.clientHeight;
    
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= windowHeight &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Função para scroll suave
 */
function smoothScrollTo(element, duration = 500) {
    if (!element) return;
    
    const targetPosition = element.offsetTop;
    const startPosition = window.pageYOffset;
    const distance = targetPosition - startPosition;
    let startTime = null;
    
    function animation(currentTime) {
        if (startTime === null) startTime = currentTime;
        const timeElapsed = currentTime - startTime;
        const run = ease(timeElapsed, startPosition, distance, duration);
        window.scrollTo(0, run);
        if (timeElapsed < duration) requestAnimationFrame(animation);
    }
    
    function ease(t, b, c, d) {
        t /= d / 2;
        if (t < 1) return c / 2 * t * t + b;
        t--;
        return -c / 2 * (t * (t - 2) - 1) + b;
    }
    
    requestAnimationFrame(animation);
}

// Exportar funções para uso global
window.DashboardUtils = {
    showToast,
    formatNumber,
    formatPercentage,
    formatDate,
    debounce,
    throttle,
    isValidEmail,
    isValidCPF,
    copyToClipboard,
    exportToCSV,
    downloadFile,
    showLoading,
    hideLoading,
    makeRequest,
    isElementVisible,
    smoothScrollTo
};

console.log('✅ Dashboard Logístico inicializado com sucesso!');
