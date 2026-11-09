# Guía de Seguridad y Protección del Proyecto RADAR LAB
## ¿Cómo proteger tu aplicación y no perder los derechos?
Tener el código en un repositorio público de GitHub NO significa que cualquiera pueda quitarte el proyecto o la aplicación.
1. **Derechos de Autor:** En el momento en que escribes una línea de código original, esta es tuya. Tienes el copyright automáticamente. GitHub guarda un registro exacto de la fecha y hora de tu primer commit, lo que sirve como prueba legal.
2. **Público no significa Libre:** Que el código sea visible NO da permiso legal para usarlo. Si no hay una licencia, la ley dicta "Todos los derechos reservados". Cualquiera puede mirar para aprender, pero no pueden usarlo ni venderlo.
3. **Los "Forks" (Copias):** Si alguien hace un Fork de tu repositorio, se crea una copia en su perfil. No te quitan nada; tu repositorio original sigue intacto y siempre se mostrará un enlace que indica que TÚ eres el creador original.
## Estrategias de Protección
- **Añadir una Licencia:** Si quieres que lo vean pero no que lo vendan como suyo, usa licencias como AGPL-3.0 o GPL-3.0. Son "virales" y obligan a que cualquier modificación del código sea también de código abierto.
- **Mantener lo valioso en secreto:** Lo que realmente vale de RADAR LAB no es el código, sino:
  * Los prompts de IA (pueden ir en una base de datos privada, no en el código).
  * Las claves de API (ya protegidas con .gitignore).
  * La base de datos de clientes.
- **Volverlo a poner privado:** En GitHub, ve a Settings > Danger Zone > Change visibility. Si nadie más lo ve, no pueden copiarlo.
## Equilibrio recomendado
1. Añadir un archivo `LICENSE` (ej. MIT o AGPL) para tener tranquilidad legal.
2. Nunca subir el archivo `.env` real.
3. Disfrutar de que sea público para usarlo en el CV, LinkedIn o portafolio, generando oportunidades profesionales.