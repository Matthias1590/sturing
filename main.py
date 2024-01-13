from __future__ import annotations
import warnings
import rply
import os

warnings.filterwarnings("ignore")

with open("main.str", "r") as f:
    source = f.read()

TOKENS = {
    "VAR": r"var",
    "FUNC": r"func",
    "RETURN": r"return",
    "IF": r"if",
    "ELSE": r"else",
    "IDENT": r"[A-z_][A-z_0-9]*",
    "LPAR": r"\(",
    "RPAR": r"\)",
    "LCUR": r"\{",
    "RCUR": r"\}",
    "COMMA": r"\,",
    "DOT": r"\.",
    "SEMI": r"\;",
    "EQ": r"\=",
    "STRING": r"\"[^\"]*\""
}

lg = rply.LexerGenerator()

for name, pattern in TOKENS.items():
    lg.add(name, pattern)

lg.ignore(r"\s+")

lexer = lg.build()

pg = rply.ParserGenerator(TOKENS.keys(), cache_id="sturing")

@pg.production("program : top_levels")
def _(ts):
    return Program(ts[0])

def stringify(value: str) -> str:
    return '"' + repr("'" + value)[2:]

def assert_str(value: str) -> None:
    if not isinstance(value, str):
        raise Exception(f"expected string, got {type(value).__name__!r}")

def assert_func(value: str) -> None:
    if not isinstance(value, Func):
        raise Exception(f"expected func, got {type(value).__name__!r}")

def assert_str_or_func(value: str | Func) -> None:
    if not isinstance(value, (str, Func)):
        raise Exception(f"expected string or func, got {type(value).__name__!r}")

class Debug:
    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join(f'{k}={v!r}' for k, v in self.__dict__.items())})"

class Program(Debug):
    def __init__(self, tops: list[any]) -> None:
        self.tops = tops
    
    def compile(self) -> Ctx:
        ctx = Ctx()

        # declare funcs
        for top in self.tops:
            if isinstance(top, Var):
                continue
            
            top.declare(ctx)

        # declare vars
        for top in self.tops:
            if not isinstance(top, Var):
                continue
            
            top.declare(ctx)

        # define vars
        for top in self.tops:
            if not isinstance(top, Var):
                continue

            top.define(ctx)

        # define funcs
        for top in self.tops:
            if isinstance(top, Var):
                continue
        
            val = top.define(ctx)
            if val:
                ctx.main.append(val + ";")

        for top in self.tops:
            top.check(ctx)
        
        return ctx

    def eval(self) -> None:
        scope = Scope()

        for top in self.tops:
            top.eval(scope)

class Type:
    STRING = "STRING"
    FUNC = "FUNC"

class Ctx(Debug):
    def __init__(self) -> None:
        self.scope = Scope()
        self.code = []
        self.main = []
    
    def emit(self, line: str) -> None:
        self.code.append(line)

    def declare(self, name: str, type: Type) -> None:
        self.scope.declare(name)
        self.scope.set(name, type)
    
    def compile(self, path: str) -> None:
        with open("out.c", "w") as f:
            f.write("#include \"std.h\"\n")
            f.write("\n")
            f.write("\n".join(self.code) + "\n")
            f.write("\n")
            f.write("int main(void)\n")
            f.write("{\n")
            f.write("\n".join(self.main) + "\n")
            f.write("return 0;\n")
            f.write("}\n")
        
        if os.system(f"gcc -o {path} out.c std.c") != 0:
            raise Exception("failed to compile")


class Scope(Debug):
    def __init__(self, parent: Scope | None = None) -> None:
        self.parent = parent
        self.symbols = {}

        if not self.parent:
            self.symbols["eq"] = PrimEq()
            self.symbols["print"] = PrimPrint()
            self.symbols["tail"] = PrimTail()
            self.symbols["cat"] = PrimCat()
            self.symbols["head"] = PrimHead()
    
    def child(self) -> Scope:
        return Scope(self)

    def declare(self, symbol: str) -> None:
        if symbol in self.symbols:
            raise Exception(f"redefinition of symbol {symbol!r}")
        
        self.symbols[symbol] = ""

    def get(self, symbol: str) -> any:
        if symbol in self.symbols:
            return self.symbols[symbol]

        if self.parent:
            return self.parent.get(symbol)
        
        raise Exception(f"undefined symbol {symbol!r}")

    def set(self, symbol: str, value: any) -> None:
        assert_str_or_func(value)

        self.get(symbol)

        if symbol in self.symbols:
            self.symbols[symbol] = value
            return

        self.parent.set(symbol, value)

