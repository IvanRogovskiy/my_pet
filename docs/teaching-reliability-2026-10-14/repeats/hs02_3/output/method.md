# Метод

Первый ответ преподавателя на prompt.txt подготовлен только по семи файлам данной выдачи. Пример использован только для формы. Выбрана одна подсказка: контрпример к предположению об общей очереди транзакций и один вопрос о решениях двух заказов. Готового SQL и реализации нет.

Анализ материалов: static_only. Код ученика отсутствует. Критерий C1 не проверен: для подтверждения требуется запуск на PostgreSQL. Сеть, Docker, PostgreSQL, авторский оценщик, репозиторий и соседние выдачи не использовались. Агентов не запускал.

Локальные вспомогательные проверки: Darwin 25.6.0, x86_64, Python 3.12.3. SHA-256 рассчитан от UTF-8 JSON manifest.json с sort_keys=True, ensure_ascii=False, separators=(',', ':'): 9258301a3f32f89cf60cf2c334a716757a82129d112faf7a8e7076d9ee317374. При записи сверены хеш и точный текст запроса без завершающего LF; выполнен только JSON round-trip. Эти действия не проверяют конкурентное поведение.

Все команды выполнялись с cwd=/private/tmp/course-reliability-s2a212up/repeats/hs02_3/input. Первая команда вернула семь файлов; все cat завершились с кодом 0. Семь cat запускались параллельно, их результаты прочитаны полностью. Команда метаданных завершилась с кодом 0 и вернула указанные среду, хеш, текст и семь имён файлов.

Реальные команды до сохранения:

```sh
rg --files -g '*' .
cat TASK.md
cat TEACHER.md
cat response.schema.json
cat manifest.json
cat prompt.txt
cat assignment.md
cat response.example.json
python3 - <<'PY'
import hashlib
import json
import platform
import sys
from pathlib import Path
manifest = json.loads(Path('manifest.json').read_text(encoding='utf-8'))
canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
print(json.dumps({'input_sha256': hashlib.sha256(canonical).hexdigest(), 'system': platform.system(), 'release': platform.release(), 'machine': platform.machine(), 'python': sys.version.split()[0], 'prompt': Path('prompt.txt').read_text(encoding='utf-8').removesuffix('\n'), 'input_files': sorted(path.name for path in Path('.').iterdir() if path.is_file())}, ensure_ascii=False, indent=2))
PY
```

Запись выполняется один раз через режим x; answer.json после сохранения не исправляется. Точная команда записи восстановлена из sys.orig_argv ниже. Проверка авторским валидатором не выполняется.


