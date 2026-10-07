"""Author-only oracle and synthetic submissions. Exported bundles do not include this file."""
MONEY_CONTRACT = "C1: validate принимает целое число >=0 и возвращает его; boolean, строка, дробь и отрицательное число дают ValueError. Архитектура функции не предписана."
OWN_CONTRACT = "C1: can_read(actor, order, request) разрешает admin любой заказ, buyer только свой. request.user_id не даёт прав. Возвращается boolean."
GOOD_MONEY = '''def validate(value):
    if type(value) is not int or value < 0:
        raise ValueError("invalid money")
    return value
'''
GOOD_OWNER = '''def can_read(actor, order, request):
    return actor["role"] == "admin" or actor["id"] == order["owner_id"]
'''
CASES = [
    {"id":"RV01", "topic":"06/1", "assignment": MONEY_CONTRACT,
     "code":'''def validate(value):
    if isinstance(value, int) and value >= 0:
        return value
    raise ValueError("invalid money")
''', "classes":["code_defect"], "verdict":"needs_changes", "criterion":"error",
     "reason":"True принимается как 1: bool является подклассом int; C1 явно исключает boolean.", "probe":"money_bad"},
    {"id":"RV02", "topic":"07/2", "assignment":OWN_CONTRACT,
     "code":'''def can_read(actor, order, request):
    return actor["role"] == "admin" or actor["id"] == request["user_id"]
''', "classes":["code_defect"], "verdict":"needs_changes", "criterion":"error",
     "reason":"Buyer подставляет свой user_id и читает чужой order; источник права неверен.", "probe":"owner_bad"},
    {"id":"RV03", "topic":"08/3", "assignment":"C1: submit(state, buyer, key, payload) идемпотентен в области (buyer,key); иное тело с тем же ключом в той же области даёт ValueError. Другой buyer независим.",
     "code":'''def submit(state, buyer, key, payload):
    if key in state:
        return state[key]
    result = {"id": len(state) + 1, "payload": dict(payload)}
    state[key] = result
    return result
''', "classes":["code_defect"], "verdict":"needs_changes", "criterion":"error",
     "reason":"Ключ глобальный; другой покупатель получает чужой результат, другое тело не вызывает конфликт.", "probe":"idempotency_bad"},
    {"id":"RV04", "topic":"08/1", "assignment":"C1: reserve(stock, qty) уменьшает stock[0] на qty при достаточном остатке; при недостатке даёт ValueError и сохраняет исходный остаток. qty гарантированно положительное целое.",
     "code":'''def reserve(stock, qty):
    stock[0] -= qty
    if stock[0] < 0:
        raise ValueError("insufficient stock")
    return stock[0]
''', "classes":["code_defect"], "verdict":"needs_changes", "criterion":"error",
     "reason":"Исключение Python не откатывает мутацию списка: stock=1,qty=2 оставляет -1.", "probe":"stock_bad"},
    {"id":"RV05", "topic":"06/1", "assignment":MONEY_CONTRACT, "code":GOOD_MONEY,
     "classes":["valid"], "verdict":"accepted", "criterion":"confirmed",
     "reason":"type(value) is int допустим по контракту; необязательно заменять на isinstance или добавлять класс.", "probe":"money_good"},
    {"id":"RV06", "topic":"06/1", "assignment":MONEY_CONTRACT,
     "code":'''def validate(value):
    if isinstance(value, bool):
        raise ValueError("boolean")
    if not isinstance(value, int) or value < 0:
        raise ValueError("invalid money")
    return value
''', "classes":["valid"], "verdict":"accepted", "criterion":"confirmed",
     "reason":"Явное исключение bool — корректная альтернативная реализация; отдельные проверки допустимы.", "probe":"money_good"},
    {"id":"RV07", "topic":"07/2", "assignment":OWN_CONTRACT, "code":GOOD_OWNER,
     "classes":["valid"], "verdict":"accepted", "criterion":"confirmed",
     "reason":"Проверяется владелец заказа; неиспользуемый request не является нарушением приёмки.", "probe":"owner_good"},
    {"id":"RV08", "topic":"09/3", "assignment":"C1: rows() возвращает пары (id,amount) для заказов 1/100 и 2/200. Порядок результата не обещан. Проверить и реализацию, и приложенный тест.",
     "code":'''def rows():
    return [(2,200),(1,100)]
''', "extra":{"test_submission.py":"from submission import rows\n\ndef test_rows():\n    assert rows() == [(1,100),(2,200)]\n"},
     "classes":["test_defect"], "verdict":"needs_changes", "criterion":"confirmed",
     "reason":"C1 выполнен; исправлению подлежит тест, добавивший необъявленный порядок. Не требовать сортировки приложения.", "probe":"test_order"},
    {"id":"RV09", "topic":"11/3", "assignment":"C1: подтвердить HTTP 200 /health на предоставленном Linux-стенде. По одному коду приёмка недопустима. Адрес и журнал — в environment.txt.",
     "code":'''from urllib.request import urlopen
def health(url):
    with urlopen(url, timeout=3) as response:
        return response.status
''', "extra":{"environment.txt":"Синтетическая запись: https://lab.invalid/health; DNS resolution failed до TCP. Доступного стенда в этом пакете нет. Команда не выполнялась проверяющим.\n"},
     "classes":["environment"], "verdict":"unverified", "criterion":"unverified",
     "reason":"Нет runtime-доказательства. DNS-ограничение не доказывает ошибку Python/health endpoint.", "probe":"no_runtime"},
    {"id":"RV10", "topic":"06/1", "assignment":"Версия v1. C1: quantity принимает положительное целое (кроме bool), остальные значения отвергает. Верхний лимит не задан. Приложено новое предложение reviewer-note.md, оно ещё не принято.",
     "code":'''def quantity(value):
    if type(value) is not int or value <= 0:
        raise ValueError("invalid quantity")
    return value
''', "extra":{"reviewer-note.md":"Предложение для v2: запретить количество >100. Это новое бизнес-условие, отсутствовавшее в v1.\n"},
     "classes":["new_requirement"], "verdict":"accepted", "criterion":"confirmed",
     "reason":"101 допустимо по v1; новое ограничение не повод отклонять прежнюю работу.", "probe":"quantity_good"},
    {"id":"RV11", "topic":"08/2", "assignment":"C1: подтвердить два конкурентных заказа на последнюю единицу реальным PostgreSQL-тестом. Есть SQL и последовательный fake-тест, конкурентного прогона нет. Отделить вывод по коду от доказательства выполнения C1.",
     "code":'''def reserve(connection, sku):
    cursor = connection.execute("UPDATE stock SET qty=qty-1 WHERE sku=%s AND qty>=1", (sku,))
    return cursor.rowcount == 1
''', "extra":{"evidence.txt":"Синтетическая сдача: fake cursor поочерёдно вернул rowcount 1 и 0. PostgreSQL не запускался. Замечание для обсуждения: возможно ли двойное резервирование?\n"},
     "classes":["hypothesis","environment"], "verdict":"unverified", "criterion":"unverified",
     "reason":"C1 не проверен. Нельзя объявить найденную гонку по этому fake-тесту или засчитать конкурентный сценарий.", "probe":"no_runtime"},
    {"id":"RV12", "topic":"13/1", "assignment":"C1: total(items) суммирует price*qty; items — список словарей с уже проверенными неотрицательными целыми. Возвращает 0 для пустого списка. Стиль, слои и классы не предписаны.",
     "code":'''def total(items):
    result = 0
    for item in items:
        result = result + item["price"] * item["qty"]
    return result
''', "classes":["valid"], "verdict":"accepted", "criterion":"confirmed",
     "reason":"Цикл корректен. sum(), dataclass и service class могут быть советами, но не условиями приёмки.", "probe":"total_good"},
]


