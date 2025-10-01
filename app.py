# MathExprWeb/app.py
from flask import Flask, render_template, request, jsonify, url_for, flash, redirect
from flask_login import login_user, current_user, logout_user, login_required
import os

from extensions import db, login_manager

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')

    # --- Configuration for Local Development ---
    app.config['SECRET_KEY'] = 'a_very_secret_key_change_this_for_production' 
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mathexpr.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    
    login_manager.login_view = 'login'
    login_manager.login_message_category = 'danger'

    from models import User, History
    from forms import RegistrationForm, LoginForm

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from solver_utils import (
        expand_expr, simplify_expr, factor_expr, substitute_expr,
        integrate_expr, resimplify_expr,
        laplace_transform_expr, fourier_transform_expr, mellin_transform_expr,
        differentiate_expr
    )
    
    # --- Register Routes within the app context ---
    @app.route('/')
    def index():
        return render_template('index.html', user=current_user)

    @app.route("/register", methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        form = RegistrationForm()
        if form.validate_on_submit():
            user = User(username=form.username.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You are now able to log in.', 'success')
            return redirect(url_for('login'))
        return render_template('register.html', title='Register', form=form)

    @app.route("/login", methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                flash('Login Unsuccessful. Please check username and password.', 'danger')
        return render_template('login.html', title='Login', form=form)

    @app.route("/logout")
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/api/solve', methods=['POST'])
    def api_solve():
        data = request.get_json() or {}
        mode = (data.get('mode') or '').lower().strip()
        expr = data.get('expr', '')
        result_tuple = None

        if mode == 'expand': result_tuple = expand_expr(expr)
        elif mode == 'simplify': result_tuple = simplify_expr(expr)
        elif mode == 'factor': result_tuple = factor_expr(expr)
        elif mode == 'substitute': result_tuple = substitute_expr(expr)
        elif mode == 'integrate': result_tuple = integrate_expr(expr)
        elif mode == 'differentiate': result_tuple = differentiate_expr(expr)
        elif mode == 'resimplify': result_tuple = resimplify_expr(expr)
        elif mode == 'laplace_t': result_tuple = laplace_transform_expr(expr)
        elif mode == 'fourier_t': result_tuple = fourier_transform_expr(expr)
        elif mode == 'mellin_t': result_tuple = mellin_transform_expr(expr)
        else: return jsonify({'ok': False, 'error': f"Unknown mode '{mode}'"}), 400

        display, latex, err = result_tuple
        if err: return jsonify({'ok': False, 'error': err}), 400

        if current_user.is_authenticated:
            new_history = History(mode=mode, expression=expr, result=display, latex=latex, user_id=current_user.id)
            db.session.add(new_history)
            db.session.commit()

        return jsonify({'ok': True, 'result': display, 'latex': latex})

    @app.route('/api/history', methods=['GET', 'DELETE'])
    @login_required
    def manage_history():
        if request.method == 'GET':
            user_history = History.query.filter_by(user_id=current_user.id).order_by(History.timestamp.desc()).all()
            history_list = [{'mode': h.mode, 'expression': h.expression, 'result': h.result, 'latex': h.latex, 'timestamp': h.timestamp.strftime('%Y-%m-%d %H:%M:%S')} for h in user_history]
            return jsonify(history_list)
        if request.method == 'DELETE':
            History.query.filter_by(user_id=current_user.id).delete()
            db.session.commit()
            return jsonify({'ok': True, 'message': 'History cleared'})
            
    return app

# Create the app instance and run it
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

