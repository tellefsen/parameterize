import ast
import astor
import copy
import inspect
import random


class _Param:

    def __init__(self, min_val, max_val):
        self.__min_val = min_val
        self.__max_val = max_val

    @property
    def min(self):
        return self.__min_val

    @property
    def max(self):
        return self.__max_val

    def random(self):
        return random.randint(self.__min_val, self.__max_val)


class Discrete(_Param):

    def __init__(self, *choices):
        self.num_choices = len(choices)
        super(Discrete, self).__init__(0, self.num_choices - 1)

    def __repr__(self):
        return f"Discrete({self.num_choices})"


class Interval(_Param):

    def __init__(self, min_val, max_val):
        super(Interval, self).__init__(min_val, max_val)

    def __repr__(self):
        return f"Interval({self.min}, {self.max})"


class Bool(_Param):

    def __init__(self):
        super(Bool, self).__init__(0, 1)

    def __repr__(self):
        return f"Bool()"


class ParamTransformer(ast.NodeTransformer):

    def __init__(self, params):
        self.params = params
        self.param_idx = 0

    def next_param(self):
        param = self.params[self.param_idx]
        self.param_idx += 1
        return param

    def handle_interval(self, node):
        return ast.Num(n=self.next_param())

    def handle_discrete(self, node):
        return node.args[self.next_param()]

    def handle_bool(self, node):
        return ast.Num(n=self.next_param())

    def visit_Call(self, node):
        self.generic_visit(node)
        if (type(node.func) == ast.Name and node.func.id == Interval.__name__):
            return self.handle_interval(node)
        if (type(node.func) == ast.Name and node.func.id == Discrete.__name__):
            return self.handle_discrete(node)
        if (type(node.func) == ast.Name and node.func.id == Bool.__name__):
            return self.handle_bool(node)
        return node


class ParamExtractor(ast.NodeVisitor):

    def __init__(self):
        self.params = []

    def handle_interval(self, node):
        min_val = node.args[0].n
        max_val = node.args[1].n
        param = Interval(min_val, max_val)
        self.params.append(param)

    def handle_discrete(self, node):
        choices = node.args
        param = Discrete(*choices)
        self.params.append(param)

    def handle_bool(self, node):
        param = Bool()
        self.params.append(param)

    def visit_Call(self, node):
        self.generic_visit(node)
        if (type(node.func) == ast.Name and node.func.id == Interval.__name__):
            self.handle_interval(node)
        if (type(node.func) == ast.Name and node.func.id == Discrete.__name__):
            self.handle_discrete(node)
        if (type(node.func) == ast.Name and node.func.id == Bool.__name__):
            self.handle_bool(node)


class Parameterizer:

    def __init__(self, func):
        src = inspect.getsource(func)
        tree = ast.parse(src)
        visitor = ParamExtractor()
        visitor.generic_visit(tree)
        self.__tree = tree
        self.__params = visitor.params
        self.__func = func

    def __rewrite_tree(self, params):
        tree = copy.deepcopy(self.__tree)
        transformer = ParamTransformer(params)
        transformer.generic_visit(tree)
        ast.fix_missing_locations(tree)
        return tree

    def random_params(self):
        return [param.random() for param in self.__params]

    def get_params(self):
        return self.__params

    def get_parameterized_function(self, params, globals_={}, locals_={}):
        tree = self.__rewrite_tree(params)
        code = compile(tree, filename="<ast>", mode="exec")
        exec(code, globals_, locals_)
        return eval(self.__func.__name__, globals_, locals_)

    def get_parameterized_function_code(self, params):
        tree = self.__rewrite_tree(params)
        return astor.to_source(tree)
