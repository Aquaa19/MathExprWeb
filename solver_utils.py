# solver_utils.py
# Full parsing / transformation logic + integrate support + trig-aware expand/factor/simplify and resimplify.

import re
import traceback
from multiprocessing import Process, Queue
from sympy import (
    expand, simplify, factor, sympify, symbols, Symbol, latex as sympy_latex,
    integrate as sympy_integrate, Integral as SympyIntegral,
    sin, cos, tan, cot, sec, csc,
    asin, acos, atan, acot, asec, acsc,
    sinh, cosh, tanh,
    exp, log, sqrt, Abs, pi, E, trigsimp,
    apart,
    diff as sympy_diff, # ADDED: for differentiation
    idiff # NEW: for implicit differentiation
)
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor
)
# REMOVED: from sympy.integrals.manualintegrate import manualintegrate
from sympy import logcombine
from sympy.integrals.transforms import (
    laplace_transform, fourier_transform, mellin_transform
)

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
        'asin','acos','atan','acot','asec','acsc',
        'arcsin', 'arccos', 'arctan', 'arccot', 'arcsec', 'arccsc',
        'sinh','cosh','tanh',
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
        'asin': asin, 'acos': acos, 'atan': atan, 'acot': acot, 'asec': asec, 'acsc': acsc,
        'arcsin': asin, 'arccos': acos, 'arctan': atan, 'arccot': acot, 'arcsec': asec, 'arccsc': acsc,
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

# --- Helper for Formatting Output ---

def _format_output(sympy_result):
    """Converts a SymPy object into both display and LaTeX strings."""
    # SymPy transform results can be tuples (result, convergence_conditions)
    if isinstance(sympy_result, tuple):
        result_expr = sympy_result[0]
        # Append conditions to display string (optional)
        display_conditions = f" (Conditions: {', '.join(map(str, sympy_result[1:]))})"
    else:
        result_expr = sympy_result
        display_conditions = ""

    display = normal_to_unicode_expr(str(result_expr))
    
    try:
        latex = sympy_latex(result_expr)
    except Exception:
        # Fallback to string representation if latex conversion fails
        latex = str(result_expr)
        
    return display + display_conditions, latex, None

def get_latex_from_expr(expression_string):
    """
    Parses a string and attempts to convert it directly to LaTeX format.
    Returns (latex_string, error_message_or_None).
    """
    if not expression_string.strip():
        return "", None

    # We use expression_string.split(';', 1)[0].strip() here to ensure we only
    # parse the main expression part for the live preview, ignoring variables/limits
    expr_for_preview = expression_string.split(';', 1)[0].strip()
    
    if not expr_for_preview:
        return "", None
        
    # If it's an equation, we parse both sides and show them separated
    if '=' in expr_for_preview:
        eq_parts = expr_for_preview.split('=', 1)
        lhs_str = eq_parts[0]
        rhs_str = eq_parts[1] if len(eq_parts) > 1 else '0' # Default RHS to 0 if empty
        
        lhs_parsed, err_lhs = _parse_expression_string(lhs_str)
        rhs_parsed, err_rhs = _parse_expression_string(rhs_str)
        
        if err_lhs: return None, err_lhs
        if err_rhs: return None, err_rhs
        
        try:
            lhs_latex = sympy_latex(lhs_parsed)
            rhs_latex = sympy_latex(rhs_parsed)
            return f"{lhs_latex} = {rhs_latex}", None
        except Exception:
            # Fallback for latex failure
            return f"\\text{{{str(lhs_parsed)} = {str(rhs_parsed)}}}", None


    parsed_expr, error = _parse_expression_string(expr_for_preview)
    if error:
        # If parsing fails, return the error message for display
        return None, error 
        
    try:
        # Here we only need the LaTeX part
        latex = sympy_latex(parsed_expr)
        return latex, None
    except Exception:
        # Fallback to string if latex conversion itself fails
        return f"\\text{{{str(parsed_expr)}}}", None

# --- Basic operations (wrap parse + sympy calls) ---

