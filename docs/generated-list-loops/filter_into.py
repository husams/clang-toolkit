# Actual compiler output; bound execution supplies the shared guards.
def direct_filter(context, arguments, owner, call_node):
    if not can_loop(context, arguments, True):
        return owner.recursion.run(context, arguments, owner, call_node)
    with execution(context, arguments, owner, call_node) as loop:
        callback, output = arguments[1:]
        for index, head in enumerate(loop.items):
            loop.enter(index)
            if loop.keep(callback, head):
                if not loop.host_ready():
                    return loop.resume()
                loop.validate(output, head)
                output.append(head)
                loop.pushed(output)
            loop.end_branch()
            loop.advance()
        return loop.finish(output)
