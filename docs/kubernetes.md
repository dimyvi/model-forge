# Kubernetes: наш стенд и порядок изучения

[К документации проекта](README.md) · [Установка и проверка K3s](k3s-installation.md)

Kubernetes запускает контейнеры на нескольких машинах и поддерживает описанное состояние приложения. K3s — дистрибутив Kubernetes, который мы выбрали для учебного стенда.

## Что уже сделано

По результатам ручной проверки 22 октября 2026 года:

- DEV: одна нода `dev-server` в состоянии `Ready`.
- PROD: `prod-control`, `prod-worker1` и `prod-worker2` в состоянии `Ready`.
- В выводе всех нод — K3s `v1.37.1+k3s1`.

Это подтверждает регистрацию и готовность нод на момент проверки. Проверка межнодовой сети, DNS, хранилища и самого приложения — следующие отдельные шаги.

Model Forge пока разворачивается через Docker Compose. В репозитории ещё нет Kubernetes-манифестов, Helm chart и CI/CD для K3s. Мониторинг на INFRA и blue-green ниже описаны как план.

## Наши пять ВМ

Для каждой ВМ выделено 2 vCPU, 4 ГБ RAM и 40 ГБ диска.

| ВМ | IP | Имя | Роль |
| --- | --- | --- | --- |
| 1 | `192.168.1.218` | `infra` — плановое имя | Мониторинг; K3s для этой роли не требуется |
| 2 | `192.168.1.193` | `dev-server` | Отдельный DEV-кластер: Server и запуск приложений на одной ВМ |
| 3 | `192.168.1.226` | `prod-control` | Server PROD: управление кластером; по умолчанию также может запускать Pod |
| 4 | `192.168.1.234` | `prod-worker1` | Agent PROD: запуск Pod |
| 5 | `192.168.1.138` | `prod-worker2` | Agent PROD: запуск Pod |

DEV — отдельный кластер на ВМ 2. PROD — один кластер из ВМ 3, 4 и 5. Blue и Green будут версиями приложения внутри PROD, а не новыми ВМ.

На INFRA планируются Grafana, Prometheus, Loki и Alertmanager. Начать можно с Docker Compose. Отказ мониторинга не должен останавливать пользовательские запросы. Если все ВМ находятся на одном физическом сервере, отказ этого сервера затронет весь стенд.

## Чем отличаются Server и Agent

