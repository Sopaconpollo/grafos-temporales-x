# Grafos temporales de X

Auditoría de capturas Zeeschuimer y análisis exploratorio de comunidades estructurales.

```
python -m pip install -r requirements.txt
python auditar.py RUTA_CAPTURAS resultados
python verificar.py resultados
python comunidades.py resultados comunidades
```

Usa Python 3.10 o posterior. La carpeta de capturas debe incluir MANIFIESTO_SHA256.txt. Los resultados se escriben en una carpeta independiente.
