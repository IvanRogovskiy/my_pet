"""Freeze the first independent teacher response; never overwrite an answer."""
from hashlib import sha256
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
metadata = json.loads((BASE / "run-metadata.json").read_text())
probes = json.loads((OUT / "probe-results.json").read_text())


def finding(file, line, explanation, repro, direction):
    return {"criterion": "C1", "file": file, "line": line,
            "explanation": explanation, "repro": repro, "direction": direction}


reviews = [
    {
        "case_id": "AD01", "classification": "code_defect", "verdict": "needs_changes",
        "criteria": {"C1": "error"},
        "findings": [
            finding("submission.py", 2,
                    "R1. Ключом служит только token; tenant не участвует ни в поиске, ни в записи на строке 7. Это нарушает независимость областей (tenant, token): операции разных арендаторов с одинаковым токеном получают одну запись и id либо ложный конфликт. Ошибка блокирует приёмку C1.",
                    "Собственный запуск probe.py: jobs={}; enqueue(jobs,'A','t',{'items':[1]}); enqueue(jobs,'B','t',{'items':[1]}) вернул id=1 для обоих, len(jobs)=1. Ожидались две записи с разными id. В отдельной пробе второй tenant с {'items':[2]} получил ValueError вместо новой записи.",
                    "Использовать полную область повтора одинаково при поиске и сохранении. Повторить оба сценария разных tenant и прежние сценарии повтора/конфликта одного tenant."),
            finding("submission.py", 6,
                    "R2. dict(payload) копирует внешний словарь, но оставляет те же вложенные списки. Последующая мутация входного списка меняет сохранённое тело, что прямо нарушает требование снимка. Это отдельная ошибка корректности, не требование защиты от мутации возвращённого результата.",
                    "Собственный запуск: p={'items':[1]}; r=enqueue({},'A','t',p); p['items'].append(2). r['payload'] стал {'items':[1,2]}, ожидалось {'items':[1]}. В пробе с сохранённым jobs повтор первоначального тела {'items':[1]} затем дал ValueError.",
                    "Отделить вложенные списки снимка от входных списков. Проверить неизменность входа самим вызовом, сохранность тела после внешней мутации исходного списка и точный повтор исходного тела.")
        ],
        "next_step": "Исправить R1 и R2, затем предъявить результаты обеих регрессионных проб вместе с проверкой точного повтора и конфликта внутри одного tenant."
    },
    {
        "case_id": "AD02", "classification": "valid", "verdict": "accepted",
        "criteria": {"C1": "confirmed"}, "findings": [],
        "next_step": "C1 подтверждён анализом строк 3–11 и шестью локальными группами проверок: область, повтор, конфликт, независимость tenant, снимок списков, неизменность входа и уникальные id. Следующий учебный шаг — объяснить разницу между неизменяемым fingerprint и отдельным снимком payload. Защита от мутации возвращённого результата не требовалась."
    },
    {
        "case_id": "AD03", "classification": "code_defect", "verdict": "needs_changes",
        "criteria": {"C1": "error"},
        "findings": [
            finding("submission.py", 3,
                    "R1. Проверяется каждая строка запроса отдельно, а не суммарная потребность повторяющегося SKU. Две строки могут пройти проверку по одному исходному остатку, после чего списание на строке 6 уводит stock ниже нуля. Нарушены суммирование, ValueError при нехватке и неизменность stock при отказе; это блокирующая ошибка C1.",
                    "Собственный запуск: stock={'a':5}; requests=[('a',3),('a',3)]; allocate вернул {'a':-1} и изменил stock. Ожидались ValueError и исходный stock={'a':5}.",
                    "Сначала рассчитать суммарную потребность каждого SKU во временной структуре и проверить весь пакет до изменения stock. Повторить пример с суммарной нехваткой и пример успешного списания ровно до нуля."),
            finding("submission.py", 2,
                    "R2. requests.sort() меняет список вызывающего кода до проверки достаточности. Контракт запрещает менять requests как при успехе, так и при отказе. Это независимое нарушение C1.",
                    "Собственный запуск: stock={'a':0,'b':2}, requests=[('b',1),('a',1)]. Возник ValueError, stock остался прежним, но requests стал [('a',1),('b',1)] вместо исходного порядка. Успешная проба также изменила порядок requests.",
                    "Работать без мутации входного списка; отдельная сортировка нужна только если она действительно помогает выбранному алгоритму. Сравнивать requests до и после успешного и отклонённого пакета.")
        ],
        "next_step": "Исправить агрегацию и мутацию requests, затем повторить оба контрпримера и успешный пакет с несколькими SKU. Конкурентная БД не является частью этого задания."
    },
    {
        "case_id": "AD04", "classification": "valid", "verdict": "accepted",
        "criteria": {"C1": "confirmed"}, "findings": [],
        "next_step": "C1 подтверждён: строки 3–8 суммируют потребность и проверяют пакет до stock.update, requests только читается, возвращается сам stock. В 1360 локальных комбинациях ошибок не найдено; отдельно проверены пустой запрос, отказ и успех. Следующий учебный шаг — объяснить, почему промежуточный after сохраняет stock при отказе в последовательной модели."
    },
    {
        "case_id": "AD05", "classification": "test_defect", "verdict": "needs_changes",
        "criteria": {"C1": "error"},
        "findings": [
            finding("test_submission.py", 7,
                    "R1. assert len(trace)==4 подтверждает только число событий, а не два чтения исходного остатка до первой записи. gather на строке 6 сам по себе не создаёт нужное пересечение: в reserve (submission.py:2–5) между чтением и записью нет точки приостановки. Приложенный тест проходит на последовательной трассе и потому не доказывает заявленный сценарий. Состояние реализации отдельно: исправление reserve для предотвращения потерянного обновления не было критерием задания; подтверждённого дефекта реализации по этому невыданному требованию нет.",
                    "Собственный запуск test_overlap завершился успешно. Отдельный запуск тех же двух reserve через gather дал trace=[('read',2),('write',1),('read',1),('write',0)], state=[0]. До первой записи только одно чтение исходного 2, ожидались два; длина трассы при этом действительно равна 4.",
                    "Построить детерминированный диагностический сценарий с управляемой точкой между чтением и записью (например, согласованным тестовым hook), затем проверять порядок событий и оба исходных значения. Для неизменённой reserve без такой точки честно фиксировать отсутствие пересечения; простое увеличение числа задач его не докажет. Не превращать диагностику в требование исправить демонстрационную reserve.")
        ],
        "next_step": "Предъявить диагностический тест и трассу, где два чтения исходного остатка предшествуют первой записи, с явной проверкой этого порядка; отдельно описать используемую точку управления расписанием."
    },
    {
        "case_id": "AD06", "classification": "environment", "verdict": "unverified",
        "criteria": {"C1": "unverified"},
        "findings": [
            finding("evidence.txt", 1,
                    "R1. Для текущей сдачи отсутствует требуемое runtime-доказательство Linux UID 10001: журнал прямо назван синтетическим, получен до изменения исходника, не содержит его хеш, после изменения запусков не было и стенд не предоставлен. Это пробел проверки, а не установленная ошибка прав доступа или кода. Доступная часть реализации submission.py:2 корректно читает текст и вызывает strip; локальная проба это подтвердила.",
                    "Собственный probe.py на darwin, Python 3.12.3, UID 501 прочитал локальный output/config-fixture.txt со строкой ' \\n\\tconfigured value\\t\\n ' и вернул 'configured value'. Это не запуск под Linux UID 10001 и не подтверждение прав на целевой файл. Приложенный журнал собственным запуском не считался; lab.invalid не посещался.",
                    "Для закрытия C1 предоставить доступный Linux-стенд или воспроизводимое свидетельство выполнения именно текущего исходника под UID 10001: версия/хеш файла, команда запуска, фактический UID, целевой путь и полученный текст. Затем повторить проверку в указанной среде; менять read_config без выявленной ошибки не требуется.")
        ],
        "next_step": "Предоставить runtime текущего read_config под Linux UID 10001 с привязкой к исходнику и результатом чтения/strip; после этого повторно проверить только оставшуюся часть C1."
    },
    {
        "case_id": "AD07", "classification": "code_defect", "verdict": "needs_changes",
        "criteria": {"C1": "error"},
        "findings": [
            finding("submission.py", 4,
                    "R1. Фильтр сравнивает только timestamp и исключает все пары с timestamp курсора. По контракту следующими являются и пары с тем же timestamp, но большим id. Сортировка и срез сами по себе верны, однако фильтр пропускает подходящие строки; это ошибка содержимого страницы.",
                    "Собственный запуск: rows=[(11,1),(10,2),(10,1),(10,3)], cursor=(10,1), limit=2. Получено [(11,1)], ожидалось [(10,2),(10,3)]. Вход rows не изменился. Пробы cursor=None и курсора после последней строки прошли.",
                    "Применять строгое лексикографическое сравнение всей пары (timestamp,id) с курсором до среза. Повторить границу внутри одинакового timestamp, начало без курсора и конец списка.")
        ],
        "next_step": "Исправить сравнение с курсором и повторить страницу, начинающуюся внутри группы одинаковых timestamp, вместе с уже работающими крайними случаями."
    },
    {
        "case_id": "AD08", "classification": "valid", "verdict": "accepted",
        "criteria": {"C1": "confirmed"}, "findings": [],
        "next_step": "C1 подтверждён: Counter считает целые пары и их кратности, не меняя входы. В 7225 локальных сравнениях результат совпал с независимой проверкой сортировкой; разная кратность и одинаковая сумма qty при разных парах отвергнуты. Следующий учебный шаг — объяснить на примере, почему мультимножество пар отличается от суммирования qty по SKU."
    }
]

