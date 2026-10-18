# Actual plain kernel for map_list(xs, (x) x * 10)
def plain_map(items, output):
    for head in items:
        output.append(head * 10)
