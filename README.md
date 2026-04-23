# KarIA Reach

Plataforma de outreach comercial B2B potenciada por IA.

## Requisitos
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Cuenta Google Cloud con OAuth2 configurado
- API key de Anthropic

## Instalación

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env      # Completar con credenciales reales
```

### Frontend
```bash
cd frontend
npm install
```

## Migraciones de base de datos
Ejecutar como superusuario PostgreSQL en orden. **Correr `000` primero, una sola vez** — crea la tabla de control de migraciones y registra las ya aplicadas:
```bash
psql -U postgres -d karia_reach -f backend/migrations/000_migration_tracker.sql
psql -U postgres -d karia_reach -f backend/migrations/001_initial_schema.sql
psql -U postgres -d karia_reach -f backend/migrations/002_gmail_integrations.sql
psql -U postgres -d karia_reach -f backend/migrations/003_contact_source_scraping.sql
psql -U postgres -d karia_reach -f backend/migrations/004_campanas_constraints.sql
psql -U postgres -d karia_reach -f backend/migrations/005_metodos_habilitados.sql
```

## Cómo correr

### Backend (puerto 3001)
```bash
cd backend
.\venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 3001 --reload
```

### Frontend (puerto 5173)
```bash
cd frontend
npm run dev
```

> Vite hace proxy de /api y /track hacia http://localhost:3001 automáticamente.

## Variables de entorno
Ver `backend/.env.example` para la lista completa de variables requeridas.

---

**Plataforma de outreach comercial B2B potenciada por inteligencia artificial.**

KarIA Reach automatiza el ciclo completo de prospección comercial: buscar contactos con IA, componer emails personalizados, enviar campañas masivas, trackear aperturas con pixel tracking y gestionar respuestas — todo desde una interfaz unificada.

Diseñada para equipos de ventas y growth que necesitan escalar su alcance sin perder personalización.

---

## Stack Tecnológico

### Backend (Python)
| Tecnología | Versión | Uso |
|---|---|---|
| FastAPI | 0.115.6 | Framework web async |
| Uvicorn | 0.34.0 | Servidor ASGI |
| asyncpg | 0.30.0 | Cliente PostgreSQL async |
| Anthropic | 0.42.0 | Claude AI (búsqueda y composición) |
| Google API Client | 2.159.0 | Gmail API (envío y lectura) |
| PyJWT | 2.9.0 | Autenticación JWT |
| bcrypt | 4.1.3 | Hashing de contraseñas |
| cryptography | 44.0.0 | Encriptación Fernet (API keys) |
| httpx | 0.28.1 | Cliente HTTP async (Apollo) |
| slowapi | 0.1.9 | Rate limiting por IP |
| bleach | 6.2.0 | Sanitización HTML |
| pydantic-settings | 2.7.1 | Configuración con validación |

### Frontend (React)
| Tecnología | Versión | Uso |
|---|---|---|
| React | 18.3.1 | UI library |
| React Router | 7.13.2 | Routing SPA |
| Vite | 6.4.1 | Build tool y dev server |
| Axios | 1.14.0 | Cliente HTTP |
| ExcelJS | 4.4.0 | Exportación a Excel |

---

## Arquitectura

```
Reach-Phyton/
├── backend/
│   ├── main.py                    # Entry point FastAPI, middleware, lifespan
│   ├── scheduler.py               # APScheduler — polling de respuestas Gmail
│   ├── logger.py                  # Logging centralizado (color dev, JSON prod)
│   ├── config/
│   │   └── settings.py            # Variables de entorno con Pydantic
│   ├── routes/                    # Definición de endpoints y validación
│   │   ├── auth.py
│   │   ├── contacts.py
│   │   ├── compose.py
│   │   ├── send.py
│   │   ├── replies.py
│   │   ├── apollo.py
│   │   └── tracking.py
│   ├── controllers/               # Adaptadores HTTP (sin lógica de negocio)
│   │   ├── auth_controller.py
│   │   ├── contacts_controller.py
│   │   ├── compose_controller.py
│   │   ├── send_controller.py
│   │   ├── replies_controller.py
│   │   └── apollo_controller.py
│   ├── services/                  # Lógica de negocio
│   │   ├── auth_service.py
│   │   ├── contacts_service.py
│   │   ├── compose_service.py
│   │   ├── send_service.py
│   │   ├── replies_service.py
│   │   ├── apollo_service.py
│   │   ├── email_builder_service.py
│   │   ├── enrichment_service.py
│   │   ├── gmail_oauth_service.py
│   │   └── gmail_credentials_service.py
│   ├── repositories/              # Acceso a datos (PostgreSQL)
│   │   ├── auth_repository.py
│   │   ├── contacts_repository.py
│   │   ├── campaigns_repository.py
│   │   ├── templates_repository.py
│   │   ├── replies_repository.py
│   │   ├── integrations_repository.py
│   │   └── tracking_repository.py
│   ├── integrations/              # Clientes de servicios externos
│   │   ├── claude_client.py
│   │   ├── gmail_client.py
│   │   ├── gmail_send_client.py
│   │   ├── gmail_reader_client.py
│   │   ├── gmail_oauth_flow.py
│   │   ├── apollo_client.py
│   │   ├── apollo_search_client.py
│   │   └── apollo_enrich_client.py
│   ├── middleware/                 # Auth, rate limiting, error handling
│   │   ├── auth.py
│   │   ├── rate_limiter.py
│   │   └── error_handler.py
│   └── utils/
│       └── security.py            # HMAC-SHA256 para tracking tokens
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx               # Entry point React
│   │   ├── App.jsx                # Router y layout principal
│   │   ├── pages/                 # Páginas de la aplicación
│   │   │   ├── Login.jsx
│   │   │   ├── BuscarContactos.jsx
│   │   │   ├── ComponerEmails.jsx
│   │   │   ├── EnviarCampana.jsx
│   │   │   ├── Historial.jsx
│   │   │   ├── Estadisticas.jsx
│   │   │   ├── Respuestas.jsx
│   │   │   └── Configuracion.jsx
│   │   ├── components/
│   │   │   ├── Layout/            # Header, Sidebar
│   │   │   └── UI/                # Button, Modal, Table, Badge, Toast, etc.
│   │   ├── context/               # AuthContext, ToastContext
│   │   ├── hooks/                 # useApi (Axios con interceptors)
│   │   ├── constants/             # Endpoints centralizados
│   │   ├── utils/                 # Exportación Excel
│   │   └── styles/                # Variables CSS, estilos globales
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
```

**Patrón arquitectónico:** Routes → Controllers → Services → Repositories (capas desacopladas, cada una con responsabilidad única).

---

## Funcionalidades

### 1. Buscar Contactos
- **Búsqueda con IA** — Claude busca en la web por industria y ubicación, devolviendo nombre, empresa, cargo, emails y teléfonos con un índice de confianza (0-1).
- **Búsqueda con Apollo.io** — Integración opcional para buscar contactos en la base de Apollo.
- **Carga manual** — Agregar contactos uno a uno.
- **Guardado selectivo** — Elegir qué contactos guardar con checkboxes. Prevención de duplicados por email.

### 2. Componer Emails
- **Generación de variantes** — Claude genera 1-5 variantes de email según descripción del producto, tono (formal, amigable, persuasivo, directo, casual) y objetivo (agendar reunión, vender, informar, seguimiento, presentación).
- **Composición desde contactos** — Emails personalizados por contacto usando variables `{{nombre}}`, `{{empresa}}`, `{{cargo}}`.
- **Templates** — Guardar, listar y eliminar templates de email para reutilizar.

### 3. Enviar Campañas
- **Envío masivo** — Seleccionar template + contactos y enviar campaña vía Gmail.
- **Pixel tracking** — Inyección automática de pixel 1x1 en cada email para trackear aperturas.
- **Resultados en tiempo real** — Conteo de enviados, fallidos y estado de la campaña.

### 4. Historial de Contactos
- Listado completo con búsqueda y filtros.
- Paginación (20 por página).
- Filas expandibles con detalle completo.
- **Exportación a Excel** con todos los campos.
- Badges de origen (AI / Apollo / Manual) y confianza.

### 5. Estadísticas
- **Dashboard global** — Total campañas, emails enviados, tasa de apertura, total respondidos.
- **Detalle por campaña** — Enviados, fallidos, abiertos, sin abrir, respondidos, tasa de apertura.
- **Tabla de resultados individuales** por email dentro de cada campaña.

### 6. Respuestas
- **Sincronización con Gmail** — Busca respuestas a emails enviados por `message_id`.
- **Bandeja de entrada** — Lista de respuestas con badges de leído/no leído.
- **Responder** — Enviar respuesta directa desde la plataforma (HTML sanitizado con bleach).
- **Marcar como leído**.

### 7. Configuración
- **Apollo.io** — Guardar/eliminar API key (almacenada con encriptación Fernet).
- **Estado de integración** visible con badge.

---

## Sistema de Autenticación

### Flujo de Login
1. El usuario envía `POST /api/auth/login` con email y contraseña.
2. El backend busca al usuario en la tabla `usuarios_reach`.
3. Verifica la contraseña con bcrypt.
4. Genera un JWT (HS256) con claims: `usuario_id`, `email`, `nombre`, `rol`, `aud: "karia-reach"`, `iss: "karia-reach-backend"`, `exp` (configurable, default 8h).
5. Retorna el token + datos del usuario.

### Autenticación Dual
- **JWT** — Para el frontend. Header: `Authorization: Bearer <jwt_token>`.
- **API Key** — Para integraciones directas. Header: `Authorization: Bearer <KARIA_API_KEY>`. Validación con `hmac.compare_digest` (constant-time).

### Rutas Públicas (sin auth)
- `GET /health`
- `GET /track/*` (pixel tracking)
- `POST /api/auth/login`

### Frontend
- Token almacenado en `sessionStorage` (se borra al cerrar el navegador).
- Interceptor Axios inyecta el token en cada request.
- Respuestas 401 limpian la sesión y redirigen al login.

---

## Integraciones

### Claude AI (Anthropic)
- **Modelo:** Claude Sonnet 4 (configurable via `ANTHROPIC_MODEL`).
- **Búsqueda de contactos** — Usa `web_search` tool para buscar contactos reales por industria/ubicación. Retorna `null` en campos no encontrados (sin alucinaciones).
- **Generación de emails** — System prompt como copywriter B2B en español. Genera variantes con asunto y cuerpo HTML.
- **Composición personalizada** — Emails adaptados a cada contacto con sus datos.
- **Seguridad** — Protección anti-prompt-injection en system prompts, respuestas JSON-only, max 4096 tokens.

### Gmail (OAuth2)
- **Scopes:** `gmail.send`, `gmail.readonly`.
- **Envío** — MIME messages con HTML, envío async con `run_in_executor`.
- **Envío masivo** — Paralelo, un fallo no detiene el resto.
- **Pixel tracking** — Inyección automática de `<img>` 1x1 antes de `</body>`.
- **Lectura de respuestas** — Búsqueda por `rfc822msgid` o `in-reply-to`, filtra mensajes propios.

### Apollo.io (Opcional)
- **Búsqueda de contactos** — Por títulos y ubicación, hasta 100 resultados.
- **Enriquecimiento** — Individual o bulk, con matching por nombre + organización.
- **API key** — Almacenada con encriptación Fernet en tabla `integraciones`.
- **Rate limits internos** — 20 req/min para search y enrich.

---

## Seguridad (Pentest 8.4/10)

### Criptografía
- **Contraseñas** — bcrypt con salt.
- **API keys de terceros** — Encriptación Fernet (AES-128-CBC) antes de guardar en DB.
- **Tracking tokens** — HMAC-SHA256 para prevenir spoofing de aperturas.
- **JWT** — HS256 con validación de audience e issuer. Secret key mínimo 16 caracteres (validado al iniciar).

### Headers HTTP de Seguridad
- `Strict-Transport-Security` (HSTS 2 años)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy: default-src 'none'`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), camera=(), microphone=()`

### Validación de Entrada
- Pydantic models en todos los endpoints (tipos, longitudes min/max).
- `EmailStr` para validación de emails.
- Sanitización HTML con bleach en respuestas de email.
- Validación de enums para tono/objetivo.

### Rate Limiting (slowapi)
| Scope | Límite |
|---|---|
| General | 120 req/min |
| Composición (Claude) | 10 req/min |
| Envío de campañas | 5 req/min |
| Búsqueda IA (Claude + web) | 5 req/min |
| Apollo search/enrich | 20 req/min |

### Otras Medidas
- CORS configurable por origins.
- Comparación constant-time para API keys.
- Deduplicación de `message_id` en respuestas (previene replay).
- Validación de secrets al startup (exit si no cumplen mínimos).
- Error handling global: mensajes genéricos al cliente, logs detallados en servidor.
- Shutdown graceful con SIGTERM (Docker compatible).

---

## Base de Datos (PostgreSQL)

### Tablas

| Tabla | Propósito |
|---|---|
| `usuarios_reach` | Usuarios de la plataforma (email, password_hash bcrypt, rol, activo) |
| `contacts` | Contactos prospectados (nombre, empresa, cargo, emails, teléfonos, confianza 0-1, origen: ai/manual/apollo) |
| `templates` | Templates de email guardados (nombre, asunto, cuerpo HTML, tono, objetivo) |
| `campaigns` | Campañas de envío (nombre, template_id FK, contacts_count, status, sent/failed count, scheduled_at) |
| `campaign_results` | Resultados por email enviado (campaign_id FK, contact_id FK, message_id Gmail, exitoso, error, enviado_at, opened_at) |
| `email_replies` | Respuestas recibidas (campaign_id FK, contact_id FK, message_id único, in_reply_to, de, asunto, cuerpo, leido, respondido) |
| `integraciones` | API keys de terceros encriptadas (servicio, api_key Fernet, activo) |

---

## Variables de Entorno

Crear archivo `.env` en `backend/`:

```env
# ── Servidor ──
PORT=3001                              # Puerto del backend
NODE_ENV=development                   # development | production
BASE_URL=http://localhost:3001         # URL base (tracking pixels)
ALLOWED_ORIGINS=http://localhost:5173  # CORS origins (comma-separated)

# ── Claude AI (Anthropic) ──
ANTHROPIC_API_KEY=sk-ant-...           # API key de Anthropic
ANTHROPIC_MODEL=claude-sonnet-4-20250514  # Modelo (opcional, default sonnet)

# ── Gmail OAuth2 ──
GMAIL_CLIENT_ID=xxxx.apps.google...    # Google OAuth client ID
GMAIL_CLIENT_SECRET=GOCSPX-...        # Google OAuth client secret
GMAIL_REFRESH_TOKEN=1//0...            # Refresh token (offline access)
GMAIL_FROM_EMAIL=tu@email.com          # Email remitente

# ── Autenticación ──
KARIA_API_KEY=clave-minimo-16-chars    # API key para acceso directo (min 16 chars)
SECRET_KEY=clave-minimo-16-chars       # HMAC key para tracking (min 16 chars)
JWT_SECRET=clave-minimo-16-chars       # JWT signing secret (min 16 chars)
JWT_EXPIRATION_HOURS=8                 # Duración del token (default 8h)

# ── Encriptación ──
ENCRYPTION_KEY=base64-fernet-key       # Fernet key para encriptar API keys en DB
# Generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# ── Rate Limiting (opcional) ──
RATE_LIMIT_GENERAL=120/minute
RATE_LIMIT_COMPOSE=10/minute
RATE_LIMIT_SEND=5/minute
```

---

## Cómo Correr el Proyecto

### Backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env  # Editar con tus credenciales

# Iniciar servidor (desarrollo)
uvicorn main:app --host 0.0.0.0 --port 3001 --reload
```

El backend estará disponible en `http://localhost:3001`.

### Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Iniciar dev server
npm run dev
```

El frontend estará disponible en `http://localhost:5173`.

> Vite está configurado para hacer proxy de `/api` y `/track` hacia `http://localhost:3001`, así que no se necesita configuración CORS adicional en desarrollo.

### Primer superadmin

El sistema arranca sin usuarios. Para crear el primer superadmin, ejecutar el script incluido:

```bash
cd backend
python scripts/crear_superadmin.py
```

Una vez creado, podés gestionar el resto de los usuarios desde el panel de administración en `/admin`.

---

## API Endpoints

### Autenticación
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/auth/login` | Login con email/password, retorna JWT |

### Contactos
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/contacts` | Listar contactos guardados con paginación |
| POST | `/api/contacts/search-ai` | Buscar contactos con Claude + web search |
| POST | `/api/contacts/save-selection` | Guardar hasta 50 contactos seleccionados |
| POST | `/api/contacts/manual` | Agregar contacto manual |
| DELETE | `/api/contacts/{id}` | Eliminar contacto por UUID |

### Composición de Emails
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/compose/generate` | Generar 1-5 variantes de email con IA |
| POST | `/api/compose/generate-from-contacts` | Generar emails personalizados por contacto |
| GET | `/api/compose/templates` | Listar templates guardados |
| POST | `/api/compose/templates` | Crear template nuevo |
| DELETE | `/api/compose/templates/{id}` | Eliminar template |

### Campañas y Envío
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/send/campaign` | Crear y ejecutar campaña de emails |
| GET | `/api/send/campaigns` | Listar todas las campañas |
| GET | `/api/send/campaigns/{id}/stats` | Estadísticas detalladas de una campaña |
| GET | `/api/send/stats` | Estadísticas globales agregadas |
| GET | `/api/send/dashboard` | Dashboard (totales de contactos, templates, campañas) |

### Respuestas
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/replies/{campaign_id}` | Listar respuestas de una campaña |
| POST | `/api/replies/{campaign_id}/sync` | Sincronizar respuestas desde Gmail |
| POST | `/api/replies/{reply_id}/respond` | Responder a un email recibido |
| PATCH | `/api/replies/{reply_id}/read` | Marcar respuesta como leída |

### Apollo.io
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/apollo/status` | Verificar si Apollo está configurado |
| POST | `/api/apollo/config` | Guardar API key de Apollo (encriptada) |
| DELETE | `/api/apollo/config` | Eliminar/desactivar API key |
| POST | `/api/apollo/search` | Buscar contactos en Apollo |
| POST | `/api/apollo/enrich` | Enriquecer contactos con datos de Apollo |

### Tracking y Health
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/track/open/{campaign_id}/{contact_id}` | Pixel tracking de apertura (público, retorna GIF 1x1) |
| GET | `/health` | Health check del servicio |

---

## Estado Actual

### Funcionando
- Login/autenticación con JWT + API Key
- Búsqueda de contactos con Claude AI (web search)
- Búsqueda de contactos con Apollo.io
- Carga manual de contactos
- Generación de emails con IA (variantes y personalizados)
- Gestión de templates
- Envío de campañas masivas via Gmail
- Pixel tracking de aperturas (HMAC validado)
- Estadísticas globales y por campaña
- Sincronización y gestión de respuestas
- Exportación a Excel
- Configuración de integraciones (Apollo)
- Envío programado de campañas (APScheduler)