answer = {
    "benchmark_version": metadata["benchmark_version"],
    "input_sha256": metadata["input_sha256"],
    "run": {
        "session_id": "/root/advanced_review",
        "model": "GPT-6 (доступное системное обозначение; точный runtime model ID не предоставлен)",
        "date": "2026-10-17", "kind": "model", "key_seen": False,
        "environment": {
            **probes["environment"],
            "read_scope": ["advanced/TEACHER.md", "advanced/run-metadata.json", "advanced/input/", "advanced/output/ (собственные выходы)"],
            "write_scope": "advanced/output/",
            "restrictions": "Без сети, lab.invalid, Docker, облака, новых агентов, исходного корпуса, авторских ключей, оценщиков и прошлых результатов. Входы не менялись; __pycache__ во входах не создавался.",
            "runtime_limit": "Linux UID 10001 для AD06 не предоставлен; локальный macOS UID 501 не заменяет обязательный runtime."
        }
    },
    "execution": "Реальные локальные запуски выполнены 2026-10-17: python3 -B docs/course-hardening-2026-10-17/advanced/output/probe.py; exit_code=0, Python 3.12.3, darwin, UID 501. AD01/AD02: по 6 групп сценариев повтора, конфликта, tenant и снимка; AD03/AD04: по 1360 комбинаций плюс 4 примера и идентичность возвращаемого stock; AD05: собственный запуск приложенного test_overlap и отдельная трасса asyncio.gather; AD06: только локальное чтение и strip; AD07: 4 сценария курсора; AD08: 7225 сравнений и 3 примера. Код также прочитан построчно. Хеши входных файлов до/после совпали. Детали в output/probe-results.json и output/method.txt. Синтетический журнал не является моим запуском.",
    "scope_notes": {
        "new_requirements": [],
        "optional_improvements": [],
        "assessment_subject": "Независимая оценка преподавателя на восьми синтетических сдачах; это не результат обучения настоящего ученика. Балл не вычислялся, авторский оценщик не читался и не запускался; объяснения требуют проверки человеком."
    },
    "reviews": reviews
}