def expand_expr(expression_string):
    parsed_expr, error = _parse_expression_string(expression_string)
    if error:
        return None, None, error
    try:
        # trig=True will also expand trig identities where applicable
        expanded = expand(parsed_expr, trig=True)
        return _format_output(expanded)
    except Exception as e:
        return None, None, f"❌ Error during expansion: {e}"

def simplify_expr(expression_string):
    parsed_expr, error = _parse_expression_string(expression_string)
    if error:
        return None, None, error
    try:
        # Try algebraic simplify then trigonometric simplification
        simplified = simplify(parsed_expr)
        simplified = trigsimp(simplified)
        try:
            # Try to factor the simplified result for readability
            result = factor(simplified, trig=True)
        except Exception:
            result = simplified
            
        return _format_output(result)
    except Exception as e:
        return None, None, f"❌ Error during simplification: {e}"

def factor_expr(expression_string):
    parsed_expr, error = _parse_expression_string(expression_string)
    if error:
        return None, None, error
    try:
        # factor(..., trig=True) attempts trig-factorization as well
        factored = factor(parsed_expr, trig=True)
        return _format_output(factored)
    except Exception as e:
        return None, None, f"❌ Error during factorization: {e}. Not all expressions can be factored."

def substitute_expr(full_input_string):
    parts = full_input_string.split(';', 1)
    expression_string = parts[0].strip()
    if not expression_string:
        return None, None, "❌ Error: Expression part cannot be empty for substitution."
    parsed_expr, error = _parse_expression_string(expression_string)
    if error:
        return None, None, error
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
                    return None, None, f"❌ Error: Invalid variable assignment format: '{assignment}'. Expected 'var=value'."
                var_name = var_val[0].strip()
                val_str = var_val[1].strip()
                if not var_name:
                    return None, None, f"❌ Error: Variable name cannot be empty in '{assignment}'."
                if not val_str:
                    return None, None, f"❌ Error: Value cannot be empty for variable '{var_name}'."
                try:
                    val = sympify(val_str)
                except Exception as e_val:
                    return None, None, f"❌ Error: Could not parse value '{val_str}' for variable '{var_name}': {e_val}"
                substitutions[symbols(var_name)] = val
        except Exception as e_parse_subs:
            return None, None, f"❌ Error parsing variable assignments: {e_parse_subs}"
    else:
        if parsed_expr.free_symbols:
            return None, None, "❌ Error: Expression has variables but no values provided for substitution. Format: expr; var1=val1, var2=val2"
    try:
        substituted_expr = parsed_expr.subs(substitutions)
        
        if not substituted_expr.free_symbols:
            evaluated_result = substituted_expr.evalf()
            display = str(evaluated_result)
            latex = sympy_latex(evaluated_result)
            return display, latex, None
        else:
            return _format_output(substituted_expr)
    except Exception as e:
        return None, None, f"❌ Error during substitution/evaluation: {e}"

