# Colombia - Churn ficticio

Este documento es ficticio y sirve para probar metadata filtering en RAG Lab. No representa datos reales de Colombia ni de ninguna empresa real.

## Early Churn

En la operación ficticia de Colombia, Early Churn significa que un cliente nuevo abandona, cancela o deja de usar activamente el servicio durante los primeros 60 días desde el alta. Esta ventana de 60 días es deliberadamente distinta a la de Bolivia para probar filtros por país.

## Señales de riesgo

Para prepago, una señal ficticia es no realizar recargas durante los primeros 25 días. Para pospago, una señal es solicitar baja antes de la segunda factura. Para hogar, una señal es acumular dos visitas técnicas fallidas durante el primer mes.

## Causas ficticias

Las causas principales inventadas son congestión en ciudades grandes, expectativas incorrectas sobre promociones, demoras en portabilidad y problemas de instalación hogar. El equipo local analiza clientes nuevos durante dos ciclos mensuales para distinguir abandono real de demora operativa.

## Retención

La retención ficticia en Colombia usa ofertas de continuidad, atención prioritaria por congestión y campañas educativas sobre promociones. Si el cliente reporta problemas repetidos durante los primeros 60 días, se abre un caso preventivo.

## Identificadores operativos ficticios

El código BOCAPP-4821 representa un flujo ficticio de la aplicación Colombia donde el cliente no completa la validación de beneficios. El plan PLAN-POST-500 también existe en Colombia, pero se evalúa dentro de una ventana de Early Churn de 60 días. El incidente INC-93821 se usa aquí como referencia regional para abandono rápido por congestión y reclamos.

El error ORA-03150 puede mencionarse en reportes importados, pero en Colombia se interpreta como una alerta técnica secundaria. La descripción semántica equivalente es: usuarios recientes dejan la compañía porque el servicio inicial no coincide con la expectativa de activación.
