# Docker 部署说明

本项目可以通过 Docker Compose 启动 FastAPI 后端和 Web Debug 调试台。

## 前置条件

- 已安装 Docker Desktop，或已安装支持 Compose 的 Docker Engine。
- 已准备后端环境变量文件：`backend/.env`。

从公开模板复制环境变量文件：

```powershell
Copy-Item .env.example backend\.env
```

然后在 `backend/.env` 中填写 Doubao / Ark 相关 key。

## 启动服务

构建并启动后端和 Web Debug：

```powershell
docker compose up --build
```

启动后访问：

- Web Debug：`http://127.0.0.1:8080`
- 后端 API：`http://127.0.0.1:8000`
- 后端健康检查：`http://127.0.0.1:8000/health`
- Swagger 文档：`http://127.0.0.1:8000/docs`

停止服务：

```powershell
docker compose down
```

## 运行数据

Compose 使用命名数据卷保存运行数据：

- `backend-data`：保存 SQLite、Chroma、上传文件和导入后的商品图片。
- `model-cache`：预留给 Hugging Face 模型缓存，挂载到容器内的 `/models`。

执行 `docker compose down` 后，数据卷仍会保留。

如果要删除运行数据并从零开始：

```powershell
docker compose down -v
```

## 新电脑首次初始化

镜像中包含已提交到仓库的商品目录模板和样例图片，但生成后的 SQLite 与 Chroma 运行文件保存在 `backend-data` 数据卷中。

导入样例商品：

```powershell
docker compose run --rm backend python -m app.scripts.import_catalog app/data/catalog/sample_products.csv --image-root app/data/catalog/images
```

重建索引：

```powershell
docker compose run --rm backend python -m app.scripts.rebuild_indexes
```

Docker Compose 默认使用确定性的本地 fallback embedding，因此新电脑没有 Hugging Face 模型文件时也可以运行：

```env
BGE_M3_ENABLE_REAL=false
CHINESE_CLIP_ENABLE_REAL=false
CHINESE_CLIP_LOCAL_FILES_ONLY=false
HF_HUB_OFFLINE=0
TRANSFORMERS_OFFLINE=0
```

这些值已经在 `docker-compose.yml` 中设置，Docker 运行时会覆盖 `backend/.env` 中的同名配置。如果后续想在 Docker 中使用真实本地 embedding 模型，需要移除这些覆盖项，在 `backend/Dockerfile` 中加入所需模型依赖，并把 Hugging Face 缓存挂载或复制到 `model-cache` 数据卷。

## 查看日志

查看实时日志：

```powershell
docker compose logs -f
```

只查看后端日志：

```powershell
docker compose logs -f backend
```

## Android 访问地址

Android 模拟器访问电脑上的 Docker 后端：

```text
http://10.0.2.2:8000
```

同一局域网内的 Android 真机访问电脑后端：

```text
http://<电脑局域网 IP>:8000
```

## 注意事项

- 本地构建镜像通常不需要登录 Docker 账号，除非当前网络环境需要认证拉取基础镜像。
- `backend/.env` 包含本地密钥，故意不提交到 Git。
- Web Debug 容器会把 `/api`、`/static`、`/docs`、`/openapi.json` 和 `/health` 代理到后端容器。
