# PostgreSQL и RabbitMQ: ошибки backend на настоящих сервисах

Четыре изолированных задания существующих тем. Они не являются вводным проектом и не заменяют интеграцию OrderFlow. Python хоста 3.11+, запущенный Docker, минимум 5 GiB свободного диска и 2 GiB RAM Docker; проверена macOS ARM с Linux-контейнерами. Docker до темы 10 может использовать преподаватель для выдачи готовой БД: ученику не требуется самостоятельно изучать его раньше программы.

| ID | Этап | Что проверяется |
| --- | --- | --- |
| B07 | 07/2 | Реальный HTTP GET/PATCH, fixture-сессия двух пользователей, владелец из PostgreSQL, неизменность чужого заказа |
| B08R | 08/2 | Два настоящих соединения и барьер, Read Committed, последняя единица товара, rollback при ошибке создания заказа |
| B08I | 08/3 | Одновременный одинаковый ключ, область owner/key, конфликт quantity, откат при недостатке остатка |
| B17 | 17/3 | Реальный RabbitMQ confirm, crash publisher до mark, crash consumer после commit до ack, повторная доставка; атомарный откат receipt/effect |

## Стенд

Все команды выполняются от корня репозитория. Выбрать новый каталог. `setup` скачивает отсутствующие образы и зависимости, создаёт только локальные ресурсы с уникальным владельцем. Стенд использует PostgreSQL 16.15, RabbitMQ 3.13.7 и Python 3.12.14 из закреплённых image digests; клиентские Python-пакеты закреплены в [Dockerfile](Dockerfile). `/dependencies.json` внутри клиентского image содержит pip report с URL/хешами загруженных пакетов. Это учебная проверенная комбинация, не рекомендация публиковать старые версии в Интернет.

```sh
python3 backend-devops-theory/assets/backend-labs/stand.py doctor /tmp/my-backend-stand
python3 backend-devops-theory/assets/backend-labs/stand.py setup /tmp/my-backend-stand
python3 backend-devops-theory/assets/backend-labs/stand.py check /tmp/my-backend-stand
```

БД и брокер находятся в отдельной **internal** сети, host ports отсутствуют. Учебные `lab/local-fixture-only` — фиксированные несекретные credentials только этого закрытого fixture; не использовать их для внешнего сервиса. Клиент работает непривилегированным UID, без Linux capabilities и без Docker socket. Это не sandbox для враждебного кода: запускается доверенная учебная сдача, внутри которой доступны учебные БД/брокер.

Пауза и продолжение:

```sh
python3 backend-devops-theory/assets/backend-labs/stand.py stop /tmp/my-backend-stand
python3 backend-devops-theory/assets/backend-labs/stand.py resume /tmp/my-backend-stand
python3 backend-devops-theory/assets/backend-labs/stand.py check /tmp/my-backend-stand
```

Stop сохраняет volumes, образы и evidence. Check после первой успешной проверки требует прежний SQL-маркер, а не восстанавливает потерянную запись. Имена/IDs/labels перечислены в приватном `stand.json`; отсутствующий ранее созданный volume не создаётся молча. Данные продолжают занимать диск на паузе. Удаление — отдельное явное решение с проверкой этого инвентаря; общего prune нет. Повтор `setup` завершает прерванную подготовку собственных ресурсов.

## Самостоятельная попытка

```sh
python3 backend-devops-theory/assets/backend-labs/lab.py prepare /tmp/my-b08r --case B08R
python3 backend-devops-theory/assets/backend-labs/lab.py check /tmp/my-b08r --stand /tmp/my-backend-stand
```

Прочитать `ASSIGNMENT.md`, исправить `submission.py`, предъявить diff, объяснение и `evidence/*.json`. Exit 0 — объявленные критерии выполнены, 1 — обнаружено нарушение, 2 — проверка/среда не завершена. Падение самого harness без валидного отчёта не является обнаруженным дефектом. Барьер в B08R/B08I — тестовая точка синхронизации, не механизм защиты данных; нельзя удалять его ради зелёного результата. Допустимы и условный UPDATE, и корректная блокировка после барьера.

`reset <каталог>` возвращает неисправный исходник; evidence и таблицы предыдущих прогонов сохраняются. Каждый check создаёт отдельную schema `probe_<UUID>` на собственной учебной БД, её имя входит в отчёт. Очередь B17 также уникальна и удаляется после снятия наблюдений; чужие очереди не затрагиваются. Самостоятельную реализацию другого способа дедупликации согласовать с объявленным контрактом receipt/effect до приёмки.

Для автора после самостоятельной попытки: `reference <каталог>` выдаёт один корректный вариант. `audit <новый-каталог> --stand <стенд>` выполняет для всех четырёх заданий цикл bad/reference/reset; ожидаемые коды **1/0/1**. `--case B17` ограничивает авторский прогон одной лабораторией. Эта команда открывает эталоны и не выдаётся ученику первым действием.

B07 проверяет object authorization при уже известной identity, не реализацию password/session security. B08I вызывает операцию непосредственно, HTTP 409 и canonical JSON проверяются в проекте отдельно. B17 использует pika и один publisher/consumer: он доказывает конкретные окна отказа и работу RabbitMQ, не настройку Celery, пропускную способность, HA или восстановление брокера после потери диска.

Механизм конкуренции соответствует [PostgreSQL 16 Read Committed](https://www.postgresql.org/docs/16/transaction-iso.html); независимые стороны подтверждения объясняет [RabbitMQ: acknowledgements и publisher confirms](https://www.rabbitmq.com/docs/confirms). Фактические результаты и версии сохранять отдельно от этих ссылок на механизм.
