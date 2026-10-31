/**
 * CYBER VIPER - Frontend Game Engine & SQLite Match History Client
 */

// ================= CONFIGURATION & CONSTANTS =================
const GRID_SIZE = 25; // 25x25 grid cells
const CANVAS_SIZE = 600;
const CELL_SIZE = CANVAS_SIZE / GRID_SIZE;

const DIFFICULTY_SETTINGS = {
  Easy: 130,     // ms per tick
  Normal: 100,
  Hard: 70,
  Insane: 50
};

// ================= SOUND SYNTHESIZER (WEB AUDIO API) =================
class SoundFX {
  constructor() {
    this.ctx = null;
    this.enabled = localStorage.getItem('sound_enabled') !== 'false';
  }

  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  toggle() {
    this.enabled = !this.enabled;
    localStorage.setItem('sound_enabled', this.enabled);
    return this.enabled;
  }

  playEat() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    const now = this.ctx.currentTime;

    osc.type = 'sine';
    osc.frequency.setValueAtTime(440, now);
    osc.frequency.exponentialRampToValueAtTime(880, now + 0.1);

    gain.gain.setValueAtTime(0.15, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.1);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(now);
    osc.stop(now + 0.1);
  }

  playGolden() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6
    notes.forEach((freq, idx) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      const startTime = this.ctx.currentTime + idx * 0.05;

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(freq, startTime);
      gain.gain.setValueAtTime(0.2, startTime);
      gain.gain.exponentialRampToValueAtTime(0.01, startTime + 0.12);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(startTime);
      osc.stop(startTime + 0.12);
    });
  }

  playGameOver() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    const now = this.ctx.currentTime;

    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(320, now);
    osc.frequency.exponentialRampToValueAtTime(60, now + 0.45);

    gain.gain.setValueAtTime(0.25, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.45);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(now);
    osc.stop(now + 0.45);
  }

  playClick() {
    if (!this.enabled) return;
    this.init();
    if (!this.ctx) return;

    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    const now = this.ctx.currentTime;

    osc.type = 'sine';
    osc.frequency.setValueAtTime(1200, now);
    gain.gain.setValueAtTime(0.08, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start(now);
    osc.stop(now + 0.04);
  }
}

const sfx = new SoundFX();

// ================= GAME ENGINE =================
class GameEngine {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');

    this.snake = [];
    this.direction = { x: 1, y: 0 };
    this.nextDirection = { x: 1, y: 0 };

    this.food = null;
    this.goldenFood = null;
    this.goldenTimer = 0;

    this.mode = 'Classic';
    this.difficulty = 'Normal';

    this.score = 0;
    this.apples = 0;
    this.highScore = 0;
    this.startTime = 0;
    this.duration = 0;

    this.state = 'IDLE'; // IDLE, RUNNING, PAUSED, GAMEOVER
    this.particles = [];
    this.lastTick = 0;
    this.gameLoopId = null;

