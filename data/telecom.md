# Telecom Demo

> Documento ficticio para un laboratorio educativo de RAG. Ningún dato, ciudad, regla, producto o métrica representa a una empresa real.

Telecom Demo es una empresa ficticia de telecomunicaciones creada para estudiar cómo un sistema RAG procesa documentos internos. La compañía ofrece servicios móviles y de conectividad hogareña en un mercado imaginario. Su información se organiza en áreas simples para que pueda ser leída, dividida en fragmentos y recuperada más adelante mediante búsqueda semántica.

El objetivo de este documento no es describir una operación real, sino servir como pequeña base de conocimiento controlada. Por eso incluye definiciones, reglas inventadas, ejemplos y datos sintéticos que nos permitirán hacer preguntas y verificar si el sistema recupera el contexto correcto.

## Clientes

Telecom Demo clasifica sus clientes en tres grandes grupos: prepago, pospago y hogar.

Los clientes prepago compran paquetes de datos, voz o mensajes antes de utilizarlos. En este escenario ficticio, suelen hacer recargas pequeñas varias veces al mes. Algunos clientes prepago usan el servicio principalmente para mensajería y redes sociales, mientras que otros compran paquetes de navegación por día cuando necesitan conectividad puntual.

Los clientes pospago tienen un abono mensual. Pagan una factura al final de cada ciclo y pueden tener beneficios adicionales, como datos acumulables, atención prioritaria o descuentos en equipos. Para este laboratorio, se supone que un cliente pospago puede tener líneas adicionales asociadas a un mismo titular.

Los clientes hogar contratan servicios de internet fijo, televisión digital o telefonía residencial. En Telecom Demo, los clientes hogar pueden vivir en zonas con distintas tecnologías de acceso, como fibra ficticia, radioenlace ficticio o cobre heredado ficticio. Estas tecnologías se mencionan solo para fines de prueba.

La empresa también usa etiquetas internas inventadas. Por ejemplo, un cliente puede tener la etiqueta "alto consumo" si supera los 80 GB mensuales de datos móviles, o la etiqueta "baja interacción" si no abre la aplicación de autogestión durante 60 días. Estas etiquetas no tienen valor fuera de este documento.

## Early Churn

Early Churn significa, en este documento ficticio, que un cliente abandona o deja de usar activamente el servicio durante los primeros 90 días desde el alta. La definición exacta depende del tipo de cliente.

Para clientes prepago, se considera Early Churn si el cliente no realiza ninguna recarga durante los primeros 45 días posteriores a la activación de la línea. También se marca como posible riesgo si el cliente consume menos del 10% del paquete inicial y no vuelve a comprar otro paquete.

Para clientes pospago, se considera Early Churn si el cliente solicita la baja antes de cumplir tres facturas emitidas. Una regla ficticia adicional indica que dos reclamos técnicos en el primer mes aumentan el nivel de riesgo de abandono temprano.

Para clientes hogar, se considera Early Churn si el servicio es cancelado antes de los 90 días o si la instalación queda incompleta durante más de 15 días. En este laboratorio, una instalación incompleta puede deberse a falta de agenda, problemas de cobertura o datos de domicilio incorrectos.

Ejemplo ficticio 1: Ana activa una línea prepago, usa el paquete de bienvenida durante dos días y luego no recarga en 50 días. Según la regla inventada, Ana entra en Early Churn prepago.

Ejemplo ficticio 2: Bruno contrata un plan pospago, recibe la primera factura, realiza tres reclamos por baja velocidad y solicita la baja al día 40. Según la regla inventada, Bruno entra en Early Churn pospago.

Ejemplo ficticio 3: Carla contrata internet hogar, pero la visita técnica se reprograma cuatro veces y la instalación no se completa en 18 días. Según la regla inventada, Carla queda marcada como riesgo de Early Churn hogar.

## Cobertura

Telecom Demo opera en ciudades ficticias llamadas Puerto Norte, Sierra Azul, Valle Claro y Costa Verde. Cada ciudad tiene condiciones de cobertura distintas, también inventadas para este ejercicio.

En Puerto Norte existe una red móvil ficticia 5G-Demo en el centro urbano y cobertura 4G-Demo en barrios periféricos. La fibra hogareña ficticia está disponible en edificios de más de ocho pisos y en algunos corredores comerciales.

En Sierra Azul predomina una tecnología llamada RadioLink Demo para hogares alejados. La cobertura móvil es estable en zonas céntricas, pero puede degradarse en rutas de montaña. Este dato nos servirá luego para probar preguntas sobre disponibilidad por ciudad.

