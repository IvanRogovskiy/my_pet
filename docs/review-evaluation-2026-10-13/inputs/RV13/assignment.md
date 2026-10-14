# RV13 — тема 25/2

C1: deploy(service, config) применяет конфигурацию. При её изменении вызывается restart() и возвращается changed=1; повтор с тем же config сохраняет config и generation, возвращает changed=0. Предоставленная модель service имеет строку config и счётчик generation; restart() увеличивает generation на один. Это локальная модель эффекта перезапуска, не проверка настоящего Ansible/systemd.
