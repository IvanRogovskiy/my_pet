"""Author-only development and reserved control cases. Do not export keys."""
from holdout_corpus import case

VERSION = "advanced-2026-10-17.1"


def entry(identity, topic, assignment, code, category, reason, defects=(), extra=None):
    value = case(identity, topic, assignment, code, category, reason, extra)
    value["defects"] = [{"id": f"D{i}", "criterion": text} for i, text in enumerate(defects, 1)]
    return value


JOB = ("enqueue(jobs, tenant, token, payload) работает последовательно в памяти. Область повтора — "
       "(tenant,token). payload — dict[str,list[int]]. Точный повтор возвращает равный результат без новой "
       "записи, изменённое тело в той же области даёт ValueError. Другой tenant независим. "
       "Изменение входных списков после вызова не должно менять сохранённое тело. "
       "Входные payload нельзя менять. Результат содержит уникальный id и снимок payload. "
       "Мутация возвращённого результата вызывающим кодом не входит в контракт.")
BATCH = ("allocate(stock, requests) работает последовательно в памяти. stock — dict[str,int>=0], "
         "requests — list[tuple[str,int>0]], все SKU существуют. Повторяющиеся SKU нужно суммировать. "
         "При нехватке ValueError и stock неизменен; при успехе списать весь пакет и вернуть stock. "
         "requests должен оставаться неизменным даже при отказе. Конкуренция/БД здесь не требуются.")

DEVELOPMENT = [
    entry("AD01", "08/3", JOB, '''def enqueue(jobs, tenant, token, payload):
    if token in jobs:
        if jobs[token]["payload"] != payload:
            raise ValueError("conflict")
        return jobs[token]
    result = {"id": len(jobs) + 1, "payload": dict(payload)}
    jobs[token] = result
    return result
''', "code_defect", "Два независимых дефекта: потеря tenant и alias вложенных списков.",
          ("Повтор ошибочно глобален по token: другой tenant получает чужой результат или конфликт.",
           "dict(payload) копирует только верхний уровень: последующая мутация входного списка меняет историю.")),
    entry("AD02", "08/3", JOB, '''from copy import deepcopy
def enqueue(jobs, tenant, token, payload):
    scope = (tenant, token)
    frozen = tuple(sorted((key, tuple(values)) for key, values in payload.items()))
    if scope in jobs:
        old = jobs[scope]
        if old["fingerprint"] != frozen:
            raise ValueError("conflict")
        return old["result"]
    result = {"id": len(jobs) + 1, "payload": deepcopy(payload)}
    jobs[scope] = {"fingerprint": frozen, "result": result}
    return result
''', "valid", "Необычная канонизация допустима: порядок ключей dict не значим, порядок списка сохранён."),
    entry("AD03", "08/1", BATCH, '''def allocate(stock, requests):
    requests.sort()
    if any(stock[sku] < qty for sku, qty in requests):
        raise ValueError("insufficient")
    for sku, qty in requests:
        stock[sku] -= qty
    return stock
''', "code_defect", "Независимые ошибки суммирования и мутации аргумента.",
          ("Проверка строк отдельно пропускает превышение суммарного спроса повторяющегося SKU.",
           "requests.sort меняет входной список, включая путь отказа.")),
    entry("AD04", "08/1", BATCH, '''from collections import Counter
def allocate(stock, requests):
    totals = Counter()
    for sku, qty in requests:
        totals[sku] += qty
    after = {sku: stock[sku] - qty for sku, qty in totals.items()}
    if any(value < 0 for value in after.values()):
        raise ValueError("insufficient")
    stock.update(after)
    return stock
''', "valid", "Сначала полный расчёт и проверка, затем единственная публикация изменений."),
    entry("AD05", "14/2", "Проверить, доказывает ли test_overlap пересечение чтений двух операций. "
          "Нужно увидеть два чтения исходного остатка до первой записи. Потеря обновления — цель "
          "диагностического теста, а не требование исправить приложенную демонстрационную reserve.", '''async def reserve(state, trace):
    before = state[0]
    trace.append(("read", before))
    state[0] = before - 1
    trace.append(("write", state[0]))
    return state[0]
''', "test_defect", "gather не создаёт переключение внутри корутины без await; тест не проверяет нужный порядок.",
          ("Тест принимает последовательный trace; запуск двух корутин не доказывает пересечение чтений.",),
          {"test_submission.py": '''import asyncio
from submission import reserve
def test_overlap():
    async def run():
        state, trace = [2], []
        await asyncio.gather(reserve(state, trace), reserve(state, trace))
        assert len(trace) == 4
    asyncio.run(run())
'''}),
    entry("AD06", "11/3", "Подтвердить для приложенной версии read_config чтение файла приложением от Linux UID 10001. "
          "Возвращать текст без внешних пробелов. Нужны и корректный код, и runtime именно этой сдачи.", '''def read_config(path):
    return path.read_text().strip()
''', "hypothesis", "Зелёный журнал от другой сдачи не привязан к этому коду; дефект чтения не доказан.", extra={
        "evidence.txt": "Синтетический журнал: Linux UID=10001, check=passed. Журнал получен до изменения submission.py; "
                        "хеш исходника не записан. После изменения запусков не было. Текущий стенд не предоставлен.\n"}),
    entry("AD07", "06/2", "page(rows, cursor, limit) получает list[(timestamp:int,id:int)], пары уникальны. "
          "Вернуть первые limit пар строго после cursor в лексикографическом порядке (timestamp,id). "
          "cursor=None начинает с начала; limit — положительное целое; rows не менять.", '''def page(rows, cursor, limit):
    ordered = sorted(rows)
    if cursor is not None:
        ordered = [row for row in ordered if row[0] > cursor[0]]
    return ordered[:limit]
''', "code_defect", "Курсор теряет второй компонент; строки с той же меткой времени пропущены.",
          ("Строгое сравнение только timestamp пропускает большие id при равном timestamp.",)),
    entry("AD08", "09/2", "same_items(left,right) сравнивает два list[(sku:str,qty:int)] как мультимножества пар. "
          "Порядок не важен, кратности важны, входы не менять. Суммировать qty или разбивать пары нельзя.", '''from collections import Counter
def same_items(left, right):
    return Counter(left) == Counter(right)
''', "valid", "Counter считает полные пары и сохраняет кратности; сортировка не обязательна."),
]
# The diagnostic demonstration is intentionally unsafe; only its test is graded.
DEVELOPMENT[4]["criterion"] = "error"

