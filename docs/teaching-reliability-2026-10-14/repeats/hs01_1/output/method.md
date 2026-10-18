# Метод

Первый ответ преподавателя в отдельном контексте /root/repeat_hs01_1. Обозначение исполнителя: Codex; точная версия модели не заявляется. Содержательной предыстории ученика нет; fresh_context=true, history_messages=0.

Прочитаны только файлы заданной input-выдачи. TEACHER.md использован как предоставленная инструкция, внешние ссылки из него не открывались. Ученик не понимает условие отказа: дан один разбор входа, исключения и неизменности списка, затем один соседний случай для самостоятельного ответа. Реализация не дана. Это static_only анализ контракта, а не запуск reserve. Личные учебные записи не создавались.

Собственные локальные Python-проверки: проверка 6 входных хешей и вычисление хеша канонического manifest.json; перед записью — проверка структуры JSON в памяти по предоставленной схеме. Авторский оценщик или валидатор не запускался. После первой записи answer.json не исправлялся. Один предварительный вызов functions.exec вернул SyntaxError: Invalid or unexpected token при разборе JavaScript; shell не был запущен, файлы не создавались.

## Реальные команды

~~~sh
rg --files -g '*' /private/tmp/course-reliability-s2a212up/repeats/hs01_1/input
~~~

~~~sh
python3 - <<'PY'
from pathlib import Path
root=Path('/private/tmp/course-reliability-s2a212up/repeats/hs01_1/input')
for name in ['TASK.md','TEACHER.md','response.schema.json','manifest.json','prompt.txt','assignment.md','response.example.json']:
    print('\nFILE:', name)
    print((root/name).read_text())
PY
~~~

~~~sh
python3 - <<'PY'
import hashlib, json, platform, sys
from pathlib import Path
root = Path('/private/tmp/course-reliability-s2a212up/repeats/hs01_1/input')
manifest = json.loads((root/'manifest.json').read_text())
canonical = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
print('input_sha256=' + hashlib.sha256(canonical).hexdigest())
print('environment=' + platform.system() + ' ' + platform.release() + '; Python ' + sys.version.split()[0])
for name, expected in manifest['sha256'].items():
    actual = hashlib.sha256((root/name).read_bytes()).hexdigest()
    assert actual == expected, name
print('Local Python check: all 6 bundled file hashes match manifest.sha256.')
print('prompt_repr=' + repr((root/'prompt.txt').read_text()))
PY
~~~

Команда первой записи (аргументы текущего процесса):

