from pathlib import Path
from fractions import Fraction
from copy import deepcopy
import contextlib
import decimal
import io
import json
import os
import platform
import sys
import traceback
import types

BASE = Path.cwd()
records = []

def emit(record):
    records.append(record)
    print(json.dumps(record, ensure_ascii=False))

def load(case):
    path = BASE / 'input' / case / 'submission.py'
    module = types.ModuleType('submission')
    exec(compile(path.read_text(), str(path), 'exec'), module.__dict__)
    return module

def outcome(fn, *args):
    try:
        value = fn(*args)
        return {'return': value, 'type': type(value).__name__}
    except Exception as exc:
        return {'exception': type(exc).__name__, 'message': str(exc)}

emit({'environment': {'python': sys.version, 'platform': platform.platform(), 'uid': os.getuid(), 'decimal_precision': decimal.getcontext().prec}, 'execution': 'local Python; no network, Docker, PostgreSQL, broker or author tests'})

for case in ('HC01', 'HC02'):
    fn = load(case).can_edit
    ids = ['', 'a', 'ab', 'b', 'team-1', 'team-10', 'команда']
    failures = []
    count = 0
    for role in ('editor', 'admin'):
        for actor_id in ids:
            for document_id in ids:
                actor = {'role': role, 'team_id': actor_id}
                document = {'team_id': document_id}
                actual = outcome(fn, actor, document)
                expected = role == 'admin' or actor_id == document_id
                count += 1
                if actual != {'return': expected, 'type': 'bool'}:
                    failures.append({'actor': actor, 'document': document, 'expected': expected, 'actual': actual})
    emit({'case': case, 'check': 'both declared roles and seven string team IDs', 'count': count, 'failures': failures})

for case in ('HC03', 'HC04'):
    fn = load(case).debit
    failures = []
    count = 0
    success_count = 0
    insufficient_count = 0
    for balance in range(11):
        for amount in range(1, 13):
            wallet = {'balance': balance, 'tag': 'preserve'}
            before = deepcopy(wallet)
            actual = outcome(fn, wallet, amount)
            count += 1
            if amount > balance:
                insufficient_count += 1
                ok = actual.get('exception') == 'ValueError' and wallet == before
                expected = {'exception': 'ValueError', 'wallet': before}
            else:
                success_count += 1
                expected_wallet = {'balance': balance - amount, 'tag': 'preserve'}
                ok = 'exception' not in actual and wallet == expected_wallet
                expected = {'wallet': expected_wallet}
            if not ok:
                failures.append({'balance': balance, 'amount': amount, 'expected': expected, 'actual': actual, 'wallet_after': deepcopy(wallet)})
    emit({'case': case, 'check': 'positive integer amounts, exact balance boundary, unchanged wallet after insufficient funds', 'count': count, 'success_inputs': success_count, 'insufficient_inputs': insufficient_count, 'failure_count': len(failures), 'first_failures': failures[:3]})

valid_numeric = [
    '0', '-0', '0.00', '0.01', '1', '1.23', '10.00', '999.99', '1e2', '1e-2',
    '123e-2', '0e-100', '1e100', '1.01e+100', '1234567890123456789012345678.91',
    '9' * 77 + '.99', '9' * 79, '1.001', '0.001', '1e-100', '1e-3', '-0.01',
    '123456789012345678901234567890.001', '2.345e1', '2.345e2',
]
invalid_numeric = ['', 'abc', 'NaN', 'sNaN', 'Infinity', '-Infinity', '-', '1e', '1,23']
for case in ('HC05', 'HC06'):
    fn = load(case).cents
    cases = []
    for raw in valid_numeric:
        assert len(raw) <= 80
        number = Fraction(raw)
        cents = number * 100
        expected = {'return': int(cents), 'type': 'int'} if number >= 0 and cents.denominator == 1 else {'exception': 'ValueError'}
        cases.append((raw, expected))
    cases.extend((raw, {'exception': 'ValueError'}) for raw in invalid_numeric)
    failures = []
    for raw, expected in cases:
        actual = outcome(fn, raw)
        ok = actual.get('exception') == 'ValueError' if expected.get('exception') else actual == expected
        if not ok:
            failures.append({'raw': raw, 'expected': expected, 'actual': actual})
    emit({'case': case, 'check': 'exact Fraction oracle for declared decimals, cent divisibility, exponent limits, 80-character input, nonfinite and malformed strings', 'count': len(cases), 'failures': failures})