CONTROL = [
    entry("AH01", "17/3", "handle(event, seen, effect) вызывается последовательно; seen — множество, effect может "
          "выбросить исключение до эффекта. После такого отказа повтор должен снова попытаться выполнить effect. "
          "После успеха повтор не выполняет эффект. Падение процесса и конкуренция вне этого задания.", '''def handle(event, seen, effect):
    if event["id"] in seen:
        return
    seen.add(event["id"])
    effect(event["payload"])
''', "code_defect", "Маркер остаётся после неуспешного эффекта и подавляет повтор.",
          ("Исключение effect оставляет преждевременный seen; повтор теряет обязательный эффект.",)),
    entry("AH02", "07/2", "allowed(actor, resource) возвращает bool: owner имеет доступ только к своему ресурсу, "
          "admin — ко всем, остальные роли — ни к одному. ID — строки; аргументы не менять.", '''def allowed(actor, resource):
    permissions = {
        "admin": True,
        "owner": actor["id"] == resource["owner_id"],
    }
    return permissions.get(actor["role"], False)
''', "valid", "Таблица разрешений корректна; иная форма ветвления не требуется."),
    entry("AH03", "29/3", "Подтвердить восстановление резервной копии: контрольная запись заказа o-7 должна "
          "читаться из восстановленной БД. service_ok только проверяет доступность процесса.", '''def service_ok(client):
    return client.get("/health").status_code == 200
''', "hypothesis", "HTTP health не свидетельствует о восстановлении контрольной записи.", extra={
        "evidence.txt": "Синтетический журнал: /health 200; restore и чтение o-7 не выполнялись. БД не предоставлена.\n"}),
    entry("AH04", "09/2", "pairs() должен вернуть [('a',2),('b',3)] в любом порядке. "
          "Оценить достаточность приложенного теста, реализация здесь — тестовый двойник с ошибкой.", '''def pairs():
    return [("a", 3), ("b", 2)]
''', "test_defect", "Раздельная сортировка теряет соответствие ключей и значений; тест пропускает дефект.",
          ("Тест сравнивает проекции отдельно и принимает неверные пары.",), extra={
        "test_submission.py": '''from submission import pairs
def test_pairs():
    actual = pairs()
    assert sorted(k for k, _ in actual) == ["a", "b"]
    assert sorted(v for _, v in actual) == [2, 3]
'''}),
]
CONTROL[3]["criterion"] = "error"


