import dis
import functools
import types

from japronto import helpers


def is_simple(fun):
    """A heuristic to find out if a function is simple enough."""
    seen_load_fast_0 = False
    seen_load_response = False
    seen_call_fun = False

    for instruction in dis.get_instructions(fun):
        if instruction.opname == 'LOAD_FAST' and instruction.arg == 0:
            seen_load_fast_0 = True
            continue

        if instruction.opname == 'LOAD_ATTR' \
           and instruction.argval == 'Response':
            seen_load_response = True
            continue

        if instruction.opname.startswith('CALL_FUNCTION'):
            if seen_call_fun:
                return False

            seen_call_fun = True
            continue

    return seen_call_fun and seen_load_fast_0 and seen_load_response


def is_pointless_coroutine(fun):
    for instruction in dis.get_instructions(fun):
        if instruction.opname in ('GET_AWAITABLE', 'YIELD_FROM'):
            return False

    return True


def coroutine_to_func(f):
    # Based on http://stackoverflow.com/questions/13503079/
    # how-to-create-a-copy-of-a-python-function
    oc = f.__code__
    code = helpers.dismiss_coroutine(oc)
    g = types.FunctionType(
        code, f.__globals__, name=f.__name__, argdefs=f.__defaults__,
        closure=f.__closure__)
    g = functools.update_wrapper(g, f)
    g.__kwdefaults__ = f.__kwdefaults__

    return g