    this.initEvents();
  }

  initEvents() {
    window.addEventListener('keydown', (e) => {
      // Prevent browser scroll on arrow keys or space
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', ' '].includes(e.key)) {
        e.preventDefault();
      }

      if (e.key === ' ' || e.code === 'Space') {
        if (this.state === 'RUNNING') this.pause();
        else if (this.state === 'PAUSED') this.resume();
        return;
      }

      if (this.state !== 'RUNNING') return;

      const key = e.key.toLowerCase();
      if ((key === 'arrowup' || key === 'w') && this.direction.y === 0) {
        this.nextDirection = { x: 0, y: -1 };
      } else if ((key === 'arrowdown' || key === 's') && this.direction.y === 0) {
        this.nextDirection = { x: 0, y: 1 };
      } else if ((key === 'arrowleft' || key === 'a') && this.direction.x === 0) {
        this.nextDirection = { x: -1, y: 0 };
      } else if ((key === 'arrowright' || key === 'd') && this.direction.x === 0) {
        this.nextDirection = { x: 1, y: 0 };
      }
    });
  }

  setDirection(dirName) {
    if (this.state !== 'RUNNING') return;
    if (dirName === 'up' && this.direction.y === 0) this.nextDirection = { x: 0, y: -1 };
    if (dirName === 'down' && this.direction.y === 0) this.nextDirection = { x: 0, y: 1 };
    if (dirName === 'left' && this.direction.x === 0) this.nextDirection = { x: -1, y: 0 };
    if (dirName === 'right' && this.direction.x === 0) this.nextDirection = { x: 1, y: 0 };
  }

  start(mode, difficulty) {
    this.mode = mode || this.mode;
    this.difficulty = difficulty || this.difficulty;

    // Reset snake at center
    const startX = Math.floor(GRID_SIZE / 2);
    const startY = Math.floor(GRID_SIZE / 2);
    this.snake = [
      { x: startX, y: startY },
      { x: startX - 1, y: startY },
      { x: startX - 2, y: startY }
    ];
    this.direction = { x: 1, y: 0 };
    this.nextDirection = { x: 1, y: 0 };

    this.score = 0;
    this.apples = 0;
    this.startTime = performance.now();
    this.duration = 0;
    this.particles = [];
    this.goldenFood = null;
    this.goldenTimer = 0;

    this.spawnFood();
    this.state = 'RUNNING';
    this.lastTick = performance.now();

    updateHUD(this);
    hideOverlays();

    if (this.gameLoopId) cancelAnimationFrame(this.gameLoopId);
    this.loop(performance.now());
  }

  pause() {
    if (this.state !== 'RUNNING') return;
    this.state = 'PAUSED';
    document.getElementById('pauseOverlay').classList.add('active');
  }

  resume() {
    if (this.state !== 'PAUSED') return;
    this.state = 'RUNNING';
    this.lastTick = performance.now();
    document.getElementById('pauseOverlay').classList.remove('active');
    this.loop(performance.now());
  }

  spawnFood() {
    const freeCells = [];
    for (let x = 0; x < GRID_SIZE; x++) {
      for (let y = 0; y < GRID_SIZE; y++) {
        const occupied = this.snake.some(segment => segment.x === x && segment.y === y);
        if (!occupied) freeCells.push({ x, y });
      }
    }
    if (freeCells.length === 0) return;
    this.food = freeCells[Math.floor(Math.random() * freeCells.length)];

    // Occasional Golden Apple spawn (1 in 4 chance after at least 3 apples eaten)
    if (this.apples >= 3 && Math.random() < 0.28 && !this.goldenFood) {
      const remaining = freeCells.filter(c => c.x !== this.food.x || c.y !== this.food.y);
      if (remaining.length > 0) {
        this.goldenFood = remaining[Math.floor(Math.random() * remaining.length)];
        this.goldenTimer = 60; // ~60 ticks countdown
      }
    }
  }

  spawnParticles(x, y, color, count = 16) {
    const px = (x + 0.5) * CELL_SIZE;
    const py = (y + 0.5) * CELL_SIZE;
    for (let i = 0; i < count; i++) {
      const angle = (Math.PI * 2 / count) * i + (Math.random() - 0.5) * 0.5;
      const speed = 1.5 + Math.random() * 3.5;
      this.particles.push({
        x: px,
        y: py,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        size: 3 + Math.random() * 3,
        alpha: 1,
        color: color
      });
    }
  }

  update() {
    this.direction = this.nextDirection;
    const head = { ...this.snake[0] };
    head.x += this.direction.x;
    head.y += this.direction.y;

    // Boundary Handling
    if (this.mode === 'Portal') {
      // Wrap around grid boundaries seamlessly
      if (head.x < 0) head.x = GRID_SIZE - 1;
      if (head.x >= GRID_SIZE) head.x = 0;
      if (head.y < 0) head.y = GRID_SIZE - 1;
      if (head.y >= GRID_SIZE) head.y = 0;
    } else {
      // Classic & Speed Rush: Wall collision results in game over
      if (head.x < 0 || head.x >= GRID_SIZE || head.y < 0 || head.y >= GRID_SIZE) {
        this.gameOver('Hit Wall');
        return;
      }
    }

    // Self Collision check
    for (let i = 0; i < this.snake.length; i++) {
      if (head.x === this.snake[i].x && head.y === this.snake[i].y) {
        this.gameOver('Collided with Self');
        return;
      }
    }

    this.snake.unshift(head);

    // Check regular food consumption
    let eaten = false;
    if (this.food && head.x === this.food.x && head.y === this.food.y) {
      eaten = true;
      this.apples++;
      const multiplier = this.mode === 'Speed Rush' ? 2 : 1;
      this.score += 10 * multiplier;
      this.spawnParticles(this.food.x, this.food.y, '#ff007f', 16);
      sfx.playEat();
      this.spawnFood();
    }

    // Check golden food consumption
    if (this.goldenFood && head.x === this.goldenFood.x && head.y === this.goldenFood.y) {
      eaten = true;
      this.apples++;
      this.score += 35;
      this.spawnParticles(this.goldenFood.x, this.goldenFood.y, '#ffd700', 25);
      sfx.playGolden();
      this.goldenFood = null;
    }

    // If no food eaten, pop tail
    if (!eaten) {
      this.snake.pop();
    }

    // Golden food expiration countdown
    if (this.goldenFood) {
      this.goldenTimer--;
      if (this.goldenTimer <= 0) {
        this.goldenFood = null;
      }
    }

    // Update real-time duration
    this.duration = (performance.now() - this.startTime) / 1000;
    updateHUD(this);
  }

  gameOver(reason) {
    this.state = 'GAMEOVER';
    sfx.playGameOver();
    this.spawnParticles(this.snake[0].x, this.snake[0].y, '#ff007f', 30);

    const playerName = document.getElementById('playerNameInput').value.trim() || 'Player 1';
    
    // Save to backend database
    saveGameRecord({
      player_name: playerName,
      game_mode: this.mode,
      difficulty: this.difficulty,
      score: this.score,
      apples_eaten: this.apples,
      duration_seconds: this.duration,
      result: reason
    });

    showGameOverOverlay(this);
  }

  loop(timestamp) {
    if (this.state === 'RUNNING') {
      let interval = DIFFICULTY_SETTINGS[this.difficulty] || 100;
      if (this.mode === 'Speed Rush') {
        // Accelerate as apples are eaten
        interval = Math.max(45, interval - Math.floor(this.apples * 1.5));
      }

      if (timestamp - this.lastTick >= interval) {
        this.update();
        this.lastTick = timestamp;
      }
    }

    this.render();
    if (this.state !== 'IDLE') {
      this.gameLoopId = requestAnimationFrame((ts) => this.loop(ts));
    }
  }

  render() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

    // 1. Draw Subtle Grid
    ctx.strokeStyle = 'rgba(0, 243, 255, 0.04)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= GRID_SIZE; i++) {
      ctx.beginPath();
      ctx.moveTo(i * CELL_SIZE, 0);
      ctx.lineTo(i * CELL_SIZE, CANVAS_SIZE);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(0, i * CELL_SIZE);
      ctx.lineTo(CANVAS_SIZE, i * CELL_SIZE);
      ctx.stroke();
    }

    // 2. Draw Food (Neon Glowing Red/Pink Apple)
    if (this.food) {
      const fx = this.food.x * CELL_SIZE + CELL_SIZE / 2;
      const fy = this.food.y * CELL_SIZE + CELL_SIZE / 2;
      const radius = CELL_SIZE * 0.38;

      ctx.save();
      ctx.shadowColor = '#ff007f';
      ctx.shadowBlur = 15;
      ctx.fillStyle = '#ff007f';
      ctx.beginPath();
      ctx.arc(fx, fy, radius, 0, Math.PI * 2);
      ctx.fill();

      // Inner highlight
      ctx.fillStyle = '#fff';
      ctx.beginPath();
      ctx.arc(fx - radius * 0.3, fy - radius * 0.3, radius * 0.25, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    // 3. Draw Golden Food if active
    if (this.goldenFood) {
      const gx = this.goldenFood.x * CELL_SIZE + CELL_SIZE / 2;
      const gy = this.goldenFood.y * CELL_SIZE + CELL_SIZE / 2;
      const radius = CELL_SIZE * 0.42;

      ctx.save();
      ctx.shadowColor = '#ffd700';
      ctx.shadowBlur = 20;
      ctx.fillStyle = '#ffd700';
      ctx.beginPath();
      ctx.arc(gx, gy, radius, 0, Math.PI * 2);
      ctx.fill();

      // Pulsing star ring
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(gx, gy, radius * 0.6, 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }

    // 4. Draw Snake Body & Head
    for (let i = this.snake.length - 1; i >= 0; i--) {
      const segment = this.snake[i];
      const sx = segment.x * CELL_SIZE;
      const sy = segment.y * CELL_SIZE;
      const isHead = i === 0;

      ctx.save();
      if (isHead) {
        ctx.shadowColor = '#00f3ff';
        ctx.shadowBlur = 18;
        ctx.fillStyle = '#00f3ff';
      } else {
        const ratio = 1 - (i / this.snake.length) * 0.65;
        ctx.shadowColor = 'rgba(0, 243, 255, 0.4)';
        ctx.shadowBlur = 8;
        ctx.fillStyle = `rgba(0, 243, 255, ${ratio})`;
      }

      const padding = 2;
      const cornerRadius = isHead ? 6 : 4;
      drawRoundedRect(ctx, sx + padding, sy + padding, CELL_SIZE - padding * 2, CELL_SIZE - padding * 2, cornerRadius);
      ctx.fill();

      // Draw eyes on head
      if (isHead) {
        ctx.fillStyle = '#05080e';
        const eyeSize = 3;
        const offset = 6;
        if (this.direction.x === 1) { // Right
          ctx.fillRect(sx + CELL_SIZE - offset, sy + offset, eyeSize, eyeSize);
          ctx.fillRect(sx + CELL_SIZE - offset, sy + CELL_SIZE - offset - eyeSize, eyeSize, eyeSize);
        } else if (this.direction.x === -1) { // Left
          ctx.fillRect(sx + offset, sy + offset, eyeSize, eyeSize);
          ctx.fillRect(sx + offset, sy + CELL_SIZE - offset - eyeSize, eyeSize, eyeSize);
        } else if (this.direction.y === -1) { // Up
          ctx.fillRect(sx + offset, sy + offset, eyeSize, eyeSize);
          ctx.fillRect(sx + CELL_SIZE - offset - eyeSize, sy + offset, eyeSize, eyeSize);
        } else { // Down
          ctx.fillRect(sx + offset, sy + CELL_SIZE - offset - eyeSize, eyeSize, eyeSize);
          ctx.fillRect(sx + CELL_SIZE - offset - eyeSize, sy + CELL_SIZE - offset - eyeSize, eyeSize, eyeSize);
        }
      }
      ctx.restore();
    }

    // 5. Draw Particle Bursts
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.x += p.vx;
      p.y += p.vy;
      p.alpha -= 0.025;
      p.size = Math.max(0.5, p.size * 0.96);

      if (p.alpha <= 0) {
        this.particles.splice(i, 1);
        continue;
      }

      ctx.save();
      ctx.globalAlpha = p.alpha;
      ctx.fillStyle = p.color;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  }
}

// Utility: Draw rounded rectangle
function drawRoundedRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}

