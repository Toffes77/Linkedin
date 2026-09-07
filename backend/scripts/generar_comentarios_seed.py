"""Agrega comentarios realistas y respuestas a las publicaciones existentes.

Uso desde la raiz del repositorio:

    python backend/scripts/generar_comentarios_seed.py --dry-run
    python backend/scripts/generar_comentarios_seed.py --apply

El seed es transaccional e idempotente por publicacion, autor, texto y padre.
Solo opera contra la base local ``Linkedin`` en entorno ``development``.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

import src.app  # noqa: E402,F401 - registra todos los modelos relacionados
from sqlalchemy import text  # noqa: E402

from src.db.connection import SessionLocal  # noqa: E402
from src.db.models.comentario_model import Comentario  # noqa: E402
from src.db.models.publicacion_model import Publicacion  # noqa: E402
from src.db.models.usuario_model import Usuario  # noqa: E402
from src.dtos.comentario_dto import GuardarComentarioDTO  # noqa: E402
from src.mappers.comentario_mapper import ComentarioMapper  # noqa: E402
from src.utils.datetime_utils import utc_now  # noqa: E402


DOMAIN_TABLES = (
    "comentario",
    "conexiones",
    "conversacion",
    "conversacion_usuario",
    "empresa",
    "empresa_usuario",
    "experiencia",
    "mensaje",
    "notificacion",
    "oferta",
    "postulacion",
    "promocion",
    "publicacion",
    "reacciones",
    "seguimiento",
    "solicitud_contratacion_promocion",
    "usuario",
)


@dataclass(frozen=True)
class ReplySpec:
    author: str
    text: str


@dataclass(frozen=True)
class RootSpec:
    author: str
    text: str
    replies: tuple[ReplySpec, ...] = ()


@dataclass(frozen=True)
class PostSpec:
    author: str
    text_start: str
    roots: tuple[RootSpec, ...]


def reply(author: str, content: str) -> ReplySpec:
    return ReplySpec(author=author, text=content)


def root(author: str, content: str, *replies: ReplySpec) -> RootSpec:
    return RootSpec(author=author, text=content, replies=tuple(replies))


# Dataset explicito: la eleccion de autores y textos no depende de aleatoriedad.
POSTS: dict[int, PostSpec] = {
    1: PostSpec(
        "Santín Ben-Konka",
        "Tomar decisiones financieras informadas",
        (
            root(
                "Franco Ghirardi",
                "La transparencia suma mucho cuando también se explican el riesgo y el horizonte de cada alternativa. Un simulador con escenarios adversos ayudaría a convertir estos informes en decisiones más concretas.",
                reply(
                    "Gael Ponce",
                    "Un simulador así podría mostrar sensibilidad a tasas e inflación sin ocultar los supuestos. La clave sería que el usuario entienda por qué cambia cada resultado.",
                ),
            ),
            root(
                "Luca Di Lauro",
                "¿Las capacitaciones contemplan herramientas específicas para comercios pequeños? Muchas pymes necesitan ordenar primero su flujo de caja antes de pensar en invertir excedentes.",
            ),
            root(
                "Manuel Valle",
                "Me parece valioso unir educación e información de mercado. Para una pyme, entender costos financieros y liquidez puede ser tan importante como vender más.",
            ),
        ),
    ),
    2: PostSpec(
        "Ignacio Labonia",
        "Maximiza la vida útil de tus equipos",
        (
            root(
                "Juan Cruz Maletti",
                "El mantenimiento preventivo suele rendir mucho más que reemplazar componentes por calendario. Estaría bueno conocer si también miden temperatura, ventilación y degradación bajo carga.",
                reply(
                    "Fernando Mayer",
                    "Sumaría consumo y estabilidad de la fuente a esas mediciones. Muchas fallas que parecen del procesador empiezan por alimentación o disipación deficientes.",
                ),
            ),
            root(
                "Gael Ponce",
                "Un historial de diagnósticos por equipo permitiría anticipar fallas repetitivas. Incluso con reglas simples se puede priorizar qué máquinas revisar antes de que afecten la operación.",
            ),
        ),
    ),
    3: PostSpec(
        "Joaquin Gambeta",
        "La consulta a tiempo transforma diagnósticos",
        (
            root(
                "Ignacio Libermann",
                "La prevención también depende de construir un espacio donde la persona pueda preguntar sin vergüenza. La combinación de claridad clínica y trato respetuoso cambia por completo la consulta temprana.",
            ),
        ),
    ),
    4: PostSpec(
        "Binyamin Al-Ghomiz",
        "La tradición técnica y la innovación",
        (
            root(
                "Juan Cruz Maletti",
                "En procesos de esta escala, innovar debería ir acompañado de trazabilidad sobre cada parámetro crítico. Esa disciplina es la que vuelve repetible una mejora técnica.",
            ),
            root(
                "Ighnas Al-Mutto",
                "¿Cómo evalúan el retorno de incorporar nueva tecnología cuando el principal beneficio es reducir riesgo operativo? Es un valor enorme, aunque no siempre aparezca de forma directa en la producción.",
                reply(
                    "Lorenzo Diaz",
                    "También hay retorno en la continuidad de operación. Mejor telemetría y comunicación remota reducen tiempos de respuesta cuando aparece una desviación.",
                ),
            ),
            root(
                "Fernando Mayer",
                "La modernización de controles tiene sentido si conserva redundancias independientes. En entornos críticos, automatizar nunca debería significar depender de una única lectura.",
            ),
            root(
                "Andrew Wilson",
                "Además de la mejora técnica, comunicar procedimientos y límites con claridad ayuda a generar confianza en los equipos y en las comunidades cercanas.",
            ),
        ),
    ),
    5: PostSpec(
        "Luca Di Lauro",
        "El capital de trabajo no tiene por qué",
        (
            root(
                "Franco Ghirardi",
                "La agilidad es útil siempre que el costo total y los criterios de riesgo sean visibles desde el inicio. Esa claridad evita que una solución de corto plazo se convierta en un problema financiero.",
                reply(
                    "Manuel Valle",
                    "Totalmente. Para una pyme es clave poder comparar la cuota con el ciclo real de cobro, no solamente mirar la velocidad de aprobación.",
                ),
            ),
            root(
                "Manuel Valle",
                "¿Tienen alternativas con cronogramas adaptados a negocios estacionales? Hay proyectos sanos cuyo flujo no encaja bien en cuotas idénticas todos los meses.",
            ),
        ),
    ),
    6: PostSpec(
        "Jacques-Antoine Lacroix",
        "📢 ¡Presentamos la nueva temporada de Back To School!",
        (
            root(
                "Benjamin Jerez",
                "La variedad de líneas mantiene una identidad común sin hacer que todos los productos se vean iguales. Neón y Picnik parecen tener públicos muy distintos, y eso le da aire a la campaña.",
                reply(
                    "Romain Lacroix",
                    "Esa diferenciación fue importante: cada línea necesitaba personalidad propia, pero debía seguir reconociéndose como parte de la misma propuesta de vuelta a clases.",
                ),
                reply(
                    "Gael Ponce",
                    "También ayuda a medir la respuesta por segmento. Con categorías tan claras se puede aprender qué diseño funciona mejor para cada edad y contexto de uso.",
                ),
            ),
            root(
                "Fernando Mayer",
                "Las reglas y escuadras resistentes a torsión me llamaron la atención. Es un problema cotidiano muy concreto y fácil de comprobar por quienes llevan todo junto en la mochila.",
            ),
            root(
                "Romain Lacroix",
                "Kidy Learn Concentration es una buena muestra de diseño aplicado: no se trata de sumar textura porque sí, sino de responder a una necesidad durante el aprendizaje.",
                reply(
                    "Fernando Mayer",
                    "Ese criterio de diseño se nota cuando la función sensorial no interfiere con la precisión de la herramienta. Sería interesante ver pruebas de uso prolongado en aula.",
                ),
            ),
            root(
                "Ignacio Labonia",
                "El showroom parece haber ordenado muy bien lanzamientos, clásicos y públicos. Para los equipos comerciales, ver el portfolio completo facilita contar una historia más consistente.",
            ),
            root(
                "Juan Cruz Moyano",
                "Más de sesenta novedades exigen una coordinación importante entre abastecimiento, exhibición y comunicación. El desafío será sostener disponibilidad durante el pico de la temporada.",
            ),
        ),
    ),
    7: PostSpec(
        "Alexandre Bompard",
        "¡Celebramos 43 años de la relación Precio-Calidad!",
        (
            root(
                "Manfred Paulmann",
                "Sostener durante décadas una promesa de precio y calidad requiere mucha consistencia operativa. La confianza se construye cuando esa relación se percibe en cada visita, no solo en una campaña.",
            ),
            root(
                "Juan Cruz Moyano",
                "Cuarenta y tres años convierten la propuesta en parte de la memoria de varias generaciones. ¿Cómo actualizaron el lenguaje sin perder ese reconocimiento histórico?",
                reply(
                    "Benjamin Jerez",
                    "Probablemente ayudó conservar los códigos más reconocibles y renovar el ritmo de la comunicación. La nostalgia funciona mejor cuando acompaña una experiencia actual.",
                ),
            ),
            root(
                "Lucas Estevo",
                "Cuando la promesa es simple, el cliente detecta rápido si se cumple. Esa claridad también facilita que quienes atienden puedan explicar diferencias entre opciones sin vueltas.",
            ),
        ),
    ),
    8: PostSpec(
        "Manfred Paulmann",
        "Celebramos un nuevo año de logros junto a Fundación Pescar",
        (
            root(
                "Agustin Pelachini",
                "La formación para el empleo tiene mucho más impacto cuando incluye práctica real y habilidades para trabajar en equipo. En operaciones de atención, esa primera experiencia hace una diferencia enorme.",
                reply(
                    "Manuel Valle",
                    "Y permite que cada joven llegue a una entrevista con ejemplos concretos de lo que hizo. Esa evidencia suele pesar más que una capacitación puramente teórica.",
                ),
            ),
            root(
                "Manuel Valle",
                "El 80% de inserción es un indicador fuerte. Sería interesante conocer el seguimiento a seis y doce meses para medir continuidad y crecimiento, además del primer empleo.",
            ),
            root(
                "Franco Ghirardi",
                "Que una parte continúe estudiando mientras se incorpora al mercado laboral también es un buen resultado. Combinar ambos caminos mejora la empleabilidad futura.",
            ),
            root(
                "Lucas Estevo",
                "Las prácticas en tienda ayudan a entender ritmos, prioridades y trato con clientes de una manera que no se aprende solamente en clase. Felicitaciones a quienes completaron el programa.",
            ),
        ),
    ),
    9: PostSpec(
        "Andy Jassy",
        "⚡ ÚLTIMO MOMENTO: Amazon Web Services",
        (
            root(
                "Gael Ponce",
                "La ampliación entre AWS y NVIDIA puede bajar bastante la barrera para entrenar y desplegar modelos grandes. El desafío seguirá siendo aprovechar el hardware sin disparar costos por cargas mal optimizadas.",
            ),
            root(
                "Lorenzo Diaz",
                "La infraestructura distribuida va a necesitar redes con latencia y capacidad previsibles. La inversión en cómputo pierde valor si la conectividad entre regiones no acompaña.",
                reply(
                    "Gael Ponce",
                    "Exacto. En inferencia en tiempo real, mover datos puede costar más que calcular. Diseñar bien la ubicación de cada carga será tan importante como elegir aceleradores.",
                ),
            ),
        ),
    ),
    10: PostSpec(
        "Henrique Braun",
        "En el país que queremos, la calidad",
        (
            root(
                "Juan Cruz Moyano",
                "La calidad funciona cuando deja de ser responsabilidad de un área aislada y se vuelve criterio cotidiano en toda la cadena. Ese compromiso compartido es lo más difícil de sostener.",
                reply(
                    "Binyamin Al-Ghomiz",
                    "En procesos industriales se nota enseguida: un control final no compensa una desviación que se dejó avanzar durante varias etapas. La prevención tiene que estar integrada.",
                ),
            ),
            root(
                "Benjamin Jerez",
                "Me gusta que la comunicación muestre a quienes sostienen el proceso. Humaniza una idea técnica sin convertir la calidad en una frase publicitaria vacía.",
            ),
            root(
                "Manuel Valle",
                "La trazabilidad con proveedores pequeños también es clave. Cuando los estándares están explicados y medidos, toda la red puede mejorar sin depender de controles improvisados.",
            ),
        ),
    ),
    11: PostSpec(
        "Agustin Pelachini",
        "Estoy en la búsqueda de mi próxima oportunidad",
        (),
    ),
    12: PostSpec(
        "Benjamin Jerez",
        "Detrás de la tapa amarilla",
        (
            root(
                "Ignacio Labonia",
                "Reducir el mensaje a tres segundos obliga a decidir qué hace reconocible a la marca de verdad. La tapa amarilla y el uso cotidiano parecen haber hecho mucho del trabajo sin sobrecargar la pieza.",
            ),
            root(
                "Juan Cruz Moyano",
                "El aumento de ventas es contundente, pero también me interesa la mejora en conversión. ¿Pudieron separar cuánto vino de captar usuarios nuevos y cuánto de reactivar compradores históricos?",
                reply(
                    "Franco Ghirardi",
                    "Esa apertura sería muy útil para proyectar recurrencia. Una campaña puede vender mucho una vez, pero el valor cambia si además incorpora consumidores que repiten.",
                ),
            ),
            root(
                "Jacques-Antoine Lacroix",
                "Actualizar un producto escolar icónico sin borrar su memoria es un equilibrio delicado. La decisión de mostrar el uso real acerca la marca a quienes hoy la tienen en la cartuchera.",
            ),
            root(
                "Gael Ponce",
                "Con mensajes tan breves, las pruebas A/B sobre primer cuadro, color y demostración de uso pueden revelar mucho. Pequeños cambios probablemente expliquen buena parte de la conversión.",
            ),
        ),
    ),
    13: PostSpec(
        "Binyamin Al-Ghomiz",
        "La gente cree que mi trabajo es romper cosas",
        (
            root(
                "Juan Cruz Maletti",
                "Lo impresionante es que el resultado visible dura segundos, mientras el verdadero trabajo está en el cálculo previo. Esa combinación de precisión, materiales y seguridad define toda la operación.",
            ),
            root(
                "Fernando Mayer",
                "¿Qué instrumentación usan para confirmar vibraciones y tiempos después de cada voladura? Comparar la medición real con el modelo debe aportar muchísimo para ajustar el siguiente diseño.",
                reply(
                    "Gael Ponce",
                    "Con una serie histórica de sensores también se podrían detectar desviaciones pequeñas antes de que sean evidentes. Siempre dejando la decisión final en el equipo especializado.",
                ),
            ),
            root(
                "Ighnas Al-Mutto",
                "La seguridad suele verse como costo hasta que se calcula el impacto de una parada o un incidente. En una actividad así, invertir en planificación es parte central del rendimiento.",
            ),
        ),
    ),
    14: PostSpec(
        "Ignacio Libermann",
        "Dirigir un proyecto enfocado en la salud felina",
        (
            root(
                "Joaquin Gambeta",
                "La excelencia clínica y la confianza del paciente —o de quien lo acompaña— no se pueden separar. La continuidad del seguimiento también ayuda a detectar cambios antes de que se vuelvan urgentes.",
                reply(
                    "Franco Bosseti",
                    "Un entorno tranquilo suma mucho en ese seguimiento. Reducir estrés facilita tanto la evaluación profesional como la experiencia de quienes llevan al animal.",
                ),
            ),
            root(
                "Manuel Valle",
                "El desafío de sostener el impacto sin descuidar la operación es muy real. Protocolos claros para insumos y turnos pueden liberar tiempo del equipo para la atención especializada.",
            ),
        ),
    ),
    15: PostSpec(
        "Joaquin Gambeta",
        "Entiendo la medicina desde la rigurosidad técnica",
        (
            root(
                "Ignacio Libermann",
                "La escucha activa es parte de un buen diagnóstico, especialmente cuando existen temores que demoran la consulta. Explicar cada paso con claridad puede cambiar la relación con la prevención.",
            ),
        ),
    ),
    16: PostSpec(
        "Juan Cruz Maletti",
        "Mi pasión es transformar desafíos técnicos",
        (
            root(
                "Fernando Mayer",
                "En sistemas electromecánicos, validar interfaces suele evitar más fallas que optimizar cada componente por separado. Simulación y ensayo físico tienen que conversar desde el principio.",
            ),
            root(
                "Gael Ponce",
                "El mantenimiento predictivo puede complementar muy bien ese enfoque. Con señales confiables de vibración y temperatura es posible priorizar intervenciones sin reemplazar el criterio de ingeniería.",
                reply(
                    "Andrew Wilson",
                    "Y la adopción mejora cuando esos indicadores se traducen en decisiones simples para el equipo operativo. Una herramienta útil tiene que explicar qué requiere atención y por qué.",
                ),
            ),
            root(
                "Lorenzo Diaz",
                "El monitoreo remoto agrega valor cuando la conectividad fue pensada como parte del sistema y no como un accesorio posterior. También exige definir bien qué ocurre si se pierde el enlace.",
            ),
            root(
                "Ignacio Labonia",
                "Los mejores prototipos aparecen cuando diseño, fabricación y usuario final participan temprano. Eso reduce iteraciones costosas y evita resolver un problema distinto al real.",
            ),
            root(
                "Binyamin Al-Ghomiz",
                "Optimizar rendimiento sin comerse los márgenes de seguridad es el equilibrio importante. Documentar cada supuesto vuelve mucho más sólida la mejora continua.",
            ),
        ),
    ),
    17: PostSpec(
        "Juan Cruz Moyano",
        "Liderar una organización implica definir",
        (
            root(
                "Manuel Valle",
                "La estrategia se vuelve real cuando cada equipo entiende qué decisión cotidiana cambia. Pocos indicadores bien elegidos suelen alinear mejor que una lista interminable de objetivos.",
            ),
            root(
                "Franco Ghirardi",
                "Además de resultados operativos, la asignación de capital muestra con claridad cuáles son las prioridades verdaderas. Presupuesto y visión tienen que contar la misma historia.",
            ),
        ),
    ),
    18: PostSpec(
        "Lorenzo Diaz",
        "Invierto y desarrollo iniciativas",
        (
            root(
                "Andy Jassy",
                "Escalar conectividad exige diseñar resiliencia desde el comienzo. La capacidad importa, pero la recuperación ante fallas es lo que sostiene servicios críticos cuando crece la demanda.",
                reply(
                    "Gael Ponce",
                    "La inteligencia en el borde también puede ayudar a mantener funciones básicas durante una desconexión. Después, la sincronización debe resolver conflictos sin perder trazabilidad.",
                ),
            ),
            root(
                "Gael Ponce",
                "Las redes definidas por software permiten adaptar capacidad con más velocidad, aunque necesitan observabilidad seria. Automatizar sin buenas métricas solo acelera errores.",
            ),
            root(
                "Juan Cruz Maletti",
                "La expansión física debería contemplar acceso y mantenimiento desde el diseño. Una infraestructura difícil de inspeccionar termina pagando ese costo durante toda su vida útil.",
            ),
        ),
    ),
    19: PostSpec(
        "Luca Di Lauro",
        "Facilitar el acceso al capital",
        (),
    ),
    20: PostSpec(
        "Lucas Estevo",
        "Entiendo la venta de un vehículo",
        (
            root(
                "Juan Cruz Moyano",
                "La experiencia no termina con la entrega. Un seguimiento breve y bien coordinado puede detectar dudas temprano y convertir una venta correcta en una relación de largo plazo.",
            ),
            root(
                "Manuel Valle",
                "Mapear cada traspaso entre asesoramiento, financiación, documentación y postventa evita que el cliente tenga que repetir información. Ahí suele perderse mucha confianza.",
            ),
            root(
                "Fernando Mayer",
                "Con vehículos eléctricos aparece además la necesidad de explicar autonomía, carga y condiciones de uso sin simplificaciones engañosas. El asesoramiento técnico va a pesar cada vez más.",
                reply(
                    "Andrew Wilson",
                    "Una demostración práctica puede ayudar mucho más que una ficha extensa. La gente necesita conectar esos datos técnicos con su rutina concreta.",
                ),
            ),
            root(
                "Benjamin Jerez",
                "Presentar pocas opciones bien justificadas suele ser más claro que mostrar todo el catálogo. Especialmente cuando financiación y versiones agregan muchas variables a la decisión.",
            ),
        ),
    ),
    21: PostSpec(
        "Manuel Valle",
        "Ayudo a las pequeñas y medianas empresas",
        (
            root(
                "Franco Ghirardi",
                "Antes de escalar conviene entender qué parte del crecimiento consume caja y cuál realmente mejora margen. Facturar más no siempre fortalece a la empresa si el capital de trabajo queda desordenado.",
                reply(
                    "Luca Di Lauro",
                    "Ese diagnóstico también permite financiar una necesidad concreta en lugar de cubrir déficits recurrentes. Plazo y destino del crédito deberían acompañar el ciclo del negocio.",
                ),
            ),
            root(
                "Ignacio Labonia",
                "La reingeniería funciona mejor cuando quienes ejecutan el proceso participan del rediseño. Suelen conocer excepciones y atajos que nunca aparecen en un organigrama.",
            ),
        ),
    ),
    22: PostSpec(
        "Santín Ben-Konka",
        "La transformación digital ha redefinido",
        (
            root(
                "Gael Ponce",
                "La IA puede ayudar a detectar fraude y priorizar alertas, pero necesita explicabilidad y revisión humana. En banca no alcanza con que el modelo acierte; también hay que justificar decisiones.",
            ),
            root(
                "Franco Ghirardi",
                "El equilibrio difícil está entre controles sólidos y una experiencia que no castigue al cliente legítimo. Medir falsos positivos debería ser tan importante como medir incidentes evitados.",
                reply(
                    "Agustin Pelachini",
                    "Cada falso positivo termina también en una conversación de soporte. Si atención recibe contexto claro, puede resolver más rápido sin debilitar el control.",
                ),
            ),
            root(
                "Agustin Pelachini",
                "Modernizar canales sin dejar atrás a quienes necesitan asistencia humana es fundamental. Una buena transición digital debería ofrecer ayuda justo cuando aparece la fricción.",
            ),
        ),
    ),
    23: PostSpec(
        "Fernando Mayer",
        "¡Oficialmente Ingeniero Eléctrico!",
        (
            root(
                "Juan Cruz Maletti",
                "¡Felicitaciones, Fernando! La mirada eléctrica y la mecánica se cruzan en casi cualquier sistema industrial; seguro se vienen proyectos interesantes para compartir.",
            ),
            root(
                "Lorenzo Diaz",
                "Gran logro. La convergencia entre energía y telecomunicaciones está abriendo desafíos enormes en redes, monitoreo y operación remota.",
            ),
            root(
                "Gael Ponce",
                "Felicitaciones. Las redes eléctricas inteligentes necesitan cada vez más profesionales capaces de combinar fundamentos sólidos con datos y automatización.",
                reply(
                    "Andrew Wilson",
                    "Esa combinación técnica también abre oportunidades en productos interactivos y simulación. Una base fuerte permite moverse entre industrias muy distintas.",
                ),
            ),
            root(
                "Binyamin Al-Ghomiz",
                "¡Enorme cierre de etapa! En campo se aprecia mucho a quien entiende tanto el cálculo como los procedimientos de seguridad y puesta en marcha.",
            ),
            root(
                "Agustin Pelachini",
                "Felicitaciones por el título y por reconocer a quienes acompañaron el proceso. Que sea el comienzo de una etapa profesional llena de buenos desafíos.",
            ),
        ),
    ),
    24: PostSpec(
        "Franco Ghirardi",
        "Saber de finanzas para dirigir un banco",
        (
            root(
                "Santín Ben-Konka",
                "Hoy pondría la gestión de liquidez muy arriba, pero acompañada por gobierno de datos. Una decisión rápida solo es buena si parte de información confiable y responsabilidades claras.",
            ),
        ),
    ),
    25: PostSpec(
        "Gael Ponce",
        "Si querés que la Inteligencia Artificial",
        (
            root(
                "Sam Altman",
                "Separar una tarea compleja en etapas suele ser la mejora más subestimada. Además de reducir errores, permite revisar el razonamiento intermedio antes de producir la versión final.",
                reply(
                    "Lorenzo Diaz",
                    "Y facilita detectar en qué etapa faltó contexto. Es mucho más simple corregir una extracción concreta que volver a ejecutar un proceso entero sin saber dónde falló.",
                ),
            ),
            root(
                "Juan Cruz Maletti",
                "En ingeniería sirve mucho pedir primero supuestos, restricciones y criterios de aceptación. Recién después conviene solicitar alternativas o cálculos; así las respuestas son más auditables.",
            ),
            root(
                "Franco Ghirardi",
                "La regla de limitarse a las fuentes provistas es indispensable cuando se trabaja con cifras. También pediría que distinga claramente dato, supuesto e interpretación.",
            ),
            root(
                "Ignacio Labonia",
                "Los ejemplos son especialmente útiles para sostener tono y estructura de marca. Conviene mostrar también un contraejemplo para dejar claro qué resultado no se quiere.",
            ),
        ),
    ),
}


def assert_safe_database(db) -> dict[str, object]:
    from src.config.env import settings

    configured = urlparse(settings.DATABASE_URL)
    if settings.ENVIRONMENT.casefold() != "development":
        raise RuntimeError("Seed abortado: ENVIRONMENT no es development")
    if configured.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Seed abortado: DATABASE_URL no apunta a loopback")
    if configured.path.lstrip("/") != "Linkedin":
        raise RuntimeError("Seed abortado: DATABASE_URL no apunta a Linkedin")

    database, address, port = db.execute(
        text("SELECT current_database(), inet_server_addr()::text, inet_server_port()")
    ).one()
    if database != "Linkedin" or not ipaddress.ip_interface(address).ip.is_loopback:
        raise RuntimeError("Seed abortado: PostgreSQL efectivo no es Linkedin local")
    return {
        "database": database,
        "server_address": address,
        "server_port": port,
        "environment": settings.ENVIRONMENT,
    }


def table_counts(db) -> dict[str, int]:
    return {
        table_name: db.execute(
            text(f'SELECT count(*) FROM public."{table_name}"')
        ).scalar_one()
        for table_name in DOMAIN_TABLES
    }


def other_table_fingerprints(db) -> dict[str, str]:
    result: dict[str, str] = {}
    for table_name in DOMAIN_TABLES:
        if table_name == "comentario":
            continue
        rows = db.execute(
            text(
                f'SELECT row_to_json(item)::text FROM public."{table_name}" AS item '
                "ORDER BY row_to_json(item)::text"
            )
        ).scalars()
        digest = hashlib.sha256()
        for row in rows:
            digest.update(row.encode("utf-8"))
            digest.update(b"\n")
        result[table_name] = digest.hexdigest()
    return result


def existing_comment_snapshot(db) -> dict[int, tuple[object, ...]]:
    return {
        row.id: (
            row.publicacion_id,
            row.usuario_id,
            row.contenido,
            row.fecha,
            row.comentario_padre_id,
        )
        for row in db.query(Comentario).order_by(Comentario.id)
    }


def validate_manifest(db) -> tuple[dict[int, Publicacion], dict[str, Usuario]]:
    publications = {item.id: item for item in db.query(Publicacion).order_by(Publicacion.id)}
    users = db.query(Usuario).order_by(Usuario.id).all()
    users_by_name = {user.nombre: user for user in users}
    if len(users_by_name) != len(users):
        raise RuntimeError("Hay nombres de usuario duplicados; el seed no puede resolver autores")
    if set(publications) != set(POSTS):
        raise RuntimeError(
            f"Se esperaban publicaciones {sorted(POSTS)} y existen {sorted(publications)}"
        )

    root_counts = Counter(len(spec.roots) for spec in POSTS.values())
    if set(root_counts) != set(range(6)):
        raise RuntimeError("La distribucion debe incluir publicaciones con 0, 1, 2, 3, 4 y 5 raices")

    for publication_id, spec in POSTS.items():
        publication = publications[publication_id]
        if publication.autor.nombre != spec.author:
            raise RuntimeError(f"Autor inesperado en publicacion {publication_id}")
        if not publication.texto.startswith(spec.text_start):
            raise RuntimeError(f"Texto inesperado en publicacion {publication_id}")
        if not 0 <= len(spec.roots) <= 5:
            raise RuntimeError(f"Cantidad de raices invalida en publicacion {publication_id}")

        for root_spec in spec.roots:
            author = users_by_name.get(root_spec.author)
            if author is None:
                raise RuntimeError(f"Comentarista inexistente: {root_spec.author}")
            if author.id == publication.autor_id:
                raise RuntimeError(f"Autocomentario prohibido en publicacion {publication_id}")
            _validate_content(root_spec.text)
            for reply_spec in root_spec.replies:
                reply_author = users_by_name.get(reply_spec.author)
                if reply_author is None:
                    raise RuntimeError(f"Autor de respuesta inexistente: {reply_spec.author}")
                if reply_author.id == publication.autor_id:
                    raise RuntimeError(f"Autor de publicacion responde en {publication_id}")
                if reply_author.id == author.id:
                    raise RuntimeError(f"Autor se responde a si mismo en {publication_id}")
                _validate_content(reply_spec.text)
    return publications, users_by_name


def _validate_content(content: str) -> None:
    if not content.strip() or content != content.strip():
        raise RuntimeError("Comentario vacio o con whitespace exterior")
    GuardarComentarioDTO(publicacion_id=1, usuario_id=1, contenido=content)


def find_exact(db, publication_id: int, user_id: int, content: str, parent_id):
    matches = (
        db.query(Comentario)
        .filter(
            Comentario.publicacion_id == publication_id,
            Comentario.usuario_id == user_id,
            Comentario.contenido == content,
            Comentario.comentario_padre_id == parent_id,
        )
        .order_by(Comentario.id)
        .all()
    )
    if len(matches) > 1:
        raise RuntimeError("Ya existen comentarios duplicados exactos")
    return matches[0] if matches else None


def dry_run_report(db, publications, users_by_name) -> dict[str, object]:
    posts: list[dict[str, object]] = []
    pending_roots = pending_replies = duplicate_roots = duplicate_replies = 0
    for publication_id, spec in POSTS.items():
        root_reports: list[dict[str, object]] = []
        for root_spec in spec.roots:
            root_author = users_by_name[root_spec.author]
            existing_root = find_exact(
                db, publication_id, root_author.id, root_spec.text, None
            )
            if existing_root is None:
                pending_roots += 1
            else:
                duplicate_roots += 1
            reply_reports = []
            for reply_spec in root_spec.replies:
                reply_author = users_by_name[reply_spec.author]
                existing_reply = (
                    find_exact(
                        db,
                        publication_id,
                        reply_author.id,
                        reply_spec.text,
                        existing_root.id,
                    )
                    if existing_root is not None
                    else None
                )
                if existing_reply is None:
                    pending_replies += 1
                else:
                    duplicate_replies += 1
                reply_reports.append(
                    {
                        "autor": reply_spec.author,
                        "texto": reply_spec.text,
                        "estado": "duplicada" if existing_reply else "lista_para_insertar",
                        "id": existing_reply.id if existing_reply else None,
                    }
                )
            root_reports.append(
                {
                    "autor": root_spec.author,
                    "texto": root_spec.text,
                    "estado": "duplicado" if existing_root else "listo_para_insertar",
                    "id": existing_root.id if existing_root else None,
                    "respuestas": reply_reports,
                }
            )
        posts.append(
            {
                "publicacion_id": publication_id,
                "autor_publicacion": spec.author,
                "texto_publicacion": publications[publication_id].texto,
                "comentarios_raiz": root_reports,
            }
        )
    return {
        "publicaciones": posts,
        "raices_definidas": sum(len(spec.roots) for spec in POSTS.values()),
        "respuestas_definidas": sum(
            len(root_spec.replies)
            for spec in POSTS.values()
            for root_spec in spec.roots
        ),
        "raices_pendientes": pending_roots,
        "respuestas_pendientes": pending_replies,
        "raices_duplicadas": duplicate_roots,
        "respuestas_duplicadas": duplicate_replies,
        "distribucion_raices": {
            str(count): sum(len(spec.roots) == count for spec in POSTS.values())
            for count in range(6)
        },
    }


def sql_verifications(db) -> dict[str, object]:
    values = {
        "autocomentarios_raiz": db.execute(
            text(
                "SELECT count(*) FROM comentario c JOIN publicacion p "
                "ON p.id=c.publicacion_id WHERE c.comentario_padre_id IS NULL "
                "AND c.usuario_id=p.autor_id"
            )
        ).scalar_one(),
        "autor_publicacion_en_respuestas": db.execute(
            text(
                "SELECT count(*) FROM comentario c JOIN publicacion p "
                "ON p.id=c.publicacion_id WHERE c.comentario_padre_id IS NOT NULL "
                "AND c.usuario_id=p.autor_id"
            )
        ).scalar_one(),
        "padres_inexistentes": db.execute(
            text(
                "SELECT count(*) FROM comentario c LEFT JOIN comentario padre "
                "ON padre.id=c.comentario_padre_id WHERE c.comentario_padre_id "
                "IS NOT NULL AND padre.id IS NULL"
            )
        ).scalar_one(),
        "padres_de_otra_publicacion": db.execute(
            text(
                "SELECT count(*) FROM comentario c JOIN comentario padre "
                "ON padre.id=c.comentario_padre_id "
                "WHERE c.publicacion_id<>padre.publicacion_id"
            )
        ).scalar_one(),
        "comentarios_antes_de_publicacion": db.execute(
            text(
                "SELECT count(*) FROM comentario c JOIN publicacion p "
                "ON p.id=c.publicacion_id WHERE c.fecha<p.fecha"
            )
        ).scalar_one(),
        "respuestas_antes_del_padre": db.execute(
            text(
                "SELECT count(*) FROM comentario c JOIN comentario padre "
                "ON padre.id=c.comentario_padre_id WHERE c.fecha<padre.fecha"
            )
        ).scalar_one(),
        "fechas_futuras": db.execute(
            text("SELECT count(*) FROM comentario WHERE fecha>now()")
        ).scalar_one(),
        "textos_vacios": db.execute(
            text("SELECT count(*) FROM comentario WHERE contenido !~ '[^[:space:]]'")
        ).scalar_one(),
        "publicaciones_con_cero_raices": db.execute(
            text(
                "SELECT count(*) FROM publicacion p WHERE NOT EXISTS "
                "(SELECT 1 FROM comentario c WHERE c.publicacion_id=p.id "
                "AND c.comentario_padre_id IS NULL)"
            )
        ).scalar_one(),
        "comentarios_con_respuestas": db.execute(
            text(
                "SELECT count(DISTINCT comentario_padre_id) FROM comentario "
                "WHERE comentario_padre_id IS NOT NULL"
            )
        ).scalar_one(),
        "maximo_raices_por_publicacion": db.execute(
            text(
                "SELECT COALESCE(max(cantidad),0) FROM (SELECT count(*) cantidad "
                "FROM comentario WHERE comentario_padre_id IS NULL "
                "GROUP BY publicacion_id) item"
            )
        ).scalar_one(),
    }
    zero_expected = {
        "autocomentarios_raiz",
        "autor_publicacion_en_respuestas",
        "padres_inexistentes",
        "padres_de_otra_publicacion",
        "comentarios_antes_de_publicacion",
        "respuestas_antes_del_padre",
        "fechas_futuras",
        "textos_vacios",
    }
    if any(values[key] for key in zero_expected):
        raise RuntimeError(f"Fallo una verificacion SQL: {values}")
    if values["publicaciones_con_cero_raices"] < 1:
        raise RuntimeError("Debe quedar al menos una publicacion sin comentarios")
    if values["comentarios_con_respuestas"] < 1:
        raise RuntimeError("Debe existir al menos un comentario con respuesta")
    if values["maximo_raices_por_publicacion"] > 5:
        raise RuntimeError("Una publicacion tiene mas de cinco comentarios raiz")
    return values


def apply_seed(db, publications, users_by_name) -> dict[str, object]:
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('atanes:comentarios-seed'))"))
    assert_safe_database(db)
    counts_before = table_counts(db)
    other_rows_before = other_table_fingerprints(db)
    comments_before = existing_comment_snapshot(db)

    created_roots: list[Comentario] = []
    created_replies: list[Comentario] = []
    duplicate_roots = duplicate_replies = 0
    for publication_id, spec in POSTS.items():
        publication = publications[publication_id]
        for root_index, root_spec in enumerate(spec.roots):
            root_author = users_by_name[root_spec.author]
            root_model = find_exact(
                db, publication_id, root_author.id, root_spec.text, None
            )
            desired_root_date = publication.fecha + timedelta(
                seconds=45 * (root_index + 1) + publication_id % 5
            )
            if root_model is None:
                root_model = ComentarioMapper.to_model(
                    GuardarComentarioDTO(
                        publicacion_id=publication_id,
                        usuario_id=root_author.id,
                        contenido=root_spec.text,
                    )
                )
                root_model.fecha = desired_root_date
                db.add(root_model)
                db.flush()
                created_roots.append(root_model)
            else:
                duplicate_roots += 1

            for reply_index, reply_spec in enumerate(root_spec.replies):
                reply_author = users_by_name[reply_spec.author]
                reply_model = find_exact(
                    db,
                    publication_id,
                    reply_author.id,
                    reply_spec.text,
                    root_model.id,
                )
                if reply_model is None:
                    reply_model = ComentarioMapper.to_model(
                        GuardarComentarioDTO(
                            publicacion_id=publication_id,
                            usuario_id=reply_author.id,
                            contenido=reply_spec.text,
                            comentario_padre_id=root_model.id,
                        )
                    )
                    reply_model.fecha = root_model.fecha + timedelta(
                        seconds=15 * (reply_index + 1)
                    )
                    db.add(reply_model)
                    db.flush()
                    created_replies.append(reply_model)
                else:
                    duplicate_replies += 1

    if any(model.fecha > utc_now() for model in created_roots + created_replies):
        raise RuntimeError("Las fechas deterministas producirian comentarios futuros")

    counts_after = table_counts(db)
    other_rows_after = other_table_fingerprints(db)
    for comment_id, original in comments_before.items():
        current = db.get(Comentario, comment_id)
        current_values = (
            current.publicacion_id,
            current.usuario_id,
            current.contenido,
            current.fecha,
            current.comentario_padre_id,
        )
        if current_values != original:
            raise RuntimeError(f"Se modifico el comentario preexistente {comment_id}")

    added = len(created_roots) + len(created_replies)
    if counts_after["comentario"] != counts_before["comentario"] + added:
        raise RuntimeError("El conteo de comentarios no aumento como se esperaba")
    if other_rows_after != other_rows_before:
        raise RuntimeError("Se modificaron datos ajenos a comentario")
    for table_name, count in counts_before.items():
        if table_name != "comentario" and counts_after[table_name] != count:
            raise RuntimeError(f"Cambio inesperado en {table_name}")

    checks = sql_verifications(db)
    created_ids = [model.id for model in created_roots + created_replies]
    db.commit()
    persisted = (
        db.query(Comentario).filter(Comentario.id.in_(created_ids)).count()
        if created_ids
        else 0
    )
    if persisted != added:
        raise RuntimeError("No se verificaron todas las filas persistidas")
    return {
        "raices_creadas": len(created_roots),
        "respuestas_creadas": len(created_replies),
        "filas_agregadas": added,
        "raices_omitidas_por_duplicado": duplicate_roots,
        "respuestas_omitidas_por_duplicado": duplicate_replies,
        "ids_creados": created_ids,
        "conteos_antes": counts_before,
        "conteos_despues": counts_after,
        "otras_tablas_sin_cambios": other_rows_after == other_rows_before,
        "comentarios_preexistentes_sin_cambios": True,
        "verificaciones_sql": checks,
        "filas_persistidas_verificadas": persisted,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        try:
            database = assert_safe_database(db)
            publications, users_by_name = validate_manifest(db)
            preview = dry_run_report(db, publications, users_by_name)
            output: dict[str, object] = {
                "mode": "dry-run" if args.dry_run else "apply",
                "database": database,
                "publicaciones_existentes": len(publications),
                "usuarios_existentes": len(users_by_name),
                "conteos_actuales": table_counts(db),
                "manifest": preview,
            }
            if args.dry_run:
                output["postgresql_modificado"] = False
            else:
                output["resultado"] = apply_seed(db, publications, users_by_name)
        except Exception:
            db.rollback()
            raise
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
