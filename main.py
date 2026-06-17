from minic.lexer import tokenize
from minic.parser import Parser
from pprint import pprint


def main():
    with open("main.c") as f:
        text = f.read()
        tokens = tokenize(text)
        pprint(tokens)
        parser = Parser(text, tokens)
        pprint(parser.parse())
        parser.print_diagnostics()


main()
