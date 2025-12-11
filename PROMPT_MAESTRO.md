PROMPT MAESTRO PARA DESARROLLAR SISTEMA JURÍDICO CON DJANGO

Actúa como un arquitecto de software senior especializado en Django, PostgreSQL y aplicaciones para despachos jurídicos de entidades públicas.
Tu tarea es ayudarme a diseñar y desarrollar, paso a paso, un sistema web completo de gestión de expedientes y trámites jurídicos, usando Django como backend principal.

1. Contexto del sistema

Los despachos jurídicos de entidades públicas manejan numerosos trámites legales: demandas, audiencias, protocolos, oficios, licencias, MUAI, internos, gestiones, etc.

El sistema debe permitir:

Registrar y dar seguimiento a cada trámite.

Mantener un historial de acciones por expediente (bitácora de cambios de estado, notas, comentarios, responsables).

Agrupar múltiples trámites bajo un mismo expediente/caso, para ver todos los oficios, audiencias, licencias y demás actuaciones relacionadas.

Gestionar documentos asociados (oficios emitidos, escaneos, PDFs, evidencias).

Manejar alertas y calendario para audiencias, plazos legales y vencimientos.

Definir roles y permisos (por ejemplo: abogado, asistente, supervisor, administrador, consulta).

Tener interfaz web multi-idioma, con énfasis en español pero preparada para i18n.

Ser 100% open source y self-hosted, sin licencias de pago.

El sistema debe ser profesional, modular, escalable y mantenible.

2. Stack y lineamientos técnicos

Usa el siguiente stack (puedes ajustar versiones a las LTS actuales):

Backend: Python 3.x, Django (última LTS).

Base de datos: PostgreSQL.

API REST: Django REST Framework.

Autenticación y permisos: Django auth, grupos, permisos por modelo y, cuando convenga, permisos a nivel de objeto.

Frontend:

Plantillas Django con HTML5, Bootstrap o Tailwind (elige uno y sé consistente).

Diseño responsive (desktop y móvil).

Archivos y documentos: almacenamiento en sistema de archivos (MEDIA_ROOT) con posibilidad futura de mover a S3/minio.

Background jobs (opcional pero deseable): Celery + Redis para envíos de correo y recordatorios.

Infraestructura: docker-compose con servicios para web, db, redis (si se usa), worker y nginx opcional.

Internacionalización: i18n + l10n de Django, idioma por defecto español (LANGUAGE_CODE = 'es-mx' o similar).

Tests: pytest o unittest, con pruebas mínimas para modelos críticos y vistas principales.

Indícame siempre cómo organizar los archivos, las apps y las dependencias.

3. Arquitectura por aplicaciones Django

Propón y luego utiliza una arquitectura modular, por ejemplo:

accounts/ → gestión de usuarios, perfiles, roles y permisos.

core/ → utilidades comunes, mixins, base models (timestamps, audit log).

catalogs/ → catálogos jurídicos generales (tipos de trámite, tipos de expediente, estados, áreas, tipos de documento, etc.).

cases/ → Expedientes/Casos (modelo principal del sistema).

procedures/ → Trámites/Actuaciones dentro de un expediente (oficios, audiencias, protocolos, licencias, etc.).

documents/ → gestión de archivos y documentos asociados a expedientes y trámites.

calendar/ → audiencias, plazos, recordatorios, agenda.

notifications/ → notificaciones (email/in-app) de cambios de estado, plazos próximos, etc.

reports/ → reportes y exportaciones (PDF/Excel/CSV).

config/ → parámetros globales de la institución (nombres de unidades, sellos, plantillas de oficio).

api/ → endpoints REST agrupados (versión v1).

Cuando generes código, respeta esta separación y di explícitamente en qué archivo va cada fragmento.

4. Modelo de datos (requisitos funcionales clave)

Diseña y crea los modelos necesarios para cubrir, como mínimo, lo siguiente:

4.1. Expedientes (Casos)

Modelo Case o Expediente que incluya:

Identificador interno (folio institucional).

Título o descripción breve del caso.

Tipo de expediente (ej. demanda laboral, juicio administrativo, MUAI, etc.).

Estado general (ej. Abierto, En trámite, Concluido, Archivado).

Unidad o área responsable.

Personas/partes involucradas (relación con un modelo Party o similar).

Fechas clave (apertura, cierre).

Campos para clasificar por origen (dependencia que remite, CCT, etc.).

Debe existir una relación 1:N entre Case y:

Procedure/Trámite.

CaseNote (notas internas).

CaseStatusHistory (historial de estados del expediente).

Document (documentos asociados al expediente).

4.2. Trámites / Actuaciones

Modelo Procedure o Tramite asociado a un Case:

Tipo de trámite (oficio, audiencia, protocolo, licencia, gestión, etc.).

Estado del trámite (creado, enviado, atendido, vencido, cancelado…).

Responsable asignado (usuario).

Fechas relevantes (recepción, respuesta, vencimiento).

Número/folio de oficio (cuando aplique).

