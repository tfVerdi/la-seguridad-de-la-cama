# Dejar el laberinto funcional
Para dejar funcionando el laberinto hacemos lo siguiente:
## Pedirle a la IA que haga el código más entendible (xd sorry)
Para que sea más fácil saber donde tengo que meter las cosas que quiera hacer ajaja
# Definición y ejecución de temática
El tema es "miedo", y la forma en la se que aplicará en el juego será la siguiente:

El jugador controla a un personaje miedoso, y debe evitar que su medidor de valentía llegue a 0. El objetivo es guiar al personaje a través de un laberinto oscuro hacia su cama, este laberinto oscuro tendrá varias celdas de "descanso", donde el jugador podrá rellenar su medidor de valentía. Pero no puede mantenerse ahí, deberá adentrarse a la oscuridad para encontrar el camino que lo lleve a sus lecho. 

==🟢Si el medidor llega a 0, la forma de indicar que perdió será que el personaje va a *miccionar* en su celda y celdas libres adyacentes. (jeje)== (PENDIENTE)
## Modíficamos la meta
Aprovecharemos el hecho de que las celdas de las esquinas siempre están libres y dejaremos predefinida la meta en la celda de abajo a la derecha. 

También reemplazamos el rectangulo rojo con el sprite 100x100 hecho en gimp de una cama (`/static/cama.png`). Esto por la temática planeada que se explicará posteriormente.
## Agregando efecto de oscuridad
Para añadir el efecto de la oscuridad, se usan 4 iluminaciones distintas, se identifican con variables constantes que funcionan como enums, igual que los tipos de celdas.

Usando la librería math sacamos la distancia desde el jugador a la celda a iluminar y le ponemos la cantidad de iluminación que corresponda (sólo los valores predeterminados en el diccionario `MULTIPLICADOR_ILUMINACION`), además si estámos en una celda "descanso", el radio de iluminación es mayor.
## Iniciamos las colisiones con las paredes
Para esto, antes de mover al jugador tenemos que revisar si la celda destino es pared. Es importante **no** revisar sólo si la celda está libre, si no que revisar si la celda destino es *específicamente* pared, así no tendremos que rehacer la lógica cuando querramos agregar otras celdas que no sean pared o libre. 

~~Bajo la misma lógica, también puede ser viable crear una clase `Celda`, la cual contenga un atributo `tiene_colision`para posteriormente poder crear distintos subtipos de celdas que puedan funcionar o no funcionar como lo hacen actualmente las paredes .~~ ==🔴Descartado por tiempo, se terminó usando los valores númericos debido a que sólo se hará un tipo de celda extra.==
# Lógica de generación de celdas de descanso
Usando el algoritmo DFS de generación de laberinto, hacemos que se generen de forma aleatoria pero controlada las celdas de descanso. Para esto contamos los saltos que da el algoritmo, y cuando sobrepasa los 15 (número definido testeando valores) genera una celda de descanso entre las celdas del último salto. 
# Lógica de "valentía"
Para el medidor de valentía, cada salto del personaje gasta 3 de energía, y estar en una celda de descanso regenera valentía (12 valentia/s) para poder seguir el camino.

Debido a que el programa no generaba imágen hasta que el jugador se moviese, no era posible ver como aumentaba el medidor en tiempo real, por lo que se tuvo que modíficar el JS para que generara una imágen cada 500ms si el jugador no se está moviendo.

Como fue mencionado anteriormente, si el personaje se queda sin valentía, pierdes el juego y tienes que reiniciar.