# AllCollege

AllCollege es un prototipo de plataforma escolar que centraliza el registro de asistencia, retiros, accidentes y notas, además de entregar un portal para apoderados.

## Características principales

- Registro y estadísticas de alumnos por curso.
- Registro de asistencia con visualización de totales y tasas por estudiante.
- Gestión de retiros con historial reciente.
- Registro de accidentes con resumen por nivel de severidad.
- Registro de notas con cálculo de promedios por alumno y asignatura.
- Portal para apoderados con acceso a asistencia y promedios de notas de su hijo o hija.

## Requisitos

- Python 3.11+
- pip

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate  # En Windows use `.venv\\Scripts\\activate`
pip install -r requirements.txt
```

## Ejecución

```bash
flask --app app run --debug
```

La base de datos SQLite (`allcollege.db`) se crea automáticamente al iniciar la aplicación.

## Estructura básica

- `app.py`: aplicación Flask con rutas y modelos de datos.
- `templates/`: vistas HTML (Jinja2).
- `static/styles.css`: estilos principales.

## Datos de prueba

Registre alumnos desde la sección "Alumnos". La contraseña definida para el apoderado servirá para el portal de apoderados.

## Notas

- Este prototipo usa autenticación sencilla para apoderados basada en el correo y una contraseña definida al registrar al alumno.
- Para un entorno productivo cambie la `SECRET_KEY` en `app.py` y considere un flujo de autenticación más robusto.
