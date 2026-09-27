"""Página de Análisis Avanzado: Barrido de Quantum, Recomendador y Monte Carlo."""

import random
import math

import reflex as rx

from . import algoritmos

COLORES = [
    "#8b5cf6", "#06b6d4", "#f43f5e", "#f59e0b", "#10b981",
    "#3b82f6", "#ec4899", "#84cc16", "#f97316", "#14b8a6",
]
MAX_PROCESOS = 10


def crear_proceso(n, llegada, rafaga, prioridad):
    return {
        "nombre": f"P{n}",
        "llegada": str(llegada),
        "rafaga": str(rafaga),
        "prioridad": str(prioridad),
        "color": COLORES[(n - 1) % len(COLORES)],
    }


# =====================================================================
#  ESTADO PARA ANÁLISIS
# =====================================================================
class AnalisisState(rx.State):
    # ---------- Procesos compartidos ----------
    procesos_analisis: list[dict[str, str]] = [
        crear_proceso(1, 0, 5, 3),
        crear_proceso(2, 1, 3, 1),
        crear_proceso(3, 2, 8, 4),
        crear_proceso(4, 3, 6, 2),
        crear_proceso(5, 4, 2, 5),
    ]
    error_analisis: str = ""

    # ---------- Tab activa ----------
    tab_activa: str = "quantum"

    # ===================== 1. BARRIDO DE QUANTUM =====================
    quantum_sweep_data: list[dict[str, str]] = []
    quantum_optimo: str = ""
    quantum_optimo_espera: str = ""
    sweep_ejecutado: bool = False
    # Gantt del quantum seleccionado en la gráfica
    quantum_seleccionado: str = ""
    gantt_sweep_segmentos: list[dict[str, str]] = []
    gantt_sweep_procesos: list[dict[str, str]] = []
    gantt_sweep_marcas: list[dict[str, str]] = []
    gantt_sweep_visible: bool = False

    @rx.var
    def gantt_sweep_altura(self) -> str:
        if not self.procesos_analisis:
            return "100px"
        return f"{len(self.procesos_analisis) * 44 + 8}px"

    # ===================== 3. MONTE CARLO =====================
    mc_num_escenarios: str = "200"
    mc_min_llegada: str = "0"
    mc_max_llegada: str = "10"
    mc_min_rafaga: str = "1"
    mc_max_rafaga: str = "10"
    mc_min_prioridad: str = "1"
    mc_max_prioridad: str = "5"
    mc_min_procesos: str = "3"
    mc_max_procesos: str = "8"

    mc_ejecutado: bool = False
    mc_ejecutando: bool = False
    mc_progreso: int = 0
    mc_total: int = 0

    # Resultados: conteo de victorias
    mc_victorias: list[dict[str, str]] = []
    # Estadísticas por algoritmo: {algoritmo, promedio, desv, minimo, maximo}
    mc_estadisticas: list[dict[str, str]] = []
    # Datos para barras de distribución
    mc_distribucion: list[dict[str, str]] = []

    # Datos numéricos para gráficas recharts
    # Bar chart de victorias: [{name, victorias, fill}]
    mc_chart_victorias: list[dict] = []
    # Bar chart de promedios: [{name, promedio, minimo, maximo, fill}]
    mc_chart_promedios: list[dict] = []
    # Line chart de victoria acumulada: [{escenario, FIFO, SJF, Prioridad, RoundRobin}]
    mc_chart_evolucion: list[dict] = []

    # ---------- Edición de la tabla ----------
    @rx.event
    def set_tab_activa(self, valor: str):
        self.tab_activa = valor

    @rx.event
    def editar_analisis(self, i: int, campo: str, valor: str):
        procesos = [dict(p) for p in self.procesos_analisis]
        procesos[i][campo] = valor
        self.procesos_analisis = procesos
        self._limpiar_resultados()

    @rx.event
    def agregar_analisis(self):
        if len(self.procesos_analisis) < MAX_PROCESOS:
            n = len(self.procesos_analisis) + 1
            self.procesos_analisis = self.procesos_analisis + [crear_proceso(n, n - 1, 3, n)]
            self._limpiar_resultados()

    @rx.event
    def eliminar_analisis(self, i: int):
        if len(self.procesos_analisis) > 1:
            restantes = [p for j, p in enumerate(self.procesos_analisis) if j != i]
            self.procesos_analisis = [
                crear_proceso(n, p["llegada"], p["rafaga"], p["prioridad"])
                for n, p in enumerate(restantes, start=1)
            ]
            self._limpiar_resultados()

    @rx.event
    def aleatorio_analisis(self):
        cantidad = random.randint(4, 6)
        self.procesos_analisis = [
            crear_proceso(n, random.randint(0, 8), random.randint(1, 8), random.randint(1, 5))
            for n in range(1, cantidad + 1)
        ]
        self._limpiar_resultados()

    def _limpiar_resultados(self):
        self.sweep_ejecutado = False
        self.quantum_sweep_data = []
        self.gantt_sweep_visible = False

        self.mc_ejecutado = False
        self.error_analisis = ""

    def _leer_procesos_analisis(self):
        datos = []
        for p in self.procesos_analisis:
            try:
                llegada, rafaga = int(p["llegada"]), int(p["rafaga"])
                prioridad = int(p["prioridad"] or 0)
            except ValueError:
                raise ValueError(f"{p['nombre']}: todos los valores deben ser números enteros.")
            if llegada < 0 or rafaga < 1:
                raise ValueError(f"{p['nombre']}: la llegada debe ser ≥ 0 y la ráfaga ≥ 1.")
            datos.append({**p, "llegada": llegada, "rafaga": rafaga, "prioridad": prioridad})
        return datos

    # ===================== 1. BARRIDO DE QUANTUM =====================
    @rx.event
    def ejecutar_sweep(self):
        try:
            datos = self._leer_procesos_analisis()
        except ValueError as e:
            self.error_analisis = str(e)
            return
        self.error_analisis = ""

        max_rafaga = max(p["rafaga"] for p in datos)
        resultados = []
        mejor_q = 1
        mejor_espera = float("inf")

        for q in range(1, max_rafaga + 1):
            gantt = algoritmos.round_robin(datos, q)
            _, espera, _ = algoritmos.calcular_tiempos(datos, gantt)
            resultados.append({
                "quantum": str(q),
                "espera": f"{espera:.2f}",
                "espera_num": str(round(espera, 4)),
            })
            if espera < mejor_espera:
                mejor_espera = espera
                mejor_q = q

        self.quantum_sweep_data = resultados
        self.quantum_optimo = str(mejor_q)
        self.quantum_optimo_espera = f"{mejor_espera:.2f}"
        self.sweep_ejecutado = True
        self.gantt_sweep_visible = False

    @rx.event
    def seleccionar_quantum(self, quantum_str: str):
        """Genera el Gantt estático para un quantum seleccionado."""
        try:
            datos = self._leer_procesos_analisis()
        except ValueError:
            return
        q = int(quantum_str)
        self.quantum_seleccionado = quantum_str

        bloques = algoritmos.round_robin(datos, q)
        colores = {p["nombre"]: p["color"] for p in datos}
        total = bloques[-1]["fin"] if bloques else 1

        nombres_procesos = [p["nombre"] for p in datos]
        proc_rows = [{"nombre": p["nombre"], "color": p["color"]} for p in datos]
        self.gantt_sweep_procesos = proc_rows

        filas_dict = {nombre: {"segmentos": []} for nombre in nombres_procesos}

        marcas = [{"tiempo": "0", "left_pct": "0%"}]
        tiempos_vistos = {"0"}

        for b in bloques:
            nombre = b["nombre"]
            inicio = b["inicio"]
            fin = b["fin"]
            duracion = fin - inicio

            t_str = str(fin)
            if t_str not in tiempos_vistos:
                marcas.append({"tiempo": t_str, "left_pct": f"{(fin / total) * 100:.2f}%"})
                tiempos_vistos.add(t_str)

            if nombre == "Ocioso":
                continue

            color = colores.get(nombre, "#52525b")
            filas_dict[nombre]["segmentos"].append({
                "color": color,
                "ancho_pct": f"{(duracion / total) * 100:.2f}%",
                "left_pct": f"{(inicio / total) * 100:.2f}%",
            })

        all_segs = []
        for proc_idx, nombre in enumerate(nombres_procesos):
            top_px = f"{proc_idx * 44}px"
            for seg in filas_dict[nombre]["segmentos"]:
                all_segs.append({
                    "nombre": nombre,
                    "color": seg["color"],
                    "left_pct": seg["left_pct"],
                    "ancho_pct": seg["ancho_pct"],
                    "fila_top": top_px,
                })
        self.gantt_sweep_segmentos = all_segs
        self.gantt_sweep_marcas = marcas
        self.gantt_sweep_visible = True



    # ===================== 3. MONTE CARLO =====================
    @rx.event
    def set_mc_campo(self, campo: str, valor: str):
        setattr(self, campo, valor)

    @rx.event(background=True)
    async def ejecutar_monte_carlo(self):
        async with self:
            if self.mc_ejecutando:
                return
            self.mc_ejecutando = True
            self.mc_ejecutado = False
            self.error_analisis = ""

            try:
                num_escenarios = int(self.mc_num_escenarios)
                min_llegada = int(self.mc_min_llegada)
                max_llegada = int(self.mc_max_llegada)
                min_rafaga = int(self.mc_min_rafaga)
                max_rafaga = int(self.mc_max_rafaga)
                min_prioridad = int(self.mc_min_prioridad)
                max_prioridad = int(self.mc_max_prioridad)
                min_procs = int(self.mc_min_procesos)
                max_procs = int(self.mc_max_procesos)
            except ValueError:
                self.error_analisis = "Todos los parámetros deben ser números enteros."
                self.mc_ejecutando = False
                return

            if num_escenarios < 1 or num_escenarios > 5000:
                self.error_analisis = "El número de escenarios debe estar entre 1 y 5000."
                self.mc_ejecutando = False
                return
            if min_rafaga < 1:
                self.error_analisis = "La ráfaga mínima debe ser ≥ 1."
                self.mc_ejecutando = False
                return
            if min_procs < 2:
                self.error_analisis = "Debe haber al menos 2 procesos."
                self.mc_ejecutando = False
                return

            self.mc_total = num_escenarios
            self.mc_progreso = 0

        algoritmo_nombres = ["FIFO", "SJF", "Prioridad", "Round Robin"]
        victorias = {a: 0 for a in algoritmo_nombres}
        todas_esperas = {a: [] for a in algoritmo_nombres}
        quantum_default = 2

        # Para la gráfica de evolución acumulada
        historial_victorias = []  # snapshots periódicos
        snapshot_interval = max(1, num_escenarios // 50)  # ~50 puntos en la gráfica

        # Procesar en lotes para actualizar progreso
        batch_size = max(1, num_escenarios // 20)

        for i in range(num_escenarios):
            # Generar conjunto aleatorio
            n_procs = random.randint(min_procs, max_procs)
            procs = []
            for j in range(1, n_procs + 1):
                procs.append({
                    "nombre": f"P{j}",
                    "llegada": random.randint(min_llegada, max_llegada),
                    "rafaga": random.randint(min_rafaga, max_rafaga),
                    "prioridad": random.randint(min_prioridad, max_prioridad),
                    "color": COLORES[(j - 1) % len(COLORES)],
                })

            # Ejecutar los 4 algoritmos
            esperas = {}
            for nombre in algoritmo_nombres:
                gantt = algoritmos.ejecutar(nombre, procs, quantum_default)
                _, espera, _ = algoritmos.calcular_tiempos(procs, gantt)
                esperas[nombre] = espera
                todas_esperas[nombre].append(espera)

            # Encontrar ganador
            min_espera = min(esperas.values())
            ganadores = [a for a, e in esperas.items() if abs(e - min_espera) < 0.001]
            for g in ganadores:
                victorias[g] += 1

            # Snapshot para la gráfica de evolución
            if (i + 1) % snapshot_interval == 0 or i == num_escenarios - 1:
                historial_victorias.append({
                    "escenario": i + 1,
                    "FIFO": victorias["FIFO"],
                    "SJF": victorias["SJF"],
                    "Prioridad": victorias["Prioridad"],
                    "RoundRobin": victorias["Round Robin"],
                })

            # Actualizar progreso periódicamente
            if (i + 1) % batch_size == 0 or i == num_escenarios - 1:
                async with self:
                    self.mc_progreso = i + 1

        # Calcular estadísticas
        colores_algo = {
            "FIFO": "#3b82f6",
            "SJF": "#10b981",
            "Prioridad": "#f59e0b",
            "Round Robin": "#8b5cf6",
        }

        total_victorias = sum(victorias.values()) or 1
        max_victorias = max(victorias.values()) or 1

        mc_victorias = []
        for nombre in algoritmo_nombres:
            mc_victorias.append({
                "algoritmo": nombre,
                "victorias": str(victorias[nombre]),
                "porcentaje": f"{victorias[nombre] / total_victorias * 100:.1f}%",
                "ancho": f"{victorias[nombre] / max_victorias * 100:.1f}%",
                "color": colores_algo[nombre],
            })

        mc_estadisticas = []
        for nombre in algoritmo_nombres:
            esperas = todas_esperas[nombre]
            media = sum(esperas) / len(esperas)
            varianza = sum((e - media) ** 2 for e in esperas) / len(esperas)
            desv = math.sqrt(varianza)
            mc_estadisticas.append({
                "algoritmo": nombre,
                "promedio": f"{media:.2f}",
                "desv": f"{desv:.2f}",
                "minimo": f"{min(esperas):.2f}",
                "maximo": f"{max(esperas):.2f}",
                "color": colores_algo[nombre],
            })

        # Distribución: barras agrupadas usando el promedio como referencia
        max_promedio = max(float(e["promedio"]) for e in mc_estadisticas) or 1
        mc_distribucion = []
        for e in mc_estadisticas:
            mc_distribucion.append({
                "algoritmo": e["algoritmo"],
                "promedio": e["promedio"],
                "ancho_promedio": f"{float(e['promedio']) / max_promedio * 100:.1f}%",
                "desv": e["desv"],
                "color": e["color"],
            })

        # Datos para recharts
        chart_victorias = []
        for nombre in algoritmo_nombres:
            chart_victorias.append({
                "name": nombre,
                "victorias": victorias[nombre],
                "fill": colores_algo[nombre],
            })

        chart_promedios = []
        for nombre in algoritmo_nombres:
            esperas_algo = todas_esperas[nombre]
            media = sum(esperas_algo) / len(esperas_algo)
            chart_promedios.append({
                "name": nombre,
                "promedio": round(media, 2),
                "minimo": round(min(esperas_algo), 2),
                "maximo": round(max(esperas_algo), 2),
                "fill": colores_algo[nombre],
            })

        async with self:
            self.mc_victorias = mc_victorias
            self.mc_estadisticas = mc_estadisticas
            self.mc_distribucion = mc_distribucion
            self.mc_chart_victorias = chart_victorias
            self.mc_chart_promedios = chart_promedios
            self.mc_chart_evolucion = historial_victorias
            self.mc_ejecutado = True
            self.mc_ejecutando = False


# =====================================================================
#  COMPONENTES
# =====================================================================
def encabezado_analisis():
    return rx.vstack(
        rx.hstack(
            rx.link(
                rx.button(
                    rx.icon("arrow-left", size=18),
                    "Volver al simulador",
                    variant="soft",
                    color_scheme="gray",
                    size="3",
                ),
                href="/",
                underline="none",
            ),
            rx.spacer(),
            rx.badge(rx.icon("brain", size=14), "Análisis Avanzado", variant="soft",
                     radius="full", size="2", color_scheme="amber"),
            width="100%",
            align="center",
        ),
        rx.heading("Análisis Avanzado de Algoritmos", size="9", weight="bold",
                   class_name="titulo-gradiente-analisis", text_align="center"),
        rx.text("Barrido de quantum y simulación Monte Carlo.",
                color_scheme="gray", size="4", text_align="center", max_width="640px"),
        align="center",
        spacing="3",
        class_name="aparecer",
    )


def titulo_seccion_analisis(icono, texto, numero):
    return rx.hstack(
        rx.center(rx.text(numero, weight="bold", size="2"), width="28px", height="28px",
                  border_radius="full", background="rgba(245,158,11,0.25)", color="#fbbf24"),
        rx.icon(icono, size=20, color="#f59e0b"),
        rx.heading(texto, size="5"),
        align="center",
        spacing="2",
    )


def punto_color_analisis(color):
    return rx.box(width="12px", height="12px", border_radius="50%", background=color,
                  flex_shrink="0")


def campo_numero_analisis(valor, al_cambiar):
    return rx.input(value=valor, on_change=al_cambiar, type="number", min=0,
                    variant="soft", width="90px", size="2")


def fila_proceso_analisis(p, i):
    return rx.table.row(
        rx.table.cell(rx.hstack(punto_color_analisis(p["color"]), rx.text(p["nombre"], weight="bold"), align="center")),
        rx.table.cell(campo_numero_analisis(p["llegada"], lambda v: AnalisisState.editar_analisis(i, "llegada", v))),
        rx.table.cell(campo_numero_analisis(p["rafaga"], lambda v: AnalisisState.editar_analisis(i, "rafaga", v))),
        rx.table.cell(campo_numero_analisis(p["prioridad"], lambda v: AnalisisState.editar_analisis(i, "prioridad", v))),
        rx.table.cell(
            rx.icon_button(rx.icon("trash-2", size=16), on_click=AnalisisState.eliminar_analisis(i),
                           variant="ghost", color_scheme="red"),
        ),
        align="center",
        class_name="aparecer",
    )


def seccion_procesos_analisis():
    return rx.box(
        rx.vstack(
            rx.hstack(
                titulo_seccion_analisis("table", "Tabla de procesos", "⚙"),
                rx.spacer(),
                rx.button(rx.icon("shuffle", size=16), "Aleatorio", on_click=AnalisisState.aleatorio_analisis,
                          variant="soft", color_scheme="gray"),
                rx.button(rx.icon("plus", size=16), "Agregar", on_click=AnalisisState.agregar_analisis,
                          variant="soft"),
                width="100%",
                align="center",
                wrap="wrap",
            ),
            rx.callout(
                "Esta tabla es compartida por las tres herramientas de análisis. "
                "Configura tus procesos aquí y luego usa las pestañas de abajo.",
                icon="info",
                color_scheme="amber",
                variant="surface",
                width="100%",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Proceso"),
                        rx.table.column_header_cell("Llegada"),
                        rx.table.column_header_cell("Ráfaga CPU"),
                        rx.table.column_header_cell("Prioridad"),
                        rx.table.column_header_cell(""),
                    )
                ),
                rx.table.body(rx.foreach(AnalisisState.procesos_analisis, fila_proceso_analisis)),
                variant="ghost",
                width="100%",
            ),
            rx.cond(
                AnalisisState.error_analisis != "",
                rx.callout(AnalisisState.error_analisis, icon="triangle-alert", color_scheme="red", width="100%"),
            ),
            spacing="4",
        ),
        class_name="vidrio aparecer",
    )


