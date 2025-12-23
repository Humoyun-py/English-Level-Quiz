// API Base URL
const API_BASE = '';

// ========== SESSION MANAGEMENT ==========
async function checkSession() {
    try {
        const response = await fetch(`${API_BASE}/api/session`);
        const data = await response.json();
        
        if (data.authenticated) {
            showMainApp(data.user);
        } else {
            showAuth();
        }
    } catch (error) {
        console.error('Session check failed:', error);
        showAuth();
    }
}

function showAuth() {
    document.getElementById('authSection').classList.remove('hidden');
    document.getElementById('mainSection').classList.add('hidden');
}

function showMainApp(user) {
    document.getElementById('authSection').classList.add('hidden');
    document.getElementById('mainSection').classList.remove('hidden');
    
    if (document.getElementById('welcomeName')) {
        document.getElementById('welcomeName').textContent = user.full_name || user.username;
    }
    if (document.getElementById('userDisplay')) {
        document.getElementById('userDisplay').textContent = user.full_name || user.username;
    }
    
    // Show admin link if user is admin
    if (user.is_admin && document.getElementById('adminLink')) {
        document.getElementById('adminLink').style.display = 'inline-block';
    }
}

// ========== AUTH FUNCTIONS ==========
async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('loginUsername').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        const response = await fetch(`${API_BASE}/api/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showMainApp(data.user);
            showNotification('Login successful!', 'success');
        } else {
            showNotification(data.error || 'Login failed', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showNotification('Login failed. Please try again.', 'error');
    }
}

async function handleRegister(event) {
    event.preventDefault();
    
    const fullName = document.getElementById('regFullName').value;
    const username = document.getElementById('regUsername').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;
    
    try {
        const response = await fetch(`${API_BASE}/api/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name: fullName, username, email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showMainApp(data.user);
            showNotification('Registration successful!', 'success');
        } else {
            showNotification(data.error || 'Registration failed', 'error');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showNotification('Registration failed. Please try again.', 'error');
    }
}

async function handleLogout() {
    try {
        await fetch(`${API_BASE}/api/logout`, { method: 'POST' });
        window.location.href = '/';
    } catch (error) {
        console.error('Logout error:', error);
    }
}

function showLogin() {
    document.getElementById('loginForm').classList.remove('hidden');
    document.getElementById('registerForm').classList.add('hidden');
}

function showRegister() {
    document.getElementById('loginForm').classList.add('hidden');
    document.getElementById('registerForm').classList.remove('hidden');
}

// ========== QUIZ FUNCTIONS ==========
let currentQuiz = null;

async function startQuiz(level = 'full') {
    try {
        const response = await fetch(`${API_BASE}/api/quiz/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ level })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentQuiz = {
                total: data.total_questions,
                current: 1,
                score: 0
            };
            displayQuestion(data.question);
        } else {
            showNotification('Failed to start quiz', 'error');
        }
    } catch (error) {
        console.error('Start quiz error:', error);
        showNotification('Failed to start quiz', 'error');
    }
}

async function submitAnswer(answerIndex) {
    try {
        const response = await fetch(`${API_BASE}/api/quiz/answer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answer: answerIndex })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            if (data.finished) {
                displayResult(data.result);
            } else {
                currentQuiz.current = data.question.number;
                currentQuiz.score = data.question.score;
                displayQuestion(data.question);
            }
        } else {
            showNotification('Failed to submit answer', 'error');
        }
    } catch (error) {
        console.error('Submit answer error:', error);
        showNotification('Failed to submit answer', 'error');
    }
}

function displayQuestion(question) {
    const container = document.getElementById('questionContainer');
    const progressBar = document.getElementById('progressBar');
    const scoreDisplay = document.getElementById('scoreDisplay');
    
    if (progressBar) {
        const progress = (currentQuiz.current / currentQuiz.total) * 100;
        progressBar.style.width = progress + '%';
    }
    
    if (scoreDisplay) {
        scoreDisplay.textContent = `Score: ${currentQuiz.score}/${currentQuiz.current - 1}`;
    }
    
    if (container) {
        container.innerHTML = `
            <div class="question-card">
                <div class="question-number">Question ${question.number} of ${currentQuiz.total}</div>
                <div class="question-text">${question.text}</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressBar" style="width: ${(question.number / currentQuiz.total) * 100}%"></div>
                </div>
                <div class="options-grid">
                    ${question.options.map((option, index) => `
                        <button class="option-btn" onclick="submitAnswer(${index})">
                            ${option}
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
    }
}

function displayResult(result) {
    const container = document.getElementById('resultContainer');
    
    if (container) {
        const percentage = result.percentage.toFixed(2);
        const minutes = Math.floor(result.time_taken / 60);
        const seconds = result.time_taken % 60;
        
        container.innerHTML = `
            <div class="result-card glass-card">
                <h2>🎉 Quiz Complete!</h2>
                <div class="result-score">${result.score}/${result.total}</div>
                <div style="font-size: 1.5rem; margin: 20px 0;">
                    ${percentage}% Correct
                </div>
                <div class="result-level">
                    Your Level: ${result.level}
                </div>
                <div style="margin: 30px 0; opacity: 0.9;">
                    ⏱️ Time: ${minutes}m ${seconds}s
                </div>
                <div class="flex flex-center gap-20" style="margin-top: 30px;">
                    <button onclick="window.location.href='/quiz'" class="btn">Take Another Quiz</button>
                    <button onclick="window.location.href='/results'" class="btn btn-secondary">View Results</button>
                    <button onclick="window.location.href='/leaderboard'" class="btn btn-outline">Leaderboard</button>
                </div>
            </div>
        `;
    }
}

