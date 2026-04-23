# 🗓 Agente de Google Calendar — CrewAI + Claude

Agente conversacional para gestionar Google Calendar en lenguaje natural.  
**Stack:** FastAPI · CrewAI · Google Calendar API · Claude (Anthropic)

---

## Paso 1 — Obtener credenciales de Google (10 min)

### 1.1 Crear proyecto en Google Cloud

1. Entrá a [console.cloud.google.com](https://console.cloud.google.com)
2. Hacé clic en **Seleccionar proyecto** → **Nuevo proyecto**
3. Dale un nombre (ej: `calendar-agent`) y crealo

### 1.2 Habilitar Google Calendar API

1. Menú → **APIs y servicios** → **Biblioteca**
2. Buscá **Google Calendar API** → clic en **Habilitar**

### 1.3 Configurar pantalla de consentimiento OAuth

1. Menú → **APIs y servicios** → **Pantalla de consentimiento de OAuth**
2. Tipo de usuario: **Externo** → Crear
3. Completá: nombre de la app, tu email de soporte, tu email de contacto
4. En **Permisos** no agregues nada (lo maneja el script)
5. En **Usuarios de prueba** → **Add Users** → agregá tu email de Google
6. Guardá

### 1.4 Crear credenciales OAuth 2.0

1. Menú → **APIs y servicios** → **Credenciales**
2. **+ Crear credenciales** → **ID de cliente OAuth**
3. Tipo de aplicación: **Aplicación de escritorio**
4. Nombre: `calendar-agent-local`
5. Creá → Copiá el **Client ID** y **Client Secret**

### 1.5 Obtener el refresh_token (ejecutá UNA VEZ)

```bash
# En tu máquina local, con el proyecto descargado:
pip install google-auth-oauthlib
# Editá get_token.py con tu Client ID y Client Secret
python get_token.py
```

Se abrirá el browser. Autorizá con tu cuenta de Google.  
El script imprimirá tus 3 variables listas para copiar.

---

## Paso 2 — Desarrollo local

```bash
cd calendar-agent
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Editá .env con tus claves
python main.py
# → Abrí http://localhost:8000
```

---

## Paso 3 — Deploy en Heroku

```bash
# 1. Login
heroku login

# 2. Crear app
heroku create nombre-de-tu-app

# 3. Variables de entorno (reemplazá con tus valores reales)
heroku config:set \
  ANTHROPIC_API_KEY="sk-ant-..." \
  GOOGLE_CLIENT_ID="xxxxxx.apps.googleusercontent.com" \
  GOOGLE_CLIENT_SECRET="GOCSPX-xxxxxxx" \
  GOOGLE_REFRESH_TOKEN="1//xxxxxxx"

# 4. Deploy
git init
git add .
git commit -m "Initial deploy"
heroku git:remote -a nombre-de-tu-app
git push heroku main

# 5. Abrir
heroku open
```

---

## Estructura del proyecto

```
calendar-agent/
├── main.py                  # FastAPI (servidor + rutas)
├── agent.py                 # Lógica del agente CrewAI
├── google_calendar_tool.py  # Herramientas CRUD de Google Calendar
├── get_token.py             # Script para obtener refresh_token (una vez)
├── templates/
│   └── index.html           # UI del chat
├── requirements.txt
├── Procfile                 # Heroku
├── runtime.txt              # Python 3.11
└── .env.example
```

---

## Troubleshooting

**Estado "Config. incompleta"**
```bash
heroku config   # verificá que las 4 variables estén seteadas
```

**Error de autenticación Google**  
El refresh_token puede expirar si la app está en modo "testing" en Google Cloud y pasaron 7 días. Volvé a correr `python get_token.py`.

**Para que no expire:** En Google Cloud Console → Pantalla de consentimiento → publicá la app (o usá una cuenta de G Suite/Workspace).

**Ver logs en vivo**
```bash
heroku logs --tail
```

**Timeout en Heroku Free**  
CrewAI puede tardar 15-30 segundos. Usá dynos **Eco** o **Basic** para evitar timeouts.