def cases_for(split):
    if split not in ("development", "control"):
        raise ValueError("unknown advanced split")
    return DEVELOPMENT if split == "development" else CONTROL


def verify(case):
    ns = {}
    exec(compile(case["code"], case["id"] + "/submission.py", "exec"), ns)
    identity = case["id"]
    if identity in ("AD01", "AD02"):
        fn, jobs, payload = ns["enqueue"], {}, {"parts": [2, 1]}
        first = fn(jobs, "a", "k", payload)
        other = fn(jobs, "b", "k", payload)
        scope_ok = first["id"] != other["id"]
        payload["parts"].append(9)
        snapshot_ok = first["payload"] == {"parts": [2, 1]}
        if identity == "AD01":
            return {"tenant": not scope_ok, "nested_snapshot": not snapshot_ok}
        try:
            fn(jobs, "a", "k", payload)
        except ValueError:
            return {"tenant": scope_ok, "nested_snapshot": snapshot_ok,
                    "replay": fn(jobs, "a", "k", {"parts": [2, 1]}) == first}
        return {"conflict": False}
    if identity in ("AD03", "AD04"):
        stock, requests = {"a": 3, "b": 1}, [("b", 1), ("a", 2), ("a", 2)]
        before, original = dict(stock), list(requests)
        try:
            ns["allocate"](stock, requests)
            refused = False
        except ValueError:
            refused = True
        if identity == "AD03":
            return {"aggregate": not refused and stock["a"] == -1,
                    "input_mutation": requests != original}
        good = {"a": 4, "b": 1}
        ns["allocate"](good, original)
        return {"atomic_reject": refused and stock == before,
                "input_unchanged": requests == original, "success": good == {"a": 0, "b": 0}}
    if identity == "AD05":
        import asyncio
        async def run():
            trace, state = [], [2]
            await asyncio.gather(ns["reserve"](state, trace), ns["reserve"](state, trace))
            return trace
        trace = asyncio.run(run())
        return {"serial": [row[0] for row in trace] == ["read", "write", "read", "write"],
                "weak_assertion_passes": len(trace) == 4}
    if identity == "AD07":
        rows = [(5, 3), (5, 2), (6, 1)]
        return {"skipped_tie": ns["page"](rows, (5, 2), 2) == [(6, 1)],
                "source_preserved": rows == [(5, 3), (5, 2), (6, 1)]}
    if identity == "AD08":
        fn = ns["same_items"]
        a = [("a", 2), ("b", 3), ("a", 2)]
        return {"order": fn(a, list(reversed(a))), "multiplicity": not fn(a, a[:2]),
                "pairing": not fn(a[:2], [("a", 3), ("b", 2)])}
    if identity == "AH01":
        seen, effects = set(), []
        def fail(_):
            raise ValueError("before effect")
        try:
            ns["handle"]({"id": "e", "payload": 1}, seen, fail)
        except ValueError:
            pass
        ns["handle"]({"id": "e", "payload": 1}, seen, effects.append)
        return {"lost_retry": seen == {"e"} and effects == []}
    if identity == "AH02":
        fn = ns["allowed"]
        return {"matrix": all(fn({"role": role, "id": "a"}, {"owner_id": owner}) is expected
                for role, owner, expected in [("owner", "a", True), ("owner", "b", False),
                                              ("admin", "b", True), ("guest", "a", False)])}
    if identity == "AH04":
        actual = ns["pairs"]()
        return {"wrong_pairs": sorted(actual) != [("a", 2), ("b", 3)],
                "weak_assertions_pass": sorted(k for k, _ in actual) == ["a", "b"] and sorted(v for _, v in actual) == [2, 3]}
    return {"limited_evidence_only": identity in ("AD06", "AH03") and bool(case["extra"]["evidence.txt"])}
