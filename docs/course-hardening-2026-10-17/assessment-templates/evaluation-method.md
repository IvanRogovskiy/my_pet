# Метод первой смысловой оценки

Дата: 2026-10-17. Оценщик: Codex (GPT-6; точный вариант модели не предоставлен), canonical ID `/root/assess_hardening`, kind=model. Это независимая модельная оценка в данном наборе, а не человеческая валидация и не результат обучения реального ученика.

## Границы

Чтение ограничено `assessment-templates/`, `recovery/RS04..RS07/input/`, соответствующими `output/`, `advanced/input/` и `advanced/output/`. Пути в этих материалах за пределами выдачи не раскрывались. Production-исходники и оценщики, protocol, другие исследования, correction, старые оценки и чужие дополнительные выходы не читались. Новых агентов, сети, Docker и облака не было. Прочитаны ровно выданные первые ответы; оценщик не просил их менять и не менял.

Шаблоны задавали критерии и авторские гипотезы о дефектах, поэтому эта проверка не является слепой к ключам. Классификация не засчитывалась сама по себе: каждый вывод сопоставлялся с assignment, исходником, response/findings, а для recovery также с полными PROGRESS и NOTES. Для спорного runtime отдельно учитывался evidence.txt.

## Порядок

1. Через `rg --files` перечислены только разрешённые каталоги. Прочитаны шаблоны и RUBRIC.md. Первоначальный большой вывод нескольких чтений был усечён; нужные response, полные snapshot и все содержательные входы затем перечитаны отдельными небольшими командами Python. TEACHER.md recovery дочитан отдельно. Старые ссылки из учебных данных не открывались.
2. Проверены источники восстановления: assignment, исходные PROGRESS/NOTES, review-02 у RS05, конфликт A/B у RS06 и новый prompt/route у RS07. Прочитаны все response и полные snapshot. Отдельные файлы PROGRESS/NOTES/response у RS06 совпадают со значениями answer.json.
3. Для advanced построчно прочитаны все восемь assignment/submission, AD05/test_submission.py, AD06/evidence.txt и REVIEW.md. Прочитаны все findings и next_step, затем приложенные probe.py, probe-results.json и method.txt. Они рассматривались как артефакты автора первого ответа, а не мои запуски. Скрипт автора повторно не запускался. Сохранённые 1360 комбинаций AD04 и 7225 сравнений AD08 сверены с кодом генерации и журналом; полную сетку я заново не исполнял.
4. Выполнены мои отдельные небольшие локальные пробы над разрешёнными submission и test_submission. Код загружался через compile/exec без записи __pycache__, для AD05 подставлен модуль submission только в памяти. Фикстура AD06, скрипт и журнал находятся в /private/tmp. Команда приведена ниже; весь её код также включён сюда для воспроизводимости.
5. Канонические SHA256 всех пяти answer.json совпали с answer_sha256 шаблонов. Канонизация: `json.dumps(answer, ensure_ascii=False, sort_keys=True, separators=(',', ':'))`, UTF-8. Сырой SHA файла ожидаемо отличается от SHA канонического JSON; это не расхождение содержания или ошибка записи.
6. До собственных проб сняты SHA256 разрешённых исходных входов, первых выходов и шаблонов. После проб и записи пяти оценок все исходные байты совпали с базой. Оценки созданы один раз режимом `x`, без перезаписи первых ответов или входов. Автоматический производственный оценщик не читался и не запускался; проверка JSON и собственных полей — только контроль записи этой оценки.

## Правила выставления

Recovery: result=confirmed означает, что критерий доказан содержанием response и полного снимка с опорой на входные источники. Это не значит, что практика ученика принята. Во всех четырёх случаях все четыре критерия подтверждены. RS04 сохраняет нужны исправления по истории при отсутствующем коде; RS06 оставляет приёмку непроверенной и R2 unknown при реальном дефекте предоставленного файла; RS07 разносит новую невыданную практику 09/1 и отложенную 08/3. Эти различия учитывались по тексту, а не только recovered.