~~~sh
/usr/local/Cellar/python@3.12/3.12.3/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/Contents/MacOS/Python -c 'import hashlib, json, shlex, sys
from pathlib import Path
root = Path('"'"'/private/tmp/course-reliability-s2a212up/repeats/hs01_1/input'"'"')
out = Path('"'"'/private/tmp/course-reliability-s2a212up/repeats/hs01_1/output'"'"')
prior_commands = json.loads("[\"rg --files -g '"'"'*'"'"' /private/tmp/course-reliability-s2a212up/repeats/hs01_1/input\",\"python3 - <<'"'"'PY'"'"'\\nfrom pathlib import Path\\nroot=Path('"'"'/private/tmp/course-reliability-s2a212up/repeats/hs01_1/input'"'"')\\nfor name in ['"'"'TASK.md'"'"','"'"'TEACHER.md'"'"','"'"'response.schema.json'"'"','"'"'manifest.json'"'"','"'"'prompt.txt'"'"','"'"'assignment.md'"'"','"'"'response.example.json'"'"']:\\n    print('"'"'\\\\nFILE:'"'"', name)\\n    print((root/name).read_text())\\nPY\",\"python3 - <<'"'"'PY'"'"'\\nimport hashlib, json, platform, sys\\nfrom pathlib import Path\\nroot = Path('"'"'/private/tmp/course-reliability-s2a212up/repeats/hs01_1/input'"'"')\\nmanifest = json.loads((root/'"'"'manifest.json'"'"').read_text())\\ncanonical = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=('"'"','"'"', '"'"':'"'"')).encode('"'"'utf-8'"'"')\\nprint('"'"'input_sha256='"'"' + hashlib.sha256(canonical).hexdigest())\\nprint('"'"'environment='"'"' + platform.system() + '"'"' '"'"' + platform.release() + '"'"'; Python '"'"' + sys.version.split()[0])\\nfor name, expected in manifest['"'"'sha256'"'"'].items():\\n    actual = hashlib.sha256((root/name).read_bytes()).hexdigest()\\n    assert actual == expected, name\\nprint('"'"'Local Python check: all 6 bundled file hashes match manifest.sha256.'"'"')\\nprint('"'"'prompt_repr='"'"' + repr((root/'"'"'prompt.txt'"'"').read_text()))\\nPY\"]")
prior_results = "input_sha256=9812fea695945e3f5a2190646809575f993d4adc9f4cfcd8e09b6efd22ea66c6\nenvironment=Darwin 25.6.0; Python 3.12.3\nLocal Python check: all 6 bundled file hashes match manifest.sha256.\nprompt_repr='"'"'Я не понимаю условие: при нехватке нужно вернуть старый остаток или выбросить ошибку? Помоги разобраться, без кода решения.\\n'"'"'\n"
manifest = json.loads((root/'"'"'manifest.json'"'"').read_text())
schema = json.loads((root/'"'"'response.schema.json'"'"').read_text())
prompt = (root/'"'"'prompt.txt'"'"').read_text().removesuffix('"'"'\n'"'"')
response = '"'"'При нехватке нужно выбросить ValueError. В этом случае обычного возвращаемого значения нет, а список должен остаться неизменным. Например, при stock = [3] и qty = 5 вызов заканчивается исключением ValueError, а stock после него остаётся [3].\n\nТеперь соседний случай: stock = [3], qty = 3. Что вернёт вызов, будет ли исключение и каким станет список?'"'"'
execution = (
    '"'"'static_only: прочитаны все 7 файлов единственной выдачи; по assignment.md разобран контракт C1, кода ученика нет, reserve не запускалась. '"'"'
    '"'"'Среда: Darwin 25.6.0; Python 3.12.3. Реальные команды чтения и локальной проверки: '"'"'
    + '"'"'\n\n'"'"'.join(prior_commands)
    + '"'"'\nРезультаты: rg перечислил 7 файлов; чтение показало их содержимое; собственная Python-проверка подтвердила все 6 хешей manifest.sha256; '"'"'
    '"'"'вычислен SHA-256 manifest.json в каноническом JSON sort_keys=True, ensure_ascii=False, separators=(\",\", \":\"). '"'"'
    '"'"'Текст ответа сопоставлен с контрактом; пример разбирается логически и не выдаётся за результат запуска. '"'"'
    '"'"'При сохранении выполнена локальная проверка структуры в памяти по response.schema.json и первая запись файлов через python3 -c; точная команда сохранена в method.md. '"'"'
    '"'"'Один предшествующий вызов functions.exec завершился ошибкой синтаксиса JavaScript до запуска shell и не создал файлов. '"'"'
    '"'"'Сеть, Docker, PostgreSQL, авторский валидатор, исходный репозиторий и другие выдачи не использовались.'"'"'
)
record = {
    '"'"'benchmark_version'"'"': manifest['"'"'version'"'"'],
    '"'"'case_id'"'"': manifest['"'"'case_id'"'"'],
    '"'"'input_sha256'"'"': hashlib.sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=('"'"','"'"', '"'"':'"'"')).encode('"'"'utf-8'"'"')).hexdigest(),
    '"'"'prompt'"'"': prompt,
    '"'"'response'"'"': response,
    '"'"'execution'"'"': execution,
    '"'"'session'"'"': {
        '"'"'id'"'"': '"'"'/root/repeat_hs01_1'"'"',
        '"'"'name'"'"': '"'"'Codex'"'"',
        '"'"'date'"'"': '"'"'2026-10-14'"'"',
        '"'"'kind'"'"': '"'"'model'"'"',
        '"'"'fresh_context'"'"': True,
        '"'"'history_messages'"'"': 0,
    },
}
assert set(record) == set(schema['"'"'required'"'"']) == set(schema['"'"'properties'"'"'])
for field in ['"'"'benchmark_version'"'"', '"'"'case_id'"'"']:
    assert record[field] == schema['"'"'properties'"'"'][field]['"'"'const'"'"']
for field in ['"'"'input_sha256'"'"', '"'"'prompt'"'"', '"'"'response'"'"', '"'"'execution'"'"']:
    assert isinstance(record[field], str) and record[field].strip()
