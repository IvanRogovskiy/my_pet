# Повторная проверка — ход 2

Исполнитель: преподаватель /root/reliability_roundtrip_writer. Собственный запуск 2026-10-14; точное время в выводе. cwd: /private/tmp/course-reliability-s2a212up/roundtrip_writer.

Сначала восстановлены точка продолжения и предпочтения:

```sh
cat learning/PROGRESS.md learning/NOTES.md
```

Затем прочитаны новая сдача, прежнее задание и относящаяся к ним история:

```sh
cat assignment.md submission.py learning/reviews/08-3-v1-review1.md learning/learning-records/0001-key-scope.md learning/learning-records/0002-body-conflict.md
```

До запуска выбраны повтор прежних четырёх сценариев, повтор после записи другого покупателя и отдельный ключ того же покупателя: последние два проверяют затронутое изменение области ключа. Код загружен через compile/exec без создания pyc. Никаких серверных критериев не добавлено.

## Собственный запуск

```sh
python3 - <<'PY'
import copy
import datetime
import hashlib
import json
import platform
import sys
from pathlib import Path

print('date_utc:', datetime.datetime.now(datetime.timezone.utc).isoformat())
print('python:', sys.version.split()[0])
print('platform:', platform.platform())
for filename in ('assignment.md', 'submission.py'):
    data = Path(filename).read_bytes()
    print(filename + ' sha256:', hashlib.sha256(data).hexdigest())
    if filename == 'submission.py':
        for number, line in enumerate(data.decode().splitlines(), 1):
            print(f'{number}: {line}')
print('assignment_matches_v1_snapshot:', Path('assignment.md').read_bytes() == Path('learning/assignments/08-3-v1.md').read_bytes())
namespace = {}
exec(compile(Path('submission.py').read_text(), 'submission.py', 'exec'), namespace)
submit = namespace['submit']

def report(name, ok, detail):
    print(json.dumps({'case': name, 'status': 'PASS' if ok else 'FAIL', 'detail': detail}, ensure_ascii=False, sort_keys=True))

state = {}
payload = {'item': 'book', 'qty': 1}
first = submit(state, 'alice', 'k1', payload)
report('C1 initial creation', len(state) == 1 and first['payload'] == payload, {'records': len(state), 'result': first})
before = copy.deepcopy(state)
again = submit(state, 'alice', 'k1', dict(payload))
report('C2 same body replay', again == first and state == before, {'records': len(state), 'same_result': again == first, 'state_unchanged': state == before})

state = {}
first = submit(state, 'alice', 'k1', {'item': 'book'})
second = submit(state, 'bob', 'k1', {'item': 'pen'})
report('C1 independent buyer (R1)', len(state) == 2 and second['payload'] == {'item': 'pen'}, {'records': len(state), 'first': first, 'second': second})
before = copy.deepcopy(state)
again = submit(state, 'alice', 'k1', {'item': 'book'})
report('C2 replay after another buyer', again == first and state == before, {'records': len(state), 'same_result': again == first, 'state_unchanged': state == before})
third = submit(state, 'alice', 'k2', {'item': 'pencil'})
report('C1 independent key for same buyer', len(state) == 3 and third['payload'] == {'item': 'pencil'}, {'records': len(state), 'third': third})

state = {}
first = submit(state, 'alice', 'k1', {'item': 'book'})
before = copy.deepcopy(state)
exception = None
returned = None
try:
    returned = submit(state, 'alice', 'k1', {'item': 'pen'})
except Exception as exc:
    exception = type(exc).__name__
report('C2 different body conflict (R2)', exception == 'ValueError', {'exception': exception, 'returned': returned, 'state_unchanged': state == before})
PY
```

Фактический stdout; код завершения 0. FAIL — статус сценария; процесс после всех проверок завершается с кодом 0.

```text
date_utc: 2026-10-14T16:49:16.422307+00:00
python: 3.12.3
platform: macOS-26.6.2-x86_64-i386-64bit
assignment.md sha256: 5b15a8f627c30534701060e04842270dbda6ff4c827dd2af5993f85808e91521
submission.py sha256: 629aa3f460a82aff9ab2cbaeaa11cff7a4c9f967da9ee8eca618f2a1815713df
1: def submit(state, buyer, key, payload):
2:     scoped = (buyer, key)
3:     if scoped in state:
4:         return state[scoped]
5:     result = {'id': len(state)+1, 'payload': dict(payload)}
6:     state[scoped] = result
7:     return result
assignment_matches_v1_snapshot: True
{"case": "C1 initial creation", "detail": {"records": 1, "result": {"id": 1, "payload": {"item": "book", "qty": 1}}}, "status": "PASS"}
{"case": "C2 same body replay", "detail": {"records": 1, "same_result": true, "state_unchanged": true}, "status": "PASS"}
{"case": "C1 independent buyer (R1)", "detail": {"first": {"id": 1, "payload": {"item": "book"}}, "records": 2, "second": {"id": 2, "payload": {"item": "pen"}}}, "status": "PASS"}
{"case": "C2 replay after another buyer", "detail": {"records": 2, "same_result": true, "state_unchanged": true}, "status": "PASS"}
{"case": "C1 independent key for same buyer", "detail": {"records": 3, "third": {"id": 3, "payload": {"item": "pencil"}}}, "status": "PASS"}
{"case": "C2 different body conflict (R2)", "detail": {"exception": null, "returned": {"id": 1, "payload": {"item": "book"}}, "state_unchanged": true}, "status": "FAIL"}
```

Итог: пять сценариев PASS, один FAIL. R1 закрыт по новому собственному запуску. R2 повторно воспроизведён, остаётся открытым. C1 подтверждён; C2 содержит ошибку. Прежняя сдача и ревью сохранены как исторические; новая сдача скопирована дословно в learning/submissions/08-3-v1-revision1.py. assignment.md и submission.py не изменялись. Сеть, Docker, PostgreSQL, commit/push и агенты не использовались.