Advanced: reviews.status=assessed, ratings — целые 0..2 по RUBRIC.md. Для каждой шкалы отдельная notes с местом в отзыве, проверенным основанием и причиной балла. Все восемь отзывов получили 2/2/2/2: правильные работы обоснованно приняты без придуманных ошибок; непроверенный Linux runtime честно оставлен непроверенным с конкретным планом получения свидетельства; дефекты объяснены и воспроизводятся. Это верхние баллы на данном небольшом наборе, не вывод об общей безошибочности преподавателя.

defect_coverage оценивается отдельно от качества объяснения. Все шесть дефектов found; finding_indices — нулевые индексы в findings соответствующего review: AD01 D1→[0], D2→[1]; AD03 D1→[0], D2→[1]; AD05 D1→[0]; AD07 D1→[0]. Каждый элемент содержит собственное evidence. Для работ без заявленного дефекта новые искусственные дефекты не добавлялись.

## Смысл, формат и пограничные условия

- Не обнаружено смыслового противоречия между response и полными snapshot. Ошибка синтаксиса оболочки при первой попытке сохранения у RS05/RS06 описана в их method; она не подменяет содержание сохранившегося валидного JSON и не снижает смысловую оценку. Эта проверка не заменяет отдельную полную формальную валидацию записей.
- AD05: исходный вопрос — доказывает ли данный test_overlap пересечение. Ответ правильно говорит, что нет. Без точки приостановки неизменённая reserve такого расписания не создаёт. Предложение согласованного тестового hook рассматривается как условный следующий диагностический шаг, а не новое исходное требование исправить бизнес-логику; это явно оговорено в direction. Само исправление reserve для предотвращения lost update не требуется.
- AD06: ни старый синтетический журнал, ни мой локальный запуск под macOS UID 501 не подтверждают Linux UID 10001 для текущего исходника. Эта часть C1 осталась unverified; за точное разделение границ возможен полный балл по рубрике.
- AD02: уникальность id рассматривается при последовательном использовании jobs согласно заданию, без внешнего удаления/подмены хранилища. Защита от мутации возвращённого результата явно исключена. Дополнительные требования к этим ситуациям не вводились.
- Собственные пробы воспроизводят поведение кода сейчас; они не устанавливают, действительно ли автор первого ответа запускал каждую исторически записанную команду. Доступные журналы и сценарии внутренне согласованы; обнаруженных противоречий с ними нет.

## Мой запуск

Команда: `python3 -B /private/tmp/assess_hardening_20261017_probe.py`. Код завершения 0. Среда: macOS-26.6.2-x86_64-i386-64bit, Python 3.12.3, UID 501. Это среда оценщика, не сведения об ученике и не Linux-стенд.

| Случай | Наблюдение моей пробы |
| --- | --- |
| RS05, RS06 | Покупатели независимы; точный повтор возвращает прежний объект; другое тело возвращает старый payload вместо ValueError. Связь RS06 с A/B не установлена. |
| AD01 | Разные tenant с одним token зависимы; чужое тело вызывает ложный ValueError; append во входном списке меняет снимок и мешает повтору исходного тела. |
| AD02 | Повтор с другим порядком ключей, независимость tenant, конфликт, неизменность входа и сохранность снимка успешны. |
| AD03 | Запас 7 при 4+4 уходит в -1; requests переставляется при успехе и отказе. |
| AD04 | Те же четыре явных сценария: суммарная/обычная нехватка, успех ровно до нуля и пустой пакет соответствуют C1, requests сохраняется. |
| AD05 | test_overlap проходит; отдельная трасса read2/write1/read1/write0, итог [0]. |
| AD06 | Локальная фикстура возвращает assessor value без внешних пробелов; требуемый Linux runtime не проверен. |
| AD07 | cursor=(4,3), limit=2: ожидалось [(4,7),(4,9)], получено [(5,2)]; исходный rows неизменен; начало и конец списка работают. |
| AD08 | Перестановка, кратности, одинаковая сумма разных пар и пустые списки дают ожидаемые результаты без мутации входов. |

Полные фактические результаты этой моей команды:

