# Guion de sustentación · G16

**Duración objetivo: 15 minutos, incluido el demo.** Las preguntas del docente van después. El reparto es sugerido: Sara cubre las diapositivas 1–5 y 8, y Juan presenta 6–7 y 9–11. Los tiempos de abajo marcan el minuto acumulado de la exposición.

Antes de empezar, descompriman el paquete y abran el HTML de la sustentación. Comprueben que el botón de la diapositiva 9 abre el explorador en otra pestaña. Para el demo basta con tener ambos archivos en la misma carpeta. Si usan el botón de pantalla completa de la presentación, salgan de ese modo antes de alternar pestañas. Arranquen el cronómetro en la portada.

## 1. Portada · 0:00–0:45 · Sara

> Buenos días. Somos Sara Valentina Figueredo Laserna y Juan Sebastian Mora Cabrera. En este artículo estudiamos cómo cambian las comunidades de interacción en X durante el ciclo presidencial colombiano, usando publicaciones de enero a junio de 2026. La pregunta surgió de algo sencillo: dos cuentas pueden interactuar porque coinciden, porque discuten o porque una menciona a la otra. Queríamos entender primero qué estructura se puede medir con esas relaciones. Vamos a mostrar cómo construimos los grafos, qué encontramos al compararlos y, al final, cómo se ven las comunidades en nuestro explorador.

## 2. Pregunta y objetivos · 0:45–1:45 · Sara

> La pregunta central es qué parte de la organización de la red se mantiene entre meses. Para responderla, primero validamos la muestra y reconstruimos las interacciones. Luego construimos la familia de grafos, calculamos matrices y comparamos comunidades con dos métodos. Por último, examinamos si las conclusiones cambian cuando modificamos los pesos o igualamos la cantidad de publicaciones. Esto es importante porque una estructura que solo aparece bajo una decisión puntual de modelamiento necesita una interpretación más cauta. El objetivo principal del artículo es estructural. La conexión con polarización ideológica queda formulada como una pregunta que requiere datos independientes sobre las posiciones de las cuentas.

**Transición:** «Empecemos por lo que realmente observamos en los archivos».

## 3. Fuente y auditoría · 1:45–2:55 · Sara

> La fuente fueron 28 capturas de Zeeschuimer. Sus tamaños y hashes coincidieron con el manifiesto. Partimos de 39.787 filas y quitamos 2.667 copias adicionales y 51 publicaciones únicas fuera de enero a junio. El corpus final tiene 37.069 publicaciones. La asignación mensual usa la fecha real en Bogotá, porque el mes de la carpeta puede diferir del mes de publicación. Revisamos además 42 eventos contra las capturas y corroboramos los 42. En una revisión temática distinta, de ocho textos por mes, 32 de 48 tenían contenido electoral explícito. Esa revisión ayuda a describir la muestra y sus límites. No permite extrapolar sin más el porcentaje a todo el corpus ni estimar cuántas aristas omitimos.

**En pantalla:** señalen primero la cifra del corpus y después las dos verificaciones. Eviten recitar cada fila del proceso.

## 4. Modelo y método · 2:55–4:15 · Sara

> Por cada mes y tipo de interacción construimos una matriz dirigida. La entrada i, j cuenta eventos del autor i al destinatario j. Una respuesta y una mención tienen significados diferentes, así que las mantuvimos en capas. La red agregada suma las capas con pesos unitarios como referencia. Para el análisis espectral usamos una proyección simétrica. El artículo escribe el promedio de la matriz y su transpuesta. El código utiliza la suma. Ambas producen el mismo laplaciano normalizado porque al duplicar los pesos también se duplican los grados y el factor se cancela al normalizar. Conservamos la dirección en los datos originales. Como las capas observadas estaban desconectadas, analizamos el espectro dentro de la componente mayor y registramos qué fracción del grafo representa. Los autolazos quedan en el registro de eventos y se excluyen de las matrices.

**Señala** el término (W_t) al explicar el agregado y (B_t) al pasar al espectro. Si preguntan por republicaciones, no hubo metadatos explícitos suficientes para identificar sus destinatarios.

## 5. Familia de grafos · 4:15–5:35 · Sara