class Func(Debug):
    def __init__(self, name: str, params: list[str], body: Block) -> None:
        self.name = name
        self.params = params
        self.body = body
    
    def eval(self, scope: Scope) -> None:
        scope.declare(self.name)
        scope.set(self.name, self)
    
    def emit_sig(self, ctx: Ctx, include_semi: bool = False) -> None:
        ctx.emit(f"str usr_{self.name}({', '.join(f'str usr_{param}' for param in self.params)}){';' if include_semi else ''}")

    def declare(self, ctx: Ctx) -> None:
        ctx.declare(self.name, Type.FUNC)
        self.emit_sig(ctx, True)

    def check(self, ctx: Ctx, expect: Type | None = None) -> None:
        assert expect == None or expect == Type.FUNC

    def define(self, ctx: Ctx) -> None:
        self.emit_sig(ctx)
        ctx.emit("{")
        self.body.define(ctx)
        ctx.emit('return str_new("");')
        ctx.emit("}")

    def call(self, scope: Scope, this: Expr, args: list[Expr]) -> any:
        child = scope.child()

        child.declare(self.params[0])
        child.set(self.params[0], this.eval(scope))

        for i, param in enumerate(self.params[1:]):
            child.declare(param)
            child.set(param, args[i].eval(scope))

        return self.body.eval(child, False)

class PrimEq(Func):
    def __init__(self) -> None:
        pass

    def call(self, scope: Scope, this: Expr, args: list[Expr]) -> str:
        return "true" if this.eval(scope) == args[0].eval(scope) else "false"

class PrimPrint(Func):
    def __init__(self) -> None:
        pass

    def call(self, scope: Scope, this: Expr, args: list[Expr]) -> None:
        print(this.eval(scope))
    
class PrimTail(Func):
    def __init__(self) -> None:
        pass

    def call(self, scope: Scope, this: Expr, args: list[Expr]) -> str:
        return this.eval(scope)[1:]

class PrimCat(Func):
    def __init__(self) -> None:
        pass

    def call(self, scope: Scope, this: Expr, args: list[Expr]) -> str:
        return this.eval(scope) + args[0].eval(scope)

class PrimHead(Func):
    def __init__(self) -> None:
        pass

    def call(self, scope: Scope, this: Expr, args: list[Expr]) -> str:
        return this.eval(scope)[:-1]

@pg.production("top_levels : top_levels top_level")
def _(ts):
    return ts[0] + [ts[1]]

@pg.production("top_levels : top_level")
def _(ts):
    return [ts[0]]

@pg.production("top_levels : ")
def _(ts):
    return []

@pg.production("top_level : var SEMI")
@pg.production("top_level : func")
@pg.production("top_level : stmt")
def _(ts):
    return ts[0]

@pg.production("func : FUNC IDENT LPAR params RPAR block")
def _(ts):
    return Func(ts[1].getstr(), ts[3], ts[5])

@pg.production("params : params COMMA param")
def _(ts):
    return ts[0] + [ts[2]]

@pg.production("params : param")
def _(ts):
    return [ts[0]]

@pg.production("params : ")
def _(ts):
    return []

@pg.production("param : IDENT")
def _(ts):
    return ts[0].getstr()

@pg.production("block : LCUR stmts RCUR")
def _(ts):
    return Block(ts[1])

class Block(Debug):
    def __init__(self, stmts: list[Stmt]) -> None:
        self.stmts = stmts
    
    def eval(self, scope: Scope, create_scope: bool = True) -> any:
        if create_scope:
            scope = scope.child()

        for stmt in self.stmts:
            res = stmt.eval(scope)
            if res is not None:
                return res

        return ""

    def define(self, ctx: Ctx) -> None:
        for stmt in self.stmts:
            stmt.define(ctx)
        
@pg.production("args : args COMMA arg")
def _(ts):
    return ts[0] + [ts[2]]

@pg.production("args : arg")
def _(ts):
    return [ts[0]]

@pg.production("args : ")
def _(ts):
    return []

@pg.production("arg : expr")
def _(ts):
    return ts[0]

@pg.production("stmts : stmts stmt")
def _(ts):
    return ts[0] + [ts[1]]

@pg.production("stmts : stmt")
def _(ts):
    return [ts[0]]

@pg.production("stmts : ")
def _(ts):
    return []