// ================= HUD & UI CONTROLS =================
const canvas = document.getElementById('gameCanvas');
const engine = new GameEngine(canvas);

function updateHUD(eng) {
  document.getElementById('scoreDisplay').textContent = eng.score;
  document.getElementById('applesDisplay').textContent = eng.apples;
  document.getElementById('highScoreDisplay').textContent = Math.max(eng.score, eng.highScore);

  const mins = Math.floor(eng.duration / 60);
  const secs = Math.floor(eng.duration % 60);
  document.getElementById('timerDisplay').textContent = 
    `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function hideOverlays() {
  document.querySelectorAll('.canvas-overlay').forEach(el => el.classList.remove('active'));
}

function showGameOverOverlay(eng) {
  document.getElementById('finalScore').textContent = eng.score;
  document.getElementById('finalApples').textContent = eng.apples;
  document.getElementById('finalDuration').textContent = `${Math.round(eng.duration)}s`;
  document.getElementById('gameOverOverlay').classList.add('active');
}

// ================= DATABASE API CLIENT =================
const API_BASE = '/api';

async function fetchStats() {
  try {
    const res = await fetch(`${API_BASE}/stats`);
    const data = await res.json();
    if (data.success && data.stats) {
      const s = data.stats;
      document.getElementById('statHighScore').textContent = s.high_score;
      document.getElementById('statTotalGames').textContent = s.total_games;
      document.getElementById('statTotalApples').textContent = s.total_apples;
      
      const mins = Math.round(s.total_seconds / 60);
      document.getElementById('statTotalTime').textContent = `${mins}m`;

      engine.highScore = s.high_score;
      document.getElementById('highScoreDisplay').textContent = s.high_score;
    }
  } catch (err) {
    console.error('Failed to fetch stats:', err);
  }
}

async function fetchLeaderboard() {
  const tbody = document.getElementById('leaderboardTableBody');
  try {
    const res = await fetch(`${API_BASE}/leaderboard?limit=10`);
    const data = await res.json();
    if (data.success && data.leaderboard) {
      if (data.leaderboard.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No leaderboard records yet. Play your first run!</td></tr>';
        return;
      }
      
      tbody.innerHTML = data.leaderboard.map((row, index) => {
        let medal = `#${index + 1}`;
        if (index === 0) medal = '<span class="medal-gold">🥇 1st</span>';
        else if (index === 1) medal = '<span class="medal-silver">🥈 2nd</span>';
        else if (index === 2) medal = '<span class="medal-bronze">🥉 3rd</span>';

        const modeBadgeClass = row.game_mode === 'Speed Rush' 
          ? 'badge-mode-speed' 
          : (row.game_mode === 'Portal' ? 'badge-mode-portal' : 'badge-mode-classic');

        return `
          <tr>
            <td>${medal}</td>
            <td style="color:#fff; font-weight:700;">${escapeHtml(row.player_name)}</td>
            <td class="neon-cyan" style="font-size:16px;">${row.score}</td>
            <td><span class="badge ${modeBadgeClass}">${escapeHtml(row.game_mode)}</span></td>
            <td><span class="badge">${escapeHtml(row.difficulty)}</span></td>
            <td style="color:var(--text-muted); font-size:12px;">${row.formatted_time || 'Just now'}</td>
          </tr>
        `;
      }).join('');
    }
  } catch (err) {
    console.error('Failed to fetch leaderboard:', err);
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">Error loading leaderboard.</td></tr>';
  }
}

