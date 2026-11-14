# Infórmate

México en mapas: quién gobierna cada lugar y con qué datos vive. Cada cifra y cada persona llevan su fuente y su fecha.

https://mexico-en-datos.github.io/mexicoendatos/

## Para ejecutarlo en tu computadora

```
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python tools/build_map.py          # mapa de municipios y distritos (una vez)
.venv/bin/python tools/fetch_politicians.py  # cargos
.venv/bin/python tools/serve.py              # abre http://127.0.0.1:8000
```

Las demás herramientas en `tools/` descargan el resto de los datos (economía, seguridad, combustibles, patrimonio); cada una explica al inicio qué lee y qué escribe. Las fuentes están en la página «Fuentes» del sitio.

```
.venv/bin/python -m pytest -q
```