// ========== LEADERBOARD FUNCTIONS ==========
async function loadLeaderboard() {
    try {
        const response = await fetch(`${API_BASE}/api/leaderboard`);
        const data = await response.json();
        
        const container = document.getElementById('leaderboardContainer');
        if (container) {
            container.innerHTML = data.map((entry, index) => {
                const rank = index + 1;
                let rankClass = '';
                if (rank === 1) rankClass = 'gold';
                else if (rank === 2) rankClass = 'silver';
                else if (rank === 3) rankClass = 'bronze';
                
                const rankSymbol = rank <= 3 ? ['🥇', '🥈', '🥉'][rank - 1] : rank;
                
                return `
                    <div class="leaderboard-row">
                        <div class="rank ${rankClass}">${rankSymbol}</div>
                        <div style="font-weight: 600;">${entry.name}</div>
                        <div style="text-align: center;">${entry.level}</div>
                        <div style="text-align: center; font-weight: 600;">${entry.percentage.toFixed(1)}%</div>
                    </div>
                `;
            }).join('');
        }
    } catch (error) {
        console.error('Load leaderboard error:', error);
    }
}

// ========== USER RESULTS FUNCTIONS ==========
async function loadUserResults() {
    try {
        const response = await fetch(`${API_BASE}/api/user/results`);
        const data = await response.json();
        
        const container = document.getElementById('resultsContainer');
        if (container) {
            if (data.length === 0) {
                container.innerHTML = '<p style="text-align: center; opacity: 0.8;">No results yet. Take a quiz to see your results!</p>';
                return;
            }
            
            container.innerHTML = data.map(result => `
                <div class="glass-card" style="margin-bottom: 20px;">
                    <div class="flex" style="justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 1.5rem; font-weight: 700; margin-bottom: 10px;">
                                Level: ${result.level}
                            </div>
                            <div style="opacity: 0.8;">
                                Score: ${result.score}/${result.total} (${result.percentage.toFixed(1)}%)
                            </div>
                            <div style="opacity: 0.7; font-size: 0.9rem; margin-top: 5px;">
                                ⏱️ ${Math.floor(result.time_taken / 60)}m ${result.time_taken % 60}s
                            </div>
                        </div>
                        <div style="text-align: right; opacity: 0.7;">
                            📅 ${new Date(result.date).toLocaleDateString()}
                        </div>
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Load results error:', error);
    }
}

// ========== ADMIN FUNCTIONS ==========
async function loadAdminStats() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/stats`);
        const data = await response.json();
        
        const container = document.getElementById('statsContainer');
        if (container) {
            container.innerHTML = `
                <div class="stat-card">
                    <div class="stat-number">${data.users}</div>
                    <div class="stat-label">Total Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${data.web_users}</div>
                    <div class="stat-label">Web Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${data.questions}</div>
                    <div class="stat-label">Questions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${data.results}</div>
                    <div class="stat-label">Quiz Results</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${data.reports}</div>
                    <div class="stat-label">Reports</div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Load stats error:', error);
    }
}

async function loadQuestions() {
    try {
        const response = await fetch(`${API_BASE}/api/admin/questions`);
        const data = await response.json();
        
        const container = document.getElementById('questionsContainer');
        if (container) {
            container.innerHTML = data.map(q => `
                <div class="question-item">
                    <div>
                        <div style="font-weight: 600; margin-bottom: 5px;">
                            [${q.level}] ${q.question}
                        </div>
                        <div style="font-size: 0.9rem; opacity: 0.8;">
                            ✅ ${q.options[q.correct]}
                        </div>
                    </div>
                    <div class="question-actions">
                        <button onclick="editQuestion(${q.id})" class="btn btn-small">Edit</button>
                        <button onclick="deleteQuestion(${q.id})" class="btn btn-secondary btn-small">Delete</button>
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Load questions error:', error);
    }
}

async function deleteQuestion(id) {
    if (!confirm('Are you sure you want to delete this question?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/admin/questions/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showNotification('Question deleted successfully', 'success');
            loadQuestions();
        } else {
            showNotification('Failed to delete question', 'error');
        }
    } catch (error) {
        console.error('Delete question error:', error);
        showNotification('Failed to delete question', 'error');
    }
}

// ========== UTILITY FUNCTIONS ==========
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 20px 30px;
        background: ${type === 'success' ? 'rgba(76, 175, 80, 0.9)' : type === 'error' ? 'rgba(244, 67, 54, 0.9)' : 'rgba(33, 150, 243, 0.9)'};
        color: white;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
        z-index: 1000;
        animation: fadeIn 0.3s ease-out;
        font-weight: 600;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}