# =====================================================================
#  1. BARRIDO DE QUANTUM
# =====================================================================
def segmento_gantt_sweep(seg):
    return rx.box(
        rx.center(
            rx.text(seg["nombre"], weight="bold", size="1", color="white"),
            height="100%",
        ),
        position="absolute",
        left=seg["left_pct"],
        width=seg["ancho_pct"],
        top=seg["fila_top"],
        height="36px",
        background=seg["color"],
        class_name="gantt-segmento",
        overflow="hidden",
    )


def fila_proceso_gantt_sweep(proc):
    return rx.hstack(
        rx.box(width="10px", height="10px", border_radius="50%",
               background=proc["color"], flex_shrink="0"),
        rx.text(proc["nombre"], weight="bold", size="2", white_space="nowrap"),
        align="center",
        spacing="2",
        height="36px",
    )


def punto_quantum(d):
    """Un punto clickeable en la gráfica de barrido de quantum."""
    es_optimo = d["quantum"] == AnalisisState.quantum_optimo
    es_seleccionado = d["quantum"] == AnalisisState.quantum_seleccionado
    return rx.tooltip(
        rx.box(
            width=rx.cond(es_optimo, "14px", rx.cond(es_seleccionado, "12px", "10px")),
            height=rx.cond(es_optimo, "14px", rx.cond(es_seleccionado, "12px", "10px")),
            border_radius="50%",
            background=rx.cond(
                es_optimo,
                "#facc15",
                rx.cond(es_seleccionado, "#22d3ee", "#8b5cf6")
            ),
            box_shadow=rx.cond(
                es_optimo,
                "0 0 12px #facc15, 0 0 24px rgba(250,204,21,0.3)",
                rx.cond(es_seleccionado, "0 0 8px #22d3ee", "0 0 4px rgba(139,92,246,0.5)")
            ),
            cursor="pointer",
            transition="all 0.2s ease",
            _hover={"transform": "scale(1.4)"},
            on_click=AnalisisState.seleccionar_quantum(d["quantum"]),
            position="relative",
            z_index="2",
        ),
        content="Q=" + d["quantum"] + " → Espera: " + d["espera"],
    )


