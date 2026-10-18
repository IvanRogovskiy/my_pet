# Метод первого ревью

Canonical agent ID: `/root/reliability_rv20`.
Дата: 2026-10-14. Модель в metadata: Codex agent; exact model version not exposed.

Свежий контекст: агент получил отдельное поручение без родительской истории и прошлых ответов; доступны служебные инструкции среды и текущая выдача. Ученик и материалы синтетические, этот ответ и перечисленные локальные запуски — настоящая первая проверка агента. Других агентов не создавал.

Рабочий каталог всех команд: `/private/tmp/course-reliability-s2a212up/rv20`.
Данные читал только из TEACHER.md, run-metadata.json и input/. Репозиторий, другие выдачи, ключи, оценщики и прежние ответы не читал. Отсутствующие ссылки не открывал. Score и авторские тесты оценивания не искал и не вызывал. Функции из input/RV08/test_submission.py и input/RV15/test_submission.py — именно приложенные к сдачам учебные тесты: проверять их прямо требует соответствующее задание. Предоставленный преподавательский harness RV16 запускался согласно assignment.md.

Проверял объявленные C1, без требований к стилю, слоям, сортировке, верхнему пределу v2 и настоящему systemd, отсутствующих в соответствующих контрактах. Для RV08 confirmed относится к реализации C1, needs_changes — к приложенному тесту. Для RV15 дефект теста доказан, но результат reserve в настоящей PostgreSQL остаётся unverified. Для RV11 двойная бронь оставлена гипотезой. Принятие работы не означает подтверждения понимания синтетического ученика или всей темы.

## Чтение материалов

Точная команда 1:

```sh
pwd
cat TEACHER.md
cat run-metadata.json
rg --files input
```

Результат: cwd совпал с назначенной выдачей; прочитаны TEACHER.md и run-metadata.json, получен список input/. Exit code 0.

Точная команда 2:

```sh
cat input/REVIEW.md
cat input/manifest.json
python3 - <<'PY'
from pathlib import Path
for p in sorted(Path('input').glob('RV*/*')):
 print('\nFILE '+str(p))
 for i,line in enumerate(p.read_text().splitlines(),1): print(f'{i}: {line}')
PY
```

Результат: прочитаны REVIEW.md, manifest.json и все файлы RV01–RV20; исходные строки пронумерованы для замечаний. Exit code 0. Все 20 заданий содержат C1; RV10 явно имеет исходную версию v1 и отдельное непринятое предложение v2.

## Собственные выполнения

Ниже точная команда и полный фактический вывод. Это диагностический скрипт преподавателя, написанный после чтения контрактов, без доступа к оценщику. Поля expected — заранее выбранные ожидания по C1, actual — наблюдения вызовов. Несоответствия не останавливают журнал: они становятся замечаниями. Exit code: 0.

