// App State
let currentMode = 'expand';
let history = [];
let currentTheme = 'dark';
let currentLatex = null;  // Store current LaTeX for export

// Mode Descriptions
const modeDescriptions = {
    expand: {
        title: 'Expand Mode',
        items: [
            'Expands algebraic expressions with trig support',
            'Example: (x+2)(x+3) → x² + 5x + 6',
            'Example: sin(2x) → 2sin(x)cos(x)'
        ],
        helper: 'Use ^ or superscripts (²³⁴) for powers. Implicit multiplication supported: 2x, xy, (x+1)(x+2)'
    },
    simplify: {
        title: 'Simplify Mode',
        items: [
            'Simplifies and factors expressions',
            'Example: x²+5x+6 → (x+2)(x+3)',
            'Combines like terms and reduces complexity'
        ],
        helper: 'Algebraic and trigonometric simplification. Supports sin, cos, tan, log, exp, sqrt.'
    },
    factor: {
        title: 'Factor Mode',
        items: [
            'Factors expressions into products',
            'Example: x²-4 → (x-2)(x+2)',
            'Works with polynomials and trig expressions'
        ],
        helper: 'Factors polynomials and trigonometric expressions when possible.'
    },
    substitute: {
        title: 'Substitute Mode',
        items: [
            'Evaluates expressions with variable values',
            'Example: 2x²+3x; x=5 → 65',
            'Supports multiple variables'
        ],
        helper: 'Format: expr; var1=val1, var2=val2. Example: x²+y²; x=3, y=4'
    },
    integrate: {
        title: 'Integration Mode',
        items: [
            'Integrates expressions (indefinite or definite)',
            'Indefinite: expr or expr; x',
            'Definite: expr; x=a,b',
            'Multi-variable: `expr; var` (e.g., `x+a; x`)'
        ],
        helper: 'For multiple variables, specify which to integrate. Example: To compute ∫(x+a)dx, enter "x+a; x"'
    },
    // NEW MODE: DIFFERENTIATE
    differentiate: {
        title: 'Differentiation Mode',
        items: [
            'Finds the derivative of an expression',
            'Format: expr or expr; var, order',
            'Example: sin(x^2); x, 2 (for second derivative)'
        ],
        helper: 'Format: expr; var, order. Default is first derivative w.r.t. x. Example: x^3; x, 2'
    },
    // REMOVED: resimplify mode
    laplace_t: {
        title: 'Laplace Transform',
        items: [
            'Computes the Laplace Transform L{f(t)}(s)',
            'Format: expr; input_var, transform_var',
            'Example: exp(-a*t); t, s'
        ],
        helper: 'Format: expr; input_var, transform_var. Example: 1/(t+1); t, s'
    },
    fourier_t: {
        title: 'Fourier Transform',
        items: [
            'Computes the Fourier Transform F{f(x)}(k)',
            'Uses SymPy\'s default convention (e.g., in terms of k)',
            'Example: exp(-x^2); x, k'
        ],
        helper: 'Format: expr; input_var, transform_var. Example: exp(-abs(x)); x, k'
    },
    mellin_t: {
        title: 'Mellin Transform',
        items: [
            'Computes the Mellin Transform M{f(x)}(s)',
            'Result includes the fundamental strip (a, b)',
            'Example: exp(-x); x, s'
        ],
        helper: 'Format: expr; input_var, transform_var. Example: x**a*exp(-x); x, s'
    }
};

// Initialize particles
function createFloatingParticles() {
    const particlesContainer = document.getElementById('particles');
    for (let i = 0; i < 20; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 15 + 's';
        particle.style.animationDuration = (Math.random() * 10 + 10) + 's';
        particlesContainer.appendChild(particle);
    }
}

// Theme Toggle
function toggleTheme() {
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.body.setAttribute('data-theme', currentTheme);
    document.getElementById('themeToggle').textContent = currentTheme === 'dark' ? '🌙' : '☀️';
}

// Update Mode Info
function updateModeInfo() {
    const info = modeDescriptions[currentMode];
    const infoBox = document.getElementById('modeInfo');
    const helperText = document.getElementById('helperText');
    
    infoBox.innerHTML = `
        <h3>${info.title}</h3>
        <ul>
            ${info.items.map(item => `<li>${item}</li>`).join('')}
        </ul>
    `;
    
    helperText.textContent = info.helper;
}