def seccion_quantum_sweep():
    return rx.vstack(
        rx.hstack(
            titulo_seccion_analisis("search", "Barrido de Quantum Óptimo", "1"),
            rx.spacer(),
            rx.button(
                rx.icon("play", size=16), "Ejecutar Barrido",
                on_click=AnalisisState.ejecutar_sweep,
                class_name="boton-analisis",
                size="3",
            ),
            width="100%",
            align="center",
            wrap="wrap",
        ),
        rx.text(
            "Ejecuta Round Robin con todos los quantums posibles (1 hasta la ráfaga más grande) "
            "y encuentra cuál produce el menor tiempo de espera promedio.",
            size="2", color_scheme="gray",
        ),
        rx.cond(
            AnalisisState.sweep_ejecutado,
            rx.vstack(
                # Tarjeta del resultado óptimo
                rx.hstack(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("trophy", size=24, color="#facc15"),
                            rx.text("Quantum óptimo", weight="medium", size="3"),
                            align="center",
                        ),
                        rx.hstack(
                            rx.text(AnalisisState.quantum_optimo, class_name="numero-grande", color="#facc15"),
                            rx.vstack(
                                rx.text("Tiempo de espera promedio:", size="2", color_scheme="gray"),
                                rx.text(AnalisisState.quantum_optimo_espera, " u.t.", weight="bold",
                                        size="3", color="#22d3ee"),
                                spacing="0",
                            ),
                            align="end",
                            spacing="4",
                        ),
                        spacing="2",
                        class_name="stat stat-espera",
                        flex="1",
                    ),
                    width="100%",
                ),
                # Gráfica de puntos
                rx.box(
                    rx.vstack(
                        rx.text("Quantum vs Tiempo de espera promedio", weight="bold",
                                size="3", color_scheme="gray"),
                        rx.text("Haz clic en un punto para ver su diagrama de Gantt",
                                size="1", color_scheme="gray"),
                        spacing="1",
                    ),
                    rx.box(
                        # Eje Y label
                        rx.text("Espera", size="1", color_scheme="gray",
                                position="absolute", left="-6px", top="50%",
                                transform="rotate(-90deg) translateX(-50%)",
                                transform_origin="left center"),
                        # Puntos
                        rx.hstack(
                            rx.foreach(AnalisisState.quantum_sweep_data, punto_quantum),
                            spacing="3",
                            align="center",
                            justify="center",
                            padding="20px 30px",
                            flex_wrap="wrap",
                        ),
                        # Eje X label
                        rx.text("Quantum", size="1", color_scheme="gray",
                                text_align="center", width="100%"),
                        position="relative",
                        border="1px solid rgba(255,255,255,0.06)",
                        border_radius="16px",
                        background="rgba(255,255,255,0.02)",
                        padding="16px",
                        margin_top="8px",
                    ),
                    width="100%",
                ),
                # Tabla de resultados
                rx.box(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Quantum"),
                                rx.table.column_header_cell("Espera Promedio"),
                                rx.table.column_header_cell(""),
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                AnalisisState.quantum_sweep_data,
                                lambda d: rx.table.row(
                                    rx.table.cell(
                                        rx.hstack(
                                            rx.text(d["quantum"], weight="bold"),
                                            rx.cond(
                                                d["quantum"] == AnalisisState.quantum_optimo,
                                                rx.badge("Óptimo", color_scheme="yellow", radius="full", size="1"),
                                            ),
                                            align="center",
                                            spacing="2",
                                        )
                                    ),
                                    rx.table.cell(rx.text(d["espera"], font_family="JetBrains Mono")),
                                    rx.table.cell(
                                        rx.icon_button(
                                            rx.icon("eye", size=14),
                                            on_click=AnalisisState.seleccionar_quantum(d["quantum"]),
                                            variant="ghost",
                                            size="1",
                                        )
                                    ),
                                    align="center",
                                    background=rx.cond(
                                        d["quantum"] == AnalisisState.quantum_optimo,
                                        "rgba(250,204,21,0.08)",
                                        "transparent",
                                    ),
                                ),
                            ),
                        ),
                        variant="ghost",
                        width="100%",
                    ),
                    max_height="300px",
                    overflow_y="auto",
                    border="1px solid rgba(255,255,255,0.06)",
                    border_radius="12px",
                ),
                # Gantt del quantum seleccionado
                rx.cond(
                    AnalisisState.gantt_sweep_visible,
                    rx.vstack(
                        rx.hstack(
                            rx.icon("chart-no-axes-gantt", size=18, color="#f59e0b"),
                            rx.text("Gantt para Quantum = ", rx.text.strong(AnalisisState.quantum_seleccionado),
                                    weight="medium", size="3"),
                            align="center",
                        ),
                        rx.hstack(
                            rx.vstack(
                                rx.foreach(AnalisisState.gantt_sweep_procesos, fila_proceso_gantt_sweep),
                                spacing="2",
                                min_width="70px",
                            ),
                            rx.box(
                                rx.foreach(AnalisisState.gantt_sweep_marcas, lambda m: rx.box(
                                    position="absolute",
                                    top="0", bottom="0", left=m["left_pct"],
                                    border_left="1px dashed rgba(255,255,255,0.15)",
                                    z_index="0",
                                )),
                                rx.box(
                                    rx.foreach(AnalisisState.gantt_sweep_segmentos, segmento_gantt_sweep),
                                    position="absolute",
                                    inset="0",
                                    z_index="1",
                                ),
                                position="relative",
                                width="100%",
                                height=AnalisisState.gantt_sweep_altura,
                                background="rgba(255,255,255,0.02)",
                                border_radius="12px",
                                border="1px solid rgba(255,255,255,0.06)",
                                overflow="hidden",
                                padding="4px 0",
                            ),
                            width="100%",
                            align="start",
                            spacing="3",
                        ),
                        # Eje temporal
                        rx.hstack(
                            rx.box(min_width="70px"),
                            rx.box(
                                rx.foreach(AnalisisState.gantt_sweep_marcas, lambda m: rx.box(
                                    rx.text(m["tiempo"], size="1", color="#a1a1aa",
                                            font_family="JetBrains Mono"),
                                    position="absolute",
                                    top="2px", left=m["left_pct"],
                                    transform="translateX(-50%)",
                                )),
                                position="relative",
                                height="24px",
                                width="100%",
                                background="rgba(255,255,255,0.02)",
                                border_radius="4px",
                                border="1px solid rgba(255,255,255,0.04)",
                            ),
                            width="100%",
                            spacing="3",
                        ),
                        spacing="3",
                        width="100%",
                        padding="12px",
                        border="1px solid rgba(245,158,11,0.2)",
                        border_radius="16px",
                        background="rgba(245,158,11,0.04)",
                        class_name="aparecer",
                    ),
                ),
                spacing="4",
                width="100%",
                class_name="aparecer",
            ),
        ),
        spacing="4",
        width="100%",
    )


