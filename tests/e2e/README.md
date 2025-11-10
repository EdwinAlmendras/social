# Tests End-to-End (E2E)

Esta carpeta contiene tests end-to-end que prueban la integración real del sistema con servicios externos.

## Tests de YT_Downloader

Los tests E2E de `YT_Downloader` realizan descargas reales de videos para verificar:

- Descarga real de videos de YouTube
- Detección automática de plataforma
- Uso de configuración personalizada
- Manejo de cookies
- Extracción de metadata
- Manejo de errores con URLs inválidas

## Tests de TelegramUploader

Los tests E2E de `TelegramUploaderService` realizan subidas reales a Telegram para verificar:

- Subida real de videos a grupos de Telegram
- Conexión y autenticación con Telegram
- Acceso a grupos y topics
- Subida con captions personalizados
- Validación de configuración de entities

## Requisitos

### Para tests de YT_Downloader:
- Conexión a internet activa
- Acceso a YouTube y otras plataformas
- `yt-dlp` instalado y funcional
- **Cookies de YouTube**: Los tests E2E requieren cookies reales para funcionar correctamente

### Para tests de TelegramUploader:
- Credenciales de Telegram API (API_ID, API_HASH, PHONE)
- Sesión de Telegram autorizada
- Acceso al grupo de Telegram configurado
- Video de prueba en `downloads/youtube/`
- Configuración válida en `.config/entities.json`

### Configurar cookies de YouTube

Los tests E2E verifican automáticamente si existen cookies antes de ejecutarse. Si no existen, los tests se saltarán con un mensaje informativo.

Para configurar las cookies:

1. Exporta tus cookies de YouTube usando una extensión del navegador (ej: "Get cookies.txt LOCALLY")
2. Guarda el archivo como `youtube.txt` en tu directorio de cookies
3. Por defecto, el directorio es `~/.config/social/cookies/` o usa la variable de entorno `COOKIES_DIR`

```bash
# Ejemplo en Linux/Mac
mkdir -p ~/.config/social/cookies
cp /ruta/a/tus/cookies/youtube.txt ~/.config/social/cookies/

# O configura la variable de entorno
export COOKIES_DIR=/ruta/personalizada/cookies
```

### Configurar credenciales de Telegram

Para ejecutar los tests de TelegramUploader, necesitas tener un archivo `.env` en la raíz del proyecto con:

```env
TELEGRAM_API_ID=tu_api_id
TELEGRAM_API_HASH=tu_api_hash
BOT_TOKEN=tu_bot_token
```

**Obtener credenciales de Telegram:**
1. Ve a https://my.telegram.org/apps
2. Inicia sesión con tu número de teléfono
3. Crea una nueva aplicación
4. Copia el `api_id` y `api_hash`

**Obtener BOT_TOKEN:**
1. Habla con @BotFather en Telegram
2. Crea un nuevo bot con `/newbot`
3. Copia el token que te proporciona

**Sesión de usuario:**
Los tests requieren una sesión de usuario autorizada. Para autorizar la sesión:

```bash
# Ejecutar el script de autorización
python tests/e2e/authorize_telegram.py
```

El script te pedirá:
1. Tu número de teléfono (con código de país, ej: +1234567890)
2. El código que recibirás en Telegram
3. Tu contraseña 2FA (si la tienes configurada)

Una vez autorizado, se creará el archivo `uploader.session` en la raíz del proyecto.

## Ejecutar tests E2E

### Ejecutar todos los tests E2E:
```bash
pytest tests/e2e -v
```

### Ejecutar solo tests E2E (excluyendo otros):
```bash
pytest -m e2e -v
```

### Ejecutar tests E2E excluyendo los lentos:
```bash
pytest tests/e2e -m "e2e and not slow" -v
```

### Ejecutar un test específico:
```bash
# Test de descarga de YouTube
pytest tests/e2e/test_yt_downloader_e2e.py::TestYT_DownloaderE2E::test_download_youtube_video_real -v

# Test de subida a Telegram
pytest tests/e2e/test_telegram_uploader_e2e.py::TestTelegramUploaderE2E::test_upload_video_to_telegram -v
```

### Ejecutar solo tests de Telegram:
```bash
pytest tests/e2e/test_telegram_uploader_e2e.py -v
```

## Notas importantes

- Los tests E2E pueden tardar varios minutos en ejecutarse
- Requieren conexión a internet estable
- **Requieren cookies reales de YouTube** - Los tests se saltarán automáticamente si no existen
- Algunos tests están marcados como `@pytest.mark.slow` porque tardan más tiempo
- Los archivos descargados se guardan en directorios temporales que se limpian automáticamente
- Si un test falla, verifica:
  - Tu conexión a internet
  - Que YouTube esté accesible
  - Que tus cookies sean válidas y no hayan expirado
  
### Tests que se saltan sin cookies

Si no tienes cookies configuradas, verás mensajes como:
```
SKIPPED [1] tests/e2e/test_yt_downloader_e2e.py:XX: YouTube cookies not found; skipping real download test
```

Esto es normal y esperado. Los tests solo se ejecutarán cuando tengas cookies válidas configuradas.

## Estructura de tests

### test_yt_downloader_e2e.py
- `TestYT_DownloaderE2E`: Tests básicos de descarga real
- `TestYT_DownloaderE2EAdvanced`: Tests avanzados con metadata y configuración personalizada

### test_telegram_uploader_e2e.py
- `TestTelegramUploaderE2E`: Tests básicos de subida a Telegram
  - `test_upload_video_to_telegram`: Sube un video real al grupo configurado
  - `test_upload_with_custom_caption`: Sube con caption personalizado
  - `test_telegram_client_connection`: Verifica conexión a Telegram
  - `test_telegram_group_access`: Verifica acceso al grupo
  - `test_video_file_exists`: Verifica que existe el video de prueba
  - `test_entities_config_valid`: Valida la configuración de entities
- `TestTelegramUploaderE2EAdvanced`: Tests avanzados (en desarrollo)