En Valle Claro, la empresa ofrece internet hogar mediante Fibra Demo y Cobre Demo. La red móvil tiene buena capacidad durante la mañana, pero presenta congestión ficticia entre las 19:00 y las 22:00.

En Costa Verde, la cobertura se concentra en zonas turísticas. Durante la temporada alta ficticia, la demanda de datos móviles aumenta un 60%. La empresa aplica refuerzos temporales de capacidad usando antenas móviles imaginarias.

## Ventas

Telecom Demo vende sus productos mediante canales ficticios: tiendas propias, distribuidores autorizados, venta telefónica, sitio web y aplicación móvil.

Las tiendas propias atienden consultas complejas, cambios de equipo y altas de planes pospago. Los distribuidores autorizados se enfocan en líneas prepago y paquetes promocionales. La venta telefónica contacta a clientes existentes para ofrecer mejoras de plan o servicios hogar.

El sitio web permite contratar planes móviles y solicitar instalación de internet hogar. La aplicación móvil permite comprar paquetes, revisar consumo y recibir ofertas personalizadas inventadas. Para este documento, se supone que el canal digital tiene menor costo operativo que las tiendas físicas.

Dato ficticio: durante un mes de prueba, el 40% de las altas prepago ocurrió en distribuidores, el 25% en tiendas propias, el 20% en la aplicación móvil y el 15% en el sitio web. En pospago, las tiendas propias representaron el 45% de las altas y la venta telefónica el 30%.

## Retención

Telecom Demo usa estrategias ficticias de retención para reducir bajas y mejorar la experiencia de los clientes.

Caso ficticio extenso para probar recursive chunking: En una campaña imaginaria llamada Cuidado Inicial 90, Telecom Demo combina señales sintéticas de uso, reclamos, instalación y actividad digital para decidir qué clientes deberían recibir seguimiento durante sus primeras semanas. La campaña no existe fuera de este laboratorio y todos sus indicadores son inventados, pero el párrafo es deliberadamente largo para mostrar qué ocurre cuando una unidad semántica supera el tamaño máximo de chunk. El equipo ficticio observa si el cliente realizó su primera recarga, si abrió la aplicación de autogestión, si recibió mensajes de bienvenida, si tuvo problemas de cobertura, si registró reclamos técnicos, si la instalación hogar fue reprogramada, si la factura inicial generó dudas y si el canal de venta dejó notas incompletas. Cuando varias señales aparecen juntas, el caso se marca como prioritario y se asigna a una cola manual de revisión, aunque esa cola también es ficticia. Un ejemplo inventado sería una persona que compra una línea pospago en Puerto Norte, reclama por velocidad durante la primera semana, no entiende la factura proporcional, no activa la aplicación y además vive en una zona donde la cobertura 5G-Demo cambia entre barrios cercanos. Otro ejemplo inventado sería un hogar de Sierra Azul cuya instalación por RadioLink Demo queda pendiente por clima, agenda técnica y validación de domicilio, lo que podría generar frustración antes de que el servicio empiece a funcionar. La campaña intenta distinguir entre abandono real, demora operativa y simple falta de información, porque cada caso requeriría una respuesta distinta. Este texto largo fue agregado únicamente para provocar un párrafo de más de mil caracteres y permitir observar cómo el algoritmo baja de párrafos a oraciones sin cortar inmediatamente por caracteres.

Para clientes prepago con riesgo de Early Churn, la empresa puede enviar un bono de datos de bienvenida si detecta que no hubo recarga en los primeros 20 días. También puede enviar mensajes educativos sobre cómo consultar saldo, comprar paquetes y usar la aplicación.

Para clientes pospago, una estrategia inventada consiste en llamar al cliente después del primer reclamo técnico para confirmar si el problema fue resuelto. Si el cliente tuvo más de un reclamo en el primer mes, puede recibir atención prioritaria durante 30 días.

Para clientes hogar, la retención se enfoca en la instalación y en los primeros días de uso. Si la instalación se demora más de 10 días, el sistema ficticio genera una alerta para seguimiento manual. Si el cliente reporta baja velocidad durante la primera semana, se programa una revisión técnica preventiva.

Otra estrategia ficticia es la oferta de combinación de servicios. Un cliente móvil pospago puede recibir descuento si agrega internet hogar, y un cliente hogar puede recibir una línea móvil secundaria con bonificación temporal. Estas reglas son inventadas y solo existen para probar recuperación de información.

El equipo de retención mide indicadores sintéticos como tasa de contacto exitoso, porcentaje de casos resueltos y reducción ficticia de Early Churn. Estos indicadores se usarán más adelante para formular preguntas y evaluar si el sistema RAG encuentra los fragmentos relevantes del documento.
