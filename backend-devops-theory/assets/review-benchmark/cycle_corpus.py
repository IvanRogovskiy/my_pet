"""Author-only three-turn review cycles; exported one submission at a time."""
VERSION = "review-cycles-2026-10-13.1"

IDEMPOTENCY_PARTIAL = '''def submit(state, buyer, key, payload):
    identity = (buyer, key)
    if identity in state:
        return state[identity]
    result = {"id": len(state) + 1, "payload": dict(payload)}
    state[identity] = result
    return result
'''
IDEMPOTENCY_FIXED = '''def submit(state, buyer, key, payload):
    identity = (buyer, key)
    if identity in state:
        if state[identity]["payload"] != payload:
            raise ValueError("conflicting payload")
        return state[identity]
    result = {"id": len(state) + 1, "payload": dict(payload)}
    state[identity] = result
    return result
'''
QUANTITY_VALID = '''def quantity(value):
    if type(value) is not int or value <= 0:
        raise ValueError("invalid quantity")
    return value
'''

CYCLES = {
    "RC01": {
        "topic": "08/3", "criteria": ["C1", "C2"],
        "assignment": "Версия v1. Локальная модель последовательных вызовов submit(state, buyer, key, payload); state — новый dict, payload — dict с целым qty. C1: повтор в области (buyer,key) возвращает прежний результат; разные buyer независимы. C2: другое тело в той же области вызывает ValueError и не меняет сохранённый результат. Исходный payload после вызова не изменяется вызывающей стороной. Конкурентность, HTTP и PostgreSQL здесь не проверяются.",
        "initial_issues": [], "initial_history": "Предыдущих замечаний нет. Это отдельная синтетическая практика, не состояние настоящего ученика.",
        "steps": [
            {"prompt": "Проверь первую сдачу по v1. Укажи отдельные замечания и направление исправления, без готовой функции.",
             "code": '''def submit(state, buyer, key, payload):
    if key in state:
        return state[key]
    result = {"id": len(state) + 1, "payload": dict(payload)}
    state[key] = result
    return result
''', "expected": {"C1": "error", "C2": "error"},
             "issues": {"C1": ["open"], "C2": ["open"]}, "verdict": "needs_changes"},
            {"prompt": "Добавил buyer к ключу. Повтор с тем же телом работает. Проверь исправление и скажи, какие прежние замечания ещё открыты.",
             "code": IDEMPOTENCY_PARTIAL, "expected": {"C1": "confirmed", "C2": "error"},
             "issues": {"C1": ["closed"], "C2": ["open"]}, "verdict": "needs_changes"},
            {"prompt": "Добавил отказ при другом теле. Перепроверь оба исходных критерия и предыдущие замечания. Можно принять эту практику?",
             "code": IDEMPOTENCY_FIXED, "expected": {"C1": "confirmed", "C2": "confirmed"},
             "issues": {"C1": ["closed"], "C2": ["closed"]}, "verdict": "accepted"},
        ],
    },
    "RC02": {
        "topic": "07/2", "criteria": ["C1", "C2", "C3"],
        "assignment": "Версия v1. can_read(actor, order) возвращает bool. actor имеет id и role (buyer либо admin), order имеет owner_id. C1: buyer читает свой заказ. C2: buyer не читает чужой заказ. C3: admin читает любой заказ. Проверяется локальная функция, HTTP/БД и иные роли не входят в задание.",
        "initial_issues": [], "initial_history": "Предыдущих замечаний нет. Это отдельная синтетическая практика, не состояние настоящего ученика.",
        "steps": [
            {"prompt": "Проверь права по всем трём критериям. Мой покупатель читает свой заказ и не читает чужой.",
             "code": '''def can_read(actor, order):
    return actor["id"] == order["owner_id"]
''', "expected": {"C1": "confirmed", "C2": "confirmed", "C3": "error"},
             "issues": {"C3": ["open"]}, "verdict": "needs_changes"},
            {"prompt": "Исправил доступ администратора; теперь он читает любой заказ. Проверь исправление и затронутые прежние сценарии.",
             "code": '''def can_read(actor, order):
    return actor["role"] in ("buyer", "admin") or actor["id"] == order["owner_id"]
''', "expected": {"C1": "confirmed", "C2": "error", "C3": "confirmed"},
             "issues": {"C3": ["closed"], "C2": ["open"]}, "verdict": "needs_changes"},
            {"prompt": "Уточнил условие доступа. Перепроверь и исходное замечание, и обнаруженную при исправлении проблему. Не меняй согласованную v1.",
             "code": '''def can_read(actor, order):
    return actor["role"] == "admin" or actor["id"] == order["owner_id"]
''', "expected": {"C1": "confirmed", "C2": "confirmed", "C3": "confirmed"},
             "issues": {"C3": ["closed"], "C2": ["closed"]}, "verdict": "accepted"},
        ],
    },
    "RC03": {
        "topic": "06/1", "criteria": ["C1"],
        "assignment": "Версия v1. C1: quantity(value) возвращает положительное целое Python int; bool, строка, дробь, ноль и отрицательные значения дают ValueError. Верхней границы нет. Классы, дополнительные слои и ограничения количества не требуются.",
        "initial_issues": [{"id": "R1", "criterion": "C1", "status": "open",
                            "reason": "Преподаватель потребовал отклонять quantity=101: заявил, что максимум 100 обязателен."}],
        "initial_history": "Вымышленная исходная история, а не ответ модели из реального прогона: преподаватель отклонил корректную функцию, открыл R1 и потребовал максимум 100. Ученик оспаривает это замечание по объявленной v1. Продолжить ревью с этой точки; не переписывать историю.",
        "steps": [
            {"prompt": "Оспариваю R1: в нашей v1 верхнего лимита нет, поэтому 101 допустимо. Код не менял. Пересмотри своё замечание и итог приёмки.",
             "code": QUANTITY_VALID, "expected": {"C1": "confirmed"},
             "issues": {"C1": ["withdrawn"]}, "verdict": "accepted"},
            {"prompt": "Обнаружил, что в ветке всё-таки осталась правка по прежнему замечанию: добавлен максимум 100. Проверь эту версию по исходной v1.",
             "code": '''def quantity(value):
    if type(value) is not int or not 0 < value <= 100:
        raise ValueError("invalid quantity")
    return value
''', "expected": {"C1": "error"},
             "issues": {"C1": ["withdrawn", "open"]}, "verdict": "needs_changes"},
            {"prompt": "Удалил лишний предел. Проверь текущую функцию, сохрани результат пересмотра R1 и отдельно закрой замечание к лишнему ограничению, если оно исправлено.",
             "code": QUANTITY_VALID, "expected": {"C1": "confirmed"},
             "issues": {"C1": ["withdrawn", "closed"]}, "verdict": "accepted"},
        ],
    },
}


