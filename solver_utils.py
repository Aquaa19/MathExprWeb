# solver_utils.py
# Full parsing / transformation logic + integrate support + trig-aware expand/factor/simplify and resimplify.

import re
import traceback
from multiprocessing import Process, Queue
from sympy import (
    expand, simplify, factor, sympify, symbols, Symbol, latex as sympy_latex,
    integrate as sympy_integrate, Integral as SympyIntegral,
    sin, cos, tan, cot, sec, csc,
    asin, acos, atan, sinh, cosh, tanh,
    exp, log, sqrt, Abs, pi, E, trigsimp,
    apart # ADDED: for partial fractions
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor
)
from sympy.integrals.manualintegrate import manualintegrate
from sympy import logcombine

# --- Unicode superscript conversion maps ---
unicode_sup_map = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")
superscript_map = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '-': '⁻'
}

def unicode_to_normal_expr(expr):
    """
    Replace occurrences like x² or 2⁻³ to x**2 or 2**-3
    """
    def replace(match):
        base = match.group(1)
        supers = match.group(2).translate(unicode_sup_map)
        return f"{base}^{supers}"
    return re.sub(r'([a-zA-Z0-9)])([⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)', replace, expr)

def normal_to_unicode_expr(expr):
    """
    Convert '**n' to unicode superscript and remove explicit '*' for nicer output.
    """
    def replace(match):
        power = match.group(1)
        return ''.join(superscript_map.get(ch, ch) for ch in power)
    expr = re.sub(r'\*\*([\-]?\d+)', lambda m: replace(m), expr)
    expr = expr.replace('*', '')  # Remove multiplication signs for display
    return expr

def insert_implicit_multiplication_rules(expr_str):
    """
    Safer insertion of explicit multiplication for parse reliability.

    - First: insert '*' between a digit and a known function name, e.g. '2sec(x)' -> '2*sec(x)'
    - Protects known function names (when followed by '(') so they are not split.
    - Inserts * between digit and letter or digit and '(' (e.g. 2x -> 2*x).
    - Inserts * between ')' and digit/letter/'(' (e.g. )( -> )*(, )x -> )*x).
    - Inserts * between letter/variable and '(' (e.g. x( -> x*().
    - Does NOT insert * between adjacent letters (avoids splitting 'sin', 'exp', etc.).
    """
    # List of common function names to protect (only when used as functions with '(')
    func_names = [
        'sin','cos','tan','cot','sec','csc',
        'asin','acos','atan','sinh','cosh','tanh',
        'exp','log','sqrt','Abs','erf','erfc'
    ]

    # 1) Insert multiplication between a digit and a following function name:
    #    e.g. "2sec(x)" -> "2*sec(x)"
    funcs_pattern = r'|'.join(re.escape(fn) for fn in func_names)
    # match a digit followed by optional spaces and one of the function names and a '('
    expr_str = re.sub(rf'(\d)\s*({funcs_pattern})\s*\(',
                      r'\1*\2(', expr_str)

    # 2) Protect known function names by replacing "name(" -> "__FN{i}__(" to avoid splitting them
    placeholder_map = {}
    for i, name in enumerate(func_names):
        token = f"__FN{i}__"
        placeholder_map[token] = name
        # replace function name only when followed by '(' (allow optional whitespace)
        expr_str = re.sub(rf'\b{name}\s*\(', f'{token}(', expr_str)

    # 3) Insert multiplication where it's safe:
    #    - 2x -> 2*x ; 2(x) -> 2*(x)
    expr_str = re.sub(r'(\d)([a-zA-Z(])', r'\1*\2', expr_str)
    #    - )(x or )2 -> )*x  )*2
    expr_str = re.sub(r'(\))([a-zA-Z0-9(])', r'\1*\2', expr_str)
    #    - x( or 2( -> x*( or 2*(
    expr_str = re.sub(r'([a-zA-Z0-9])(\()', r'\1*\2', expr_str)

    # 4) Restore function names (token -> original)
    for token, name in placeholder_map.items():
        expr_str = expr_str.replace(token + '(', name + '(')

    return expr_str


