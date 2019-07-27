from __future__ import annotations

import inspect, ast

from typing import List


class JavaGenerator(ast.NodeVisitor):
    def visit(self, node):
        getattr(self, "visit_"+node.__class__.__name__)(node)

    def visit_Module(self, node: ast.Module):
        for stmt in node.body:
            self.visit(stmt)

    def visit_ClassDef(self, node: ast.ClassDef):
        out("public class ")
        out(node.name)
        out(" {\n")
        for stmt in node.body:
            self.visit(stmt)
            out("\n")
        out("}\n")

    @staticmethod
    def ann(name):
        typ_dict = {
            "int": "Integer",
            "str": "String"
        }
        return typ_dict[name]

    def visit_Expr(self, node: ast.Expr):
        out(" " * node.col_offset)
        self.visit(node.value)
        out(";\n")

    def visit_If(self, node: ast.If):
        out(" " * node.col_offset)
        out("if (")
        self.visit(node.test)
        out(") {\n")
        for stmt in node.body:
            self.visit(stmt)
        out(" " * node.col_offset)
        out("}")
        if hasattr(node, "orelse"):
            out(" else {\n")
            for stmt in node.orelse:
                self.visit(stmt)
            out(" " * node.col_offset)
            out("}")
        out("\n")

    def visit_FunctionDef(self, node: ast.FunctionDef):

        if node.name == "__init__":
            instance_vars = [self.ann(arg.annotation.id) + " " + arg.arg for arg in node.args.args if arg.arg != "self"]
            for var in instance_vars:
                out(" " * node.col_offset)
                out(var)
                out(";\n")

            out("\n")
            out(" " * node.col_offset)
            out("public ")
            cls_name = next(arg.annotation.id for arg in node.args.args if arg.arg == "self")
            out(cls_name)
            out("(")
            out(", ".join(self.ann(arg.annotation.id) + " " + arg.arg for arg in node.args.args if arg.arg != "self"))
            out(") {\n")

            for stmt in node.body:
                self.visit(stmt)
            out(" " * node.col_offset)
            out("}\n")
        else:
            out(" " * node.col_offset)

            if any((dec.id == "staticmethod" if isinstance(dec, ast.Name) else False)  for dec in node.decorator_list):
                out("public static ")
            else:
                out("public ")
            self.visit(node.returns)
            # out(self.ann(node.returns.id))
            out(" ")
            out(node.name)

            out("(")
            sep = ""
            for arg in node.args.args:
                if arg.arg == "self":
                    continue
                elif isinstance(arg.annotation, ast.Subscript):
                    out(sep)
                    if isinstance(arg.annotation.value, ast.Name) and arg.annotation.value.id == "List":
                        if isinstance(arg.annotation.slice, ast.Index):
                            out(self.ann(arg.annotation.slice.value.id))
                            out("[]")
                        else:
                            raise NotImplementedError()
                    else:
                        # print(arg.annotation.value.value)
                        raise NotImplementedError()
                elif isinstance(arg.annotation, ast.Name):
                    out(sep)
                    out(self.ann(arg.annotation.id))
                else:
                    raise NotImplementedError()
                out(" ")
                out(arg.arg)
                sep = ", "
            # out(", ".join(self.ann(arg.annotation.id) + " " + arg.arg for arg in node.args.args if arg.arg != "self"))
            out(") {\n")

            for stmt in node.body:
                self.visit(stmt)

            # print(node.col_offset)
            out(" " * node.col_offset)
            out("}\n")

    def visit_BinOp(self, node: ast.BinOp):
        if isinstance(node.op, ast.Mult):
            out("(")
            self.visit(node.left)
            out(" * ")
            self.visit(node.right)
            out(")")
        elif isinstance(node.op, ast.Pow):
            out("Math.pow(")
            self.visit(node.left)
            out(", ")
            self.visit(node.right)
            out(")")
        elif isinstance(node.op, ast.Add):
            out("(")
            self.visit(node.left)
            out(" + ")
            self.visit(node.right)
            out(")")
        elif isinstance(node.op, ast.Sub):
            out("(")
            self.visit(node.left)
            out(" - ")
            self.visit(node.right)
            out(")")
        else:
            raise NotImplementedError(node.op)

    def visit_Compare(self, node: ast.Compare):
        if isinstance(node.ops[0], ast.Gt):
            out("(")
            self.visit(node.left)
            out(" > ")
            self.visit(node.comparators[0])
            out(")")
        elif isinstance(node.ops[0], ast.Lt):
            out("(")
            self.visit(node.left)
            out(" < ")
            self.visit(node.comparators[0])
            out(")")
        else:
            raise NotImplementedError(node.op)

    def visit_NameConstant(self, node: ast.NameConstant):
        if node.value is True:
            out("true")
        elif node.value is False:
            out("false")
        elif node.value is None:
            out("void")
        else:
            raise NotImplementedError()

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            name = node.id
            if name == "int":
                out("Integer")
            else:
                out(node.id)
        else:
            raise NotImplementedError()

    def visit_Attribute(self, node: ast.Attribute):
        if isinstance(node.ctx, ast.Load):
            if isinstance(node.value, ast.Name) and node.value.id == "self":
                out("this.")
            else:
                out(node.value)
                out(".")
            out(node.attr)
        else:
            raise NotImplementedError()

    def visit_Return(self, node: ast.Return):
        out(" "*node.col_offset)
        out("return ")
        self.visit(node.value)
        out(";\n")

    def visit_Assign(self, node: ast.Assign):
        out(" " * node.col_offset)

        target = node.targets[0]

        if isinstance(target, ast.Name):
            out(target.id)
        elif isinstance(target, ast.Attribute):
            if isinstance(target.value, ast.Name) and target.value.id == "self":
                out("this.")
            else:
                # self.visit(target.value)
                out(target.value)
                out(".")
            out(target.attr)
        else:
            raise NotImplementedError()

        out(" = ")

        self.visit(node.value)
        out(";\n")

    def visit_AnnAssign(self, node: ast.AnnAssign):
        out(" " * node.col_offset)

        if isinstance(node.target, ast.Name):
            out(self.ann(node.annotation.id) + " " + node.target.id)
        elif isinstance(node.target, ast.Attribute):
            out(self.ann(node.annotation.id))
            out(" ")
            if isinstance(node.target.value, ast.Name) and node.target.value.id == "self":
                pass
            else:
                out(node.target.value)
                out(".")
            out(node.target.attr)
        else:
            raise NotImplementedError()

        out(" = ")

        self.visit(node.value)
        out(";\n")

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "int":
            out("(int) (")
            self.visit(node.args[0])
            out(")")
        else:
            self.visit(node.func)
            out("(")

            sep = ""
            for arg in node.args:
                out(sep)
                self.visit(arg)
                sep = ", "
            out(")")

    def visit_Num(self, node: ast.Num):
        out(node.n)


def out(arg):
    with open("out.java", "a") as file:
        file.write(str(arg))


def generate_java(func):
    with open("out.java", "w"):
        pass
    code = ast.parse(inspect.getsource(func))
    JavaGenerator().visit(code)


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
