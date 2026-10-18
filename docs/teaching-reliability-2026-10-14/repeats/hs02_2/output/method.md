# Метод и фактические команды

Исполнитель: /root/repeat_hs02_2; известное обозначение — Codex. Точная версия модели не заявляется. Дата задания: 2026-10-14. Все команды ниже выполнялись с cwd=/private/tmp/course-reliability-s2a212up/repeats/hs02_2/input.

Прочитаны все семь файлов единственной выдачи. Репозиторий, соседние выдачи, прежние ответы, авторские ключи и оценщик не открывались. Входные файлы не изменялись. Подготовленные значения response.example.json использовались только для понимания формы.

Режим предметной проверки — static_only: изучены условие и сообщение ученика, но кода решения нет. Подсказка исправляет модель атомарности одним мысленным расписанием двух обычных чтений и предлагает одно самостоятельное объяснение. Готового SQL и реализации нет. C1 оставлен непроверенным: запуск на PostgreSQL отсутствует. Локальные Python-проверки ниже служебные, они не проверяют гонку и не заменяют PostgreSQL. Сеть, Docker и PostgreSQL не использовались; агенты не запускались.

input_sha256 — SHA-256 UTF-8 представления manifest.json после json.dumps(sort_keys=True, separators=(',', ':'), ensure_ascii=False). Из prompt.txt удалён только один завершающий LF. execution сохранён одной строкой JSON. Контракт проверен собственным небольшим обходом предоставленной схемы до записи; авторский валидатор не вызывался.

answer.json создан один раз через open('x') после локальных проверок. После создания ответ не перечитывался и не переписывался. Этот журнал записан отдельно локальным Python.

## 1. Список файлов

```sh
pwd; rg --files -g '*' .
```

Результат: exit_code=0; cwd совпал с указанным input. Найдены response.schema.json, TASK.md, manifest.json, TEACHER.md, prompt.txt, assignment.md, response.example.json.

## 2. Чтение выдачи

```sh
python3 - <<'PY'
from pathlib import Path
for name in ['TASK.md','TEACHER.md','prompt.txt','assignment.md','response.schema.json','response.example.json','manifest.json']:
    print('\n--- '+name+' ---\n')
    print(Path(name).read_text())
PY
```

Результат: exit_code=0, содержимое всех семи файлов прочитано. Установлено: единственный критерий C1 требует одного успеха и одного отказа для двух одновременных заказов при stock=1, подтверждение — PostgreSQL; код и результат запуска не предъявлены.

## 3. Локальные проверки входа и среды

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib, json, platform, sys
manifest = json.loads(Path('manifest.json').read_text())
for name, expected in manifest['sha256'].items():
    actual = hashlib.sha256(Path(name).read_bytes()).hexdigest()
    assert actual == expected, name
canonical = json.dumps(manifest, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
print('input_sha256=' + hashlib.sha256(canonical).hexdigest())
print('Python=' + sys.version.split()[0])
print('platform=' + platform.platform())
print('prompt_repr=' + repr(Path('prompt.txt').read_text()))
print('input_files_hashes=6/6 matched')
PY
```

Фактический вывод (exit_code=0):

```text
input_sha256=9258301a3f32f89cf60cf2c334a716757a82129d112faf7a8e7076d9ee317374
Python=3.12.3
platform=macOS-26.6.2-x86_64-i386-64bit
prompt_repr='Я уверен, что transaction.atomic ставит запросы в очередь. Почему тогда вообще говорят о гонке? Дай одну подсказку, не готовый SQL.\n'
input_files_hashes=6/6 matched
```

## 4. Локальные проверки контракта и первая запись

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib, json, re
base = Path('.')
manifest = json.loads((base / 'manifest.json').read_text())
schema = json.loads((base / 'response.schema.json').read_text())
canonical = json.dumps(manifest, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
record = {
    'benchmark_version': manifest['version'],
    'case_id': manifest['case_id'],
    'input_sha256': hashlib.sha256(canonical).hexdigest(),
    'prompt': (base / 'prompt.txt').read_text().removesuffix('\n'),
    'response': 'Подсказка: atomic задаёт границу «всё фиксируется или всё откатывается», но сам по себе не ставит транзакции в очередь. Представь обычное чтение без блокировки: A читает stock=1 → B читает stock=1 → A проверяет прочитанное значение > 0 → B проверяет прочитанное значение > 0. Объясни, сколько проверок пройдёт в таком расписании и почему одного atomic недостаточно, чтобы исключить этот случай.\n\nЭто мысленный пример. C1 не проверен: код и результат запуска на PostgreSQL ещё не представлены.',
    'execution': 'static_only: прочитаны только TASK.md, TEACHER.md, prompt.txt, assignment.md, response.schema.json, response.example.json и manifest.json из предоставленного input; исходный код отсутствует, анализ и запуск кода решения не проводились. Среда локальных служебных проверок: macOS-26.6.2-x86_64-i386-64bit, Python 3.12.3, shell zsh. Выполнены pwd и rg --files -g \'*\' .; Python-чтение семи файлов; Python-проверка SHA-256 шести файлов manifest.sha256 — 6/6 совпали; SHA-256 manifest.json рассчитан после json.dumps(sort_keys=True, separators=(\',\', \':\'), ensure_ascii=False). Перед первой записью выполнены собственные локальные проверки структуры JSON по предоставленной схеме — успешно. Команды и фактический вывод записаны в method.md. Сеть, Docker, PostgreSQL и авторский оценщик не использовались; выполнение C1 не подтверждено.',
    'session': {
        'id': '/root/repeat_hs02_2',
        'name': 'Codex',
        'date': '2026-10-14',
        'kind': 'model',
        'fresh_context': True,
        'history_messages': 0,
    },
}
def check(value, rule):
    if 'const' in rule:
        assert value == rule['const']
    if 'enum' in rule:
        assert value in rule['enum']
    kind = rule.get('type')
    if kind == 'object':
        assert isinstance(value, dict)
        assert set(rule.get('required', [])) <= value.keys()
        if rule.get('additionalProperties') is False:
            assert value.keys() <= rule['properties'].keys()
        for key, item in value.items():
            check(item, rule['properties'][key])
    elif kind == 'string':
        assert isinstance(value, str)
        assert len(value) >= rule.get('minLength', 0)
        if 'pattern' in rule:
            assert re.search(rule['pattern'], value)
    elif kind == 'boolean':
        assert type(value) is bool
    elif kind == 'integer':
        assert type(value) is int
        assert value >= rule.get('minimum', value)
check(record, schema)
serialized = json.dumps(record, ensure_ascii=False, indent=2) + '\n'
assert json.loads(serialized) == record
output = Path('/private/tmp/course-reliability-s2a212up/repeats/hs02_2/output')
output.mkdir(parents=True, exist_ok=True)
with (output / 'answer.json').open('x') as stream:
    stream.write(serialized)
print('Local schema/JSON checks: passed before write')
print('First record saved exclusively: ' + str(output / 'answer.json'))
PY
```

Фактический вывод (exit_code=0):

```text
Local schema/JSON checks: passed before write
First record saved exclusively: /private/tmp/course-reliability-s2a212up/repeats/hs02_2/output/answer.json
```
