def parse(pattern):
    names = set()
    result = []

    rest = pattern
    while rest:
        exact = ''
        while rest:
            chunk, _, rest = rest.partition('{')
            exact += chunk
            if rest and rest[0] == '{':
                exact += '{{'
                rest = rest[1:]
            else:
                break

        if exact:
            exact = exact.replace('{{', '{').replace('}}', '}')
            result.append(('exact', exact))
        if not rest:
            break

        name, _, rest = rest.partition('}')
        if not _:
            raise ValueError('Unbalanced "{" in pattern')
        if rest and rest[0] != '/':
            raise ValueError('"}" must be followed by "/" or appear at the end')
        if name in names:
            raise ValueError('Duplicate name "{}" in pattern'.format(name))
        names.add(name)
        result.append(('placeholder', name))

    return result
