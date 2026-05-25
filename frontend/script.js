const themeToggleBtn = document.getElementById('theme-toggle');

if (localStorage.getItem('theme') === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    themeToggleBtn.innerText = '☀️';
}

themeToggleBtn.addEventListener('click', () => {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    
    if (isDark) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
        themeToggleBtn.innerText = '🌙';
    } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
        themeToggleBtn.innerText = '☀️';
    }
    
    if (projectChartInstance) {
        loadAnalyticsData();
    }
});

function checkAuth() {
    const token = localStorage.getItem('access_token');
    if (token) {
        document.getElementById('login-overlay').classList.add('hidden');
        initApp();
    } else {
        document.getElementById('login-overlay').classList.remove('hidden');
    }
}

function logout() {
    localStorage.removeItem('access_token');
    checkAuth();
}

async function apiFetch(endpoint, options = {}) {
    const token = localStorage.getItem('access_token');
    const headers = { 
        'Content-Type': 'application/json', 
        ...(options.headers || {}) 
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(endpoint, { ...options, headers });
    
    if (response.status === 401) {
        logout();
        throw new Error("Unauthorized");
    }
    return response;
}

document.getElementById('login-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('username', document.getElementById('username').value);
    formData.append('password', document.getElementById('password').value);
    
    try {
        const response = await fetch('/api/login', { 
            method: 'POST', 
            body: formData 
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access_token);
            document.getElementById('login-overlay').classList.add('hidden');
            initApp();
        } else {
            document.getElementById('login-error').innerText = 'Невірний логін або пароль!';
        }
    } catch (error) { 
        document.getElementById('login-error').innerText = 'Помилка сервера'; 
    }
});

document.getElementById('logout-btn')?.addEventListener('click', logout);

const loginFormObj = document.getElementById('login-form');
const registerFormObj = document.getElementById('register-form');
const authTitle = document.getElementById('auth-title');
const registerMessage = document.getElementById('register-message');

document.getElementById('show-register-btn')?.addEventListener('click', (e) => {
    e.preventDefault(); 
    loginFormObj.classList.add('hidden'); 
    registerFormObj.classList.remove('hidden'); 
    authTitle.innerText = 'Реєстрація';
});

document.getElementById('show-login-btn')?.addEventListener('click', (e) => {
    e.preventDefault(); 
    registerFormObj.classList.add('hidden'); 
    loginFormObj.classList.remove('hidden'); 
    authTitle.innerText = 'Вхід у систему';
});

document.getElementById('register-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const regData = { 
        username: document.getElementById('reg-username').value, 
        password: document.getElementById('reg-password').value 
    };
    
    const response = await fetch('/api/register', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify(regData) 
    });
    
    if (response.ok) {
        registerMessage.style.color = '#2ecc71'; 
        registerMessage.innerText = 'Успішно! Тепер ви можете увійти.';
        document.getElementById('register-form').reset(); 
        
        setTimeout(() => { 
            document.getElementById('show-login-btn').click(); 
        }, 2000);
    } else {
        const error = await response.json(); 
        registerMessage.style.color = '#e74c3c'; 
        registerMessage.innerText = error.detail || 'Помилка';
    }
});

function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.add('hidden');
    });
    document.getElementById(tabId)?.classList.remove('hidden');
    
    if (tabId === 'tab-materials') loadMaterials();
    if (tabId === 'tab-projects') loadProjects();
    if (tabId === 'tab-logistics') loadLogisticsData();
    if (tabId === 'tab-analytics') loadAnalyticsData();
}

document.getElementById('nav-materials')?.addEventListener('click', () => showTab('tab-materials'));
document.getElementById('nav-projects')?.addEventListener('click', () => showTab('tab-projects'));
document.getElementById('nav-logistics')?.addEventListener('click', () => showTab('tab-logistics'));
document.getElementById('nav-analytics')?.addEventListener('click', () => showTab('tab-analytics'));

async function loadMaterials() {
    const response = await apiFetch('/api/materials'); 
    const materials = await response.json();
    const tbody = document.getElementById('materials-table-body'); 
    tbody.innerHTML = '';
    
    materials.forEach(mat => {
        tbody.innerHTML += `
            <tr>
                <td>${mat.id}</td>
                <td>${mat.name}</td>
                <td><strong>${mat.quantity}</strong> ${mat.unit}</td>
                <td><button class="btn-delete" onclick="deleteMaterial(${mat.id})">Видалити</button></td>
            </tr>
        `;
    });
}

