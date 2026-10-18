# Generated from examples/recursive_lists.ctk; compiler namespace supplies bound nodes and safety helpers.
def direct_reverse(context, arguments, owner, call_node):
    if not can_loop(context, arguments, host, True):
        return owner.recursion.run(context, arguments, owner, call_node)
    saved_scopes = list(context._scopes)
    saved_depth = context.consume_depth
    arena = Arena()
    try:
        items = snapshot(context, arguments, owner, call_node)
        for index in range(len(items)):
            if index:
                context.tick(group)
                context.tick(group)
            bind_scope(context, owner, shape, items, index, arena, None, None)
            for step in descent_steps:
                context.tick(step)
            context.consume_depth += consumed
            for step in recursive_steps:
                context.tick(step)
            if index >= context.max_items:
                raise error(context, recursive, 'continuation stack exceeds item limit', LimitError)
        if items:
            context.tick(group)
        bind_scope(context, owner, shape, items, len(items), arena, None, None)
        context.push_scope()
        try:
            context.tick(base_block)
            context.tick(base_value)
            output = []
            if observe_base:
                observe(context, base_value, output)
        finally:
            context.pop_scope()
        for index in range(len(items) - 1, -1, -1):
            context.consume_depth -= consumed
            bind_scope(context, owner, shape, items, index, arena, None, None)
            context.define(result_name, output)
            if observe_assignment:
                observe(context, assignment, output)
            for step in push_steps:
                context.tick(step)
            if host_ready(context):
                for step in push_argument_steps:
                    context.tick(step)
                insertable(context, push_node, output, items[index])
                output.append(items[index])
                pushed = output
            else:
                pushed = context.host_evaluator(context, push_node)
            if observe_push:
                observe(context, push_node, pushed)
            context.tick(final)
            output = context.lookup(result_name)
            if observe_final:
                observe(context, final, output)
        return output
    finally:
        context.consume_depth = saved_depth
        context._scopes[:] = saved_scopes
