# Метод первой записи

Исполнитель: `/root/repeat_rs01_2`, Codex; точная версия модели не предоставлена. Дата: 2026-10-14. Контекст ученика восстановлен исключительно из выданных файлов; прежняя переписка ученика не передавалась (`fresh_context=true`, `history_messages=0`).

Прочитаны все десять файлов выдачи. Первый общий вывод был усечён интерфейсом, поэтому TEACHER.md дополнительно прочитан полностью двумя командами sed. Ссылки на отсутствующие исходные материалы не открывались. Репозиторий, соседние выдачи, авторские ключи, оценщик и прежние ответы не читались. Сеть, Docker, PostgreSQL и дополнительные агенты не использовались.

Метод преподавания: отделить заготовку от сдачи по прямому указанию PROGRESS, сохранить полный маршрут и практику v1 со статусом «выдана», не создавать замечаний до первой сдачи, предложить один следующий шаг — самостоятельную реализацию и два примера из исходного задания. Новых критериев и готового решения нет. NOTES сохранены дословно; PROGRESS представлен полным обновлённым снимком в answer.json. Входные файлы не изменялись.

Проверка учебного кода: `static_only`. Просмотр показал функцию с pass; функция не импортировалась и не запускалась. C1 не проверен, практику не принимали. Локальный Python использовался только для чтения, SHA-256 и записи JSON. Среда: zsh, Python 3.12.3, macOS-26.6.2-x86_64-i386-64bit. Это среда исполнителя, а не подтверждённое окружение ученика.

Фактические результаты: все команды завершились с кодом 0; найдено 10 входных файлов; 9 файловых хешей manifest.json совпали; канонизация использовала UTF-8, ensure_ascii=False, sort_keys=True, separators=(',', ':'); input_sha256 = `c0d25f9efc2ef4b2fbc34d194449072e6828b0d8685cdf5b67607ee7176b51ac`; prompt после удаления одного завершающего перевода строки — `Продолжай`. answer.json создан эксклюзивным режимом `x` с результатом `Created answer.json with exclusive first write; no student code executed.` Авторский валидатор не запускался; после первой записи ответ не проверялся им и не переписывался.

Ниже приведены точные выполненные shell-команды. Заключительная запись самого method.md выполнена инструментом apply_patch; shell-команд после первой записи answer.json не выполнялось.

## Команда 1

```sh
ls -la /private/tmp/course-reliability-s2a212up/repeats/rs01_2/input && find /private/tmp/course-reliability-s2a212up/repeats/rs01_2/input -type f -print
```

## Команда 2

```sh
python3 - <<'PY'
from pathlib import Path
p=Path('/private/tmp/course-reliability-s2a212up/repeats/rs01_2/input')
for f in sorted(p.rglob('*')):
    if f.is_file():
        print('\n===== '+str(f.relative_to(p))+' =====\n')
        print(f.read_text())
PY
```

## Команда 3

```sh
sed -n '1,130p' /private/tmp/course-reliability-s2a212up/repeats/rs01_2/input/TEACHER.md
```

## Команда 4

```sh
sed -n '131,260p' /private/tmp/course-reliability-s2a212up/repeats/rs01_2/input/TEACHER.md
```

