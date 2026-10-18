# Actual compiler output; bound execution supplies the shared guards.
def direct_reverse(context, arguments, owner, call_node):
    if not can_loop(context, arguments, True, True):
        return owner.recursion.run(context, arguments, owner, call_node)
    with execution(context, arguments, owner, call_node) as loop:
        for index in range(len(loop.items)):
            loop.descend(index)
        output = loop.finish([])
        for index in range(len(loop.items) - 1, -1, -1):
            head = loop.items[index]
            loop.unwind(index, output)
            if loop.host_ready():
                loop.validate(output, head)
                output.append(head)
                loop.pushed(output)
            else:
                loop.host_push()
            output = loop.result()
        return output