// Mode Button Click Handlers
document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentMode = btn.dataset.mode;
        updateModeInfo();
    });
});

// Quick Insert Buttons
document.querySelectorAll('.quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const input = document.getElementById('expression');
        const insert = btn.dataset.insert;
        const pos = input.selectionStart;
        const val = input.value;
        input.value = val.slice(0, pos) + insert + val.slice(pos);
        input.focus();
        input.selectionStart = input.selectionEnd = pos + insert.length;
    });
});

// Show/Hide Loading State
function setLoading(isLoading) {
    const btn = document.getElementById('calculateBtn');
    const btnText = document.getElementById('btnText');
    const btnLoader = document.getElementById('btnLoader');
    
    if (isLoading) {
        btn.classList.add('calculating');
    } else {
        btn.classList.remove('calculating');
    }
    
    btn.disabled = isLoading;
    btnText.style.display = isLoading ? 'none' : 'inline';
    btnLoader.style.display = isLoading ? 'inline-block' : 'none';
}

// Display Result
function displayResult(result, latex = null, isError = false) {
    const resultSection = document.getElementById('resultSection');
    const resultContent = document.getElementById('resultContent');
    const latexSection = document.getElementById('latexSection');
    const latexRender = document.getElementById('latexRender');
    const exportBtn = document.getElementById('exportLatexBtn');
    const resimplifyBtn = document.getElementById('resimplifyBtn'); // NEW

    resultContent.textContent = result;
    
    if (isError) {
        resultContent.classList.add('error');
        latexSection.style.display = 'none';
        exportBtn.style.display = 'none';
        resimplifyBtn.style.display = 'none'; // Hide on error
        currentLatex = null;
    } else {
        resultContent.classList.remove('error');
        
        if (latex) {
            // Store latex for export
            currentLatex = latex;
            
            // Render LaTeX using KaTeX
            try {
                latexRender.innerHTML = '';
                katex.render(latex, latexRender, {
                    throwOnError: false,
                    displayMode: true
                });
                latexSection.style.display = 'block';
            } catch (e) {
                console.error('KaTeX rendering error:', e);
                latexRender.textContent = latex;
                latexSection.style.display = 'block';
            }
        } else {
            latexSection.style.display = 'none';
            currentLatex = null;
        }
        
        // Show Export and Re-Simplify on success
        exportBtn.style.display = 'block';
        resimplifyBtn.style.display = 'block';
    }
    
    resultSection.classList.add('show');
}

// Process Expression via API
async function processExpression() {
    const exprInput = document.getElementById('expression').value.trim();
    
    if (!exprInput) {
        displayResult('❌ Please enter an expression', null, true);
        return;
    }
    
    setLoading(true);
    
    try {
        const response = await fetch('/api/solve', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                mode: currentMode,
                expr: exprInput
            })
        });
        
        const data = await response.json();
        
        if (data.ok) {
            displayResult(data.result, data.latex || null, false);
            addToHistory(currentMode, exprInput, data.result, data.latex);
        } else {
            displayResult(data.error || 'An error occurred', null, true);
        }
    } catch (error) {
        displayResult(`❌ Network error: ${error.message}`, null, true);
    } finally {
        setLoading(false);
    }
}

// NEW: Function to handle Re-Simplify button click
async function processResimplification() {
    const exprToSimplify = document.getElementById('resultContent').textContent.trim();
    
    if (!exprToSimplify || exprToSimplify.startsWith('❌') || exprToSimplify.startsWith('⚠️')) {
        return; 
    }
    
    setLoading(true);
    
    try {
        const response = await fetch('/api/solve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mode: 'resimplify', // Fixed mode call
                expr: exprToSimplify
            })
        });
        
        const data = await response.json();
        
        if (data.ok) {
            // Display the new simplified result without changing the currentMode
            displayResult(data.result, data.latex || null, false);
            // Optionally: Update history with the resimplified result if needed, but not done here to keep history clean.
        } else {
            displayResult(data.error || 'Re-simplification failed.', null, true);
        }
    } catch (error) {
        displayResult(`❌ Network error during Re-Simplify: ${error.message}`, null, true);
    } finally {
        setLoading(false);
    }
}

