# Publicación

El sitio es la carpeta `web/`, servida por GitHub Pages desde la rama `main` (`.github/workflows/pages.yml`). Un segundo flujo (`.github/workflows/refresh.yml`) actualiza a diario los cargos y los precios de combustibles y confirma los cambios en la misma rama.

Para publicar un cambio basta con subirlo a `main`; Pages lo reconstruye en uno o dos minutos.
