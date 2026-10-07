# Воспроизводимая подготовка локального Linux/kind

[bootstrap.py](bootstrap.py) создаёт один собственный kind node и готовит в нём Linux-пользователя 1500, D-Bus/user manager, доступ к журналу и Ansible. В новой приватной папке устанавливаются **kind 0.29.0, kubectl 1.33.1, Helm 3.18.3, Terraform 1.13.5**; чужие CLI и прежние временные каталоги не используются. Образы Python/PostgreSQL/kindest node закреплены digest. CLI скачиваются с официальных release endpoints, до запуска сверяются опубликованные SHA256; URL и обе суммы сохранены в `stand.json`.

Это локальный учебный профиль для systemd/Ansible/Terraform/Kubernetes. Он не заменяет SSH к VM, reboot гостевой ОС, remote Terraform state или облачный IAM. Требуются Python 3.11+, curl, запущенный Docker, минимум 8 GiB свободного места и 4 GiB RAM Docker; желательно больше при работающих сторонних контейнерах. Проверен macOS ARM; другие поддержанные в выборе бинарников платформы требуют собственного runtime-прогона.

```sh
python3 backend-devops-theory/assets/labs/bootstrap.py doctor /tmp/my-linux-stand
python3 backend-devops-theory/assets/labs/bootstrap.py setup /tmp/my-linux-stand
python3 backend-devops-theory/assets/labs/bootstrap.py check /tmp/my-linux-stand
```

`setup` явно разрешает скачивание указанных инструментов/зависимостей и создание локального kind. Kind использует привилегированный Docker node; не применять этот профиль как границу безопасности для недоверенного кода. Нет платных облачных ресурсов, изменения глобального kubeconfig или установки в host `/usr/local/bin`. Уникальное имя, node ID и kind ownership label сверяются перед повторной операцией. При прерванной подготовке повторить setup в **том же** каталоге; исчезнувший ранее записанный node не создаётся заново молча.

На node дополнительно устанавливается `dbus-user-session` из Debian репозитория; фактические версии systemd/dbus/Python записываются в паспорт. Это не полностью герметичный apt snapshot. Ansible и его зависимости закреплены по версиям; pip report внутри `ansible-deps/install-report.json` содержит фактические hashes. Для строгого повторения между датами нужен отдельный архив Debian-пакетов и Python wheels, а не обещание побайтовой идентичности apt update.

Образы импортируются в kind с собственными локальными именами. Точный containerd **manifest digest** определяется после импорта и записывается в `images`; registry index digest не подменяет manifest. `kubeconfig` содержит доступ к собственному локальному кластеру, хранится внутри папки 0700 и не включается в отчёты/репозиторий.

Проверка и пауза:

```sh
python3 backend-devops-theory/assets/labs/bootstrap.py audit /tmp/my-linux-stand
python3 backend-devops-theory/assets/labs/bootstrap.py stop /tmp/my-linux-stand
python3 backend-devops-theory/assets/labs/bootstrap.py resume /tmp/my-linux-stand
python3 backend-devops-theory/assets/labs/bootstrap.py check /tmp/my-linux-stand
```

`audit` — **авторская** команда, открывающая эталоны. Она проверяет L02a/b/c, A25, T24, K27 и H28 в цикле 1/0/1 и сохраняет отдельный `checks-<id>` с JSON/диагностикой. Обычному ученику выдаётся одна подходящая лаборатория из [README](README.md), без запуска всей матрицы. Пауза останавливает только собственный node; root filesystem, PVC, инструменты и evidence сохраняются. После resume проверяется прежний marker и готовность кластера/user manager. Пауза не освобождает диск. Автоматического удаления кластера или volumes нет.

Для собственного запуска lab.py использовать `tools/` этого каталога в PATH, его kubeconfig через `KUBECONFIG`, явный context `kind-<prefix>` из паспорта и точные `images.*.manifest`. Не копировать абсолютные пути чужого отчёта. Linux-лаборатории выполнять внутри node через `docker exec <node> runuser -u learner -- env XDG_RUNTIME_DIR=/run/user/1500 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1500/bus ...`; это сохраняет supplementary group для чтения журнала. `docker exec --user 1500:1500` её теряет. CLI расположен в `/opt/orderflow-labs/lab.py`, Ansible — `/opt/ansible-playbook`. Для целевого повторного авторского прогона доступен `audit ... --cases L02a A25`.

Официальные процедуры: [kind: создание, kubeconfig и импорт образов](https://kind.sigs.k8s.io/docs/user/quick-start/), [установка Helm из release](https://helm.sh/docs/intro/install/). Это закреплённая учебная матрица, не автоматически выбранные latest-версии.