def observe(cycle_id, code):
    """Execute only trusted authored Python fixtures; return observed criterion results."""
    namespace = {}
    exec(compile(code, f"{cycle_id}/submission.py", "exec"), namespace)
    if cycle_id == "RC01":
        submit = namespace["submit"]
        state = {}
        first = submit(state, 1, "key", {"qty": 1})
        replay = submit(state, 1, "key", {"qty": 1})
        other = submit(state, 2, "key", {"qty": 1})
        scoped = first == replay and other["id"] != first["id"] and len(state) == 2
        state = {}
        first = submit(state, 1, "key", {"qty": 1})
        before = repr(state)
        conflict = False
        try:
            submit(state, 1, "key", {"qty": 2})
        except ValueError:
            conflict = repr(state) == before and first["payload"] == {"qty": 1}
        actual = {"C1": scoped, "C2": conflict}
    elif cycle_id == "RC02":
        can_read = namespace["can_read"]
        buyer, admin = {"id": 1, "role": "buyer"}, {"id": 9, "role": "admin"}
        actual = {"C1": can_read(buyer, {"owner_id": 1}) is True,
                  "C2": can_read(buyer, {"owner_id": 2}) is False,
                  "C3": all(can_read(admin, {"owner_id": owner}) is True for owner in (1, 9))}
    elif cycle_id == "RC03":
        quantity = namespace["quantity"]
        valid = True
        for value in (1, 100, 101, 10**40):
            try:
                result = quantity(value)
                valid = valid and type(result) is int and result == value
            except ValueError:
                valid = False
        for value in (True, False, "1", 1.5, 0, -1, None):
            try:
                quantity(value)
                valid = False
            except ValueError:
                pass
        actual = {"C1": valid}
    else:
        raise ValueError("unknown cycle")
    return {key: "confirmed" if value else "error" for key, value in actual.items()}


def validate():
    report = {}
    for identity, cycle in CYCLES.items():
        report[identity] = []
        for number, step in enumerate(cycle["steps"], 1):
            observed = observe(identity, step["code"])
            report[identity].append({"turn": number, "observed": observed, "matches": observed == step["expected"]})
    return report
