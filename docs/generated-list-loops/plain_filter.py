# Actual chunked scalar specialization for filter_list(xs, (x) x % 2 == 0)
def plain_filter(context, items, output, cancel, observer, plan):
    pending = iter(items)
    for start in range(0, len(items), 128):
        if cancel is not None and cancel():
            cancelled(context, plan.body if start == 0 else plan.shape.group)
        count = min(128, len(items) - start)
        before = len(output)
        for head in islice(pending, 128):
            keep = (head % 2 if head >= 0 else -(-head % 2)) == 0
            if keep:
                output.append(head)
        context.steps += count * 17 + (len(output) - before) * 3 - (2 if start == 0 else 0)
        context.step_count = context.steps
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
