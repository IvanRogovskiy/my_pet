import hashlib
import json
from pathlib import Path

root = Path('/private/tmp/course-teacher-run-noqf97ev/HS03')
manifest = json.loads((root / 'inputs/manifest.json').read_text())
canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
response = '''Сделай один диагностический прогон с `stock = [1]` и `qty = 2`: в отладчике остановись перед `submission.py:2`, затем проследи значение `stock` сразу после этой строки и после перехвата `ValueError`. Так мы увидим, в какой момент меняется список и отменяет ли исключение это изменение. Пришли эти два значения.

Опираюсь на код и твой журнал; сам функцию не запускал.'''
answer = {
    'benchmark_version': manifest['version'],
    'case_id': manifest['case_id'],
    'input_sha256': hashlib.sha256(canonical.encode('utf-8')).hexdigest(),
    'prompt': (root / 'inputs/prompt.txt').read_text().rstrip('\n'),
    'response': response,
    'execution': [
        'Среда: локальная файловая система; shell zsh; cwd /Users/ivanrogovskiy; локальный python3; дата 2026-10-14.',
        'static_only: submission.py прочитан; reserve и тесты не запускались. evidence.txt — предоставленный журнал ученика, не мой запуск.',
        'cat /private/tmp/course-teacher-run-noqf97ev/HS03/inputs/TASK.md /private/tmp/course-teacher-run-noqf97ev/HS03/inputs/TEACHER.md — успешно, exit_code 0.',
        'rg --files /private/tmp/course-teacher-run-noqf97ev/HS03/inputs — успешно, exit_code 0; перечислены семь файлов выдачи.',
        'python3 через heredoc прочитал manifest.json, prompt.txt, assignment.md, submission.py, evidence.txt только внутри inputs; успешно, exit_code 0; точная команда записана в method.md.',
        'mkdir -p /private/tmp/course-teacher-run-noqf97ev/HS03/output — успешно, exit_code 0.',
        'Локальный create_answer.py вычислил SHA256 канонического JSON manifest и записал первый ответ через эксклюзивное создание; результат выполнения фиксируется в method.md.',
        'Сеть, облако, исходный репозиторий, соседние выдачи, авторские рубрики, оценщик и дополнительные агенты не использовались. Входные файлы не изменялись.'
    ],
    'session': {
        'id': '/root/teacher_hs03',
        'name': 'Codex; точное имя и версия модели неизвестны',
        'date': '2026-10-14',
        'kind': 'model',
        'fresh_context': True,
        'history_messages': 0
    }
}
with (root / 'output/answer.json').open('x', encoding='utf-8') as target:
    json.dump(answer, target, ensure_ascii=False, indent=2)
    target.write('\n')
print('Created output/answer.json; case_id=' + answer['case_id'])
print('input_sha256=' + answer['input_sha256'])