```json
{
  "assessor": "/root/assess_hardening",
  "environment": {
    "platform": "macOS-26.6.2-x86_64-i386-64bit",
    "python": "3.12.3 (main, Apr  9 2024, 08:09:14) [Clang 15.0.0 (clang-1500.3.9.4)]",
    "uid": 501
  },
  "cases": {
    "RS05": {
      "independent": true,
      "exact_repeat": true,
      "changed_body": {
        "returned": {
          "id": 1,
          "payload": {
            "n": 4
          }
        }
      }
    },
    "RS06": {
      "independent": true,
      "exact_repeat": true,
      "changed_body": {
        "returned": {
          "id": 1,
          "payload": {
            "n": 4
          }
        }
      }
    },
    "AD01": {
      "input_unchanged": true,
      "same_result": true,
      "tenants_independent": false,
      "other_tenant_other_body": {
        "exception": "ValueError"
      },
      "same_scope_conflict": {
        "exception": "ValueError"
      },
      "stored_after_input_mutation": {
        "z": [
          -1,
          3,
          8
        ],
        "a": []
      },
      "snapshot_retained": false,
      "repeat_original": {
        "exception": "ValueError"
      }
    },
    "AD02": {
      "input_unchanged": true,
      "same_result": true,
      "tenants_independent": true,
      "other_tenant_other_body": {
        "returned": {
          "id": 3,
          "payload": {
            "a": [
              5
            ]
          }
        }
      },
      "same_scope_conflict": {
        "exception": "ValueError"
      },
      "stored_after_input_mutation": {
        "z": [
          -1,
          3
        ],
        "a": []
      },
      "snapshot_retained": true,
      "repeat_original": {
        "returned": {
          "id": 1,
          "payload": {
            "z": [
              -1,
              3
            ],
            "a": []
          }
        }
      }
    },
    "AD03": [
      {
        "before": [
          {
            "x": 7
          },
          [
            [
              "x",
              4
            ],
            [
              "x",
              4
            ]
          ]
        ],
        "actual": {
          "returned": {
            "x": -1
          }
        },
        "after": [
          {
            "x": -1
          },
          [
            [
              "x",
              4
            ],
            [
              "x",
              4
            ]
          ]
        ]
      },
      {
        "before": [
          {
            "x": 0,
            "y": 3
          },
          [
            [
              "y",
              2
            ],
            [
              "x",
              1
            ]
          ]
        ],
        "actual": {
          "exception": "ValueError"
        },
        "after": [
          {
            "x": 0,
            "y": 3
          },
          [
            [
              "x",
              1
            ],
            [
              "y",
              2
            ]
          ]
        ]
      },
      {
        "before": [
          {
            "x": 7,
            "y": 3
          },
          [
            [
              "y",
              2
            ],
            [
              "x",
              3
            ],
            [
              "x",
              4
            ]
          ]
        ],
        "actual": {
          "returned": {
            "x": 0,
            "y": 1
          }
        },
        "after": [
          {
            "x": 0,
            "y": 1
          },
          [
            [
              "x",
              3
            ],
            [
              "x",
              4
            ],
            [
              "y",
              2
            ]
          ]
        ]
      },
      {
        "before": [
          {
            "x": 7
          },
          []
        ],
        "actual": {
          "returned": {
            "x": 7
          }
        },
        "after": [
          {
            "x": 7
          },
          []
        ]
      }
    ],
    "AD04": [
      {
        "before": [
          {
            "x": 7
          },
          [
            [
              "x",
              4
            ],
            [
              "x",
              4
            ]
          ]
        ],
        "actual": {
          "exception": "ValueError"
        },
        "after": [
          {
            "x": 7
          },
          [
            [
              "x",
              4
            ],
            [
              "x",
              4
            ]
          ]
        ]
      },
      {
        "before": [
          {
            "x": 0,
            "y": 3
          },
          [
            [
              "y",
              2
            ],
            [
              "x",
              1
            ]
          ]
        ],
        "actual": {
          "exception": "ValueError"
        },
        "after": [
          {
            "x": 0,
            "y": 3
          },
          [
            [
              "y",
              2
            ],
            [
              "x",
              1
            ]
          ]
        ]
      },
      {
        "before": [
          {
            "x": 7,
            "y": 3
          },
          [
            [
              "y",
              2
            ],
            [
              "x",
              3
            ],
            [
              "x",
              4
            ]
          ]
        ],
        "actual": {
          "returned": {
            "x": 0,
            "y": 1
          }
        },
        "after": [
          {
            "x": 0,
            "y": 1
          },
          [
            [
              "y",
              2
            ],
            [
              "x",
              3
            ],
            [
              "x",
              4
            ]
          ]
        ]
      },
      {
        "before": [
          {
            "x": 7
          },
          []
        ],
        "actual": {
          "returned": {
            "x": 7
          }
        },
        "after": [
          {
            "x": 7
          },
          []
        ]
      }
    ],
    "AD05": {
      "test_result": {
        "returned": null
      },
      "independent_trace": {
        "state": [
          0
        ],
        "trace": [
          [
            "read",
            2
          ],
          [
            "write",
            1
          ],
          [
            "read",
            1
          ],
          [
            "write",
            0
          ]
        ]
      }
    },
    "AD06": {
      "local_result": "assessor value",
      "linux_uid_10001": "unverified; no authorized stand in supplied files"
    },
    "AD07": {
      "rows": [
        [
          5,
          2
        ],
        [
          4,
          9
        ],
        [
          4,
          3
        ],
        [
          4,
          7
        ]
      ],
      "cursor": [
        4,
        3
      ],
      "limit": 2,
      "expected": [
        [
          4,
          7
        ],
        [
          4,
          9
        ]
      ],
      "actual": [
        [
          5,
          2
        ]
      ],
      "rows_unchanged": true,
      "start": [
        [
          4,
          3
        ],
        [
          4,
          7
        ]
      ],
      "end": []
    },
    "AD08": [
      {
        "inputs": [
          [
            [
              "x",
              2
            ],
            [
              "y",
              -1
            ]
          ],
          [
            [
              "y",
              -1
            ],
            [
              "x",
              2
            ]
          ]
        ],
        "expected": true,
        "actual": true,
        "inputs_unchanged": true
      },
      {
        "inputs": [
          [
            [
              "x",
              2
            ]
          ],
          [
            [
              "x",
              1
            ],
            [
              "x",
              1
            ]
          ]
        ],
        "expected": false,
        "actual": false,
        "inputs_unchanged": true
      },
      {
        "inputs": [
          [
            [
              "x",
              1
            ]
          ],
          [
            [
              "x",
              1
            ],
            [
              "x",
              1
            ]
          ]
        ],
        "expected": false,
        "actual": false,
        "inputs_unchanged": true
      },
      {
        "inputs": [
          [],
          []
        ],
        "expected": true,
        "actual": true,
        "inputs_unchanged": true
      }
    ]
  }
}
```