```sh
python3 - <<'PY'
import contextlib
import copy
import io
import json
import platform
import sqlite3
import sys
import threading
import time
import types
from pathlib import Path

root = Path("input")
print(json.dumps({"environment": {"python": sys.version.split()[0], "platform": platform.platform(), "sqlite": sqlite3.sqlite_version, "cwd": str(Path.cwd()), "network": "not used", "docker": "not used", "postgresql": "not used"}}, ensure_ascii=False))
mods = {}
def module(case, file="submission.py"):
    name = case + "_" + file.replace(".", "_")
    m = types.ModuleType(name)
    exec(compile((root/case/file).read_text(), str(root/case/file), "exec"), m.__dict__)
    return m

for n in range(1, 21):
    case = f"RV{n:02d}"
    mods[case] = module(case)

def call(fn, *args):
    try:
        value = fn(*args)
        return {"return": value, "type": type(value).__name__}
    except Exception as e:
        return {"exception": type(e).__name__, "message": str(e)}
def emit(case, scenario, actual, expected):
    print(json.dumps({"case": case, "scenario": scenario, "actual": actual, "expected": expected}, ensure_ascii=False))

for case in ["RV01", "RV05", "RV06"]:
    for value in [0, 1, 100000000000000000000, True, False, "1", 1.0, 1.5, -1]:
        expected = {"return": value, "type": "int"} if type(value) is int and value >= 0 else "ValueError"
        emit(case, {"input": value, "input_type": type(value).__name__}, call(mods[case].validate, value), expected)

auth_cases = [
    ("admin_any", {"role":"admin","id":1}, {"owner_id":2}, {"user_id":99}, True),
    ("buyer_own_forged_request", {"role":"buyer","id":1}, {"owner_id":1}, {"user_id":99}, True),
    ("buyer_foreign_request_self", {"role":"buyer","id":1}, {"owner_id":2}, {"user_id":1}, False),
    ("buyer_foreign_request_other", {"role":"buyer","id":1}, {"owner_id":2}, {"user_id":99}, False),
]
for case in ["RV02", "RV07"]:
    for label, actor, order, request, expected in auth_cases:
        emit(case, label, call(mods[case].can_read, actor, order, request), {"return":expected,"type":"bool"})

fn=mods["RV03"].submit
s={}
first=copy.deepcopy(fn(s,"buyer1","K",{"qty":1}))
repeat=copy.deepcopy(fn(s,"buyer1","K",{"qty":1}))
emit("RV03","same buyer/key/body",{"first":first,"repeat":repeat,"entries":len(s)}, "same result; one entry")
s={}
fn(s,"buyer1","K",{"qty":1})
before=copy.deepcopy(s)
r=call(fn,s,"buyer1","K",{"qty":2})
emit("RV03","same buyer/key, different body",{"result":r,"before":before,"after":s}, "ValueError; original entry preserved")
s={}
one=copy.deepcopy(fn(s,"buyer1","K",{"qty":1}))
two=copy.deepcopy(fn(s,"buyer2","K",{"qty":2}))
emit("RV03","different buyer, same key",{"first":one,"second":two,"entries":len(s)}, "independent second result with qty=2; two entries")
s={}
one=copy.deepcopy(fn(s,"buyer1","K",{"qty":1}))
two=copy.deepcopy(fn(s,"buyer1","J",{"qty":2}))
emit("RV03","same buyer, different key",{"first":one,"second":two,"entries":len(s)}, "independent results; two entries")

for initial, qty in [(5,2),(2,2),(2,3),(0,1)]:
    stock=[initial]
    result=call(mods["RV04"].reserve,stock,qty)
    emit("RV04",{"stock":initial,"qty":qty},{"result":result,"stock_after":stock}, {"result":initial-qty,"stock_after":[initial-qty]} if initial>=qty else {"exception":"ValueError","stock_after":[initial]})

actual=mods["RV08"].rows()
emit("RV08","implementation unordered rows",sorted(actual),[(1,100),(2,200)])
prior=sys.modules.get("submission")
sys.modules["submission"]=mods["RV08"]
try:
    test=module("RV08","test_submission.py")
    emit("RV08","provided learner test",call(test.test_rows), "must accept both permitted orders")
finally:
    if prior is None: del sys.modules["submission"]
    else: sys.modules["submission"]=prior

emit("RV09","HTTP Linux runtime", "not executed: no provided reachable endpoint; lab.invalid not accessed", "trusted evidence of live HTTP 200 required")

for value in [1,100,101,100000000000000000000,0,-1,True,False,1.0,"1",None,[]]:
    expected={"return":value,"type":"int"} if type(value) is int and value>0 else "ValueError"
    emit("RV10",{"input":value,"input_type":type(value).__name__},call(mods["RV10"].quantity,value),expected)

emit("RV11","PostgreSQL concurrent runtime","not executed: PostgreSQL unavailable and forbidden for this review", "real two-session overlapping PostgreSQL test required")

for items in [[],[{"price":0,"qty":5}],[{"price":4,"qty":0}],[{"price":100,"qty":2},{"price":30,"qty":3}],[{"price":10**30,"qty":10**20}]]:
    expected=sum(x["price"]*x["qty"] for x in items)
    emit("RV12",{"items":items},call(mods["RV12"].total,items),{"return":expected,"type":"int"})

class Service:
    def __init__(self):
        self.config="old"
        self.generation=7
    def restart(self):
        self.generation+=1

for case in ["RV13","RV14"]:
    svc=Service()
    for config, expected_gen, expected_changed in [("new",8,1),("new",8,0),("other",9,1),("other",9,0)]:
        before={"config":svc.config,"generation":svc.generation}
        result=call(mods[case].deploy,svc,config)
        emit(case,{"config":config,"before":before},{"result":result,"config":svc.config,"generation":svc.generation},{"return":{"changed":expected_changed},"config":config,"generation":expected_gen})

trace=[]
attempt_lock=threading.Lock()
active=0
max_active=0
sequence=0
def attempt():
    global active, max_active, sequence
    with attempt_lock:
        sequence+=1
        attempt_id=sequence
        active+=1
        max_active=max(max_active,active)
        trace.append({"event":"start","attempt":attempt_id,"thread":threading.get_ident()})
    time.sleep(0.02)
    with attempt_lock:
        trace.append({"event":"end","attempt":attempt_id,"thread":threading.get_ident()})
        active-=1
    return attempt_id==1

test15=module("RV15","test_submission.py")
res=call(test15.run_concurrent_test,attempt)
emit("RV15","provided test with local instrumented attempts",{"result":res,"trace":trace,"max_active":max_active},"overlap required; this probe is not PostgreSQL evidence")

callback_calls=[]
def client_check(instance):
    callback_calls.append(instance)
    return 200
harness=module("RV16","harness.py")
res=call(harness.run,root/"RV16"/"ready.json",client_check)
emit("RV16","provided harness before network request",{"result":res,"callback_calls":callback_calls},"valid readiness id and client invocation needed")
for status in [200,503]:
    emit("RV16",{"local_stub_status":status},call(mods["RV16"].check,lambda:types.SimpleNamespace(status=status)),200 if status==200 else "ValueError; TLS not exercised")

raws=["1","1.0","1e0","1000","1000.0","1e3","0","1001","true","false",'"1"',"[]","null","1.5","NaN","Infinity","-Infinity","1e999","1.0000000000000001","0.99999999999999999","1000.00000000000001","999.99999999999999","1"+"0"*400,"not json"]
valid={"1":1,"1.0":1,"1e0":1,"1000":1000,"1000.0":1000,"1e3":1000}
for case in ["RV17","RV18"]:
    for raw in raws:
        emit(case,{"raw":raw},call(mods[case].quantity,raw),{"return":valid[raw],"type":"int"} if raw in valid else "ValueError (including subclasses)")

for case in ["RV19","RV20"]:
    with sqlite3.connect(":memory:") as conn:
        conn.executescript((root/case/"fixture.sql").read_text())
        emit(case,"provided SQLite fixture",sorted(mods[case].totals(conn)),[(1,700),(2,100)])
        conn.execute("INSERT INTO orders VALUES (13, 1)")
        conn.execute("INSERT INTO lines VALUES (5, 13, 100, 2)")
        emit(case,"same monetary value in another order",sorted(mods[case].totals(conn)),[(1,900),(2,100)])
        conn.execute("DELETE FROM lines")
        conn.execute("DELETE FROM orders")
        emit(case,"empty database",mods[case].totals(conn),[])
print(json.dumps({"completed":"all 20 submissions inspected; local executions above; no live HTTP/TLS/PostgreSQL test"},ensure_ascii=False))

PY
```

