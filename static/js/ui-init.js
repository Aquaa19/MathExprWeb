// static/js/ui-init.js
(() => {
  // Quick safe-get
  const $ = id => document.getElementById(id);

  // Elements
  const themeToggle = $('themeToggle');
  const particles = $('particles');
  const quickExamples = $('quickExamples');
  const expr = $('expr');
  const quickButtons = document.querySelectorAll('.quick-btn');
  const modeButtonsContainer = document.querySelector('.mode-selector');
  const modeButtons = document.querySelectorAll('.mode-btn');
  const subVars = $('subVars');
  const varsInput = $('vars');

  // theme toggle (uses data-theme on body)
  function setTheme(t) {
    document.body.setAttribute('data-theme', t);
    themeToggle.textContent = t === 'dark' ? '🌙' : '☀️';
    themeToggle.setAttribute('aria-pressed', t === 'light' ? 'true' : 'false');
    // store
    localStorage.setItem('math_theme', t);
  }
  function toggleTheme() {
    const cur = document.body.getAttribute('data-theme') || 'dark';
    setTheme(cur === 'dark' ? 'light' : 'dark');
  }
  themeToggle?.addEventListener('click', toggleTheme);
  // restore theme
  const savedTheme = localStorage.getItem('math_theme') || 'dark';
  setTheme(savedTheme);

  // create decorative particles (non-essential)
  function createParticles(n = 18) {
    if (!particles) return;
    for (let i=0;i<n;i++){
      const el = document.createElement('div');
      el.className = 'particle';
      el.style.left = Math.random()*100 + '%';
      el.style.top = Math.random()*100 + '%';
      el.style.opacity = 0.06 + Math.random()*0.2;
      particles.appendChild(el);
    }
  }
  createParticles();

  // Mode button behavior: update visuals and show/hide var input
  function setActiveMode(mode) {
    modeButtons.forEach(b => {
      if (b.dataset.mode === mode) {
        b.classList.add('active');
      } else {
        b.classList.remove('active');
      }
    });
    // show substitute input
    if (subVars) subVars.style.display = mode === 'substitute' ? 'block' : 'none';
    // update description (if modeDescription available, app.js will replace it too)
    const desc = document.getElementById('modeDescription');
    const map = {
      expand: ['Expand Mode', 'Expands algebraic expressions. Example: (x+2)(x+3) → x² + 5x + 6'],
      simplify: ['Simplify Mode', 'Simplifies algebraic/trigonometric expressions to a compact form.'],
      factor: ['Factor Mode', 'Factorizes expressions into products of simpler factors.'],
      substitute: ['Substitute Mode', 'Substitute values into expressions. Use `;` (e.g., expr ; x=2)'],
      integrate: ['Integrate Mode', 'Compute indefinite/definite integrals. Use `; x` to specify variable or limits.']
    };
    if (desc && map[mode]) {
      desc.innerHTML = `<strong>${map[mode][0]}</strong><p class="muted">${map[mode][1]}</p>`;
    }
  }

  // attach click handlers
  modeButtons.forEach(b => {
    b.addEventListener('click', () => {
      const mode = b.dataset.mode;
      setActiveMode(mode);
      // If your app.js has a setActiveMode function exposed, call it too (for state sync)
      if (window.__mathApp && typeof window.__mathApp.setMode === 'function') {
        window.__mathApp.setMode(mode);
      }
    });
  });

  // quick insert buttons
  quickButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const ins = btn.dataset.insert || '';
      const el = expr;
      if (!el) return;
      const start = el.selectionStart || 0;
      const end = el.selectionEnd || 0;
      const val = el.value;
      el.value = val.slice(0,start) + ins + val.slice(end);
      el.focus();
      const pos = start + ins.length;
      el.selectionStart = el.selectionEnd = pos;
      // trigger input events for preview
      el.dispatchEvent(new Event('input'));
    });
  });

  // quick examples selection: put example in textarea
  quickExamples?.addEventListener('change', (e) => {
    if (!e.target.value) return;
    expr.value = e.target.value;
    expr.dispatchEvent(new Event('input'));
    // reset select (optional)
    quickExamples.value = '';
  });

  // expose small utility for showing/hiding history from UI
  const historyToggle = $('historyToggle');
  const historyPanel = $('historyPanel');
  const clearHistory = $('clearHistory');

  if (historyToggle && historyPanel) {
    historyToggle.addEventListener('click', () => {
      historyPanel.style.display = historyPanel.style.display === 'block' ? 'none' : 'block';
      // if your app.js exposes populateHistory, call it
      if (window.__mathApp && typeof window.__mathApp.populateHistory === 'function') {
        window.__mathApp.populateHistory();
      }
    });
  }
  if (clearHistory) {
    clearHistory.addEventListener('click', () => {
      // clear localStorage history key used by your app.js
      try { localStorage.removeItem('mathpro_history_v1'); } catch(e){}
      if (window.__mathApp && typeof window.__mathApp.populateHistory === 'function') {
        window.__mathApp.populateHistory();
      } else {
        // remove children
        const list = document.getElementById('historyList');
        if (list) list.innerHTML = '<li class="empty-history">No history yet</li>';
      }
    });
  }

  // If your main app.js exposes helpers, attach them for two-way sync
  // (This is harmless if not present)
  if (window.__mathApp) {
    // request initial drawing / sync mode if app.js has current mode
    try {
      const cur = window.__mathApp.getMode ? window.__mathApp.getMode() : 'expand';
      setActiveMode(cur);
    } catch(e){}
  } else {
    // default
    setActiveMode('expand');
  }

})();