def _parse_expression_string(expression_string):
    """
    Parses and normalizes a user-supplied expression string into a SymPy expression.
    Returns (parsed_expr, error_message_or_None).
    """
    expr_str = expression_string.strip()
    if not expr_str:
        return None, "❌ Error: Expression cannot be empty."

    # Convert unicode superscript and caret -> **
    expr_str = unicode_to_normal_expr(expr_str)
    expr_processed = expr_str.replace('^', '**')

    # Apply implicit multiplication heuristics (safer version)
    expr_processed = insert_implicit_multiplication_rules(expr_processed)

    # Whitelist of allowed functions/constants for parse_expr local namespace
    allowed_locals = {
        # elementary trig
        'sin': sin, 'cos': cos, 'tan': tan, 'cot': cot, 'sec': sec, 'csc': csc,
        # inverse trig
        'asin': asin, 'acos': acos, 'atan': atan,
        # hyperbolic
        'sinh': sinh, 'cosh': cosh, 'tanh': tanh,
        # other math
        'exp': exp, 'log': log, 'sqrt': sqrt, 'Abs': Abs,
        # constants
        'pi': pi, 'E': E
    }

    try:
        transformations = standard_transformations + (implicit_multiplication_application, convert_xor)
        parsed_expr = parse_expr(expr_processed, transformations=transformations, local_dict=allowed_locals, evaluate=False)
        return parsed_expr, None
    except Exception as e:
        return None, f"❌ Error parsing expression: {e}"

# --- Basic operations (wrap parse + sympy calls) ---

def expand_expr(expression_string):
    parsed_expr, error = _parse_expression_string(expression_string)
    if error:
        return None, error
    try:
        # trig=True will also expand trig identities where applicable
        expanded = expand(parsed_expr, trig=True)
        return normal_to_unicode_expr(str(expanded)), None
    except Exception as e:
        return None, f"❌ Error during expansion: {e}"

def simplify_expr(expression_string):
    parsed_expr, error = _parse_expression_string(expression_string)
    if error:
        return None, error
    try:
        # Try algebraic simplify then trigonometric simplification
        simplified = simplify(parsed_expr)
        simplified = trigsimp(simplified)
        try:
            factored_after_simplify = factor(simplified, trig=True)
            return normal_to_unicode_expr(str(factored_after_simplify)), None
        except Exception:
            return normal_to_unicode_expr(str(simplified)), None
    except Exception as e:
        return None, f"❌ Error during simplification: {e}"

def factor_expr(expression_string):
    parsed_expr, error = _parse_expression_string(expression_string)
    if error:
        return None, error
    try:
        # factor(..., trig=True) attempts trig-factorization as well
        factored = factor(parsed_expr, trig=True)
        return normal_to_unicode_expr(str(factored)), None
    except Exception as e:
        return None, f"❌ Error during factorization: {e}. Not all expressions can be factored."

def partial_fraction_decomposition(expression_string):
    """
    Performs partial fraction decomposition on the expression.
    """
    parsed_expr, error = _parse_expression_string(expression_string)
    if error:
        return None, error
    try:
        decomposed = apart(parsed_expr)
        return normal_to_unicode_expr(str(decomposed)), None
    except Exception as e:
        return None, f"❌ Error during partial fraction decomposition: {e}. Ensure the expression is a rational function."