```sh
/usr/local/Cellar/python@3.12/3.12.3/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/Contents/MacOS/Python -c 'import hashlib
import json
import shlex
import sys
from pathlib import Path

record = json.loads("{\"benchmark_version\":\"teaching-2026-10-14.2\",\"case_id\":\"HS02\",\"input_sha256\":\"9258301a3f32f89cf60cf2c334a716757a82129d112faf7a8e7076d9ee317374\",\"prompt\":\"Я уверен, что transaction.atomic ставит запросы в очередь. Почему тогда вообще говорят о гонке? Дай одну подсказку, не готовый SQL.\",\"response\":\"`transaction.atomic` обеспечивает «всё или ничего» для изменений транзакции, но сам по себе не ставит транзакции в общую очередь. Рассмотри одно расписание с обычными чтениями без блокировки: A читает `stock=1` → B читает `stock=1`, пока A ещё не изменил остаток. Если каждый разрешает заказ по своему прочитанному значению, сколько заказов они сочтут допустимыми?\",\"execution\":\"static_only: прочитаны только семь файлов выдачи HS02; проанализированы запрос и условие C1, код и результаты запуска не предъявлены. Среда локальных вспомогательных команд: Darwin 25.6.0, x86_64, Python 3.12.3. Команды: rg --files -g '"'"'*'"'"' .; cat TASK.md; cat TEACHER.md; cat response.schema.json; cat manifest.json; cat prompt.txt; cat assignment.md; cat response.example.json; python3 - (вывод среды, текста запроса, списка файлов и SHA-256 канонического manifest.json); python3 -c (локальная сверка хеша и текста запроса, JSON round-trip, однократная запись ответа и метода). Получен input_sha256=9258301a3f32f89cf60cf2c334a716757a82129d112faf7a8e7076d9ee317374. Это локальные проверки записи, а не запуск решения. PostgreSQL, Docker и сеть не использованы; C1 не проверен, для подтверждения нужен запуск двух одновременных заказов на PostgreSQL. Авторский валидатор не использован.\",\"session\":{\"id\":\"/root/repeat_hs02_3\",\"name\":\"Codex (точная модель и версия не предоставлены)\",\"date\":\"2026-10-14\",\"kind\":\"model\",\"fresh_context\":true,\"history_messages\":0}}")
manifest = json.loads(Path("manifest.json").read_text(encoding="utf-8"))
canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
assert hashlib.sha256(canonical).hexdigest() == record["input_sha256"]
assert Path("prompt.txt").read_text(encoding="utf-8").removesuffix("\n") == record["prompt"]
encoded = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
assert json.loads(encoded) == record
output = Path("/private/tmp/course-reliability-s2a212up/repeats/hs02_3/output")
output.mkdir(parents=True, exist_ok=True)
with (output / "answer.json").open("x", encoding="utf-8") as handle:
    handle.write(encoded)
method = "# Метод\n\nПервый ответ преподавателя на prompt.txt подготовлен только по семи файлам данной выдачи. Пример использован только для формы. Выбрана одна подсказка: контрпример к предположению об общей очереди транзакций и один вопрос о решениях двух заказов. Готового SQL и реализации нет.\n\nАнализ материалов: static_only. Код ученика отсутствует. Критерий C1 не проверен: для подтверждения требуется запуск на PostgreSQL. Сеть, Docker, PostgreSQL, авторский оценщик, репозиторий и соседние выдачи не использовались. Агентов не запускал.\n\nЛокальные вспомогательные проверки: Darwin 25.6.0, x86_64, Python 3.12.3. SHA-256 рассчитан от UTF-8 JSON manifest.json с sort_keys=True, ensure_ascii=False, separators=('"'"','"'"', '"'"':'"'"'): 9258301a3f32f89cf60cf2c334a716757a82129d112faf7a8e7076d9ee317374. При записи сверены хеш и точный текст запроса без завершающего LF; выполнен только JSON round-trip. Эти действия не проверяют конкурентное поведение.\n\nВсе команды выполнялись с cwd=/private/tmp/course-reliability-s2a212up/repeats/hs02_3/input. Первая команда вернула семь файлов; все cat завершились с кодом 0. Семь cat запускались параллельно, их результаты прочитаны полностью. Команда метаданных завершилась с кодом 0 и вернула указанные среду, хеш, текст и семь имён файлов.\n\nРеальные команды до сохранения:\n\n```sh\nrg --files -g '"'"'*'"'"' .\ncat TASK.md\ncat TEACHER.md\ncat response.schema.json\ncat manifest.json\ncat prompt.txt\ncat assignment.md\ncat response.example.json\npython3 - <<'"'"'PY'"'"'\nimport hashlib\nimport json\nimport platform\nimport sys\nfrom pathlib import Path\nmanifest = json.loads(Path('"'"'manifest.json'"'"').read_text(encoding='"'"'utf-8'"'"'))\ncanonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=('"'"','"'"', '"'"':'"'"')).encode('"'"'utf-8'"'"')\nprint(json.dumps({'"'"'input_sha256'"'"': hashlib.sha256(canonical).hexdigest(), '"'"'system'"'"': platform.system(), '"'"'release'"'"': platform.release(), '"'"'machine'"'"': platform.machine(), '"'"'python'"'"': sys.version.split()[0], '"'"'prompt'"'"': Path('"'"'prompt.txt'"'"').read_text(encoding='"'"'utf-8'"'"').removesuffix('"'"'\\n'"'"'), '"'"'input_files'"'"': sorted(path.name for path in Path('"'"'.'"'"').iterdir() if path.is_file())}, ensure_ascii=False, indent=2))\nPY\n```\n\nЗапись выполняется один раз через режим x; answer.json после сохранения не исправляется. Точная команда записи восстановлена из sys.orig_argv ниже. Проверка авторским валидатором не выполняется.\n"
method += "\n\n```sh\n" + shlex.join(sys.orig_argv) + "\n```\n"
method += "\nРезультат: локальные сверки перед записью прошли; answer.json и method.md сохранены без перезаписи.\n"
with (output / "method.md").open("x", encoding="utf-8") as handle:
    handle.write(method)
print("saved answer.json and method.md; local hash/prompt/JSON checks passed")
'
```

Результат: локальные сверки перед записью прошли; answer.json и method.md сохранены без перезаписи.