# Validate only output structure and source locations; this is not an author scorer.
assert metadata["session_id"] == answer["run"]["session_id"]
assert probes["inputs_unchanged"]
assert len(reviews) == 8 and len({r["case_id"] for r in reviews}) == 8
for review in reviews:
    assert review["classification"] in {"code_defect", "valid", "test_defect", "environment", "new_requirement", "hypothesis"}
    assert review["verdict"] in {"accepted", "needs_changes", "unverified"}
    assert set(review["criteria"]) == {"C1"}
    for f in review["findings"]:
        lines = (BASE / "input" / review["case_id"] / f["file"]).read_text().splitlines()
        assert 1 <= f["line"] <= len(lines)

method = """Независимое ревью преподавателя; 2026-10-17; canonical session_id=/root/advanced_review.
Доступное имя модели: GPT-6; точный runtime model ID не предоставлен.
Это синтетические сдачи для оценки преподавателя, не результаты настоящего ученика.

Границы чтения: advanced/TEACHER.md, advanced/run-metadata.json, advanced/input/ и собственные выходы в advanced/output/.
Сначала прочитаны TEACHER.md и input/REVIEW.md; затем run-metadata.json, список входных файлов и построчно все assignment.md/submission.py/дополнительные материалы AD01–AD08.
Сеть, lab.invalid, Docker, облако и новые агенты не использовались. Исходный корпус, ключи, оценщики и предыдущие результаты не читались.
Входы неизменны: SHA-256 каждого файла до и после probe.py одинаков; полный перечень сохранён в probe-results.json. Python запущен с -B, дополнительно выставлен sys.dont_write_bytecode=True.

Метод: сопоставление ровно с C1 каждой assignment.md, чтение кода и собственные маленькие контрпримеры/проверки. probe.py содержит весь код проверок. Функции загружены из разрешённых входов; AD05 test_overlap вызван непосредственно, pytest не запускался.
Среда собственного запуска: macOS (sys.platform=darwin), Python 3.12.3, UID 501.

AD01: 6 групп проб, 3 успешны и 3 воспроизводят два независимых дефекта: token без tenant и поверхностная копия вложенных списков.
AD02: все 6 групп успешны; проверены повторы, конфликты, разные tenant с одинаковым/разным телом, сохранность снимка, порядок ключей, id и неизменность входа вызовом. По анализу поддерживается объявленный dict[str,list[int]]; изменение возвращённого объекта, конкуренция и внешнее удаление записей не добавлены в требования.
AD03: 4 явных примера и 1360 комбинаций запасов a,b от 0 до 3 и запросов длины 0–3 с qty 1/2. В 936 комбинациях нарушен хотя бы один аспект C1; это число не означает 936 независимых дефектов. Подтверждены две причины: отсутствие агрегации и мутация requests.sort(). Возвращается сам stock.
AD04: те же 1360 комбинаций без отклонений; явные примеры отказа, успеха и пустого запроса также соответствуют контракту, возвращается сам stock. По коду все проверки до единственного обновления stock, requests не мутируется.
AD05: приложенный test_overlap завершился успешно, но реальная трасса read2/write1/read1/write0 содержит лишь одно чтение исходного значения до первой записи. Дефект доказательства в тесте; исправления reserve для устранения потери обновления не требуются заданием.
AD06: собственное чтение фикстуры вернуло configured value без внешних пробелов. Linux UID 10001 для текущей сдачи не проверен: предоставленного стенда нет, синтетический журнал устарел и не связан хешем с текущим исходником. Не утверждается ни успех требуемого runtime, ни ошибка кода/прав.
AD07: 4 примера, два проходят и два воспроизводят потерю элементов с timestamp курсора и большим id; rows остаётся прежним.
AD08: 7225 пар коротких списков (длина 0–3, пары ('a',0),('a',1),('a',2),('b',-1)) сравнивались с sorted(left)==sorted(right); совпали все, мутаций входов нет. Отдельно проверены кратность, одинаковая сумма при разных парах и перестановка.

Приёмка опирается на анализ объявленной области и локальные пробы, а не на утверждение исчерпывающего тестирования любых данных. Новые требования и необязательные улучшения не добавлялись. Полные исправленные реализации не выдавались.

answer.json записывается один раз через режим x. Перед записью проверены структура, восемь ID и номера строк по разрешённым исходникам. Это самопроверка формата, не авторский оценщик. После фиксации исправление по оценщику не выполняется. SHA-256 ответа записывается отдельно в answer.sha256.
"""
commands = """cwd=/Users/ivanrogovskiy/Documents/tries/my_pet

1. cat docs/course-hardening-2026-10-17/advanced/TEACHER.md docs/course-hardening-2026-10-17/advanced/input/REVIEW.md docs/course-hardening-2026-10-17/advanced/run-metadata.json
   exit=0; прочитаны инструкции и метаданные.

2. rg --files docs/course-hardening-2026-10-17/advanced/input
   exit=0; получен список входных файлов.

3. python3 -B - <<'PY'
from pathlib import Path
root=Path('docs/course-hardening-2026-10-17/advanced/input')
for d in sorted(root.glob('AD*')):
    for p in sorted(d.iterdir()):
        if p.is_file():
            print('\\nFILE '+str(p.relative_to(root)))
            for i,line in enumerate(p.read_text().splitlines(),1):
                print(f'{i:3}: {line}')
PY
   exit=0; просмотрены все задания и сдачи с номерами строк.

4. tools.apply_patch: создан advanced/output/probe.py.
   Результат: успешно; исходные входы не редактировались.

5. python3 -B docs/course-hardening-2026-10-17/advanced/output/probe.py
   exit=0; wall_time_seconds=0.336028792; результаты полностью в probe-results.json.

6. tools.apply_patch: создан advanced/output/write_answer.py.
   Результат: успешно; в нём первый ответ и документирование метода.

7. python3 -B docs/course-hardening-2026-10-17/advanced/output/write_answer.py
   Записывает answer.json только при отсутствии файла, method.txt, commands.txt и answer.sha256; перед записью проверяет собственный формат и ссылки.
"""

with (OUT / "method.txt").open("x") as handle:
    handle.write(method)
with (OUT / "commands.txt").open("x") as handle:
    handle.write(commands)
encoded = (json.dumps(answer, ensure_ascii=False, indent=2) + "\n").encode()
with (OUT / "answer.json").open("xb") as handle:
    handle.write(encoded)
digest = sha256(encoded).hexdigest()
with (OUT / "answer.sha256").open("x") as handle:
    handle.write(digest + "  answer.json\n")
print(json.dumps({"answer": str(OUT / "answer.json"), "sha256": digest,
                  "reviews": len(reviews), "structure_and_locations": "valid",
                  "first_response_frozen": True}, ensure_ascii=False, indent=2))