# =====================================================================
#  3. MONTE CARLO
# =====================================================================
def campo_mc(label, campo, valor):
    return rx.vstack(
        rx.text(label, size="2", weight="medium"),
        rx.input(
            value=valor,
            on_change=lambda v: AnalisisState.set_mc_campo(campo, v),
            type="number", min=0, variant="soft", width="100%", size="2",
        ),
        spacing="1",
        width="100%",
    )


def barra_victoria(v):
    return rx.vstack(
        rx.hstack(
            rx.box(width="12px", height="12px", border_radius="50%",
                   background=v["color"], flex_shrink="0"),
            rx.text(v["algoritmo"], weight="bold", size="2"),
            rx.spacer(),
            rx.text(v["victorias"], " victorias", weight="bold", size="2",
                    font_family="JetBrains Mono"),
            rx.badge(v["porcentaje"], color_scheme="amber", size="1"),
            width="100%",
            align="center",
        ),
        rx.box(
            rx.box(
                class_name="barra-comp",
                width=v["ancho"],
                height="100%",
                background=v["color"],
            ),
            width="100%",
            height="14px",
            border_radius="999px",
            background="rgba(255,255,255,0.06)",
            overflow="hidden",
        ),
        spacing="1",
        width="100%",
    )


def fila_estadistica(e):
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.box(width="10px", height="10px", border_radius="50%",
                       background=e["color"], flex_shrink="0"),
                rx.text(e["algoritmo"], weight="bold"),
                align="center",
            )
        ),
        rx.table.cell(rx.text(e["promedio"], font_family="JetBrains Mono")),
        rx.table.cell(rx.text(e["desv"], font_family="JetBrains Mono")),
        rx.table.cell(rx.text(e["minimo"], font_family="JetBrains Mono")),
        rx.table.cell(rx.text(e["maximo"], font_family="JetBrains Mono")),
        align="center",
    )


