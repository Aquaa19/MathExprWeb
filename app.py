# app.py
from flask import Flask, render_template, request, jsonify
from solver_utils import (
    expand_expr, simplify_expr, factor_expr, substitute_expr,
    integrate_expr, resimplify_expr
)
import os

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/solve', methods=['POST'])
def api_solve():
    data = request.get_json() or {}
    mode = (data.get('mode') or '').lower()
    expr = data.get('expr', '')

    if mode == 'expand':
        display, latex, err = expand_expr(expr)
        if err:
            return jsonify({'ok': False, 'error': err}), 400
        return jsonify({'ok': True, 'result': display, 'latex': latex})
    elif mode == 'simplify':
        display, latex, err = simplify_expr(expr)
        if err:
            return jsonify({'ok': False, 'error': err}), 400
        return jsonify({'ok': True, 'result': display, 'latex': latex})
    elif mode == 'factor':
        display, latex, err = factor_expr(expr)
        if err:
            return jsonify({'ok': False, 'error': err}), 400
        return jsonify({'ok': True, 'result': display, 'latex': latex})
    elif mode == 'substitute':
        display, latex, err = substitute_expr(expr)
        if err:
            return jsonify({'ok': False, 'error': err}), 400
        return jsonify({'ok': True, 'result': display, 'latex': latex})
    elif mode == 'integrate':
        display, latex, err = integrate_expr(expr)
        if err:
            return jsonify({'ok': False, 'error': err}), 400
        return jsonify({'ok': True, 'result': display, 'latex': latex})
    elif mode == 'resimplify':
        display, latex, err = resimplify_expr(expr)
        if err:
            return jsonify({'ok': False, 'error': err}), 400
        return jsonify({'ok': True, 'result': display, 'latex': latex})
    else:
        return jsonify({'ok': False, 'error': f"Unknown mode '{mode}'"}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # debug True is helpful during development; turn off in production
    app.run(host='0.0.0.0', port=port, debug=True)