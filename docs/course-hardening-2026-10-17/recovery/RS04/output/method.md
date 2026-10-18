# Метод RS04

Новая изолированная сессия /root/recovery_rs04; исполнитель ответа — Codex (GPT-6; точный вариант модели не раскрыт). Дата 2026-10-17 взята из контекста среды. Прошлая переписка ученика не использовалась. Прочитаны только файлы input/ и собственный результат output/answer.json. Ответ — работа преподавателя для синтетического участника, не свидетельство обучения настоящего пользователя.

Выполненные команды:

1. `rg --files /Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery/RS04/input` — перечислены 9 файлов, submission.py среди них отсутствует.
2. `python3 -` с pathlib: полный текст каждого файла из `sorted(input.rglob('*'))` выведен через `read_text()`; просмотрены TASK.md, TEACHER.md, assignment.md, learning/NOTES.md, learning/PROGRESS.md, manifest.json, prompt.txt, response.example.json, response.schema.json. Вывод содержал усечение в середине TEACHER.md.
3. `sed -n '90,150p' /Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17/recovery/RS04/input/TEACHER.md` — прочитан усечённый фрагмент.
4. `python3 -` со стандартными библиотеками pathlib/hashlib/json/platform: сверены 8 хешей manifest.sha256; рассчитан input_sha256; создан первый answer.json в режиме exclusive create; файл прочитан обратно, JSON совпал с исходным объектом; создан этот method.md. Форма обязательных полей и допустимые статусы проверены перед записью. Полный оценщик не запускался.

Формула input_sha256: `sha256(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()`.

Фактические результаты: все 8 входных хешей совпали; JSON сохранён и перечитан без расхождений; prompt сохранён без завершающего перевода строки; полные снимки PROGRESS.md и NOTES.md вложены в JSON. NOTES.md сохранён дословно. PROGRESS.md содержит исходную историю R1/R2 и актуальный единственный следующий шаг — восстановить submission.py.

static_only: выполнено восстановление по текстовым свидетельствам. Кода ученика нет; собственного анализа кода и runtime-проверок нет. Статус практики «нужны исправления» основан на открытом R2, а не на новой проверке. Историческое закрытие R1 сохранено. Новая помощь ограничена восстановлением задания и запросом единственного недостающего файла; решение не выдано.

Входы не изменялись; __pycache__ не создавался. Сеть, Docker, облако и оценщик не использовались. Запись answer.json после сохранения не исправлялась.
