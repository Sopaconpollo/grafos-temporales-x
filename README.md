# Grafos temporales de X

Auditoría de capturas Zeeschuimer y análisis exploratorio de comunidades estructurales.

```
python -m pip install -r requirements.txt
python auditar.py RUTA_CAPTURAS resultados
python verificar.py resultados
python comunidades.py resultados comunidades
python validar_objetivos.py resultados comunidades validacion
python contraste_textual.py RUTA_CAPTURAS resultados comunidades validacion
python muestra_revision.py RUTA_CAPTURAS resultados fichas_revision.json
python analisis_ampliado.py RUTA_CAPTURAS resultados analisis_ampliado
python figuras_g16.py analisis_ampliado g16_figuras
python explorador_grafos.py resultados comunidades explorador_plantilla.html explorador_grafos.html
```

Usa Python 3.10 o posterior. La carpeta de capturas debe incluir MANIFIESTO_SHA256.txt. Los resultados se escriben en una carpeta independiente.

Para regenerar las figuras vectoriales, instala ReportLab. La revisión de la entrega anotada está en G16_revision.tex.
