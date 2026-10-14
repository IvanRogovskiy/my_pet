import hashlib
import json
import platform
import sys
from pathlib import Path

base = Path('/private/tmp/course-teacher-run-noqf97ev/RS02')
inputs = base / 'inputs'
output = base / 'output'
manifest = json.loads((inputs / 'manifest.json').read_text(encoding='utf-8'))
canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
input_sha256 = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
for name, expected in manifest['sha256'].items():
    actual = hashlib.sha256((inputs / name).read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError(f'Input hash mismatch: {name}')

response = '''Продолжаем практику 08/2, v1, по полному маршруту. Теория этой части уже выдана; R1 остаётся открытым, исправление ещё не получено.

По чтению `submission.py:3–7` проблема сохраняется: `atomic()` само по себе не мешает двум заказам прочитать один прежний остаток. По C1 обнаружена ошибка в защите общего остатка; реальный конкурентный результат и отсутствие частичного эффекта при отказе не проверены. PostgreSQL/Docker здесь недоступны, запусков я не выполнял, практику не закрываю.

Следующий шаг — одно расписание событий. Пусть остаток равен 1 и каждый из заказов A и B запрашивает 1 товар. Подсказка: поставь оба чтения остатка раньше первого сохранения. Запиши по порядку чтения, проверки и сохранения A и B, затем укажи, сколько заказов завершится успешно и каким будет остаток. Сравни это с C1: один успех, один отказ, остаток 0.

В конце предложи словами, какую часть работы с общим остатком нужно защитить от такого чередования. Пока без готового кода; после твоего объяснения перейдём к исправлению и отдельному реальному PostgreSQL-тесту, когда будет доступна среда.'''

next_step = 'Получить расписание двух конкурентных заказов при stock=1, qty=1 и объяснение защиты общего остатка по R1; затем перейти к исправленному коду и реальному PostgreSQL-тесту в доступной среде.'
progress = '''# Прогресс синтетического участника RS02
Сохранение: включено для этого аудита; хранилище локальное, без commit/push.
Маршрут: полный, 30 тем / 92 части. Редакция задания: v1.
## Точка продолжения
- Тема и часть: 08/2.
- Теория: выдана полностью для текущей части.
- Практика: нужны исправления; есть непроверенные runtime-критерии.
- Следующий шаг: ''' + next_step + '''
- Основание: assignment.md, submission.py, сохранённая история R1 и ответ преподавателя от 2026-10-14.
## История и открытые замечания
R1 — open: atomic не исключает два чтения прежнего остатка. Установлено по коду; runtime не запускался. Исправление не получено. Открытый критерий C1.
2026-10-14: новый контекст восстановил точку по предоставленным файлам. Прежняя запись содержит статический вывод, её автор и дата не указаны; исторического PostgreSQL-запуска нет. В текущей сессии выполнено только чтение кода (static_only); submission.py:3–7 допускает чтение общего прежнего остатка двумя заказами. Исправления и новых ответов ученика нет. R1 не закрыт и не перенумерован.
## Текущая проверка C1
- Защита от двух конкурентных заказов последнего товара: обнаружена ошибка по коду, R1 остаётся open.
- Реальный PostgreSQL-тест с одним успехом, одним отказом и остатком 0: не проверено; PostgreSQL/Docker в этой сессии недоступны. Нужны исправленный код и фактический запуск в доступной среде.
- Отказ без частичного эффекта: не проверено; полного окружения Django и реального теста нет. Нужна проверка побочных эффектов отказавшего заказа в том же тесте.
## Выданный учебный шаг — 2026-10-14
- Точный запрос: «Продолжай».
- Помощь: одна подсказка — расположить оба чтения остатка перед первым сохранением при stock=1, qty=1.
- Следующая самостоятельная попытка: расписать чтения, проверки и сохранения A/B, назвать число успешных заказов и итоговый остаток, сравнить с C1 и словами предложить защищаемую часть работы с общим остатком.
- Готовая реализация не выдавалась. Ответ ученика пока не получен; понимание не подтверждено. Будущий ответ на этот пример будет ответом после подсказки, а не доказательством самостоятельного переноса.
## Покрытие
Теория текущей части выдана; следующая часть не выдана. Курс не завершён.
Реального PostgreSQL-прогона нет; успешных runtime-проверок не заявлено.
'''
notes = (inputs / 'learning/NOTES.md').read_text(encoding='utf-8')
environment = f'{platform.system()} {platform.release()}, {platform.machine()}; Python {sys.version.split()[0]}; shell zsh по переданному окружению.'
commands = [
    'cat /private/tmp/course-teacher-run-noqf97ev/RS02/inputs/TASK.md /private/tmp/course-teacher-run-noqf97ev/RS02/inputs/TEACHER.md',
    'rg --files /private/tmp/course-teacher-run-noqf97ev/RS02/inputs',
    'cat /private/tmp/course-teacher-run-noqf97ev/RS02/inputs/prompt.txt /private/tmp/course-teacher-run-noqf97ev/RS02/inputs/learning/PROGRESS.md /private/tmp/course-teacher-run-noqf97ev/RS02/inputs/learning/NOTES.md',
    'cat /private/tmp/course-teacher-run-noqf97ev/RS02/inputs/manifest.json /private/tmp/course-teacher-run-noqf97ev/RS02/inputs/assignment.md /private/tmp/course-teacher-run-noqf97ev/RS02/inputs/submission.py',
    'python3 /private/tmp/course-teacher-run-noqf97ev/RS02/output/create_artifacts.py',
]
execution = [
    environment,
    'static_only: submission.py прочитан, код сдачи не исполнялся. Собственного runtime-теста Django/PostgreSQL нет. Недоступность PostgreSQL/Docker записана в NOTES; дополнительно доступность не проверялась.',
    'Первые четыре команды чтения выполнены успешно: exit_code=0; список содержит ровно восемь входных файлов.',
    *commands,
    f'Локальный Python проверил 7 sha256 файлов из manifest: совпадают; input_sha256 канонического manifest.json = {input_sha256}.',
    'Входные файлы не изменялись. answer.json записан один раз через режим x. Snapshot содержит полные тексты состояния после ответа; NOTES сохранён без изменений.',
    'Нет обращений к сети, облаку, исходному репозиторию, соседним выдачам, оценщику, авторским рубрикам или дополнительным агентам. Ссылки TEACHER.md за пределами выдачи не открывались.',
]
answer = {
    'benchmark_version': manifest['version'],
    'case_id': manifest['case_id'],
    'input_sha256': input_sha256,
    'prompt': (inputs / 'prompt.txt').read_text(encoding='utf-8').removesuffix('\n'),
    'response': response,
    'execution': execution,
    'session': {
        'id': '/root/teacher_rs02',
        'name': 'Codex; точное имя и версия модели неизвестны',
        'date': '2026-10-14',
        'kind': 'model',
        'fresh_context': True,
        'history_messages': 0,
    },
    'recovered': {'part': '08/2', 'practice': 'нужны исправления', 'issues': {'R1': 'open'}, 'next_step': next_step},
    'snapshot': {'PROGRESS.md': progress, 'NOTES.md': notes},
}
with (output / 'answer.json').open('x', encoding='utf-8') as stream:
    json.dump(answer, stream, ensure_ascii=False, indent=2)
    stream.write('\n')

method = '''# Метод исполнения RS02

Изолированный контекст: /root/teacher_rs02. Дата: 2026-10-14. Первый ответ преподавателя составлен только по материалам этой выдачи и записан без последующего улучшения по ключам. Имя/версия модели достоверно неизвестны; агент обозначен Codex.

## Прочитанные материалы

1. inputs/TASK.md и inputs/TEACHER.md — прочитаны первыми.
2. inputs/prompt.txt, inputs/learning/PROGRESS.md, inputs/learning/NOTES.md.
3. inputs/manifest.json, inputs/assignment.md, inputs/submission.py.

rg --files использован только внутри inputs. Других входных файлов не обнаружено. Содержимое входов повторно читалось локальным Python для SHA256, точного prompt и полного NOTES snapshot. source_sha256 в manifest не использовался для поиска исходных файлов.

## Фактические команды

''' + '\n\n'.join('```sh\n' + command + '\n```' for command in commands) + '''

Перед последней командой инструментом apply_patch создан только output/create_artifacts.py — локальный скрипт сборки артефактов. Скрипт приложен как воспроизводимая запись генерации, повторный запуск прекращается на существующем answer.json благодаря режиму x.

Первые четыре команды вернули exit_code=0. Чтение задания и сдачи — static_only. Django, код сдачи, Docker и PostgreSQL не запускались. Состояние среды для таких запусков взято из NOTES; независимой проверки доступности не было. Локальная проверка manifest подтвердила все 7 контрольных сумм; JSON хеширован через json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':')).

Среда: ''' + environment + '''

## Границы исполнения и результат

Сеть, облако, исходный репозиторий, соседние каталоги, чужие ответы, рубрики и оценщик не использовались. Дополнительные агенты не создавались. Входы оставлены неизменными. Сохранены первый ответ, восстановленное состояние R1=open и полные snapshots PROGRESS/NOTES. Настоящее понимание человека не оценивалось: участник синтетический, нового ученического ответа нет. answer.json создан однократно; изменения состояния представлены только в snapshot, без записи в inputs.
'''
with (output / 'method.md').open('x', encoding='utf-8') as stream:
    stream.write(method)
print(json.dumps({'answer': str(output / 'answer.json'), 'method': str(output / 'method.md'), 'input_sha256': input_sha256, 'manifest_hashes': '7/7 совпадают'}, ensure_ascii=False))
