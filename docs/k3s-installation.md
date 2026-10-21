# Установка и проверка K3s

[К документации проекта](README.md) · [Архитектура и что читать](kubernetes.md)

Инструкция для Rocky Linux 9 и нашего стенда из пяти ВМ. По ручной проверке 22 октября 2026 года DEV и все три PROD-ноды уже были `Ready`. На работающих нодах начните с [проверки](#проверка-кластеров); повторная установка для проверки не нужна.

Основа: [Requirements](https://docs.k3s.io/installation/requirements), [Quick Start](https://docs.k3s.io/quick-start), [Configuration Options](https://docs.k3s.io/installation/configuration).

## 1. Подготовить ВМ

У каждой ноды должно быть уникальное hostname. Проверить его можно командой `hostnamectl`. Менять имя лучше до установки K3s; если нода уже зарегистрирована, не переименовывайте её в рамках обычной проверки.

| ВМ | IP | Имя Linux | Установка |
| --- | --- | --- | --- |
| 1 | `192.168.1.218` | `infra` | K3s не требуется |
| 2 | `192.168.1.193` | `dev-server` | Server отдельного DEV-кластера |
| 3 | `192.168.1.226` | `prod-control` | Server PROD-кластера |
| 4 | `192.168.1.234` | `prod-worker1` | Agent PROD |
| 5 | `192.168.1.138` | `prod-worker2` | Agent PROD |

Например, до первой установки на ВМ 4:

```bash
sudo hostnamectl set-hostname prod-worker1
```

Перезагрузка только ради изменения hostname обычно не нужна. SSH-подключение используйте уже настроенное: например, `ssh vm3-prod-control`, либо `ssh -p 8228 admin@192.168.1.226`, если после подготовки SSH работает на порту 8228.

Ansible подготавливает пользователя, SSH, ОС и firewall. K3s включает собственный containerd; отдельно ставить Docker для Kubernetes не требуется. Требования ОС проверяйте по [Requirements](https://docs.k3s.io/installation/requirements#operating-systems).

### Сеть и firewall

Для нашего PROD с обычным Flannel VXLAN:

| Назначение | Куда разрешить | Откуда |
| --- | --- | --- |
| TCP 6443: API и регистрация | ВМ 3 | ВМ 4/5 и доверенный компьютер администратора |
| UDP 8472: межнодовая сеть | ВМ 3/4/5 | Только другие ноды этого PROD-кластера |
| TCP 10250: kubelet/метрики | ВМ 3/4/5 | Другие ноды этого PROD-кластера |

DEV имеет отдельные правила для своего Server и административного доступа. Не открывайте UDP 8472 в интернет. Для firewalld также нужно учесть трафик Pod и Service: по умолчанию используются `10.42.0.0/16` и `10.43.0.0/16`. Трёх правил портов недостаточно для любой конфигурации firewall. Официальные разделы: [Firewalld](https://docs.k3s.io/installation/requirements#operating-systems) и [Networking / Inbound Rules](https://docs.k3s.io/installation/requirements#networking).

Настройку доступа к сайту на 80/443 выполняйте отдельно после выбора точки входа Traefik. Если сохраняете firewalld, проверьте не только `Ready` нод, но и связь Pod между workers.

## 2. Установить DEV Server

Только на ВМ 2, при первой установке:

```bash
curl -4 -sfL https://get.k3s.io | \
sudo env INSTALL_K3S_VERSION="v1.37.1+k3s1" sh -s - server
```

Это версия, установленная на нашем стенде; это не рекомендация обновляться до неё без проверки. Явный `INSTALL_K3S_VERSION` позволяет не обращаться к `update.k3s.io` для определения версии. Загрузка установщика и файлов с GitHub всё равно требует сети. Документация: [Configuration Options](https://docs.k3s.io/installation/configuration).

```bash
sudo systemctl is-active k3s
sudo /usr/local/bin/k3s kubectl get nodes -o wide
```

Ожидается `active` и одна нода `dev-server` со статусом `Ready`. Она и управляет DEV, и запускает его приложения.

## 3. Установить PROD Server

Только на ВМ 3 выполните ту же команду установки Server из предыдущего шага. Она создаст отдельный PROD-кластер.

Получите токен на ВМ 3:

```bash
sudo cat /var/lib/rancher/k3s/server/node-token
```

Он понадобится только для подключения PROD agents. Скопируйте полную строку без изменения. Токен DEV здесь не подходит. Не отправляйте токен в чат и не сохраняйте в Git. Для уже раскрытого токена запланируйте замену по [документации токенов K3s](https://docs.k3s.io/cli/token).

## 4. Подключить PROD workers

На ВМ 4 и затем отдельно на ВМ 5 используйте следующую команду. Она явно устанавливает **Agent**, который подключается к ВМ 3. Сначала введите полный актуальный токен PROD через скрытый ввод Bash:

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

Токен не записывается как литерал в историю команд; установщик сохраняет нужные настройки службы на ноде. Перед выполнением agent-команды на worker не нужно устанавливать Server. Параметры подключения: [Quick Start](https://docs.k3s.io/quick-start).

Проверка на каждой worker-ВМ:

```bash
sudo systemctl is-active k3s-agent
sudo journalctl -u k3s-agent -n 30 --no-pager
```

Ожидается `active`. `activating` означает, что запуск ещё не завершился; причину ожидания смотрите в журнале.

## Проверка кластеров

На ВМ 2 команды показывают только DEV:

```bash
sudo /usr/local/bin/k3s kubectl get nodes -o wide
sudo /usr/local/bin/k3s kubectl get pods -A -o wide
```

На ВМ 3 те же команды показывают PROD. В списке нод должны быть:

```text
prod-control   Ready   control-plane
prod-worker1   Ready   <none>
prod-worker2   Ready   <none>
```

Системные Pod должны быть `Running`/готовы; завершённые установочные Jobs могут иметь статус `Completed`. События кластера:

```bash
sudo /usr/local/bin/k3s kubectl get events -A --sort-by=.metadata.creationTimestamp
```

Для ноды с ошибкой используйте `kubectl describe node <имя>`, для Pod — `kubectl describe pod <имя> -n <namespace>` и `kubectl logs <имя> -n <namespace>`. Эти команды дописываются после `sudo /usr/local/bin/k3s`.

## Kubectl без sudo на Server

Разовая команда с полным путём работает даже тогда, когда `sudo` не находит `k3s` в PATH:

```bash
sudo /usr/local/bin/k3s kubectl get nodes
```

Для повседневной работы от `admin` на ВМ 2 или ВМ 3 можно использовать личную копию kubeconfig. Если `~/.kube/config` уже существует, сохраните его и сначала разберитесь, к какому кластеру он относится.

При отсутствии личного kubeconfig:

```bash
mkdir -p "$HOME/.kube"
chmod 700 "$HOME/.kube"
sudo install -o "$(id -u)" -g "$(id -g)" -m 600 \
  /etc/rancher/k3s/k3s.yaml "$HOME/.kube/config"
export KUBECONFIG="$HOME/.kube/config"
/usr/local/bin/kubectl get nodes
```

Чтобы сохранить выбор файла после входа, добавьте один раз в `~/.bashrc` строку `export KUBECONFIG="$HOME/.kube/config"`. Это нужно явно указать для kubectl, который поставляется с K3s: по умолчанию он читает системный файл. Ошибка `permission denied` не доказывает, что переменная уже была задана.

В пользовательском PATH у нас `/usr/local/bin` уже доступен. Менять `sudo PATH` или создавать ссылку в `/usr/bin` для этих команд не требуется. Копия kubeconfig даёт административные права; права `600` сохраняйте. K3s обновляет сертификаты в системном kubeconfig, а личные копии нужно обновлять отдельно: [Cluster Access](https://docs.k3s.io/cluster-access).

## Если установка или запуск не проходят

| Сообщение | Что проверить |
| --- | --- |
| Сброс соединения с `update.k3s.io` | Использовать конкретный `INSTALL_K3S_VERSION`; отдельно проверить доступ к GitHub и release assets |
| `sudo: k3s: command not found` | Запустить `/usr/local/bin/k3s` полным путём |
| Нет прав на `/etc/rancher/k3s/k3s.yaml` | Использовать sudo или явно указать личный `KUBECONFIG` |
| `127.0.0.1:6444: address already in use` | Найти процесс через `sudo ss -ltnp`; проверить, не запущен ли Server вместе с Agent |
| `not authorized` | Проверить полный актуальный токен именно PROD и настройки Agent; если токен верен — журнал Server и регистрацию ноды |
| Ожидание на `Starting k3s-agent` | В другом SSH-сеансе посмотреть состояние службы и журнал |

Команды на worker с проблемой:

```bash
sudo systemctl status k3s-agent --no-pager -l
sudo journalctl -u k3s-agent -n 80 --no-pager
sudo systemctl status k3s --no-pager -l
sudo ss -ltnp
```

Наличие `k3s.service` на worker может означать случайную установку Server. Перед удалением выясните, какие данные он хранит. Скрипт uninstall удаляет локальные данные K3s и не является обычной командой диагностики. Порядок и последствия описаны в [Uninstalling K3s](https://docs.k3s.io/installation/uninstall).

После проверки инфраструктуры продолжайте по [плану переноса Model Forge](kubernetes.md#порядок-переноса-model-forge). Устанавливать Redis, Celery, MinIO или второй Traefik для проверки нод не требуется.