def substitute_expr(full_input_string):
    parts = full_input_string.split(';', 1)
    expression_string = parts[0].strip()
    if not expression_string:
        return None, "❌ Error: Expression part cannot be empty for substitution."
    parsed_expr, error = _parse_expression_string(expression_string)
    if error:
        return None, error
    substitutions = {}
    if len(parts) > 1 and parts[1].strip():
        var_assignments_str = parts[1].strip()
        try:
            assignments = var_assignments_str.split(',')
            for assignment in assignments:
                assignment = assignment.strip()
                if not assignment:
                    continue
                var_val = assignment.split('=', 1)
                if len(var_val) != 2:
                    return None, f"❌ Error: Invalid variable assignment format: '{assignment}'. Expected 'var=value'."
                var_name = var_val[0].strip()
                val_str = var_val[1].strip()
                if not var_name:
                    return None, f"❌ Error: Variable name cannot be empty in '{assignment}'."
                if not val_str:
                    return None, f"❌ Error: Value cannot be empty for variable '{var_name}'."
                try:
                    val = sympify(val_str)
                except Exception as e_val:
                    return None, f"❌ Error: Could not parse value '{val_str}' for variable '{var_name}': {e_val}"
                substitutions[symbols(var_name)] = val
        except Exception as e_parse_subs:
            return None, f"❌ Error parsing variable assignments: {e_parse_subs}"
    else:
        if parsed_expr.free_symbols:
            return None, "❌ Error: Expression has variables but no values provided for substitution. Format: expr; var1=val1, var2=val2"
    try:
        substituted_expr = parsed_expr.subs(substitutions)
        if not substituted_expr.free_symbols:
            evaluated_result = substituted_expr.evalf()
            return str(evaluated_result), None
        else:
            return normal_to_unicode_expr(str(substituted_expr)), None
    except Exception as e:
        return None, f"❌ Error during substitution/evaluation: {e}"

# --- Worker/timeout helper for heavy CAS operations ---
def _worker_wrapper(fn, q, *args, **kwargs):
    """Run fn(*args, **kwargs) and put (result, latex, error) in queue."""
    try:
        res = fn(*args, **kwargs)
        # res may be a tuple or a SymPy object or string
        if isinstance(res, tuple) and len(res) == 3:
            q.put(res)
        else:
            # single returned expression -> produce display and latex
            display = normal_to_unicode_expr(str(res))
            try:
                latex = sympy_latex(res)
            except Exception:
                latex = str(res)
            q.put((display, latex, None))
    except Exception as e:
        q.put((None, None, f"{e}\n{traceback.format_exc()}"))

def _run_with_timeout(fn, args=(), kwargs=None, timeout=5):
    """
    Run fn in separate process with timeout (seconds).
    Returns (display, latex, error) where one of display/latex is filled on success.
    """
    if kwargs is None:
        kwargs = {}
    q = Queue()
    p = Process(target=_worker_wrapper, args=(fn, q) + args, kwargs=kwargs)
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        p.join()
        return None, None, f"❌ Error: Operation timed out after {timeout} seconds."
    try:
        if q.empty():
            return None, None, "❌ Error: Worker did not return a result."
        display, latex, err = q.get_nowait()
        return display, latex, err
    except Exception as e:
        return None, None, f"❌ Error retrieving worker result: {e}"

# --- Integration support ---

def _parse_integration_request(full_input_string):
    """
    Supported forms:
    - "expr"                      => indefinite, variable autodetected (if single symbol)
    - "expr ; x"                  => indefinite, variable x
    - "expr ; x=a,b"              => definite integral from a to b
    """
    parts = full_input_string.split(';', 1)
    expr_part = parts[0].strip()
    if not expr_part:
        return None, None, None, "❌ Error: Expression cannot be empty."

    parsed_expr, err = _parse_expression_string(expr_part)
    if err:
        return None, None, None, err

    var = None
    limits = None

    if len(parts) > 1 and parts[1].strip():
        varpart = parts[1].strip()
        # expect either "x" or "x=a,b"
        if '=' in varpart:
            try:
                varname, bounds = varpart.split('=', 1)
                varname = varname.strip()
                bounds = bounds.strip()
                if ',' in bounds:
                    a_str, b_str = bounds.split(',', 1)
                elif '..' in bounds:
                    a_str, b_str = bounds.split('..', 1)
                else:
                    return None, None, None, "❌ Error: Definite integral bounds must be 'a,b' or 'a..b'."
                a = sympify(a_str.strip())
                b = sympify(b_str.strip())
                var = Symbol(varname)
                limits = (a, b)
            except Exception as e:
                return None, None, None, f"❌ Error parsing variable/limits: {e}"
        else:
            varname = varpart.strip()
            try:
                var = Symbol(varname)
            except Exception as e:
                return None, None, None, f"❌ Error: Invalid variable name '{varname}': {e}"
    else:
        syms = list(parsed_expr.free_symbols)
        if len(syms) == 1:
            var = syms[0]
        elif len(syms) == 0:
            var = Symbol('x')  # default
        else:
            return None, None, None, "❌ Error: multiple variables detected — specify variable like '; x' or '; x=a,b'."

    return parsed_expr, var, limits, None

