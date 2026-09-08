# Términos y Condiciones de Atanes

Última actualización: 8 de septiembre de 2026.

## 1. Qué es Atanes

Atanes es una aplicación web educativa y demostrativa, inspirada en una red profesional. El proyecto ofrece una experiencia simplificada para crear perfiles, relacionarse con otras personas, publicar contenido, conversar y administrar empresas y ofertas laborales. No es una bolsa de trabajo ni una agencia de colocación y no garantiza entrevistas, contrataciones, ingresos ni resultados profesionales.

Estos Términos y Condiciones son la única página informativa de Atanes sobre las reglas de uso y el tratamiento técnico de los datos en la implementación actual. No existe una Política de Privacidad separada para complementar este documento.

## 2. Aceptación y cambios

Al crear una cuenta, la persona debe marcar la casilla «Acepto los Términos y Condiciones» y enviar `acepta_terminos` con valor `true`. Esa aceptación se usa solamente para validar el registro: no se guarda en PostgreSQL, no se agrega a la cuenta, no se escribe en una cookie y no se conserva en localStorage ni en sessionStorage. Si el campo falta o vale `false`, el backend rechaza el registro.

Atanes puede actualizar estos términos o modificar la aplicación a medida que avance el proyecto educativo. La versión publicada en esta página es la que describe el funcionamiento vigente. Si una modificación cambia de forma relevante el uso de la plataforma, se procurará comunicarla dentro de la propia aplicación cuando sea técnicamente posible.

## 3. Cuenta y credenciales

El registro es público y actualmente solicita un email único, una contraseña de al menos ocho caracteres, nombre visible, titular profesional y una ciudad seleccionada del catálogo de ubicaciones. El email se normaliza para evitar duplicados por mayúsculas o minúsculas. La contraseña se almacena como un hash bcrypt y nunca se incluye en las respuestas de la API.

Cada persona es responsable de proporcionar información propia y de mantener bajo control su contraseña y sus medios de acceso. No debe compartir credenciales, hacerse pasar por otra persona ni intentar acceder a cuentas o recursos que no le correspondan. Si se sospecha un acceso no autorizado, se debe cerrar la sesión y cambiar la contraseña desde la función disponible en el perfil.

## 4. Perfil, foto y experiencias

El perfil puede mostrar nombre, titular profesional, ciudad, foto de perfil y experiencias laborales asociadas a empresas. La foto es opcional; se admiten imágenes JPG, JPEG, PNG o WEBP válidas de hasta 5 MiB. El usuario puede actualizar sus datos, reemplazar su foto y agregar, editar o eliminar sus propias experiencias según las reglas de la aplicación.

Las fotos de personas y los logos de empresas se guardan como archivos en el servidor y la base de datos conserva su ruta pública. Atanes no agrega una foto a un perfil sin que se envíe mediante la función correspondiente.

## 5. Publicaciones, imágenes y videos

Una persona autenticada puede crear, editar y eliminar sus propias publicaciones. El texto admite hasta 3000 caracteres; también puede existir una publicación formada solamente por archivos multimedia. Las publicaciones pueden incluir hasta 10 archivos, con un máximo total de 150 MiB, hasta 5 MiB por imagen y hasta 50 MiB por video. Los formatos actuales son JPG, JPEG, PNG, WEBP, MP4 y WEBM, y el servidor valida el contenido real del archivo.

Las imágenes y videos de publicaciones se almacenan físicamente en el servidor, en el directorio destinado a multimedia de publicaciones, y se registran en PostgreSQL junto con el tipo, la ruta y el orden. El contenido visible de una publicación puede aparecer en el feed, en el perfil de su autor o al compartirse en una conversación, de acuerdo con las reglas actuales de la aplicación.

La persona que publica debe contar con los derechos necesarios para usar el texto, las imágenes y los videos que envía. Es responsable de que su contenido sea lícito y no vulnere derechos de terceros.

## 6. Comentarios y reacciones

Las personas autenticadas pueden comentar publicaciones y responder comentarios. Cada comentario admite hasta 1000 caracteres y puede eliminarlo su autor. Las reacciones disponibles son `like`, `celebrar`, `apoyar` e `interesante`; una persona puede tener como máximo una reacción por publicación, cambiarla o quitarla.

Los comentarios, respuestas y reacciones se guardan en PostgreSQL vinculados a la persona y a la publicación. El texto, las imágenes y los videos de terceros no representan necesariamente la opinión de Atanes.

## 7. Conexiones y seguimientos

La plataforma permite enviar invitaciones de conexión, aceptarlas o rechazarlas y eliminar una conexión aceptada. Las conexiones aceptadas se utilizan, entre otras cosas, para habilitar la mensajería privada. También se puede seguir o dejar de seguir a otra persona; el seguimiento es direccional y no se permite seguirse a sí mismo.