В K3s Server включает управляющие и исполнительные компоненты. Agent включает исполнительные компоненты. Поэтому управляющая ВМ может выполнять приложения, а Agent без управляющих компонентов кластером не управляет. Подробнее: [архитектура K3s](https://docs.k3s.io/architecture).

| Компонент | Для чего нужен | Где у нас |
| --- | --- | --- |
| API Server | Принимает запросы `kubectl` и компонентов кластера | ВМ 2 для DEV; ВМ 3 для PROD |
| Scheduler | Выбирает ноду для ещё не назначенного Pod | Там же |
| Controllers | Сравнивают желаемое состояние с фактическим и создают нужные объекты | Там же |
| Datastore K3s | Хранит состояние кластера; при одиночном Server по умолчанию SQLite | Там же |
| Kubelet | Следит за Pod, назначенными этой ноде | На всех нодах K3s |
| Containerd | Скачивает образы и запускает контейнеры по запросу kubelet | На всех нодах K3s |
| Сетевые компоненты | Связывают Pod и обеспечивают доступ через Service | На всех нодах K3s |

Хранилище состояния K3s и PostgreSQL Model Forge — разные базы с разными задачами. Термины и устройство компонентов: [Kubernetes Components](https://kubernetes.io/docs/concepts/overview/components/).

При создании Deployment API Server принимает описание, controllers создают необходимые Pod, Scheduler назначает ноды, а kubelet через containerd запускает контейнеры. После запуска kubelet следит за ними. Controllers поддерживают число реплик; Scheduler выбирает место для новых Pod.

В `kubectl get nodes` роль `<none>` у `prod-worker1` и `prod-worker2` нормальна: это отсутствие метки роли в выводе, а не ошибка подключения.

### Как оставить PROD Server для управления

Статус `control-plane` сам по себе не запрещает запуск приложений. Для нашей схемы планируется taint `NoSchedule`. Сначала проверьте текущие ограничения и размещение:

```bash
# На ВМ 3
sudo /usr/local/bin/k3s kubectl describe node prod-control
sudo /usr/local/bin/k3s kubectl get pods -A -o wide
```

Когда обе worker-ноды готовы и размещение проверено, можно добавить ограничение:

```bash
sudo /usr/local/bin/k3s kubectl taint nodes prod-control \
  node-role.kubernetes.io/control-plane=true:NoSchedule
```

Оно не переселяет уже запущенные Pod и допускает Pod с подходящим toleration. Управляющая нода сохраняет kubelet и containerd. На единственном DEV Server такой taint пока не нужен. Документация: [Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/).

## Что читать по порядку

Не нужно читать всю документацию сразу. Сначала пройдите первые четыре пункта и попробуйте небольшой Deployment в DEV.

| Порядок | Материал | Что нужно понять на примере Model Forge |
| --- | --- | --- |
| 1 | [Kubernetes Components](https://kubernetes.io/docs/concepts/overview/components/) и [K3s Architecture](https://docs.k3s.io/architecture) | Почему ВМ 3 управляет, а ВМ 4/5 исполняют |
| 2 | [Pods](https://kubernetes.io/docs/concepts/workloads/pods/) и [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) | Pod — экземпляр запущенного приложения; Deployment поддерживает его реплики |
| 3 | [Service](https://kubernetes.io/docs/concepts/services-networking/service/) | Как backend получает стабильный адрес при смене Pod |
| 4 | [Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/) и [Traefik в K3s](https://docs.k3s.io/networking/networking-services#traefik-ingress-controller) | Как домен и путь запроса направляются в frontend или API |
| 5 | [ConfigMap](https://kubernetes.io/docs/concepts/configuration/configmap/) и [Secret](https://kubernetes.io/docs/concepts/configuration/secret/) | Куда перенести настройки и пароли из `.env`; Secret требует защиты доступа |
| 6 | [Persistent Volumes / PVC](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) и [хранилище K3s](https://docs.k3s.io/add-ons/storage) | Где будут жить PostgreSQL, датасеты и модели после пересоздания Pod |
| 7 | [Requests и limits](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/) и [probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/) | Как выделять ресурсы и отличать запущенный контейнер от готового приложения |
| 8 | [Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/) | Как отдельно запускать миграции перед выпуском версии |

Для практики подойдёт [Learn Kubernetes Basics](https://kubernetes.io/docs/tutorials/kubernetes-basics/). Раздел создания кластера можно пропустить, если работающий K3s уже есть. Затем вернитесь к нашим [командам проверки](k3s-installation.md#проверка-кластеров).

## Как части Model Forge будут выглядеть в Kubernetes

Это план объектов, а не готовые манифесты:

| Сейчас в Compose | План в Kubernetes |
| --- | --- |
| `frontend` | Deployment с production-образом и Service |
| `backend` | Deployment с Gunicorn и Service |
| `ml-worker` | Отдельный Deployment из backend-образа с командой `python manage.py run_ml_worker`, сначала одна реплика |
| `db` | PostgreSQL с постоянным томом; например, StatefulSet на одну реплику и Service |
| `migrate` | Job для `migrate` и `collectstatic` с ожиданием его успешного завершения |
| `.env` | ConfigMap для обычных настроек и Secret для паролей/ключей |
| `media_data`, `static_data` | Постоянное хранилище, доступное нужным Pod |
| Внешний Nginx | Ingress и Traefik с настроенным HTTPS |

Уже установленные по умолчанию компоненты K3s включают Traefik, CoreDNS и ServiceLB. Проверяйте их Pod перед установкой дополнительных копий: [Networking Services](https://docs.k3s.io/networking/networking-services).

План пользовательского маршрута:

```text
Браузер → роутер:443 → настроенная точка входа Traefik
                         ├── /             → Service frontend → Pod frontend
                         └── /api/, /admin/ → Service backend  → Pod backend → PostgreSQL
```

Traefik обрабатывает запросы по правилам Ingress. Control plane управляет этими объектами, а запросы к сайту не идут через API Server Kubernetes. Проброс роутера на конкретную ВМ остаётся отдельной точкой отказа, пока не настроен резервный вход.

## Данные и ограничения стенда

Главная задача перед переносом — сохранить доступ к PostgreSQL и файлам приложения.

**Media.** Backend сохраняет CSV, ML-worker читает его через `dataset.file.path`, а backend выдаёт готовую модель. Оба процесса должны видеть одни файлы. Встроенный `local-path` K3s создаёт том на конкретной ноде; такой диск автоматически на другую ВМ не переезжает. Для первого опыта можно разместить связанные Pod и локальный том на одном worker. Для распределения между worker-нодами потребуется общее файловое хранилище, например NFS с подходящим provisioner. Оба варианта требуют резервных копий.

**PostgreSQL.** Один экземпляр с PVC переживает пересоздание контейнера при доступном диске, но не даёт автоматический failover базы при отказе её ВМ. Нужны backup и пробное восстановление. Один StatefulSet не создаёт репликацию PostgreSQL.

**Django-статика.** Сейчас `collectstatic` пишет в volume, который читает frontend Nginx. В K3s надо обеспечить тот же доступ или отдельно изменить способ сборки и выдачи статики. Простой перенос frontend-образа не добавит в него Django-статику.

**Ресурсы.** Начинайте с одной реплики ML-worker и небольших CSV. Requests и limits выбирайте по измерениям, оставляя память ОС и компонентам K3s. При обновлении одного worker-Deployment избегайте временного второго worker, если требуется строго одно обучение за раз. Для логов, метрик, образов и backup задайте лимиты хранения: диск ВМ всего 40 ГБ.

**Отказы.** У PROD один управляющий Server. При его отказе часть контейнеров на workers может продолжить работу, но кластер не сможет нормально создавать и перераспределять Pod. Две worker-ноды сами по себе не делают весь стенд отказоустойчивым.

MinIO, MLflow и Redis/Celery можно изучить позже. Они не требуются для первого переноса текущего приложения; переход на объектное хранилище потребует адаптации кода работы с файлами.

## Как будет работать blue-green

Blue — текущая версия frontend/backend, Green — новая. Обе версии находятся в одном PROD-кластере и могут запускаться на любых разрешённых worker-нодах. Отдельная ВМ для каждого цвета не нужна.

Для первого варианта удобно держать оба цвета в одном namespace, различая Pod метками `version: blue` и `version: green`. Стабильные Service выбирают активный цвет по selector. Обычный Service выбирает Pod в своём namespace, поэтому размещение цветов в разных namespaces потребует другой схемы маршрутизации. Принцип selectors описан в [Service](https://kubernetes.io/docs/concepts/services-networking/service/).

Порядок выпуска:

1. Запустить Green, оставив пользовательский трафик на Blue.
2. Проверить Green по отдельному тестовому маршруту, включая обучение и скачивание.
3. Переключить frontend и backend на Green согласованно. Два Service не переключаются одной атомарной операцией, поэтому краткий смешанный режим надо учитывать.
4. Сохранить Blue для возврата до завершения проверки, затем освободить ресурсы.

База и media обычно общие для двух цветов внутри PROD. Миграции должны быть совместимы с обеими версиями: возврат трафика не отменяет изменения БД. На первом этапе оставляем один общий ML-worker и проверяем совместимость задач с обеими версиями API. Kubernetes сам не выполняет этот сценарий целиком: его нужно описать в deploy-процессе или выбрать подходящий инструмент.

## Порядок переноса Model Forge

- [x] Установить отдельный DEV K3s и PROD K3s с двумя agents.
- [ ] Проверить системные Pod, межнодовую сеть, DNS и правила firewall.
- [ ] Проверить taint управляющей PROD-ноды и оставить её для управления.
- [ ] Освоить Deployment и Service на небольшом приложении в DEV.
- [ ] Выбрать хранение PostgreSQL, media и Django-статики; проверить backup/restore.
- [ ] Подготовить образы с тегами версий и доступный нодам registry, например GHCR.
- [ ] Добавить в репозиторий манифесты для DEV, миграций и компонентов Model Forge.
- [ ] Проверить полный сценарий Model Forge в DEV через Ingress.
- [ ] Подготовить PROD-манифесты, HTTPS и проверенный перенос данных с Compose.
- [ ] Изменить CI/CD для публикации образов и deploy в нужный кластер.
- [ ] Настроить мониторинг на INFRA.
- [ ] Добавить blue-green и отработать возврат трафика.

Дополняйте этот список по мере выполнения. Готовность инфраструктуры и перенос приложения отмечаются отдельно, чтобы установка K3s не считалась завершённым развёртыванием Model Forge.
