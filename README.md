# la-seguridad-de-la-cama

Juego basado en el código base provisto en https://github.com/AlonsoDiCandia/discretizando-el-tiempo-continuo.

El tema del juego es "miedo", y la forma en la se que aplicará en el juego será la siguiente:

El jugador controla a un personaje miedoso, y debe evitar que su medidor de valentía llegue a 0. El objetivo es guiar al personaje a través de un laberinto oscuro hacia su cama, este laberinto oscuro tiene varias celdas de "descanso", donde el jugador podrá rellenar su medidor de valentía. Pero no puede mantenerse ahí, deberá adentrarse a la oscuridad para encontrar el camino que lo lleve a sus lecho. 

Pierdes si el medidor de valentía llega a 0, los controles son WASD.

---
vvv README ORIGINAL vvv
---

# discretizando-el-tiempo-continuo

Para poder levantar el proyecto usted debe ejecutar:

docker compose up -d --build

Luego verifique la url: localhost:8000

Si hay un error de conexion con la base de datos, cambiar 'db' por localhost o docker.internal.host o llame al profesor