Los estados de las conexiones, sus fechas, las relaciones de seguimiento y las personas involucradas se almacenan en PostgreSQL para poder mostrar la red y aplicar las reglas de acceso.

## 8. Mensajería privada

La mensajería actual es uno a uno entre personas con una conexión aceptada. Existe como máximo una conversación por cada par de personas. Los mensajes de texto admiten hasta 2000 caracteres y también se puede compartir una publicación existente. Solo los participantes pueden consultar una conversación, enviar mensajes o marcarla como leída; si la conexión deja de estar aceptada, no se pueden enviar nuevos mensajes.

El contenido de los mensajes, su tipo, fecha, autor, conversación y estado de lectura se guarda en PostgreSQL. Cerrar o minimizar la ventana del chat solo cambia la interfaz y no elimina el historial. Los mensajes privados no generan notificaciones en el sistema actual.

## 9. Notificaciones

Atanes guarda notificaciones de actividad como nuevas postulaciones, cambios de estado de postulaciones, nuevos seguidores, invitaciones de conexión, conexiones aceptadas y propuestas de contratación desde una promoción. Cada notificación tiene destinatario, mensaje, fecha, tipo y estado de lectura, y puede marcarse como leída desde la aplicación.

## 10. Empresas, roles y experiencias laborales

Una persona autenticada puede crear una empresa. La empresa puede tener nombre, industria, sitio web y logo. El creador recibe el rol `OWNER`. Los roles disponibles son:

- `OWNER`: puede editar los datos y el logo, administrar miembros y gestionar ofertas, postulaciones y estadísticas.
- `RECRUITER`: puede gestionar ofertas, postulaciones y estadísticas, pero no editar los datos o el logo ni administrar miembros.
- `COLLABORATOR`: representa pertenencia a la empresa y no habilita controles administrativos.

La aplicación conserva las membresías, los roles y las experiencias laborales en PostgreSQL. Una empresa debe conservar al menos un `OWNER`. Una contratación aceptada puede agregar automáticamente el rol `COLLABORATOR` cuando la persona todavía no pertenece a esa empresa.

## 11. Ofertas y postulaciones

Los `OWNER` y `RECRUITER` pueden crear, editar, publicar y despublicar ofertas de una empresa que gestionan. Una oferta contiene título, descripción, estado de publicación y, cuando corresponde, fecha de publicación. Las ofertas publicadas se pueden consultar y buscar; los borradores quedan disponibles para quienes tienen permisos de gestión.

Una persona que no pertenece a la empresa puede postularse a una oferta publicada una sola vez. La postulación se registra con la persona, la oferta, la fecha y uno de estos estados: `nueva`, `vista`, `entrevista`, `contratado` o `rechazada`. Los gestores de la empresa pueden consultar postulaciones y estadísticas y avanzar el estado conforme a las transiciones implementadas. Pasar una postulación a `contratado` agrega la membresía de colaborador si corresponde y despublica la oferta.

Atanes no verifica la relación laboral, la identidad de las empresas, la exactitud de una oferta ni la concreción de una contratación. Las conversaciones, decisiones y acuerdos entre personas y empresas son responsabilidad de quienes participan.

## 12. Promociones y propuestas del tablón

Una persona autenticada puede publicar en el tablón una promoción con título de hasta 160 caracteres y descripción de hasta 3000 caracteres. Las promociones propias no se muestran como oportunidades disponibles para la misma persona. Un `OWNER` o `RECRUITER` puede proponer contratar a la persona autora desde una empresa que gestiona; la persona destinataria puede aceptar la propuesta. Una aceptación crea o confirma la membresía de colaborador según las reglas actuales.

Las promociones, las propuestas, sus estados, fechas, empresas y notificaciones relacionadas se almacenan en PostgreSQL. Publicar una promoción o aceptar una propuesta no constituye una promesa de empleo ni reemplaza un acuerdo entre las partes.

## 13. Datos, cookies y almacenamiento técnico

La información que actualmente utiliza Atanes se guarda principalmente en PostgreSQL. Incluye, según la función utilizada, datos de cuenta y perfil (email normalizado, nombre, titular, ciudad, hash de contraseña, fecha de registro y ruta de foto), experiencias, empresas y sus roles, ofertas y postulaciones, publicaciones y sus archivos multimedia, comentarios, reacciones, conexiones, seguimientos, conversaciones, mensajes, notificaciones, promociones y propuestas de contratación. La API devuelve identificadores para relacionar recursos, pero la contraseña y su hash no se devuelven al frontend.

### Cookies y autenticación

