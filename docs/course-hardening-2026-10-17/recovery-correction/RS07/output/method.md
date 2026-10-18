# Метод и команды RS07

Ответ сформирован моделью Codex (на базе GPT-6; точный вариант модели не сообщён) в новой сессии `/root/recovery_rs07_contract` без предыдущей переписки. Дата сессии из environment_context: 2026-10-17, Europe/Moscow. Среда команды записи: Darwin 25.6.0 x86_64, Python 3.12.3, shell zsh. Это среда исполнителя аудита, не утверждение об окружении синтетического ученика.

Разрешённые источники: только 11 файлов `RS07/input/`. Прочитаны все; внешние ссылки TEACHER.md не открывались. Ответ опирается на новый запрос о сокращённом backend-маршруте и частичном начале теории 09/1. Текущая практика 09/1 не выдана. Прежняя практика 08/3 v1 сохранена отложенной без зачёта, с историей R1 closed и R2 open. Код submission.py только прочитан (`static_only`), не импортирован и не исполнен. Новых тестов или доказательств понимания ученика нет.

Команды чтения, выполненные с кодом завершения 0:

```sh
rg --files /Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/input
cat '/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/input/TEACHER.md'
cat '/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/input/TASK.md'
cat '/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/input/prompt.txt'
cat '/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/input/response.schema.json'
cat '/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/input/response.example.json'
cat '/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/input/manifest.json'
cat '/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/input/route.md'
cat '/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/input/assignment.md'
cat '/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/input/submission.py'
cat '/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/input/learning/NOTES.md'
cat '/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/input/learning/PROGRESS.md'
cat /Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/input/TEACHER.md
```

Одиннадцать независимых команд cat выполнялись через Promise.allSettled. Общий вывод был усечён в TEACHER.md, поэтому последняя команда повторно прочитала только этот файл целиком с достаточным лимитом вывода.

Инструментом apply_patch создан `output/build_answer.py`. Полный код генерации, включая дословный ответ и полные снимки, сохранён в этом файле. Запись первой версии выполнена следующей командой с cwd `/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07`:

```sh
python3 -B output/build_answer.py
```

Результат: exit code 0, создан `output/answer.json`. Использован режим `open("x")`: существующий ответ не перезаписывается. `-B` предотвращает создание __pycache__. `input_sha256` вычислен через SHA256 UTF-8 представления `json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':'))` и равен `fd2fa4c0c955d000dcba4acbad211cd1289cbb3388ae4fe04ac168b517ba397a`. Из prompt.txt удалён ровно один файловый завершающий перевод строки; текст запроса сохранён без добавленного перевода строки. Поля answer.json соответствуют предоставленной схеме; execution — одна строка.

После фиксации записи создан этот method.md; ответ не редактируется. Для заключительного чтения собственных выходов используются независимые команды:

```sh
cat /Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/output/answer.json
cat /Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/output/method.md
cat /Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery-correction/RS07/output/build_answer.py
```

Оценщик не запускался. Сеть, Docker, облако и новые агенты не использовались. Исходные файлы и каталоги не изменялись; все созданные файлы находятся в sibling output/.
