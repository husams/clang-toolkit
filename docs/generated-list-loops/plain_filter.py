# Actual plain kernel for filter_list(xs, (x) x % 2 == 0)
def plain_filter(items, output):
    keep = False
    for head in items:
        keep = (head % 2 if head >= 0 else -(-head % 2)) == 0
        if keep:
            output.append(head)
    return keep
