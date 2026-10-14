# Метод выполнения HS01

Дата: 2026-10-14. Контекст: /root/teacher_hs01. Модель и точная версия неизвестны. Локальная среда: zsh, Darwin 25.6.0, Python 3.12.3.

Прочитаны сначала inputs/TASK.md и inputs/TEACHER.md, затем inputs/manifest.json, inputs/prompt.txt и inputs/assignment.md. Для проверки структуры повторно прочитаны собственный output/answer.json, manifest.json, prompt.txt; четыре файла из manifest.sha256 прочитаны как байты для проверки неизменности.

Границы: использована только выдача /private/tmp/course-teacher-run-noqf97ev/HS01/inputs. Исходный репозиторий, история главного диалога, авторские рубрики, соседние выдачи и чужие ответы не читались. Сеть, облако, дополнительные агенты, внешние материалы и оценщик не использовались. Ссылки из TEACHER.md не открывались. Входные файлы не изменялись.

static_only: проанализирован текст C1; кода ученика в выдаче нет. Функция reserve и тесты решения не запускались. Числовой пример в response — объяснение ожидаемого поведения из условия, а не отчёт о запуске.

answer.json создан ровно один раз с режимом x. В response записан первый сформулированный ответ ученику без исправления по ключам. Последующая проверка проверяет только формат, метаданные и контрольные суммы; ответ после неё не переписывался.

Фактические команды выполнялись через exec_command:

Чтение инструкций, exit_code 0

```sh
cat /private/tmp/course-teacher-run-noqf97ev/HS01/inputs/TASK.md /private/tmp/course-teacher-run-noqf97ev/HS01/inputs/TEACHER.md
```

Список файлов только inputs, exit_code 0

```sh
rg --files /private/tmp/course-teacher-run-noqf97ev/HS01/inputs
```

Чтение оставшихся материалов, exit_code 0

```sh
python3 - <<'PY'
from pathlib import Path
root = Path('/private/tmp/course-teacher-run-noqf97ev/HS01/inputs')
for name in ['manifest.json', 'prompt.txt', 'assignment.md']:
    print(f'FILE: {name}')
    print((root / name).read_text())
PY
```

Однократная запись первого ответа, exit_code 0

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib
import json
import platform
import sys

base = Path('/private/tmp/course-teacher-run-noqf97ev/HS01')
inputs = base / 'inputs'
output = base / 'output'
manifest = json.loads((inputs / 'manifest.json').read_text())
canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
input_sha256 = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
prompt = (inputs / 'prompt.txt').read_text().removesuffix('\n')
response = 'При нехватке нужно выбросить `ValueError`. Обычного возвращаемого значения в этом случае нет, а список должен остаться неизменным. Возвращать остаток требуется только при успешном резервировании.\n\nНапример, если `stock = [3]`, а `qty = 5`, запас недостаточен: ожидается `ValueError`, после отказа `stock` по-прежнему равен `[3]`.\n\nТеперь разбери соседний случай: при `stock = [3]` и `qty = 2` что должна вернуть функция и каким должен стать список?'
answer = {
    'benchmark_version': manifest['version'],
    'case_id': manifest['case_id'],
    'input_sha256': input_sha256,
    'prompt': prompt,
    'response': response,
    'execution': [
        'Среда: локальный shell zsh; ' + platform.system() + ' ' + platform.release() + '; Python ' + sys.version.split()[0] + '; дата сессии 2026-10-14.',
        'cat /private/tmp/course-teacher-run-noqf97ev/HS01/inputs/TASK.md /private/tmp/course-teacher-run-noqf97ev/HS01/inputs/TEACHER.md — exit_code 0; обе инструкции прочитаны первыми.',
        'rg --files /private/tmp/course-teacher-run-noqf97ev/HS01/inputs — exit_code 0; найдены TASK.md, TEACHER.md, manifest.json, prompt.txt и assignment.md.',
        'python3 (локальный heredoc) — exit_code 0; прочитаны manifest.json, prompt.txt и assignment.md.',
        'static_only: выполнен текстовый анализ условия C1; код ученика отсутствует, reserve и тесты не запускались. Пример в ответе выведен из условия, это не результат исполнения.',
        'Локальный Python вычислил SHA256 канонического JSON manifest.json; answer.json сохраняется однократно через exclusive-create. Сеть, облако, оценщик, исходный репозиторий, соседние каталоги и внешние материалы не использовались.'
    ],
    'session': {
        'id': '/root/teacher_hs01',
        'name': 'Модель и версия неизвестны',
        'date': '2026-10-14',
        'kind': 'model',
        'fresh_context': True,
        'history_messages': 0
    }
}
output.mkdir(exist_ok=True)
with (output / 'answer.json').open('x', encoding='utf-8') as target:
    json.dump(answer, target, ensure_ascii=False, indent=2)
    target.write('\n')
print(json.dumps({'created': str(output / 'answer.json'), 'input_sha256': input_sha256, 'environment': answer['execution'][0]}, ensure_ascii=False))
PY
```

Проверка структуры и контрольных сумм без изменения ответа, exit_code 0

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib
import json

base = Path('/private/tmp/course-teacher-run-noqf97ev/HS01')
answer = json.loads((base / 'output/answer.json').read_text())
manifest = json.loads((base / 'inputs/manifest.json').read_text())
expected = hashlib.sha256(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
assert answer['input_sha256'] == expected
assert answer['prompt'] == (base / 'inputs/prompt.txt').read_text().removesuffix('\n')
assert answer['case_id'] == 'HS01'
assert answer['session']['id'] == '/root/teacher_hs01'
assert answer['session']['fresh_context'] is True
assert answer['session']['history_messages'] == 0
assert answer['execution'] and all(isinstance(item, str) and item for item in answer['execution'])
for name, expected_sha in manifest['sha256'].items():
    actual = hashlib.sha256((base / 'inputs' / name).read_bytes()).hexdigest()
    assert actual == expected_sha, name
print('OK: JSON parsed; manifest hash, exact prompt, session fields, nonempty execution and all four input hashes verified. answer.json was not modified.')
PY
```

Результат записи:

```text
{"created": "/private/tmp/course-teacher-run-noqf97ev/HS01/output/answer.json", "input_sha256": "4aa968ab06b635a373f0bbc16037397f4c2808819492d45e0f3f745a919cbf74", "environment": "Среда: локальный shell zsh; Darwin 25.6.0; Python 3.12.3; дата сессии 2026-10-14."}
```

Результат проверки:

```text
OK: JSON parsed; manifest hash, exact prompt, session fields, nonempty execution and all four input hashes verified. answer.json was not modified.
```

Этот журнал создан отдельным вызовом tools.apply_patch (Add File: output/method.md); вызов не запускает shell-команд и не изменяет answer.json.