Al iniciar sesión, el backend emite la única cookie de aplicación actual, `access_token`. Su valor es un JWT firmado que contiene los datos mínimos de autenticación usados por el servidor, como el identificador y el email de la cuenta y una fecha de vencimiento; no contiene la contraseña ni el perfil completo. La cookie se configura como `HttpOnly`, `SameSite=Lax`, `Path=/` y con una duración aproximada de una hora (3600 segundos). El atributo `Secure` se activa en producción o cuando así lo indica la configuración del entorno.

La API también acepta el mismo JWT mediante el encabezado `Authorization: Bearer <token>`, una alternativa destinada a clientes que no utilizan cookies. Si llegan ambos mecanismos, el encabezado Bearer tiene prioridad. Cerrar sesión solicita al backend eliminar la cookie. El frontend usa credenciales incluidas en sus solicitudes y no intenta leer el JWT.

### Almacenamiento del navegador

El frontend no guarda el JWT, contraseñas ni credenciales en `localStorage` o `sessionStorage`, y la implementación actual no usa `sessionStorage`. Sí guarda preferencias de interfaz no esenciales:

- `localStorage` conserva las preferencias de tamaño, color y tipografía del panel de Mensajes bajo `atanes-messages-preferences:v1`.
- `localStorage` puede conservar, asociadas al `usuario_id`, las claves `atanes_profile_completion_pending_<usuario_id>` y `atanes_profile_completion_seen_<usuario_id>` para controlar la confirmación visual de perfil completado. Son estados de interfaz y no determinan si el perfil está completo.
- IndexedDB, en la base `atanes-message-preferences`, almacena opcionalmente como Blob la imagen de fondo personalizada del chat bajo la clave `chat-background-v1`.

La aceptación de estos términos no se guarda en ninguno de esos almacenamientos. Las fotos de perfiles y logos se guardan físicamente en `backend/imagenes`, y las imágenes y videos de publicaciones en `backend/multimedia_publicaciones`. Sus URLs son servidas por los recursos estáticos del backend sin exigir un JWT adicional; el acceso efectivo depende de que la ruta sea conocida y de la visibilidad que otorgue la propia aplicación.

## 14. Uso permitido y prohibiciones

La plataforma debe utilizarse de forma lícita, respetuosa y coherente con su finalidad educativa. Está prohibido, entre otras conductas:

- publicar contenido ilegal, amenazante, discriminatorio, abusivo, engañoso o que invada la privacidad de otra persona;
- suplantar identidades, registrar cuentas para terceros o usar credenciales ajenas;
- enviar spam, malware o archivos manipulados, o intentar eludir las validaciones de tamaño y formato;
- acceder, modificar o extraer datos, conversaciones, archivos o funciones sin autorización;
- usar Atanes para acosar, defraudar, discriminar en procesos laborales o infringir derechos de autor, marcas, imagen o datos personales;
- interferir con la disponibilidad, seguridad o funcionamiento de la aplicación o de su API.

La persona usuaria conserva la responsabilidad por lo que publica, comenta, comparte, envía o informa en su perfil y en sus postulaciones.

## 15. Moderación y cambios de contenido

La implementación actual no expone un panel de moderación general. Los permisos y validaciones del backend pueden impedir operaciones que no correspondan; además, cada autor puede editar o eliminar sus publicaciones y comentarios, actualizar el perfil, la foto y sus experiencias, y los `OWNER` pueden gestionar los datos de sus empresas mientras que los gestores autorizados administran sus ofertas y postulaciones. El proyecto puede incorporar controles adicionales en versiones futuras.

No hay en la aplicación actual una promesa de conservación, moderación humana permanente ni un plazo específico de retención. La disponibilidad de una función de edición o eliminación puede cambiar junto con el proyecto.

## 16. Disponibilidad y responsabilidad

Atanes se ofrece como proyecto educativo y demostrativo, sin garantía de disponibilidad continua, ausencia de errores, conservación permanente de archivos o compatibilidad con todos los dispositivos. Puede haber interrupciones, cambios, pérdida de datos o comportamientos incompletos propios de una aplicación en desarrollo.

Dentro de lo permitido por la normativa aplicable, el proyecto y sus responsables no responden por decisiones laborales, acuerdos entre usuarios, contenido aportado por terceros, interrupciones, daños indirectos ni resultados profesionales derivados del uso de Atanes. Esta limitación no elimina las responsabilidades que legalmente no puedan excluirse.

## 17. Contacto y vigencia

Estos términos rigen mientras esta versión de Atanes se encuentre publicada. El código actual no incluye un formulario o canal de contacto propio; si la instalación ofrece uno, se podrá utilizar para reportar problemas de seguridad, contenido o funcionamiento. Al continuar usando las funciones de Atanes después de una actualización, se aplicará la versión vigente publicada en `/terminos`.
