from random import randint
from contextlib import contextmanager


@contextmanager
def peida_ao_sair():
    try:
        yield
    finally:
        print("peidei")


with peida_ao_sair():
    print("ola torugo")
    if randint(0, 100) > 50:
        raise Exception("caguei nas calças")