Код моей пробы (это не скрипт автора отзыва и не production-оценщик):

```python
from pathlib import Path
from copy import deepcopy
import asyncio
import itertools
import json
import os
import platform
import sys
import types

ROOT = Path('/Users/ivanrogovskiy/Documents/tries/my_pet/docs/course-hardening-2026-10-17')
OUT = Path('/private/tmp/assess_hardening_20261017_results.json')
results = {'assessor': '/root/assess_hardening', 'environment': {
    'platform': platform.platform(), 'python': sys.version, 'uid': os.getuid()}, 'cases': {}}

def load(relative):
    path = ROOT / relative
    ns = {}
    exec(compile(path.read_text(), str(path), 'exec'), ns)
    return ns

def outcome(fn, *args):
    try:
        return {'returned': deepcopy(fn(*args))}
    except Exception as exc:
        return {'exception': type(exc).__name__}

for case in ['RS05', 'RS06']:
    submit = load(f'recovery/{case}/input/submission.py')['submit']
    state = {}
    first = submit(state, 'one', 'same', {'n': 4})
    second = submit(state, 'two', 'same', {'n': 7})
    repeated = submit(state, 'one', 'same', {'n': 4})
    results['cases'][case] = {
        'independent': first is not second and len(state) == 2,
        'exact_repeat': repeated is first,
        'changed_body': outcome(submit, state, 'one', 'same', {'n': 9})}

for case in ['AD01', 'AD02']:
    enqueue = load(f'advanced/input/{case}/submission.py')['enqueue']
    jobs, payload = {}, {'z': [-1, 3], 'a': []}
    original = deepcopy(payload)
    first = enqueue(jobs, 'one', 'same', payload)
    input_unchanged = payload == original
    repeated = enqueue(jobs, 'one', 'same', {'a': [], 'z': [-1, 3]})
    same_result = repeated == first and len(jobs) == 1
    second = enqueue(jobs, 'two', 'same', original)
    independent = first['id'] != second['id'] and len(jobs) == 2
    other_body = outcome(enqueue, jobs, 'three', 'same', {'a': [5]})
    conflict = outcome(enqueue, jobs, 'one', 'same', {'z': [-1, 9], 'a': []})
    payload['z'].append(8)
    stored_after = deepcopy(first['payload'])
    original_repeat = outcome(enqueue, jobs, 'one', 'same', original)
    results['cases'][case] = {
        'input_unchanged': input_unchanged, 'same_result': same_result,
        'tenants_independent': independent, 'other_tenant_other_body': other_body,
        'same_scope_conflict': conflict, 'stored_after_input_mutation': stored_after,
        'snapshot_retained': stored_after == original, 'repeat_original': original_repeat}

for case in ['AD03', 'AD04']:
    allocate = load(f'advanced/input/{case}/submission.py')['allocate']
    observed = []
    for stock, req in [({'x': 7}, [('x', 4), ('x', 4)]),
                       ({'x': 0, 'y': 3}, [('y', 2), ('x', 1)]),
                       ({'x': 7, 'y': 3}, [('y', 2), ('x', 3), ('x', 4)]),
                       ({'x': 7}, [])]:
        before = [deepcopy(stock), deepcopy(req)]
        actual = outcome(allocate, stock, req)
        observed.append({'before': before, 'actual': actual, 'after': [stock, req]})
    results['cases'][case] = observed

reserve = load('advanced/input/AD05/submission.py')['reserve']
module = types.ModuleType('submission')
module.reserve = reserve
sys.modules['submission'] = module
test = load('advanced/input/AD05/test_submission.py')['test_overlap']
test_result = outcome(test)
async def overlap():
    state, trace = [2], []
    await asyncio.gather(reserve(state, trace), reserve(state, trace))
    return {'state': state, 'trace': trace}
results['cases']['AD05'] = {'test_result': test_result, 'independent_trace': asyncio.run(overlap())}

read_config = load('advanced/input/AD06/submission.py')['read_config']
fixture = Path('/private/tmp/assess_hardening_20261017_fixture.txt')
fixture.write_text('\t\n assessor value \n\t')
results['cases']['AD06'] = {'local_result': read_config(fixture),
    'linux_uid_10001': 'unverified; no authorized stand in supplied files'}

page = load('advanced/input/AD07/submission.py')['page']
rows = [(5, 2), (4, 9), (4, 3), (4, 7)]
source = rows.copy()
results['cases']['AD07'] = {'rows': source,
    'cursor': [4, 3], 'limit': 2, 'expected': [[4, 7], [4, 9]],
    'actual': page(rows, (4, 3), 2), 'rows_unchanged': rows == source,
    'start': page(rows, None, 2), 'end': page(rows, (6, 0), 2)}

same_items = load('advanced/input/AD08/submission.py')['same_items']
checks = []
for left, right, expected in [
    ([('x', 2), ('y', -1)], [('y', -1), ('x', 2)], True),
    ([('x', 2)], [('x', 1), ('x', 1)], False),
    ([('x', 1)], [('x', 1), ('x', 1)], False),
    ([], [], True)]:
    before = [deepcopy(left), deepcopy(right)]
    actual = same_items(left, right)
    checks.append({'inputs': before, 'expected': expected, 'actual': actual,
                   'inputs_unchanged': before == [left, right]})
results['cases']['AD08'] = checks
OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(results, ensure_ascii=False, indent=2))
```
