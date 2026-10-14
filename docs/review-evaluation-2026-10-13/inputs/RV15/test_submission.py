from concurrent.futures import ThreadPoolExecutor

def run_concurrent_test(attempt):
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(attempt).result(timeout=2)
        second = pool.submit(attempt).result(timeout=2)
    assert sorted([first, second]) == [False, True]
    return [first, second]
