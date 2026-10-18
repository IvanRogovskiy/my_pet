"""Author-only fixtures derived from F05/F07/F08/F11/F12/F40. No live services."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile


DEPLOY_CONTRACT = (
    "C1: deploy(service, config) применяет конфигурацию. При её изменении вызывается "
    "restart() и возвращается changed=1; повтор с тем же config сохраняет config и "
    "generation, возвращает changed=0. Предоставленная модель service имеет строку "
    "config и счётчик generation; restart() увеличивает generation на один. "
    "Это локальная модель эффекта перезапуска, не проверка настоящего Ansible/systemd."
)
JSON_CONTRACT = (
    "C1: quantity(raw) принимает исходный JSON одного математически целого числа "
    "от 1 до 1000 включительно и возвращает int. 1, 1.0 и 1e0 равнозначны. "
    "Bool, строки, массивы, null, дроби, non-finite и числа вне диапазона дают "
    "ValueError. Проверять точное исходное число до потери точности; raw имеет тип str."
)
SQL_CONTRACT = (
    "C1: totals(connection) возвращает пары (buyer_id, amount) — сумму price*qty "
    "всех позиций всех заказов каждого покупателя. Порядок результата не задан. "
    "Схема и данные для SQLite находятся в fixture.sql. Каждый line.id уникален; "
    "одинаковая стоимость разных позиций допустима. В каждом заказе есть позиции. "
    "Форма SQL не предписана."
)
SQL_FIXTURE = """CREATE TABLE orders (id INTEGER PRIMARY KEY, buyer_id INTEGER NOT NULL);
CREATE TABLE lines (id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL,
                    price INTEGER NOT NULL, qty INTEGER NOT NULL);
