# Checklist de Pruebas Manuales - OneDrive Business Monitor

## Matriz de Transiciones a Probar

| Estado Anterior   | Estado Actual   | ¿Incidente? | ¿Enviar? | Tipo de Correo / Acción Esperada         | Emoji Esperado |
|-------------------|----------------|-------------|----------|------------------------------------------|---------------|
| Cualquiera        | INCIDENTE      | Sí          | Sí       | Enviar INCIDENTE                         | 🚨, ❌, ⚠️     |
| INCIDENTE         | OK             | Sí          | Sí       | Enviar RESOLVED                          | ✅            |
| INCIDENTE         | SYNCING        | Sí          | Sí       | Enviar RESOLVED y luego SYNCING          | ✅, 🔄         |
| OK                | SYNCING        | No          | Sí       | Enviar SYNCING                           | 🔄            |
| SYNCING           | SYNCING        | No          | No       | No enviar nada                           | 🔄            |
| SYNCING           | OK             | No          | Sí       | Enviar OK                                | ✅            |
| OK (inicio)       | OK             | No          | Sí       | Enviar OK (al iniciar monitor)           | ✅            |
| OK                | OK             | No          | No       | No enviar nada                           | ✅            |
| RESOLVED          | OK             | No          | No       | No enviar nada                           | ✅            |
| OK                | RESOLVED       | No          | No       | No enviar nada                           | ✅            |

## Pasos para cada transición

1. Forzar el estado anterior (simularlo si es necesario, por ejemplo editando status.json o usando el monitor).
2. Cambiar el estado actual según la fila de la tabla.
3. Observar y anotar:
   - Si se envía el correo esperado (tipo y contenido).
   - Si el log muestra el mensaje esperado (ej: RESOLVED, SYNCING, INCIDENTE).
   - Si el dashboard muestra el emoji y mensaje correcto.
4. Para INCIDENTE → SYNCING, verifica que primero se envía RESOLVED y luego SYNCING.
5. Marca cada transición como OK o FALLO según el resultado.

## Notas
- Los emojis deben aparecer siempre en dashboard y correos.
- Si alguna transición no genera notificación cuando debería, anótalo.
- Si se genera notificación cuando NO debería, anótalo.
- Adjunta capturas de pantalla o logs si encuentras un fallo.

---

Marca cada transición como OK o FALLO y anota cualquier observación relevante.