def _manualintegrate_worker(parsed_expr, var, limits):
    """
    Worker target to attempt manualintegrate then fallback to sympy.integrate.
    Includes partial fraction decomposition for rational functions.
    Returns SymPy expression (antiderivative for indefinite or value for definite).
    """
    # Check if the expression is a rational function of the integration variable
    # If the expression is a rational function of the variable, perform partial fraction decomposition
    if parsed_expr.is_rational_function(var):
        try:
            # Apply partial fraction decomposition using `apart`
            parsed_expr = apart(parsed_expr, var)
        except Exception:
            # If apart fails (e.g., SymPy issues), continue with original expression
            pass

    # Try manualintegrate for an indefinite antiderivative
    if limits is None:
        try:
            manual_res = manualintegrate(parsed_expr, var)
            # manualintegrate can return an expression or raise NotImplementedError or return Integral
            if isinstance(manual_res, SympyIntegral):
                # fallback to direct integration
                return sympy_integrate(parsed_expr, var)
            return manual_res
        except NotImplementedError:
            return sympy_integrate(parsed_expr, var)
    else:
        a, b = limits
        return sympy_integrate(parsed_expr, (var, a, b))

def integrate_expr(full_input_string, timeout_seconds=6):
    """
    Integrates expression with optional variable and limits:
    - Input syntax: "expr" or "expr ; x" or "expr ; x=a,b"
    Returns (display_result_str, latex_result_str, error_or_None).
    For indefinite integrals the display ends with ' + C' and latex ends with '+ C'.
    """
    parsed_expr, var, limits, err = _parse_integration_request(full_input_string)
    if err:
        return None, None, err

    # Use worker with timeout for heavy CAS work
    display, latex, worker_err = _run_with_timeout(
        _manualintegrate_worker,
        args=(parsed_expr, var, limits),
        timeout=timeout_seconds
    )

    if worker_err:
        return None, None, worker_err

    # For indefinite integrals append + C
    if limits is None and display is not None and latex is not None:
        display = display + " + C"
        latex = latex + " + C"
    return display, latex, None

# --- Resimplify: re-simplify an already computed result (strong trig simplification) ---
def resimplify_expr(expression_string):
    """
    Takes a result string (or expression string), strips trailing '+ C' if present,
    parses it, and applies aggressive simplification including trig simplification
    and log combining. Returns (display_str, error_or_None).
    """
    # strip trailing '+ C' (common for indefinite integrals) to avoid parse problems
    expr_str = expression_string.strip()
    # remove trailing + C or +C (case-insensitive, with optional spaces)
    expr_str = re.sub(r'\s*\+\s*C\s*$', '', expr_str, flags=re.IGNORECASE)

    parsed_expr, error = _parse_expression_string(expr_str)
    if error:
        return None, error
    try:
        s = simplify(parsed_expr)     # algebraic simplify
        s = trigsimp(s)               # trig simplification

        # attempt to combine logs — import locally in case environment differs
        try:
            from sympy import logcombine
            # logcombine can sometimes raise for certain forms; guard it
            s = logcombine(s, force=True)
        except Exception:
            # ignore logcombine errors and continue with what we have
            pass

        # final tidy: factor trig-aware if it helps readability
        try:
            s = factor(s, trig=True)
        except Exception:
            pass

        # convert to nicer display (unicode superscripts etc.)
        return normal_to_unicode_expr(str(s)), None
    except Exception as e:
        return None, f"❌ Error during re-simplification: {e}"