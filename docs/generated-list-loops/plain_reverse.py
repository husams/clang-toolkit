# Actual scalar specialization for reverse_list(xs)
def plain_reverse(context, items, output, cancel, observer, plan):
    if cancel is not None and cancel():
        cancelled(context, plan.body if items else plan.base)
    context.steps += len(items) * 7 + (1 if items else 2)
    context.step_count = context.steps
    context.consume_depth += len(items) * 1
    output = []
    if observer is not None:
        observer.last_tail = 'list'
    for head in reversed(items):
        context.consume_depth -= 1
        if observer is not None:
            observer.last_tail = 'let'
        if cancel is not None and cancel():
            cancelled(context, plan.shape.push)
        context.steps += 4
        context.step_count = context.steps
        output.append(head)
        if observer is not None:
            observer.last_tail = 'ref'
    final = plan.final if items else plan.base_value
    context.location = context.current_location = (final.line, final.column)
    return output
