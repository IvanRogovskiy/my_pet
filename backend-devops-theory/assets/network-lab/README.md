# Готовый TLS endpoint для 03/1

Редакция 2026-10-12.1. Подготовка преподавателя до выдачи curl-задания: Python3.11+, cryptography50.0.2, право bind только 127.0.0.1. Зависимость из requirements.txt устанавливать в выбранный venv; fixture не скачивает её автоматически. Docker, Flask, Django и системная установка CA не требуются. Все данные синтетические.

Из корня репозитория, в первом терминале:

```sh
python3 -m pip install -r backend-devops-theory/assets/network-lab/requirements.txt
python3 backend-devops-theory/assets/network-lab/fixture.py prepare /tmp/of-tls-student
python3 backend-devops-theory/assets/network-lab/fixture.py serve /tmp/of-tls-student
```

Установка нужна только при отсутствии закреплённой зависимости в выбранной среде. prepare требует новый каталог; owner.json — публичный паспорт CA/leaf с UTC-сроками и SHA. CA private key не сохраняется, leaf/control keys имеют 0600, каталог 0700. serve работает на переднем плане до stop; ready.json появляется только после bind всех трёх endpoint, содержит новые instance и динамические ports.

Во втором терминале:

```sh
python3 backend-devops-theory/assets/network-lab/fixture.py check /tmp/of-tls-student
python3 backend-devops-theory/assets/network-lab/fixture.py stop /tmp/of-tls-student
```

check проверяет живую идентичность и пять настоящих HTTP/TLS исходов: trusted200, trusted403, unknown CA, wrong name, expired leaf. Проверка только timeout/refused не проходит как ожидаемый TLS-отказ. Сохраняется отдельный check-*.json, exit0/1/2 означает успех/нарушение/непроверенную среду. Это stdlib HTTP/TLS проверка; самостоятельные curl-запросы ученика остаются частью 03/1. Для них использовать localhost и порт valid/expired из ready.json, /denied для 403, --cacert с ca.pem. Подстановка 127.0.0.1 вместо localhost проверяет несовпадение SAN.

Перед продолжением после паузы сверить паспорт и выполнить check. Истёкший valid leaf не восстанавливается копированием старого PEM: после stop создать новый каталог/generation, сохранить прежнее evidence. serve отказывается использовать истёкший valid leaf; каждый запуск заменяет stale ready и проверяющий сверяет instance с ответом. Второй одновременный serve запрещён lock. stop отправляет приватный control token своему loopback endpoint; процессы по одному PID не убиваются. После подтверждённого stop ready удалён, порты закрыты. Private ключи остаются в собственном каталоге: после сохранения публичного отчёта удалить только этот каталог.

Smoke проверяется тестами в tests/test_course_revision.py; на машине без cryptography TLS-тесты явно skipped. Отдельный запуск в кэшированном Linux-образе указан в отчёте редакции, не считается установкой на машине ученика.
