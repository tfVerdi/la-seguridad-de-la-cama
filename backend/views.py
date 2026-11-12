import os
import random
import time

import cv2
import numpy as np
import math
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from backend.models import Personaje, PersonajeSeleccionado
from backend.generar_imagen.Jugador import Jugador

# ---------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------
ANCHO_TABLERO = 1200
ALTO_TABLERO = 500
PATH = os.getcwd()
PATH_CAMA = "/static/cama.png"

COLUMNAS = 31
FILAS = 13
TAMANO_CELDA_X = ANCHO_TABLERO // COLUMNAS   # 38 px
TAMANO_CELDA_Y = ALTO_TABLERO // FILAS       # 38 px

LIBRE = 0
PARED = 1
DESCANSO = 2

ILUMINADO = 0
MEDIO_ILUMINADO = 1
MEDIO_OSCURO = 2
OSCURO = 3

SALTOS_ANTES_DE_DESCANSO = 15

COLOR_FONDO = (81, 137, 181)
COLOR_PARED = (201, 196, 212)
COLOR_DESCANSO = (190, 190, 250)

INICIO_X = TAMANO_CELDA_X
INICIO_Y = TAMANO_CELDA_Y

META_COLUMNA = COLUMNAS - 2
META_FILA = FILAS - 2

RADIO_LIBRE = 3
RADIO_DESCANSO = 5

MULTIPLICADOR_ILUMINACION = {
    ILUMINADO: 1,
    MEDIO_ILUMINADO: .7,
    MEDIO_OSCURO: .3,
    OSCURO: .2
}

VALENTIA_MAX = 100
VALENTIA_PERDIDA = 3
VALENTIA_RECARGA_POR_SEGUNDO = 12

# ---------------------------------------------------------------
# Laberinto
# ---------------------------------------------------------------
def crear_matriz(columnas, filas, valor_default):
    matriz = [[valor_default] * columnas for _ in range(filas)]
    return matriz


