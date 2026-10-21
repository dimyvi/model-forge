# Kubernetes

[Документация проекта](README.md) · [Установка K3s](k3s-installation.md)

Для DEV и PROD используются отдельные кластеры K3s. Миграция приложения с Docker Compose ещё не выполнена: Kubernetes-манифесты, публикация образов в registry и deploy в K3s не добавлены в репозиторий.

## Состояние инфраструктуры

На 22 октября 2026 года установлена версия K3s `v1.37.1+k3s1`. В DEV зарегистрирована нода `dev-server`, в PROD — `prod-control`, `prod-worker1` и `prod-worker2`. Все четыре ноды прошли проверку `Ready`.

Межнодовая сеть, DNS, постоянное хранилище и развёртывание Model Forge требуют отдельной проверки. Мониторинг на INFRA и blue-green запланированы.

## Виртуальные машины

Ресурсы каждой ВМ: 2 vCPU, 4 ГБ RAM, диск 40 ГБ.

| ВМ | IP | Hostname | Назначение |
| --- | --- | --- | --- |
| 1 | `192.168.1.218` | `infra` — плановое имя | Grafana, Prometheus, Loki, Alertmanager; вне кластеров K3s |
| 2 | `192.168.1.193` | `dev-server` | Однонодовый DEV-кластер: управление и запуск приложения |
| 3 | `192.168.1.226` | `prod-control` | K3s Server, управляющая нода PROD |
| 4 | `192.168.1.234` | `prod-worker1` | K3s Agent, worker-нода PROD |
| 5 | `192.168.1.138` | `prod-worker2` | K3s Agent, worker-нода PROD |

PROD состоит из ВМ 3–5. DEV на ВМ 2 не подключается к PROD. Мониторинг на ВМ 1 не участвует в обработке пользовательских запросов; для его развёртывания планируется Docker Compose.

## Роли нод

K3s Server включает control plane и компоненты запуска контейнеров. По умолчанию на Server разрешено размещение Pod. K3s Agent запускает назначенные ему Pod и не содержит control plane.

| Компонент | Назначение | Размещение |
| --- | --- | --- |
| API Server | Приём запросов к API Kubernetes | DEV Server / PROD Server |
| Scheduler | Выбор ноды для Pod | DEV Server / PROD Server |
| Controllers | Поддержание заданного состояния ресурсов | DEV Server / PROD Server |
| Datastore K3s | Состояние кластера; для одиночного Server по умолчанию SQLite | DEV Server / PROD Server |
| Kubelet | Управление Pod на ноде | Server и Agent |
| Containerd | Загрузка образов и запуск контейнеров | Server и Agent |
| Сетевые компоненты | Связь Pod и доступ через Service | Server и Agent |

При создании Deployment controllers создают Pod, Scheduler назначает им ноды, а kubelet запускает контейнеры через containerd. Состояние K3s хранится отдельно от PostgreSQL приложения.

Значение `<none>` в колонке `ROLES` у agents означает отсутствие метки роли. ML-worker приложения и worker-нода Kubernetes — разные сущности: первый выполняет обучение, вторая предоставляет ресурсы для Pod.