def barra_distribucion(d):
    return rx.vstack(
        rx.hstack(
            rx.box(width="10px", height="10px", border_radius="50%",
                   background=d["color"], flex_shrink="0"),
            rx.text(d["algoritmo"], weight="bold", size="2"),
            rx.spacer(),
            rx.text("μ = ", d["promedio"], " ± ", d["desv"],
                    size="2", font_family="JetBrains Mono", color_scheme="gray"),
            width="100%",
            align="center",
        ),
        rx.box(
            rx.box(
                class_name="barra-comp",
                width=d["ancho_promedio"],
                height="100%",
                background=rx.cond(True, d["color"], d["color"]),
                opacity="0.8",
            ),
            width="100%",
            height="18px",
            border_radius="999px",
            background="rgba(255,255,255,0.06)",
            overflow="hidden",
        ),
        spacing="1",
        width="100%",
    )


def seccion_monte_carlo():
    return rx.vstack(
        rx.hstack(
            titulo_seccion_analisis("dice-5", "Simulación Monte Carlo", "3"),
            rx.spacer(),
            rx.button(
                rx.icon("play", size=16),
                rx.cond(AnalisisState.mc_ejecutando, "Simulando...", "Ejecutar Monte Carlo"),
                on_click=AnalisisState.ejecutar_monte_carlo,
                loading=AnalisisState.mc_ejecutando,
                class_name="boton-analisis",
                size="3",
            ),
            width="100%",
            align="center",
            wrap="wrap",
        ),
        rx.text(
            "Genera miles de conjuntos de procesos aleatorios, ejecuta los 4 algoritmos en cada uno "
            "y compara estadísticamente cuál gana más veces.",
            size="2", color_scheme="gray",
        ),
        # Configuración
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("settings", size=18, color="#f59e0b"),
                    rx.text("Parámetros de la simulación", weight="bold", size="3"),
                    align="center",
                ),
                rx.grid(
                    campo_mc("Escenarios", "mc_num_escenarios", AnalisisState.mc_num_escenarios),
                    campo_mc("Mín. procesos", "mc_min_procesos", AnalisisState.mc_min_procesos),
                    campo_mc("Máx. procesos", "mc_max_procesos", AnalisisState.mc_max_procesos),
                    campo_mc("Mín. llegada", "mc_min_llegada", AnalisisState.mc_min_llegada),
                    campo_mc("Máx. llegada", "mc_max_llegada", AnalisisState.mc_max_llegada),
                    campo_mc("Mín. ráfaga", "mc_min_rafaga", AnalisisState.mc_min_rafaga),
                    campo_mc("Máx. ráfaga", "mc_max_rafaga", AnalisisState.mc_max_rafaga),
                    campo_mc("Mín. prioridad", "mc_min_prioridad", AnalisisState.mc_min_prioridad),
                    campo_mc("Máx. prioridad", "mc_max_prioridad", AnalisisState.mc_max_prioridad),
                    columns=rx.breakpoints(initial="2", sm="3", md="5"),
                    spacing="3",
                    width="100%",
                ),
                spacing="3",
            ),
            padding="16px",
            border="1px solid rgba(255,255,255,0.06)",
            border_radius="16px",
            background="rgba(255,255,255,0.02)",
            width="100%",
        ),
        # Progreso
        rx.cond(
            AnalisisState.mc_ejecutando,
            rx.vstack(
                rx.hstack(
                    rx.box(class_name="punto-vivo"),
                    rx.text("Simulando escenarios: ",
                            rx.text.strong(AnalisisState.mc_progreso),
                            " / ",
                            rx.text.strong(AnalisisState.mc_total),
                            size="2"),
                    align="center",
                ),
                rx.box(
                    rx.box(
                        height="100%",
                        background="linear-gradient(90deg, #f59e0b, #f43f5e)",
                        border_radius="999px",
                        transition="width 0.3s ease",
                        width=rx.cond(
                            AnalisisState.mc_total > 0,
                            f"{AnalisisState.mc_progreso}",
                            "0%",
                        ),
                    ),
                    width="100%",
                    height="8px",
                    border_radius="999px",
                    background="rgba(255,255,255,0.06)",
                    overflow="hidden",
                ),
                spacing="2",
                width="100%",
                class_name="aparecer",
            ),
        ),
        # Resultados
        rx.cond(
            AnalisisState.mc_ejecutado,
            rx.vstack(
                # ========== GRÁFICA 1: Victorias (Bar Chart) ==========
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("trophy", size=20, color="#facc15"),
                            rx.text("Conteo de Victorias", weight="bold", size="4"),
                            rx.badge(AnalisisState.mc_total.to(str), " escenarios",
                                     color_scheme="amber", size="1"),
                            align="center",
                            spacing="2",
                        ),
                        rx.text("Veces que cada algoritmo produjo el menor tiempo de espera promedio.",
                                size="2", color_scheme="gray"),
                        # Recharts bar chart de victorias
                        rx.recharts.bar_chart(
                            rx.recharts.bar(
                                data_key="victorias",
                                radius=[8, 8, 0, 0],
                            ),
                            rx.recharts.x_axis(
                                data_key="name",
                                tick={"fill": "#a1a1aa", "fontSize": 12},
                                axis_line=False,
                                tick_line=False,
                            ),
                            rx.recharts.y_axis(
                                tick={"fill": "#a1a1aa", "fontSize": 11},
                                axis_line=False,
                                tick_line=False,
                            ),
                            rx.recharts.cartesian_grid(
                                stroke_dasharray="3 6",
                                stroke="rgba(255,255,255,0.06)",
                                vertical=False,
                            ),
                            rx.recharts.graphing_tooltip(
                                content_style={
                                    "backgroundColor": "rgba(15,15,25,0.95)",
                                    "border": "1px solid rgba(255,255,255,0.1)",
                                    "borderRadius": "12px",
                                    "color": "#e4e4e7",
                                    "fontSize": "13px",
                                },
                            ),
                            data=AnalisisState.mc_chart_victorias,
                            width="100%",
                            height=300,
                        ),
                        # Barras resumidas debajo
                        rx.vstack(
                            rx.foreach(AnalisisState.mc_victorias, barra_victoria),
                            spacing="3",
                            width="100%",
                        ),
                        spacing="4",
                    ),
                    padding="20px",
                    border="1px solid rgba(250,204,21,0.2)",
                    border_radius="16px",
                    background="rgba(250,204,21,0.04)",
                    width="100%",
                ),
                # ========== GRÁFICA 2: Evolución acumulada (Line Chart) ==========
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("trending-up", size=20, color="#22d3ee"),
                            rx.text("Evolución de Victorias Acumuladas", weight="bold", size="4"),
                            align="center",
                        ),
                        rx.text(
                            "Muestra cómo se acumulan las victorias de cada algoritmo conforme avanzan los escenarios.",
                            size="2", color_scheme="gray",
                        ),
                        rx.recharts.line_chart(
                            rx.recharts.line(
                                data_key="FIFO",
                                stroke="#3b82f6",
                                stroke_width=2,
                                dot=False,
                                name="FIFO",
                            ),
                            rx.recharts.line(
                                data_key="SJF",
                                stroke="#10b981",
                                stroke_width=2,
                                dot=False,
                                name="SJF",
                            ),
                            rx.recharts.line(
                                data_key="Prioridad",
                                stroke="#f59e0b",
                                stroke_width=2,
                                dot=False,
                                name="Prioridad",
                            ),
                            rx.recharts.line(
                                data_key="RoundRobin",
                                stroke="#8b5cf6",
                                stroke_width=2,
                                dot=False,
                                name="Round Robin",
                            ),
                            rx.recharts.x_axis(
                                data_key="escenario",
                                tick={"fill": "#a1a1aa", "fontSize": 11},
                                axis_line=False,
                                tick_line=False,
                            ),
                            rx.recharts.y_axis(
                                tick={"fill": "#a1a1aa", "fontSize": 11},
                                axis_line=False,
                                tick_line=False,
                            ),
                            rx.recharts.cartesian_grid(
                                stroke_dasharray="3 6",
                                stroke="rgba(255,255,255,0.06)",
                            ),
                            rx.recharts.legend(
                                icon_type="circle",
                                wrapper_style={"fontSize": "12px", "color": "#a1a1aa"},
                            ),
                            rx.recharts.graphing_tooltip(
                                content_style={
                                    "backgroundColor": "rgba(15,15,25,0.95)",
                                    "border": "1px solid rgba(255,255,255,0.1)",
                                    "borderRadius": "12px",
                                    "color": "#e4e4e7",
                                    "fontSize": "13px",
                                },
                            ),
                            data=AnalisisState.mc_chart_evolucion,
                            width="100%",
                            height=320,
                        ),
                        spacing="4",
                    ),
                    padding="20px",
                    border="1px solid rgba(34,211,238,0.15)",
                    border_radius="16px",
                    background="rgba(34,211,238,0.03)",
                    width="100%",
                ),
                # ========== GRÁFICA 3: Promedios comparativos (Bar Chart) ==========
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("bar-chart-3", size=20, color="#8b5cf6"),
                            rx.text("Tiempo de Espera Promedio por Algoritmo", weight="bold", size="4"),
                            align="center",
                        ),
                        rx.text("Promedio del tiempo de espera a lo largo de todos los escenarios simulados.",
                                size="2", color_scheme="gray"),
                        rx.recharts.bar_chart(
                            rx.recharts.bar(
                                data_key="promedio",
                                radius=[8, 8, 0, 0],
                                name="Promedio",
                            ),
                            rx.recharts.x_axis(
                                data_key="name",
                                tick={"fill": "#a1a1aa", "fontSize": 12},
                                axis_line=False,
                                tick_line=False,
                            ),
                            rx.recharts.y_axis(
                                tick={"fill": "#a1a1aa", "fontSize": 11},
                                axis_line=False,
                                tick_line=False,
                            ),
                            rx.recharts.cartesian_grid(
                                stroke_dasharray="3 6",
                                stroke="rgba(255,255,255,0.06)",
                                vertical=False,
                            ),
                            rx.recharts.graphing_tooltip(
                                content_style={
                                    "backgroundColor": "rgba(15,15,25,0.95)",
                                    "border": "1px solid rgba(255,255,255,0.1)",
                                    "borderRadius": "12px",
                                    "color": "#e4e4e7",
                                    "fontSize": "13px",
                                },
                            ),
                            data=AnalisisState.mc_chart_promedios,
                            width="100%",
                            height=300,
                        ),
                        spacing="4",
                    ),
                    padding="20px",
                    border="1px solid rgba(139,92,246,0.15)",
                    border_radius="16px",
                    background="rgba(139,92,246,0.03)",
                    width="100%",
                ),
                # ========== Estadísticas detalladas (tabla) ==========
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("table", size=20, color="#22d3ee"),
                            rx.text("Estadísticas Detalladas", weight="bold", size="4"),
                            align="center",
                        ),
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Algoritmo"),
                                    rx.table.column_header_cell("Promedio"),
                                    rx.table.column_header_cell("Desv. Estándar"),
                                    rx.table.column_header_cell("Mínimo"),
                                    rx.table.column_header_cell("Máximo"),
                                )
                            ),
                            rx.table.body(
                                rx.foreach(AnalisisState.mc_estadisticas, fila_estadistica),
                            ),
                            variant="ghost",
                            width="100%",
                        ),
                        spacing="3",
                    ),
                    padding="20px",
                    border="1px solid rgba(255,255,255,0.06)",
                    border_radius="16px",
                    background="rgba(255,255,255,0.02)",
                    width="100%",
                ),
                spacing="4",
                width="100%",
                class_name="aparecer",
            ),
        ),
        spacing="4",
        width="100%",
    )