@pg.production("if : IF expr block")
def _(ts):
    return If(ts[1], ts[2])

class If(Debug):
    def __init__(self, cond: Expr, body: Block) -> None:
        self.cond = cond
        self.body = body
    
    def eval(self, scope: Scope) -> None:
        if self.cond.eval(scope) == "true":
            return self.body.eval(scope)

    def define(self, ctx: Ctx) -> None:
        ctx.emit(f'if (str_eq({self.cond.define(ctx)}, str_new("true")))')
        ctx.emit("{")
        self.body.define(ctx)
        ctx.emit("}")

@pg.production("expr : parexp | call | str | ident")
def _(ts):
    return ts[0]

@pg.production("ident : IDENT")
def _(ts):
    return Ident(ts[0].getstr())

class Ident(Debug):
    def __init__(self, value: str) -> None:
        self.value = value
    
    def eval(self, scope: Scope) -> any:
        var = scope.get(self.value)
        assert_str(var)
        return var

    def define(self, ctx: Ctx) -> str:
        return f"usr_{self.value}"

    def debug_str(self) -> str:
        return self.value

@pg.production("parexp : LPAR expr RPAR")
def _(ts):
    return ts[1]

@pg.production("call : expr DOT IDENT LPAR args RPAR")
def _(ts):
    return Call(ts[0], ts[2].getstr(), ts[4])

class Call(Debug):
    def __init__(self, expr: Expr, func: str, args: list[Expr]) -> None:
        self.expr = expr
        self.func = func
        self.args = args
    
    def eval(self, scope: Scope) -> any:
        func = scope.get(self.func)
        assert_func(func)
        return func.call(scope, self.expr, self.args)

    def declare(self, ctx: Ctx) -> None:
        pass

    def define(self, ctx: Ctx) -> str:
        return f"usr_{self.func}({self.expr.define(ctx)}{', ' if self.args else ''}{', '.join(arg.define(ctx) for arg in self.args)})"

    def check(self, ctx: Ctx, expect: Type | None = None) -> None:
        return expect == Type.STRING

    def assert_str(self) -> None:
        pass

    def debug_str(self) -> str:
        return f"{self.expr.debug_str()}.{self.func}({', '.join(arg.debug_str() for arg in self.args)})"


@pg.production("str : STRING")
def _(ts):
    return String(ts[0].getstr())

class String(Debug):
    def __init__(self, value: str) -> None:
        self.value = eval(value)
    
    def eval(self, scope: Scope) -> str:
        return self.value

    def check(self, ctx: Ctx, expect: Type | None = None) -> None:
        assert expect == Type.STRING

    def define(self, ctx: Ctx) -> str:
        return f"str_new({stringify(self.value)})"

    def assert_str(self) -> None:
        pass

    def debug_str(self) -> str:
        return repr(self.value)

@pg.production("stmt : var SEMI")
@pg.production("stmt : return SEMI")
@pg.production("stmt : if")
@pg.production("stmt : expr SEMI")
def _(ts):
    return ts[0]

@pg.production("return : RETURN expr")
def _(ts):
    return Return(ts[1])

@pg.production("return : RETURN")
def _(ts):
    return Return(None)

class Return(Debug):
    def __init__(self, value: Expr) -> None:
        self.value = value
    
    def eval(self, scope: Scope) -> any:
        if not self.value:
            return ""

        value = self.value.eval(scope)
        assert_str(value)
        return value

    def define(self, ctx: Ctx) -> None:
        ctx.emit(f"return {self.value.define(ctx)};")

@pg.production("var : VAR IDENT EQ expr")
def _(ts):
    return Var(ts[1].getstr(), ts[3])

class Var(Debug):
    def __init__(self, name: str, value: Expr) -> None:
        self.name = name
        self.value = value
    
    def eval(self, scope: Scope) -> None:
        scope.declare(self.name)
        scope.set(self.name, self.value.eval(scope))
    
    def declare(self, ctx: Ctx) -> None:
        ctx.declare(self.name, Type.STRING)

    def define(self, ctx: Ctx) -> None:
        ctx.emit(f"str usr_{self.name};")
        ctx.main.append(f"usr_{self.name} = {self.value.define(ctx)};")

    def check(self, ctx: Ctx, expect: Type | None = None) -> None:
        assert expect == None

        self.value.check(ctx, Type.STRING)

class Expr:
    ...

parser = pg.build()

program = parser.parse(lexer.lex(source))

ctx = program.compile()

ctx.compile("out.exe")
