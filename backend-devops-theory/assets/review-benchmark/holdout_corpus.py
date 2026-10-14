"""Author-only control set. Never include this module in reviewer inputs."""
VERSION = "holdout-2026-10-14.1"


def case(identity, topic, assignment, code, category, reason, extra=None):
    accepted = category in ("valid", "new_requirement")
    unknown = category in ("environment", "hypothesis")
    return dict(id=identity, topic=topic, assignment="C1: " + assignment, code=code,
                classes=[category], reason=reason, extra=extra or {},
                verdict="accepted" if accepted else "unverified" if unknown else "needs_changes",
                criterion="confirmed" if accepted or category == "test_defect" else "unverified" if unknown else "error")


ACCESS = "can_edit(actor, document) разрешает editor изменять только документ своей команды; admin — любой. Роли только editor/admin, ID — строки. Возвращается bool."
DEBIT = "debit(wallet, amount) списывает положительное целое amount из wallet['balance']; при нехватке даёт ValueError и оставляет словарь неизменным. balance — неотрицательное целое."
MONEY = "cents(raw) принимает строку с конечным десятичным числом рублей >=0, кратным 0.01, и возвращает точное целое число копеек. Остальное даёт ValueError. Экспоненциальная запись допустима. Входы гарантированно имеют тип str, длину до 80 символов и модуль явно указанной экспоненты не больше 100."
CACHE = "remember(cache, tenant, token, body) возвращает сохранённый результат для одинаковых tenant/token/body; иное тело в той же области даёт ValueError. Tenant независим. body — словарь строк; входные словари нельзя менять."

CASES = [
    case("HC01", "07/2", ACCESS, '''def can_edit(actor, document):
    return actor["role"] == "admin" or actor["team_id"] in document["team_id"]
''', "code_defect", "Подстрока team-a ошибочно получает доступ к team-ab; требуется равенство ID."),
    case("HC02", "07/2", ACCESS, '''def can_edit(actor, document):
    if actor["role"] == "admin":
        return True
    return actor["team_id"] == document["team_id"]
''', "valid", "Ветвление и равенство удовлетворяют двум объявленным ролям."),
    case("HC03", "08/1", DEBIT, '''def debit(wallet, amount):
    before = wallet
    wallet["balance"] -= amount
    if wallet["balance"] < 0:
        wallet.update(before)
        raise ValueError("insufficient")
    return wallet["balance"]
''', "code_defect", "before — ссылка на изменяемый словарь; update не восстанавливает исходное состояние."),
    case("HC04", "08/1", DEBIT, '''def debit(wallet, amount):
    remaining = wallet["balance"] - amount
    if remaining < 0:
        raise ValueError("insufficient")
    wallet["balance"] = remaining
    return remaining
''', "valid", "Проверка предшествует единственной мутации."),
    case("HC05", "06/1", MONEY, '''from decimal import Decimal, InvalidOperation
def cents(raw):
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("invalid") from exc
    if not value.is_finite() or value < 0:
        raise ValueError("invalid")
    return int(value * 100)
''', "code_defect", "1.001 молча усечён до 100 копеек вместо ValueError."),
    case("HC06", "06/1", MONEY, '''from decimal import Decimal, InvalidOperation
def cents(raw):
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("invalid") from exc
    if not value.is_finite() or value < 0:
        raise ValueError("invalid")
    numerator, denominator = value.as_integer_ratio()
    whole, remainder = divmod(numerator * 100, denominator)
    if remainder:
        raise ValueError("fraction of a cent")
    return whole
''', "valid", "Точное отношение сохраняет длинные числа; остаток выявляет долю копейки."),
    case("HC07", "08/3", CACHE, '''def remember(cache, tenant, token, body):
    key = (tenant, token)
    if key in cache:
        old = cache[key]
        if set(old["body"]) != set(body):
            raise ValueError("conflict")
        return old
    result = {"id": len(cache) + 1, "body": dict(body)}
    cache[key] = result
    return result
''', "code_defect", "Сравниваются имена полей, но изменение значения qty остаётся незамеченным."),
    case("HC08", "08/3", CACHE, '''def remember(cache, tenant, token, body):
    key = (tenant, token)
    if key in cache:
        if cache[key]["body"] != body:
            raise ValueError("conflict")
        return cache[key]
    result = {"id": len(cache) + 1, "body": dict(body)}
    cache[key] = result
    return result
''', "valid", "Область и сравнение тела корректны, вход скопирован."),
    case("HC09", "09/3", "pairs() возвращает [('a',2),('b',3)] в любом порядке. Проверить реализацию и тест.", '''def pairs():
    return [("b", 3), ("a", 2)]
''', "test_defect", "Тест требует фиксированный порядок колонок, хотя порядок пар не объявлен.",
         {"test_submission.py": '''from submission import pairs
def test_pairs():
    actual = pairs()
    assert [key for key, _ in actual] == ["a", "b"]
    assert [value for _, value in actual] == [2, 3]
'''}),
    case("HC10", "11/3", "read_secret(path) читает текст файла и возвращает строку без начальных и конечных пробельных символов. На предоставленном Linux-стенде подтвердить чтение файлом приложения от UID 10001; локальный запуск от другого UID недостаточен.", '''def read_secret(path):
    return path.read_text().strip()
''', "environment", "Отказ Docker socket возникает до запуска приложения; доступ UID 10001 не проверен.",
         {"evidence.txt": "Синтетический журнал: docker run завершился permission denied while connecting to Docker socket; контейнер не создан. Другой Linux-стенд не предоставлен. Секретов в пакете нет.\n"}),
    case("HC11", "06/1", "Версия v1: label(value) принимает непустую строку, включая пробелы по краям, и возвращает её без изменений. Нестрочные и пустая строка дают ValueError. Приложено непринятое предложение v2.", '''def label(value):
    if not isinstance(value, str) or not value:
        raise ValueError("invalid")
    return value
''', "new_requirement", "strip изменил бы объявленное поведение v1.",
         {"reviewer-note.md": "Предложение v2: обрезать внешние пробелы и запрещать строку только из пробелов. В v1 этого нет.\n"}),
    case("HC12", "17/3", "Подтвердить устойчивость consumer при падении после бизнес-эффекта до ack: повтор не создаёт второй эффект. effect_once по договору атомарно фиксирует event_id вместе с эффектом в БД. Нужен crash/replay-тест реальной связки БД и брокера.", '''def consume(event, effect_once, ack):
    effect_once(event["id"], event["payload"])
    ack()
''', "hypothesis", "Порядок вызовов согласуется с контрактом effect_once, но обычный fake не подтверждает crash/replay.",
         {"evidence.txt": "Синтетическая сдача: fake записал effect_once затем ack; вызов один. БД, брокер и crash/replay не запускались. Вопрос ученика: дубли точно исключены?\n"}),
]


