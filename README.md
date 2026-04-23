# KarIA Reach

Plataforma de prospección outbound: busca contactos con IA, Apollo, Perplexity, Google Maps, Instagram y Scraping Web; redacta emails personalizados con Claude; envía campañas vía Gmail OAuth; lee respuestas y gestiona usuarios con roles.

## Stack

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Backend | FastAPI + Uvicorn | 0.115.6 / 0.34.0 |
| Backend | asyncpg (PostgreSQL) | 0.30.0 |
| Backend | Anthropic SDK | 0.49.0 |
| Backend | APScheduler | 3.10.4 |
| Backend | slowapi (rate limiting) | 0.1.9 |
| Backend | bcrypt / PyJWT / cryptography | 4.1.3 / 2.9.0 / 44.0.0 |
| Backend | BeautifulSoup4 / bleach | 4.12.3 / 6.2.0 |
| Frontend | React + Vite | 18.3.1 / 6.4.1 |
| Frontend | react-router-dom | 7.13.2 |
| Frontend | axios / dompurify / exceljs | 1.14.0 / 3.3.3 / ^4.4.0 |
| Base de datos | PostgreSQL | 14+ |

## Arquitectura

```
Karia-Reach-Phyton/
├── backend/
│   ├── routes/          # Validación Pydantic, decoradores de rate limit
│   ├── controllers/     # Orquestación, sin lógica de negocio
│   ├── services/        # Lógica de negocio (IA, OAuth, schedulers)
│   ├── repositories/    # Queries asyncpg parametrizadas
│   ├── integrations/    # Clientes externos (Gmail, Apify, Apollo, Perplexity)
│   ├── middleware/      # auth, error_handler, rate_limiter, security_headers
│   ├── migrations/      # 7 archivos SQL numerados (000–006)
│   ├── utils/           # db.py (pool, METODOS_BUSQUEDA_VALIDOS), helpers
│   └── main.py          # FastAPI app, routers, lifespan
└── frontend/
    └── src/
        ├── pages/       # BuscarContactos, Redactar, Enviar, Respuestas...
        ├── components/  # UI/, Layout/
        ├── context/     # AuthContext, ToastContext
        ├── constants/   # api.js — todos los endpoints centralizados
        └── hooks/       # useApi (axios con interceptores JWT)
```

## Requisitos

- Python 3.11+
- Node 18+
- PostgreSQL 14+
- API key de Anthropic (obligatoria)
- Cuenta de Google Cloud con Gmail API habilitada (para OAuth por usuario)

## Instalación

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # completar variables (ver sección Variables)

# Frontend
cd ../frontend
npm install
```

## Migraciones

```bash
createdb karia_reach
psql -d karia_reach -f backend/migrations/000_migration_tracker.sql
psql -d karia_reach -f backend/migrations/001_initial_schema.sql
psql -d karia_reach -f backend/migrations/002_gmail_integrations.sql
psql -d karia_reach -f backend/migrations/003_contact_source_scraping.sql
psql -d karia_reach -f backend/migrations/004_campanas_constraints.sql
psql -d karia_reach -f backend/migrations/005_metodos_habilitados.sql
psql -d karia_reach -f backend/migrations/006_campanas_programadas.sql
```

## Primer superadmin

Generar el hash bcrypt e insertar directamente en PostgreSQL:

```python
import bcrypt
print(bcrypt.hashpw(b"tupassword", bcrypt.gensalt()).decode())
```

```sql
INSERT INTO usuarios (email, password_hash, nombre, rol)
VALUES ('admin@tudominio.com', '$2b$12$...hash_generado...', 'Admin', 'superadmin');
```

## Cómo correr

```bash
# Backend (desde /backend, con .venv activo)
uvicorn main:app --reload --port 3001

