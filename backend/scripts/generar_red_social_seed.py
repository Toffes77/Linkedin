"""Genera una red social determinista sobre los usuarios existentes de Atanes.

Uso desde la raiz del repositorio:

    python backend/scripts/generar_red_social_seed.py --dry-run
    python backend/scripts/generar_red_social_seed.py --apply

La carga es transaccional, incremental e idempotente. Crea conexiones aceptadas,
seguimientos, chats y mensajes sin generar notificaciones. También elimina la
leyenda técnica del seed que una versión anterior dejó en ofertas visibles.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import sys
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

import src.app  # noqa: E402,F401
from sqlalchemy import text  # noqa: E402

from src.db.connection import SessionLocal  # noqa: E402
from src.db.models.conexiones_model import Conexion  # noqa: E402
from src.db.models.conversacion_model import (  # noqa: E402
    Conversacion,
    ConversacionUsuario,
    Mensaje,
)
from src.db.models.oferta_model import Oferta  # noqa: E402
from src.db.models.seguimiento_model import Seguimiento  # noqa: E402
from src.db.models.usuario_model import Usuario  # noqa: E402
from src.dtos.conexiones_dto import CreateConexionDTO  # noqa: E402
from src.mappers.conexion_mapper import ConexionMapper  # noqa: E402


SOCIAL_REFERENCE_DATE = datetime(2026, 9, 6, 17, 0, tzinfo=timezone.utc)
TECHNICAL_OFFER_SUFFIX = " La posición forma parte de este dataset local de prueba."
ALLOWED_TABLES = {
    "conexiones",
    "seguimiento",
    "conversacion",
    "conversacion_usuario",
    "mensaje",
    "oferta",
}
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
class MessageSpec:
    author: str
    content: str


@dataclass(frozen=True)
class ChatSpec:
    first: str
    second: str
    messages: tuple[MessageSpec, ...]
    unread_messages: int


def canonical_names(first: str, second: str) -> tuple[str, str]:
    return tuple(sorted((first, second)))


def chat(
    first: str,
    second: str,
    unread: int,
    contents: tuple[str, ...],
    pattern: str | None = None,
) -> ChatSpec:
    author_pattern = pattern or "".join(
        "A" if index % 2 == 0 else "B" for index in range(len(contents))
    )
    if len(author_pattern) != len(contents) or set(author_pattern) - {"A", "B"}:
        raise ValueError("Patron de autores invalido")
    authors = {"A": first, "B": second}
    return ChatSpec(
        first=first,
        second=second,
        messages=tuple(
            MessageSpec(authors[letter], content)
            for letter, content in zip(author_pattern, contents, strict=True)
        ),
        unread_messages=unread,
    )


RING = (
    "Andy Jassy",
    "Sam Altman",
    "Gael Ponce",
    "Juan Cruz Maletti",
    "Fernando Mayer",
    "Lorenzo Diaz",
    "Binyamin Al-Ghomiz",
    "Ighnas Al-Mutto",
    "Franco Ghirardi",
    "Santín Ben-Konka",
    "Luca Di Lauro",
    "Manuel Valle",
    "Juan Cruz Moyano",
    "Alexandre Bompard",
    "Manfred Paulmann",
    "Chris Kempczinski",
    "Henrique Braun",
    "Benjamin Jerez",
    "Ignacio Labonia",
    "Jacques-Antoine Lacroix",
    "Romain Lacroix",
    "Andrew Wilson",
    "Lucas Estevo",
    "Agustin Pelachini",
    "Ignacio Libermann",
    "Joaquin Gambeta",
    "Franco Bosseti",
)

RING_CONNECTIONS = tuple(
    (RING[index], RING[(index + 1) % len(RING)]) for index in range(len(RING))
)
EXTRA_CONNECTIONS = (
    ("Sam Altman", "Juan Cruz Maletti"),
    ("Sam Altman", "Fernando Mayer"),
    ("Gael Ponce", "Fernando Mayer"),
    ("Gael Ponce", "Lorenzo Diaz"),
    ("Juan Cruz Maletti", "Binyamin Al-Ghomiz"),
    ("Juan Cruz Maletti", "Ighnas Al-Mutto"),
    ("Fernando Mayer", "Binyamin Al-Ghomiz"),
    ("Lorenzo Diaz", "Andy Jassy"),
    ("Lorenzo Diaz", "Andrew Wilson"),
    ("Franco Ghirardi", "Luca Di Lauro"),
    ("Santín Ben-Konka", "Alexandre Bompard"),
    ("Santín Ben-Konka", "Ighnas Al-Mutto"),
    ("Luca Di Lauro", "Agustin Pelachini"),
    ("Manuel Valle", "Franco Ghirardi"),
    ("Manuel Valle", "Ignacio Labonia"),
    ("Juan Cruz Moyano", "Henrique Braun"),
    ("Juan Cruz Moyano", "Andrew Wilson"),
    ("Alexandre Bompard", "Chris Kempczinski"),
    ("Manfred Paulmann", "Henrique Braun"),
    ("Manfred Paulmann", "Andy Jassy"),
    ("Chris Kempczinski", "Juan Cruz Moyano"),
    ("Benjamin Jerez", "Jacques-Antoine Lacroix"),
    ("Benjamin Jerez", "Romain Lacroix"),
    ("Ignacio Labonia", "Lucas Estevo"),
    ("Jacques-Antoine Lacroix", "Andrew Wilson"),
    ("Ignacio Libermann", "Franco Bosseti"),
    ("Joaquin Gambeta", "Agustin Pelachini"),
)
CONNECTIONS = RING_CONNECTIONS + EXTRA_CONNECTIONS

FOLLOWS = (
    ("Agustin Pelachini", "Manuel Valle"),
    ("Agustin Pelachini", "Santín Ben-Konka"),
    ("Alexandre Bompard", "Manfred Paulmann"),
    ("Alexandre Bompard", "Henrique Braun"),
    ("Andrew Wilson", "Benjamin Jerez"),
    ("Andrew Wilson", "Gael Ponce"),
    ("Andrew Wilson", "Andy Jassy"),
    ("Andy Jassy", "Sam Altman"),
    ("Andy Jassy", "Gael Ponce"),
    ("Andy Jassy", "Lorenzo Diaz"),
    ("Benjamin Jerez", "Jacques-Antoine Lacroix"),
    ("Benjamin Jerez", "Ignacio Labonia"),
    ("Binyamin Al-Ghomiz", "Juan Cruz Maletti"),
    ("Binyamin Al-Ghomiz", "Fernando Mayer"),
    ("Chris Kempczinski", "Alexandre Bompard"),
    ("Chris Kempczinski", "Manfred Paulmann"),
    ("Fernando Mayer", "Juan Cruz Maletti"),
    ("Fernando Mayer", "Gael Ponce"),
    ("Franco Bosseti", "Ignacio Libermann"),
    ("Franco Ghirardi", "Santín Ben-Konka"),
    ("Franco Ghirardi", "Luca Di Lauro"),
    ("Franco Ghirardi", "Ighnas Al-Mutto"),
    ("Gael Ponce", "Sam Altman"),
    ("Gael Ponce", "Andy Jassy"),
    ("Henrique Braun", "Juan Cruz Moyano"),
    ("Henrique Braun", "Benjamin Jerez"),
    ("Ighnas Al-Mutto", "Franco Ghirardi"),
    ("Ighnas Al-Mutto", "Santín Ben-Konka"),
    ("Ignacio Labonia", "Benjamin Jerez"),
    ("Ignacio Labonia", "Manuel Valle"),
    ("Ignacio Libermann", "Joaquin Gambeta"),
    ("Ignacio Libermann", "Manuel Valle"),
    ("Jacques-Antoine Lacroix", "Romain Lacroix"),
    ("Jacques-Antoine Lacroix", "Benjamin Jerez"),
    ("Joaquin Gambeta", "Ignacio Libermann"),
    ("Juan Cruz Maletti", "Gael Ponce"),
    ("Juan Cruz Maletti", "Fernando Mayer"),
    ("Juan Cruz Moyano", "Alexandre Bompard"),
    ("Juan Cruz Moyano", "Henrique Braun"),
    ("Lorenzo Diaz", "Andy Jassy"),
    ("Lorenzo Diaz", "Gael Ponce"),
    ("Luca Di Lauro", "Franco Ghirardi"),
    ("Luca Di Lauro", "Manuel Valle"),
    ("Lucas Estevo", "Juan Cruz Moyano"),
    ("Manfred Paulmann", "Alexandre Bompard"),
    ("Manfred Paulmann", "Chris Kempczinski"),
    ("Manuel Valle", "Juan Cruz Moyano"),
    ("Manuel Valle", "Franco Ghirardi"),
    ("Manuel Valle", "Ignacio Labonia"),
    ("Romain Lacroix", "Jacques-Antoine Lacroix"),
    ("Sam Altman", "Gael Ponce"),
    ("Sam Altman", "Andy Jassy"),
    ("Sam Altman", "Andrew Wilson"),
    ("Santín Ben-Konka", "Franco Ghirardi"),
)

CHATS = (
    chat("Andy Jassy", "Sam Altman", 1, (
        "Vi la discusión sobre infraestructura de IA. La demanda de cómputo está cambiando más rápido que los ciclos tradicionales de capacidad.",
        "Sí, y sumar capacidad no alcanza si evaluación y seguridad quedan para el final. Hay que diseñarlas junto con el sistema.",
        "Coincido. También estamos mirando cómo reducir tiempos entre experimentación y despliegue sin perder observabilidad.",
        "La trazabilidad de cada versión ayuda mucho. Permite comparar mejoras reales y no confundir escala con calidad.",
        "Podríamos intercambiar criterios sobre planificación de capacidad y pruebas antes del próximo trimestre.",
        "Me interesa. Te envío una agenda breve y coordinamos una llamada.",
    )),
    chat("Sam Altman", "Gael Ponce", 1, (
        "Tu publicación sobre prompts resume bien por qué separar tareas mejora los resultados.",
        "Gracias. En proyectos reales también sirve para detectar exactamente en qué paso empezó el error.",
        "¿Estás probando evaluaciones automáticas además de revisión humana?",
        "Sí, uso ambas. Las métricas encuentran regresiones y la revisión humana aporta contexto.",
    )),
    chat("Gael Ponce", "Juan Cruz Maletti", 0, (
        "Me quedó dando vueltas tu enfoque de optimización mecánica. ¿Trabajaste con señales de vibración para mantenimiento predictivo?",
        "Sí, aunque el desafío suele ser distinguir una tendencia útil del ruido normal de operación.",
        "Podemos empezar con variables simples y modelos explicables antes de probar algo más complejo.",
        "Eso facilitaría que mantenimiento confíe en la alerta y pueda verificarla en campo.",
        "Te paso un esquema de variables y vemos si sirve para un prototipo pequeño.",
    )),
    chat("Juan Cruz Maletti", "Fernando Mayer", 1, (
        "Estoy revisando un banco de pruebas para motores y necesito ordenar mejor la parte de adquisición eléctrica.",
        "Puedo ayudarte a separar potencia, protecciones y medición. ¿Qué frecuencia de muestreo necesitás?",
        "Todavía la estamos definiendo; queremos capturar transitorios sin llenar de datos inútiles el sistema.",
        "Mandame el rango de potencia y las señales críticas. Con eso armamos una propuesta razonable.",
    )),
    chat("Fernando Mayer", "Lorenzo Diaz", 2, (
        "Vi que trabajás en telecomunicaciones. Me interesa cómo están resolviendo alimentación de respaldo en sitios remotos.",
        "Estamos comparando baterías y monitoreo remoto para anticipar degradación antes de una caída.",
        "Si querés, te comparto las variables eléctricas que más nos sirvieron para detectar problemas temprano.",
    ), pattern="ABB"),
    chat("Lorenzo Diaz", "Binyamin Al-Ghomiz", 0, (
        "En operaciones alejadas, una red confiable puede ahorrar horas cuando aparece una desviación.",
        "Totalmente. En campo necesitamos telemetría clara, pero también procedimientos que funcionen sin conexión.",
        "Estoy diseñando una arquitectura con almacenamiento local y sincronización cuando vuelve el enlace.",
        "Suena útil. Podemos revisar juntos qué datos son críticos y cuáles pueden esperar.",
    )),
    chat("Binyamin Al-Ghomiz", "Ighnas Al-Mutto", 1, (
        "Estamos evaluando una mejora de instrumentación y necesito presentar el beneficio más allá del costo inicial.",
        "Armemos escenarios con reducción de paradas, exposición al riesgo y vida útil. Ahí suele aparecer el valor completo.",
    )),
    chat("Ighnas Al-Mutto", "Franco Ghirardi", 1, (
        "¿Cómo estás modelando el impacto de tasas en la cartera para el próximo trimestre?",
        "Uso tres escenarios y separo el efecto sobre liquidez del efecto sobre mora. Mezclarlos esconde decisiones importantes.",
        "Tiene sentido. Yo agregaría sensibilidad por plazo de fondeo y concentración de clientes.",
        "Buena idea. Te paso la planilla base para comparar supuestos.",
    )),
    chat("Franco Ghirardi", "Santín Ben-Konka", 0, (
        "Estuve revisando los indicadores de liquidez y hay margen para simplificar el tablero ejecutivo.",
        "Prefiero pocos indicadores, pero con alertas claras y trazabilidad hasta el dato original.",
        "Podemos separar vista diaria, estrés semanal y tendencias mensuales.",
        "Eso ayudaría a no mezclar urgencias operativas con decisiones de estructura.",
        "Lo preparo y lo revisamos con riesgo antes de circularlo.",
    )),
    chat("Santín Ben-Konka", "Luca Di Lauro", 1, (
        "Me interesa cómo están explicando costo total en productos de aprobación rápida.",
        "Lo mostramos antes de confirmar, con cuota, plazo y costo expresados en el mismo lugar.",
        "¿También prueban comprensión con usuarios que no usan servicios financieros digitales seguido?",
        "Sí. Esa prueba encontró términos que parecían claros internamente y no lo eran para el cliente.",
    )),
    chat("Luca Di Lauro", "Manuel Valle", 2, (
        "Varias pymes nos piden crédito sin tener ordenado su ciclo de cobros.",
        "Podemos preparar una guía corta para que identifiquen la necesidad real antes de elegir plazo.",
        "Me gusta. La hacemos práctica, con ejemplos de negocios estacionales y capital de trabajo.",
    ), pattern="ABB"),
    chat("Manuel Valle", "Juan Cruz Moyano", 0, (
        "La expansión comercial viene bien, pero algunos procesos internos no están acompañando el ritmo.",
        "Empecemos por los traspasos entre ventas, operaciones y finanzas; ahí aparecen muchas demoras.",
        "Quiero evitar una reorganización enorme que distraiga a todo el equipo.",
        "Entonces prioricemos dos flujos críticos y midamos antes de ampliar el cambio.",
    )),
    chat("Juan Cruz Moyano", "Alexandre Bompard", 1, (
        "La consistencia entre precio, disponibilidad y experiencia parece simple, pero exige mucha coordinación.",
        "Sí, el cliente ve una sola promesa aunque internamente participen abastecimiento, tienda y comunicación.",
        "Estamos buscando indicadores que no optimicen un área a costa de otra.",
        "Podemos comparar algunos criterios de disponibilidad y satisfacción por categoría.",
    )),
    chat("Alexandre Bompard", "Manfred Paulmann", 1, (
        "Vi los resultados del programa de formación. La práctica en tienda parece haber sido decisiva.",
        "Lo fue. Los jóvenes pudieron mostrar experiencia concreta y los equipos aprendieron a acompañarlos mejor.",
        "¿Midieron continuidad laboral después del primer ingreso?",
        "Estamos preparando ese seguimiento para distinguir inserción inicial de trayectoria sostenida.",
        "Cuando lo tengan, me gustaría intercambiar aprendizajes sobre el modelo.",
    )),
    chat("Manfred Paulmann", "Chris Kempczinski", 0, (
        "En operaciones con mucho volumen, formar supervisores sigue siendo uno de los mayores desafíos.",
        "Coincido. La diferencia está en enseñar a priorizar durante el turno, no solo en memorizar procedimientos.",
        "También necesitamos retroalimentación breve y frecuente para que el aprendizaje no llegue tarde.",
        "Podemos compartir formatos de seguimiento que funcionaron bien con equipos nuevos.",
    )),
    chat("Chris Kempczinski", "Henrique Braun", 1, (
        "Estamos reforzando controles de calidad sin volver más lenta la operación diaria.",
        "Conviene integrar los controles en el proceso y reservar la revisión final para confirmar, no para descubrir todo.",
        "¿Te parece si comparamos cómo documentamos desvíos y acciones preventivas?",
    )),
    chat("Henrique Braun", "Benjamin Jerez", 2, (
        "Queremos comunicar calidad mostrando el trabajo real detrás del producto, sin caer en mensajes técnicos fríos.",
        "Podemos contar una decisión concreta y a la persona que la sostiene. Eso vuelve visible el estándar sin exagerarlo.",
        "Me gusta. Probemos una pieza corta centrada en trazabilidad y otra en prevención.",
        "Armo ambos enfoques con el mismo tono para que podamos compararlos.",
    ), pattern="ABAA"),
    chat("Benjamin Jerez", "Ignacio Labonia", 0, (
        "Estoy trabajando una campaña para una marca conocida y quiero actualizarla sin borrar su memoria.",
        "Yo conservaría dos códigos muy reconocibles y cambiaría ritmo, encuadre y contexto de uso.",
        "También quiero que funcione en piezas muy breves, donde no hay tiempo para explicar demasiado.",
        "Entonces el primer cuadro tiene que contar casi toda la historia.",
        "Podemos preparar variantes con producto, gesto de uso y resultado final.",
        "Perfecto. Las probamos con el mismo mensaje y medimos qué se entiende primero.",
    )),
    chat("Ignacio Labonia", "Jacques-Antoine Lacroix", 1, (
        "La línea escolar nueva tiene públicos distintos y conviene ordenar mejor la presentación comercial.",
        "Necesitamos que cada familia tenga identidad propia sin perder la relación con la marca.",
        "Propongo agrupar por momento de uso y no solamente por tipo de producto.",
        "Prepará ese recorrido; puede servir tanto para showroom como para material de ventas.",
    )),
    chat("Jacques-Antoine Lacroix", "Romain Lacroix", 1, (
        "Revisé las primeras devoluciones del showroom. La línea sensorial generó muchas preguntas útiles.",
        "Bien. Organicemos esas preguntas por edad, contexto de uso y expectativa del docente.",
    )),
    chat("Romain Lacroix", "Andrew Wilson", 0, (
        "Me interesa cómo prueban productos interactivos con usuarios antes de cerrar el diseño.",
        "Trabajamos con prototipos tempranos y observamos dónde la persona duda, no solo qué dice al final.",
        "Ese enfoque podría servir para herramientas escolares con funciones nuevas.",
        "Claro. Una sesión corta con tareas concretas suele revelar más que una encuesta general.",
    )),
    chat("Andrew Wilson", "Lucas Estevo", 1, (
        "La demostración cambia mucho la percepción cuando un producto tiene varias funciones nuevas.",
        "En vehículos pasa igual: una prueba concreta aclara más que una ficha con veinte características.",
        "¿Cómo evitás que la explicación dependa demasiado de cada vendedor?",
        "Usamos un recorrido común, pero dejamos espacio para adaptar ejemplos a la rutina del cliente.",
        "Ese equilibrio entre consistencia y personalización también sirve en experiencias digitales.",
    )),
    chat("Lucas Estevo", "Agustin Pelachini", 2, (
        "Estamos revisando el seguimiento postventa y aparecen consultas repetidas que podríamos anticipar.",
        "Clasifiquemos los motivos por momento del recorrido y preparemos respuestas antes de la entrega.",
        "Te paso una muestra de conversaciones para detectar dónde falta información.",
    ), pattern="ABB"),
    chat("Agustin Pelachini", "Ignacio Libermann", 0, (
        "Estoy ordenando un flujo de atención donde algunas consultas requieren mucha contención además de información.",
        "En salud ayuda explicar el siguiente paso y confirmar que la persona entendió, sin apurar la conversación.",
        "Voy a incorporar una verificación breve al cierre para reducir contactos repetidos.",
    )),
    chat("Ignacio Libermann", "Joaquin Gambeta", 1, (
        "La confianza influye muchísimo en que una persona consulte a tiempo.",
        "Sí. Privacidad, lenguaje claro y escucha activa son parte del diagnóstico, no un detalle adicional.",
        "Estamos revisando cómo explicar preparaciones previas sin generar más ansiedad.",
        "Puedo compartirte un formato breve que usamos antes de cada consulta.",
    )),
    chat("Joaquin Gambeta", "Franco Bosseti", 1, (
        "Un entorno tranquilo cambia mucho la experiencia de quienes llegan tensos a una consulta.",
        "La recepción y el ritmo de atención pueden ayudar antes incluso de que empiece la evaluación profesional.",
    )),
    chat("Franco Bosseti", "Andy Jassy", 0, (
        "Vi que están explorando experiencias de entrega nuevas. La percepción del cliente también depende de cómo se comunica el cambio.",
        "Totalmente. La tecnología tiene que resolver una necesidad concreta y explicar bien sus límites.",
        "Una introducción gradual permitiría recoger dudas antes de ampliar el servicio.",
        "Ese es el enfoque: medir operación y confianza al mismo tiempo.",
    )),
    chat("Sam Altman", "Juan Cruz Maletti", 1, (
        "Tu comentario sobre supuestos y criterios de aceptación aplica muy bien al trabajo con modelos.",
        "En ingeniería, explicitar restricciones evita optimizar una solución que después no puede fabricarse.",
        "En IA ocurre algo parecido: una métrica aislada puede mejorar mientras el producto empeora.",
        "Entonces conviene definir varias pruebas y cuáles son realmente bloqueantes.",
        "Podríamos armar un ejemplo común con diseño mecánico asistido y revisión humana.",
        "Me interesa. Te envío un caso pequeño con restricciones claras para empezar.",
    )),
    chat("Gael Ponce", "Fernando Mayer", 2, (
        "Estoy probando detección de anomalías sobre consumo eléctrico, pero quiero evitar alertas difíciles de explicar.",
        "Empezaría con umbrales físicos y tendencias conocidas antes de sumar un modelo más flexible.",
        "Eso nos daría una referencia interpretable para comparar falsos positivos.",
        "Mandame las variables disponibles y revisamos cuáles tienen sentido eléctrico.",
    ), pattern="ABAA"),
    chat("Juan Cruz Maletti", "Binyamin Al-Ghomiz", 0, (
        "Me interesó cómo describiste la precisión necesaria en una voladura controlada.",
        "El resultado depende de modelar bien el material y respetar cada verificación antes de cargar.",
        "En diseño mecánico pasa algo similar con tolerancias que parecen pequeñas hasta que se acumulan.",
        "Exacto. Documentar supuestos y medir después de ejecutar permite corregir sin adivinar.",
        "Podemos comparar métodos de análisis de causa para desvíos de campo.",
    )),
    chat("Lorenzo Diaz", "Andy Jassy", 1, (
        "La expansión de cómputo regional va a exigir mucha coordinación con conectividad y energía.",
        "Sí, la capacidad del centro no sirve si los enlaces o la alimentación se vuelven el cuello de botella.",
        "Estamos evaluando rutas redundantes y observabilidad compartida entre proveedores.",
        "Me gustaría revisar ese enfoque para cargas que necesitan recuperación rápida.",
    )),
    chat("Franco Ghirardi", "Luca Di Lauro", 1, (
        "Estoy analizando cómo mostrar costo y riesgo sin llenar la pantalla de cifras.",
        "Podemos priorizar cuota, costo total y consecuencia de cambiar el plazo, con detalles desplegables.",
        "Te paso dos variantes para que las prueben con usuarios.",
    )),
    chat("Santín Ben-Konka", "Alexandre Bompard", 0, (
        "Los medios de pago digitales reducen fricción, pero también cambian las consultas en tienda.",
        "Necesitamos que caja y atención entiendan qué hacer cuando una validación falla.",
        "Podemos preparar un flujo de resolución con contexto suficiente sin exponer información sensible.",
        "Eso ayudaría a resolver más casos en el primer contacto.",
    )),
    chat("Manuel Valle", "Ignacio Labonia", 1, (
        "Una pyme nos pidió rediseñar procesos y marca al mismo tiempo; temo que el equipo reciba demasiados cambios juntos.",
        "Separaría primero lo que afecta al cliente y después el trabajo interno que lo sostiene.",
        "Así podemos mostrar avances visibles sin esconder los ajustes operativos pendientes.",
        "Exacto. Definamos una secuencia corta y responsables claros para cada etapa.",
    )),
    chat("Juan Cruz Moyano", "Henrique Braun", 2, (
        "Estamos revisando trazabilidad con proveedores y quiero evitar controles duplicados.",
        "Mapeemos qué evidencia necesita cada etapa y dónde se genera por primera vez.",
        "También conviene acordar cómo escalar un desvío sin frenar materiales conformes.",
        "Sí, y distinguir corrección inmediata de acción preventiva para no mezclar plazos.",
        "Te comparto nuestro esquema y marcamos los puntos que podrían simplificarse.",
    ), pattern="ABABB"),
    chat("Benjamin Jerez", "Jacques-Antoine Lacroix", 0, (
        "La campaña de vuelta a clases tiene muchas novedades; necesitamos evitar que el mensaje se vuelva un catálogo.",
        "Podemos elegir una necesidad por línea y dejar que el producto la demuestre visualmente.",
        "Para Neón usaría expresión personal; para Trazado Irrompible, resistencia cotidiana.",
        "Y Kidy Learn debería mostrar concentración en una situación real, sin promesas exageradas.",
        "Armo un sistema de piezas con esa lógica y códigos compartidos de marca.",
        "Perfecto. Después probamos reconocimiento de cada línea y de Maped por separado.",
    )),
)


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
    return {"database": database, "server_address": address, "server_port": port}


def table_counts(db) -> dict[str, int]:
    return {
        name: db.execute(text(f'SELECT count(*) FROM public."{name}"')).scalar_one()
        for name in DOMAIN_TABLES
    }


def protected_fingerprints(db) -> dict[str, str]:
    result = {}
    for table_name in DOMAIN_TABLES:
        if table_name in ALLOWED_TABLES:
            continue
        rows = db.execute(
            text(
                f'SELECT row_to_json(item)::text FROM public."{table_name}" item '
                "ORDER BY row_to_json(item)::text"
            )
        ).scalars()
        digest = hashlib.sha256()
        for row in rows:
            digest.update(row.encode("utf-8") + b"\n")
        result[table_name] = digest.hexdigest()
    return result


def normalize_pairs(pairs):
    return {canonical_names(first, second) for first, second in pairs}


def connection_date(index: int) -> datetime:
    return SOCIAL_REFERENCE_DATE - timedelta(days=index % 30, minutes=index * 3)


def follow_date(index: int) -> datetime:
    return SOCIAL_REFERENCE_DATE - timedelta(days=index % 21, minutes=index * 2)


def validate_manifest(users_by_name: dict[str, Usuario]) -> dict[str, object]:
    all_names = set(users_by_name)
    if len(all_names) != 27 or set(RING) != all_names:
        raise RuntimeError("El conjunto actual de usuarios no coincide con el seed validado")
    connection_pairs = normalize_pairs(CONNECTIONS)
    if len(connection_pairs) != len(CONNECTIONS):
        raise RuntimeError("Hay conexiones duplicadas o invertidas")
    if any(first == second for first, second in CONNECTIONS):
        raise RuntimeError("Hay una autoconexion")
    if any(name not in all_names for pair in CONNECTIONS for name in pair):
        raise RuntimeError("Una conexion referencia un usuario inexistente")

    adjacency = {name: set() for name in all_names}
    for first, second in connection_pairs:
        adjacency[first].add(second)
        adjacency[second].add(first)
    visited = {RING[0]}
    queue = deque([RING[0]])
    while queue:
        current = queue.popleft()
        for neighbor in adjacency[current] - visited:
            visited.add(neighbor)
            queue.append(neighbor)
    if visited != all_names:
        raise RuntimeError("La red de conexiones no es conexa")
    degrees = {name: len(neighbors) for name, neighbors in adjacency.items()}
    if min(degrees.values()) < 3 or max(degrees.values()) > 5:
        raise RuntimeError(f"Distribucion de grados inesperada: {degrees}")

    if len(set(FOLLOWS)) != len(FOLLOWS):
        raise RuntimeError("Hay seguimientos duplicados")
    if any(follower == followed for follower, followed in FOLLOWS):
        raise RuntimeError("Hay un autoseguimiento")
    follow_counts = Counter(follower for follower, _ in FOLLOWS)
    if Counter(follow_counts.values()) != {1: 5, 2: 17, 3: 5}:
        raise RuntimeError(f"Distribucion de seguimientos inesperada: {follow_counts}")

    chat_pairs = [canonical_names(item.first, item.second) for item in CHATS]
    if len(set(chat_pairs)) != len(chat_pairs):
        raise RuntimeError("Hay chats duplicados")
    if not set(chat_pairs) <= connection_pairs:
        raise RuntimeError("Hay un chat entre usuarios no conectados")
    for item in CHATS:
        authors = {message.author for message in item.messages}
        if authors != {item.first, item.second}:
            raise RuntimeError("Un chat no tiene participacion de ambas personas")
        if not 2 <= len(item.messages) <= 6:
            raise RuntimeError("Cantidad de mensajes fuera de rango")
        if not 0 <= item.unread_messages <= 2:
            raise RuntimeError("Cantidad de no leidos fuera de rango")
        if item.unread_messages == 2:
            if len({message.author for message in item.messages[-2:]}) != 1:
                raise RuntimeError("Los dos no leidos deben pertenecer al mismo destinatario")
        if any(not message.content.strip() for message in item.messages):
            raise RuntimeError("Mensaje vacio")
        if any(len(message.content) > 2000 for message in item.messages):
            raise RuntimeError("Mensaje demasiado largo")
    return {
        "connection_degrees": degrees,
        "connection_average": 2 * len(CONNECTIONS) / len(all_names),
        "follow_counts": dict(follow_counts),
        "follow_average": len(FOLLOWS) / len(all_names),
        "network_connected": True,
        "chat_coverage_percent": 100 * len(CHATS) / len(CONNECTIONS),
        "message_distribution": dict(Counter(len(item.messages) for item in CHATS)),
    }


def existing_offer_corrections(db) -> list[Oferta]:
    matches = db.query(Oferta).filter(Oferta.descripcion.contains(TECHNICAL_OFFER_SUFFIX)).all()
    for item in matches:
        if not item.descripcion.endswith(TECHNICAL_OFFER_SUFFIX):
            raise RuntimeError(f"La leyenda tecnica no esta al final de oferta {item.id}")
    return matches


def find_connection(db, first_id: int, second_id: int):
    smaller, larger = sorted((first_id, second_id))
    return db.get(Conexion, (smaller, larger))


def find_conversation(db, first_id: int, second_id: int):
    smaller, larger = sorted((first_id, second_id))
    return (
        db.query(Conversacion)
        .filter(
            Conversacion.usuario_menor_id == smaller,
            Conversacion.usuario_mayor_id == larger,
        )
        .one_or_none()
    )


def find_message(db, conversation_id: int, spec: MessageSpec, users_by_name):
    matches = (
        db.query(Mensaje)
        .filter(
            Mensaje.conversacion_id == conversation_id,
            Mensaje.autor_id == users_by_name[spec.author].id,
            Mensaje.contenido == spec.content,
            Mensaje.tipo == "TEXTO",
            Mensaje.publicacion_id.is_(None),
        )
        .all()
    )
    if len(matches) > 1:
        raise RuntimeError("Hay mensajes duplicados exactos")
    return matches[0] if matches else None


def dry_run_report(db, users_by_name, graph_info) -> dict[str, object]:
    connections = []
    for first, second in CONNECTIONS:
        current = find_connection(db, users_by_name[first].id, users_by_name[second].id)
        if current is not None and current.estado != "aceptada":
            raise RuntimeError(f"La conexion existente {first} - {second} no esta aceptada")
        connections.append({"usuarios": [first, second], "estado": "existente" if current else "nueva"})
    follows = []
    for follower, followed in FOLLOWS:
        current = db.get(Seguimiento, (users_by_name[follower].id, users_by_name[followed].id))
        follows.append({"seguidor": follower, "seguido": followed, "estado": "existente" if current else "nuevo"})
    chats = []
    pending_messages = duplicate_messages = 0
    for item in CHATS:
        conversation = find_conversation(db, users_by_name[item.first].id, users_by_name[item.second].id)
        messages = []
        for message in item.messages:
            existing = find_message(db, conversation.id, message, users_by_name) if conversation else None
            pending_messages += existing is None
            duplicate_messages += existing is not None
            messages.append({"autor": message.author, "contenido": message.content, "estado": "existente" if existing else "nuevo"})
        chats.append({
            "participantes": [item.first, item.second],
            "estado": "existente" if conversation else "nuevo",
            "mensajes": messages,
            "no_leidos_preparados": item.unread_messages,
        })
    corrections = existing_offer_corrections(db)
    return {
        "conexiones": connections,
        "seguimientos": follows,
        "chats": chats,
        "conexiones_nuevas": sum(item["estado"] == "nueva" for item in connections),
        "conexiones_existentes": sum(item["estado"] == "existente" for item in connections),
        "seguimientos_nuevos": sum(item["estado"] == "nuevo" for item in follows),
        "seguimientos_existentes": sum(item["estado"] == "existente" for item in follows),
        "chats_nuevos": sum(item["estado"] == "nuevo" for item in chats),
        "chats_existentes": sum(item["estado"] == "existente" for item in chats),
        "mensajes_nuevos": pending_messages,
        "mensajes_existentes": duplicate_messages,
        "ofertas_a_corregir": [item.id for item in corrections],
        "grafo": graph_info,
    }


def create_conversation(db, first_id: int, second_id: int, created_at: datetime):
    smaller, larger = sorted((first_id, second_id))
    conversation = Conversacion(
        usuario_menor_id=smaller,
        usuario_mayor_id=larger,
        fecha_creacion=created_at,
    )
    db.add(conversation)
    db.flush()
    db.add_all([
        ConversacionUsuario(conversacion_id=conversation.id, usuario_id=smaller, ultima_lectura=created_at),
        ConversacionUsuario(conversacion_id=conversation.id, usuario_id=larger, ultima_lectura=created_at),
    ])
    db.flush()
    return conversation


def sql_verifications(db) -> dict[str, object]:
    degree_rows = db.execute(text(
        "SELECT usuario_id,count(*) grado FROM ("
        "SELECT usuario_a usuario_id FROM conexiones WHERE estado='aceptada' UNION ALL "
        "SELECT usuario_b FROM conexiones WHERE estado='aceptada') edges "
        "GROUP BY usuario_id"
    )).all()
    degrees = [row.grado for row in degree_rows]
    message_counts = [row[0] for row in db.execute(text(
        "SELECT count(*) FROM mensaje GROUP BY conversacion_id ORDER BY conversacion_id"
    )).all()]
    values = {
        "conexiones": db.execute(text("SELECT count(*) FROM conexiones WHERE estado='aceptada'")).scalar_one(),
        "grado_promedio": sum(degrees) / 27,
        "grado_minimo": min(degrees),
        "grado_maximo": max(degrees),
        "autoconexiones": db.execute(text("SELECT count(*) FROM conexiones WHERE usuario_a=usuario_b")).scalar_one(),
        "conexiones_no_canonicas": db.execute(text("SELECT count(*) FROM conexiones WHERE usuario_a>=usuario_b")).scalar_one(),
        "seguimientos": db.execute(text("SELECT count(*) FROM seguimiento")).scalar_one(),
        "seguimientos_promedio": db.execute(text("SELECT count(*)::float/27 FROM seguimiento")).scalar_one(),
        "autoseguimientos": db.execute(text("SELECT count(*) FROM seguimiento WHERE seguidor_id=seguido_id")).scalar_one(),
        "conversaciones": db.execute(text("SELECT count(*) FROM conversacion")).scalar_one(),
        "chats_sin_conexion": db.execute(text(
            "SELECT count(*) FROM conversacion c LEFT JOIN conexiones x ON "
            "x.usuario_a=c.usuario_menor_id AND x.usuario_b=c.usuario_mayor_id AND x.estado='aceptada' "
            "WHERE x.usuario_a IS NULL"
        )).scalar_one(),
        "pares_de_chat_duplicados": db.execute(text(
            "SELECT count(*) FROM (SELECT usuario_menor_id,usuario_mayor_id FROM conversacion "
            "GROUP BY 1,2 HAVING count(*)>1) duplicated"
        )).scalar_one(),
        "chats_con_participantes_invalidos": db.execute(text(
            "SELECT count(*) FROM conversacion c WHERE (SELECT count(*) FROM conversacion_usuario cu "
            "WHERE cu.conversacion_id=c.id AND cu.usuario_id IN (c.usuario_menor_id,c.usuario_mayor_id))<>2"
        )).scalar_one(),
        "mensajes": db.execute(text("SELECT count(*) FROM mensaje")).scalar_one(),
        "mensajes_promedio": sum(message_counts) / len(message_counts),
        "mensajes_minimo": min(message_counts),
        "mensajes_maximo": max(message_counts),
        "mensajes_autor_fuera": db.execute(text(
            "SELECT count(*) FROM mensaje m LEFT JOIN conversacion_usuario cu ON "
            "cu.conversacion_id=m.conversacion_id AND cu.usuario_id=m.autor_id WHERE cu.usuario_id IS NULL"
        )).scalar_one(),
        "mensajes_vacios": db.execute(text("SELECT count(*) FROM mensaje WHERE contenido !~ '[^[:space:]]'")).scalar_one(),
        "mensajes_futuros": db.execute(text("SELECT count(*) FROM mensaje WHERE fecha>now()" )).scalar_one(),
        "chats_un_solo_autor": db.execute(text(
            "SELECT count(*) FROM (SELECT conversacion_id FROM mensaje GROUP BY conversacion_id "
            "HAVING count(DISTINCT autor_id)<2) one_author"
        )).scalar_one(),
        "ultimo_mensaje_inconsistente": db.execute(text(
            "SELECT count(*) FROM conversacion c WHERE c.fecha_ultimo_mensaje IS DISTINCT FROM "
            "(SELECT max(m.fecha) FROM mensaje m WHERE m.conversacion_id=c.id)"
        )).scalar_one(),
        "mensajes_no_leidos": db.execute(text("SELECT count(*) FROM mensaje WHERE NOT leido_por_destinatario")).scalar_one(),
        "notificaciones": db.execute(text("SELECT count(*) FROM notificacion")).scalar_one(),
        "texto_tecnico_visible": db.execute(text(
            "WITH contenido(tabla, valor) AS ("
            "SELECT 'usuario', concat_ws(' ', nombre, headline, ciudad) FROM usuario UNION ALL "
            "SELECT 'empresa', concat_ws(' ', nombre, industria, sitio_web) FROM empresa UNION ALL "
            "SELECT 'publicacion', texto FROM publicacion UNION ALL "
            "SELECT 'comentario', contenido FROM comentario UNION ALL "
            "SELECT 'oferta', concat_ws(' ', titulo, descripcion) FROM oferta UNION ALL "
            "SELECT 'mensaje', contenido FROM mensaje"
            ") SELECT count(*) FROM contenido WHERE "
            "lower(valor) LIKE '%dataset local de prueba%' OR "
            "lower(valor) LIKE '%dataset de prueba%' OR "
            "lower(valor) LIKE '%datos generados para testing%' OR "
            "lower(valor) LIKE '%información simulada%' OR "
            "lower(valor) LIKE '%perfil de prueba%' OR "
            "lower(valor) LIKE '%empresa ficticia para desarrollo%' OR "
            "lower(valor) LIKE '%esta oferta es ficticia%' OR "
            "lower(valor) LIKE '%esta posición pertenece%'"
        )).scalar_one(),
    }
    zero_fields = (
        "autoconexiones", "conexiones_no_canonicas", "autoseguimientos",
        "chats_sin_conexion", "pares_de_chat_duplicados",
        "chats_con_participantes_invalidos", "mensajes_autor_fuera",
        "mensajes_vacios", "mensajes_futuros", "chats_un_solo_autor",
        "ultimo_mensaje_inconsistente", "notificaciones", "texto_tecnico_visible",
    )
    if any(values[key] for key in zero_fields):
        raise RuntimeError(f"Fallo una verificacion SQL: {values}")
    return values


def apply_seed(db, users_by_name, graph_info):
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('atanes:red-social-seed'))"))
    assert_safe_database(db)
    counts_before = table_counts(db)
    protected_before = protected_fingerprints(db)

    corrected_offer_ids = []
    for item in existing_offer_corrections(db):
        item.descripcion = item.descripcion.removesuffix(TECHNICAL_OFFER_SUFFIX)
        corrected_offer_ids.append(item.id)

    new_connections = 0
    connection_models = {}
    for index, (first, second) in enumerate(CONNECTIONS):
        first_user, second_user = users_by_name[first], users_by_name[second]
        current = find_connection(db, first_user.id, second_user.id)
        if current is None:
            dto = CreateConexionDTO(
                usuario_a=min(first_user.id, second_user.id),
                usuario_b=max(first_user.id, second_user.id),
                solicitante_id=first_user.id,
            )
            current = ConexionMapper.to_model(dto)
            current.estado = "aceptada"
            current.fecha = connection_date(index)
            db.add(current)
            new_connections += 1
        elif current.estado != "aceptada":
            raise RuntimeError(f"Conexion existente no aceptada: {first} - {second}")
        connection_models[canonical_names(first, second)] = current
    db.flush()

    new_follows = 0
    for index, (follower, followed) in enumerate(FOLLOWS):
        key = (users_by_name[follower].id, users_by_name[followed].id)
        if db.get(Seguimiento, key) is None:
            db.add(Seguimiento(seguidor_id=key[0], seguido_id=key[1], fecha=follow_date(index)))
            new_follows += 1
    db.flush()

    new_conversations = new_messages = 0
    unread_created = 0
    for chat_index, item in enumerate(CHATS):
        first_id = users_by_name[item.first].id
        second_id = users_by_name[item.second].id
        pair = canonical_names(item.first, item.second)
        connection = connection_models[pair]
        conversation = find_conversation(db, first_id, second_id)
        created_at = connection.fecha + timedelta(hours=1)
        if conversation is None:
            conversation = create_conversation(db, first_id, second_id, created_at)
            new_conversations += 1
        participants = {
            row.usuario_id: row
            for row in db.query(ConversacionUsuario)
            .filter(ConversacionUsuario.conversacion_id == conversation.id)
        }
        if set(participants) != {first_id, second_id}:
            raise RuntimeError("Participantes invalidos en conversacion existente")

        chat_models = []
        chat_new_messages = 0
        for message_index, message_spec in enumerate(item.messages):
            existing = find_message(db, conversation.id, message_spec, users_by_name)
            if existing is None:
                is_unread = message_index >= len(item.messages) - item.unread_messages
                existing = Mensaje(
                    conversacion_id=conversation.id,
                    autor_id=users_by_name[message_spec.author].id,
                    contenido=message_spec.content,
                    tipo="TEXTO",
                    fecha=conversation.fecha_creacion + timedelta(minutes=5 * (message_index + 1)),
                    leido_por_destinatario=not is_unread,
                )
                db.add(existing)
                new_messages += 1
                chat_new_messages += 1
                unread_created += is_unread
            chat_models.append(existing)
        db.flush()
        ordered = sorted(chat_models, key=lambda model: (model.fecha, model.id))
        if len({model.autor_id for model in ordered}) != 2:
            raise RuntimeError("Ambos participantes deben escribir")
        if chat_new_messages:
            conversation.fecha_ultimo_mensaje = ordered[-1].fecha
        for participant_id, participation in participants.items():
            unread_incoming = [
                model for model in ordered
                if model.autor_id != participant_id and not model.leido_por_destinatario
            ]
            if unread_incoming:
                participation.ultima_lectura = min(model.fecha for model in unread_incoming) - timedelta(seconds=1)
            else:
                participation.ultima_lectura = ordered[-1].fecha
    db.flush()

    counts_after = table_counts(db)
    protected_after = protected_fingerprints(db)
    if protected_after != protected_before:
        raise RuntimeError("Se modifico una tabla protegida")
    allowed_increases = {
        "conexiones": new_connections,
        "seguimiento": new_follows,
        "conversacion": new_conversations,
        "conversacion_usuario": new_conversations * 2,
        "mensaje": new_messages,
    }
    for table_name, before in counts_before.items():
        expected = before + allowed_increases.get(table_name, 0)
        if counts_after[table_name] != expected:
            raise RuntimeError(f"Conteo inesperado en {table_name}")
    checks = sql_verifications(db)
    db.commit()
    return {
        "ofertas_corregidas": corrected_offer_ids,
        "conexiones_creadas": new_connections,
        "seguimientos_creados": new_follows,
        "conversaciones_creadas": new_conversations,
        "participaciones_creadas": new_conversations * 2,
        "mensajes_creados": new_messages,
        "mensajes_no_leidos_creados": unread_created,
        "conteos_antes": counts_before,
        "conteos_despues": counts_after,
        "tablas_protegidas_sin_cambios": protected_before == protected_after,
        "verificaciones_sql": checks,
        "grafo": graph_info,
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
            users = db.query(Usuario).order_by(Usuario.id).all()
            users_by_name = {user.nombre: user for user in users}
            if len(users_by_name) != len(users):
                raise RuntimeError("Hay nombres de usuario duplicados")
            graph_info = validate_manifest(users_by_name)
            preview = dry_run_report(db, users_by_name, graph_info)
            output = {
                "mode": "dry-run" if args.dry_run else "apply",
                "database": database,
                "usuarios": len(users),
                "conteos_actuales": table_counts(db),
                "manifest": preview,
            }
            if args.dry_run:
                output["postgresql_modificado"] = False
            else:
                output["resultado"] = apply_seed(db, users_by_name, graph_info)
        except Exception:
            db.rollback()
            raise
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
