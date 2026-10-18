# Actual scalar specialization for map_list(xs, (x) x * 10)
def plain_map(context, items, output, cancel, observer, plan):
    for index, head in enumerate(items):
        if cancel is not None and cancel():
            cancelled(context, plan.body if index == 0 else plan.shape.group)
        context.steps += 13 if index == 0 else 15
        context.step_count = context.steps
        output.append(head * 10)
        if observer is not None:
            observer.last_tail = 'host'
    if cancel is not None and cancel():
        cancelled(context, plan.shape.group if items else plan.base)
    context.steps += 3 if items else 2
    context.step_count = context.steps
    context.location = context.current_location = (plan.base_value.line, plan.base_value.column)
    if observer is not None:
        observer.last_tail = 'ref'
    return output