async function fetchHistory() {
  const tbody = document.getElementById('historyTableBody');
  const mode = document.getElementById('modeFilterSelect').value;
  try {
    const query = mode && mode !== 'All' ? `?mode=${encodeURIComponent(mode)}` : '';
    const res = await fetch(`${API_BASE}/history${query}`);
    const data = await res.json();

    if (data.success && data.history) {
      if (data.history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No match history recorded yet. Complete a game to save!</td></tr>';
        return;
      }

      tbody.innerHTML = data.history.map(row => {
        const modeBadgeClass = row.game_mode === 'Speed Rush' 
          ? 'badge-mode-speed' 
          : (row.game_mode === 'Portal' ? 'badge-mode-portal' : 'badge-mode-classic');

        return `
          <tr>
            <td style="color:var(--text-muted); font-size:12px;">${row.formatted_time || 'Just now'}</td>
            <td style="color:#fff;">${escapeHtml(row.player_name)}</td>
            <td><span class="badge ${modeBadgeClass}">${escapeHtml(row.game_mode)}</span></td>
            <td><span class="badge">${escapeHtml(row.difficulty)}</span></td>
            <td class="neon-cyan">${row.score}</td>
            <td class="neon-pink">${row.apples_eaten}</td>
            <td>${row.duration_seconds}s</td>
          </tr>
        `;
      }).join('');
    }
  } catch (err) {
    console.error('Failed to fetch history:', err);
    tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Error loading history.</td></tr>';
  }
}

