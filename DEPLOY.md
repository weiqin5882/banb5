# Linux 部署说明

## 1. 环境准备

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

## 2. 部署应用

```bash
cd /workspace/banb5
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 3. Systemd（可选）

`/etc/systemd/system/order-reconcile.service`

```ini
[Unit]
Description=Order Reconciliation Web App
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/workspace/banb5
ExecStart=/workspace/banb5/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now order-reconcile
sudo systemctl status order-reconcile
```
