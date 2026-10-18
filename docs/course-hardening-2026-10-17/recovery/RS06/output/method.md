# Метод RS06

Дата: 2026-10-17, Europe/Moscow. Исполнитель: /root/recovery_rs06, Codex (семейство GPT-6; точный вариант модели не предоставлен). Новый контекст преподавателя, прежней переписки ученика нет. Все данные взяты из input/ этой выдачи. Сеть, Docker, облако и оценщик не использовались. Входы не менялись; Python всегда запускался с -B.

Входной каталог: /Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery/RS06/input
Выходной каталог: /Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery/RS06/output

## Чтение и проверка входов

Команда `rg --files /Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery/RS06/input` обнаружила 10 файлов. Затем выполнен Python-скрипт чтения всех файлов:

```python
from pathlib import Path
p=Path('/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery/RS06/input')
for f in sorted(p.rglob('*')):
    if f.is_file():
        print('\n===== '+str(f.relative_to(p))+' =====')
        print(f.read_text())
```

Запуск: `python3 -B - <<'PY'` с указанным телом и завершающим PY. Вывод полного чтения был сокращён инструментом, поэтому TEACHER.md дочитан целиком командами:

```sh
sed -n '1,120p' /Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery/RS06/input/TEACHER.md
sed -n '121,260p' /Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery/RS06/input/TEACHER.md
```

Отдельный `python3 -B` выполнил следующий скрипт:

```python
from pathlib import Path
import sys, platform, hashlib, json, datetime
p=Path('/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery/RS06/input')
m=json.loads((p/'manifest.json').read_text())
print('python:', sys.version.split()[0])
print('platform:', platform.system(), platform.release(), platform.machine())
print('date:', datetime.datetime.now().astimezone().isoformat())
print('canonical_manifest_sha256:',hashlib.sha256(json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest())
for n,h in m['sha256'].items():
    actual=hashlib.sha256((p/n).read_bytes()).hexdigest()
    print(n, 'match' if actual==h else 'MISMATCH', actual)
print('prompt_repr:',repr((p/'prompt.txt').read_text()))
print('numbered_submission:')
for i,line in enumerate((p/'submission.py').read_text().splitlines(),1): print(f'{i}: {line}')
```

Все 9 хешей совпали. Среда: Python 3.12.3, Darwin 25.6.0 x86_64. Время проверки: 2026-10-17T21:08:38.038652+03:00. Prompt на диске содержит один конечный перевод строки; в JSON записан точный текст «Продолжай» без конечного перевода строки согласно TASK.md.
Канонический SHA256 manifest: d5d6a63284dc9508b75052591465f752d4e4d2e474560bde415b9fdc5abfbb23.

## Проверка доступной работы

Чтение и анализ кода: static_only. Дополнительно проведён собственный локальный runtime-запуск; историческим запуском он не объявляется. Точная команда:

```sh
python3 -B - <<'PY'
from pathlib import Path
p=Path('/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery/RS06/input/submission.py')
ns={}
exec(compile(p.read_text(), str(p), 'exec'),ns)
submit=ns['submit']
s={}
a=submit(s,'alice','key-1',{'amount':1})
b=submit(s,'bob','key-1',{'amount':2})
print('C1_independent_buyers:', 'PASS' if len(s)==2 and a is not b and a['payload']=={'amount':1} and b['payload']=={'amount':2} else 'FAIL')
a_repeat=submit(s,'alice','key-1',{'amount':1})
print('C2_same_payload:', 'PASS' if a_repeat is a and len(s)==2 else 'FAIL')
try:
    changed=submit(s,'alice','key-1',{'amount':3})
except ValueError:
    print('C2_changed_payload: PASS ValueError')
else:
    print('C2_changed_payload: FAIL expected ValueError; got', repr(changed), '; same_result=', changed is a)
PY
```

Фактический вывод (exit code 0; ожидаемое нарушение явно напечатано как FAIL):

```text
C1_independent_buyers: PASS
C2_same_payload: PASS
C2_changed_payload: FAIL expected ValueError; got {'id': 1, 'payload': {'amount': 1}} ; same_result= True
```

Связь файла с A/B и последней сдачей отсутствует. Подтверждение ошибки этого файла не превращено в произвольный выбор исторического статуса. R1 сохранён closed, R2 записан unknown; приёмка практики не проверена. Запрошено только уточнение актуальности сдачи. Нового вывода об усвоении и фиктивной приёмки нет.

## Сохранение первого результата

Выполнена команда:

```sh
mkdir -p /Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery/RS06/output
```

Первая команда Python для сохранения не выполнилась: внешний heredoc PY конфликтовал с вложенным примером команды в method.md. Результат оболочки: `zsh:179: parse error near }`, exit code 1. Ответ при этой попытке не записан. Повторная команда использует уникальный разделитель PY_RS06_WRITE_20261017.

Затем `python3 -B` сформировал объект answer.json из дословного ответа, исходного NOTES.md и полного обновлённого PROGRESS.md. Перед первой записью проверены обязательные поля, типы, const, enum, pattern, ограничения дополнительных полей по response.schema.json; все входные хеши повторно совпали. Запись файлов выполнялась с режимом x, без перезаписи существующего результата. Сохранены answer.json, response.txt, PROGRESS.md, NOTES.md и этот method.md. Проверка структуры JSON не является оцениванием ответа; оценщик не запускался. После сохранения планируется только чтение собственных выходов и проверка совпадения снимков, без изменения ответа.
