import hashlib
import json
import os
import platform
import sys
from pathlib import Path

base = Path('/private/tmp/course-teacher-run-noqf97ev/RS01')
inputs = base / 'inputs'
output = base / 'output'
manifest = json.loads((inputs / 'manifest.json').read_text(encoding='utf-8'))
canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
input_sha256 = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
checks = {
    name: hashlib.sha256((inputs / name).read_bytes()).hexdigest() == expected
    for name, expected in manifest['sha256'].items()
}
if not all(checks.values()):
    raise RuntimeError(f'Input hash mismatch: {checks}')

response = '''Продолжаем практику 08/1, версия v1, по полному маршруту. Теория этой части уже выдана; реализация reserve начата, но ещё не сдана. Ревью пока не было.

Следующий шаг — дописать функцию и прислать её с двумя примерами: при достаточном остатке и при нехватке. По условию reserve(stock, qty) уменьшает stock[0] на qty; если остатка недостаточно, выбрасывает ValueError и оставляет список без изменений. qty — положительное целое. В примерах покажи результат и состояние списка после вызова, включая случай отказа.'''

progress = '''# Прогресс синтетического участника RS01
Сохранение: включено для этого аудита; хранилище локальное, без commit/push.
Маршрут: полный, 30 тем / 92 части. Редакция задания: v1.
## Точка продолжения
- Тема и часть: 08/1, практика reserve.
- Теория: выдана полностью для текущей части.
- Практика: выдана; работа начата, но ещё не сдана.
- Следующий шаг: получить первую самостоятельную сдачу reserve — функцию и два примера: достаточный остаток и нехватка.
- Следующая часть теории: не выдана; номер и название в предоставленных материалах не указаны.
- Основание: assignment.md, submission.py и история ниже.
## История и открытые замечания
Ревью ещё не было. Ученик остановился в середине самостоятельной работы. Не считать заготовку сданной практикой.
2026-10-14: в новой сессии по запросу «Продолжай» восстановлена точка продолжения. Повторены требования задания v1 и запрошена первая самостоятельная сдача. Готовая реализация и подсказка по механизму не выдавались. Нового ответа ученика нет; ID замечаний не создавались.
## Покрытие
Теория текущей части выдана; следующая часть не выдана. Курс не завершён.
Реального PostgreSQL-прогона нет; успешных runtime-проверок не заявлено.
В этой сессии submission.py только прочитан (static_only); выполнение задания и понимание ученика не подтверждались.
'''
notes = (inputs / 'learning/NOTES.md').read_text(encoding='utf-8')