# =====================================================================
#  TABS Y PÁGINA
# =====================================================================
def seccion_tabs():
    return rx.box(
        rx.vstack(
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger(
                        rx.hstack(rx.icon("search", size=16), rx.text("Barrido de Quantum"), align="center", spacing="2"),
                        value="quantum",
                    ),

                    rx.tabs.trigger(
                        rx.hstack(rx.icon("dice-5", size=16), rx.text("Monte Carlo"), align="center", spacing="2"),
                        value="montecarlo",
                    ),
                ),
                rx.tabs.content(seccion_quantum_sweep(), value="quantum", padding_top="20px"),

                rx.tabs.content(seccion_monte_carlo(), value="montecarlo", padding_top="20px"),
                default_value="quantum",
                width="100%",
            ),
            spacing="4",
        ),
        class_name="vidrio aparecer",
    )


# =====================================================================
#  PARTÍCULAS DE FONDO
# =====================================================================
def particulas_fondo_analisis():
    return rx.script("""
    (function() {
        if (document.getElementById('bg-particles-canvas-analisis')) return;
        const canvas = document.createElement('canvas');
        canvas.id = 'bg-particles-canvas-analisis';
        canvas.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:1;pointer-events:none;opacity:0.6;';
        document.body.appendChild(canvas);
        const ctx = canvas.getContext('2d');
        const COLORS = ['#f59e0b','#facc15','#f43f5e','#8b5cf6','#22d3ee','#10b981'];
        const NUM = 60;
        const CONNECT_DIST = 140;
        let particles = [];
        
        function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
        resize();
        window.addEventListener('resize', resize);
        
        class Particle {
            constructor(init) {
                this.x = Math.random() * canvas.width;
                this.y = init ? Math.random() * canvas.height : (Math.random() < 0.5 ? -5 : canvas.height + 5);
                this.r = Math.random() * 2 + 1;
                this.color = COLORS[Math.floor(Math.random() * COLORS.length)];
                const a = Math.random() * Math.PI * 2;
                const speed = Math.random() * 0.5 + 0.2;
                this.vx = Math.cos(a) * speed;
                this.vy = Math.sin(a) * speed;
                this.alpha = Math.random() * 0.5 + 0.2;
            }
            update() {
                this.x += this.vx; this.y += this.vy;
                if (this.x < -10) this.x = canvas.width + 10;
                if (this.x > canvas.width + 10) this.x = -10;
                if (this.y < -10) this.y = canvas.height + 10;
                if (this.y > canvas.height + 10) this.y = -10;
            }
            draw() {
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
                ctx.fillStyle = this.color;
                ctx.globalAlpha = this.alpha;
                ctx.fill();
                ctx.globalAlpha = 1;
            }
        }
        for (let i = 0; i < NUM; i++) particles.push(new Particle(true));
        
        function loop() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(p => p.update());
            
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const dist = Math.sqrt(dx*dx + dy*dy);
                    if (dist < CONNECT_DIST) {
                        const alpha = (1 - dist/CONNECT_DIST) * 0.18;
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.strokeStyle = '#f59e0b';
                        ctx.globalAlpha = alpha;
                        ctx.lineWidth = 1;
                        ctx.stroke();
                        ctx.globalAlpha = 1;
                    }
                }
            }
            particles.forEach(p => p.draw());
            requestAnimationFrame(loop);
        }
        requestAnimationFrame(loop);
    })();
    """)


def analisis_page():
    return rx.box(
        particulas_fondo_analisis(),
        rx.container(
            rx.vstack(
                encabezado_analisis(),
                seccion_procesos_analisis(),
                seccion_tabs(),
                rx.text("Desarrollado por: ", size="1", color_scheme="gray",
                        align_self="center"),
                rx.text("Kevin Esteban Sánchez Torres ", size="1", color_scheme="gray",
                                        align_self="center"),
                rx.text("Yeison Orozco Vasco ", size="1", color_scheme="gray",
                                        align_self="center"),
                spacing="6",
                padding_y="48px",
            ),
            size="4",
            position="relative",
            z_index="1",
        ),
        class_name="fondo-analisis",
    )
