# Tests

Tests para el módulo social usando pytest, organizados por tipo.

## Estructura

```
tests/
├── unit/              # Tests unitarios (rápidos, sin dependencias externas)
│   ├── test_config.py
│   └── test_platforms.py
├── integration/       # Tests de integración (con mocks)
│   └── test_yt_downloader.py
├── e2e/              # Tests end-to-end (integración real)
│   ├── test_yt_downloader_e2e.py
│   └── README.md
├── conftest.py       # Fixtures compartidas
└── README.md         # Este archivo
```

## Tipos de tests

### Unit Tests (`tests/unit/`)
Tests unitarios que prueban componentes individuales de forma aislada:
- `test_config.py`: Tests para `social.config.Config`
- `test_platforms.py`: Tests para `social.platforms` (Platform, YouTubePlatform, etc.)

**Ejecutar:**
```bash
pytest tests/unit -v
```

### Integration Tests (`tests/integration/`)
Tests de integración que prueban la interacción entre componentes usando mocks:
- `test_yt_downloader.py`: Tests para `social.services.YT_Downloader` con mocks

**Ejecutar:**
```bash
pytest tests/integration -v
```

### E2E Tests (`tests/e2e/`)
Tests end-to-end que prueban la integración real con servicios externos:
- `test_yt_downloader_e2e.py`: Tests de descarga real de videos de YouTube

**Ejecutar:**
```bash
pytest tests/e2e -v
# o usando markers
pytest -m e2e -v
```

## Ejecutar tests

```bash
# Instalar dependencias de testing
pip install pytest pytest-cov

# Ejecutar todos los tests
pytest

# Solo tests rápidos (excluir e2e y slow)
pytest -m "not e2e and not slow"

# Solo tests unitarios
pytest tests/unit -v

# Solo tests de integración
pytest tests/integration -v

# Solo tests e2e
pytest tests/e2e -v

# Ejecutar tests con coverage
pytest --cov=social --cov-report=html

# Ejecutar un test específico
pytest tests/unit/test_platforms.py::TestPlatform::test_platform_init_defaults -v

# Ejecutar tests y mostrar output
pytest -v -s
```

## Markers disponibles

- `@pytest.mark.unit`: Tests unitarios
- `@pytest.mark.integration`: Tests de integración
- `@pytest.mark.e2e`: Tests end-to-end (requieren conexión a internet)
- `@pytest.mark.slow`: Tests que tardan más tiempo
- `@pytest.mark.download`: Tests que descargan archivos

**Ejemplos:**
```bash
# Solo tests e2e
pytest -m e2e

# Excluir tests e2e
pytest -m "not e2e"

# Tests e2e pero no los lentos
pytest -m "e2e and not slow"
```

## Fixtures

Las fixtures están definidas en `conftest.py`:

- `temp_dir`: Directorio temporal para tests
- `config`: Instancia de Config con directorios temporales
- `platforms_json_file`: Archivo platforms.json de ejemplo
- `cookie_file`: Archivo de cookies de ejemplo

## Mocking

Los tests de integración usan `monkeypatch` (fixture nativa de pytest) para hacer mocking:
- Se usa `monkeypatch.setattr()` para reemplazar funciones/clases
- Se usa `monkeypatch.setenv()` para variables de entorno
- Los tests E2E NO usan mocks, realizan operaciones reales

## Notas

- Los tests unitarios y de integración usan directorios temporales
- Los tests de integración mockean yt-dlp para evitar descargas reales
- Los tests E2E realizan descargas reales y requieren conexión a internet
- Los tests verifican tanto casos exitosos como manejo de errores
- Todos los tests están escritos usando pytest puro
