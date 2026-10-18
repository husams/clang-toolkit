# Actual scalar specialization for filter_list(xs, (x) x % 2 == 0)
def plain_filter(context, items, output, cancel, observer, plan):
    for index, head in enumerate(items):
        if cancel is not None and cancel():
            cancelled(context, plan.body if index == 0 else plan.shape.group)
        keep = (head % 2 if head >= 0 else -(-head % 2)) == 0
        context.steps += (18 if keep else 15) + (2 if index else 0)
        context.step_count = context.steps
        if keep:
            output.append(head)
        if observer is not None:
            observer.last_tail = 'host' if keep else 'binary'
    if cancel is not None and cancel():
        cancelled(context, plan.shape.group if items else plan.base)
    context.steps += 3 if items else 2
    context.step_count = context.steps
    context.location = context.current_location = (plan.base_value.line, plan.base_value.column)
    if observer is not None:
        observer.last_tail = 'ref'
    return output
