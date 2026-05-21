"""
Recipix Part 2 interpreter.

Owner:   Berk Hakan Öge (210104004132)
Plan:    Implements plan §2.2, §2.4 (interpreter normalizes ``QuantityLit``
         to base unit at evaluation), §2.5 (environment chain), §2.6
         (``serves`` evaluated once at recipe instantiation; ``scale``
         servings uses ``int(round(servings * by))``), §4 (Berk's task list).

The interpreter walks the AST produced by ``recipix.parser`` (and
optionally annotated by ``recipix.typechecker``) and produces a list of
rendered strings — one per ``evaluate`` statement.

Runtime errors (spec §10):

  R1  division by zero
  R2  negative repeat count
  R3  ``scale`` ``by`` <= 0
  R4  ``substitute`` of an unknown ingredient
  R5  (reserved — division-by-zero already covered by R1)

Step-body action arguments are stored as one of:

  ("ingredient_ref", name)   — bare Identifier resolving to RtIngredient
  ("value", value)            — any other evaluated value

The renderer resolves ``ingredient_ref`` against the current recipe's
ingredient dict, so ``scale`` and ``substitute`` only need to rebuild
that dict — they do not have to walk step bodies.
"""

from __future__ import annotations

from . import ast_nodes as ast
from .ast_nodes import Program
from .environment import Environment
from .errors import RuntimeRecipixError
from .runtime_values import (
    RtIngredient,
    RtList,
    RtPinch,
    RtQuantity,
    RtRecipe,
    PINCH,
    normalize_to_base,
)


def run(program: Program, *, render_output: bool = True) -> list[str]:
    return Interpreter().run(program, render_output=render_output)


