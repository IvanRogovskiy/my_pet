from collections import Counter
def same_items(left, right):
    return Counter(left) == Counter(right)
