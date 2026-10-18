import hashlib, json, os, pathlib, platform, sys, threading, time
from fractions import Fraction

bundle_path = pathlib.Path('/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/calibration/input/bundle.json')
raw_bundle = bundle_path.read_bytes()
bundle = json.loads(raw_bundle)
items = {item['id']: item for item in bundle['items']}

def namespace(case, filename='submission.py'):
    ns = {}
    exec(compile(items[case]['files'][filename], case + '/' + filename, 'exec'), ns)
    return ns

def call(fn, *args):
    try:
        value = fn(*args)
        return {'return': value, 'type': type(value).__name__}
    except Exception as exc:
        return {'exception': type(exc).__name__, 'message': str(exc)}

result = {'bundle_sha256': hashlib.sha256(raw_bundle).hexdigest(), 'runtime': {'python': sys.version, 'platform': platform.system(), 'uid': os.getuid()}, 'cases': {}}
f = namespace('P01')['validate']
result['cases']['P01'] = [{'input': repr(value), 'actual': call(f, value)} for value in [True, False, 0, 1, 10**70, '1', 0.1, -1, None]]

f = namespace('P02')['cents']
valid = ['0', '-0.00', '0.01', '1.23', '12.3400', '1e-2', '1e100', '0e-100', '1e+100', '9' * 80, '9' * 77 + '.00', '123456789012345678901234567890.12']
invalid = ['0.001', '1e-100', '-0.01', '-1e100', 'NaN', 'sNaN', 'Infinity', '-Infinity', '', 'abc', '.', '1.2.3']
r = []
for value in valid:
    expected = Fraction(value) * 100
    assert expected.denominator == 1
    actual = call(f, value)
    ok = actual == {'return': expected.numerator, 'type': 'int'}
    assert ok, (value, actual, expected)
    r.append({'input': value, 'expected': expected.numerator, 'actual': actual, 'pass': ok})
for value in invalid:
    actual = call(f, value)
    ok = actual.get('exception') == 'ValueError'
    assert ok, (value, actual)
    r.append({'input': value, 'expected': 'ValueError', 'actual': actual, 'pass': ok})
result['cases']['P02'] = {'count': len(r), 'checks': r}

run = namespace('P03', 'test_submission.py')['run_concurrent_test']
state = {'started': 0, 'active': 0, 'max_active': 0}
lock = threading.Lock()
trace = []
def attempt():
    with lock:
        state['started'] += 1
        number = state['started']
        state['active'] += 1
        state['max_active'] = max(state['max_active'], state['active'])
        trace.append('start' + str(number))
    time.sleep(0.02)
    with lock:
        trace.append('end' + str(number))
        state['active'] -= 1
    return number == 1
result['cases']['P03'] = {'actual': call(run, attempt), 'trace': trace, 'max_active': state['max_active'], 'database_run': False}

f = namespace('P04')['read_secret']
class TextPathDouble:
    def read_text(self):
        return ' \t demo-value \n'
result['cases']['P04'] = {'double_return': call(f, TextPathDouble()), 'real_secret_file_read': False, 'linux_uid10001_run': False}

ns = namespace('P05')
rows = ns['rows']()
# The function body is executed unchanged; its import is satisfied by the supplied callable.
source = items['P05']['files']['test_submission.py'].split('\n', 1)[1]
exec(compile(source, 'P05/test_submission.py', 'exec'), ns)
result['cases']['P05'] = {'rows': rows, 'multiset_matches': sorted(rows) == [(1, 100), (2, 200)], 'test': call(ns['test_rows'])}

f = namespace('P06')['consume']
trace = []
def effect(event_id, payload):
    trace.append(['effect_once', event_id, payload])
def ack():
    trace.append(['ack'])
normal = call(f, {'id': 'evt-1', 'payload': 'p'}, effect, ack)
normal_trace = list(trace)
trace.clear()
def failed_effect(event_id, payload):
    trace.append(['effect_once', event_id, payload])
    raise RuntimeError('fake failure')
failure = call(f, {'id': 'evt-1', 'payload': 'p'}, failed_effect, ack)
result['cases']['P06'] = {'success': normal, 'success_trace': normal_trace, 'failure': failure, 'failure_trace': trace, 'crash_replay_run': False, 'database_broker_run': False}

ready_path = pathlib.Path('P07-ready.json')
ready_path.write_text(items['P07']['files']['ready.json'])
calls = []
def client_check(instance):
    calls.append(instance)
    return 'called'
harness = namespace('P07', 'harness.py')['run']
f = namespace('P07')['check']
class Response:
    def __init__(self, status):
        self.status = status
result['cases']['P07'] = {'harness': call(harness, ready_path, client_check), 'callback_calls': calls, 'status200': call(f, lambda: Response(200)), 'status503': call(f, lambda: Response(503)), 'tcp_tls_run': False}

f = namespace('P08')['debit']
r = []
for balance, amount in [(2, 3), (0, 1), (10, 3), (3, 3)]:
    wallet = {'balance': balance, 'note': 'preserve'}
    before = wallet.copy()
    actual = call(f, wallet, amount)
    r.append({'before': before, 'amount': amount, 'actual': actual, 'after': wallet, 'unchanged': wallet == before})
result['cases']['P08'] = r
pathlib.Path('probe-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