> En la red completa, la componente mayor contiene el 94,2 % de las cuentas en enero y el 59,9 % en junio. Pero enero tiene muchas más publicaciones, así que hicimos un contraste con el mismo volumen de publicaciones con interacción. Junio fija el mínimo de 433. En cada mes seleccionamos publicaciones completas, conservando juntos todos sus eventos. En enero, la mediana de conectividad a ese volumen baja a 70,6 %. La brecha entre enero y junio pasa de 34,2 a 10,6 puntos porcentuales. Eso nos muestra cuánto puede cambiar la comparación al controlar solo el volumen. La brecha restante puede depender de la composición de cuentas y de la captura. Los intervalos de submuestreo del artículo describen variación dentro de los datos observados.

**Entrega:** «Juan va a mostrar qué ocurre cuando intentamos dividir esas componentes en comunidades».

## 6. Comunidades y particiones · 5:35–7:05 · Juan

> Aplicamos dos métodos a las mismas componentes mayores. En la bipartición espectral usamos los dos primeros autovectores del laplaciano normalizado, normalizamos las filas y agrupamos con k-medias para obtener dos grupos. Eso sirve para comprobar si aparece un corte informativo. En la red agregada el grupo pequeño solo tuvo entre 8 y 21 cuentas. El segundo método empieza con cada cuenta en su propio grupo y fusiona pares siempre que aumente la modularidad. Esta función compara el peso dentro de las comunidades con el esperado según los grados de los nodos. El procedimiento obtuvo entre 27 y 79 grupos mensuales. La diferencia se entiende porque los métodos trabajan con resoluciones distintas. Uno obliga a producir dos grupos y el otro permite varios. En el demo veremos ambos sobre la red de enero.

**Idea de apoyo si sobra tiempo:** un valor alto de modularidad describe cómo se concentra la interacción bajo el modelo de referencia. Su valor por sí solo no permite atribuir una ideología a cada grupo.

## 7. Continuidad y robustez · 7:05–8:15 · Juan

> Para comparar meses usamos dos medidas complementarias. Jaccard divide la intersección de dos grupos por su unión. El mejor par de comunidades de modularidad en cada transición tuvo valores entre 0,083 y 0,222 con los conjuntos completos. El índice de Rand ajustado, en cambio, compara el agrupamiento de todas las cuentas que aparecen en ambas componentes. En modularidad estuvo entre 0,034 y 0,103. Esto indica poca coincidencia global incluso entre las cuentas que sí permanecieron. También probamos la sensibilidad a las interacciones. Duplicar el peso de respuestas o citas mantuvo gran parte de la bipartición de referencia. Cuando quitamos las menciones, los cinco meses comparables dieron un ARI cercano a cero. La elección de la capa importa para entender el resultado.

**Entrega:** «Sara va a explicar qué podemos observar cuando pasamos de las aristas al contenido».

## 8. Contenido y contexto · 8:15–9:30 · Sara

> Para analizar el contenido usamos reglas reproducibles que buscan nombres y palabras clave. Por ejemplo, entre marzo y junio las referencias a Paloma Valencia pasaron de 37,7 a 2,1 por ciento, mientras que las de Abelardo de la Espriella pasaron de 17,9 a 53,5 por ciento. Una publicación puede mencionar más de una figura. También comparamos vocabulario con TF-IDF y similitud coseno en las dos comunidades mayores del método de modularidad. Entre enero y mayo, la similitud promedio entre los dos grupos fue menor que las dos similitudes internas. En junio esa relación no se mantuvo para ambos grupos. Estos resultados describen palabras observadas en el corpus. Tampoco atribuimos cambios a eventos electorales, porque las ventanas alrededor de las jornadas son descriptivas y dependen de lo que se capturó.

**Entrega:** «Ahora vamos a ver cómo se traducen estos resultados en el explorador».

## 9. Demo en vivo · 9:30–13:00 · Juan

### 9:30–10:25 · Enero, red agregada, modularidad

**Acción.** Abrir el explorador. Confirmar **Enero**, capa **Agregada** y **Modularidad voraz**. Señalar el encabezado y hacer clic en **G1**.

> Cada círculo agrupa cuentas. El tamaño da una idea de cuántas hay en cada grupo. Las flechas muestran dirección y su grosor refleja el peso de las interacciones entre grupos. En esta vista hay 79 grupos en la componente mayor, que abarca 5.483 de las 5.822 cuentas de la red de enero. Al seleccionar G1, el panel separa eventos internos, entradas y salidas. Abajo vemos hasta 24 cuentas anónimas seleccionadas por su peso interno.