Справочники: [K3s Architecture](https://docs.k3s.io/architecture), [Kubernetes Components](https://kubernetes.io/docs/concepts/overview/components/).

### Ограничение размещения на PROD Server

Для `prod-control` запланирован taint `NoSchedule`. Перед применением проверяются готовность обеих worker-нод и размещение системных Pod:

```bash
# ВМ 3
sudo /usr/local/bin/k3s kubectl describe node prod-control
sudo /usr/local/bin/k3s kubectl get pods -A -o wide
```

Установка taint:

```bash
sudo /usr/local/bin/k3s kubectl taint nodes prod-control \
  node-role.kubernetes.io/control-plane=true:NoSchedule
```

`NoSchedule` запрещает назначение новых Pod без подходящего toleration. Уже запущенные Pod остаются на ноде. Kubelet и containerd продолжают работать. На однонодовом DEV-кластере это ограничение не применяется.

Документация: [Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/).

## Компоненты приложения

План переноса сервисов Compose в Kubernetes:

| Сервис / конфигурация | Ресурсы Kubernetes |
| --- | --- |
| `frontend` | Deployment с production-образом, Service |
| `backend` | Deployment с Gunicorn, Service |
| `ml-worker` | Deployment из backend-образа, команда `python manage.py run_ml_worker`, одна реплика |
| `db` | PostgreSQL: StatefulSet на одну реплику, PVC и Service |
| `migrate` | Job для `migrate` и `collectstatic`; завершение до выпуска приложения |
| `.env` | ConfigMap с обычными настройками, Secret с паролями и ключами |
| `media_data`, `static_data` | Постоянные тома с доступом из соответствующих Pod |
| Внешний Nginx | Ingress и Traefik с HTTPS |

Traefik, CoreDNS и ServiceLB входят в стандартную установку K3s. Состав и состояние проверяются через `kubectl get pods -A`: [Networking Services](https://docs.k3s.io/networking/networking-services).

План маршрутизации:

```text
Браузер → роутер:443 → Traefik
                         ├── /             → Service frontend → Pod frontend
                         └── /api/, /admin/ → Service backend  → Pod backend → PostgreSQL
```

Правила задаются в Ingress. API Server Kubernetes управляет ресурсами и не обрабатывает запросы к сайту. Проброс роутера должен указывать на выбранную точку входа Traefik.

## Ограничения

### Хранилище

Backend и ML-worker должны иметь доступ к одним файлам в `media`. Worker читает датасет через `dataset.file.path`, backend сохраняет CSV и выдаёт готовые модели.

Встроенный provisioner `local-path` создаёт том на конкретной ноде. Такой том не переносится на другую ВМ при отказе. Начальный вариант — размещение связанных Pod на одном worker. Для распределения между нодами требуется общее файловое хранилище, например NFS с provisioner. MinIO потребует изменений в коде работы с файлами.

`collectstatic` записывает Django-статику в том, который читает frontend Nginx. При переносе нужен общий доступ к этому тому либо изменение сборки и выдачи статики.

PostgreSQL с одной репликой и PVC сохраняет данные при пересоздании Pod, пока доступен диск. StatefulSet не настраивает репликацию базы. Для PostgreSQL и media необходимы резервные копии и проверка восстановления.

### Ресурсы

Для первоначального развёртывания предусмотрена одна реплика ML-worker. Requests и limits определяются по потреблению на тестовых CSV с запасом для ОС и K3s. Если требуется строго одно обучение за раз, стратегия обновления worker должна исключать временный запуск второй реплики.

Диск ВМ ограничен 40 ГБ. Для образов, логов, метрик и резервных копий нужны ограничения хранения. Одновременный запуск Blue и Green требует дополнительного запаса памяти.

### Отказоустойчивость

PROD имеет один Server. При его отказе запущенные контейнеры на agents могут продолжить работу, но создание и перераспределение Pod недоступны. Локальные диски и проброс роутера на одну ВМ также остаются точками отказа. Если все ВМ размещены на одном физическом хосте, его отказ затронет весь стенд.

## Blue-green

Blue — рабочая версия frontend/backend, Green — версия кандидата на выпуск. Обе размещаются в одном PROD-кластере. Цвет не привязан к конкретной ВМ.

Планируется один namespace с метками `version: blue` и `version: green`. Стабильные Service выбирают активную версию по selector. Service выбирает Pod в своём namespace: [Service](https://kubernetes.io/docs/concepts/services-networking/service/).

Порядок выпуска:

1. Развернуть Green без переключения пользовательского трафика.
2. Проверить Green по отдельному маршруту: вход, загрузка CSV, обучение, скачивание модели.
3. Переключить Service frontend и backend на Green.
4. Сохранить Blue на время проверки после выпуска, затем удалить неактивную версию.

Переключение двух Service не атомарно. Frontend и backend должны допускать кратковременную работу разных версий. PostgreSQL и media остаются общими для цветов; миграции должны быть совместимы с обеими версиями. Переключение трафика обратно на Blue не отменяет изменения базы.

На первом этапе используется один общий ML-worker с форматом задач, совместимым с обеими версиями API. Автоматизация blue-green в CI/CD ещё не реализована.

## План миграции

- [x] Установить отдельные DEV- и PROD-кластеры K3s.
- [ ] Проверить системные Pod, межнодовую сеть, DNS и firewall.
- [ ] Ограничить размещение приложений на `prod-control`.
- [ ] Определить хранилище PostgreSQL, media и Django-статики; проверить восстановление из backup.
- [ ] Подготовить registry и образы с тегами версий.
- [ ] Добавить манифесты DEV и Job миграций.
- [ ] Проверить приложение в DEV через Ingress.
- [ ] Подготовить PROD, HTTPS и перенос данных с Compose.
- [ ] Перевести CI/CD на публикацию образов и deploy в K3s.
- [ ] Развернуть мониторинг на INFRA.
- [ ] Настроить blue-green и проверить откат трафика.

## Материалы для изучения

Рекомендуемый порядок:

1. [Kubernetes Components](https://kubernetes.io/docs/concepts/overview/components/) и [K3s Architecture](https://docs.k3s.io/architecture) — компоненты кластера и роли нод.
2. [Pods](https://kubernetes.io/docs/concepts/workloads/pods/) и [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) — запуск приложений, реплики и обновления.
3. [Service](https://kubernetes.io/docs/concepts/services-networking/service/) — адресация и доступ к Pod.
4. [Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/) и [Traefik в K3s](https://docs.k3s.io/networking/networking-services#traefik-ingress-controller) — маршрутизация HTTP/HTTPS.
5. [ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/) и [Secret](https://kubernetes.io/docs/concepts/configuration/secret/) — настройки, учётные данные и доступ к ним.
6. [Persistent Volumes / PVC](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) и [хранилище K3s](https://docs.k3s.io/add-ons/storage) — постоянные данные и привязка томов к нодам.
7. [Requests и limits](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/) и [probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/) — ресурсы и проверки состояния контейнеров.
8. [Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/) — однократные задачи, в том числе миграции.

Практические упражнения: [Learn Kubernetes Basics](https://kubernetes.io/docs/tutorials/kubernetes-basics/). Команды для установленного стенда: [проверка кластеров](k3s-installation.md#проверка-кластеров).
