# Generated from examples/recursive_lists.ctk; compiler namespace supplies bound nodes and safety helpers.
def direct_map(context, arguments, owner, call_node):
    if not can_loop(context, arguments, host):
        return owner.recursion.run(context, arguments, owner, call_node)
    saved_scopes = list(context._scopes)
    arena = Arena()
    callback, output = arguments[1:]
    try:
        items = snapshot(context, arguments, owner, call_node)
        for index in range(len(items)):
            if index:
                context.tick(group)
                context.tick(group)
            bind_scope(context, owner, shape, items, index, arena, callback, output)
            context.tick(body)
            generic_push = False
            for step in push_steps:
                context.tick(step)
            if host_ready(context):
                for step in callback_steps:
                    context.tick(step)
                value = callback_value(context, callback_node, head_node, callback, items[index], host_argument)
                insertable(context, push_node, output, value)
                output.append(value)
                pushed = output
            else:
                pushed = context.host_evaluator(context, push_node)
                generic_push = True
            if observe_push:
                observe(context, push_node, pushed)
            for step in recursive_steps:
                context.tick(step)
            if generic_push:
                remaining = [context.lookup(shape.tail), context.lookup(shape.callback), context.lookup(shape.output)]
                return owner.recursion.run(context, remaining, owner, recursive)
        if items:
            context.tick(group)
        bind_scope(context, owner, shape, items, len(items), arena, callback, output)
        context.push_scope()
        try:
            for step in base_steps:
                context.tick(step)
            if observe_base:
                observe(context, base_value, output)
        finally:
            context.pop_scope()
        return output
    finally:
        context._scopes[:] = saved_scopes
