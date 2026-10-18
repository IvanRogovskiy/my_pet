"""Independent, local checks against only the distributed assignment contracts."""
import asyncio
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import importlib.util
import itertools
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
INPUT = OUT.parent / "input"
results = {"environment": {"sys_platform": sys.platform,
                            "python": sys.version,
                            "uid": os.getuid(),
                            "network_docker_cloud": "not used"},
           "cases": {}}


def hashes():
    return {str(p.relative_to(INPUT)): sha256(p.read_bytes()).hexdigest()
            for p in sorted(INPUT.rglob("*")) if p.is_file()}


def load(case_id, filename="submission.py"):
    path = INPUT / case_id / filename
    spec = importlib.util.spec_from_file_location(case_id + filename.replace(".", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def invoke(function, *args):
    try:
        return {"returned": deepcopy(function(*args))}
    except Exception as exc:
        return {"exception": type(exc).__name__, "message": str(exc)}


before_hashes = hashes()
for case_id in ("AD01", "AD02"):
    enqueue = load(case_id).enqueue
    checks = []
    jobs, payload = {}, {"items": [1, 2]}
    source = deepcopy(payload)
    first = deepcopy(enqueue(jobs, "A", "t", payload))
    second = deepcopy(enqueue(jobs, "A", "t", deepcopy(payload)))
    checks.append({"name": "exact repeat and unchanged input",
                   "passed": first == second and len(jobs) == 1 and payload == source,
                   "first": first, "second": second, "records": len(jobs)})
    snapshot = deepcopy(jobs)
    conflict = invoke(enqueue, jobs, "A", "t", {"items": [3]})
    checks.append({"name": "same scope changed body raises without mutation",
                   "passed": conflict.get("exception") == "ValueError" and jobs == snapshot,
                   "observed": conflict})
    jobs = {}
    a = deepcopy(enqueue(jobs, "A", "t", {"items": [1]}))
    b = deepcopy(enqueue(jobs, "B", "t", {"items": [1]}))
    checks.append({"name": "same token different tenant independent ids",
                   "passed": a["id"] != b["id"] and len(jobs) == 2,
                   "A": a, "B": b, "records": len(jobs)})
    jobs = {}
    enqueue(jobs, "A", "t", {"items": [1]})
    other_body = invoke(enqueue, jobs, "B", "t", {"items": [2]})
    checks.append({"name": "other tenant may submit different body",
                   "passed": "returned" in other_body and len(jobs) == 2,
                   "observed": other_body, "records": len(jobs)})
    jobs, payload = {}, {"items": [1]}
    result = enqueue(jobs, "A", "t", payload)
    payload["items"].append(2)
    stored_after = deepcopy(result)
    repeat_original = invoke(enqueue, jobs, "A", "t", {"items": [1]})
    checks.append({"name": "snapshot survives caller mutating source list",
                   "passed": stored_after["payload"] == {"items": [1]}
                             and "returned" in repeat_original,
                   "stored_after": stored_after, "repeat_original": repeat_original})
    jobs = {}
    x = enqueue(jobs, "A", "x", {"b": [2], "a": [1]})
    y = enqueue(jobs, "A", "x", {"a": [1], "b": [2]})
    z = enqueue(jobs, "A", "y", {})
    checks.append({"name": "dict order irrelevant and distinct token unique id",
                   "passed": x == y and x["id"] != z["id"] and len(jobs) == 2})
    results["cases"][case_id] = checks

for case_id in ("AD03", "AD04"):
    allocate = load(case_id).allocate
    examples = []
    for stock, requests in [({"a": 5}, [("a", 3), ("a", 3)]),
                            ({"a": 0, "b": 2}, [("b", 1), ("a", 1)]),
                            ({"a": 5, "b": 2}, [("b", 1), ("a", 2), ("a", 3)]),
                            ({"a": 5}, [])]:
        stock_before, requests_before = deepcopy(stock), deepcopy(requests)
        actual = invoke(allocate, stock, requests)
        examples.append({"stock_before": stock_before, "requests_before": requests_before,
                         "actual": actual, "stock_after": stock, "requests_after": requests})
    count, failures, first_failures = 0, 0, []
    options = [(sku, qty) for sku in ("a", "b") for qty in (1, 2)]
    for a, b in itertools.product(range(4), repeat=2):
        for length in range(4):
            for seq in itertools.product(options, repeat=length):
                stock, requests = {"a": a, "b": b}, list(seq)
                original_stock, original_requests = stock.copy(), requests.copy()
                totals = Counter()
                for sku, qty in requests:
                    totals[sku] += qty
                insufficient = any(totals[sku] > stock[sku] for sku in totals)
                expected_stock = stock.copy() if insufficient else {
                    sku: qty - totals[sku] for sku, qty in stock.items()}
                actual = invoke(allocate, stock, requests)
                passed = (requests == original_requests and stock == expected_stock and
                          (actual.get("exception") == "ValueError" if insufficient else
                           actual.get("returned") == expected_stock))
                count += 1
                if not passed:
                    failures += 1
                    if len(first_failures) < 4:
                        first_failures.append({"stock": original_stock, "requests": original_requests,
                                               "actual": actual, "stock_after": stock,
                                               "requests_after": requests})
    stock = {"a": 2}
    return_identity = allocate(stock, [("a", 1)]) is stock
    results["cases"][case_id] = {"examples": examples, "enumerated": count,
                                 "failures": failures, "first_failures": first_failures,
                                 "returns_stock_object": return_identity}

reserve_module = load("AD05")
sys.modules["submission"] = reserve_module
submitted_test = load("AD05", "test_submission.py")
test_result = invoke(submitted_test.test_overlap)


async def inspect_overlap():
    state, trace = [2], []
    returned = await asyncio.gather(reserve_module.reserve(state, trace),
                                    reserve_module.reserve(state, trace))
    first_write = next(i for i, item in enumerate(trace) if item[0] == "write")
    reads_before_first_write = sum(item == ("read", 2) for item in trace[:first_write])
    return {"state": state, "trace": trace, "returned": returned,
            "reads_of_initial_value_before_first_write": reads_before_first_write,
            "criterion_demonstrated": reads_before_first_write == 2}


results["cases"]["AD05"] = {"submitted_test": test_result,
                             "independent_trace": asyncio.run(inspect_overlap())}
fixture = OUT / "config-fixture.txt"
fixture.write_text(" \n\tconfigured value\t\n ")
local_read = invoke(load("AD06").read_config, fixture)
results["cases"]["AD06"] = {"local_text_and_strip_check": local_read,
                             "local_text_and_strip_passed": local_read.get("returned") == "configured value",
                             "required_linux_uid_10001_current_submission_runtime": "unverified",
                             "reason": "No provided Linux stand. Local check has the host environment above; supplied synthetic log predates source modification and has no source hash."}

page = load("AD07").page
rows = [(11, 1), (10, 2), (10, 1), (10, 3)]
examples = []
for cursor, limit in [(None, 3), ((10, 1), 2), ((10, 2), 5), ((99, 99), 2)]:
    source = rows.copy()
    actual = page(rows, cursor, limit)
    expected = sorted(row for row in rows if cursor is None or row > cursor)[:limit]
    examples.append({"rows": source, "cursor": cursor, "limit": limit,
                     "expected": expected, "actual": actual,
                     "input_unchanged": rows == source, "passed": actual == expected and rows == source})
results["cases"]["AD07"] = examples

same_items = load("AD08").same_items
options = [("a", 0), ("a", 1), ("a", 2), ("b", -1)]
lists = [list(seq) for length in range(4) for seq in itertools.product(options, repeat=length)]
count, failures = 0, 0
for left in lists:
    for right in lists:
        original_left, original_right = deepcopy(left), deepcopy(right)
        actual = same_items(left, right)
        expected = sorted(left) == sorted(right)
        count += 1
        if actual != expected or left != original_left or right != original_right:
            failures += 1
results["cases"]["AD08"] = {"enumerated": count, "failures": failures,
                             "different_multiplicity": same_items([("a", 1)], [("a", 1), ("a", 1)]),
                             "same_quantity_sum_different_pairs": same_items([("a", 2)], [("a", 1), ("a", 1)]),
                             "reordered_equal": same_items([("a", 1), ("b", 2)], [("b", 2), ("a", 1)])}
after_hashes = hashes()
results["input_files_before"] = before_hashes
results["input_files_after"] = after_hashes
results["inputs_unchanged"] = before_hashes == after_hashes
path = OUT / "probe-results.json"
path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(results, ensure_ascii=False, indent=2))