class Interpreter:
    class ReturnException(Exception):
        __slots__ = ("value",)

        def __init__(self, value):
            self.value = value
            super().__init__()

    def __init__(self) -> None:
        self.globals: Environment = Environment()
        self.outputs: list[str] = []

    # -- top-level ----------------------------------------------------------

    def run(self, program: Program, *, render_output: bool = True) -> list[str]:
        from . import rendering  # local import to avoid cycles
        self._render_output = render_output
        self._render_recipe = rendering.render_recipe

        for item in program.items:
            if isinstance(item, ast.RecipeDecl):
                self.globals.define(item.name, item)
            elif isinstance(item, ast.FunctionDecl):
                self.globals.define(item.name, item)

        for item in program.items:
            if isinstance(item, ast.EvalStmt):
                self._eval_EvalStmt(item, self.globals)

        return self.outputs

    # -- dispatch -----------------------------------------------------------

    def _eval(self, node, env: Environment):
        method = getattr(self, f"_eval_{type(node).__name__}", None)
        if method is None:
            raise RuntimeRecipixError(
                getattr(node, "line", 0),
                f"interpreter has no handler for AST node {type(node).__name__}",
            )
        return method(node, env)

    def _exec_stmt(self, stmt, env: Environment) -> None:
        method = getattr(self, f"_eval_{type(stmt).__name__}", None)
        if method is None:
            raise RuntimeRecipixError(
                getattr(stmt, "line", 0),
                f"interpreter has no handler for statement {type(stmt).__name__}",
            )
        method(stmt, env)

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _project_to_quantity(v):
        """Implicit Ingredient -> Quantity projection (decision #31)."""
        if isinstance(v, RtIngredient):
            return v.quantity
        return v

    # -- statements ---------------------------------------------------------

    def _eval_EvalStmt(self, node, env):
        value = self._eval(node.expr, env)
        if isinstance(value, RtRecipe):
            text = self._render_recipe(value) if self._render_output else repr(value)
        else:
            text = repr(value)
        self.outputs.append(text)

    def _eval_LetStmt(self, node, env):
        value = self._eval(node.expr, env)
        env.define(node.name, value)

    def _eval_IfStmt(self, node, env):
        cond = self._eval(node.condition, env)
        if cond:
            inner = env.child()
            for s in node.then_body:
                self._exec_stmt(s, inner)
        elif node.else_body is not None:
            inner = env.child()
            for s in node.else_body:
                self._exec_stmt(s, inner)

    def _eval_RepeatStmt(self, node, env):
        n = self._eval(node.count, env)
        if isinstance(n, bool) or not isinstance(n, int):
            raise RuntimeRecipixError(
                node.line, f"repeat count must be int, got {type(n).__name__}"
            )
        if n < 0:
            raise RuntimeRecipixError(node.line, f"negative repeat count: {n}")
        for _ in range(n):
            inner = env.child()
            for s in node.body:
                self._exec_stmt(s, inner)

    def _eval_ForeachStmt(self, node, env):
        iterable = self._eval(node.iterable, env)
        if not isinstance(iterable, RtList):
            raise RuntimeRecipixError(
                node.line,
                f"foreach source must be a list, got {type(iterable).__name__}",
            )
        for val in iterable.elements:
            inner = env.child()
            inner.define(node.var_name, val)
            for s in node.body:
                self._exec_stmt(s, inner)

    def _eval_ReturnStmt(self, node, env):
        raise Interpreter.ReturnException(self._eval(node.expr, env))

    def _eval_ActionStmt(self, node, env):
        # Outside of recipe bodies, action statements are not legal — the
        # type checker would have rejected this. If we still see one here
        # (e.g. running parse-only code), treat it as a no-op for safety.
        return None

    # -- expressions: literals + identifier --------------------------------

    def _eval_IntLit(self, node, env):
        return node.value

    def _eval_FloatLit(self, node, env):
        return node.value

    def _eval_BoolLit(self, node, env):
        return node.value

    def _eval_StringLit(self, node, env):
        return node.value

    def _eval_Identifier(self, node, env):
        try:
            return env.lookup(node.name)
        except KeyError:
            raise RuntimeRecipixError(
                node.line, f"unknown identifier {node.name!r}"
            ) from None

    def _eval_QuantityLit(self, node, env):
        if node.unit == "pinch":
            return PINCH
        base_value, dimension = normalize_to_base(float(node.number), node.unit)
        # Keep int-ness if the input was int and the conversion produced a whole
        # number — useful for Count quantities. Mostly cosmetic for rendering.
        if isinstance(node.number, int) and base_value.is_integer():
            base_value = int(base_value)
        return RtQuantity(value=base_value, dimension=dimension)

    def _eval_ListLit(self, node, env):
        elements = [self._eval(e, env) for e in node.elements]
        # element_type is best-effort at runtime; the type checker has the
        # authoritative value. Use the first element's runtime kind.
        if not elements:
            element_type = "unknown"
        else:
            first = elements[0]
            if isinstance(first, RtQuantity):
                element_type = first.dimension
            elif isinstance(first, bool):
                element_type = "bool"
            elif isinstance(first, int):
                element_type = "int"
            elif isinstance(first, float):
                element_type = "float"
            elif isinstance(first, str):
                element_type = "string"
            else:
                element_type = type(first).__name__
        return RtList(elements=elements, element_type=element_type)

    # -- expressions: operators --------------------------------------------

    def _eval_UnaryOp(self, node, env):
        v = self._eval(node.operand, env)
        v = self._project_to_quantity(v)
        if node.op == "-":
            if isinstance(v, RtQuantity):
                return RtQuantity(-v.value, v.dimension)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return -v
            raise RuntimeRecipixError(
                node.line, f"unary '-' on unsupported type {type(v).__name__}"
            )
        if node.op == "!":
            return not bool(v)
        raise RuntimeRecipixError(node.line, f"unknown unary operator {node.op!r}")

    def _eval_BinaryOp(self, node, env):
        op = node.op
        if op == "&&":
            l = self._eval(node.left, env)
            if not l:
                return False
            return bool(self._eval(node.right, env))
        if op == "||":
            l = self._eval(node.left, env)
            if l:
                return True
            return bool(self._eval(node.right, env))

        left = self._project_to_quantity(self._eval(node.left, env))
        right = self._project_to_quantity(self._eval(node.right, env))

        is_num_left = isinstance(left, (int, float)) and not isinstance(left, bool)
        is_num_right = isinstance(right, (int, float)) and not isinstance(right, bool)

        # Numeric / numeric
        if is_num_left and is_num_right:
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                if right == 0:
                    raise RuntimeRecipixError(node.line, "division by zero")
                if isinstance(left, int) and isinstance(right, int):
                    # int / int — truncated toward zero per spec §3
                    return int(left / right)
                return left / right
            raise RuntimeRecipixError(node.line, f"unknown binary op {op!r}")

        # Quantity arithmetic
        if isinstance(left, RtQuantity) and isinstance(right, RtQuantity):
            if op in ("+", "-"):
                if left.dimension != right.dimension:
                    raise RuntimeRecipixError(
                        node.line,
                        f"dimension mismatch: {left.dimension} {op} {right.dimension}",
                    )
                val = left.value + right.value if op == "+" else left.value - right.value
                return RtQuantity(val, left.dimension)
            if op == "/":
                if left.dimension != right.dimension:
                    raise RuntimeRecipixError(
                        node.line,
                        f"dimension mismatch: {left.dimension} / {right.dimension}",
                    )
                if right.value == 0:
                    raise RuntimeRecipixError(node.line, "division by zero")
                return left.value / right.value  # unitless ratio
            raise RuntimeRecipixError(
                node.line, f"unsupported operation: Quantity {op} Quantity"
            )

        if isinstance(left, RtQuantity) and is_num_right:
            if op == "*":
                return RtQuantity(left.value * right, left.dimension)
            if op == "/":
                if right == 0:
                    raise RuntimeRecipixError(node.line, "division by zero")
                return RtQuantity(left.value / right, left.dimension)
            raise RuntimeRecipixError(
                node.line, f"unsupported operation: Quantity {op} scalar"
            )

        if is_num_left and isinstance(right, RtQuantity):
            if op == "*":
                return RtQuantity(left * right.value, right.dimension)
            raise RuntimeRecipixError(
                node.line, f"unsupported operation: scalar {op} Quantity"
            )

        raise RuntimeRecipixError(
            node.line,
            f"unsupported {op} between {type(left).__name__} and {type(right).__name__}",
        )

    def _eval_CompareOp(self, node, env):
        left = self._project_to_quantity(self._eval(node.left, env))
        right = self._project_to_quantity(self._eval(node.right, env))

        if isinstance(left, RtQuantity) and isinstance(right, RtQuantity):
            if left.dimension != right.dimension:
                raise RuntimeRecipixError(
                    node.line,
                    f"dimension mismatch in comparison: "
                    f"{left.dimension} {node.op} {right.dimension}",
                )
            a, b = left.value, right.value
        else:
            a, b = left, right

        op = node.op
        if op == "<":  return a < b
        if op == "<=": return a <= b
        if op == ">":  return a > b
        if op == ">=": return a >= b
        if op == "==": return a == b
        if op == "!=": return a != b
        raise RuntimeRecipixError(node.line, f"unknown comparison {op!r}")

    def _eval_QuantityOf(self, node, env):
        v = self._eval(node.operand, env)
        if not isinstance(v, RtIngredient):
            raise RuntimeRecipixError(
                node.line,
                f"quantity_of expects an Ingredient, got {type(v).__name__}",
            )
        return v.quantity

    # -- expressions: calls ------------------------------------------------

    def _eval_FunctionCall(self, node, env):
        try:
            decl = env.lookup(node.name)
        except KeyError:
            raise RuntimeRecipixError(
                node.line, f"unknown function {node.name!r}"
            ) from None
        if not isinstance(decl, ast.FunctionDecl):
            raise RuntimeRecipixError(
                node.line, f"{node.name!r} is not a function"
            )

        call_env = self.globals.child()
        for param, arg in zip(decl.params, node.args):
            val = self._eval(arg, env)
            call_env.define(param.name, val)

        try:
            for stmt in decl.body:
                self._exec_stmt(stmt, call_env)
        except Interpreter.ReturnException as ret:
            return ret.value
        raise RuntimeRecipixError(
            node.line, f"function {node.name!r} returned no value"
        )

    def _eval_AmbiguousCall(self, node, env):
        # Type checker is expected to resolve and rewrite these. If a raw
        # AmbiguousCall reaches us, attempt name-table dispatch as a fallback
        # (zero-arg calls have no kwargs to disambiguate anyway).
        kind = getattr(node, "resolved_kind", None)
        try:
            decl = env.lookup(node.name)
        except KeyError:
            raise RuntimeRecipixError(
                node.line, f"unknown name in call: {node.name!r}"
            ) from None
        if kind == "recipe" or isinstance(decl, ast.RecipeDecl):
            fake = ast.RecipeCall(name=node.name, kwargs=[], line=node.line)
            return self._eval_RecipeCall(fake, env)
        if kind == "function" or isinstance(decl, ast.FunctionDecl):
            fake = ast.FunctionCall(name=node.name, args=[], line=node.line)
            return self._eval_FunctionCall(fake, env)
        raise RuntimeRecipixError(
            node.line,
            "AmbiguousCall reached interpreter — typechecker did not run",
        )

    def _eval_RecipeCall(self, node, env):
        try:
            decl = env.lookup(node.name)
        except KeyError:
            raise RuntimeRecipixError(
                node.line, f"unknown recipe {node.name!r}"
            ) from None
        if not isinstance(decl, ast.RecipeDecl):
            raise RuntimeRecipixError(
                node.line, f"{node.name!r} is not a recipe"
            )

        # Fresh scope parented to globals so functions/recipes are visible
        recipe_env = self.globals.child()

        kwarg_map = {kw.name: kw.value for kw in node.kwargs}
        for p in decl.params:
            if p.name not in kwarg_map:
                raise RuntimeRecipixError(
                    node.line,
                    f"recipe {node.name!r}: missing kwarg {p.name!r}",
                )
            val = self._eval(kwarg_map[p.name], env)
            recipe_env.define(p.name, val)

        servings_value = self._eval(decl.serves, recipe_env)
        if isinstance(servings_value, bool) or not isinstance(servings_value, int):
            raise RuntimeRecipixError(
                node.line,
                f"recipe 'serves' must evaluate to int, got "
                f"{type(servings_value).__name__}",
            )

        ingredients: dict[str, RtIngredient] = {}
        for ing in decl.ingredients:
            v = self._eval(ing.expr, recipe_env)
            if isinstance(v, RtPinch):
                quantity = v
            elif isinstance(v, RtQuantity):
                quantity = v
            else:
                raise RuntimeRecipixError(
                    ing.line,
                    f"ingredient {ing.name!r}: expected Quantity or Pinch, "
                    f"got {type(v).__name__}",
                )
            rti = RtIngredient(name=ing.name, quantity=quantity)
            ingredients[ing.name] = rti
            recipe_env.define(ing.name, rti)

        steps: list = []
        for step in decl.steps:
            step_env = recipe_env.child()
            at_v = self._eval(step.at_expr, step_env) if step.at_expr else None
            for_v = self._eval(step.for_expr, step_env) if step.for_expr else None
            actions: list[tuple[str, list]] = []
            self._exec_step_body(step.body, step_env, actions)
            steps.append({
                "description": step.description,
                "at": at_v,
                "for": for_v,
                "actions": actions,
                "line": step.line,
            })

        return RtRecipe(
            name=decl.name,
            servings=servings_value,
            ingredients=ingredients,
            steps=steps,
        )

    def _exec_step_body(self, body, env: Environment, actions: list) -> None:
        for stmt in body:
            if isinstance(stmt, ast.ActionStmt):
                arg_records: list = []
                for a in stmt.args:
                    if isinstance(a, ast.Identifier):
                        try:
                            v = env.lookup(a.name)
                        except KeyError:
                            raise RuntimeRecipixError(
                                a.line, f"unknown identifier {a.name!r}"
                            ) from None
                        if isinstance(v, RtIngredient):
                            arg_records.append(("ingredient_ref", a.name))
                            continue
                        arg_records.append(("value", v))
                    else:
                        arg_records.append(("value", self._eval(a, env)))
                actions.append((stmt.verb, arg_records))
            elif isinstance(stmt, ast.RepeatStmt):
                n = self._eval(stmt.count, env)
                if isinstance(n, bool) or not isinstance(n, int):
                    raise RuntimeRecipixError(
                        stmt.line,
                        f"repeat count must be int, got {type(n).__name__}",
                    )
                if n < 0:
                    raise RuntimeRecipixError(
                        stmt.line, f"negative repeat count: {n}"
                    )
                for _ in range(n):
                    self._exec_step_body(stmt.body, env.child(), actions)
            elif isinstance(stmt, ast.IfStmt):
                cond = self._eval(stmt.condition, env)
                if cond:
                    self._exec_step_body(stmt.then_body, env.child(), actions)
                elif stmt.else_body is not None:
                    self._exec_step_body(stmt.else_body, env.child(), actions)
            elif isinstance(stmt, ast.ForeachStmt):
                iterable = self._eval(stmt.iterable, env)
                if not isinstance(iterable, RtList):
                    raise RuntimeRecipixError(
                        stmt.line,
                        f"foreach source must be a list, got "
                        f"{type(iterable).__name__}",
                    )
                for val in iterable.elements:
                    inner = env.child()
                    inner.define(stmt.var_name, val)
                    self._exec_step_body(stmt.body, inner, actions)
            elif isinstance(stmt, ast.LetStmt):
                env.define(stmt.name, self._eval(stmt.expr, env))
            else:
                raise RuntimeRecipixError(
                    getattr(stmt, "line", 0),
                    f"unexpected statement in step body: {type(stmt).__name__}",
                )

    def _eval_ScaleCall(self, node, env):
        recipe = self._eval(node.recipe, env)
        if not isinstance(recipe, RtRecipe):
            raise RuntimeRecipixError(
                node.line, f"scale expects a Recipe, got {type(recipe).__name__}"
            )
        by = self._eval(node.by, env)
        if isinstance(by, bool) or not isinstance(by, (int, float)):
            raise RuntimeRecipixError(
                node.line, f"scale 'by' must be numeric, got {type(by).__name__}"
            )
        if by <= 0:
            raise RuntimeRecipixError(
                node.line, f"scale 'by' must be > 0 (got {by})"
            )

        new_ings: dict[str, RtIngredient] = {}
        for key, ing in recipe.ingredients.items():
            q = ing.quantity
            if isinstance(q, RtQuantity) and q.dimension in ("Mass", "Volume", "Count"):
                new_q = RtQuantity(q.value * by, q.dimension)
            else:
                new_q = q
            new_ings[key] = RtIngredient(name=ing.name, quantity=new_q)

        new_servings = int(round(recipe.servings * by))

        return RtRecipe(
            name=recipe.name,
            servings=new_servings,
            ingredients=new_ings,
            steps=recipe.steps,
        )

    def _eval_SubstituteCall(self, node, env):
        recipe = self._eval(node.recipe, env)
        if not isinstance(recipe, RtRecipe):
            raise RuntimeRecipixError(
                node.line,
                f"substitute expects a Recipe, got {type(recipe).__name__}",
            )
        ratio = self._eval(node.ratio, env)
        if isinstance(ratio, bool) or not isinstance(ratio, (int, float)):
            raise RuntimeRecipixError(
                node.line,
                f"substitute ratio must be numeric, got {type(ratio).__name__}",
            )

        original_name = node.original_name
        replacement_name = node.replacement_name

        if original_name not in recipe.ingredients:
            raise RuntimeRecipixError(
                node.line,
                f"substitute: ingredient {original_name!r} not in recipe "
                f"{recipe.name!r}",
            )
        if replacement_name not in recipe.ingredients:
            raise RuntimeRecipixError(
                node.line,
                f"substitute: replacement ingredient {replacement_name!r} "
                f"not in recipe {recipe.name!r}",
            )

        original = recipe.ingredients[original_name]
        if not isinstance(original.quantity, RtQuantity):
            raise RuntimeRecipixError(
                node.line,
                f"substitute: cannot substitute on Pinch ingredient "
                f"{original_name!r}",
            )
        new_q = RtQuantity(original.quantity.value * ratio, original.quantity.dimension)

        new_ings = dict(recipe.ingredients)
        new_ings[original_name] = RtIngredient(name=replacement_name, quantity=new_q)
        if replacement_name != original_name:
            new_ings.pop(replacement_name, None)

        return RtRecipe(
            name=recipe.name,
            servings=recipe.servings,
            ingredients=new_ings,
            steps=recipe.steps,
        )

    def _eval_KwArg(self, node, env):
        return self._eval(node.value, env)


__all__ = ["run", "Interpreter", "RuntimeRecipixError"]