def differentiate_expr(full_input_string):
    """
    Differentiates an expression (Explicit/Partial) or an equation (Implicit).
    Explicit Input: expr or expr; var, order (e.g., x^3; x, 2)
    Implicit Input: equation=expr; dependent_var, independent_var (e.g., x^2+y^2=1; y, x)
    """
    parts = full_input_string.split(';', 1)
    expr_or_equation_string = parts[0].strip()

    if not expr_or_equation_string:
        return None, None, "❌ Error: Expression or equation cannot be empty."

    # --- Implicit Differentiation Check ---
    if '=' in expr_or_equation_string:
        # Implicit Differentiation Case: F(x, y) = 0
        eq_parts = expr_or_equation_string.split('=', 1)
        
        # Calculate F = LHS - RHS
        lhs_parsed, err_lhs = _parse_expression_string(eq_parts[0])
        if err_lhs: return None, None, f"❌ Error parsing LHS: {err_lhs}"

        if len(eq_parts) > 1 and eq_parts[1].strip():
            rhs_parsed, err_rhs = _parse_expression_string(eq_parts[1])
            if err_rhs: return None, None, f"❌ Error parsing RHS: {err_rhs}"
        else:
            # If RHS is empty (e.g., x^2+y^2=) treat as = 0
            rhs_parsed = sympify(0)
            
        F_expr = lhs_parsed - rhs_parsed

        # Parse variables part: dependent_var, independent_var
        dependent_var_name = 'y' # Default dependent var
        independent_var_name = 'x' # Default independent var
        
        if len(parts) > 1 and parts[1].strip():
            var_part = parts[1].strip()
            # Split by comma to find dependent and independent variables
            var_parts_split = [p.strip() for p in var_part.split(',', 2)]
            
            if len(var_parts_split) == 1:
                # If only one var is provided, assume it's the dependent variable and independent is 'x'
                dependent_var_name = var_parts_split[0]
            elif len(var_parts_split) >= 2:
                # Both dependent and independent are provided (e.g., y, x)
                dependent_var_name = var_parts_split[0]
                independent_var_name = var_parts_split[1]
            
        try:
            dependent = Symbol(dependent_var_name)
            independent = Symbol(independent_var_name)
        except Exception as e:
            return None, None, f"❌ Error: Invalid variable names: {e}"

        try:
            # SymPy idiff signature: idiff(eq, dependent_var, independent_var)
            differentiated = idiff(F_expr, dependent, independent)
            return _format_output(differentiated)
        except Exception as e:
            return None, None, f"❌ Error during implicit differentiation: {e}"

    # --- Explicit/Partial Differentiation Case (Existing Logic) ---
    else:
        expression_string = expr_or_equation_string
        parsed_expr, error = _parse_expression_string(expression_string)
        if error:
            return None, None, error

        var = Symbol('x') # Default variable is 'x'
        order = 1         # Default order is 1 (first derivative)

        if len(parts) > 1 and parts[1].strip():
            var_part = parts[1].strip()
            # Expecting: "x" (variable only) or "x, 2" (variable and order)
            var_parts_split = [p.strip() for p in var_part.split(',', 1)]
            
            var_name = var_parts_split[0]
            try:
                var = Symbol(var_name)
            except Exception as e:
                return None, None, f"❌ Error: Invalid variable name '{var_name}'"
                
            if len(var_parts_split) > 1:
                try:
                    order = int(var_parts_split[1])
                    if order <= 0:
                        return None, None, "❌ Error: Differentiation order must be a positive integer."
                except ValueError:
                    return None, None, f"❌ Error: Invalid order '{var_parts_split[1]}'. Must be an integer."

        try:
            # SymPy diff signature: diff(expr, var, order)
            differentiated = sympy_diff(parsed_expr, var, order)
            return _format_output(differentiated)
        except Exception as e:
            return None, None, f"❌ Error during differentiation: {e}"

# --- Helper for Transform Functions ---

def _parse_transform_request(full_input_string, expected_vars=2):
    """
    Parses Laplace/Fourier/Mellin Transform requests.
    Input format: expr; input_var, transform_var
    Returns: (parsed_expr, input_var, transform_var, error_or_None)
    """
    parts = full_input_string.split(';', 1)
    expr_part = parts[0].strip()
    
    if not expr_part:
        return None, None, None, "❌ Error: Expression cannot be empty."

    parsed_expr, err = _parse_expression_string(expr_part)
    if err:
        return None, None, None, err

    if len(parts) < 2 or not parts[1].strip():
        return None, None, None, "❌ Error: Please specify input and transform variables. Format: expr; input_var, transform_var"

    var_parts = [p.strip() for p in parts[1].split(',', expected_vars)]
    
    if len(var_parts) != expected_vars:
        return None, None, None, f"❌ Error: Expected {expected_vars} variables (input, transform) but received {len(var_parts)}."
    
    try:
        input_var = Symbol(var_parts[0])
        transform_var = Symbol(var_parts[1])
    except Exception as e:
        return None, None, None, f"❌ Error: Invalid variable name: {e}"

    return parsed_expr, input_var, transform_var, None

# --- Integral Transform operations ---

