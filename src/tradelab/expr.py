"""Formulas from strategy rules, evaluated without eval().

A formula is parsed to a syntax tree and walked by hand. Only numbers, known names, arithmetic,
comparisons, and/or/not, `group.field` and the functions below exist. Anything else is an error.
"""

import ast
import operator
from collections.abc import Mapping
from functools import reduce
from typing import Any

import numpy as np
import pandas as pd

MAX_LENGTH = 500


class ExprError(ValueError):
    pass


class Namespace(dict):
    """A group of series reached with a dot in formulas: first.high, macd.hist."""


def prev(x, n=1):
    return x.shift(int(n)) if isinstance(x, pd.Series) else x


def highest(x, n):
    return x.rolling(int(n)).max()


def lowest(x, n):
    return x.rolling(int(n)).min()


def crossover(a, b):
    return (a > b) & (prev(a) <= prev(b))


def crossunder(a, b):
    return (a < b) & (prev(a) >= prev(b))


FUNCTIONS = {
    "prev": prev, "highest": highest, "lowest": lowest,
    "crossover": crossover, "crossunder": crossunder,
    "abs": abs,
    "min": lambda *xs: reduce(np.minimum, xs),
    "max": lambda *xs: reduce(np.maximum, xs),
}

_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
_COMPARE = {ast.Gt: operator.gt, ast.GtE: operator.ge, ast.Lt: operator.lt, ast.LtE: operator.le,
            ast.Eq: operator.eq, ast.NotEq: operator.ne}


def _parse(expr: str) -> ast.Expression:
    if not isinstance(expr, str) or not expr.strip() or len(expr) > MAX_LENGTH:
        raise ExprError(f"Empty or too long formula: {expr}")
    try:
        return ast.parse(expr.strip(), mode="eval")
    except (SyntaxError, ValueError, RecursionError):
        raise ExprError(f"Cannot read formula: {expr}") from None


def refs_in(expr: str) -> set[str]:
    """What a formula reads, with the field after a dot: {"close", "first.high"}. No function names."""
    nodes = list(ast.walk(_parse(expr)))
    refs, not_a_value = set(), set()
    for node in nodes:
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            refs.add(f"{node.value.id}.{node.attr}")
            not_a_value.add(id(node.value))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            not_a_value.add(id(node.func))
    return refs | {n.id for n in nodes if isinstance(n, ast.Name) and id(n) not in not_a_value}


def names_in(expr: str) -> set[str]:
    """The names a formula uses, without function names and without the field after a dot."""
    return {ref.split(".")[0] for ref in refs_in(expr)}


def evaluate(expr: str, env: Mapping[str, Any]) -> Any:
    tree = _parse(expr)
    try:
        return _walk(tree.body, env)
    except ExprError as error:
        raise ExprError(f"{error} in formula: {expr}") from None
    except (TypeError, ValueError, ZeroDivisionError, RecursionError, AttributeError) as error:
        raise ExprError(f"Cannot calculate ({type(error).__name__}) formula: {expr}") from None


def _truth(x):
    return x.fillna(False).astype(bool) if isinstance(x, pd.Series) else bool(x)


def _walk(node: ast.AST, env: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise ExprError(f"Unknown name '{node.id}'")
        return env[node.id]
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        group = env.get(node.value.id)
        if not isinstance(group, Namespace) or node.attr not in group:
            raise ExprError(f"Unknown name '{node.value.id}.{node.attr}'")
        return group[node.attr]
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        return _BINARY[type(node.op)](_walk(node.left, env), _walk(node.right, env))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_walk(node.operand, env)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        value = _truth(_walk(node.operand, env))
        return ~value if isinstance(value, pd.Series) else not value
    if isinstance(node, ast.BoolOp):
        combine = operator.and_ if isinstance(node.op, ast.And) else operator.or_
        return reduce(combine, (_truth(_walk(v, env)) for v in node.values))
    if isinstance(node, ast.Compare) and all(type(op) in _COMPARE for op in node.ops):
        values = [_walk(v, env) for v in (node.left, *node.comparators)]
        parts = [_COMPARE[type(op)](a, b) for op, a, b in zip(node.ops, values, values[1:])]
        return reduce(operator.and_, parts)
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id in FUNCTIONS and not node.keywords):
        return FUNCTIONS[node.func.id](*(_walk(arg, env) for arg in node.args))
    raise ExprError(f"'{type(node).__name__}' is not allowed")
