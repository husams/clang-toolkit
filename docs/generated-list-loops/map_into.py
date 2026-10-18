# Actual generated dispatcher; bound namespace supplies invocation guards.
def direct_map(context, arguments, owner, call_node):
    if not can_loop(context, arguments, True):
        return owner.recursion.run(context, arguments, owner, call_node)
    with execution(context, arguments, owner, call_node) as loop:
        plain = prepare_plain(loop)
        if plain is not None:
            return plain[0](*plain[1])
        callback, output = arguments[1:]
        for index, head in enumerate(loop.items):
            loop.enter(index)
            if not loop.host_ready():
                return loop.resume()
            value = loop.map_value(callback, head)
            loop.validate(output, value)
            output.append(value)
            loop.pushed(output)
            loop.advance()
        return loop.finish(output)
