# Barra de límites para Claude Code

Un mod que dibuja una banda compacta sobre el cuadro de texto de Claude Code:

- El uso de la ventana de 5 horas y la semanal de tu plan: mini barra de 5 segmentos, porcentaje y tiempo hasta el reinicio.
- Los tokens de toda la sesión y su costo equivalente en dólares, al extremo derecho.
- Cuando el contexto pasa de 300k, un aviso con un botón **Compactar** que resume la conversación.

<p align="center">
  <img src="docs/demo.svg" width="760" alt="Se escribe un mensaje y, mientras Claude responde, la barra sobre el cuadro de texto se actualiza: el uso de 5h sube a 40 %, el semanal pasa de 88 % en ámbar a 98 % en rojo, y los tokens y el costo de la sesión suben a 50.2M y $15.75. Luego aparece el aviso de que el contexto va en 360.5k; al pulsar Compactar el aviso desaparece.">
</p>

## Instalación

> [!TIP]
> ### La forma más fácil: pídeselo a Claude
>
> Abre Claude Code (la app de escritorio o la terminal), copia este mensaje, pégalo en el chat y envíalo:
>
> ```text
> Instala el plugin plan-limits del marketplace de GitHub Gonriel-Labs/claude-plan-limits, con alcance de usuario, y activa la actualización automática de ese marketplace (autoUpdate).
> ```
>
> Claude hace el resto. Te pedirá permiso antes de ejecutar los comandos: acéptalo. Cuando termine, **abre una sesión nueva** y la barra aparecerá después de la primera respuesta. Las mejoras te llegarán solas: se descargan mientras usas Claude Code y se activan la próxima vez que lo abras.

> [!NOTE]
> **¿Lo instalaste antes del 19 de noviembre de 2026?** Tu copia no se actualiza sola. Pégale esto a Claude una vez:
>
> ```text
> Actualiza el plugin plan-limits y activa la actualización automática de su marketplace Gonriel-Labs/claude-plan-limits (autoUpdate).
> ```

> [!NOTE]
> **¿No tienes Node.js?** Pídeselo también a Claude en el mismo chat:
>
> ```text
> Instala Node.js en mi computadora.
> ```
>
> Si Windows muestra un aviso de administrador, acéptalo. Luego reinicia Claude Code. Sin Node.js la barra funciona igual, pero el contador de tokens se queda en 0.

### Requisitos

- Claude Code con un plan de suscripción (Pro o Max). Los porcentajes de 5h y semanal solo existen con un plan.
- Node.js, para el contador de tokens.

### Otras formas de instalarlo

En el prompt de una sesión de Claude Code en la terminal:

```
/plugin install plan-limits --marketplace Gonriel-Labs/claude-plan-limits
```

Responde `y` para agregar el marketplace y elige el alcance (usuario, para todas tus sesiones). Para que se actualice solo: `/plugin` → pestaña **Marketplaces** → `claude-plan-limits` → activa la actualización automática.

Desde una terminal:

```bash
claude plugin install plan-limits --marketplace Gonriel-Labs/claude-plan-limits
```

En la app de escritorio, donde `/plugin` no funciona: haz clic en **+** junto al cuadro de texto, luego **Plugins**, **Add marketplace** con `Gonriel-Labs/claude-plan-limits`, y después **Add plugin**.

La barra aparece en una sesión nueva, tras la primera respuesta.

## Desinstalar

```bash
claude plugin uninstall plan-limits
```

## Regenerar la animación

La animación de `docs/demo.svg` se arma con los mismos colores y textos de la barra real. Si cambias la barra, vuelve a generarla (necesita Python 3):

```bash
python tools/escena_demo.py
```