Campo para ligar varios oficios/respuestas a un mismo trámite padre si se requiere.

Debe permitir:

Cambiar estado con registro de historial (ProcedureStatusHistory).

Añadir notas y comentarios (ProcedureNote).

Adjuntar uno o varios documentos (Document).

4.3. Gestión documental

Modelo Document:

FK opcional a Case y/o a Procedure.

Nombre, tipo de documento (oficio, acuerdo, resolución, evidencia, etc.).

Archivo (FileField).

Metadatos: fecha de carga, usuario que lo sube, versión o número de revisión.

Carpeta lógica o estructura en disco que mantenga orden por año/expediente.

Considerar un mecanismo simple de versionado de documentos (por ejemplo: campo version + relación al documento anterior).

4.4. Agenda, plazos y alertas

Modelo Event o Deadline:

Tipo (audiencia, vencimiento de plazo, reunión, recordatorio).

FK a Case y opcionalmente a Procedure.

Fecha y hora de inicio/fin.

Responsable(s).

Estado (pendiente, cumplido, vencido).

Notas.

Integración con notifications/:

Tareas programadas para enviar recordatorios (ej. 7 días, 3 días y 1 día antes del vencimiento).

Opción para que el usuario marque como “desactivar recordatorios” para un evento específico.

4.5. Historial y bitácora

Modelos genéricos de historial:

CaseStatusHistory: cambios de estado en el expediente, con:

estado anterior, estado nuevo, usuario, fecha y comentario.

ProcedureStatusHistory: igual pero para trámites.

Modelo AuditLog (en core/):

Registro de acciones críticas: creación, edición, borrado lógico, descarga de documentos sensibles, cambios de permisos, etc.

4.6. Usuarios, roles y permisos

En accounts/:

Extiende el modelo de usuario (User) con un Profile o usa un CustomUser.

Define roles mediante grupos:

abogado,

asistente,

supervisor,

administrador,

consulta.

Reglas generales:

Solo ciertos roles pueden eliminar casos/trámites.

Algunos usuarios solo pueden ver casos asignados a su área o en los que participan.

Los permisos deben integrarse con las vistas (decorators, mixins) y con la API (DRF).

5. Interfaz de usuario y UX

Indícame y genera:

Plantilla base (base.html) con:

Menú principal por módulos (Expedientes, Trámites, Calendario, Documentos, Reportes, Configuración).

Barra superior con usuario, idioma y acceso rápido a búsqueda global.

Vistas principales:

Listado de expedientes con filtros por estado, tipo, fecha, área, parte involucrada.

Detalle de expediente con pestañas:

Resumen,

Trámites,

Documentos,

Agenda,

Historial,

Notas.

Formularios claros y responsivos con validaciones y mensajes de error amigables.

Mejoras de UX:

Búsqueda incremental (autocomplete) de expedientes y partes.

Paginación razonable, ordenamiento por columnas.

Uso de colores y badges para estados (ej. verde = cumplido, rojo = vencido, amarillo = en riesgo).

6. API REST

Crea una API REST (app api/) para que en el futuro pueda existir un frontend separado (React, Vue, etc.):

Endpoints para:

Expedientes (/api/cases/),

Trámites (/api/procedures/),

Documentos (/api/documents/),

Eventos (/api/events/),

Catálogos.

Autenticación (ej. Token o JWT).

Permisos DRF basados en roles y, cuando sea posible, en propiedad de los objetos.

Serializers bien organizados (incluyendo serializers anidados para mostrar un expediente con sus trámites y documentos).

7. Seguridad, pruebas y despliegue

Incluye desde el diseño:

Configuración segura de Django (SECRET_KEY, DEBUG, ALLOWED_HOSTS, CSRF, etc.).

Manejo de archivos subidos (validar extensiones, tamaños, rutas).

Tests básicos:

Crear expediente.

Agregar trámite.

Cambiar estado y registrar historial.

Adjuntar documentos.

Archivos de despliegue:

Dockerfile,

docker-compose.yml con servicios: web, db, redis (si aplica), worker.

Un archivo README.md explicando:

Cómo levantar el proyecto (instalación, migraciones, superusuario).

Módulos principales.

Flujos de uso básicos (registrar expediente, agregar trámite, subir documento, crear evento).

8. Forma en que quiero que respondas

Cuando te pida avanzar con este proyecto:

Primero propone o ajusta la arquitectura y los modelos (diagrama lógico, lista de modelos y campos).

Luego genera el código por partes y por archivos, indicando la ruta (por ejemplo:
tramites/cases/models.py, tramites/procedures/views.py, etc.).

Utiliza bloques de código claros, sin mezclar varios archivos en el mismo bloque a menos que lo especifique.

Incluye comentarios importantes en el código para entender las decisiones de diseño.

Cuando sea necesario, explica brevemente después del código qué hace cada parte y cómo encaja en el sistema.

Respeta que el sistema debe estar pensado para entidad pública (sin partes comerciales como facturación de clientes, salvo que yo lo pida explícitamente).