def crear_matriz_laberinto(columnas, filas):
    """Devuelve una matriz filas x columnas con PARED (1), LIBRE (0) y DESCANSO (2).

    Usa un recorrido en profundidad aleatorio: salta de 2 en 2 celdas
    y abre también la celda intermedia, para que queden paredes entre pasillos.
    """
    contador_de_saltos = 0

    # El algoritmo necesita un tamaño impar para que las paredes caigan en el borde
    matriz = crear_matriz(columnas, filas, PARED)
    limite_x = columnas if columnas % 2 != 0 else columnas + 1
    limite_y = filas if filas % 2 != 0 else filas + 1

    def saltos_posibles(x, y):
        """Celdas a 2 pasos que siguen siendo pared (aún no visitadas)."""
        destinos = []
        for salto_x, salto_y in [(0, -2), (0, 2), (-2, 0), (2, 0)]:
            destino_x, destino_y = x + salto_x, y + salto_y
            dentro = 0 < destino_x < limite_x - 1 and 0 < destino_y < limite_y - 1
            if dentro and matriz[destino_y][destino_x] == PARED:
                destinos.append((destino_x, destino_y))
        return destinos

    pila = [(1, 1)]
    matriz[1][1] = LIBRE

    while pila:
        x, y = pila[-1]
        destinos = saltos_posibles(x, y)

        if destinos:
            destino_x, destino_y = random.choice(destinos)
            # Abrir la celda intermedia y la celda destino
            if contador_de_saltos > SALTOS_ANTES_DE_DESCANSO:
                matriz[(y + destino_y) // 2][(x + destino_x) // 2] = DESCANSO
                contador_de_saltos = 0
            else:
                matriz[(y + destino_y) // 2][(x + destino_x) // 2] = LIBRE

            matriz[destino_y][destino_x] = LIBRE
            pila.append((destino_x, destino_y))
        else:
            pila.pop()  # callejón sin salida: retroceder
        contador_de_saltos += 1

    return matriz


def crear_matriz_iluminacion(columnas, filas, jugador_col, jugador_fila, celda_actual_jugador):
    matriz = crear_matriz(columnas, filas, OSCURO)
    radio = RADIO_DESCANSO if celda_actual_jugador == DESCANSO else RADIO_LIBRE

    for fila in range(max(0, jugador_fila - radio), min(filas, jugador_fila + radio + 1)):
        for col in range(max(0, jugador_col - radio), min(columnas, jugador_col + radio + 1)):
            distancia = math.hypot(col - jugador_col, fila - jugador_fila)
            if distancia > radio:
                continue

            nivel = min(int(distancia / radio * 3), MEDIO_OSCURO)
            matriz[fila][col] = nivel

    return matriz


def es_transitable(matriz, x, y):
    columna = x // TAMANO_CELDA_X
    fila = y // TAMANO_CELDA_Y
    dentro = 0 <= fila < len(matriz) and 0 <= columna < len(matriz[0])
    return dentro and matriz[fila][columna] != PARED


def gastar_valentia(valentia, celda):
    if celda == DESCANSO:
        return valentia
    return max(0, valentia - VALENTIA_PERDIDA)


def recargar_valentia(valentia, segundos):
    return min(VALENTIA_MAX, valentia + VALENTIA_RECARGA_POR_SEGUNDO * segundos)


# ---------------------------------------------------------------
# Dibujo
# ---------------------------------------------------------------
def cargar_sprite(personaje_db):
    """Carga la imagen del personaje ajustada al tamaño de una celda."""
    try:
        sprite = cv2.imread(PATH + personaje_db.imagen.url)
        return cv2.resize(sprite, (TAMANO_CELDA_X, TAMANO_CELDA_Y))
    except Exception:
        return np.zeros((30, 30, 3), dtype=np.uint8)  # cuadrado negro de respaldo


def atenuar(color, nivel, factor_maximo=1.0):
    factor = min(MULTIPLICADOR_ILUMINACION[nivel], factor_maximo)
    return tuple(int(c * factor) for c in color)


def dibujar_laberinto(img, matriz_laberinto, matriz_iluminacion):
    for fila, linea in enumerate(matriz_laberinto):
        for columna, celda in enumerate(linea):
            esquina_1 = (columna * TAMANO_CELDA_X, fila * TAMANO_CELDA_Y)
            esquina_2 = ((columna + 1) * TAMANO_CELDA_X, (fila + 1) * TAMANO_CELDA_Y)
            nivel = matriz_iluminacion[fila][columna]

            if celda == PARED:
                color = atenuar(COLOR_PARED, nivel, MULTIPLICADOR_ILUMINACION[MEDIO_ILUMINADO])
            elif celda == DESCANSO:
                color = atenuar(COLOR_DESCANSO, nivel)
            else:
                color = atenuar(COLOR_FONDO, nivel)
            cv2.rectangle(img, esquina_1, esquina_2, color, -1)


def dibujar_meta(img, matriz_iluminacion):
    """Pega la cama en la celda de la meta, atenuada según la luz de esa celda."""
    x = META_COLUMNA * TAMANO_CELDA_X
    y = META_FILA * TAMANO_CELDA_Y

    sprite = cv2.imread(PATH + PATH_CAMA)
    if sprite is None:
        sprite = np.zeros((TAMANO_CELDA_Y, TAMANO_CELDA_X, 3), dtype=np.uint8)
    sprite = cv2.resize(sprite, (TAMANO_CELDA_X, TAMANO_CELDA_Y))

    factor = MULTIPLICADOR_ILUMINACION[matriz_iluminacion[META_FILA][META_COLUMNA]]
    img[y:y + TAMANO_CELDA_Y, x:x + TAMANO_CELDA_X] = (sprite * factor).astype(np.uint8)


def dibujar_barra_valentia(img, valentia):
    """Barra sobre la fila de pared superior (siempre es pared, así que no tapa nada).

    Roja cuando está vacía, verde cuando está llena.
    """
    x0, y0 = 10, 9
    ancho, alto = 300, 20

    proporcion = max(0.0, min(1.0, valentia / VALENTIA_MAX))
    color = (0, int(255 * proporcion), int(255 * (1 - proporcion)))  # BGR

    cv2.rectangle(img, (x0, y0), (x0 + ancho, y0 + alto), (255, 255, 255), 2)
    cv2.rectangle(
        img,
        (x0 + 2, y0 + 2),
        (x0 + 2 + int((ancho - 4) * proporcion), y0 + alto - 2),
        color,
        -1,
    )
    cv2.putText(
        img, f"VALENTIA {int(valentia)}/{VALENTIA_MAX}", (x0 + ancho + 15, y0 + 17),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA,
    )


def _texto_centrado(img, texto, y, escala, color, grosor):
    fuente = cv2.FONT_HERSHEY_SIMPLEX
    (ancho, _), _ = cv2.getTextSize(texto, fuente, escala, grosor)
    cv2.putText(img, texto, ((ANCHO_TABLERO - ancho) // 2, y),
                fuente, escala, color, grosor, cv2.LINE_AA)


def dibujar_game_over(img):
    """Oscurece el último frame y escribe el mensaje encima.

    Sin tildes ni ñ: las fuentes de OpenCV no las soportan.
    """
    img = (img * 0.25).astype(np.uint8)
    _texto_centrado(img, "GAME OVER", ALTO_TABLERO // 2, 3, (0, 0, 255), 6)
    _texto_centrado(img, "Te quedaste sin valentia", ALTO_TABLERO // 2 + 60, 1, (255, 255, 255), 2)
    _texto_centrado(img, "Pulsa Reiniciar Laberinto para reintentarlo", ALTO_TABLERO // 2 + 105, 0.8, (180, 180, 180), 2)
    return img


def dibujar_victoria(img, valentia):
    """Atenúa el último frame y escribe el mensaje de victoria encima."""
    img = (img * 0.35).astype(np.uint8)
    _texto_centrado(img, "GANASTE", ALTO_TABLERO // 2, 3, (0, 200, 0), 6)
    _texto_centrado(img, f"Llegaste a la cama con {int(valentia)} de valentia", ALTO_TABLERO // 2 + 60, 1, (255, 255, 255), 2)
    _texto_centrado(img, "Pulsa Reiniciar Laberinto para jugar de nuevo", ALTO_TABLERO // 2 + 105, 0.8, (180, 180, 180), 2)
    return img


def dibujar_frame(matriz_laberinto, matriz_iluminacion, sprite, x, y, valentia, game_over, victoria):
    """Compone la imagen completa: fondo, laberinto, meta, personaje y energía."""
    img = np.full((ALTO_TABLERO, ANCHO_TABLERO, 3), COLOR_FONDO, dtype=np.uint8)
    dibujar_laberinto(img, matriz_laberinto, matriz_iluminacion)
    dibujar_meta(img, matriz_iluminacion)  # antes del personaje, para que este quede encima

    alto_sprite, ancho_sprite = sprite.shape[:2]
    img[y:y + alto_sprite, x:x + ancho_sprite] = sprite

    dibujar_barra_valentia(img, valentia)
    if victoria:
        img = dibujar_victoria(img, valentia)
    elif game_over:
        img = dibujar_game_over(img)
    return img


# ---------------------------------------------------------------
# Estado de la partida
# ---------------------------------------------------------------
def cargar_partida(request, reiniciar):
    """Devuelve (matriz, x, y, valentia, game_over, victoria). Crea un laberinto nuevo si hace falta."""
    if "laberinto" not in request.session or reiniciar:
        request.session["laberinto"] = crear_matriz_laberinto(COLUMNAS, FILAS)
        request.session["pos_x"] = INICIO_X
        request.session["pos_y"] = INICIO_Y
        request.session["valentia"] = VALENTIA_MAX
        request.session["game_over"] = False
        request.session["victoria"] = False
        request.session["ultimo_tick"] = time.time()

    return (
        request.session["laberinto"],
        request.session.get("pos_x", INICIO_X),
        request.session.get("pos_y", INICIO_Y),
        request.session.get("valentia", VALENTIA_MAX),
        request.session.get("game_over", False),
        request.session.get("victoria", False),
    )


# ---------------------------------------------------------------
# Views
# ---------------------------------------------------------------
def seleccion_personaje(request):
    personajes = [
        {"id": p.id, "nombre": p.nombre, "imagen_url": p.imagen.url}
        for p in Personaje.objects.all()
    ]

    seleccion = PersonajeSeleccionado.objects.first()
    personaje_seleccionado = None
    if seleccion and seleccion.seleccionado:
        personaje_seleccionado = {
            "nombre": seleccion.seleccionado.nombre,
            "imagen_url": seleccion.seleccionado.imagen.url,
        }

    return render(request, "seleccion_personaje.html", {
        "personajes": personajes,
        "personaje_seleccionado": personaje_seleccionado,
    })


@require_POST
def seleccionar_personaje(request, id):
    personaje = get_object_or_404(Personaje, id=id)
    seleccion = PersonajeSeleccionado.objects.first()

    if seleccion:
        seleccion.seleccionado = personaje
        seleccion.save()
    else:
        PersonajeSeleccionado.objects.create(seleccionado=personaje)

    return JsonResponse({"id": personaje.id, "nombre": personaje.nombre})


def generar_imagen(request):
    seleccion = PersonajeSeleccionado.objects.first()
    if not seleccion or not seleccion.seleccionado:
        return HttpResponse("No hay personaje seleccionado", status=400)

    personaje_db = seleccion.seleccionado
    tecla = request.GET.get("tecla", "")
    reiniciar = request.GET.get("nuevo_juego") == "1"

    sprite = cargar_sprite(personaje_db)
    matriz_laberinto, x, y, valentia, game_over, victoria = cargar_partida(request, reiniciar)

    tiempo_actual = time.time()
    segundos = tiempo_actual - request.session.get("ultimo_tick", tiempo_actual)

    if not game_over and not victoria:
        celda_antes = matriz_laberinto[y // TAMANO_CELDA_Y][x // TAMANO_CELDA_X]
        if celda_antes == DESCANSO and valentia < VALENTIA_MAX:
            valentia = recargar_valentia(valentia, segundos)
            request.session["valentia"] = valentia
            request.session["ultimo_tick"] = tiempo_actual

        if tecla:
            personaje_db.x, personaje_db.y = x, y
            jugador = Jugador(personaje_db, velocidad=TAMANO_CELDA_X)
            nuevo_x, nuevo_y = jugador.movimiento_personaje(tecla)

            if es_transitable(matriz_laberinto, nuevo_x, nuevo_y):
                x, y = nuevo_x, nuevo_y
                celda_nueva = matriz_laberinto[y // TAMANO_CELDA_Y][x // TAMANO_CELDA_X]
                valentia = gastar_valentia(valentia, celda_nueva)
                victoria = (x // TAMANO_CELDA_X, y // TAMANO_CELDA_Y) == (META_COLUMNA, META_FILA)
                game_over = valentia <= 0 and not victoria

                request.session["pos_x"] = x
                request.session["pos_y"] = y
                request.session["valentia"] = valentia
                request.session["game_over"] = game_over
                request.session["victoria"] = victoria
                request.session["ultimo_tick"] = tiempo_actual

    personaje_db.x = x
    personaje_db.y = y
    personaje_db.save()

    columnas = x // TAMANO_CELDA_X
    filas = y // TAMANO_CELDA_Y
    celda_actual = matriz_laberinto[filas][columnas]

    matriz_iluminacion = crear_matriz_iluminacion(
        len(matriz_laberinto[0]), len(matriz_laberinto), columnas, filas, celda_actual
    )
    img = dibujar_frame(matriz_laberinto, matriz_iluminacion, sprite, x, y, valentia, game_over, victoria)
    ok, buffer = cv2.imencode(".jpg", img)
    return HttpResponse(buffer.tobytes(), content_type="image/jpeg")


def tablero(request):
    return render(request, "tablero.html")
