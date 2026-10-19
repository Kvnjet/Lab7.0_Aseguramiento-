# Laboratorio de pruebas de integración API (Postman + Pytest)

API usada: https://dummyjson.com (carrito simulado: `POST /carts/add` calcula total pero no persiste).
Limitación: DummyJSON usa `thumbnail` en lugar de `image`. El usuario `emilys` es una credencial demo pública.

## Pytest
```
pip install -r requirements.txt
pytest -v --junitxml=pytest_report.xml
```

## Postman
1. Importar `postman/Integracion_API_Carrito.postman_collection.json` y `postman/QA_API_LAB.postman_environment.json`.
2. Seleccionar el environment `QA_API_LAB` y ejecutar con Collection Runner (3 iteraciones).
3. Newman (opcional):
```
newman run postman/Integracion_API_Carrito.postman_collection.json -e postman/QA_API_LAB.postman_environment.json -n 3
```

## Contenido
`tests/` pruebas Pytest · `postman/` colección y environment · `Reporte_Laboratorio.docx` reporte final.