## Команда 5

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib, json, platform, sys
root = Path('/private/tmp/course-reliability-s2a212up/repeats/rs01_2/input')
manifest = json.loads((root / 'manifest.json').read_text())
canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
print('input_sha256=' + hashlib.sha256(canonical).hexdigest())
print('python=' + sys.version.split()[0])
print('platform=' + platform.platform())
print('prompt=' + repr((root / 'prompt.txt').read_text().removesuffix('\n')))
print('manifest_entries=' + str(len(manifest['sha256'])))
print('manifest_file_hashes_match=' + str(all(hashlib.sha256((root / name).read_bytes()).hexdigest() == expected for name, expected in manifest['sha256'].items())))
PY
```

## Команда 6

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib, json
root = Path('/private/tmp/course-reliability-s2a212up/repeats/rs01_2/input')
out = Path('/private/tmp/course-reliability-s2a212up/repeats/rs01_2/output')
manifest = json.loads((root / 'manifest.json').read_text())
input_sha256 = hashlib.sha256(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
response = '''Продолжаем с 08/1 по полному маршруту, практика v1. Теория текущей части уже выдана. В `submission.py` пока заготовка с `pass`; работа начата, но ещё не сдана. Ревью не было, замечаний с ID нет.

Следующий шаг — завершить первую самостоятельную реализацию `reserve(stock, qty)` и прислать функцию с двумя примерами: достаточный остаток и нехватка. По условию `qty` — положительное целое; при достаточном остатке функция уменьшает `stock[0]`, а при нехватке вызывает `ValueError`, оставляя список неизменным.

Пришли первую попытку, когда будешь готов: проверим её по C1. Пока C1 не проверен, практика остаётся выданной.'''
progress = '''# Прогресс синтетического участника RS01
Сохранение: включено для этого аудита; хранилище локальное, без commit/push. Разрешение действует только для выданных синтетических учебных данных; входные файлы не изменены, состояние представлено снимком ответа.
Маршрут: полный, 30 тем / 92 части. Основание: сохранённая запись learning/PROGRESS.md; изменения объёма не запрошены. Редакция задания: v1.
## Точка продолжения
- Тема и часть: 08/1.
- Теория: выдана полностью для текущей части согласно сохранённому состоянию.
- Практика: выдана.
- Следующий шаг: Ученик завершает первую самостоятельную реализацию reserve и присылает функцию с двумя примерами: достаточный остаток и нехватка.
- Основание: assignment.md, заготовка submission.py, сохранённая история и запрос «Продолжай».
## История и открытые замечания
Ревью ещё не было. Ученик остановился в середине самостоятельной работы. Не считать заготовку сданной практикой. Замечаний с ID нет; закрытых и снятых замечаний нет.
2026-10-14: точка восстановлена по файлам в новой сессии /root/repeat_rs01_2. На запрос «Продолжай» повторены исходные условия C1 и предложено предъявить первую попытку. Решение и подсказка по реализации не выданы; нового ответа ученика нет.
## Покрытие
Теория текущей части выдана; следующая часть не выдана. Её номер и название в выдаче не указаны. Курс не завершён.
Практика 08/1 v1: работа начата, ещё не сдана. C1 не проверен: для ревью необходима реализация и два примера.
Реального PostgreSQL-прогона нет; успешных runtime-проверок не заявлено. В текущей сессии код submission.py только прочитан (static_only), функция не запускалась.
Восстановление состояния не подтверждает понимание ученика; оснований для новой записи о навыке или повторении пока нет.
'''
answer = {
    'benchmark_version': manifest['version'],
    'case_id': manifest['case_id'],
    'input_sha256': input_sha256,
    'prompt': (root / 'prompt.txt').read_text().removesuffix('\n'),
    'response': response,
    'execution': 'static_only: прочитаны все 10 файлов только внутри выдачи input; submission.py содержит pass, полноценной сдачи и ревью по сохранённой истории нет. Среда исполнителя: zsh, Python 3.12.3, macOS-26.6.2-x86_64-i386-64bit; это не сведения о машине синтетического ученика. Команды чтения: ls/find, python3 с Path.rglob и read_text, sed -n 1,130p и 131,260p для TEACHER.md. Локальный Python-запуск проверил только целостность материалов: 9 хешей файлов совпали, SHA-256 канонического manifest.json = c0d25f9efc2ef4b2fbc34d194449072e6828b0d8685cdf5b67607ee7176b51ac; prompt = Продолжай. Код ученика не запускался, C1 не проверен, успешный runtime не заявляется. Сеть, Docker, PostgreSQL, исходный репозиторий, прежние ответы, авторский валидатор и новые агенты не использовались. Python сформировал answer.json первой эксклюзивной записью; точные команды и метод сохранены отдельно в method.md.',
    'session': {
        'id': '/root/repeat_rs01_2',
        'name': 'Codex (точная версия модели не сообщена)',
        'date': '2026-10-14',
        'kind': 'model',
        'fresh_context': True,
        'history_messages': 0
    },
    'recovered': {
        'part': '08/1',
        'practice': 'выдана',
        'practice_note': 'Практика v1 начата, но ещё не сдана: submission.py — заготовка с pass. Ревью ещё не было; C1 не проверен. Это состояние самостоятельной работы, а не открытого замечания после ревью.',
        'issues': {},
        'next_step': 'Завершить первую самостоятельную реализацию reserve и прислать функцию с двумя примерами: достаточный остаток и нехватка.'
    },
    'snapshot': {
        'PROGRESS.md': progress,
        'NOTES.md': (root / 'learning/NOTES.md').read_text()
    }
}
out.mkdir(parents=True, exist_ok=True)
with (out / 'answer.json').open('x', encoding='utf-8') as f:
    json.dump(answer, f, ensure_ascii=False, indent=2)
    f.write('\n')
print('Created answer.json with exclusive first write; no student code executed.')
PY
```

