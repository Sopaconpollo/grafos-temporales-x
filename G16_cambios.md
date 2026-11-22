# Revisión de G16 para la segunda entrega

El LaTeX revisado toma como base el PDF anotado G16 (2). Conserva el orden de las secciones de la entrega, los seis objetivos específicos, las preguntas de investigación y la notación central. El archivo original de LaTeX de esa versión no estaba adjunto. El texto y las ecuaciones se reconstruyeron desde el PDF, de modo que pueden variar detalles de composición y saltos de página.

| Página | Marca del docente | Cambio aplicado |
|---|---|---|
| 1 | Tachó «pt2» y marcó el bloque de autoría con «Revisar» | Se quitó «pt2» y se usaron los nombres completos del borrador anterior, en el orden del PDF. |
| 2–3 | «MODELO» al lado del ejemplo aplicado y «Aquí se inicia con el grafo» al inicio del modelamiento | Se conservan las definiciones generales en el marco teórico. El modelamiento abre con el grafo mensual y recoge el ejemplo de cuentas, la asignación temporal y las capas de interacción. |
| 4 | Revisar la fuente y el tamaño de los datos | Se identifican Zeeschuimer, las 28 exportaciones NDJSON, los 39.787 registros, las 37.069 publicaciones únicas dentro del periodo y la cobertura de enero a junio de 2026. |

Las marcas de visto se interpretaron como aceptación. La simetrización promedio de la entrega se conserva en la formulación y se explica su equivalencia con la simetrización por suma para el laplaciano normalizado y la modularidad.

Los resultados nuevos se añadieron después de la solución propuesta. Incluyen reciprocidad, concentración del peso entrante, conectividad por capa, submuestreo a igual volumen, continuidad sobre cuentas compartidas y coincidencias de contenido. La bibliografía original se conserva y se añaden las referencias usadas en el análisis nuevo.

## Uso de los archivos

El ZIP del artículo contiene `G16_revision.tex` y la carpeta `g16_figuras`. Hay que conservar esa carpeta junto al archivo principal al importarlos en Overleaf. Los gráficos son PDF vectoriales. Se cotejaron las cifras principales y se comprobó la estructura del LaTeX. La composición del artículo completo queda por verificar con un compilador IEEEtran.

Para reproducir las nuevas tablas y figuras, con Python y NumPy, y ReportLab para los gráficos:

```text
python analisis_ampliado.py RUTA_CAPTURAS resultados analisis_ampliado
python figuras_g16.py analisis_ampliado g16_figuras
```

El análisis de contenido usa reglas léxicas explícitas. Las tablas correspondientes no incluyen textos originales ni identificadores de cuenta.