def rejected(function, value):
    try:
        function(value)
    except ValueError:
        return True
    return False


def verify_case(case):
    """Verify the authored fixture, not the model's prose or a student's real skill."""
    namespace = {}
    exec(compile(case["code"], case["id"] + "/submission.py", "exec"), namespace)
    probe = case["probe"]
    if probe.startswith("money"):
        fn = namespace["validate"]
        if probe == "money_bad":
            return fn(True) is True
        return fn(0) == 0 and fn(175) == 175 and all(rejected(fn,v) for v in (True,False,-1,1.5,"5",None))
    if probe.startswith("owner"):
        fn = namespace["can_read"]
        buyer = {"id":1,"role":"buyer"}
        other = {"owner_id":2}
        leaked = fn(buyer, other, {"user_id":1})
        if probe == "owner_bad":
            return leaked is True
        return leaked is False and fn(buyer,{"owner_id":1},{"user_id":2}) is True and fn({"id":3,"role":"admin"},other,{"user_id":9}) is True
    if probe == "idempotency_bad":
        state = {}
        first = namespace["submit"](state,1,"k",{"qty":1})
        return namespace["submit"](state,2,"k",{"qty":2}) == first
    if probe == "stock_bad":
        stock = [1]
        try:
            namespace["reserve"](stock,2)
        except ValueError:
            return stock == [-1]
        return False
    if probe == "test_order":
        rows = namespace["rows"]()
        return sorted(rows) == [(1,100),(2,200)] and rows != [(1,100),(2,200)]
    if probe == "quantity_good":
        return namespace["quantity"](101) == 101 and rejected(namespace["quantity"],0)
    if probe == "total_good":
        return namespace["total"]([]) == 0 and namespace["total"]([{"price":100,"qty":2},{"price":300,"qty":1}]) == 500
    return probe == "no_runtime"  # Deliberately no network/DB evidence fabricated.