def verify(case):
    ns = {}
    exec(compile(case["code"], case["id"] + "/submission.py", "exec"), ns)
    identity = case["id"]
    if identity in ("HC01", "HC02"):
        fn = ns["can_edit"]
        actor = {"role": "editor", "team_id": "team-a"}
        other = fn(actor, {"team_id": "team-ab"})
        return other is (identity == "HC01") and fn(actor, {"team_id": "team-a"}) is True and fn({"role": "admin"}, {"team_id": "x"}) is True
    if identity in ("HC03", "HC04"):
        wallet = {"balance": 2, "tag": "unchanged"}
        try:
            ns["debit"](wallet, 3)
        except ValueError:
            expected = -1 if identity == "HC03" else 2
            return wallet == {"balance": expected, "tag": "unchanged"} and ns["debit"]({"balance": 3}, 2) == 1
        return False
    if identity in ("HC05", "HC06"):
        fn = ns["cents"]
        if identity == "HC05":
            return fn("1.001") == 100
        for raw, expected in (("0", 0), ("1.20", 120), ("1e2", 10000), ("123456789012345678901234567890.12", 12345678901234567890123456789012)):
            if fn(raw) != expected:
                return False
        for raw in ("1.001", "-0.01", "NaN", "Infinity", "oops"):
            try:
                fn(raw)
            except ValueError:
                continue
            return False
        return True
    if identity in ("HC07", "HC08"):
        fn, state, body = ns["remember"], {}, {"qty": "2"}
        first = fn(state, "a", "k", body)
        if fn(state, "a", "k", body) != first or fn(state, "b", "k", body) == first:
            return False
        try:
            changed = fn(state, "a", "k", {"qty": "3"})
        except ValueError:
            return identity == "HC08" and body == {"qty": "2"}
        return identity == "HC07" and changed == first
    if identity == "HC09":
        code = case["extra"]["test_submission.py"].split("\n", 1)[1]
        test = {"pairs": ns["pairs"]}
        exec(code, test)
        try:
            test["test_pairs"]()
        except AssertionError:
            return sorted(ns["pairs"]()) == [("a", 2), ("b", 3)]
        return False
    if identity == "HC11":
        return ns["label"](" x ") == " x " and ns["label"](" ") == " "
    # These checks validate only the presence of explicitly limited evidence.
    return identity in ("HC10", "HC12") and bool(case["extra"]["evidence.txt"])
