# Настоящая проверка gates и артефактов в GitLab

Авторский опыт для 12/1–2 и предпосылок 26. Четыре pipeline в **новых** случайных ветках явно выбранного приватного учебного проекта. Main, CI variables, environments и настройки доступа не изменяются. Нужны доступ через авторизованный glab, `.gitlab-ci.yml` в default branch, стандартный путь CI-конфига и runner с доступом к закреплённому Python image. Pipeline потребляет обычные CI minutes проекта; платные дополнительные ресурсы сам инструмент не заказывает.

| Сценарий | Gate | Marker | Смысл |
| --- | --- | --- | --- |
| bypass | failed | success до запуска gate | Дефект needs позволяет обойти проверку |
| blocked | failed | skipped | Правильная зависимость блокирует следующий шаг |
| success | success | success после gate | Передан и проверен артефакт того же commit |
| corrupt | success | failed | Изменённое содержимое отвергнуто проверкой хеша |

Marker записывает синтетический JSON; приложения или production deploy здесь нет. Manual gate — управляемая синхронизация опыта: bypass успевает завершиться **до** запуска падающей проверки. В остальных сценариях gate запускается после успешной сборки. Не переносить неисправный вариант в рабочий pipeline.

`hosted.py` принимает путь к glab-compatible shell wrapper. Пример собственного `gitlab.sh`: `#!/bin/sh`, затем `exec glab "$@"`. Авторизоваться локально поддерживаемым способом; токены не передавать в argv/чат. В этом репозитории ранее настроенный wrapper находится в `course-audit/2026-10-01/scripts/gitlab.sh`; установленный skill от него не зависит, можно передать свой.

```sh
python3 backend-devops-theory/assets/gitlab-validation/hosted.py prepare /tmp/my-gitlab-audit --project my-namespace/my-private-course
python3 backend-devops-theory/assets/gitlab-validation/hosted.py publish /tmp/my-gitlab-audit --wrapper ./gitlab.sh
python3 backend-devops-theory/assets/gitlab-validation/hosted.py collect /tmp/my-gitlab-audit --wrapper ./gitlab.sh --seconds 40
python3 backend-devops-theory/assets/gitlab-validation/hosted.py verify /tmp/my-gitlab-audit --wrapper ./gitlab.sh
```

`collect` можно повторять: завершённые сценарии не запускаются заново. До `verify` у каждого сценария должен появиться `result`; успешный выход collect при ещё выполняющемся pipeline означает лишь успешный сбор текущего состояния. `verify` отдельно скачивает build payload/manifest, пересчитывает SHA256, сверяет promotion и timestamps, проверяет неизменность main. Не считать четыре намеренно разные статуса pipeline четырьмя зелёными pipeline: три должны быть failed именно по условиям опыта.

Перед POST публикации сохраняется pending-запись. Если исход операции неизвестен, инструмент не делает слепой повтор; сверить ref/commit в GitLab. Ветки и результаты остаются для ревью. Автоматического удаления веток и retry неудачных jobs нет. `state.json` содержит только выбранные поля, commit, job/pipeline URLs и хеши; kubeconfig, environment, trace и полный API project response туда не входят.

**Правило обработки API:** даже GET проекта может вернуть credential-поля. Сначала разобрать ответ в памяти, затем выбрать разрешённые поля; не печатать полный ответ до фильтрации. Рекурсивная маска token/password/secret и известные префиксы — дополнительная защита, не замена allowlist. При фактическом раскрытии отдельно согласовать ротацию нужного типа токена, не менять authentication token runner вместо registration token.

Основание механизма: [GitLab needs](https://docs.gitlab.com/ci/yaml/needs/) и [job artifacts](https://docs.gitlab.com/ci/jobs/job_artifacts/). Проведённый опыт сохранён в `docs/course-quality-2026-10-06/gitlab/` основного репозитория; ссылки на документацию не заменяют реальный результат.
