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


def srtf(procesos):
    """Shortest Remaining Time First (SRTF): versión expropiativa de SJF.
    En cada unidad de tiempo se ejecuta el proceso con menor tiempo restante."""
    pendientes = sorted(procesos, key=lambda p: p["llegada"])
    restante = {p["nombre"]: p["rafaga"] for p in procesos}
    completados = set()
    tiempo = 0
    gantt = []
    n = len(procesos)

    while len(completados) < n:
        # Procesos que ya llegaron y no han terminado
        listos = [p for p in pendientes if p["llegada"] <= tiempo and p["nombre"] not in completados]

        if not listos:
            # Nadie ha llegado: la CPU espera al siguiente proceso
            futuros = [p for p in pendientes if p["nombre"] not in completados]
            siguiente = min(p["llegada"] for p in futuros)
            gantt.append({"nombre": OCIOSO, "inicio": tiempo, "fin": siguiente})
            tiempo = siguiente
            continue

        # Elegir el de menor tiempo restante (empate: el que llegó primero)
        elegido = min(listos, key=lambda p: (restante[p["nombre"]], p["llegada"]))

        # Determinar cuánto tiempo puede ejecutar antes de una posible expropiación
        # (hasta que llegue otro proceso o termine)
        proxima_llegada = None
        for p in pendientes:
            if p["llegada"] > tiempo and p["nombre"] not in completados:
                proxima_llegada = p["llegada"]
                break

        if proxima_llegada is not None:
            duracion = min(restante[elegido["nombre"]], proxima_llegada - tiempo)
        else:
            duracion = restante[elegido["nombre"]]

        gantt.append({"nombre": elegido["nombre"], "inicio": tiempo, "fin": tiempo + duracion})
        tiempo += duracion
        restante[elegido["nombre"]] -= duracion

        if restante[elegido["nombre"]] == 0:
            completados.add(elegido["nombre"])

    return gantt