async function saveGameRecord(payload) {
  const syncStatus = document.getElementById('liveSyncStatus');
  const dbStatus = document.getElementById('dbStatus');
  const badge = document.getElementById('newHighBadge');

  syncStatus.textContent = 'Saving...';
  syncStatus.style.color = '#ffd700';

  try {
    const res = await fetch(`${API_BASE}/history`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.success) {
      syncStatus.textContent = 'Synchronized';
      syncStatus.style.color = 'var(--neon-green)';
      dbStatus.textContent = 'SAVED ✓';
      dbStatus.className = 'val neon-green';

      if (data.record && data.record.is_new_high) {
        badge.style.display = 'block';
        sfx.playGolden();
      } else {
        badge.style.display = 'none';
      }

      // Refresh all lists and stats
      fetchStats();
      fetchLeaderboard();
      fetchHistory();
    } else {
      throw new Error(data.error || 'Server rejected save');
    }
  } catch (err) {
    console.error('Save failed:', err);
    syncStatus.textContent = 'Sync Failed';
    syncStatus.style.color = 'var(--neon-pink)';
    dbStatus.textContent = 'OFFLINE';
    dbStatus.className = 'val neon-pink';
  }
}

async function clearAllHistory() {
  if (!confirm('Are you sure you want to delete all match history and database records? This cannot be undone.')) {
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/clear`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      fetchStats();
      fetchLeaderboard();
      fetchHistory();
    }
  } catch (err) {
    alert('Failed to clear history: ' + err.message);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>"']/g, (m) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[m]));
}

// ================= SETUP EVENT LISTENERS =================
document.addEventListener('DOMContentLoaded', () => {
  // Restore player name & sound preferences
  const savedName = localStorage.getItem('player_name');
  if (savedName) document.getElementById('playerNameInput').value = savedName;

  document.getElementById('playerNameInput').addEventListener('change', (e) => {
    localStorage.setItem('player_name', e.target.value.trim());
  });

  const soundBtn = document.getElementById('soundToggleBtn');
  soundBtn.textContent = sfx.enabled ? '🔊' : '🔇';
  soundBtn.addEventListener('click', () => {
    const isEnabled = sfx.toggle();
    soundBtn.textContent = isEnabled ? '🔊' : '🔇';
    sfx.playClick();
  });

  // Segmented Mode Controls
  let selectedMode = 'Classic';
  document.querySelectorAll('#modeSelector .seg-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#modeSelector .seg-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedMode = btn.dataset.mode;
      sfx.playClick();
    });
  });

  // Segmented Difficulty Controls
  let selectedDiff = 'Normal';
  document.querySelectorAll('#diffSelector .seg-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#diffSelector .seg-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedDiff = btn.dataset.diff;
      sfx.playClick();
    });
  });

  // Buttons in Overlays
  document.getElementById('startGameBtn').addEventListener('click', () => {
    sfx.playClick();
    engine.start(selectedMode, selectedDiff);
  });

  document.getElementById('resumeGameBtn').addEventListener('click', () => {
    sfx.playClick();
    engine.resume();
  });

  document.getElementById('quitGameBtn').addEventListener('click', () => {
    sfx.playClick();
    hideOverlays();
    document.getElementById('startOverlay').classList.add('active');
    engine.state = 'IDLE';
  });

  document.getElementById('restartGameBtn').addEventListener('click', () => {
    sfx.playClick();
    engine.start(selectedMode, selectedDiff);
  });

  document.getElementById('changeModeBtn').addEventListener('click', () => {
    sfx.playClick();
    hideOverlays();
    document.getElementById('startOverlay').classList.add('active');
  });

  // Virtual Controls
  document.getElementById('dpadUp').addEventListener('click', () => engine.setDirection('up'));
  document.getElementById('dpadDown').addEventListener('click', () => engine.setDirection('down'));
  document.getElementById('dpadLeft').addEventListener('click', () => engine.setDirection('left'));
  document.getElementById('dpadRight').addEventListener('click', () => engine.setDirection('right'));
  document.getElementById('dpadPause').addEventListener('click', () => {
    if (engine.state === 'RUNNING') engine.pause();
    else if (engine.state === 'PAUSED') engine.resume();
  });

  // Tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.dataset.tab;
      document.getElementById(targetId).classList.add('active');
      sfx.playClick();
    });
  });

  // Filter & Refresh & Clear
  document.getElementById('modeFilterSelect').addEventListener('change', () => fetchHistory());
  document.getElementById('refreshBtn').addEventListener('click', () => {
    sfx.playClick();
    fetchStats();
    fetchLeaderboard();
    fetchHistory();
  });
  document.getElementById('clearHistoryBtn').addEventListener('click', () => clearAllHistory());

  // Initial Fetch
  fetchStats();
  fetchLeaderboard();
  fetchHistory();
});
