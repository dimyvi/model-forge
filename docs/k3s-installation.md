# Установка K3s

[Документация проекта](README.md) · [Инфраструктура Kubernetes](kubernetes.md)

ОС: Rocky Linux 9. Версия стенда: K3s `v1.37.1+k3s1`.

Процедура предназначена для первоначальной установки. Состав и статус существующих нод приведены в [описании инфраструктуры](kubernetes.md#виртуальные-машины). Для работающего кластера используется раздел [проверки](#проверка-кластеров).

Официальные инструкции: [Requirements](https://docs.k3s.io/installation/requirements), [Quick Start](https://docs.k3s.io/quick-start), [Configuration Options](https://docs.k3s.io/installation/configuration).

## Подготовка

Ansible подготавливает ОС, пользователя `admin`, SSH и firewall. K3s использует встроенный containerd; отдельная установка Docker на ноды не требуется.

Hostname задаётся до установки K3s и должен быть уникальным. Пример для ВМ 4:

```bash
sudo hostnamectl set-hostname prod-worker1
hostnamectl
```

Остальные имена указаны в [таблице ВМ](kubernetes.md#виртуальные-машины). Переименование зарегистрированной ноды не входит в эту процедуру.

Подключение по настроенному SSH alias:

```bash
ssh vm3-prod-control
```

При подключении по IP указывается настроенный порт, например `ssh -p 8228 admin@192.168.1.226`.

### Сеть и firewall

Для PROD с Flannel VXLAN используются следующие правила:

| Порт | Назначение | Получатель | Источник |
| --- | --- | --- | --- |
| TCP 6443 | API и регистрация agents | ВМ 3 | ВМ 4/5, компьютер администратора |
| UDP 8472 | Межнодовая сеть | ВМ 3/4/5 | Другие ноды PROD |
| TCP 10250 | Kubelet и метрики | ВМ 3/4/5 | Другие ноды PROD |

UDP 8472 доступен только внутри кластера. DEV использует отдельные правила доступа к своему Server.

В firewalld также учитывается трафик Pod и Service: стандартные сети K3s — `10.42.0.0/16` и `10.43.0.0/16`. Правила должны разрешать связь Pod между worker-нодами. Полный список требований: [настройки ОС](https://docs.k3s.io/installation/requirements#operating-systems), [Networking / Inbound Rules](https://docs.k3s.io/installation/requirements#networking).

Доступ на 80/443 настраивается после выбора точки входа Traefik.

## DEV Server

Установка на ВМ 2 (`192.168.1.193`):

```bash
curl -4 -sfL https://get.k3s.io | \
sudo env INSTALL_K3S_VERSION="v1.37.1+k3s1" sh -s - server
```

`INSTALL_K3S_VERSION` фиксирует версию и исключает запрос к `update.k3s.io` для её определения. Установщик и release assets загружаются из сети: [Configuration Options](https://docs.k3s.io/installation/configuration).

Проверка:

```bash
sudo systemctl is-active k3s
sudo /usr/local/bin/k3s kubectl get nodes -o wide
```

Ожидаемый результат: служба `active`, нода `dev-server` в состоянии `Ready`. На ней работают control plane и приложения DEV.

## PROD Server

На ВМ 3 (`192.168.1.226`) выполняется та же команда установки Server. Создаётся отдельный PROD-кластер.

Токен подключения agents:

```bash
sudo cat /var/lib/rancher/k3s/server/node-token
```

Токен передаётся полностью, включая префикс и хеш CA. Для PROD используется токен его Server. Токены хранятся вне репозитория; порядок замены описан в [K3s Token](https://docs.k3s.io/cli/token).

## PROD Agents

Процедура выполняется отдельно на ВМ 4 (`192.168.1.234`) и ВМ 5 (`192.168.1.138`). На них устанавливается только Agent.

Ввод токена PROD и установка:

```bash
read -rsp 'Токен PROD: ' PROD_K3S_TOKEN
printf '\n'

curl -4 -sfL https://get.k3s.io | \
sudo env \
INSTALL_K3S_VERSION="v1.37.1+k3s1" \
K3S_URL="https://192.168.1.226:6443" \
K3S_TOKEN="$PROD_K3S_TOKEN" \
sh -s - agent

unset PROD_K3S_TOKEN
```

Скрытый ввод не сохраняет значение токена в истории команд. Установщик записывает параметры подключения в конфигурацию службы. Описание параметров: [Quick Start](https://docs.k3s.io/quick-start).

Проверка на каждой worker-ноде:

```bash
sudo systemctl is-active k3s-agent
sudo journalctl -u k3s-agent -n 30 --no-pager
```

Ожидаемое состояние — `active`. Причина незавершённого запуска (`activating`) выводится в журнале службы.

## Проверка кластеров

На Server нужного кластера — ВМ 2 для DEV или ВМ 3 для PROD:

```bash
sudo /usr/local/bin/k3s kubectl get nodes -o wide
sudo /usr/local/bin/k3s kubectl get pods -A -o wide
sudo /usr/local/bin/k3s kubectl get events -A --sort-by=.metadata.creationTimestamp
```

Ожидаемый список PROD:

```text
prod-control   Ready   control-plane
prod-worker1   Ready   <none>
prod-worker2   Ready   <none>
```

В DEV отображается только `dev-server`. Системные Pod должны быть готовы и иметь статус `Running`; завершённые установочные Jobs — `Completed`.

Подробности ноды и Pod:

```bash
sudo /usr/local/bin/k3s kubectl describe node prod-worker1
```

Для Pod используются `kubectl describe pod <имя> -n <namespace>` и `kubectl logs <имя> -n <namespace>` с тем же префиксом `sudo /usr/local/bin/k3s`.

## Доступ через kubectl

Системный kubeconfig находится в `/etc/rancher/k3s/k3s.yaml`. Команда с sudo использует его напрямую:

```bash
sudo /usr/local/bin/k3s kubectl get nodes
```

Для работы от `admin` на Server доступна личная копия kubeconfig. Следующие команды предназначены для случая, когда `~/.kube/config` ещё не создан; существующий файл сохраняется отдельно перед заменой.

```bash
mkdir -p "$HOME/.kube"
chmod 700 "$HOME/.kube"
sudo install -o "$(id -u)" -g "$(id -g)" -m 600 \
  /etc/rancher/k3s/k3s.yaml "$HOME/.kube/config"
export KUBECONFIG="$HOME/.kube/config"
/usr/local/bin/kubectl get nodes
```

Для последующих сеансов в `~/.bashrc` добавляется строка `export KUBECONFIG="$HOME/.kube/config"`. Kubectl из поставки K3s по умолчанию читает системный файл, поэтому путь к личной копии задаётся явно.

Kubeconfig предоставляет административный доступ; права файла — `600`. K3s обновляет сертификаты в системном файле, личные копии обновляются отдельно: [Cluster Access](https://docs.k3s.io/cluster-access).

## Диагностика

| Ошибка | Проверка |
| --- | --- |
| Сброс соединения с `update.k3s.io` | Фиксация `INSTALL_K3S_VERSION`, доступ к GitHub и release assets |
| `sudo: k3s: command not found` | Полный путь `/usr/local/bin/k3s` вместо имени команды |
| Нет прав на `/etc/rancher/k3s/k3s.yaml` | Sudo или личный kubeconfig с явно заданным `KUBECONFIG` |
| `127.0.0.1:6444: address already in use` | Процесс, занявший порт; одновременный запуск Server и Agent |
| `not authorized` | Полный токен PROD, параметры Agent, журнал Server и регистрация ноды |
| Ожидание на `Starting k3s-agent` | Статус и журнал службы в другом SSH-сеансе |

Команды на worker-ноде:

```bash
sudo systemctl status k3s-agent --no-pager -l
sudo journalctl -u k3s-agent -n 80 --no-pager
sudo systemctl status k3s --no-pager -l
sudo ss -ltnp
```

Наличие `k3s.service` на worker может указывать на ошибочную установку Server. Перед его удалением требуется проверить локальные данные. Скрипт uninstall удаляет данные K3s: [Uninstalling K3s](https://docs.k3s.io/installation/uninstall).
