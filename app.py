from flask import Flask, render_template, request, jsonify
from sympy import symbols, Function, dsolve, Eq, simplify, latex, classify_ode, exp, log, sin, cos, tan, sqrt, atan, asin, acos, pi as sympy_pi
from sympy import integrate, diff, Symbol, Wild, Rational, parse_expr, sympify, solve as sympy_solve, subs
from sympy.parsing.sympy_parser import parse_expr as sympy_parse_expr, standard_transformations, implicit_multiplication_application
import re

app = Flask(__name__)

# Configurar transformaciones para parsing
transformations = (standard_transformations + (implicit_multiplication_application,))

# Manejador de errores para la ruta /solve
def ensure_json_response(func):
    """Decorador para asegurar que la ruta siempre devuelva JSON"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            return jsonify({
                'success': False,
                'solution': None,
                'steps': [f'❌ Error inesperado: {str(e)}', f'📄 Detalles: {error_trace[:300]}']
            }), 500
    wrapper.__name__ = func.__name__
    return wrapper

def normalize_and_simplify_solution(solution):
    """
    Normaliza y simplifica una solución de dsolve.
    Maneja el caso donde dsolve devuelve una lista de soluciones.
    """
    if solution is None:
        return None
    
    try:
        # Si es una lista, simplificar cada elemento
        if isinstance(solution, list):
            if len(solution) == 0:
                return None
            if len(solution) == 1:
                # Si solo hay una solución, devolverla simplificada
                try:
                    return simplify(solution[0])
                except:
                    return solution[0]  # Si falla, devolver original
            else:
                # Múltiples soluciones, simplificar cada una
                result = []
                for sol in solution:
                    try:
                        result.append(simplify(sol))
                    except:
                        result.append(sol)  # Si falla, devolver original
                return result
        
        # Si no es una lista, simplificar normalmente
        try:
            return simplify(solution)
        except:
            return solution  # Si falla, devolver original
    except Exception:
        # Si algo falla, devolver la solución original
        return solution

def parse_equation_string(eq_str):
    """
    Parsea una ecuación diferencial desde string de manera segura usando SymPy
    """
    x = symbols('x')
    y_func = Function('y')
    
    # Normalizar espacios
    eq_str = eq_str.strip()
    
    # Normalizar caracteres Unicode especiales a ASCII estándar
    # Guion menos Unicode (U+2212) y otros guiones especiales → guion normal
    eq_str = eq_str.replace('−', '-')  # U+2212 (MINUS SIGN)
    eq_str = eq_str.replace('–', '-')  # U+2013 (EN DASH)
    eq_str = eq_str.replace('—', '-')  # U+2014 (EM DASH)
    
    # Superíndices Unicode → formato potencia estándar
    superscript_map = {
        '²': '^2',  # U+00B2 (SUPERSCRIPT TWO)
        '³': '^3',  # U+00B3 (SUPERSCRIPT THREE)
        '¹': '^1',  # U+00B9 (SUPERSCRIPT ONE)
        '⁰': '^0',  # U+2070 (SUPERSCRIPT ZERO)
        '⁴': '^4',  # U+2074
        '⁵': '^5',  # U+2075
        '⁶': '^6',  # U+2076
        '⁷': '^7',  # U+2077
        '⁸': '^8',  # U+2078
        '⁹': '^9',  # U+2079
    }
    for sup, replacement in superscript_map.items():
        eq_str = eq_str.replace(sup, replacement)
    
    # Subíndices Unicode (menos común pero posible)
    subscript_map = {
        '₂': '_2',  # U+2082
        '₃': '_3',  # U+2083
        '₁': '_1',  # U+2081
        '₀': '_0',  # U+2080
    }
    for sub, replacement in subscript_map.items():
        eq_str = eq_str.replace(sub, replacement)
    
    # Preparar diccionario local para el parser
    local_dict = {
        'x': x,
        'y': y_func,
        'diff': diff,
        'exp': exp,
        'log': log,
        'ln': log,  # Alias para logaritmo natural
        'sin': sin,
        'cos': cos,
        'tan': tan,
        'sqrt': sqrt,
        'Symbol': Symbol,
        'Eq': Eq,
        'abs': abs,
        'pi': sympy_pi,
        'E': exp(1),
        'e': exp(1)
    }
    
    # Normalizar la ecuación
    eq_normalized = eq_str
    
    # Reemplazar comas por puntos en números decimales (formato europeo)
    eq_normalized = re.sub(r'(\d),(\d)', r'\1.\2', eq_normalized)
    
    # Reemplazar ^ por ** para potencias PRIMERO
    eq_normalized = eq_normalized.replace('^', '**')
    
    # Reemplazar derivadas usando marcadores temporales únicos ANTES de agregar multiplicación
    # Usar marcadores que NO puedan ser afectados por regex de multiplicación implícita
    # Usar un formato con números y caracteres especiales que evite conflictos
    eq_normalized = re.sub(r"y'''", "@@@DERIV_3@@@", eq_normalized)
    eq_normalized = re.sub(r"y''", "@@@DERIV_2@@@", eq_normalized)
    eq_normalized = re.sub(r"y'", "@@@DERIV_1@@@", eq_normalized)
    eq_normalized = re.sub(r"dy/dx", "@@@DERIV_1@@@", eq_normalized)
    eq_normalized = re.sub(r"d\^?2y/dx\^?2", "@@@DERIV_2@@@", eq_normalized)
    
    # Agregar multiplicación implícita de forma cuidadosa
    # Números seguidos de letras (3x -> 3*x) - NO afecta marcadores @@@DERIV_*@@@
    eq_normalized = re.sub(r'(\d+)([a-zA-Z_])', r'\1*\2', eq_normalized)
    # Números seguidos de paréntesis (3(x+y) -> 3*(x+y))
    eq_normalized = re.sub(r'(\d+)\s*\(', r'\1*(', eq_normalized)
    # Paréntesis cerrado seguido de letra o número ((x+y)x -> (x+y)*x)
    eq_normalized = re.sub(r'\)\s*([a-zA-Z0-9_])', r')*\1', eq_normalized)
    
    # Manejar e^x y e**(x) como exp(x)
    eq_normalized = re.sub(r'\be\*\*x\b', 'exp(x)', eq_normalized)
    eq_normalized = re.sub(r'\be\*\*\(x\)', 'exp(x)', eq_normalized)
    
    try:
        # Detectar si hay igualdad
        if '=' in eq_normalized:
            left_str, right_str = eq_normalized.split('=', 1)
            left_str = left_str.strip()
            right_str = right_str.strip()
            
            # Reemplazar marcadores de derivadas con diff() PRIMERO
            left_str = left_str.replace('@@@DERIV_3@@@', 'diff(y(x), x, 3)')
            left_str = left_str.replace('@@@DERIV_2@@@', 'diff(y(x), x, 2)')
            left_str = left_str.replace('@@@DERIV_1@@@', 'diff(y(x), x)')
            right_str = right_str.replace('@@@DERIV_3@@@', 'diff(y(x), x, 3)')
            right_str = right_str.replace('@@@DERIV_2@@@', 'diff(y(x), x, 2)')
            right_str = right_str.replace('@@@DERIV_1@@@', 'diff(y(x), x)')
            
            # Agregar multiplicación implícita donde falte (después de procesar derivadas)
            # Números seguidos de letras (3x -> 3*x, 4y -> 4*y)
            # Pero proteger diff, exp, log, sin, cos, tan, sqrt
            func_protect = r'(?!(?:diff|exp|log|ln|sin|cos|tan|sqrt|abs)\()'
            left_str = re.sub(rf'(\d+)([a-zA-Z_]){func_protect}', r'\1*\2', left_str)
            right_str = re.sub(rf'(\d+)([a-zA-Z_]){func_protect}', r'\1*\2', right_str)
            
            # Reemplazar y que no esté en diff, y(x), o funciones
            left_str = re.sub(r'(?<!diff\(y\()(?<!exp\()(?<!log\()(?<!sin\()(?<!cos\()(?<!tan\()(?<!sqrt\()\by\b(?!\()(?!\w)', 'y(x)', left_str)
            right_str = re.sub(r'(?<!diff\(y\()(?<!exp\()(?<!log\()(?<!sin\()(?<!cos\()(?<!tan\()(?<!sqrt\()\by\b(?!\()(?!\w)', 'y(x)', right_str)
            
            # Agregar multiplicación implícita después de reemplazar y
            # Números seguidos de y(x) (4y(x) -> 4*y(x))
            left_str = re.sub(r'(\d+)(y\(x\))', r'\1*\2', left_str)
            right_str = re.sub(r'(\d+)(y\(x\))', r'\1*\2', right_str)
            # Variables seguidas de y(x) (xy(x) -> x*y(x))
            left_str = re.sub(r'([a-zA-Z_])(y\(x\))', r'\1*\2', left_str)
            right_str = re.sub(r'([a-zA-Z_])(y\(x\))', r'\1*\2', right_str)
            
            # Intentar parsear usando SymPy parser primero
            try:
                left_expr = sympy_parse_expr(left_str, local_dict=local_dict, transformations=transformations)
                right_expr = sympy_parse_expr(right_str, local_dict=local_dict, transformations=transformations)
                eq = Eq(left_expr, right_expr)
            except Exception as parse_err:
                # Si falla, intentar con eval como respaldo
                try:
                    left_expr = eval(left_str, {"__builtins__": {}}, local_dict)
                    right_expr = eval(right_str, {"__builtins__": {}}, local_dict)
                    eq = Eq(left_expr, right_expr)
                except Exception as eval_err:
                    raise Exception(f"Error al parsear: parser={str(parse_err)[:100]}, eval={str(eval_err)[:100]}. Izquierda: '{left_str}', Derecha: '{right_str}'")
        else:
            # Sin igualdad, asumir igualado a 0
            eq_normalized = eq_normalized.replace('@@@DERIV_3@@@', 'diff(y(x), x, 3)')
            eq_normalized = eq_normalized.replace('@@@DERIV_2@@@', 'diff(y(x), x, 2)')
            eq_normalized = eq_normalized.replace('@@@DERIV_1@@@', 'diff(y(x), x)')
            eq_normalized = re.sub(r'(?<!diff\(y\()\by\b(?!\()(?!\w)', 'y(x)', eq_normalized)
            try:
                expr = sympy_parse_expr(eq_normalized, local_dict=local_dict, transformations=transformations)
                eq = Eq(expr, 0)
            except Exception as parse_err:
                try:
                    expr = eval(eq_normalized, {"__builtins__": {}}, local_dict)
                    eq = Eq(expr, 0)
                except Exception as eval_err:
                    raise Exception(f"Error al parsear: parser={str(parse_err)[:100]}, eval={str(eval_err)[:100]}. Expresión: '{eq_normalized}'")
        
        return eq
    except Exception as e:
        error_msg = str(e)
        raise Exception(f"Error al parsear la ecuación: {error_msg}")

def solve_separable(eq, steps):
    """Resuelve ecuaciones de variables separables"""
    x = symbols('x')
    y = Function('y')(x)
    
    steps.append("**Ecuación de Variables Separables**")
    steps.append(f"Ecuación original: $$latex({latex(eq)})$$")
    
    try:
        solution = dsolve(eq, y, hint='separable')
        if isinstance(solution, list):
            steps.append(f"✅ Solución encontrada (múltiples soluciones):")
            for i, sol in enumerate(solution, 1):
                steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
        else:
            steps.append(f"✅ Solución encontrada: $$latex({latex(solution)})$$")
        
        solution = normalize_and_simplify_solution(solution)
        return solution
    except Exception as e:
        try:
            solution = dsolve(eq, y)
            if isinstance(solution, list):
                steps.append(f"✅ Solución encontrada (método alternativo) - múltiples soluciones:")
                for i, sol in enumerate(solution, 1):
                    steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
            else:
                steps.append(f"✅ Solución encontrada (método alternativo): $$latex({latex(solution)})$$")
            solution = normalize_and_simplify_solution(solution)
            return solution
        except Exception as e2:
            error_msg = str(e) if 'e' in locals() else str(e2)
            steps.append(f"❌ Error al resolver con método específico: {error_msg}")
            steps.append(f"⚠️ Intentando método alternativo...")
            try:
                solution = dsolve(eq, y)
                if isinstance(solution, list):
                    steps.append(f"✅ Solución encontrada (método general) - múltiples soluciones:")
                    for i, sol in enumerate(solution, 1):
                        steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                else:
                    steps.append(f"✅ Solución encontrada (método general): $$latex({latex(solution)})$$")
                solution = normalize_and_simplify_solution(solution)
                return solution
            except Exception as e3:
                steps.append(f"❌ Error final: {str(e3)}")
                import traceback
                steps.append(f"📄 Traceback: {traceback.format_exc()[:200]}")
                return None

def solve_homogeneous(eq, steps):
    """Resuelve ecuaciones diferenciales homogéneas"""
    x = symbols('x')
    y = Function('y')(x)
    
    steps.append("**Ecuación Diferencial Homogénea**")
    steps.append(f"Ecuación original: $$latex({latex(eq)})$$")
    
    try:
        solution = dsolve(eq, y, hint='homogeneous')
        if isinstance(solution, list):
            steps.append(f"✅ Solución encontrada (múltiples soluciones):")
            for i, sol in enumerate(solution, 1):
                steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
        else:
            steps.append(f"✅ Solución encontrada: $$latex({latex(solution)})$$")
        
        solution = normalize_and_simplify_solution(solution)
        return solution
    except Exception as e:
        try:
            solution = dsolve(eq, y)
            if isinstance(solution, list):
                steps.append(f"✅ Solución encontrada (método alternativo) - múltiples soluciones:")
                for i, sol in enumerate(solution, 1):
                    steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
            else:
                steps.append(f"✅ Solución encontrada (método alternativo): $$latex({latex(solution)})$$")
            solution = normalize_and_simplify_solution(solution)
            return solution
        except Exception as e2:
            error_msg = str(e) if 'e' in locals() else str(e2)
            steps.append(f"❌ Error al resolver con método específico: {error_msg}")
            steps.append(f"⚠️ Intentando método alternativo...")
            try:
                solution = dsolve(eq, y)
                if isinstance(solution, list):
                    steps.append(f"✅ Solución encontrada (método general) - múltiples soluciones:")
                    for i, sol in enumerate(solution, 1):
                        steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                else:
                    steps.append(f"✅ Solución encontrada (método general): $$latex({latex(solution)})$$")
                solution = normalize_and_simplify_solution(solution)
                return solution
            except Exception as e3:
                steps.append(f"❌ Error final: {str(e3)}")
                import traceback
                steps.append(f"📄 Traceback: {traceback.format_exc()[:200]}")
                return None

def solve_exact(eq, steps):
    """Resuelve ecuaciones diferenciales exactas"""
    x = symbols('x')
    y = Function('y')(x)
    
    steps.append("**Ecuación Diferencial Exacta**")
    steps.append(f"Ecuación original: $$latex({latex(eq)})$$")
    
    try:
        solution = dsolve(eq, y, hint='1st_exact')
        if isinstance(solution, list):
            steps.append(f"✅ Solución encontrada (múltiples soluciones):")
            for i, sol in enumerate(solution, 1):
                steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
        else:
            steps.append(f"✅ Solución encontrada: $$latex({latex(solution)})$$")
        
        solution = normalize_and_simplify_solution(solution)
        return solution
    except Exception as e:
        try:
            solution = dsolve(eq, y)
            if isinstance(solution, list):
                steps.append(f"✅ Solución encontrada (método alternativo) - múltiples soluciones:")
                for i, sol in enumerate(solution, 1):
                    steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
            else:
                steps.append(f"✅ Solución encontrada (método alternativo): $$latex({latex(solution)})$$")
            solution = normalize_and_simplify_solution(solution)
            return solution
        except Exception as e2:
            error_msg = str(e) if 'e' in locals() else str(e2)
            steps.append(f"❌ Error al resolver con método específico: {error_msg}")
            steps.append(f"⚠️ Intentando método alternativo...")
            try:
                solution = dsolve(eq, y)
                if isinstance(solution, list):
                    steps.append(f"✅ Solución encontrada (método general) - múltiples soluciones:")
                    for i, sol in enumerate(solution, 1):
                        steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                else:
                    steps.append(f"✅ Solución encontrada (método general): $$latex({latex(solution)})$$")
                solution = normalize_and_simplify_solution(solution)
                return solution
            except Exception as e3:
                steps.append(f"❌ Error final: {str(e3)}")
                import traceback
                steps.append(f"📄 Traceback: {traceback.format_exc()[:200]}")
                return None

def solve_linear(eq, steps):
    """Resuelve ecuaciones diferenciales lineales"""
    x = symbols('x')
    y = Function('y')(x)
    
    steps.append("**Ecuación Diferencial Lineal**")
    steps.append(f"Ecuación original: $$latex({latex(eq)})$$")
    
    # Intentar simplificar la ecuación primero
    try:
        eq_simplified = simplify(eq)
        if eq_simplified != eq:
            steps.append(f"📐 Ecuación simplificada: $$latex({latex(eq_simplified)})$$")
            eq = eq_simplified
    except:
        pass  # Si no se puede simplificar, continuar con la original
    
    try:
        solution = dsolve(eq, y, hint='1st_linear')
        if isinstance(solution, list):
            steps.append(f"✅ Solución encontrada (múltiples soluciones):")
            for i, sol in enumerate(solution, 1):
                steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
        else:
            steps.append(f"✅ Solución encontrada: $$latex({latex(solution)})$$")
        
        solution = normalize_and_simplify_solution(solution)
        return solution
    except Exception as e:
        steps.append(f"⚠️ Método '1st_linear' falló: {str(e)}")
        steps.append(f"🔄 Intentando resolución general...")
        try:
            solution = dsolve(eq, y)
            if isinstance(solution, list):
                steps.append(f"✅ Solución encontrada (método general) - múltiples soluciones:")
                for i, sol in enumerate(solution, 1):
                    steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
            else:
                steps.append(f"✅ Solución encontrada (método general): $$latex({latex(solution)})$$")
            solution = normalize_and_simplify_solution(solution)
            return solution
        except Exception as e2:
            error_msg = str(e) if 'e' in locals() else str(e2)
            steps.append(f"❌ Error al resolver con método específico: {error_msg}")
            steps.append(f"⚠️ Intentando método alternativo...")
            try:
                solution = dsolve(eq, y)
                if isinstance(solution, list):
                    steps.append(f"✅ Solución encontrada (método general) - múltiples soluciones:")
                    for i, sol in enumerate(solution, 1):
                        steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                else:
                    steps.append(f"✅ Solución encontrada (método general): $$latex({latex(solution)})$$")
                solution = normalize_and_simplify_solution(solution)
                return solution
            except Exception as e3:
                steps.append(f"❌ Error final: {str(e3)}")
                import traceback
                steps.append(f"📄 Traceback: {traceback.format_exc()[:200]}")
                return None

def solve_bernoulli(eq, steps):
    """Resuelve ecuaciones diferenciales de Bernoulli"""
    x = symbols('x')
    y = Function('y')(x)
    
    steps.append("**Ecuación Diferencial de Bernoulli**")
    steps.append(f"Ecuación original: $$latex({latex(eq)})$$")
    
    try:
        solution = dsolve(eq, y, hint='Bernoulli')
        if isinstance(solution, list):
            steps.append(f"✅ Solución encontrada (múltiples soluciones):")
            for i, sol in enumerate(solution, 1):
                steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
        else:
            steps.append(f"✅ Solución encontrada: $$latex({latex(solution)})$$")
        
        solution = normalize_and_simplify_solution(solution)
        return solution
    except Exception as e:
        try:
            solution = dsolve(eq, y)
            if isinstance(solution, list):
                steps.append(f"✅ Solución encontrada (método alternativo) - múltiples soluciones:")
                for i, sol in enumerate(solution, 1):
                    steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
            else:
                steps.append(f"✅ Solución encontrada (método alternativo): $$latex({latex(solution)})$$")
            solution = normalize_and_simplify_solution(solution)
            return solution
        except Exception as e2:
            error_msg = str(e) if 'e' in locals() else str(e2)
            steps.append(f"❌ Error al resolver con método específico: {error_msg}")
            steps.append(f"⚠️ Intentando método alternativo...")
            try:
                solution = dsolve(eq, y)
                if isinstance(solution, list):
                    steps.append(f"✅ Solución encontrada (método general) - múltiples soluciones:")
                    for i, sol in enumerate(solution, 1):
                        steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                else:
                    steps.append(f"✅ Solución encontrada (método general): $$latex({latex(solution)})$$")
                solution = normalize_and_simplify_solution(solution)
                return solution
            except Exception as e3:
                steps.append(f"❌ Error final: {str(e3)}")
                import traceback
                steps.append(f"📄 Traceback: {traceback.format_exc()[:200]}")
                return None

def solve_reducible_first_order(eq, steps):
    """Resuelve ecuaciones reducibles a primer orden"""
    x = symbols('x')
    y = Function('y')(x)
    
    steps.append("**Ecuación Reducible a Primer Orden**")
    steps.append(f"Ecuación original: $$latex({latex(eq)})$$")
    
    try:
        solution = dsolve(eq, y)
        if isinstance(solution, list):
            steps.append(f"✅ Solución encontrada (múltiples soluciones):")
            for i, sol in enumerate(solution, 1):
                steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
        else:
            steps.append(f"✅ Solución encontrada: $$latex({latex(solution)})$$")
        
        solution = normalize_and_simplify_solution(solution)
        return solution
    except Exception as e:
        steps.append(f"❌ Error: {str(e)}")
        return None

def solve_constant_coefficients(eq, steps):
    """Resuelve ecuaciones con coeficientes constantes"""
    x = symbols('x')
    y = Function('y')(x)
    
    steps.append("**Ecuación con Coeficientes Constantes**")
    steps.append(f"Ecuación original: $$latex({latex(eq)})$$")
    
    try:
        solution = dsolve(eq, y, hint='nth_linear_constant_coeff_homogeneous')
        if isinstance(solution, list):
            steps.append(f"✅ Solución encontrada (múltiples soluciones):")
            for i, sol in enumerate(solution, 1):
                steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
        else:
            steps.append(f"✅ Solución encontrada: $$latex({latex(solution)})$$")
        
        solution = normalize_and_simplify_solution(solution)
        return solution
    except Exception as e:
        try:
            solution = dsolve(eq, y, hint='nth_linear_constant_coeff_undetermined_coefficients')
            if isinstance(solution, list):
                steps.append(f"✅ Solución encontrada (múltiples soluciones):")
                for i, sol in enumerate(solution, 1):
                    steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
            else:
                steps.append(f"✅ Solución encontrada: $$latex({latex(solution)})$$")
            solution = normalize_and_simplify_solution(solution)
            return solution
        except Exception as e2:
            try:
                solution = dsolve(eq, y)
                if isinstance(solution, list):
                    steps.append(f"✅ Solución encontrada (método general) - múltiples soluciones:")
                    for i, sol in enumerate(solution, 1):
                        steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                else:
                    steps.append(f"✅ Solución encontrada (método general): $$latex({latex(solution)})$$")
                solution = normalize_and_simplify_solution(solution)
                return solution
            except:
                steps.append(f"❌ Error: {str(e)}")
                return None

def solve_undetermined_coefficients(eq, steps):
    """Resuelve usando coeficientes indeterminados"""
    x = symbols('x')
    y = Function('y')(x)
    
    steps.append("**Método de Coeficientes Indeterminados**")
    steps.append(f"Ecuación original: $$latex({latex(eq)})$$")
    
    try:
        solution = dsolve(eq, y, hint='nth_linear_constant_coeff_undetermined_coefficients')
        if isinstance(solution, list):
            steps.append(f"✅ Solución encontrada (múltiples soluciones):")
            for i, sol in enumerate(solution, 1):
                steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
        else:
            steps.append(f"✅ Solución encontrada: $$latex({latex(solution)})$$")
        
        solution = normalize_and_simplify_solution(solution)
        return solution
    except Exception as e:
        try:
            solution = dsolve(eq, y)
            if isinstance(solution, list):
                steps.append(f"✅ Solución encontrada (método alternativo) - múltiples soluciones:")
                for i, sol in enumerate(solution, 1):
                    steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
            else:
                steps.append(f"✅ Solución encontrada (método alternativo): $$latex({latex(solution)})$$")
            solution = normalize_and_simplify_solution(solution)
            return solution
        except Exception as e2:
            error_msg = str(e) if 'e' in locals() else str(e2)
            steps.append(f"❌ Error al resolver con método específico: {error_msg}")
            steps.append(f"⚠️ Intentando método alternativo...")
            try:
                solution = dsolve(eq, y)
                if isinstance(solution, list):
                    steps.append(f"✅ Solución encontrada (método general) - múltiples soluciones:")
                    for i, sol in enumerate(solution, 1):
                        steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                else:
                    steps.append(f"✅ Solución encontrada (método general): $$latex({latex(solution)})$$")
                solution = normalize_and_simplify_solution(solution)
                return solution
            except Exception as e3:
                steps.append(f"❌ Error final: {str(e3)}")
                import traceback
                steps.append(f"📄 Traceback: {traceback.format_exc()[:200]}")
                return None

def solve_integrating_factor(eq, steps):
    """Resuelve usando factores integrantes"""
    x = symbols('x')
    y = Function('y')(x)
    
    steps.append("**Método de Factor Integrante**")
    steps.append(f"Ecuación original: $$latex({latex(eq)})$$")
    
    try:
        solution = dsolve(eq, y, hint='1st_linear')
        if isinstance(solution, list):
            steps.append(f"✅ Solución encontrada (múltiples soluciones):")
            for i, sol in enumerate(solution, 1):
                steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
        else:
            steps.append(f"✅ Solución encontrada: $$latex({latex(solution)})$$")
        
        solution = normalize_and_simplify_solution(solution)
        return solution
    except Exception as e:
        try:
            solution = dsolve(eq, y)
            if isinstance(solution, list):
                steps.append(f"✅ Solución encontrada (método alternativo) - múltiples soluciones:")
                for i, sol in enumerate(solution, 1):
                    steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
            else:
                steps.append(f"✅ Solución encontrada (método alternativo): $$latex({latex(solution)})$$")
            solution = normalize_and_simplify_solution(solution)
            return solution
        except Exception as e2:
            error_msg = str(e) if 'e' in locals() else str(e2)
            steps.append(f"❌ Error al resolver con método específico: {error_msg}")
            steps.append(f"⚠️ Intentando método alternativo...")
            try:
                solution = dsolve(eq, y)
                if isinstance(solution, list):
                    steps.append(f"✅ Solución encontrada (método general) - múltiples soluciones:")
                    for i, sol in enumerate(solution, 1):
                        steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                else:
                    steps.append(f"✅ Solución encontrada (método general): $$latex({latex(solution)})$$")
                solution = normalize_and_simplify_solution(solution)
                return solution
            except Exception as e3:
                steps.append(f"❌ Error final: {str(e3)}")
                import traceback
                steps.append(f"📄 Traceback: {traceback.format_exc()[:200]}")
                return None

def parse_initial_conditions(conditions_str, steps):
    """
    Parsea condiciones iniciales desde un string.
    Retorna una lista de tuplas (x_val, y_val, deriv_order)
    y un diccionario de constantes {C: valor, ...}
    """
    if not conditions_str or not conditions_str.strip():
        return [], {}
    
    x = symbols('x')
    y_func = Function('y')
    conditions = []
    constant_values = {}
    
    # Normalizar el string
    conditions_str = conditions_str.strip()
    
    # Dividir por comas
    parts = [p.strip() for p in conditions_str.split(',')]
    
    for part in parts:
        if not part:
            continue
        
        try:
            # Intentar parsear como y(a)=b o y'(a)=b, etc.
            # Patrones: y(0)=3, y'(2)=5, y''(1)=0, C=5, etc.
            
            # Patrón para constantes: C=5, c=3, etc.
            const_match = re.match(r'^([A-Za-z][A-Za-z0-9_]*)\s*=\s*(.+)$', part)
            if const_match:
                const_name = const_match.group(1)
                const_value_str = const_match.group(2).strip()
                try:
                    # Intentar evaluar el valor
                    local_dict = {
                        'x': x,
                        'exp': exp,
                        'log': log,
                        'sin': sin,
                        'cos': cos,
                        'tan': tan,
                        'sqrt': sqrt,
                        'pi': sympy_pi,
                        'E': exp(1),
                        'e': exp(1)
                    }
                    const_value = sympy_parse_expr(const_value_str, local_dict=local_dict, transformations=transformations)
                    constant_values[const_name] = const_value
                    steps.append(f"   📌 Condición detectada: ${const_name} = {latex(const_value)}$")
                except:
                    try:
                        const_value = float(const_value_str)
                        constant_values[const_name] = const_value
                        steps.append(f"   📌 Condición detectada: ${const_name} = {const_value}$")
                    except:
                        steps.append(f"   ⚠️ No se pudo parsear la constante: {part}")
                continue
            
            # Patrón para y(a)=b, y'(a)=b, y''(a)=b, etc.
            # y(0)=3, y'(2)=5, y''(1)=0
            pattern = r"y('*)\(([^)]+)\)\s*=\s*(.+)$"
            match = re.match(pattern, part)
            
            if match:
                primes = match.group(1)
                x_val_str = match.group(2).strip()
                y_val_str = match.group(3).strip()
                
                deriv_order = len(primes)
                
                # Parsear x_val
                try:
                    local_dict = {
                        'x': x,
                        'exp': exp,
                        'log': log,
                        'sin': sin,
                        'cos': cos,
                        'tan': tan,
                        'sqrt': sqrt,
                        'pi': sympy_pi,
                        'E': exp(1),
                        'e': exp(1)
                    }
                    x_val = sympy_parse_expr(x_val_str, local_dict=local_dict, transformations=transformations)
                except:
                    try:
                        x_val = float(x_val_str)
                    except:
                        steps.append(f"   ⚠️ No se pudo parsear x en: {part}")
                        continue
                
                # Parsear y_val
                try:
                    local_dict = {
                        'x': x,
                        'exp': exp,
                        'log': log,
                        'sin': sin,
                        'cos': cos,
                        'tan': tan,
                        'sqrt': sqrt,
                        'pi': sympy_pi,
                        'E': exp(1),
                        'e': exp(1)
                    }
                    y_val = sympy_parse_expr(y_val_str, local_dict=local_dict, transformations=transformations)
                except:
                    try:
                        y_val = float(y_val_str)
                    except:
                        steps.append(f"   ⚠️ No se pudo parsear y en: {part}")
                        continue
                
                conditions.append((x_val, y_val, deriv_order))
                
                deriv_str = "y" + "'" * deriv_order
                steps.append(f"   📌 Condición inicial detectada: ${deriv_str}({latex(x_val)}) = {latex(y_val)}$")
            else:
                steps.append(f"   ⚠️ Formato no reconocido: {part}")
        except Exception as e:
            steps.append(f"   ⚠️ Error al parsear condición '{part}': {str(e)}")
    
    return conditions, constant_values

def apply_initial_conditions(solution, conditions, constant_values, steps):
    """
    Aplica condiciones iniciales a la solución para encontrar constantes.
    Retorna la solución particular.
    """
    if not solution:
        return None
    
    x = symbols('x')
    y_func = Function('y')
    
    # Si hay múltiples soluciones, trabajar con la primera (o todas si es necesario)
    if isinstance(solution, list):
        if len(solution) == 0:
            return None
        # Por ahora, trabajar con la primera solución
        solution = solution[0]
    
    try:
        # Extraer todas las constantes de la solución
        all_constants = []
        for symbol in solution.free_symbols:
            s_str = str(symbol)
            if s_str not in ['x', 'y'] and not s_str.startswith('_') and isinstance(symbol, Symbol):
                all_constants.append(symbol)
        
        if not all_constants:
            steps.append(f"   ℹ️ La solución no contiene constantes de integración.")
            return solution
        
        # Si hay valores de constantes directos, aplicarlos primero
        if constant_values:
            steps.append(f"")
            steps.append(f"🔧 **Aplicando valores de constantes:**")
            for const_name, const_value in constant_values.items():
                # Buscar el símbolo correspondiente
                const_symbol = None
                for c in all_constants:
                    if str(c) == const_name:
                        const_symbol = c
                        break
                
                if const_symbol:
                    solution = solution.subs(const_symbol, const_value)
                    steps.append(f"   Sustituyendo ${latex(const_symbol)} = {latex(const_value)}$")
                    steps.append(f"   Solución actualizada: $$latex({latex(solution)})$$")
                    # Remover de la lista de constantes
                    all_constants = [c for c in all_constants if c != const_symbol]
                else:
                    steps.append(f"   ⚠️ No se encontró la constante ${const_name}$ en la solución")
        
        # Si no hay condiciones iniciales, retornar la solución general
        if not conditions:
            return solution
        
        steps.append(f"")
        steps.append(f"🔧 **Aplicando condiciones iniciales para encontrar constantes:**")
        
        # Crear sistema de ecuaciones a partir de las condiciones
        equations = []
        
        for x_val, y_val, deriv_order in conditions:
            # Calcular la derivada correspondiente
            if deriv_order == 0:
                # y(x_val) = y_val
                expr = solution.subs(x, x_val) - y_val
            else:
                # Calcular la derivada n-ésima
                deriv_expr = diff(solution, x, deriv_order)
                expr = deriv_expr.subs(x, x_val) - y_val
            
            equations.append(Eq(expr, 0))
            
            deriv_str = "y" + "'" * deriv_order
            steps.append(f"   Condición: ${deriv_str}({latex(x_val)}) = {latex(y_val)}$")
            steps.append(f"   Ecuación resultante: $$latex({latex(equations[-1])})$$")
        
        # Resolver el sistema de ecuaciones
        if equations and all_constants:
            steps.append(f"")
            steps.append(f"🔍 **Resolviendo el sistema de ecuaciones para las constantes:**")
            
            try:
                # Intentar resolver el sistema
                solutions_dict = sympy_solve(equations, all_constants, dict=True)
                
                if solutions_dict:
                    # Tomar la primera solución (puede haber múltiples)
                    sol_dict = solutions_dict[0]
                    
                    steps.append(f"   Soluciones encontradas para las constantes:")
                    for const, value in sol_dict.items():
                        steps.append(f"   ${latex(const)} = {latex(value)}$")
                    
                    # Aplicar las constantes a la solución
                    particular_solution = solution.subs(sol_dict)
                    particular_solution = simplify(particular_solution)
                    
                    steps.append(f"")
                    steps.append(f"✅ **Solución particular obtenida:**")
                    steps.append(f"   $$latex({latex(particular_solution)})$$")
                    
                    return particular_solution
                else:
                    steps.append(f"   ⚠️ No se encontró solución para el sistema de ecuaciones")
                    steps.append(f"   Se mostrará la solución general con las constantes sin determinar")
                    return solution
            except Exception as solve_error:
                steps.append(f"   ⚠️ Error al resolver el sistema: {str(solve_error)}")
                steps.append(f"   Se mostrará la solución general")
                return solution
        else:
            return solution
            
    except Exception as e:
        steps.append(f"   ⚠️ Error al aplicar condiciones iniciales: {str(e)}")
        import traceback
        steps.append(f"   📄 Detalles: {traceback.format_exc()[:200]}")
        return solution

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/solve', methods=['POST'])
@ensure_json_response
def solve():
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'solution': None,
                'steps': ['❌ Error: No se recibieron datos en la petición']
            }), 400
        
        equation_str = data.get('equation', '')
        method = data.get('method', 'auto')
        initial_conditions_str = data.get('initial_conditions', '')
        
        steps = []
        solution = None
        general_solution = None
        particular_solution = None
    except Exception as e:
        return jsonify({
            'success': False,
            'solution': None,
            'steps': [f'❌ Error al procesar la petición: {str(e)}']
        }), 400
    
    try:
        x = symbols('x')
        y = Function('y')(x)
        
        # Parsear la ecuación
        steps.append(f"📋 **Paso 1: Ecuación ingresada**")
        steps.append(f"   Ecuación original: `{equation_str}`")
        
        try:
            eq = parse_equation_string(equation_str)
            steps.append(f"📝 **Paso 2: Ecuación parseada**")
            steps.append(f"   La ecuación en formato matemático es: $$latex({latex(eq)})$$")
            
            # Mostrar forma estándar de la ecuación
            try:
                # Intentar reorganizar a forma estándar: y' = f(x,y)
                from sympy import collect, expand
                eq_lhs = eq.lhs
                eq_rhs = eq.rhs
                
                # Si el lado izquierdo es una derivada, mostrar forma estándar
                if eq_lhs.has(diff):
                    steps.append(f"📐 **Forma estándar:**")
                    steps.append(f"   $$latex({latex(eq)})$$")
                    
                    # Mostrar información sobre el tipo de ecuación
                    order = 0
                    if eq.has(diff(Function('y')(symbols('x')), symbols('x'))):
                        order = 1
                    elif eq.has(diff(Function('y')(symbols('x')), symbols('x'), 2)):
                        order = 2
                    elif eq.has(diff(Function('y')(symbols('x')), symbols('x'), 3)):
                        order = 3
                    
                    if order > 0:
                        steps.append(f"   Esta es una ecuación diferencial de orden {order}.")
            except:
                pass
                
        except Exception as parse_error:
            steps.append(f"❌ Error al parsear la ecuación: {str(parse_error)}")
            return jsonify({
                'success': False,
                'solution': None,
                'steps': steps
            })
        
        # Seleccionar método de solución
        if method == 'auto':
            # Intentar clasificar automáticamente y probar múltiples métodos
            steps.append(f"🔍 **Paso 3: Clasificación automática de la ecuación**")
            try:
                hints = classify_ode(eq, y)
                if hints:
                    steps.append(f"   Se detectaron los siguientes métodos aplicables:")
                    for i, hint in enumerate(hints[:5], 1):
                        # Traducir nombres de métodos a español
                        method_names = {
                            'separable': 'Variables Separables',
                            '1st_linear': 'Lineal de Primer Orden',
                            '1st_exact': 'Exacta',
                            'homogeneous': 'Homogénea',
                            'Bernoulli': 'Bernoulli',
                            '1st_power_series': 'Serie de Potencias',
                            'nth_linear_constant_coeff_homogeneous': 'Lineal con Coeficientes Constantes (Homogénea)',
                            '1st_rational_riccati': 'Riccati Racional',
                            '1st_homogeneous_coeff_best': 'Homogénea (mejor método)',
                            '1st_homogeneous_coeff_subs_indep_div_dep': 'Homogénea (sustitución)',
                            '1st_homogeneous_coeff_subs_dep_div_indep': 'Homogénea (sustitución alterna)',
                        }
                        method_name = method_names.get(hint, hint)
                        steps.append(f"   {i}. {method_name} ({hint})")
                    
                    # Intentar con cada hint hasta que uno funcione
                    solution = None
                    successful_hint = None
                    for hint_idx, hint in enumerate(hints[:5], 1):  # Probar hasta 5 métodos
                        try:
                            steps.append(f"")
                            steps.append(f"🔄 **Paso 3.{hint_idx}: Intentando resolver con método '{hint}'**")
                            
                            solution = dsolve(eq, y, hint=hint)
                            
                            successful_hint = hint
                            method_names = {
                                'separable': 'Variables Separables',
                                '1st_linear': 'Lineal de Primer Orden',
                                '1st_exact': 'Exacta',
                                'homogeneous': 'Homogénea',
                                'Bernoulli': 'Bernoulli',
                            }
                            method_name = method_names.get(hint, hint)
                            
                            if isinstance(solution, list):
                                steps.append(f"✅ ¡Éxito! Solución encontrada usando método '{method_name}' (múltiples soluciones):")
                                for i, sol in enumerate(solution, 1):
                                    steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                            else:
                                steps.append(f"✅ ¡Éxito! Solución encontrada usando método '{method_name}':")
                                steps.append(f"   $$latex({latex(solution)})$$")
                            
                            solution = normalize_and_simplify_solution(solution)
                            break  # Si funciona, salir del loop
                        except Exception as hint_error:
                            method_names = {
                                'separable': 'Variables Separables',
                                '1st_linear': 'Lineal de Primer Orden',
                                '1st_exact': 'Exacta',
                                'homogeneous': 'Homogénea',
                                'Bernoulli': 'Bernoulli',
                            }
                            method_name = method_names.get(hint, hint)
                            steps.append(f"⚠️ El método '{method_name}' no es aplicable o falló.")
                            if hint_idx < min(5, len(hints)):
                                steps.append(f"   Probando siguiente método...")
                            continue
                    
                    # Si ningún hint funcionó, intentar sin hint
                    if solution is None:
                        steps.append(f"")
                        steps.append(f"🔄 **Paso 3.6: Intentando resolución general (sin método específico)**")
                        steps.append(f"   Como los métodos específicos no funcionaron, se intenta un método general...")
                        solution = dsolve(eq, y)
                        if isinstance(solution, list):
                            steps.append(f"✅ Solución encontrada (múltiples soluciones):")
                            for i, sol in enumerate(solution, 1):
                                steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                        else:
                            steps.append(f"✅ Solución encontrada:")
                            steps.append(f"   $$latex({latex(solution)})$$")
                        solution = normalize_and_simplify_solution(solution)
                else:
                    steps.append(f"   No se pudieron detectar métodos específicos para esta ecuación.")
                    steps.append(f"🔄 **Paso 3.1: Intentando resolución directa...**")
                    steps.append(f"   Se intentará resolver directamente sin restricciones de método...")
                    solution = dsolve(eq, y)
                    if isinstance(solution, list):
                        steps.append(f"✅ Solución encontrada (múltiples soluciones):")
                        for i, sol in enumerate(solution, 1):
                            steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                    else:
                        steps.append(f"✅ Solución encontrada:")
                        steps.append(f"   $$latex({latex(solution)})$$")
                    solution = normalize_and_simplify_solution(solution)
            except Exception as e:
                steps.append(f"⚠️ Error en clasificación: {str(e)[:100]}")
                steps.append(f"🔄 Intentando resolución directa...")
                try:
                    solution = dsolve(eq, y)
                    if isinstance(solution, list):
                        steps.append(f"✅ Solución encontrada (múltiples soluciones):")
                        for i, sol in enumerate(solution, 1):
                            steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                    else:
                        steps.append(f"✅ Solución encontrada: $$latex({latex(solution)})$$")
                except Exception as e2:
                    steps.append(f"❌ Error al resolver: {str(e2)}")
                    solution = None
        else:
            # Usar método específico
            method_functions = {
                'separable': solve_separable,
                'homogeneous': solve_homogeneous,
                'exact': solve_exact,
                'linear': solve_linear,
                'bernoulli': solve_bernoulli,
                'reducible': solve_reducible_first_order,
                'constant_coeff': solve_constant_coefficients,
                'undetermined': solve_undetermined_coefficients,
                'integrating_factor': solve_integrating_factor
            }
            
            if method in method_functions:
                solution = method_functions[method](eq, steps)
                # Si el método específico falló, intentar automático
                if solution is None and method != 'auto':
                    steps.append(f"⚠️ El método '{method}' no funcionó, intentando auto-detección...")
                    try:
                        hints = classify_ode(eq, y)
                        if hints:
                            steps.append(f"🔍 Métodos disponibles: {', '.join(hints[:5])}")
                            # Intentar con cada hint hasta que uno funcione
                            solution = None
                            for hint in hints[:5]:
                                try:
                                    steps.append(f"🔄 Intentando método: '{hint}'...")
                                    solution = dsolve(eq, y, hint=hint)
                                    if isinstance(solution, list):
                                        steps.append(f"✅ Solución encontrada usando '{hint}' (auto-detectado):")
                                        for i, sol in enumerate(solution, 1):
                                            steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                                    else:
                                        steps.append(f"✅ Solución encontrada usando '{hint}' (auto-detectado): $$latex({latex(solution)})$$")
                                    solution = normalize_and_simplify_solution(solution)
                                    break
                                except Exception:
                                    continue
                            
                            # Si ningún hint funcionó, intentar sin hint
                            if solution is None:
                                solution = dsolve(eq, y)
                                if isinstance(solution, list):
                                    steps.append(f"✅ Solución encontrada (múltiples soluciones):")
                                    for i, sol in enumerate(solution, 1):
                                        steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                                else:
                                    steps.append(f"✅ Solución encontrada: $$latex({latex(solution)})$$")
                                solution = normalize_and_simplify_solution(solution)
                        else:
                            solution = dsolve(eq, y)
                            if isinstance(solution, list):
                                steps.append(f"✅ Solución encontrada (múltiples soluciones):")
                                for i, sol in enumerate(solution, 1):
                                    steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                            else:
                                steps.append(f"✅ Solución encontrada: $$latex({latex(solution)})$$")
                            solution = normalize_and_simplify_solution(solution)
                    except Exception as auto_error:
                        steps.append(f"❌ Error en auto-detección: {str(auto_error)}")
            else:
                try:
                    solution = dsolve(eq, y)
                    if isinstance(solution, list):
                        steps.append(f"✅ Solución encontrada (múltiples soluciones):")
                        for i, sol in enumerate(solution, 1):
                            steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                    else:
                        steps.append(f"✅ Solución encontrada: $$latex({latex(solution)})$$")
                except Exception as e:
                    steps.append(f"❌ Error: {str(e)}")
                    solution = None
        
        if solution is not None:
            # Guardar solución general
            general_solution = solution
            
            # Normalizar y simplificar la solución (puede ser lista o expresión única)
            steps.append(f"")
            steps.append(f"🔧 **Paso 4: Simplificación de la solución general**")
            try:
                original_solution = solution
                solution = normalize_and_simplify_solution(solution)
                general_solution = solution
                
                # Si cambió, agregar paso de simplificación
                # Comparar usando representación en string para evitar problemas con listas
                try:
                    if str(solution) != str(original_solution):
                        steps.append(f"   Simplificando la solución encontrada...")
                        if isinstance(solution, list):
                            steps.append(f"   Solución simplificada (múltiples soluciones):")
                            for i, sol in enumerate(solution, 1):
                                steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                        else:
                            steps.append(f"   Solución simplificada:")
                            steps.append(f"   $$latex({latex(solution)})$$")
                    else:
                        steps.append(f"   La solución ya está en su forma más simple.")
                        if isinstance(solution, list):
                            for i, sol in enumerate(solution, 1):
                                steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                        else:
                            steps.append(f"   $$latex({latex(solution)})$$")
                except:
                    # Si la comparación falla, mostrar la solución actual
                    steps.append(f"   Solución general:")
                    if isinstance(solution, list):
                        for i, sol in enumerate(solution, 1):
                            steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                    else:
                        steps.append(f"   $$latex({latex(solution)})$$")
            except Exception as simplify_error:
                steps.append(f"⚠️ Advertencia: Error al simplificar solución: {str(simplify_error)}")
                steps.append(f"   Se mostrará la solución sin simplificar.")
                # Continuar con la solución original
            
            # Procesar condiciones iniciales si se proporcionaron
            if initial_conditions_str:
                steps.append(f"")
                steps.append(f"📋 **Paso 5: Procesando condiciones iniciales**")
                steps.append(f"   Condiciones ingresadas: `{initial_conditions_str}`")
                
                conditions, constant_values = parse_initial_conditions(initial_conditions_str, steps)
                
                if conditions or constant_values:
                    # Aplicar condiciones iniciales
                    particular_solution = apply_initial_conditions(general_solution, conditions, constant_values, steps)
                    
                    if particular_solution and particular_solution != general_solution:
                        solution = particular_solution  # Usar solución particular para mostrar
                else:
                    steps.append(f"   ⚠️ No se detectaron condiciones iniciales válidas.")
                    steps.append(f"   Se mostrará únicamente la solución general.")
        else:
            # Si no hay solución, agregar mensaje informativo
            if not any("❌" in step for step in steps):
                steps.append("❌ No se pudo encontrar una solución para esta ecuación.")
        
    except Exception as e:
        steps.append(f"❌ Error general al procesar: {str(e)}")
        import traceback
        steps.append(f"📄 Detalles técnicos: {traceback.format_exc()[:500]}")
    
    # Convertir solución a LaTeX, manejando listas
    solution_latex = None
    general_solution_latex = None
    particular_solution_latex = None
    
    try:
        if solution is not None:
            # Mostrar solución particular si existe, sino la general
            display_solution = particular_solution if (particular_solution and particular_solution != general_solution) else solution
            
            if isinstance(display_solution, list):
                # Si hay múltiples soluciones, formatearlas juntas
                solution_latex = '\\begin{cases} ' + ' \\\\ '.join([latex(sol) for sol in display_solution]) + ' \\end{cases}'
            else:
                solution_latex = latex(display_solution)
            
            # También preparar LaTeX para solución general y particular si existen
            if general_solution:
                if isinstance(general_solution, list):
                    general_solution_latex = '\\begin{cases} ' + ' \\\\ '.join([latex(sol) for sol in general_solution]) + ' \\end{cases}'
                else:
                    general_solution_latex = latex(general_solution)
            
            if particular_solution and particular_solution != general_solution:
                if isinstance(particular_solution, list):
                    particular_solution_latex = '\\begin{cases} ' + ' \\\\ '.join([latex(sol) for sol in particular_solution]) + ' \\end{cases}'
                else:
                    particular_solution_latex = latex(particular_solution)
            
            # Agregar información sobre constantes de integración y resumen
            steps.append(f"")
            steps.append(f"📌 **Paso 6: Resumen final**")
            
            # Mostrar solución general si hay solución particular
            if particular_solution and particular_solution != general_solution:
                steps.append(f"")
                steps.append(f"📊 **Solución General:**")
                if isinstance(general_solution, list):
                    for i, sol in enumerate(general_solution, 1):
                        steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                else:
                    steps.append(f"   $$latex({latex(general_solution)})$$")
                
                steps.append(f"")
                steps.append(f"📊 **Solución Particular (con condiciones iniciales aplicadas):**")
                if isinstance(particular_solution, list):
                    for i, sol in enumerate(particular_solution, 1):
                        steps.append(f"   Solución {i}: $$latex({latex(sol)})$$")
                else:
                    steps.append(f"   $$latex({latex(particular_solution)})$$")
            else:
                # Detectar constantes de integración en la solución general
                from sympy import Symbol as SympySymbol, Wild
                constants = []
                sol_to_check = general_solution if general_solution else solution
                if isinstance(sol_to_check, list):
                    for sol in sol_to_check:
                        # Buscar todos los símbolos que no sean x ni y
                        for s in sol.free_symbols:
                            s_str = str(s)
                            if s_str not in ['x', 'y'] and not s_str.startswith('_') and isinstance(s, SympySymbol):
                                # Filtrar símbolos que parecen constantes de integración
                                if any(s_str.startswith(prefix) for prefix in ['C', 'c', 'K', 'k', 'A', 'a', 'B', 'b']):
                                    constants.append(s_str)
                else:
                    for s in sol_to_check.free_symbols:
                        s_str = str(s)
                        if s_str not in ['x', 'y'] and not s_str.startswith('_') and isinstance(s, SympySymbol):
                            if any(s_str.startswith(prefix) for prefix in ['C', 'c', 'K', 'k', 'A', 'a', 'B', 'b']):
                                constants.append(s_str)
                
                if constants:
                    unique_constants = sorted(set(constants))
                    if len(unique_constants) == 1:
                        steps.append(f"   La solución contiene la constante de integración: ${unique_constants[0]}$")
                        steps.append(f"   Esta constante puede tomar cualquier valor real.")
                        steps.append(f"   Para obtener una solución particular, proporcione una condición inicial (ej: y(0)=3).")
                    else:
                        steps.append(f"   La solución contiene las siguientes constantes de integración: {', '.join([f'${c}$' for c in unique_constants])}")
                        steps.append(f"   Estas constantes pueden tomar cualquier valor real.")
                        steps.append(f"   Para obtener una solución particular, proporcione condiciones iniciales (ej: y(0)=3, y'(0)=1).")
                else:
                    # Intentar detectar si hay símbolos que puedan ser constantes
                    all_symbols = set()
                    if isinstance(sol_to_check, list):
                        for sol in sol_to_check:
                            all_symbols.update([str(s) for s in sol.free_symbols if str(s) not in ['x', 'y']])
                    else:
                        all_symbols = set([str(s) for s in sol_to_check.free_symbols if str(s) not in ['x', 'y']])
                    
                    if all_symbols:
                        steps.append(f"   Nota: La solución puede depender de valores iniciales o condiciones de contorno.")
            
            steps.append(f"")
            steps.append(f"✅ **Resumen:** La ecuación diferencial ha sido resuelta exitosamente.")
            
    except Exception as latex_error:
        steps.append(f"⚠️ Advertencia: Error al convertir solución a LaTeX: {str(latex_error)}")
        if solution is not None:
            try:
                solution_latex = str(solution)
            except:
                solution_latex = "Solución encontrada pero no se pudo formatear"
    
    return jsonify({
        'success': solution is not None,
        'solution': solution_latex,
        'general_solution': general_solution_latex,
        'particular_solution': particular_solution_latex,
        'steps': steps
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