commands = [
    'cat /private/tmp/course-teacher-run-noqf97ev/RS01/inputs/TASK.md /private/tmp/course-teacher-run-noqf97ev/RS01/inputs/TEACHER.md',
    'rg --files --hidden /private/tmp/course-teacher-run-noqf97ev/RS01/inputs',
    'cat /private/tmp/course-teacher-run-noqf97ev/RS01/inputs/prompt.txt /private/tmp/course-teacher-run-noqf97ev/RS01/inputs/learning/PROGRESS.md /private/tmp/course-teacher-run-noqf97ev/RS01/inputs/learning/NOTES.md',
    'cat /private/tmp/course-teacher-run-noqf97ev/RS01/inputs/manifest.json /private/tmp/course-teacher-run-noqf97ev/RS01/inputs/assignment.md /private/tmp/course-teacher-run-noqf97ev/RS01/inputs/submission.py',
    'python3 /private/tmp/course-teacher-run-noqf97ev/RS01/output/create_answer.py',
]
environment = f'{platform.system()} {platform.release()}, {platform.machine()}; Python {platform.python_version()}; cwd={os.getcwd()}'
execution = [
    f'Среда сохранения артефактов: {environment}.',
    'Чтение выполнено командами: ' + ' | '.join(commands[:-1]) + '. Все четыре команды завершились с кодом 0; найдены восемь входных файлов, их содержимое прочитано.',
    'static_only: submission.py содержит заготовку reserve(stock, qty) с pass; код не запускался. Это незавершённая самостоятельная работа, не сдача на ревью.',
    'По NOTES.md PostgreSQL/Docker недоступны; собственная проверка их наличия не выполнялась. Тесты, БД, облачные и сетевые операции не запускались.',
    f'Команда сохранения: {commands[-1]}. SHA256 всех семи файлов, перечисленных в manifest.sha256, совпали. input_sha256 рассчитан из канонического JSON manifest.',
    'answer.json создан один раз с режимом x; snapshot содержит полный текст PROGRESS.md после ответа и неизменённый NOTES.md. Входные файлы не изменены.',
]
answer = {
    'benchmark_version': manifest['version'],
    'case_id': manifest['case_id'],
    'input_sha256': input_sha256,
    'prompt': (inputs / 'prompt.txt').read_text(encoding='utf-8').removesuffix('\n'),
    'response': response,
    'execution': execution,
    'session': {
        'id': '/root/teacher_rs01',
        'name': 'Модель и точная версия неизвестны',
        'date': '2026-10-14',
        'kind': 'model',
        'fresh_context': True,
        'history_messages': 0,
    },
    'recovered': {
        'part': '08/1',
        'practice': 'выдана; работа начата, но ещё не сдана',
        'issues': {},
        'next_step': 'Получить первую самостоятельную сдачу reserve — функцию и два примера: достаточный остаток и нехватка.',
    },
    'snapshot': {'PROGRESS.md': progress, 'NOTES.md': notes},
}
with (output / 'answer.json').open('x', encoding='utf-8') as handle:
    json.dump(answer, handle, ensure_ascii=False, indent=2)
    handle.write('\n')

files = ['TASK.md', 'TEACHER.md', 'prompt.txt', 'learning/PROGRESS.md', 'learning/NOTES.md', 'manifest.json', 'assignment.md', 'submission.py']
method = '# Метод исполнения RS01\n\n'
method += 'Контекст: /root/teacher_rs01; новый изолированный контекст, без предыдущей переписки ученика. Модель и точная версия неизвестны. Дата: 2026-10-14.\n\n'
method += f'Среда: {environment}.\n\n'
method += 'Прочитаны только файлы внутри inputs, в следующем порядке:\n\n' + '\n'.join('- ' + name for name in files) + '\n\n'
method += 'Фактические команды, в порядке исполнения:\n\n' + '\n\n'.join('```sh\n' + command + '\n```' for command in commands) + '\n\n'
method += 'Перед последней командой инструментом apply_patch создан output/create_answer.py. Этот файл содержит полный код вычисления хешей, формирования первого ответа и записи артефактов.\n\n'
method += 'Результат чтения: все четыре команды завершились с кодом 0. rg перечислил восемь входных файлов. Состояние соответствует начатой, но не сданной практике 08/1 v1; ревью и ID замечаний отсутствуют.\n\n'
method += f'Проверка целостности: все семь файлов manifest.sha256 совпали. Канонический SHA256 manifest: {input_sha256}.\n\n'
method += 'Граница исполнения: static_only для submission.py. Заготовка не исполнялась; тесты и проверки PostgreSQL/Docker не выполнялись. Ограничение среды PostgreSQL/Docker взято из NOTES.md. Сеть, облако, оценщик, внешние материалы, исходный репозиторий, соседние каталоги, чужие ответы и дополнительные агенты не использованы.\n\n'
method += 'answer.json содержит первый сформированный ответ ученику без последующего улучшения по ключам. Файл создан эксклюзивно (open x) и после записи не переписывался. Снимки состояния сохранены внутри answer.json; входные файлы не изменялись. NOTES.md сохранён дословно.\n'
with (output / 'method.md').open('x', encoding='utf-8') as handle:
    handle.write(method)
print(json.dumps({'created': ['answer.json', 'method.md'], 'input_sha256': input_sha256, 'input_hash_checks': checks, 'environment': environment}, ensure_ascii=False))