INSERT INTO orders VALUES (10,1), (11,1), (12,2);
INSERT INTO lines VALUES (1,10,200,1), (2,10,200,1), (3,11,150,2), (4,12,100,1);
"""

AUDIT_CASES = [
    {"id": "RV13", "topic": "25/2", "assignment": DEPLOY_CONTRACT,
     "code": '''def deploy(service, config):
    service.config = config
    service.restart()
    return {"changed": 0}
''', "classes": ["code_defect"], "verdict": "needs_changes", "criterion": "error",
     "reason": "Повтор меняет generation; changed=0 маскирует эффект и не доказывает идемпотентность.",
     "source_findings": ["F40"], "probe": "deploy_bad"},
    {"id": "RV14", "topic": "25/2", "assignment": DEPLOY_CONTRACT,
     "code": '''def deploy(service, config):
    changed = service.config != config
    if changed:
        service.config = config
        service.restart()
    return {"changed": int(changed)}
''', "classes": ["valid"], "verdict": "accepted", "criterion": "confirmed",
     "reason": "Сравнение состояния допустимо: повтор не перезапускает модель, новое значение применяется.",
     "source_findings": ["F40"], "probe": "deploy_good"},
    {"id": "RV15", "topic": "08/2",
     "assignment": "C1: подтвердить два конкурентных заказа последней единицы в PostgreSQL: один успех, один отказ, остаток 0. Две сессии и пересечение операций должны быть наблюдаемы. Проверить reserve и тест. attempt в тесте открывает отдельное соединение, вызывает reserve и возвращает bool. Установленное по коду и подтверждённое запуском указать отдельно.",
     "code": '''def reserve(connection, sku):
    cursor = connection.execute(
        "UPDATE stock SET qty=qty-1 WHERE sku=%s AND qty>=1", (sku,))
    return cursor.rowcount == 1
''', "extra": {"test_submission.py": '''from concurrent.futures import ThreadPoolExecutor

def run_concurrent_test(attempt):
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(attempt).result(timeout=2)
        second = pool.submit(attempt).result(timeout=2)
    assert sorted([first, second]) == [False, True]
    return [first, second]
''', "evidence.txt": "Синтетический отчёт автора сдачи: тест зелёный, ответы True/False, stock=0; C1 отмечен выполненным. PID сессий и trace пересечения не приложены. PostgreSQL-стенда в пакете нет.\n"},
     "classes": ["test_defect"], "verdict": "needs_changes", "criterion": "unverified",
     "reason": "result() первого задания вызывается до submit второго: тест последовательный. Это не доказанная гонка в reserve; C1 остаётся непроверенным.",
     "source_findings": ["F11", "F12"], "probe": "serial_test"},
    {"id": "RV16", "topic": "03/1",
     "assignment": "C1: подтвердить проверку доверенного TLS и HTTP 200 клиентом ученика на предоставленном стенде. request выполняет подготовленный преподавателем запрос с заданным CA. Сначала запускается предоставленный преподавателем harness.py. Материалы и traceback приложены; живого endpoint в пакете нет.",
     "code": '''def check(request):
    response = request()
    if response.status != 200:
        raise ValueError("unexpected HTTP status")
    return response.status
''', "extra": {"harness.py": '''import json

def run(ready_path, client_check):
    ready = json.loads(ready_path.read_text())
    instance = ready["id"]
    return client_check(instance)
''', "ready.json": '{"stale": true}\n',
         "evidence.txt": "Синтетический журнал подготовки: harness.py, строка 5, KeyError: 'id'. client_check ещё не вызван, TCP/TLS запрос не начат. Файл ready.json остался после предыдущей сессии.\n"},
     "classes": ["environment"], "verdict": "unverified", "criterion": "unverified",
     "reason": "Падает предоставленный harness до вызова клиента. Исправить готовность стенда и повторить проверку; ошибка TLS/клиента не установлена.",
     "source_findings": ["F05"], "probe": "stale_setup"},
    {"id": "RV17", "topic": "06/1", "assignment": JSON_CONTRACT,
     "code": '''import json
import math

def quantity(raw):
    value = json.loads(raw)
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("invalid quantity")
    if not 1 <= value <= 1000 or int(value) != value:
        raise ValueError("invalid quantity")
    return int(value)
''', "classes": ["code_defect"], "verdict": "needs_changes", "criterion": "error",
     "reason": "json.loads округляет дробь 1.0000000000000001 до float 1.0 до проверки; исходная дробь ошибочно принята.",
     "source_findings": ["F08"], "probe": "json_bad"},
    {"id": "RV18", "topic": "06/1", "assignment": JSON_CONTRACT,
     "code": '''import json
from decimal import Decimal, InvalidOperation

def quantity(raw):
    try:
        value = json.loads(raw, parse_float=Decimal, parse_int=Decimal,
                           parse_constant=Decimal)
    except InvalidOperation as exc:
        raise ValueError("invalid quantity") from exc
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError("invalid quantity")
    if not 1 <= value <= 1000 or value != value.to_integral_value():
        raise ValueError("invalid quantity")
    return int(value)
''', "classes": ["valid"], "verdict": "accepted", "criterion": "confirmed",
     "reason": "Decimal сохраняет исходное число, диапазон проверяется до int. Запрет точки или экспоненты нарушил бы контракт.",
     "source_findings": ["F06", "F08"], "probe": "json_good"},
    {"id": "RV19", "topic": "04/3", "assignment": SQL_CONTRACT,
     "code": '''def totals(connection):
    return connection.execute("""
        SELECT o.buyer_id, SUM(DISTINCT l.price*l.qty)
        FROM orders o JOIN lines l ON l.order_id=o.id
        GROUP BY o.buyer_id
    """).fetchall()
''', "extra": {"fixture.sql": SQL_FIXTURE},
     "classes": ["code_defect"], "verdict": "needs_changes", "criterion": "error",
     "reason": "Две разные позиции по 200 схлопнуты DISTINCT; покупатель 1 получает 500 вместо 700.",
     "source_findings": ["F07"], "probe": "sql_bad"},
    {"id": "RV20", "topic": "04/3", "assignment": SQL_CONTRACT,
     "code": '''def totals(connection):
    return connection.execute("""
        WITH per_order AS (
            SELECT order_id, SUM(price*qty) AS amount
            FROM lines GROUP BY order_id
        )
        SELECT o.buyer_id, SUM(p.amount)
        FROM orders o JOIN per_order p ON p.order_id=o.id
        GROUP BY o.buyer_id
    """).fetchall()
''', "extra": {"fixture.sql": SQL_FIXTURE},
     "classes": ["valid"], "verdict": "accepted", "criterion": "confirmed",
     "reason": "Предварительная агрегация по заказу сохраняет все позиции. Не требуется переписывать CTE под стиль проверяющего.",
     "source_findings": ["F07"], "probe": "sql_good"},
]


def verify_audit_case(case, namespace):
    """Execute deterministic local counterexamples; never imply live PG/TLS/Ansible."""
    probe = case["probe"]
    if probe in ("deploy_bad", "deploy_good"):
        class Service:
            config = "old"
            generation = 10

            def restart(self):
                self.generation += 1

        service = Service()
        first = namespace["deploy"](service, "new")
        generation = service.generation
        again = namespace["deploy"](service, "new")
        if probe == "deploy_bad":
            return again == {"changed": 0} and service.generation > generation
        return (first == {"changed": 1} and again == {"changed": 0}
                and generation == 11 and service.generation == generation
                and service.config == "new")
    if probe == "serial_test":
        extra = {}
        exec(case["extra"]["test_submission.py"], extra)
        trace = []

        class ObservedFuture:
            def __init__(self, future):
                self.future = future

            def result(self, timeout=None):
                trace.append("result")
                return self.future.result(timeout=timeout)

        class ObservedPool(ThreadPoolExecutor):
            def submit(self, *args, **kwargs):
                trace.append("submit")
                return ObservedFuture(super().submit(*args, **kwargs))

        extra["ThreadPoolExecutor"] = ObservedPool
        outcomes = iter((True, False))

        def attempt():
            return next(outcomes)

        result = extra["run_concurrent_test"](attempt)
        return sorted(result) == [False, True] and trace == ["submit", "result", "submit", "result"]
    if probe == "stale_setup":
        extra = {}
        exec(case["extra"]["harness.py"], extra)
        called = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ready.json"
            path.write_text(case["extra"]["ready.json"])
            try:
                extra["run"](path, called.append)
            except KeyError as exc:
                return exc.args == ("id",) and not called
        return False
    if probe in ("json_bad", "json_good"):
        quantity = namespace["quantity"]
        if probe == "json_bad":
            return quantity("1.0000000000000001") == 1
        for raw, expected in (("1", 1), ("1.0", 1), ("1e0", 1), ("1000", 1000)):
            if type(quantity(raw)) is not int or quantity(raw) != expected:
                return False
        for raw in ("true", "false", '"1"', "null", "[]", "{}", "0", "-1", "1001",
                    "1.5", "1.0000000000000001", "1e-10000", "1e10000",
                    "1e99999999999999999999", "NaN", "Infinity", "-Infinity"):
            try:
                quantity(raw)
            except ValueError:
                continue
            return False
        return True
    if probe in ("sql_bad", "sql_good"):
        connection = sqlite3.connect(":memory:")
        try:
            connection.executescript(case["extra"]["fixture.sql"])
            result = sorted(namespace["totals"](connection))
            return result == ([(1, 500), (2, 100)] if probe == "sql_bad" else [(1, 700), (2, 100)])
        finally:
            connection.close()
    return False