def laplace_transform_expr(full_input_string):
    """Laplace Transform: L{f(t)}(s) = F(s). Input: expr; t, s"""
    parsed_expr, var, transform_var, err = _parse_transform_request(full_input_string)
    if err:
        return None, None, err
    try:
        # laplace_transform returns (F(s), a, cond)
        result_tuple = laplace_transform(parsed_expr, var, transform_var)
        # _format_output handles the result tuple
        return _format_output(result_tuple)
    except Exception as e:
        return None, None, f"❌ Error during Laplace Transform: {e}"

def fourier_transform_expr(full_input_string):
    """Fourier Transform: F{f(x)}(k) = F(k). Input: expr; x, k"""
    parsed_expr, var, transform_var, err = _parse_transform_request(full_input_string)
    if err:
        return None, None, err
    try:
        # fourier_transform returns (F(k), cond)
        result_tuple = fourier_transform(parsed_expr, var, transform_var)
        # _format_output handles the result tuple
        return _format_output(result_tuple)
    except Exception as e:
        return None, None, f"❌ Error during Fourier Transform: {e}"

def mellin_transform_expr(full_input_string):
    """Mellin Transform: M{f(x)}(s) = F(s). Input: expr; x, s"""
    parsed_expr, var, transform_var, err = _parse_transform_request(full_input_string)
    if err:
        return None, None, err
    try:
        # mellin_transform returns (F(s), (a, b), cond)
        result_tuple = mellin_transform(parsed_expr, var, transform_var)
        # _format_output handles the result tuple
        return _format_output(result_tuple)
    except Exception as e:
        return None, None, f"❌ Error during Mellin Transform: {e}"

# --- Worker/timeout helper for heavy CAS operations ---
def _worker_wrapper(fn, q, *args, **kwargs):
    """Run fn(*args, **kwargs) and put (result, latex, error) in queue."""
    try:
        res = fn(*args, **kwargs)
        # Check if the result is already a (display, latex, error) tuple 
        if isinstance(res, tuple) and len(res) == 3 and res[2] is not None:
            # If it's an error tuple, pass it through
            q.put(res)
        elif isinstance(res, tuple) and len(res) == 3:
             # If it's a display, latex, None tuple (from the new functions), pass it
             q.put(res)
        else:
            # single returned expression -> produce display and latex
            display, latex, err = _format_output(res)
            q.put((display, latex, err))
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
                limits = (var, a, b) 
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
            return None, None, None, "❌ Error: Multiple variables detected. Please specify the integration variable. Example: x+a; x"

    return parsed_expr, var, limits, None

def _manualintegrate_worker(parsed_expr, var, limits):
    """
    Worker target to perform integration.
    Includes partial fraction decomposition for rational functions and relies on
    sympy.integrate for complex techniques like trigonometric substitution.
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
            
    # --- OPTIMIZATION FOR COMPLEX INTEGRALS LIKE sin(2x) * exp(...) ---
    try:
        # 1. Use trigsimp to handle basic trig identities
        simplified_expr = trigsimp(parsed_expr)
        # 2. Use factor with trig=True to expand sin(2x) etc., which is key for u-sub
        parsed_expr = factor(simplified_expr, trig=True)
    except Exception:
        # Ignore simplification failure and proceed with the original expression.
        pass

    # Use the powerful sympy_integrate directly to handle all complex cases
    if limits is None:
        # Indefinite integral (handles trigonometric substitution, u-sub, etc.)
        return sympy_integrate(parsed_expr, var)
    else:
        # Definite integral
        return sympy_integrate(parsed_expr, limits)

def integrate_expr(full_input_string, timeout_seconds=20):
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
    and log combining. Returns (display_str, latex_str, error_or_None).
    """
    # strip trailing '+ C' (common for indefinite integrals) to avoid parse problems
    expr_str = expression_string.strip()
    # remove trailing + C or +C (case-insensitive, with optional spaces)
    expr_str = re.sub(r'\s*\+\s*C\s*$', '', expr_str, flags=re.IGNORECASE)

    parsed_expr, error = _parse_expression_string(expr_str)
    if error:
        return None, None, error
    try:
        s = simplify(parsed_expr)     # algebraic simplify
        s = trigsimp(s)               # trig simplification

        # attempt to combine logs
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
        return _format_output(s)
    except Exception as e:
        return None, None, f"❌ Error during re-simplification: {e}"