// Add to History
function addToHistory(mode, expr, result, latex = null) {
    const entry = {
        mode,
        expression: expr,
        result,
        latex,
        timestamp: new Date().toLocaleString()
    };
    
    history.unshift(entry);
    if (history.length > 20) history.pop();
    
    updateHistoryDisplay();
}

// Update History Display
function updateHistoryDisplay() {
    const historyContent = document.getElementById('historyContent');
    
    if (history.length === 0) {
        historyContent.innerHTML = '<div class="empty-history">No calculations yet</div>';
        return;
    }
    
    historyContent.innerHTML = history.map((entry, index) => `
        <div class="history-item" data-index="${index}">
            <div class="history-mode">${entry.mode.toUpperCase()}</div>
            <div class="history-expr">${entry.expression}</div>
            <div class="history-result">→ ${entry.result}</div>
        </div>
    `).join('');
    
    // Add click handlers to history items
    document.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', () => {
            const index = parseInt(item.dataset.index);
            const entry = history[index];
            
            document.getElementById('expression').value = entry.expression;
            
            // Switch to the mode used in history
            document.querySelectorAll('.mode-btn').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.mode === entry.mode);
            });
            currentMode = entry.mode;
            updateModeInfo();
            
            // Display the result
            displayResult(entry.result, entry.latex, false);
        });
    });
}

// Clear History
function clearHistory() {
    history = [];
    updateHistoryDisplay();
}

// Event Listeners
document.getElementById('themeToggle').addEventListener('click', toggleTheme);
document.getElementById('calculateBtn').addEventListener('click', processExpression);
document.getElementById('clearHistoryBtn').addEventListener('click', clearHistory);
document.getElementById('resimplifyBtn').addEventListener('click', processResimplification); // NEW LISTENER

// Export LaTeX functionality (omitted for brevity, remains unchanged)
document.getElementById('exportLatexBtn').addEventListener('click', () => {
    const expr = document.getElementById('expression').value.trim();
    const result = document.getElementById('resultContent').textContent.trim();
    const mode = currentMode.toUpperCase();
    
    if (!expr || !result || !currentLatex) {
        alert("⚠️ No LaTeX result to export yet.");
        return;
    }
    
    const latexDoc = `\\documentclass{article}
\\usepackage{amsmath}
\\usepackage{amssymb}
\\usepackage{geometry}
\\geometry{a4paper, margin=1in}
\\title{Algebra Calculator Solution}
\\author{Generated by Algebra Calculator}
\\date{\\today}

\\begin{document}

\\maketitle

\\section*{Problem}
\\textbf{Mode:} ${mode} \\\\[0.5em]
\\textbf{Input:} \\( ${expr.replace(/\\/g, '\\\\')} \\)

\\section*{Solution}
\\textbf{Result:} ${result}

\\subsection*{LaTeX Expression}
\\[
${currentLatex}
\\]

\\end{document}`;
    
    // Create downloadable file
    const blob = new Blob([latexDoc], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `algebra_solution_${Date.now()}.tex`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    // Also show in new window
    const newWindow = window.open("", "_blank");
    newWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>LaTeX Export</title>
            <style>
                body {
                    font-family: monospace;
                    padding: 20px;
                    background: #1e1e1e;
                    color: #d4d4d4;
                }
                pre {
                    background: #2d2d2d;
                    padding: 20px;
                    border-radius: 8px;
                    overflow-x: auto;
                    line-height: 1.5;
                }
                .header {
                    background: #4ade80;
                    color: #000;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    font-weight: bold;
                }
                button {
                    background: #4ade80;
                    color: #000;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-weight: bold;
                    margin-top: 10px;
                }
                button:hover {
                    background: #22c55e;
                }
            </style>
        </head>
        <body>
            <div class="header">
                ✅ LaTeX file downloaded! Below is the content:
            </div>
            <button onclick="navigator.clipboard.writeText(document.querySelector('pre').textContent); alert('Copied to clipboard!')">
                📋 Copy to Clipboard
            </button>
            <pre>${latexDoc.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>
        </body>
        </html>
    `);
    newWindow.document.close();
});


// Enter key support
document.getElementById('expression').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        processExpression();
    }
});

// Initialize
createFloatingParticles();
updateModeInfo();