assert len(record['"'"'input_sha256'"'"']) == 64 and all(c in '"'"'0123456789abcdef'"'"' for c in record['"'"'input_sha256'"'"'])
assert set(record['"'"'session'"'"']) == set(schema['"'"'properties'"'"']['"'"'session'"'"']['"'"'required'"'"'])
for field in ['"'"'id'"'"', '"'"'name'"'"', '"'"'date'"'"']:
    assert isinstance(record['"'"'session'"'"'][field], str) and record['"'"'session'"'"'][field].strip()
assert record['"'"'session'"'"']['"'"'kind'"'"'] in schema['"'"'properties'"'"']['"'"'session'"'"']['"'"'properties'"'"']['"'"'kind'"'"']['"'"'enum'"'"']
assert record['"'"'session'"'"']['"'"'fresh_context'"'"'] is True
assert type(record['"'"'session'"'"']['"'"'history_messages'"'"']) is int and record['"'"'session'"'"']['"'"'history_messages'"'"'] == 0
method = (
    '"'"'# Метод\n\n'"'"'
    '"'"'Первый ответ преподавателя в отдельном контексте /root/repeat_hs01_1. Обозначение исполнителя: Codex; точная версия модели не заявляется. '"'"'
    '"'"'Содержательной предыстории ученика нет; fresh_context=true, history_messages=0.\n\n'"'"'
    '"'"'Прочитаны только файлы заданной input-выдачи. TEACHER.md использован как предоставленная инструкция, внешние ссылки из него не открывались. '"'"'
    '"'"'Ученик не понимает условие отказа: дан один разбор входа, исключения и неизменности списка, затем один соседний случай для самостоятельного ответа. '"'"'
    '"'"'Реализация не дана. Это static_only анализ контракта, а не запуск reserve. Личные учебные записи не создавались.\n\n'"'"'
    '"'"'Собственные локальные Python-проверки: проверка 6 входных хешей и вычисление хеша канонического manifest.json; перед записью — проверка структуры JSON в памяти по предоставленной схеме. '"'"'
    '"'"'Авторский оценщик или валидатор не запускался. После первой записи answer.json не исправлялся. '"'"'
    '"'"'Один предварительный вызов functions.exec вернул SyntaxError: Invalid or unexpected token при разборе JavaScript; shell не был запущен, файлы не создавались.\n\n'"'"'
    '"'"'## Реальные команды\n\n'"'"'
    + '"'"'\n\n'"'"'.join('"'"'~~~sh\n'"'"' + command + '"'"'\n~~~'"'"' for command in prior_commands)
    + '"'"'\n\nКоманда первой записи (аргументы текущего процесса):\n\n~~~sh\n'"'"'
    + shlex.join(sys.orig_argv) + '"'"'\n~~~\n\n'"'"'
    '"'"'## Фактические результаты\n\n'"'"'
    '"'"'Команда rg нашла 7 файлов; следующая команда прочитала все 7.\n\n~~~text\n'"'"'
    + prior_results + '"'"'~~~\n\n'"'"'
    '"'"'Проверки структуры в памяти прошли. Оба выходных файла открыты в режиме x: существующие файлы не перезаписываются. '"'"'
    '"'"'Сеть, Docker и PostgreSQL не использованы.\n'"'"'
)
out.mkdir(parents=True, exist_ok=True)
with (out/'"'"'answer.json'"'"').open('"'"'x'"'"') as file:
    json.dump(record, file, ensure_ascii=False, indent=2)
    file.write('"'"'\n'"'"')
with (out/'"'"'method.md'"'"').open('"'"'x'"'"') as file:
    file.write(method)
print('"'"'Saved first answer.json and method.md; in-memory structure assertions passed.'"'"')
'
~~~

## Фактические результаты

Команда rg нашла 7 файлов; следующая команда прочитала все 7.

~~~text
input_sha256=9812fea695945e3f5a2190646809575f993d4adc9f4cfcd8e09b6efd22ea66c6
environment=Darwin 25.6.0; Python 3.12.3
Local Python check: all 6 bundled file hashes match manifest.sha256.
prompt_repr='Я не понимаю условие: при нехватке нужно вернуть старый остаток или выбросить ошибку? Помоги разобраться, без кода решения.\n'
~~~

Проверки структуры в памяти прошли. Оба выходных файла открыты в режиме x: существующие файлы не перезаписываются. Сеть, Docker и PostgreSQL не использованы.
