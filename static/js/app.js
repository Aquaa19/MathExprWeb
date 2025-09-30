// static/js/app.js — mode buttons + descriptions + rest of features
(() => {
  // DOM refs
  const exprEl = document.getElementById('expr');
  const runBtn = document.getElementById('run');
  const resultText = document.getElementById('resultText');
  const inputMathRender = document.getElementById('inputMathRender');
  const outputMathRender = document.getElementById('outputMathRender');
  const modeButtonsContainer = document.getElementById('modeButtons');
  const modeDescription = document.getElementById('modeDescription');
  const copyBtn = document.getElementById('copy');
  const simplifyBtn = document.getElementById('simplifyBtn');
  const quickExamples = document.getElementById('quickExamples');
  const themeToggle = document.getElementById('themeToggle');
  const timingEl = document.getElementById('timing');
  const logEl = document.getElementById('log');

  // history refs
  const historyList = document.getElementById('historyList');
  const historyPanel = document.getElementById('historyPanel');
  const toggleHistoryBtn = document.getElementById('toggleHistory');
  const clearHistoryBtn = document.getElementById('clearHistory');

  const precisionEl = document.getElementById('precision');

  // mode + descriptions
  const MODES = {
    expand: { title: "Expand", desc: "Expands algebraic expressions. Example: (x+2)(x+3) → x² + 5x + 6" },
    simplify: { title: "Simplify", desc: "Simplifies algebraic/trigonometric expressions to a compact form." },
    factor: { title: "Factor", desc: "Factorizes expressions into products of simpler factors." },
    substitute: { title: "Substitute", desc: "Substitute values into expressions. Use `;` (e.g., expr ; x=2)" },
    integrate: { title: "Integrate", desc: "Compute indefinite/definite integrals. Use `; x` to specify variable or limits." }
  };

  let selectedMode = 'expand';
  let lastOutputLatex = '';

  // Initialize mode buttons behaviors
  function setActiveMode(mode) {
    selectedMode = mode;
    // update button visuals
    const btns = modeButtonsContainer.querySelectorAll('.mode-btn');
    btns.forEach(b => {
      if (b.dataset.mode === mode) { b.classList.add('active'); b.setAttribute('aria-pressed','true'); }
      else { b.classList.remove('active'); b.setAttribute('aria-pressed','false'); }
    });
    // update description
    const info = MODES[mode] || {title:mode, desc:''};
    modeDescription.innerHTML = `<strong>${info.title} Mode</strong><p class="muted">${info.desc}</p>`;
  }

  // attach click listeners to buttons
  modeButtonsContainer.addEventListener('click', (ev) => {
    const btn = ev.target.closest('.mode-btn');
    if (!btn) return;
    const mode = btn.dataset.mode;
    setActiveMode(mode);
  });

  // initial active mode
  setActiveMode(selectedMode);

  // rendering helpers (MathJax)
  function renderInputMath(l) {
    if (!inputMathRender) return;
    inputMathRender.innerHTML = l ? '$$' + l + '$$' : '';
    if (window.MathJax && window.MathJax.typesetPromise) {
      MathJax.typesetClear();
      MathJax.typesetPromise([inputMathRender]).catch(()=>{});
    }
  }
  function renderOutputMath(l) {
    if (!outputMathRender) return;
    outputMathRender.innerHTML = l ? '$$' + l + '$$' : '';
    lastOutputLatex = l || '';
    if (window.MathJax && window.MathJax.typesetPromise) {
      MathJax.typesetClear();
      MathJax.typesetPromise([outputMathRender]).catch(()=>{});
    }
  }

  // debounce preview
  let previewTimer = null;
  function schedulePreview() {
    if (previewTimer) clearTimeout(previewTimer);
    previewTimer = setTimeout(()=> {
      const text = exprEl.value.trim();
      if (!text) { renderInputMath(''); return; }
      const latexGuess = text.replace(/\^([^\s\^]+)/g, (m,g1)=>'^{' + g1 + '}');
      renderInputMath(latexGuess);
    }, 250);
  }

  // HTTP helper
  async function postSolve(expr, mode) {
    const resp = await fetch('/api/solve', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({expr, mode})
    });
    const data = await resp.json().catch(()=>({ok:false,error:'Invalid JSON'}));
    return {status: resp.status, data};
  }

  // Run action -- uses selectedMode
  runBtn.addEventListener('click', async ()=>{
    const expr = exprEl.value.trim();
    if(!expr){ setLog('Expression empty.'); return; }
    setLog('Sending request...');
    const t0 = performance.now();
    try {
      const {status, data} = await postSolve(expr, selectedMode);
      const dur = (performance.now() - t0).toFixed(0);
      if (timingEl) timingEl.textContent = `${dur} ms`;
      if (data && data.ok) {
        resultText.textContent = data.result || '';
        renderOutputMath(data.latex || data.result || '');
        setLog('Success.');
        saveHistory({expr, mode: selectedMode, result: data.result || '', latex: data.latex || ''});
      } else {
        resultText.textContent = data && data.error ? data.error : 'Server error';
        renderOutputMath('');
        setLog(data && data.error ? data.error : 'Error from server.');
      }
    } catch(e) {
      setLog('Network error: ' + e);
    }
  });

  // copy result
  copyBtn.addEventListener('click', ()=> {
    const txt = resultText.textContent || '';
    if (!txt) return setLog('No result to copy.');
    navigator.clipboard?.writeText(txt).then(()=> setLog('Copied.'), ()=> setLog('Copy failed.'));
  });

  // simplify result (resimplify)
  simplifyBtn.addEventListener('click', async ()=> {
    const text = resultText.textContent.trim();
    if (!text) return setLog('No result to simplify.');
    try {
      const resp = await fetch('/api/solve', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({expr: text, mode:'resimplify'})
      });
      const data = await resp.json().catch(()=>({ok:false,error:'Invalid JSON'}));
      if (data && data.ok) {
        resultText.textContent = data.result || '';
        renderOutputMath(data.latex || data.result || '');
        setLog('Simplified.');
      } else setLog(data.error || 'Simplify failed.');
    } catch(e) { setLog('Network error: ' + e); }
  });

  // quick examples
  if (quickExamples) quickExamples.addEventListener('change', (e)=> {
    if (e.target.value) { exprEl.value = e.target.value; schedulePreview(); quickExamples.value = ''; }
  });

  // theme toggle
  if (themeToggle) themeToggle.addEventListener('click', ()=>{
    const body = document.body;
    const isLight = body.classList.toggle('theme-light');
    themeToggle.textContent = isLight ? '☀️' : '🌙';
  });

  // live preview hookup
  exprEl.addEventListener('input', schedulePreview);
  schedulePreview();

  // Logging helper
  function setLog(m){ if (logEl) logEl.textContent = m; }

  /* -------------------------
     Simple local history (keeps existing logic)
     ------------------------- */
  const HISTORY_KEY = 'mathpro_history_v1';
  function loadHistory(){ try{ return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }catch{return []} }
  function saveHistory(arr){ localStorage.setItem(HISTORY_KEY, JSON.stringify(arr.slice(0,50))); populateHistory(); }
  function saveHistoryItem(item){ const arr = loadHistory(); arr.unshift(item); saveHistory(arr); }
  function saveHistory(item){ const arr = loadHistory(); arr.unshift(item); localStorage.setItem(HISTORY_KEY, JSON.stringify(arr.slice(0,50))); populateHistory(); }
  function populateHistory() {
    const arr = loadHistory();
    historyList.innerHTML = '';
    if (!arr.length) { const li = document.createElement('li'); li.className='muted'; li.textContent='No history yet'; historyList.appendChild(li); return; }
    arr.forEach((it, idx) => {
      const li = document.createElement('li');
      li.innerHTML = `<div><strong>${escapeHtml(it.mode)}</strong>: <code>${escapeHtml(it.expr)}</code></div>
                      <div style="display:flex;gap:6px">
                        <button data-idx="${idx}" data-action="load" class="muted">Load</button>
                        <button data-idx="${idx}" data-action="del" class="muted">Delete</button>
                      </div>`;
      historyList.appendChild(li);
    });
  }
  if (historyList) historyList.addEventListener('click', (ev)=> {
    const btn = ev.target.closest('button');
    if (!btn) return;
    const i = Number(btn.dataset.idx); const action = btn.dataset.action;
    const arr = loadHistory();
    if (action === 'load') {
      const it = arr[i]; if (it) { exprEl.value = it.expr; setActiveFromMode(it.mode); schedulePreview(); }
    } else if (action === 'del') { arr.splice(i,1); localStorage.setItem(HISTORY_KEY, JSON.stringify(arr)); populateHistory(); }
  });

  function setActiveFromMode(mode) { setActiveMode(mode); } // helper to keep naming consistent

  // expose toggleHistory/clearHistory
  if (toggleHistoryBtn) toggleHistoryBtn.addEventListener('click', ()=> { historyPanel.style.display = historyPanel.style.display === 'block' ? 'none' : 'block'; populateHistory(); });
  if (clearHistoryBtn) clearHistoryBtn.addEventListener('click', ()=> { localStorage.removeItem(HISTORY_KEY); populateHistory(); });

  function escapeHtml(s){ return String(s).replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

  // on load
  populateHistory();
  setLog('Ready.');
})();