**Pausa breve.** Señalar la diferencia entre eventos internos y flechas que salen, sin intentar leer cada arista.

### 10:25–11:15 · Misma red, bipartición espectral

**Acción.** Mantener enero y la capa agregada. Cambiar **Partición** a **Bipartición espectral**.

> Cambiamos únicamente el método. La componente mayor sigue teniendo 5.483 cuentas, pero ahora vemos dos grupos: 5.472 y 11. Esa es la evidencia visual de que el corte espectral separa un grupo pequeño, mientras el otro método describe la estructura con más detalle. La diferencia se debe a la pregunta que hace cada algoritmo sobre la misma red.

### 11:15–12:20 · Junio, capa de respuestas

**Acción.** Cambiar a **Junio**, seleccionar **Respuestas** y volver a **Modularidad voraz**. Señalar el texto «10 de 255 cuentas».

> Ahora cambiamos simultáneamente el mes y la capa para mostrar un caso de fragmentación. En junio, la red de respuestas tiene 255 cuentas, pero la componente mayor solo contiene 10, aproximadamente el 3,9 por ciento. Los círculos en pantalla representan esos diez nodos agrupados. El encabezado es importante para saber cuánto del grafo original describe la partición. Además, la etiqueta G1 se asigna por tamaño dentro de cada vista. Para afirmar que un grupo persiste entre meses necesitamos comparar sus integrantes con Jaccard o ARI.

### 12:20–13:00 · Volver y conectar con el artículo

**Acción.** Volver a la pestaña de la presentación y avanzar a la diapositiva 10. Si se van retrasando, regresen a las **12:40** y omitan cualquier clic adicional.

> Las tres vistas muestran por qué debemos decir qué mes, qué tipo de interacción y qué componente estamos analizando. El explorador nos deja inspeccionar ejemplos. Las tablas y los gráficos del artículo hacen la comparación sistemática de todos los meses.

**Respaldo.** Si el demo falla, abrir el desplegable de la diapositiva 9 y explicar las tres vistas con sus cifras. Mantener el paso al cierre a las 13:00.

## 10. Interpretación · 13:00–14:10 · Juan

> La evidencia más sólida es que la continuidad global fue baja y que las menciones influyen en la bipartición agregada. Hay que interpretar esas comparaciones teniendo en cuenta la rotación de cuentas y las diferencias de cobertura. El análisis de texto aporta una dimensión descriptiva, pero las menciones pueden expresar apoyo, crítica o simplemente señalar a otra persona. Para medir polarización ideológica se necesitarían etiquetas construidas de forma independiente, un protocolo para verificar el acuerdo entre revisores y un referente estadístico que tenga en cuenta tamaños de grupos y grados. Esta distinción permite responder los objetivos estructurales del artículo sin extender la conclusión por encima de lo que observamos.

## 11. Cierre · 14:10–15:00 · Juan

> El trabajo deja tres resultados. En conectividad, el volumen de publicaciones explica parte de la brecha entre enero y junio. En comunidades, algunos grupos locales coinciden, pero la asignación global cambia incluso entre las cuentas compartidas. En contenido, vimos cambios en el vocabulario explícito y dejamos abierta la interpretación ideológica. El aporte es una familia de grafos verificable, con un procedimiento que permite rastrear de dónde salen los resultados y examinar sus decisiones. Muchas gracias. Quedamos atentos a sus preguntas.

## Respuestas cortas para el docente

- **¿Por qué usar la componente mayor?** En el grafo completo desconectado, el segundo autovalor es cero. La componente mayor permite comparar conectividad interna y reportar por separado cuánto del grafo cubre.
- **¿Por qué comparar dos métodos?** El corte espectral diagnostica una división en dos. La optimización de modularidad ofrece una partición con número variable de grupos. La diferencia entre sus resultados hace visible la escala del agrupamiento.
- **¿Igualar el volumen elimina el sesgo de captura?** Iguala el número de publicaciones con interacción. Siguen variando las consultas, las cuentas observadas y los destinatarios.
- **¿Qué significa que el ARI sea cercano a cero?** Poco acuerdo frente al referente ajustado por azar entre dos asignaciones sobre las mismas cuentas. No es un porcentaje de cuentas que cambiaron de grupo.
- **¿Podemos decir que aumentó la polarización?** El estudio mide estructura y vocabulario. Para estudiar polarización ideológica se necesitan posiciones independientes y evidencia del sentido de las interacciones.
