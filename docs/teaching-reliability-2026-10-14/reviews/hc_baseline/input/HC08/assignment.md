# HC08 — тема 08/3

C1: remember(cache, tenant, token, body) возвращает сохранённый результат для одинаковых tenant/token/body; иное тело в той же области даёт ValueError. Tenant независим. body — словарь строк; входные словари нельзя менять.
