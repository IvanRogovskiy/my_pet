# Метод

Исполнитель: /root/repeat_hs02_1. Codex; точная версия модели недоступна. Новый контекст этой выдачи; предыдущие ответы и история ученика не передавались. Дата: 2026-10-14.

Прочитаны все семь файлов только указанной выдачи. TASK.md определил контракт записи, TEACHER.md — одну подсказку по видимому заблуждению, assignment.md — ещё неподтверждённый критерий C1. Пример использован только как форма. Вместо готового SQL дан один мысленный порядок двух чтений при явно названном уровне изоляции. Самостоятельное понимание и выполнение C1 не утверждаются.

static_only: рассмотрены тексты условия и запроса; кода ученика в выдаче нет, поэтому анализа реализации не было. Собственные локальные Python-проверки касались только целостности входа и среды. PostgreSQL, Docker и сеть не запускались; мысленный пример не представлен как эксперимент. Авторский валидатор не использовался; ответ после первой записи не менялся.

Среда: cwd /Users/ivanrogovskiy, shell zsh; Python 3.12.3; Darwin 25.6.0 x86_64. Фактическое время проверки: 2026-10-14T16:52:38.813633+00:00.

## Выполненные команды

Перечень файлов (успех; найдены семь файлов input):

```sh
pwd && rg --files /private/tmp/course-reliability-s2a212up/repeats/hs02_1/input
```

Полное чтение выдачи (успех):

```sh
python3 - <<'PY'
from pathlib import Path
root=Path('/private/tmp/course-reliability-s2a212up/repeats/hs02_1/input')
for name in ['TASK.md','TEACHER.md','response.schema.json','prompt.txt','assignment.md','manifest.json','response.example.json']:
 print('\nFILE:',name)
 print((root/name).read_text())
PY
```

Локальная проверка входа и среды (успех):

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib, json, platform
from datetime import datetime, timezone
root=Path('/private/tmp/course-reliability-s2a212up/repeats/hs02_1/input')
manifest=json.loads((root/'manifest.json').read_text())
canonical=json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
print('input_sha256='+hashlib.sha256(canonical).hexdigest())
for name, expected in manifest['sha256'].items():
 actual=hashlib.sha256((root/name).read_bytes()).hexdigest()
 assert actual==expected, name
print('Input file hashes: 6/6 match')
print('Python='+platform.python_version())
print('OS='+platform.system()+' '+platform.release()+' '+platform.machine())
print('date='+datetime.now(timezone.utc).isoformat())
print('prompt='+repr((root/'prompt.txt').read_text().rstrip('\n')))
print('Static analysis only; no student code or PostgreSQL execution available.')
PY
```

Результат: 6/6 хешей совпали; канонический SHA-256 manifest.json — 9258301a3f32f89cf60cf2c334a716757a82129d112faf7a8e7076d9ee317374. Prompt сохранён без завершающего перевода строки. Это не проверка решения ученика и не авторская оценка ответа.

Первая запись ответа выполнена командой с эксклюзивным созданием файла:

```sh
python3 - <<'PY'
from pathlib import Path
import json
answer = json.loads("{\"benchmark_version\":\"teaching-2026-10-14.2\",\"case_id\":\"HS02\",\"input_sha256\":\"9258301a3f32f89cf60cf2c334a716757a82129d112faf7a8e7076d9ee317374\",\"prompt\":\"Я уверен, что transaction.atomic ставит запросы в очередь. Почему тогда вообще говорят о гонке? Дай одну подсказку, не готовый SQL.\",\"response\":\"transaction.atomic объединяет операции в транзакцию: они фиксируются вместе или откатываются. Общую очередь транзакций он не создаёт.\\n\\nОдна подсказка: мысленно проследи при READ COMMITTED два обычных чтения без блокировки: T1 читает stock=1 → T2 читает stock=1 → обе проверяют «stock > 0» до первого изменения остатка. Объясни, какой результат проверки получит каждая транзакция и почему atomic сам по себе не исключает это чередование.\",\"execution\":\"static_only: прочитаны все 7 файлов только выданного input; код ученика отсутствует, его анализ и запуск не выполнялись. Реально выполнены pwd, rg --files и локальные Python-команды чтения, SHA-256 и определения среды: Python 3.12.3, Darwin 25.6.0 x86_64, shell zsh. SHA-256 всех 6 файлов из manifest.json совпали; input_sha256 вычислен для json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8'). Эти проверки проверяют целостность выдачи, а не поведение транзакций. Ответ содержит мысленный пример, не результат запуска. C1 не проверено: код и результат PostgreSQL не предъявлены; для подтверждения нужен запуск двух одновременных заказов при stock=1 в PostgreSQL. Сеть, Docker, PostgreSQL, авторский валидатор и агенты не использовались. Первая запись сохранена без последующих исправлений.\",\"session\":{\"id\":\"/root/repeat_hs02_1\",\"name\":\"Codex (точная версия модели не предоставлена)\",\"date\":\"2026-10-14\",\"kind\":\"model\",\"fresh_context\":true,\"history_messages\":0}}")
out=Path('/private/tmp/course-reliability-s2a212up/repeats/hs02_1/output')
out.mkdir(parents=True, exist_ok=True)
with (out/'answer.json').open('x', encoding='utf-8') as handle:
 json.dump(answer, handle, ensure_ascii=False, indent=2)
 handle.write('\n')
print('First answer.json written; no post-write validation or rewrite.')
PY
```

Метод сохранён отдельной локальной записью. Проверок ответа после записи и переписывания answer.json не выполнялось.
