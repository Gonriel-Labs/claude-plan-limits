# Barra de límites para Claude Code

Un mod que dibuja una banda compacta sobre el cuadro de texto de Claude Code:

- El uso de la ventana de 5 horas y la semanal de tu plan: mini barra de 5 segmentos, porcentaje y tiempo hasta el reinicio.
- Los tokens de toda la sesión y su costo equivalente en dólares, al extremo derecho.
- Cuando el contexto pasa de 250k, un aviso con un botón **Compactar** que resume la conversación.

```
5h  ■■□□□  31%  ↻ 2h 50m   │   Semanal  ■■■■■  97%  ↻ 2d 19h        39.4M tokens  ·  $13.37
──────────────────────────────────────────────────────────────────────────────────────────
▲  El contexto va en 333.2k. Compactar lo resume y abarata las respuestas.       [Compactar]
```

## Requisitos

- Claude Code con un plan de suscripción (los porcentajes de 5h y semanal solo existen con un plan).
- Node.js instalado (el contador de tokens lo usa).

## Instalación

En el prompt de una sesión de Claude Code en la terminal:

```
/plugin install plan-limits --marketplace mark-quispe/claude-plan-limits
```

Responde `y` para agregar el marketplace y elige el alcance (usuario, para todas tus sesiones).

Desde una terminal:

```bash
claude plugin install plan-limits --marketplace mark-quispe/claude-plan-limits
```

En la app de escritorio, donde `/plugin` no funciona: haz clic en **+** junto al cuadro de texto, luego **Plugins**, **Add marketplace** con `mark-quispe/claude-plan-limits`, y después **Add plugin**.

La barra aparece en una sesión nueva, tras la primera respuesta.

## Desinstalar

```bash
claude plugin uninstall plan-limits
```
