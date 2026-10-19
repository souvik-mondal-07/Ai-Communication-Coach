"""
Safe arithmetic evaluator used to *independently* re-check numeric answer keys.

Question content stores a textbook formula as a string (e.g. ``"1200*(1+10/100)**2"``). This
module evaluates it by walking the parsed syntax tree and allowing only numbers, arithmetic
operators and a short whitelist of math functions. It never calls ``eval``/``exec`` and it
bounds exponents and factorials so a malformed or hostile expression cannot hang the server.
"""

from __future__ import annotations

import ast
import math
import operator
import re
from fractions import Fraction

MAX_EXPRESSION_LENGTH = 300
MAX_EXPONENT = 400
MAX_FACTORIAL = 200
MAX_ABS_VALUE = 10**60


class UnsafeExpressionError(ValueError):
    """The expression is malformed, too large, or uses something outside the whitelist."""


_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _bounded_factorial(n):
    if not isinstance(n, int) or n < 0 or n > MAX_FACTORIAL:
        raise UnsafeExpressionError("factorial argument out of range")
    return math.factorial(n)


def _bounded_comb(n, k):
    if not (isinstance(n, int) and isinstance(k, int)) or n < 0 or k < 0 or n > 2000:
        raise UnsafeExpressionError("comb arguments out of range")
    return math.comb(n, k)


def _bounded_perm(n, k):
    if not (isinstance(n, int) and isinstance(k, int)) or n < 0 or k < 0 or n > 500:
        raise UnsafeExpressionError("perm arguments out of range")
    return math.perm(n, k)


def _lcm(a, b):
    return math.lcm(int(a), int(b))


_FUNCTIONS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "gcd": math.gcd,
    "lcm": _lcm,
    "factorial": _bounded_factorial,
    "comb": _bounded_comb,
    "perm": _bounded_perm,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "radians": math.radians,
    "frac": Fraction,
}
_CONSTANTS = {"pi": math.pi}


def _check_size(value):
    if isinstance(value, (int, float, Fraction)) and abs(value) > MAX_ABS_VALUE:
        raise UnsafeExpressionError("value too large")
    return value


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise UnsafeExpressionError("only numeric literals are allowed")
        return node.value
    if isinstance(node, ast.Name):
        if node.id in _CONSTANTS:
            return _CONSTANTS[node.id]
        raise UnsafeExpressionError(f"unknown name '{node.id}'")
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow):
            if abs(right) > MAX_EXPONENT:
                raise UnsafeExpressionError("exponent too large")
            if isinstance(left, (int, Fraction)) and abs(left) > 10**6 and abs(right) > 8:
                raise UnsafeExpressionError("power too large")
        try:
            return _check_size(_BIN_OPS[type(node.op)](left, right))
        except ZeroDivisionError as exc:
            raise UnsafeExpressionError("division by zero") from exc
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS or node.keywords:
            raise UnsafeExpressionError("function not allowed")
        if len(node.args) > 4:
            raise UnsafeExpressionError("too many arguments")
        try:
            return _check_size(_FUNCTIONS[node.func.id](*[_eval(a) for a in node.args]))
        except UnsafeExpressionError:
            raise
        except (ValueError, TypeError, OverflowError) as exc:
            raise UnsafeExpressionError(f"bad call: {exc}") from exc
    raise UnsafeExpressionError(f"unsupported syntax: {type(node).__name__}")


def safe_eval(expression: str) -> float:
    """Evaluate a whitelisted arithmetic expression and return a float."""
    if not isinstance(expression, str) or not expression.strip():
        raise UnsafeExpressionError("empty expression")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise UnsafeExpressionError("expression too long")
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpressionError("syntax error") from exc
    return float(_eval(tree))


_MIXED = re.compile(r"(-?\d[\d,]*)\s+(\d+)\s*/\s*(\d+)")
_FRACTION = re.compile(r"(-?\d[\d,]*)\s*/\s*(\d+)")
_NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def parse_number(text: str) -> float | None:
    """
    First numeric value in an option such as ``"₹1,200"``, ``"16.67%"``, ``"3/8"`` or
    ``"7 1/5 days"``. Returns None when the option contains no number.
    """
    if not isinstance(text, str):
        return None
    mixed = _MIXED.search(text)
    if mixed:
        whole, num, den = mixed.groups()
        w = float(whole.replace(",", ""))
        frac = int(num) / int(den) if int(den) else 0.0
        return w + frac if w >= 0 else w - frac
    fraction = _FRACTION.search(text)
    if fraction:
        num, den = fraction.groups()
        return float(num.replace(",", "")) / int(den) if int(den) else None
    number = _NUMBER.search(text)
    return float(number.group().replace(",", "")) if number else None