for case in ('HC07', 'HC08'):
    fn = load(case).remember
    results = []
    cache = {}
    body = {'a': '1', 'b': '2'}
    saved = fn(cache, 'tenant-a', 'token', body)
    results.append({'scenario': 'first call leaves body unchanged', 'passed': body == {'a': '1', 'b': '2'}, 'result': deepcopy(saved)})
    same = {'b': '2', 'a': '1'}
    same_before = deepcopy(same)
    replay = outcome(fn, cache, 'tenant-a', 'token', same)
    results.append({'scenario': 'equal body with different key order returns saved result', 'passed': replay.get('return') == saved and same == same_before, 'actual': deepcopy(replay)})
    for changed in ({'a': 'changed', 'b': '2'}, {'a': '1'}, {'a': '1', 'b': '2', 'c': '3'}):
        cache_before = deepcopy(cache)
        changed_before = deepcopy(changed)
        actual = outcome(fn, cache, 'tenant-a', 'token', changed)
        results.append({'scenario': 'different body conflicts', 'body': changed_before, 'passed': actual.get('exception') == 'ValueError' and changed == changed_before and cache == cache_before, 'actual': deepcopy(actual)})
    other_body = {'a': 'changed', 'b': '2'}
    other = outcome(fn, cache, 'tenant-b', 'token', other_body)
    results.append({'scenario': 'tenant isolation', 'passed': other.get('return', {}).get('body') == other_body and cache[('tenant-a', 'token')] == saved, 'actual': deepcopy(other)})
    token_body = {'a': 'new-token'}
    another = outcome(fn, cache, 'tenant-a', 'another-token', token_body)
    results.append({'scenario': 'token isolation', 'passed': another.get('return', {}).get('body') == token_body, 'actual': deepcopy(another)})
    body['a'] = 'caller changed later'
    results.append({'scenario': 'stored body copied from original input', 'passed': saved['body'] == {'a': '1', 'b': '2'}})
    empty_cache = {}
    empty_first = fn(empty_cache, 'tenant-a', 'empty', {})
    empty_second = fn(empty_cache, 'tenant-a', 'empty', {})
    results.append({'scenario': 'empty dictionary replay', 'passed': empty_first == empty_second})
    emit({'case': case, 'check': 'idempotent replay, conflicts, isolation and input dictionary preservation', 'count': len(results), 'failure_count': sum(not item['passed'] for item in results), 'results': results})

module = load('HC09')
actual = module.pairs()
emit({'case': 'HC09', 'check': 'implementation matches pairs independent of order and including multiplicity', 'actual': actual, 'expected_unordered': [('a', 2), ('b', 3)], 'passed': sorted(actual) == [('a', 2), ('b', 3)]})
sys.modules['submission'] = module
test_path = BASE / 'input' / 'HC09' / 'test_submission.py'
test_namespace = {}
exec(compile(test_path.read_text(), str(test_path), 'exec'), test_namespace)
try:
    test_namespace['test_pairs']()
    test_result = {'passed': True}
except Exception as exc:
    frames = traceback.extract_tb(exc.__traceback__)
    test_result = {'passed': False, 'exception': type(exc).__name__, 'location': [{'file': str(Path(frame.filename).relative_to(BASE)), 'line': frame.lineno, 'source': frame.line} for frame in frames if str(frame.filename).startswith(str(BASE / 'input'))]}
emit({'case': 'HC09', 'check': 'execute explicitly supplied student test (not an author test)', 'result': test_result})

fn = load('HC10').read_secret
fixture = BASE / 'output' / 'synthetic-text.txt'
text_samples = ['  example\n', '\n\t пример \t\n', '', ' \t\n', 'a b\nc']
results = []
for contents in text_samples:
    fixture.write_text(contents)
    actual = outcome(fn, fixture)
    results.append({'input': contents, 'actual': actual, 'passed': actual == {'return': contents.strip(), 'type': 'str'}})
fixture.unlink()
emit({'case': 'HC10', 'check': 'local synthetic text fixture only; not Linux application UID 10001 verification', 'uid': os.getuid(), 'count': len(results), 'results': results, 'required_deployment_check': 'unverified; no supplied Linux stand; Docker forbidden and not attempted'})

fn = load('HC11').label
results = []
for value in ['name', ' name ', ' ', '\t\n', 'пример', '', None, 0, 1, False, [], {}, b'text']:
    expected = {'return': value, 'type': 'str'} if isinstance(value, str) and value else {'exception': 'ValueError'}
    actual = outcome(fn, value)
    ok = actual.get('exception') == 'ValueError' if expected.get('exception') else actual == expected
    results.append({'input_repr': repr(value), 'expected': expected, 'actual': actual, 'passed': ok})
emit({'case': 'HC11', 'check': 'v1 only, including nonempty whitespace strings and preservation of surrounding spaces', 'count': len(results), 'results': results})

fn = load('HC12').consume
calls = []
event = {'id': 'event-1', 'payload': {'amount': '10'}}
def effect(event_id, payload):
    calls.append(['effect_once', event_id, payload])
def ack():
    calls.append(['ack'])
actual = outcome(fn, event, effect, ack)
emit({'case': 'HC12', 'check': 'local fake records normal call order only', 'actual': actual, 'calls': deepcopy(calls), 'passed': [item[0] for item in calls] == ['effect_once', 'ack']})
calls.clear()
def fail_effect(event_id, payload):
    calls.append(['effect_once', event_id, payload])
    raise RuntimeError('synthetic effect failure')
actual = outcome(fn, event, fail_effect, ack)
emit({'case': 'HC12', 'check': 'local fake effect exception prevents ack', 'actual': actual, 'calls': deepcopy(calls), 'passed': actual.get('exception') == 'RuntimeError' and [item[0] for item in calls] == ['effect_once'], 'required_crash_replay_check': 'unverified; no real DB or broker started; this fake is not durability evidence'})

emit({'summary': 'all twelve submissions examined and locally invoked; HC09 supplied test invoked; HC10 Linux UID check and HC12 real DB/broker crash/replay remain unverified'})