window.deleteMaterial = async function(id) {
    if (!(await CustomConfirm('Ви впевнені, що хочете видалити цей матеріал?', 'Підтвердження', true))) return;
    
    const response = await apiFetch(`/api/materials/${id}`, { method: 'DELETE' }); 
    if (response.ok) {
        loadMaterials();
    }
};

document.getElementById('add-material-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = { 
        name: document.getElementById('mat-name').value, 
        quantity: parseFloat(document.getElementById('mat-quantity').value), 
        unit: document.getElementById('mat-unit').value 
    };
    
    const response = await apiFetch('/api/materials', { 
        method: 'POST', 
        body: JSON.stringify(data) 
    });
    
    if (response.ok) { 
        e.target.reset(); 
        await CustomAlert('Матеріал додано!', 'Успіх'); 
        loadMaterials(); 
    }
});

async function loadProjects() {
    const response = await apiFetch('/api/projects'); 
    const projects = await response.json();
    
    const activeList = document.getElementById('active-projects-list'); 
    const archivedList = document.getElementById('archived-projects-list');
    activeList.innerHTML = ''; 
    archivedList.innerHTML = '';
    
    projects.forEach(proj => {
        const div = document.createElement('div'); 
        div.className = 'project-card';
        
        if (proj.status === 'archived') {
            div.style.borderLeft = '4px solid var(--text-muted)';
        }
        
        let transfersHtml = '';
        if (proj.transfers && proj.transfers.length > 0) {
            transfersHtml = `
                <div class="transfers-box">
                    <ul>
                        ${proj.transfers.map(t => `<li>${t.material_name}: <b>${t.quantity}</b> ${t.unit}</li>`).join('')}
                    </ul>
                </div>
            `;
        } else {
            transfersHtml = `<div class="transfers-box" style="color: var(--text-muted);">Матеріалів ще не видано</div>`;
        }

        div.innerHTML = `
            <h3>${proj.name}</h3>
            <p>Адреса: ${proj.address}</p>
            ${transfersHtml}
            <div class="project-actions">
                <button class="btn-archive-toggle" onclick="archiveProject(${proj.id})">
                    ${proj.status === 'active' ? 'В архів' : 'Відновити'}
                </button>
                <button class="btn-delete" onclick="deleteProject(${proj.id})">Видалити</button>
            </div>
        `;
        
        if (proj.status === 'active') {
            activeList.appendChild(div);
        } else {
            archivedList.appendChild(div);
        }
    });
}

document.getElementById('add-project-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = { 
        name: document.getElementById('proj-name').value, 
        address: document.getElementById('proj-address').value 
    };
    
    const response = await apiFetch('/api/projects', { 
        method: 'POST', 
        body: JSON.stringify(data) 
    });
    
    if (response.ok) { 
        e.target.reset(); 
        await CustomAlert("Об'єкт створено!", 'Успіх'); 
        loadProjects(); 
    }
});

window.archiveProject = async function(id) { 
    await apiFetch(`/api/projects/${id}/archive`, { method: 'POST' }); 
    loadProjects(); 
};

window.deleteProject = async function(id) {
    if (!(await CustomConfirm('Видалити цей проєкт та всю його історію?', 'Попередження', true))) return;
    
    await apiFetch(`/api/projects/${id}`, { method: 'DELETE' }); 
    loadProjects();
};

async function loadLogisticsData() {
    const [matRes, projRes] = await Promise.all([
        apiFetch('/api/materials'), 
        apiFetch('/api/projects')
    ]);
    
    const materials = await matRes.json(); 
    const projects = await projRes.json();
    
    const matSelect = document.getElementById('transfer-material-id'); 
    const projSelect = document.getElementById('transfer-project-id');
    
    matSelect.innerHTML = '<option value="">Оберіть матеріал...</option>';
    materials.forEach(m => {
        matSelect.innerHTML += `<option value="${m.id}">${m.name} (Залишок: ${m.quantity} ${m.unit})</option>`;
    });
    
    projSelect.innerHTML = '<option value="">Оберіть проєкт...</option>';
    projects.forEach(p => { 
        if (p.status === 'active') {
            projSelect.innerHTML += `<option value="${p.id}">${p.name}</option>`; 
        }
    });
}

