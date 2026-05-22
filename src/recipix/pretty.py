"""AST pretty-printer for --dump-ast.  Produces indented S-expression style output."""

from __future__ import annotations
from .ast_nodes import *


_INDENT = "  "


def dump(node, indent: int = 0) -> str:
    prefix = _INDENT * indent
    name = type(node).__name__

    if isinstance(node, Program):
        lines = [f"{prefix}(Program"]
        for item in node.items:
            lines.append(dump(item, indent + 1))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, RecipeDecl):
        lines = [f"{prefix}(RecipeDecl name={node.name!r} line={node.line}"]
        if node.params:
            lines.append(f"{_INDENT*(indent+1)}params:")
            for p in node.params:
                lines.append(dump(p, indent + 2))
        lines.append(f"{_INDENT*(indent+1)}serves:")
        lines.append(dump(node.serves, indent + 2))
        if node.ingredients:
            lines.append(f"{_INDENT*(indent+1)}ingredients:")
            for ing in node.ingredients:
                lines.append(dump(ing, indent + 2))
        if node.steps:
            lines.append(f"{_INDENT*(indent+1)}steps:")
            for s in node.steps:
                lines.append(dump(s, indent + 2))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, FunctionDecl):
        lines = [f"{prefix}(FunctionDecl name={node.name!r} -> {node.return_type} line={node.line}"]
        if node.params:
            lines.append(f"{_INDENT*(indent+1)}params:")
            for p in node.params:
                lines.append(dump(p, indent + 2))
        lines.append(f"{_INDENT*(indent+1)}body:")
        for s in node.body:
            lines.append(dump(s, indent + 2))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, Param):
        return f"{prefix}(Param {node.name} : {node.type_name})"

    if isinstance(node, IngredientDecl):
        lines = [f"{prefix}(IngredientDecl {node.name!r} line={node.line}"]
        lines.append(dump(node.expr, indent + 1))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, StepDecl):
        lines = [f"{prefix}(StepDecl {node.description!r} line={node.line}"]
        if node.at_expr is not None:
            lines.append(f"{_INDENT*(indent+1)}at:")
            lines.append(dump(node.at_expr, indent + 2))
        if node.for_expr is not None:
            lines.append(f"{_INDENT*(indent+1)}for:")
            lines.append(dump(node.for_expr, indent + 2))
        lines.append(f"{_INDENT*(indent+1)}body:")
        for s in node.body:
            lines.append(dump(s, indent + 2))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, EvalStmt):
        lines = [f"{prefix}(EvalStmt line={node.line}"]
        lines.append(dump(node.expr, indent + 1))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, LetStmt):
        lines = [f"{prefix}(LetStmt {node.name!r} : {node.type_name} line={node.line}"]
        lines.append(dump(node.expr, indent + 1))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, IfStmt):
        lines = [f"{prefix}(IfStmt line={node.line}"]
        lines.append(f"{_INDENT*(indent+1)}condition:")
        lines.append(dump(node.condition, indent + 2))
        lines.append(f"{_INDENT*(indent+1)}then:")
        for s in node.then_body:
            lines.append(dump(s, indent + 2))
        if node.else_body is not None:
            lines.append(f"{_INDENT*(indent+1)}else:")
            for s in node.else_body:
                lines.append(dump(s, indent + 2))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, RepeatStmt):
        lines = [f"{prefix}(RepeatStmt line={node.line}"]
        lines.append(f"{_INDENT*(indent+1)}count:")
        lines.append(dump(node.count, indent + 2))
        lines.append(f"{_INDENT*(indent+1)}body:")
        for s in node.body:
            lines.append(dump(s, indent + 2))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, ForeachStmt):
        lines = [f"{prefix}(ForeachStmt {node.var_name!r} in line={node.line}"]
        lines.append(f"{_INDENT*(indent+1)}iterable:")
        lines.append(dump(node.iterable, indent + 2))
        lines.append(f"{_INDENT*(indent+1)}body:")
        for s in node.body:
            lines.append(dump(s, indent + 2))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, ReturnStmt):
        lines = [f"{prefix}(ReturnStmt line={node.line}"]
        lines.append(dump(node.expr, indent + 1))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, ActionStmt):
        lines = [f"{prefix}(ActionStmt {node.verb!r} line={node.line}"]
        for a in node.args:
            lines.append(dump(a, indent + 1))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, BinaryOp):
        lines = [f"{prefix}(BinaryOp {node.op!r} line={node.line}"]
        lines.append(dump(node.left, indent + 1))
        lines.append(dump(node.right, indent + 1))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, CompareOp):
        lines = [f"{prefix}(CompareOp {node.op!r} line={node.line}"]
        lines.append(dump(node.left, indent + 1))
        lines.append(dump(node.right, indent + 1))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, UnaryOp):
        lines = [f"{prefix}(UnaryOp {node.op!r} line={node.line}"]
        lines.append(dump(node.operand, indent + 1))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, QuantityOf):
        lines = [f"{prefix}(QuantityOf line={node.line}"]
        lines.append(dump(node.operand, indent + 1))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, SubstituteCall):
        lines = [f"{prefix}(SubstituteCall orig={node.original_name!r} repl={node.replacement_name!r} line={node.line}"]
        lines.append(f"{_INDENT*(indent+1)}recipe:")
        lines.append(dump(node.recipe, indent + 2))
        lines.append(f"{_INDENT*(indent+1)}ratio:")
        lines.append(dump(node.ratio, indent + 2))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, ScaleCall):
        lines = [f"{prefix}(ScaleCall line={node.line}"]
        lines.append(f"{_INDENT*(indent+1)}recipe:")
        lines.append(dump(node.recipe, indent + 2))
        lines.append(f"{_INDENT*(indent+1)}by:")
        lines.append(dump(node.by, indent + 2))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, FunctionCall):
        lines = [f"{prefix}(FunctionCall {node.name!r} line={node.line}"]
        for a in node.args:
            lines.append(dump(a, indent + 1))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, AmbiguousCall):
        return f"{prefix}(AmbiguousCall {node.name!r} line={node.line})"

    if isinstance(node, RecipeCall):
        lines = [f"{prefix}(RecipeCall {node.name!r} line={node.line}"]
        for kw in node.kwargs:
            lines.append(dump(kw, indent + 1))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, KwArg):
        lines = [f"{prefix}(KwArg {node.name!r}:"]
        lines.append(dump(node.value, indent + 1))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    if isinstance(node, Identifier):
        return f"{prefix}(Identifier {node.name!r} line={node.line})"

    if isinstance(node, IntLit):
        return f"{prefix}(IntLit {node.value} line={node.line})"

    if isinstance(node, FloatLit):
        return f"{prefix}(FloatLit {node.value} line={node.line})"

    if isinstance(node, BoolLit):
        return f"{prefix}(BoolLit {node.value} line={node.line})"

    if isinstance(node, StringLit):
        return f"{prefix}(StringLit {node.value!r} line={node.line})"

    if isinstance(node, QuantityLit):
        return f"{prefix}(QuantityLit {node.number} {node.unit} line={node.line})"

    if isinstance(node, ListLit):
        lines = [f"{prefix}(ListLit line={node.line}"]
        for e in node.elements:
            lines.append(dump(e, indent + 1))
        lines.append(f"{prefix})")
        return "\n".join(lines)

    return f"{prefix}(UNKNOWN {name})"