Фактический stdout:

```jsonl
{"environment": {"python": "3.12.3", "platform": "macOS-26.6.2-x86_64-i386-64bit", "sqlite": "3.46.0", "cwd": "/private/tmp/course-reliability-s2a212up/rv20", "network": "not used", "docker": "not used", "postgresql": "not used"}}
{"case": "RV01", "scenario": {"input": 0, "input_type": "int"}, "actual": {"return": 0, "type": "int"}, "expected": {"return": 0, "type": "int"}}
{"case": "RV01", "scenario": {"input": 1, "input_type": "int"}, "actual": {"return": 1, "type": "int"}, "expected": {"return": 1, "type": "int"}}
{"case": "RV01", "scenario": {"input": 100000000000000000000, "input_type": "int"}, "actual": {"return": 100000000000000000000, "type": "int"}, "expected": {"return": 100000000000000000000, "type": "int"}}
{"case": "RV01", "scenario": {"input": true, "input_type": "bool"}, "actual": {"return": true, "type": "bool"}, "expected": "ValueError"}
{"case": "RV01", "scenario": {"input": false, "input_type": "bool"}, "actual": {"return": false, "type": "bool"}, "expected": "ValueError"}
{"case": "RV01", "scenario": {"input": "1", "input_type": "str"}, "actual": {"exception": "ValueError", "message": "invalid money"}, "expected": "ValueError"}
{"case": "RV01", "scenario": {"input": 1.0, "input_type": "float"}, "actual": {"exception": "ValueError", "message": "invalid money"}, "expected": "ValueError"}
{"case": "RV01", "scenario": {"input": 1.5, "input_type": "float"}, "actual": {"exception": "ValueError", "message": "invalid money"}, "expected": "ValueError"}
{"case": "RV01", "scenario": {"input": -1, "input_type": "int"}, "actual": {"exception": "ValueError", "message": "invalid money"}, "expected": "ValueError"}
{"case": "RV05", "scenario": {"input": 0, "input_type": "int"}, "actual": {"return": 0, "type": "int"}, "expected": {"return": 0, "type": "int"}}
{"case": "RV05", "scenario": {"input": 1, "input_type": "int"}, "actual": {"return": 1, "type": "int"}, "expected": {"return": 1, "type": "int"}}
{"case": "RV05", "scenario": {"input": 100000000000000000000, "input_type": "int"}, "actual": {"return": 100000000000000000000, "type": "int"}, "expected": {"return": 100000000000000000000, "type": "int"}}
{"case": "RV05", "scenario": {"input": true, "input_type": "bool"}, "actual": {"exception": "ValueError", "message": "invalid money"}, "expected": "ValueError"}
{"case": "RV05", "scenario": {"input": false, "input_type": "bool"}, "actual": {"exception": "ValueError", "message": "invalid money"}, "expected": "ValueError"}
{"case": "RV05", "scenario": {"input": "1", "input_type": "str"}, "actual": {"exception": "ValueError", "message": "invalid money"}, "expected": "ValueError"}
{"case": "RV05", "scenario": {"input": 1.0, "input_type": "float"}, "actual": {"exception": "ValueError", "message": "invalid money"}, "expected": "ValueError"}
{"case": "RV05", "scenario": {"input": 1.5, "input_type": "float"}, "actual": {"exception": "ValueError", "message": "invalid money"}, "expected": "ValueError"}
{"case": "RV05", "scenario": {"input": -1, "input_type": "int"}, "actual": {"exception": "ValueError", "message": "invalid money"}, "expected": "ValueError"}
{"case": "RV06", "scenario": {"input": 0, "input_type": "int"}, "actual": {"return": 0, "type": "int"}, "expected": {"return": 0, "type": "int"}}
{"case": "RV06", "scenario": {"input": 1, "input_type": "int"}, "actual": {"return": 1, "type": "int"}, "expected": {"return": 1, "type": "int"}}
{"case": "RV06", "scenario": {"input": 100000000000000000000, "input_type": "int"}, "actual": {"return": 100000000000000000000, "type": "int"}, "expected": {"return": 100000000000000000000, "type": "int"}}
{"case": "RV06", "scenario": {"input": true, "input_type": "bool"}, "actual": {"exception": "ValueError", "message": "boolean"}, "expected": "ValueError"}
{"case": "RV06", "scenario": {"input": false, "input_type": "bool"}, "actual": {"exception": "ValueError", "message": "boolean"}, "expected": "ValueError"}
{"case": "RV06", "scenario": {"input": "1", "input_type": "str"}, "actual": {"exception": "ValueError", "message": "invalid money"}, "expected": "ValueError"}
{"case": "RV06", "scenario": {"input": 1.0, "input_type": "float"}, "actual": {"exception": "ValueError", "message": "invalid money"}, "expected": "ValueError"}
{"case": "RV06", "scenario": {"input": 1.5, "input_type": "float"}, "actual": {"exception": "ValueError", "message": "invalid money"}, "expected": "ValueError"}
{"case": "RV06", "scenario": {"input": -1, "input_type": "int"}, "actual": {"exception": "ValueError", "message": "invalid money"}, "expected": "ValueError"}
{"case": "RV02", "scenario": "admin_any", "actual": {"return": true, "type": "bool"}, "expected": {"return": true, "type": "bool"}}
{"case": "RV02", "scenario": "buyer_own_forged_request", "actual": {"return": false, "type": "bool"}, "expected": {"return": true, "type": "bool"}}
{"case": "RV02", "scenario": "buyer_foreign_request_self", "actual": {"return": true, "type": "bool"}, "expected": {"return": false, "type": "bool"}}
{"case": "RV02", "scenario": "buyer_foreign_request_other", "actual": {"return": false, "type": "bool"}, "expected": {"return": false, "type": "bool"}}
{"case": "RV07", "scenario": "admin_any", "actual": {"return": true, "type": "bool"}, "expected": {"return": true, "type": "bool"}}
{"case": "RV07", "scenario": "buyer_own_forged_request", "actual": {"return": true, "type": "bool"}, "expected": {"return": true, "type": "bool"}}
{"case": "RV07", "scenario": "buyer_foreign_request_self", "actual": {"return": false, "type": "bool"}, "expected": {"return": false, "type": "bool"}}
{"case": "RV07", "scenario": "buyer_foreign_request_other", "actual": {"return": false, "type": "bool"}, "expected": {"return": false, "type": "bool"}}
{"case": "RV03", "scenario": "same buyer/key/body", "actual": {"first": {"id": 1, "payload": {"qty": 1}}, "repeat": {"id": 1, "payload": {"qty": 1}}, "entries": 1}, "expected": "same result; one entry"}
{"case": "RV03", "scenario": "same buyer/key, different body", "actual": {"result": {"return": {"id": 1, "payload": {"qty": 1}}, "type": "dict"}, "before": {"K": {"id": 1, "payload": {"qty": 1}}}, "after": {"K": {"id": 1, "payload": {"qty": 1}}}}, "expected": "ValueError; original entry preserved"}
{"case": "RV03", "scenario": "different buyer, same key", "actual": {"first": {"id": 1, "payload": {"qty": 1}}, "second": {"id": 1, "payload": {"qty": 1}}, "entries": 1}, "expected": "independent second result with qty=2; two entries"}
{"case": "RV03", "scenario": "same buyer, different key", "actual": {"first": {"id": 1, "payload": {"qty": 1}}, "second": {"id": 2, "payload": {"qty": 2}}, "entries": 2}, "expected": "independent results; two entries"}
{"case": "RV04", "scenario": {"stock": 5, "qty": 2}, "actual": {"result": {"return": 3, "type": "int"}, "stock_after": [3]}, "expected": {"result": 3, "stock_after": [3]}}
{"case": "RV04", "scenario": {"stock": 2, "qty": 2}, "actual": {"result": {"return": 0, "type": "int"}, "stock_after": [0]}, "expected": {"result": 0, "stock_after": [0]}}
{"case": "RV04", "scenario": {"stock": 2, "qty": 3}, "actual": {"result": {"exception": "ValueError", "message": "insufficient stock"}, "stock_after": [-1]}, "expected": {"exception": "ValueError", "stock_after": [2]}}
{"case": "RV04", "scenario": {"stock": 0, "qty": 1}, "actual": {"result": {"exception": "ValueError", "message": "insufficient stock"}, "stock_after": [-1]}, "expected": {"exception": "ValueError", "stock_after": [0]}}
{"case": "RV08", "scenario": "implementation unordered rows", "actual": [[1, 100], [2, 200]], "expected": [[1, 100], [2, 200]]}
{"case": "RV08", "scenario": "provided learner test", "actual": {"exception": "AssertionError", "message": ""}, "expected": "must accept both permitted orders"}
{"case": "RV09", "scenario": "HTTP Linux runtime", "actual": "not executed: no provided reachable endpoint; lab.invalid not accessed", "expected": "trusted evidence of live HTTP 200 required"}
{"case": "RV10", "scenario": {"input": 1, "input_type": "int"}, "actual": {"return": 1, "type": "int"}, "expected": {"return": 1, "type": "int"}}
{"case": "RV10", "scenario": {"input": 100, "input_type": "int"}, "actual": {"return": 100, "type": "int"}, "expected": {"return": 100, "type": "int"}}
{"case": "RV10", "scenario": {"input": 101, "input_type": "int"}, "actual": {"return": 101, "type": "int"}, "expected": {"return": 101, "type": "int"}}
{"case": "RV10", "scenario": {"input": 100000000000000000000, "input_type": "int"}, "actual": {"return": 100000000000000000000, "type": "int"}, "expected": {"return": 100000000000000000000, "type": "int"}}
{"case": "RV10", "scenario": {"input": 0, "input_type": "int"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError"}
{"case": "RV10", "scenario": {"input": -1, "input_type": "int"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError"}
{"case": "RV10", "scenario": {"input": true, "input_type": "bool"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError"}
{"case": "RV10", "scenario": {"input": false, "input_type": "bool"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError"}
{"case": "RV10", "scenario": {"input": 1.0, "input_type": "float"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError"}
{"case": "RV10", "scenario": {"input": "1", "input_type": "str"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError"}
{"case": "RV10", "scenario": {"input": null, "input_type": "NoneType"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError"}
{"case": "RV10", "scenario": {"input": [], "input_type": "list"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError"}
{"case": "RV11", "scenario": "PostgreSQL concurrent runtime", "actual": "not executed: PostgreSQL unavailable and forbidden for this review", "expected": "real two-session overlapping PostgreSQL test required"}
{"case": "RV12", "scenario": {"items": []}, "actual": {"return": 0, "type": "int"}, "expected": {"return": 0, "type": "int"}}
{"case": "RV12", "scenario": {"items": [{"price": 0, "qty": 5}]}, "actual": {"return": 0, "type": "int"}, "expected": {"return": 0, "type": "int"}}
{"case": "RV12", "scenario": {"items": [{"price": 4, "qty": 0}]}, "actual": {"return": 0, "type": "int"}, "expected": {"return": 0, "type": "int"}}
{"case": "RV12", "scenario": {"items": [{"price": 100, "qty": 2}, {"price": 30, "qty": 3}]}, "actual": {"return": 290, "type": "int"}, "expected": {"return": 290, "type": "int"}}
{"case": "RV12", "scenario": {"items": [{"price": 1000000000000000000000000000000, "qty": 100000000000000000000}]}, "actual": {"return": 100000000000000000000000000000000000000000000000000, "type": "int"}, "expected": {"return": 100000000000000000000000000000000000000000000000000, "type": "int"}}
{"case": "RV13", "scenario": {"config": "new", "before": {"config": "old", "generation": 7}}, "actual": {"result": {"return": {"changed": 0}, "type": "dict"}, "config": "new", "generation": 8}, "expected": {"return": {"changed": 1}, "config": "new", "generation": 8}}
{"case": "RV13", "scenario": {"config": "new", "before": {"config": "new", "generation": 8}}, "actual": {"result": {"return": {"changed": 0}, "type": "dict"}, "config": "new", "generation": 9}, "expected": {"return": {"changed": 0}, "config": "new", "generation": 8}}
{"case": "RV13", "scenario": {"config": "other", "before": {"config": "new", "generation": 9}}, "actual": {"result": {"return": {"changed": 0}, "type": "dict"}, "config": "other", "generation": 10}, "expected": {"return": {"changed": 1}, "config": "other", "generation": 9}}
{"case": "RV13", "scenario": {"config": "other", "before": {"config": "other", "generation": 10}}, "actual": {"result": {"return": {"changed": 0}, "type": "dict"}, "config": "other", "generation": 11}, "expected": {"return": {"changed": 0}, "config": "other", "generation": 9}}
{"case": "RV14", "scenario": {"config": "new", "before": {"config": "old", "generation": 7}}, "actual": {"result": {"return": {"changed": 1}, "type": "dict"}, "config": "new", "generation": 8}, "expected": {"return": {"changed": 1}, "config": "new", "generation": 8}}
{"case": "RV14", "scenario": {"config": "new", "before": {"config": "new", "generation": 8}}, "actual": {"result": {"return": {"changed": 0}, "type": "dict"}, "config": "new", "generation": 8}, "expected": {"return": {"changed": 0}, "config": "new", "generation": 8}}
{"case": "RV14", "scenario": {"config": "other", "before": {"config": "new", "generation": 8}}, "actual": {"result": {"return": {"changed": 1}, "type": "dict"}, "config": "other", "generation": 9}, "expected": {"return": {"changed": 1}, "config": "other", "generation": 9}}
{"case": "RV14", "scenario": {"config": "other", "before": {"config": "other", "generation": 9}}, "actual": {"result": {"return": {"changed": 0}, "type": "dict"}, "config": "other", "generation": 9}, "expected": {"return": {"changed": 0}, "config": "other", "generation": 9}}
{"case": "RV15", "scenario": "provided test with local instrumented attempts", "actual": {"result": {"return": [true, false], "type": "list"}, "trace": [{"event": "start", "attempt": 1, "thread": 12999319552}, {"event": "end", "attempt": 1, "thread": 12999319552}, {"event": "start", "attempt": 2, "thread": 12999319552}, {"event": "end", "attempt": 2, "thread": 12999319552}], "max_active": 1}, "expected": "overlap required; this probe is not PostgreSQL evidence"}
{"case": "RV16", "scenario": "provided harness before network request", "actual": {"result": {"exception": "KeyError", "message": "'id'"}, "callback_calls": []}, "expected": "valid readiness id and client invocation needed"}
{"case": "RV16", "scenario": {"local_stub_status": 200}, "actual": {"return": 200, "type": "int"}, "expected": 200}
{"case": "RV16", "scenario": {"local_stub_status": 503}, "actual": {"exception": "ValueError", "message": "unexpected HTTP status"}, "expected": "ValueError; TLS not exercised"}
{"case": "RV17", "scenario": {"raw": "1"}, "actual": {"return": 1, "type": "int"}, "expected": {"return": 1, "type": "int"}}
{"case": "RV17", "scenario": {"raw": "1.0"}, "actual": {"return": 1, "type": "int"}, "expected": {"return": 1, "type": "int"}}
{"case": "RV17", "scenario": {"raw": "1e0"}, "actual": {"return": 1, "type": "int"}, "expected": {"return": 1, "type": "int"}}
{"case": "RV17", "scenario": {"raw": "1000"}, "actual": {"return": 1000, "type": "int"}, "expected": {"return": 1000, "type": "int"}}
{"case": "RV17", "scenario": {"raw": "1000.0"}, "actual": {"return": 1000, "type": "int"}, "expected": {"return": 1000, "type": "int"}}
{"case": "RV17", "scenario": {"raw": "1e3"}, "actual": {"return": 1000, "type": "int"}, "expected": {"return": 1000, "type": "int"}}
{"case": "RV17", "scenario": {"raw": "0"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "1001"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "true"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "false"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "\"1\""}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "[]"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "null"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "1.5"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "NaN"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "Infinity"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "-Infinity"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "1e999"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "1.0000000000000001"}, "actual": {"return": 1, "type": "int"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "0.99999999999999999"}, "actual": {"return": 1, "type": "int"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "1000.00000000000001"}, "actual": {"return": 1000, "type": "int"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "999.99999999999999"}, "actual": {"return": 1000, "type": "int"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"}, "actual": {"exception": "OverflowError", "message": "int too large to convert to float"}, "expected": "ValueError (including subclasses)"}
{"case": "RV17", "scenario": {"raw": "not json"}, "actual": {"exception": "JSONDecodeError", "message": "Expecting value: line 1 column 1 (char 0)"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "1"}, "actual": {"return": 1, "type": "int"}, "expected": {"return": 1, "type": "int"}}
{"case": "RV18", "scenario": {"raw": "1.0"}, "actual": {"return": 1, "type": "int"}, "expected": {"return": 1, "type": "int"}}
{"case": "RV18", "scenario": {"raw": "1e0"}, "actual": {"return": 1, "type": "int"}, "expected": {"return": 1, "type": "int"}}
{"case": "RV18", "scenario": {"raw": "1000"}, "actual": {"return": 1000, "type": "int"}, "expected": {"return": 1000, "type": "int"}}
{"case": "RV18", "scenario": {"raw": "1000.0"}, "actual": {"return": 1000, "type": "int"}, "expected": {"return": 1000, "type": "int"}}
{"case": "RV18", "scenario": {"raw": "1e3"}, "actual": {"return": 1000, "type": "int"}, "expected": {"return": 1000, "type": "int"}}
{"case": "RV18", "scenario": {"raw": "0"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "1001"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "true"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "false"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "\"1\""}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "[]"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "null"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "1.5"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "NaN"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "Infinity"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "-Infinity"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "1e999"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "1.0000000000000001"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "0.99999999999999999"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "1000.00000000000001"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "999.99999999999999"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"}, "actual": {"exception": "ValueError", "message": "invalid quantity"}, "expected": "ValueError (including subclasses)"}
{"case": "RV18", "scenario": {"raw": "not json"}, "actual": {"exception": "JSONDecodeError", "message": "Expecting value: line 1 column 1 (char 0)"}, "expected": "ValueError (including subclasses)"}
{"case": "RV19", "scenario": "provided SQLite fixture", "actual": [[1, 500], [2, 100]], "expected": [[1, 700], [2, 100]]}
{"case": "RV19", "scenario": "same monetary value in another order", "actual": [[1, 500], [2, 100]], "expected": [[1, 900], [2, 100]]}
{"case": "RV19", "scenario": "empty database", "actual": [], "expected": []}
{"case": "RV20", "scenario": "provided SQLite fixture", "actual": [[1, 700], [2, 100]], "expected": [[1, 700], [2, 100]]}
{"case": "RV20", "scenario": "same monetary value in another order", "actual": [[1, 900], [2, 100]], "expected": [[1, 900], [2, 100]]}
{"case": "RV20", "scenario": "empty database", "actual": [], "expected": []}
{"completed": "all 20 submissions inspected; local executions above; no live HTTP/TLS/PostgreSQL test"}
```

