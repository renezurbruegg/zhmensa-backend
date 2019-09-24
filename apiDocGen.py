from flask_app import server as server
import re

def findDecorators(target):
    import ast, inspect
    res = {}
    def visit_FunctionDef(node):
        res[node.name] = [ast.dump(e) for e in node.decorator_list]

    V = ast.NodeVisitor()
    V.visit_FunctionDef = visit_FunctionDef
    V.visit(compile(inspect.getsource(target), '?', 'exec', ast.PyCF_ONLY_AST))
    return res



def main():
    print("start")
    f = open("api.md", "w")
    pattern = re.compile('\\n    ')

    functions = findDecorators(server)
    for entry in functions:
        isApiRoute = False

        for info in functions[entry]:
            if( "attr='route'" in str(info)):
                isApiRoute = True
                break

        if(isApiRoute):
            function = getattr(server, str(entry))

            doc = function.__doc__
            clean = pattern.sub("\n", doc)
            f.write(clean)
            f.write("***")
            #f.write(function.__doc__)
    f.close()

if __name__ == '__main__':
    main()