# Frontend (desde /frontend)
npm run dev
```

- Backend: http://localhost:3001
- Frontend: http://localhost:5173
- Docs interactivas: http://localhost:3001/docs

## Funcionalidades

- **Búsqueda de contactos** con 7 métodos configurables por usuario desde el panel admin
- **Redacción con IA** — variantes de email (tono, objetivo), personalización por contacto, formato de texto natural a HTML
- **Campañas** — envío inmediato o programado vía Gmail con pixel de tracking de apertura
- **Respuestas** — sincronización de replies desde Gmail, respuesta asistida por IA
- **Bloques** — agrupación de contactos para campañas segmentadas
- **Templates** — guardado y reutilización de emails
- **Gmail OAuth** — cada usuario conecta su propia cuenta Gmail
- **Admin** — gestión de usuarios, roles (`user` / `superadmin`) y métodos habilitados por usuario
- **Enriquecimiento** — actualización de datos de contactos existentes vía IA, Apollo o Apify

## Métodos de búsqueda

| Método | Clave | Fuente | API key requerida |
|--------|-------|--------|------------------|
| Claude (IA) | `claude_ai` | Anthropic + web search | `ANTHROPIC_API_KEY` en `.env` |
| Apollo.io | `apollo` | Apollo REST API | por usuario en BD (Fernet) |
| Perplexity | `perplexity` | Perplexity API | por usuario en BD (Fernet) |
| Google Maps | `google_maps` | Apify — actor Google Maps | por usuario en BD (Fernet) |
| Instagram | `instagram` | Apify — followers + likers + profiles | por usuario en BD (Fernet) |
| Scraping Web | `scraping_web` | BeautifulSoup4 + protección SSRF | ninguna |
| Carga Manual | `carga_manual` | Formulario en frontend | ninguna |

Los métodos válidos están definidos en `utils/db.py → METODOS_BUSQUEDA_VALIDOS` (fuente única de verdad).

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `PORT` | Puerto del servidor (`3001`) |
| `BASE_URL` | URL pública del backend |
| `ALLOWED_ORIGINS` | CORS origins (ej: `http://localhost:5173`) |
| `ANTHROPIC_API_KEY` | API key de Claude |
| `ANTHROPIC_MODEL` | Modelo (ej: `claude-sonnet-4-20250514`) |
| `GMAIL_CLIENT_ID` | OAuth Google — Client ID |
| `GMAIL_CLIENT_SECRET` | OAuth Google — Client Secret |
| `GMAIL_OAUTH_REDIRECT_URI` | Callback OAuth (`/api/gmail/oauth/callback`) |
| `SECRET_KEY` | HMAC-SHA256 para tokens de tracking |
| `JWT_SECRET` | Firma de JWT |
| `JWT_EXPIRATION_HOURS` | Duración del token (`8`) |
| `ENCRYPTION_KEY` | Fernet key para cifrar tokens OAuth en BD |
| `PG_HOST / PG_PORT / PG_USER / PG_PASSWORD / PG_DATABASE` | Conexión PostgreSQL |
| `PG_POOL_MIN_SIZE / PG_POOL_MAX_SIZE` | Pool asyncpg (`2` / `10`) |
| `RATE_LIMIT_GENERAL / COMPOSE / SEND` | Rate limits (`120/minute`, etc.) |

Generar `ENCRYPTION_KEY`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## API Endpoints

Todos los endpoints excepto `/api/auth/login` y `/api/gmail/oauth/callback` requieren `Authorization: Bearer <jwt>`.

