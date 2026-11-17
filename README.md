![Cabecera](../../assets/cabecera_mlops.png)

# Live Review — API calidad del aire + Docker + PostgreSQL

**La API y el agente ya vienen dados** (tools, RAG, historial, API key, rate limit, CORS, timeout).  
**No hay que tocar código de seguridad ni del agente.** El ejercicio es ops: Postgres + Docker + Render.

```text
cliente → /ask?api_key=... → agente (uvicorn o contenedor)
                                    │
                                    ▼
                            PostgreSQL (:5432)
                                    ▲
                               pgAdmin (visor)
```

## Qué tenéis que hacer (entregable)

| # | Qué | Criterio de hecho |
|---|-----|-------------------|
| **1** | Postgres en Docker (`aire-pg`) + pgAdmin | Conectáis a `localhost:5432` |
| **2** | `.env` + API con uvicorn | `/health` → `"storage":"postgres"` |
| **3** | Probar la API | `/ask` sin clave → **401**; con clave → **200**; historial en pgAdmin |
| **4** | Imagen Docker de la API | `docker build` + `docker run` con `--env-file`; mismas pruebas OK |
| **5** | Deploy en **Render** | URL pública: `/health`, 401 sin clave, `/ask` con clave OK |

Orden: **1 → 2 → 3 → 4 → 5**. Detalle de cada paso abajo.

---

## Estructura

```text
.
├── app.py
├── schemas.py
├── config.py          # DATABASE_URL (Postgres), API_KEY, GEMINI, …
├── security.py
├── rate_limit.py
├── gemini_auth.py
├── src/               # agente + SQLModel (dado)
├── data/              # guía + fallback
├── assets/            # imagen_demo.jpg (la pone el autor)
├── Dockerfile
├── .dockerignore
├── requirements.txt
├── .env.example
├── verificar.py
└── README.md
```

---

## 1) PostgreSQL en Docker

Docker Desktop abierto.

```bash
docker run --name aire-pg -e POSTGRES_PASSWORD=123456 -d -p 5432:5432 postgres
```

| Pieza | Significado |
|-------|-------------|
| `--name aire-pg` | Nombre del contenedor |
| `POSTGRES_PASSWORD=123456` | Contraseña del usuario `postgres` |
| `-p 5432:5432` | Acceso desde el PC en `localhost:5432` |
| `-d` | En segundo plano |

Por defecto la BD se llama `postgres`.  
Comprobad: `docker ps` → `aire-pg`.

La password debe coincidir con `DATABASE_URL` en el `.env`.

---

## 2) pgAdmin (visor)

1. Instalad [pgAdmin 4](https://www.pgadmin.org/download/).
2. **Add New Server**.
3. **General**: p. ej. `local-aire`.
4. **Connection**:

| Campo | Valor |
|-------|--------|
| Host name/address | `localhost` |
| Port | `5432` |
| Maintenance database | `postgres` |
| Username | `postgres` |
| Password | `123456` |

5. Save. Deberíais ver la BD `postgres`. Tras unos `/ask`, tablas del historial (`conversation`, `message`).

---

## 3) Arranque de la API (uvicorn en el PC)

Ejecutad **desde esta carpeta** (donde está `app.py`).

```bash
cp .env.example .env
# Completad: GEMINI_API_KEY, API_KEY
# Con uvicorn: usad 127.0.0.1 en DATABASE_URL (descomentad esa línea
# y comentad la de host.docker.internal)

python -m venv .venv
source .venv/bin/activate          # Git Bash / macOS / Linux
# .venv\Scripts\Activate.ps1       # Windows PowerShell

pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

- Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) → `storage: postgres`  
- Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Sin `DATABASE_URL` la app **no arranca**.

Opcional: `python verificar.py` (checks estáticos de Postgres/Docker).

---

## 4) Empaquetar la API en Docker

Postgres sigue en `aire-pg` (`-p 5432:5432`).  
Desde el contenedor de la API, `127.0.0.1` **no** es vuestro PC → usad **`host.docker.internal`** en `DATABASE_URL`:

```text
DATABASE_URL=postgresql://postgres:123456@host.docker.internal:5432/postgres
```

```bash
docker build -t calidad-aire .
docker run --rm --name aire-api -p 8000:8000 --env-file .env calidad-aire
```

| Pieza | Por qué |
|-------|---------|
| `--name aire-api` | Nombre fijo |
| `--env-file .env` | Secretos en runtime (no van en la imagen) |
| `.dockerignore` | Evita meter `.env`, `.venv`, `.git` |

### Cómo leer el Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Comandos útiles

```bash
docker ps
docker stop aire-api
docker start aire-api
docker rm aire-api

docker stop aire-pg
docker start aire-pg

docker images
docker rmi calidad-aire
```

**Nota `--rm`:** al hacer `stop`, el contenedor se borra. Para stop→start, lanzad sin `--rm`.

---

## Rutas

| Método | Ruta | ¿Clave? | Qué hace |
|--------|------|---------|----------|
| GET | `/health` | No | Pulso + `storage: postgres` |
| GET | `/docs` | No | Swagger |
| POST | `/ask` | **Sí** | Un turno; timeout → 504 |
| GET | `/threads/{id}/messages` | **Sí** | Historial en Postgres |

---

## Práctica guiada

Con la API en marcha y Postgres en `aire-pg`. Sustituid `<CLAVE>` por `API_KEY` del `.env`.

### 1) Health

GET [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) → **200** y `"storage":"postgres"`.

### 2) Ask sin clave → 401

POST `http://127.0.0.1:8000/ask` con body:

```json
{
  "pregunta": "Zona centro, contaminante NO2. ¿Cómo lo interpreto?",
  "thread_id": "demo-1",
  "auto_aprobar": true
}
```

### 3) Ask con clave → 200

POST `http://127.0.0.1:8000/ask?api_key=<CLAVE>` con el mismo body → **200**.

### 4) Historial

GET `http://127.0.0.1:8000/threads/demo-1/messages?api_key=<CLAVE>`

### 5) pgAdmin

Tras el `/ask`, filas en `conversation` / `message` (refrescad F5).

### 6) Tras Docker

1. Parad uvicorn (puerto 8000 libre).
2. `.env` con `host.docker.internal`.
3. `docker build` + `docker run` (sección 4).
4. Repetid health / ask / messages.

---

## 5) Render (despliegue en la nube)

1. **New → PostgreSQL** (anotad Internal Database URL).
2. **New → Web Service → Docker** (esta carpeta como raíz).
3. Environment: `API_KEY`, `GEMINI_API_KEY`, `GEMINI_MODEL` (opcional), `ASK_TIMEOUT_SECONDS`, `CORS_ORIGINS`, `DATABASE_URL` (Internal URL del Postgres de Render).
4. `PORT` lo inyecta Render; el Dockerfile ya lo usa.

Nunca subáis `.env` con secretos reales.

En la **URL pública** de Render comprobad lo mismo que en local:

- `GET /health` → 200 y `"storage":"postgres"`
- `POST /ask` sin `api_key` → 401
- `POST /ask?api_key=<CLAVE>` → 200

---

## Checklist

- [ ] **1** Contenedor `aire-pg` + pgAdmin en `localhost:5432`
- [ ] **2** uvicorn: `/health` → `"storage":"postgres"`
- [ ] **3** `/ask` sin clave → 401; con clave → 200; historial en pgAdmin
- [ ] **4** Imagen Docker de la API (mismas pruebas)
- [ ] **5** Render: `/health`, 401 y `/ask` OK en la URL pública