Числа потоков в trace — локальные Python thread IDs, не PostgreSQL PID. Instrumented attempt у RV15 — модель порядка вызовов; она доказала последовательную организацию теста, но не результат SQL-конкуренции. Service в RV13/RV14 — ровно локальная модель config/generation/restart из задания. Заглушки request в RV16 проверили только реакцию на статус. Загрузка модуля RV09 не делает сетевого запроса.

## Целостность входных файлов

Точная команда:

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib
import json
root=Path('input')
manifest=json.loads((root/'manifest.json').read_text())
mismatches=[]
for name, expected in manifest['sha256'].items():
 actual=hashlib.sha256((root/name).read_bytes()).hexdigest()
 if actual != expected: mismatches.append(name)
print(json.dumps({'manifest_version':manifest['version'],'files_verified':len(manifest['sha256']),'hash_mismatches':mismatches,'cases':sorted(p.name for p in root.glob('RV*') if p.is_dir())},ensure_ascii=False))
assert not mismatches
PY
```

Фактический stdout, exit code 0:

```json
{"manifest_version": "2026-10-12.1", "files_verified": 52, "hash_mismatches": [], "cases": ["RV01", "RV02", "RV03", "RV04", "RV05", "RV06", "RV07", "RV08", "RV09", "RV10", "RV11", "RV12", "RV13", "RV14", "RV15", "RV16", "RV17", "RV18", "RV19", "RV20"]}
```

## Ограничения и фиксация

Среда фактического запуска: Python 3.12.3, macOS-26.6.2-x86_64-i386-64bit, SQLite 3.46.0. Сеть, Docker и PostgreSQL не использованы. Адрес lab.invalid не открывался. HTTP 200 на Linux, доверенный TLS на живом endpoint и настоящая конкуренция PostgreSQL не проверены. Это ограничения текущей проверки, а не автоматический диагноз коду ученика. Синтетические evidence.txt/environment.txt атрибутированы материалам сдачи и не выданы за мои запуски.

Статический анализ дополняет конкретные запуски и везде отделён от них. Конечный набор входов не является исчерпывающим перебором всех возможных данных; вывод о контракте основан на анализе реализации и перечисленных существенных границах/сценариях отказа.

answer.json формируется один раз, с benchmark_version из input/manifest.json и run, без изменений скопированным из run-metadata.json. Перед первой записью в памяти проверяются 20 уникальных case_id, допустимые enum-значения, C1 и существование указанных строк исходников. Запись выполняется Python open(..., 'x') для предотвращения перезаписи. method.md записывается тем же способом. После записи ответ не корректируется по ожидаемой оценке; оценивание не запускается.

Проверка перед первой записью прошла: 20 уникальных case_id, 20 статусов C1, 16 ссылок на существующие строки; JSON разбирается, run и benchmark_version совпадают с входными данными. Вердикты: {"accepted": 8, "needs_changes": 9, "unverified": 3}.