| Módulo | Método | Ruta | Descripción |
|--------|--------|------|-------------|
| Auth | POST | `/api/auth/login` | Login, retorna JWT |
| Contacts | GET | `/api/contacts` | Listar contactos |
| | POST | `/api/contacts/search-ai` | Búsqueda con IA |
| | POST | `/api/contacts/save-selection` | Guardar selección (max 50) |
| | POST | `/api/contacts/manual` | Agregar contacto manual |
| | POST | `/api/contacts/{id}/enrich` | Enriquecer contacto existente |
| | DELETE | `/api/contacts/{id}` | Eliminar contacto |
| Compose | POST | `/api/compose/generate` | Generar variantes de email con IA |
| | POST | `/api/compose/generate-from-contacts` | Email personalizado por contacto |
| | POST | `/api/compose/format-manual` | Formatear texto natural a HTML |
| | GET / POST | `/api/compose/templates` | Listar / Crear template |
| | DELETE | `/api/compose/templates/{id}` | Eliminar template |
| Send | POST | `/api/send/campaign` | Crear y enviar campaña |
| | GET | `/api/send/campaigns` | Listar campañas |
| | GET | `/api/send/campaigns/{id}/stats` | Stats de una campaña |
| | GET | `/api/send/stats` | Stats globales |
| | GET | `/api/send/dashboard` | Dashboard de totales |
| Gmail | GET | `/api/gmail/status` | Estado de conexión Gmail |
| | GET | `/api/gmail/oauth/authorize` | Genera URL de autorización Google |
| | GET | `/api/gmail/oauth/callback` | Callback OAuth (público) |
| | POST | `/api/gmail/disconnect` | Desconectar Gmail |
| Replies | GET | `/api/replies/{campaign_id}` | Respuestas de una campaña |
| | POST | `/api/replies/{campaign_id}/sync` | Sincronizar desde Gmail |
| | POST | `/api/replies/{reply_id}/respond` | Responder con IA |
| | PATCH | `/api/replies/{reply_id}/read` | Marcar como leída |
| Bloques | GET / POST | `/api/bloques` | Listar / Crear bloque |
| | PUT / DELETE | `/api/bloques/{id}` | Editar / Eliminar bloque |
| | GET / POST | `/api/bloques/{id}/contactos` | Ver / Agregar contactos |
| | DELETE | `/api/bloques/{id}/contactos/{cid}` | Quitar contacto del bloque |
| Apify | GET / POST | `/api/apify/status` · `/api/apify/config` | Estado y configuración |
| | POST | `/api/apify/buscar` | Búsqueda Google Maps |
| | POST | `/api/apify/instagram/buscar` | Búsqueda Instagram |
| | POST | `/api/apify/enriquecer-contacto` | Enriquecer contacto con Apify |
| Apollo | GET / POST | `/api/apollo/status` · `/api/apollo/config` | Estado y configuración |
| | POST | `/api/apollo/search` | Búsqueda Apollo |
| Perplexity | GET / POST | `/api/perplexity/status` · `/api/perplexity/config` | Estado y configuración |
| | POST | `/api/perplexity/search` | Búsqueda Perplexity |
| Scraping | POST | `/api/scraping/buscar` | Búsqueda por scraping |
| | GET / POST | `/api/scraping/preferencias` | Preferencias de scraping |
| Admin | GET / POST | `/api/admin/usuarios` | Listar / Crear usuarios |
| | GET / PATCH / DELETE | `/api/admin/usuarios/{id}` | Ver / Editar / Eliminar usuario |
| | GET | `/api/admin/usuarios/{id}/metodos` | Métodos habilitados del usuario |
| Programadas | GET | `/api/campanas-programadas` | Campañas programadas pendientes |
| | DELETE | `/api/campanas-programadas/{id}` | Cancelar campaña programada |

## Seguridad

- **JWT** firmado con `PyJWT` + `JWT_SECRET`; expiración configurable vía `JWT_EXPIRATION_HOURS`
- **Contraseñas** hasheadas con bcrypt costo 12; `max_length=72` en el field para evitar DoS por hash digest
- **Tokens OAuth y API keys** cifrados con Fernet (AES-128-CBC) antes de persistir en BD
- **Rate limiting** con slowapi: login 5/15min; búsqueda IA y compose 10/min; send 5/min
- **SSRF** bloqueado en scraping: chequeo explícito de `169.254.169.254` + validación `ipaddress` para rangos privados/reservados
- **CORS** restringido a `ALLOWED_ORIGINS`; headers CSP, X-Frame-Options, HSTS y X-Content-Type-Options en cada respuesta
- **Queries** 100% parametrizadas con asyncpg (`$1`, `$2`); nombres de columna en whitelist de frozenset
- **Inputs** validados con Pydantic v2 en todas las rutas; `bleach` sanitiza HTML en replies
