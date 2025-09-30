// static/js/app.js — updated: Export LaTeX now opens new tab with editable LaTeX doc + preview
(() => {
  const exprEl = document.getElementById('expr');
  const runBtn = document.getElementById('run');
  const modeEl = document.getElementById('mode');
  const resultText = document.getElementById('resultText');

  // Two render containers
  const inputMathRender = document.getElementById('inputMathRender');
  const outputMathRender = document.getElementById('outputMathRender');

  const copyBtn = document.getElementById('copy');
  const logEl = document.getElementById('log');
  const timingEl = document.getElementById('timing');
  const quickExamples = document.getElementById('quickExamples');
  const historyList = document.getElementById('historyList');
  const historyPanel = document.getElementById('historyPanel');
  const toggleHistoryBtn = document.getElementById('toggleHistory');
  const clearHistoryBtn = document.getElementById('clearHistory');
  const themeToggle = document.getElementById('themeToggle');
  const precisionEl = document.getElementById('precision');
  const simplifyBtn = document.getElementById('simplifyBtn');

  // Add Export PNG and Export LaTeX buttons to results header
  const actionArea = document.querySelector('.results-header .result-actions');
  if (actionArea) {
    const exportPng = document.createElement('button');
    exportPng.textContent = 'Export PNG';
    exportPng.className = 'muted';
    exportPng.style.marginLeft = '8px';
    exportPng.addEventListener('click', exportPngHandler);

    const exportTex = document.createElement('button');
    exportTex.textContent = 'Export LaTeX';
    exportTex.className = 'muted';
    exportTex.style.marginLeft = '6px';
    exportTex.addEventListener('click', exportLatexHandler);

    actionArea.appendChild(exportPng);
    actionArea.appendChild(exportTex);
  }

  let lastOutputLatex = ''; // store last output latex when available

  function setLog(msg) { if (logEl) logEl.textContent = msg; }

  async function postSolve(expr, mode) {
    const resp = await fetch('/api/solve', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({expr, mode})
    });
    const data = await resp.json().catch(()=>({ok:false, error:'Invalid JSON response'}));
    return {status: resp.status, data};
  }

  // Render helpers for input vs output
  function renderInputMath(latexOrText) {
    if(!inputMathRender) return;
    if(!latexOrText) { inputMathRender.innerHTML = ''; return; }
    inputMathRender.innerHTML = '$$' + latexOrText + '$$';
    if(window.MathJax && window.MathJax.typesetPromise){
      MathJax.typesetClear();
      MathJax.typesetPromise([inputMathRender]).catch(()=>{});
    }
  }
  function renderOutputMath(latexOrText) {
    if(!outputMathRender) return;
    if(!latexOrText) { outputMathRender.innerHTML = ''; lastOutputLatex = ''; return; }
    outputMathRender.innerHTML = '$$' + latexOrText + '$$';
    lastOutputLatex = latexOrText || '';
    if(window.MathJax && window.MathJax.typesetPromise){
      MathJax.typesetClear();
      MathJax.typesetPromise([outputMathRender]).catch(()=>{});
    }
  }

  // Live preview debounce
  let previewTimer = null;
  function schedulePreview() {
    if (previewTimer) clearTimeout(previewTimer);
    previewTimer = setTimeout(()=> {
      const text = exprEl.value.trim();
      if (!text) { renderInputMath(''); return; }
      // Convert caret ^x to ^{x} for nicer MathJax rendering (best-effort)
      const latexGuess = text.replace(/\^([^\s\^]+)/g, (m, g1) => '^{' + g1 + '}');
      renderInputMath(latexGuess);
    }, 240);
  }

  // History
  const HISTORY_KEY = 'mathpro_history_v1';
  const MAX_HISTORY = 50;
  function loadHistory(){ try{ const raw = localStorage.getItem(HISTORY_KEY); return raw ? JSON.parse(raw) : []; }catch{return []} }
  function saveHistory(arr){ localStorage.setItem(HISTORY_KEY, JSON.stringify(arr.slice(0, MAX_HISTORY))); populateHistory(); }
  function addHistory(item){ const arr = loadHistory(); arr.unshift(item); saveHistory(arr); }
  function clearHistory(){ localStorage.removeItem(HISTORY_KEY); populateHistory(); }

  function populateHistory(){
    const arr = loadHistory();
    historyList.innerHTML = '';
    if(arr.length === 0){ const li=document.createElement('li'); li.className='muted'; li.textContent='No history yet'; historyList.appendChild(li); return; }
    arr.forEach((it, idx) => {
      const li = document.createElement('li'); li.className='history-item'; li.dataset.index = idx;
      const left = document.createElement('div'); left.style.maxWidth = '70%';
      left.innerHTML = `<strong>${escapeHtml(it.mode)}</strong>: <code>${escapeHtml(it.expr)}</code>`;
      const actions = document.createElement('div'); actions.style.display='flex'; actions.style.gap='6px';
      const loadBtn = document.createElement('button'); loadBtn.textContent='Load'; loadBtn.className='muted'; loadBtn.dataset.action='load'; loadBtn.dataset.index=idx;
      const delBtn = document.createElement('button'); delBtn.textContent='Delete'; delBtn.className='muted'; delBtn.dataset.action='delete'; delBtn.dataset.index=idx;
      actions.appendChild(loadBtn); actions.appendChild(delBtn);
      li.appendChild(left); li.appendChild(actions); historyList.appendChild(li);
    });
  }
  if (historyList) {
    historyList.addEventListener('click', (ev)=> {
      const btn = ev.target.closest('button');
      if (!btn) return;
      const action = btn.dataset.action;
      const idx = Number(btn.dataset.index);
      const arr = loadHistory();
      if (action === 'load') {
        const it = arr[idx];
        if (it) { modeEl.value = it.mode; exprEl.value = it.expr; schedulePreview(); }
      } else if (action === 'delete') {
        arr.splice(idx, 1); saveHistory(arr);
      }
    });
  }

  function escapeHtml(s){ return String(s).replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

  if (quickExamples) quickExamples.addEventListener('change', (e)=>{ if(e.target.value){ exprEl.value = e.target.value; schedulePreview(); quickExamples.value=''; }});

  if (themeToggle) themeToggle.addEventListener('click', ()=>{ const body=document.body; const isLight=body.classList.toggle('theme-light'); themeToggle.textContent = isLight ? '☀️' : '🌙'; themeToggle.setAttribute('aria-pressed', isLight ? 'true' : 'false'); });

  if (toggleHistoryBtn) toggleHistoryBtn.addEventListener('click', ()=>{ if(historyPanel.style.display === 'none' || historyPanel.style.display === '') { historyPanel.style.display='block'; populateHistory(); } else { historyPanel.style.display='none'; }});
  if (clearHistoryBtn) clearHistoryBtn.addEventListener('click', clearHistory);

  if (copyBtn) copyBtn.addEventListener('click', ()=>{ const text = resultText.textContent; if(!text) return; navigator.clipboard?.writeText(text).then(()=> setLog('Copied to clipboard.'), ()=> setLog('Copy failed.')); });

  // Simplify current result (calls backend mode 'resimplify')
  if (simplifyBtn) simplifyBtn.addEventListener('click', async ()=> {
    const text = resultText.textContent.trim();
    if(!text || text.startsWith('❌')) { setLog('No valid result to simplify.'); return; }
    setLog('Simplifying...');
    try {
      const resp = await fetch('/api/solve', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({expr: text, mode: 'resimplify'})
      });
      const data = await resp.json().catch(()=>({ok:false,error:'Invalid JSON'}));
      if(data && data.ok){
        resultText.textContent = data.result || '';
        // render output panel; prefer latex if backend provided
        renderOutputMath(data.latex || data.result || '');
        setLog('Simplified.');
      } else {
        setLog(data.error || 'Error simplifying.');
      }
    } catch (e) { setLog('Network error: '+e); }
  });

  // Run
  if (runBtn) runBtn.addEventListener('click', async ()=> {
    const expr = exprEl.value.trim();
    const mode = modeEl.value;
    if(!expr) { setLog('Expression empty.'); return; }
    setLog('Sending request...');
    const t0 = performance.now();
    try {
      const {status, data} = await postSolve(expr, mode);
      const dur = (performance.now() - t0).toFixed(0);
      if (timingEl) timingEl.textContent = `${dur} ms`;
      if(data && data.ok){
        resultText.textContent = data.result || '';
        // render output panel (prefer latex)
        if(data.latex) renderOutputMath(data.latex); else renderOutputMath((data.result || '').replace(/\^/g,'^{'));
        setLog('Success.');
        addHistory({expr, mode, result: data.result || '', latex: data.latex || null, when: Date.now()});
      } else {
        resultText.textContent = data && data.error ? data.error : 'Server error';
        renderOutputMath('');
        setLog(data && data.error ? data.error : 'Error from server.');
      }
    } catch (e) {
      if (timingEl) timingEl.textContent = '—';
      setLog('Network/internal error: ' + e);
    }
  });

  // Ctrl/Cmd + Enter to run
  if (exprEl) exprEl.addEventListener('keydown', (ev)=>{ if((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter'){ runBtn.click(); } });

  // live preview hookup
  if (exprEl) { exprEl.addEventListener('input', schedulePreview); schedulePreview(); }

  // --- Export handlers ---

  // Export PNG (screenshot results card)
  async function exportPngHandler() {
    try {
      setLog('Rendering PNG...');
      const target = document.querySelector('.results-card') || document.body;
      const canvas = await html2canvas(target, {scale: 2, useCORS: true});
      const dataUrl = canvas.toDataURL('image/png');
      const link = document.createElement('a');
      link.download = 'mathpro-result.png';
      link.href = dataUrl;
      link.click();
      setLog('PNG exported.');
    } catch (e) {
      setLog('PNG export failed: ' + e);
    }
  }

  // Export LaTeX — open a new tab with editable LaTeX document + preview + copy button
  function exportLatexHandler() {
    try {
      setLog('Preparing LaTeX export...');
      // Input LaTeX: best-effort conversion of input box (same as preview)
      const rawInput = exprEl.value.trim();
      const inputLatex = rawInput ? rawInput.replace(/\^([^\s\^]+)/g, (m, g1) => '^{' + g1 + '}') : '';

      // Output LaTeX: prefer backend-provided lastOutputLatex; if not available fallback to resultText
      const outputLatex = lastOutputLatex || resultText.textContent || '';

      // Build LaTeX document content
      const doc = [
        '\\documentclass{article}',
        '\\usepackage{amsmath,amssymb}',
        '\\usepackage[utf8]{inputenc}',
        '\\begin{document}',
        '\\section*{Input}',
        inputLatex ? `\\[ ${inputLatex} \\]` : '\\texttt{(empty)}',
        '\\vspace{8pt}',
        '\\section*{Output}',
        outputLatex ? `\\[ ${outputLatex} \\]` : '\\texttt{(empty)}',
        '\\end{document}'
      ].join('\n');

      // Open new tab and write UI
      const newWin = window.open('', '_blank');
      if (!newWin) { setLog('Popup blocked. Allow popups for this site.'); return; }

      const html = `
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Export LaTeX — MathExprWeb</title>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <style>
    body{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial;margin:18px;color:#0b1220}
    h1{font-size:1.1rem;margin:0 0 6px}
    .row{display:flex;gap:8px;align-items:center;margin:8px 0}
    textarea{width:100%;height:45vh;padding:12px;border-radius:8px;border:1px solid #ccc;font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, "Roboto Mono", monospace}
    button{padding:8px 10px;border-radius:8px;border:0;background:#2563eb;color:white;cursor:pointer}
    .muted{background:#f3f4f6;color:#0b1220;border:1px solid #e5e7eb}
    .preview{margin-top:12px;padding:12px;border:1px solid #eee;background:#fff}
    .note{color:#475569;font-size:0.9rem;margin-top:8px}
  </style>
  <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
  <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
  <h1>LaTeX Export — MathExprWeb</h1>
  <div class="row">
    <button id="copyBtn">Copy LaTeX</button>
    <button id="downloadBtn" class="muted">Download .tex</button>
  </div>
  <textarea id="texArea">${escapeHtml(doc)}</textarea>

  <div class="note">Below is a preview of input and output (rendered). Edit LaTeX above and click "Copy LaTeX" to copy the final document.</div>

  <div class="preview" id="preview">
    <div><strong>Input:</strong></div>
    <div id="previewInput">\\[ ${escapeHtml(inputLatex)} \\]</div>
    <div style="height:8px;"></div>
    <div><strong>Output:</strong></div>
    <div id="previewOutput">\\[ ${escapeHtml(outputLatex)} \\]</div>
  </div>

  <script>
    const texArea = document.getElementById('texArea');
    const copyBtn = document.getElementById('copyBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const previewInput = document.getElementById('previewInput');
    const previewOutput = document.getElementById('previewOutput');

    copyBtn.addEventListener('click', async ()=> {
      try {
        await navigator.clipboard.writeText(texArea.value);
        copyBtn.textContent = 'Copied!';
        setTimeout(()=> copyBtn.textContent = 'Copy LaTeX', 1400);
      } catch(e) {
        alert('Copy failed: ' + e);
      }
    });

    downloadBtn.addEventListener('click', ()=> {
      const blob = new Blob([texArea.value], {type:'text/x-tex'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'mathpro-result.tex';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    });

    // update preview when textarea changes (simple)
    texArea.addEventListener('input', ()=> {
      // attempt to extract the \\[ ... \\] blocks for input and output using naive regex
      const txt = texArea.value;
      const matches = txt.match(/\\\\\\[([\\s\\S]*?)\\\\\\]/g);
      if (matches) {
        // best-effort: update previewInput and previewOutput if present
        if (matches[0]) previewInput.innerText = matches[0].replace(/\\\\\\[/g,'\\\\[').replace(/\\\\\\]/g,'\\\\]');
        if (matches[1]) previewOutput.innerText = matches[1].replace(/\\\\\\[/g,'\\\\[').replace(/\\\\\\]/g,'\\\\]');
      }
      if(window.MathJax && window.MathJax.typesetPromise){
        MathJax.typesetClear();
        MathJax.typesetPromise([previewInput, previewOutput]).catch(()=>{});
      }
    });

    // initial MathJax typeset
    if(window.MathJax && window.MathJax.typesetPromise){
      MathJax.typesetClear();
      MathJax.typesetPromise([previewInput, previewOutput]).catch(()=>{});
    }

    // small utility to escape HTML (copied from parent)
    function escapeHtml(s){ return String(s).replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
  </script>
</body>
</html>
      `;

      // write the html and close the document
      newWin.document.open();
      newWin.document.write(html);
      newWin.document.close();

      setLog('LaTeX export opened in new tab.');
    } catch (e) {
      setLog('LaTeX export failed: ' + e);
    }
  }

  // placeholder to satisfy earlier addEventListener references
  function exportPngHandler() { /* overwritten above */ }

  // initial population & ready
  populateHistory();
  setLog('Ready.');
})();