document.getElementById('transfer-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = { 
        material_id: parseInt(document.getElementById('transfer-material-id').value), 
        project_id: parseInt(document.getElementById('transfer-project-id').value), 
        quantity: parseFloat(document.getElementById('transfer-quantity').value) 
    };
    
    const response = await apiFetch('/api/transfer', { 
        method: 'POST', 
        body: JSON.stringify(data) 
    });
    
    if (response.ok) { 
        e.target.reset(); 
        await CustomAlert('Матеріал успішно списано!', 'Успіх'); 
        loadLogisticsData(); 
    } else { 
        const err = await response.json(); 
        await CustomAlert(`Помилка: ${err.detail}`, 'Помилка'); 
    }
});

document.getElementById('download-report-btn')?.addEventListener('click', async () => {
    const response = await fetch('/api/reports/materials', { 
        headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` } 
    });
    
    if (!response.ok) {
        return CustomAlert('Помилка завантаження.', 'Помилка');
    }
    
    const blob = await response.blob(); 
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a'); 
    
    a.href = url; 
    a.download = `materials_report_${new Date().toISOString().split('T')[0]}.csv`;
    
    document.body.appendChild(a); 
    a.click(); 
    window.URL.revokeObjectURL(url); 
    document.body.removeChild(a);
});

function initApp() { 
    showTab('tab-materials'); 
}

document.addEventListener('DOMContentLoaded', checkAuth);

function CustomDialog(message, title = 'Повідомлення', isConfirm = false, isDanger = false) {
    return new Promise((resolve) => {
        const modal = document.getElementById('custom-modal'); 
        const btnConfirm = document.getElementById('modal-btn-confirm'); 
        const btnCancel = document.getElementById('modal-btn-cancel');
        
        document.getElementById('modal-title').innerText = title; 
        document.getElementById('modal-message').innerText = message;
        
        btnConfirm.innerText = isConfirm ? 'Так' : 'ОК'; 
        btnConfirm.className = isDanger ? 'btn-danger' : 'btn-confirm';
        
        if (isConfirm) {
            btnCancel.classList.remove('hidden');
        } else {
            btnCancel.classList.add('hidden');
        }
        
        modal.classList.remove('hidden');
        
        const cleanup = () => { 
            modal.classList.add('hidden'); 
            btnConfirm.onclick = null; 
            btnCancel.onclick = null; 
        };
        
        btnConfirm.onclick = () => { cleanup(); resolve(true); }; 
        btnCancel.onclick = () => { cleanup(); resolve(false); };
    });
}

window.CustomAlert = (message, title) => CustomDialog(message, title, false);
window.CustomConfirm = (message, title, isDanger) => CustomDialog(message, title, true, isDanger);

let projectChartInstance = null;

async function loadAnalyticsData() {
    try {
        const response = await apiFetch('/api/analytics'); 
        const data = await response.json();
        const forecastList = document.getElementById('forecast-list');
        
        if (data.forecast.length === 0) { 
            forecastList.innerHTML = '<div class="forecast-safe">Усі матеріали в достатній кількості.</div>'; 
        } else {
            forecastList.innerHTML = data.forecast.map(f => `
                <div class="forecast-item">
                    Матеріал <b>${f.material_name}</b> може закінчитися через <strong>${f.days_left} днів</strong>.<br>
                    <span style="font-size: 12px;">Залишок: ${f.current_quantity} | Витрата: ~${f.daily_burn_rate}/день</span>
                </div>
            `).join('');
        }

        const ctx = document.getElementById('projectChart'); 
        if (!ctx) return;
        
        if (projectChartInstance) {
            projectChartInstance.destroy();
        }
        
        const labels = data.distribution.map(d => d.project_name); 
        const chartData = data.distribution.map(d => d.total_received);
        
        if (labels.length === 0) { 
            ctx.parentElement.innerHTML = '<p style="text-align: center; margin-top: 50px;">Немає даних для графіка</p>'; 
            return; 
        }

        const isDarkTheme = document.documentElement.getAttribute('data-theme') === 'dark';
        Chart.defaults.color = isDarkTheme ? '#94a3b8' : '#7f8c8d';

        projectChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{ 
                    data: chartData, 
                    backgroundColor: ['#3498db', '#2ecc71', '#f1c40f', '#e74c3c', '#9b59b6', '#1abc9c'], 
                    borderWidth: 0 
                }]
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false, 
                plugins: { 
                    legend: { position: 'bottom' } 
                } 
            }
        });
    } catch (error) { 
        document.getElementById('forecast-list').innerHTML = '<p class="error-msg">Помилка завантаження.</p>'; 
    }
}