from __future__ import annotations

import ast
import inspect
from typing import List, IO


class JavaGenerator(ast.NodeVisitor):
    def __init__(self, stream: IO):
        self.stream = stream

    def out(self, text: str):
        self.stream.write(str(text))

    def indent(self, node: ast.AST):
        self.out(" " * node.col_offset)

    def visit(self, node):
        getattr(self, "visit_"+node.__class__.__name__)(node)

    def visit_Module(self, node: ast.Module):
        for stmt in node.body:
            self.visit(stmt)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.out(f"public class {node.name} {{\n")
        for stmt in node.body:
            self.visit(stmt)
            self.out("\n")
        self.out("}\n")

    @staticmethod
    def ann(name):
        typ_dict = {
            "int": "Integer",
            "str": "String"
        }
        return typ_dict[name]

    def visit_Expr(self, node: ast.Expr):
        self.indent(node)
        self.visit(node.value)
        self.out(";\n")

    def visit_If(self, node: ast.If):
        self.indent(node)
        self.out("if (")
        self.visit(node.test)
        self.out(") {\n")
        for stmt in node.body:
            self.visit(stmt)
        self.indent(node)
        self.out("}")
        if hasattr(node, "orelse"):
            self.out(" else {\n")
            for stmt in node.orelse:
                self.visit(stmt)
            self.indent(node)
            self.out("}")
        self.out("\n")

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name == "__init__":
            # TODO: Maybe search __annotations__ for the instance vars instead?
            instance_vars = [self.ann(arg.annotation.id) + " " + arg.arg for arg in node.args.args if arg.arg != "self"]
            for var in instance_vars:
                self.indent(node)
                self.out(var)
                self.out(";\n")

            self.out("\n")
            self.indent(node)
            self.out("public ")
            cls_name = next(arg.annotation.id for arg in node.args.args if arg.arg == "self")
            self.out(cls_name)
            self.out("(")
            self.out(", ".join(self.ann(arg.annotation.id)+" "+arg.arg for arg in node.args.args if arg.arg != "self"))
            self.out(") {\n")

            for stmt in node.body:
                self.visit(stmt)
            self.indent(node)
            self.out("}\n")
        else:
            self.indent(node)

            if any((dec.id == "staticmethod" if isinstance(dec, ast.Name) else False) for dec in node.decorator_list):
                self.out("public static ")
            else:
                self.out("public ")
            self.visit(node.returns)
            # self.out(self.ann(node.returns.id))
            self.out(" ")
            self.out(node.name)

            self.out("(")
            sep = ""
            for arg in node.args.args:
                if arg.arg == "self":
                    continue
                elif isinstance(arg.annotation, ast.Subscript):
                    self.out(sep)
                    if isinstance(arg.annotation.value, ast.Name) and arg.annotation.value.id == "List":
                        if isinstance(arg.annotation.slice, ast.Index):
                            self.out(self.ann(arg.annotation.slice.value.id))
                            self.out("[]")
                        else:
                            raise NotImplementedError()
                    else:
                        # print(arg.annotation.value.value)
                        raise NotImplementedError()
                elif isinstance(arg.annotation, ast.Name):
                    self.out(sep)
                    self.out(self.ann(arg.annotation.id))
                else:
                    raise NotImplementedError()
                self.out(" ")
                self.out(arg.arg)
                sep = ", "
            self.out(") {\n")

            for stmt in node.body:
                self.visit(stmt)

            # print(node.col_offset)
            self.indent(node)
            self.out("}\n")

    def visit_BinOp(self, node: ast.BinOp):
        if isinstance(node.op, ast.Mult):
            self.out("(")
            self.visit(node.left)
            self.out(" * ")
            self.visit(node.right)
            self.out(")")
        elif isinstance(node.op, ast.Pow):
            self.out("Math.pow(")
            self.visit(node.left)
            self.out(", ")
            self.visit(node.right)
            self.out(")")
        elif isinstance(node.op, ast.Add):
            self.out("(")
            self.visit(node.left)
            self.out(" + ")
            self.visit(node.right)
            self.out(")")
        elif isinstance(node.op, ast.Sub):
            self.out("(")
            self.visit(node.left)
            self.out(" - ")
            self.visit(node.right)
            self.out(")")
        else:
            raise NotImplementedError(node.op)

    def visit_Compare(self, node: ast.Compare):
        if isinstance(node.ops[0], ast.Gt):
            self.out("(")
            self.visit(node.left)
            self.out(" > ")
            self.visit(node.comparators[0])
            self.out(")")
        elif isinstance(node.ops[0], ast.Lt):
            self.out("(")
            self.visit(node.left)
            self.out(" < ")
            self.visit(node.comparators[0])
            self.out(")")
        else:
            raise NotImplementedError(node.op)

    def visit_NameConstant(self, node: ast.NameConstant):
        if node.value is True:
            self.out("true")
        elif node.value is False:
            self.out("false")
        elif node.value is None:
            self.out("void")
        else:
            raise NotImplementedError()

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            name = node.id
            if name == "int":
                self.out("Integer")
            else:
                self.out(node.id)
        else:
            raise NotImplementedError()

    def visit_Attribute(self, node: ast.Attribute):
        if isinstance(node.ctx, ast.Load):
            if isinstance(node.value, ast.Name) and node.value.id == "self":
                self.out("this.")
            else:
                self.out(node.value)
                self.out(".")
            self.out(node.attr)
        else:
            raise NotImplementedError()

    def visit_Return(self, node: ast.Return):
        self.indent(node)
        self.out("return ")
        self.visit(node.value)
        self.out(";\n")

    def visit_Assign(self, node: ast.Assign):
        self.indent(node)

        target = node.targets[0]

        if isinstance(target, ast.Name):
            self.out(target.id)
        elif isinstance(target, ast.Attribute):
            if isinstance(target.value, ast.Name) and target.value.id == "self":
                self.out("this.")
            else:
                # self.visit(target.value)
                self.out(target.value)
                self.out(".")
            self.out(target.attr)
        else:
            raise NotImplementedError()

        self.out(" = ")

        self.visit(node.value)
        self.out(";\n")

    def visit_AnnAssign(self, node: ast.AnnAssign):
        self.indent(node)

        if isinstance(node.target, ast.Name):
            self.out(self.ann(node.annotation.id) + " " + node.target.id)
        elif isinstance(node.target, ast.Attribute):
            self.out(self.ann(node.annotation.id))
            self.out(" ")
            if isinstance(node.target.value, ast.Name) and node.target.value.id == "self":
                pass
            else:
                self.out(node.target.value)
                self.out(".")
            self.out(node.target.attr)
        else:
            raise NotImplementedError()

        self.out(" = ")

        self.visit(node.value)
        self.out(";\n")

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "int":
            self.out("(int) (")
            self.visit(node.args[0])
            self.out(")")
        else:
            self.visit(node.func)
            self.out("(")

            sep = ""
            for arg in node.args:
                self.out(sep)
                self.visit(arg)
                sep = ", "
            self.out(")")

    def visit_Num(self, node: ast.Num):
        self.out(node.n)


def generate_java(func):
    code = ast.parse(inspect.getsource(func))
    with open("out.java", "w") as file:
        JavaGenerator(file).visit(code)


class Main:
    def __init__(self: Main, name: int):
        self.name = name

    @staticmethod
    def main(self, args: List[str]) -> None:
        print(self.fibo(15))

    @staticmethod
    def fibo(self, n: int) -> int:
        if n < 2:
            return n
        else:
            return self.fibo(n-1) + self.fibo(n-2)


generate_java(Main)