def mlq(procesos, quantum=2):
    """Multilevel Queue (MLQ): 3 niveles de colas.
    Cola 1 (prioridad 1-2): Round Robin con quantum 2 — Mayor prioridad
    Cola 2 (prioridad 3-4): Round Robin con quantum 4 — Prioridad media
    Cola 3 (prioridad 5+):  FCFS — Menor prioridad

    Las colas se atienden en orden estricto: Cola 1 > Cola 2 > Cola 3.
    Un proceso de una cola inferior solo se ejecuta si las colas superiores están vacías."""

    # Clasificar procesos en colas
    cola1_procs = sorted([p for p in procesos if p["prioridad"] <= 2], key=lambda p: p["llegada"])
    cola2_procs = sorted([p for p in procesos if 3 <= p["prioridad"] <= 4], key=lambda p: p["llegada"])
    cola3_procs = sorted([p for p in procesos if p["prioridad"] >= 5], key=lambda p: p["llegada"])

    restante = {p["nombre"]: p["rafaga"] for p in procesos}
    completados = set()
    tiempo = 0
    gantt = []
    n = len(procesos)

    # Colas con sus quantums (cola3 usa FCFS = quantum infinito)
    cola1 = deque()
    cola2 = deque()
    cola3 = deque()

    i1, i2, i3 = 0, 0, 0  # índices de llegada

    def encolar_llegadas():
        nonlocal i1, i2, i3
        while i1 < len(cola1_procs) and cola1_procs[i1]["llegada"] <= tiempo:
            if cola1_procs[i1]["nombre"] not in completados:
                cola1.append(cola1_procs[i1])
            i1 += 1
        while i2 < len(cola2_procs) and cola2_procs[i2]["llegada"] <= tiempo:
            if cola2_procs[i2]["nombre"] not in completados:
                cola2.append(cola2_procs[i2])
            i2 += 1
        while i3 < len(cola3_procs) and cola3_procs[i3]["llegada"] <= tiempo:
            if cola3_procs[i3]["nombre"] not in completados:
                cola3.append(cola3_procs[i3])
            i3 += 1

    encolar_llegadas()

    while len(completados) < n:
        encolar_llegadas()

        if cola1:
            # Cola 1: RR con quantum 2
            p = cola1.popleft()
            uso = min(2, restante[p["nombre"]])

            # Verificar si llega alguien de cola1 durante la ejecución
            gantt.append({"nombre": p["nombre"], "inicio": tiempo, "fin": tiempo + uso})
            tiempo += uso
            restante[p["nombre"]] -= uso
            encolar_llegadas()

            if restante[p["nombre"]] > 0:
                cola1.append(p)
            else:
                completados.add(p["nombre"])

        elif cola2:
            # Cola 2: RR con quantum 4
            p = cola2.popleft()
            uso = min(4, restante[p["nombre"]])

            # Verificar si llega alguien de cola1 durante la ejecución (expropiación por cola superior)
            proxima_c1 = None
            for proc in cola1_procs[i1:]:
                if proc["llegada"] > tiempo:
                    proxima_c1 = proc["llegada"]
                    break

            if proxima_c1 is not None and proxima_c1 < tiempo + uso:
                uso = proxima_c1 - tiempo

            gantt.append({"nombre": p["nombre"], "inicio": tiempo, "fin": tiempo + uso})
            tiempo += uso
            restante[p["nombre"]] -= uso
            encolar_llegadas()

            if restante[p["nombre"]] > 0:
                cola2.append(p)
            else:
                completados.add(p["nombre"])

        elif cola3:
            # Cola 3: FCFS (ejecutar completo, pero puede ser interrumpido por colas superiores)
            p = cola3.popleft()
            uso = restante[p["nombre"]]

            # Verificar si llega alguien de cola1 o cola2 durante la ejecución
            proxima_superior = None
            for proc in cola1_procs[i1:]:
                if proc["llegada"] > tiempo:
                    proxima_superior = proc["llegada"]
                    break
            for proc in cola2_procs[i2:]:
                if proc["llegada"] > tiempo:
                    if proxima_superior is None or proc["llegada"] < proxima_superior:
                        proxima_superior = proc["llegada"]
                    break

            if proxima_superior is not None and proxima_superior < tiempo + uso:
                uso = proxima_superior - tiempo

            gantt.append({"nombre": p["nombre"], "inicio": tiempo, "fin": tiempo + uso})
            tiempo += uso
            restante[p["nombre"]] -= uso
            encolar_llegadas()

            if restante[p["nombre"]] > 0:
                cola3.append(p)
            else:
                completados.add(p["nombre"])

        else:
            # Ninguna cola tiene procesos, avanzar al próximo que llegue
            futuros = []
            if i1 < len(cola1_procs):
                futuros.append(cola1_procs[i1]["llegada"])
            if i2 < len(cola2_procs):
                futuros.append(cola2_procs[i2]["llegada"])
            if i3 < len(cola3_procs):
                futuros.append(cola3_procs[i3]["llegada"])

            if not futuros:
                break

            siguiente = min(futuros)
            gantt.append({"nombre": OCIOSO, "inicio": tiempo, "fin": siguiente})
            tiempo = siguiente

    return gantt


def ejecutar(algoritmo, procesos, quantum=2):
    if algoritmo == "FIFO":
        return fifo(procesos)
    if algoritmo == "SJF":
        return sjf(procesos)
    if algoritmo == "Prioridad":
        return prioridad(procesos)
    if algoritmo == "Round Robin":
        return round_robin(procesos, quantum)
    if algoritmo == "SRTF":
        return srtf(procesos)
    if algoritmo == "MLQ":
        return mlq(procesos, quantum)
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


def comparar(procesos, quantum):
    """Ejecuta los 4 algoritmos con los mismos procesos y devuelve sus promedios."""
    resultados = []
    for nombre in ["FIFO", "SJF", "Prioridad", "Round Robin"]:
        gantt = ejecutar(nombre, procesos, quantum)
        _, espera, sistema = calcular_tiempos(procesos, gantt)
        resultados.append({"algoritmo": nombre, "espera": espera, "sistema": sistema})
    return resultados


def comparar_extras(procesos, quantum):
    """Ejecuta los 2 algoritmos extras con los mismos procesos y devuelve sus promedios."""
    resultados = []
    for nombre in ["SRTF", "MLQ"]:
        gantt = ejecutar(nombre, procesos, quantum)
        _, espera, sistema = calcular_tiempos(procesos, gantt)
        resultados.append({"algoritmo": nombre, "espera": espera, "sistema": sistema})
    return resultados


def mejores(resultados, campo):
    """Nombres de los algoritmos con el menor valor en `campo` (puede haber empate)."""
    minimo = min(round(r[campo], 2) for r in resultados)
    return [r["algoritmo"] for r in resultados if round(r[campo], 2) == minimo]
