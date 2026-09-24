"""Algoritmos de planificación de CPU (lógica pura, sin interfaz).

Cada proceso es un diccionario:
    {"nombre": "P1", "llegada": 0, "rafaga": 5, "prioridad": 2}

Cada algoritmo devuelve la lista de bloques del diagrama de Gantt:
    {"nombre": "P1", "inicio": 0, "fin": 5}

Cuando la CPU no tiene nada que hacer se agrega un bloque "Ocioso".
"""

from collections import deque

OCIOSO = "Ocioso"


def _no_expropiativo(procesos, criterio):
    """Base de FIFO, SJF y Prioridad: en cada paso se elige, entre los
    procesos que ya llegaron, el que tenga el menor valor según `criterio`,
    y se ejecuta completo."""
    pendientes = sorted(procesos, key=lambda p: p["llegada"])
    tiempo = 0
    gantt = []

    while pendientes:
        listos = [p for p in pendientes if p["llegada"] <= tiempo]

        if not listos:
            # Nadie ha llegado: la CPU espera al siguiente proceso
            siguiente = pendientes[0]["llegada"]
            gantt.append({"nombre": OCIOSO, "inicio": tiempo, "fin": siguiente})
            tiempo = siguiente
            continue

        p = min(listos, key=criterio)
        gantt.append({"nombre": p["nombre"], "inicio": tiempo, "fin": tiempo + p["rafaga"]})
        tiempo += p["rafaga"]
        pendientes.remove(p)

    return gantt


def fifo(procesos):
    # El que llegó primero
    return _no_expropiativo(procesos, lambda p: p["llegada"])


def sjf(procesos):
    # La ráfaga más corta (si empatan, el que llegó primero)
    return _no_expropiativo(procesos, lambda p: (p["rafaga"], p["llegada"]))


def prioridad(procesos):
    # El número de prioridad más bajo = más importante
    return _no_expropiativo(procesos, lambda p: (p["prioridad"], p["llegada"]))


def round_robin(procesos, quantum):
    pendientes = sorted(procesos, key=lambda p: p["llegada"])
    restante = {p["nombre"]: p["rafaga"] for p in procesos}
    cola = deque()
    tiempo = 0
    gantt = []
    i = 0  # índice del próximo proceso por llegar

    def encolar_llegadas():
        nonlocal i
        while i < len(pendientes) and pendientes[i]["llegada"] <= tiempo:
            cola.append(pendientes[i])
            i += 1

    encolar_llegadas()
    while cola or i < len(pendientes):
        if not cola:
            siguiente = pendientes[i]["llegada"]
            gantt.append({"nombre": OCIOSO, "inicio": tiempo, "fin": siguiente})
            tiempo = siguiente
            encolar_llegadas()
            continue

        p = cola.popleft()
        uso = min(quantum, restante[p["nombre"]])
        gantt.append({"nombre": p["nombre"], "inicio": tiempo, "fin": tiempo + uso})
        tiempo += uso
        restante[p["nombre"]] -= uso

        # Los que llegaron durante este turno entran a la cola antes
        # que el proceso que acaba de salir de la CPU
        encolar_llegadas()
        if restante[p["nombre"]] > 0:
            cola.append(p)

    return gantt


def ejecutar(algoritmo, procesos, quantum=2):
    if algoritmo == "FIFO":
        return fifo(procesos)
    if algoritmo == "SJF":
        return sjf(procesos)
    if algoritmo == "Prioridad":
        return prioridad(procesos)
    return round_robin(procesos, quantum)


def calcular_tiempos(procesos, gantt):
    """Tiempo de sistema = fin - llegada.  Tiempo de espera = sistema - ráfaga."""
    filas = []
    for p in procesos:
        fin = max(b["fin"] for b in gantt if b["nombre"] == p["nombre"])
        sistema = fin - p["llegada"]
        espera = sistema - p["rafaga"]
        filas.append({**p, "fin": fin, "sistema": sistema, "espera": espera})

    prom_espera = sum(f["espera"] for f in filas) / len(filas)
    prom_sistema = sum(f["sistema"] for f in filas) / len(filas)
    return filas, prom_espera, prom_sistema
