import dis


def is_simple(fun):
    """A heuristic to find out if a function is simple enough."""
    seen_load_fast_0 = False
    seen_load_response = False
    seen_call_fun = False

    for instruction in dis.get_instructions(fun):
        if instruction.opname == 'LOAD_FAST' and instruction.arg == 0:
            seen_load_fast_0 = True
            continue

        if instruction.opname == 'LOAD_ATTR' and instruction.argval == 'Response':
            seen_load_response = True
            continue

        if instruction.opname.startswith('CALL_FUNCTION'):
            if seen_call_fun:
                return False

            seen_call_fun = True
            continue

    return seen_call_fun and seen_load_fast_0 and seen_load_response
