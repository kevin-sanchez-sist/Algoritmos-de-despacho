"""Página de Algoritmos Extras: SRTF y MLQ."""

import asyncio
import random

import reflex as rx

from . import algoritmos

COLORES = [
    "#8b5cf6", "#06b6d4", "#f43f5e", "#f59e0b", "#10b981",
    "#3b82f6", "#ec4899", "#84cc16", "#f97316", "#14b8a6",
]
MAX_PROCESOS = 10

ALGORITMOS_EXTRAS = [
    {"nombre": "SRTF", "icono": "zap-off", "desc": "Expropiativo: ejecuta siempre el proceso con menor tiempo restante"},
    {"nombre": "MLQ", "icono": "layers-3", "desc": "Colas multinivel: 3 colas con diferente prioridad y política"},
]

# Factor de velocidad: cuántos segundos dura 1 unidad de tiempo
VELOCIDADES = {"Lenta": 1.0, "Normal": 0.5, "Rápida": 0.2}


def crear_proceso(n, llegada, rafaga, prioridad):
    return {
        "nombre": f"P{n}",
        "llegada": str(llegada),
        "rafaga": str(rafaga),
        "prioridad": str(prioridad),
        "color": COLORES[(n - 1) % len(COLORES)],
    }


# =====================================================================
#  ESTADO PARA EXTRAS
# =====================================================================
class ExtrasState(rx.State):
    algoritmo_extra: str = "SRTF"
    quantum_extra: str = "2"
    velocidad_extra: str = "Normal"
    procesos_extra: list[dict[str, str]] = [
        crear_proceso(1, 0, 5, 1),
        crear_proceso(2, 1, 3, 3),
        crear_proceso(3, 2, 8, 5),
        crear_proceso(4, 3, 6, 2),
        crear_proceso(5, 4, 2, 4),
    ]

    # Gantt multi-fila
    gantt_segmentos_extra: list[dict[str, str]] = []
    gantt_procesos_extra: list[dict[str, str]] = []
    gantt_progreso_extra: float = 0.0
    gantt_progreso_pct_extra: str = "0%"
    gantt_marcas_extra: list[dict[str, str]] = []
    gantt_clip_path_extra: str = "inset(0 100% 0 0)"
    gantt_progreso_transition_extra: str = "none"

    @rx.var
    def gantt_altura_extra(self) -> str:
        if not self.procesos_extra:
            return "100px"
        return f"{len(self.procesos_extra) * 44 + 8}px"

    resultados_extra: list[dict[str, str]] = []
    prom_espera_extra: str = ""
    prom_sistema_extra: str = ""
    ejecutando_extra: str = ""
    tiempo_actual_extra: str = "0"
    animando_extra: bool = False
    terminado_extra: bool = False
    error_extra: str = ""

    # Comparación de los 2 algoritmos extras
    comparacion_extra: list[dict[str, str]] = []
    mejor_espera_extra: str = ""
    mejor_espera_valor_extra: str = ""
    mejor_sistema_extra: str = ""
    mejor_sistema_valor_extra: str = ""

    # ---------- Edición de la tabla ----------
    @rx.event
    def elegir_algoritmo_extra(self, nombre: str):
        if not self.animando_extra:
            self.algoritmo_extra = nombre
            self._limpiar_extra()

    @rx.event
    def set_quantum_extra(self, valor: str):
        self.quantum_extra = valor
        self.comparacion_extra = []

    @rx.event
    def set_velocidad_extra(self, valor: str | list[str]):
        self.velocidad_extra = str(valor)

    @rx.event
    def editar_extra(self, i: int, campo: str, valor: str):
        procesos = [dict(p) for p in self.procesos_extra]
        procesos[i][campo] = valor
        self.procesos_extra = procesos
        self.comparacion_extra = []

    @rx.event
    def agregar_extra(self):
        if len(self.procesos_extra) < MAX_PROCESOS:
            n = len(self.procesos_extra) + 1
            self.procesos_extra = self.procesos_extra + [crear_proceso(n, n - 1, 3, n)]
            self.comparacion_extra = []

    @rx.event
    def eliminar_extra(self, i: int):
        if len(self.procesos_extra) > 1:
            restantes = [p for j, p in enumerate(self.procesos_extra) if j != i]
            self.procesos_extra = [
                crear_proceso(n, p["llegada"], p["rafaga"], p["prioridad"])
                for n, p in enumerate(restantes, start=1)
            ]
            self.comparacion_extra = []

    @rx.event
    def aleatorio_extra(self):
        cantidad = random.randint(4, 6)
        self.procesos_extra = [
            crear_proceso(n, random.randint(0, 8), random.randint(1, 8), random.randint(1, 5))
            for n in range(1, cantidad + 1)
        ]
        self._limpiar_extra()
        self.comparacion_extra = []

    def _limpiar_extra(self):
        self.gantt_segmentos_extra = []
        self.gantt_procesos_extra = []
        self.gantt_progreso_extra = 0.0
        self.gantt_progreso_pct_extra = "0%"
        self.gantt_marcas_extra = []
        self.gantt_clip_path_extra = "inset(0 100% 0 0)"
        self.gantt_progreso_transition_extra = "none"
        self.resultados_extra = []
        self.ejecutando_extra = ""
        self.tiempo_actual_extra = "0"
        self.terminado_extra = False
        self.error_extra = ""

    def _leer_procesos_extra(self):
        datos = []
        for p in self.procesos_extra:
            try:
                llegada, rafaga = int(p["llegada"]), int(p["rafaga"])
                prioridad = int(p["prioridad"] or 0)
            except ValueError:
                raise ValueError(f"{p['nombre']}: todos los valores deben ser números enteros.")
            if llegada < 0 or rafaga < 1:
                raise ValueError(f"{p['nombre']}: la llegada debe ser ≥ 0 y la ráfaga ≥ 1.")
            datos.append({**p, "llegada": llegada, "rafaga": rafaga, "prioridad": prioridad})

        try:
            quantum = int(self.quantum_extra)
        except ValueError:
            quantum = 0
        if quantum < 1:
            raise ValueError("El quantum debe ser un número entero ≥ 1.")
        return datos, quantum

    @rx.event
    def comparar_extras(self):
        if self.animando_extra:
            return
        try:
            datos, quantum = self._leer_procesos_extra()
        except ValueError as e:
            self.error_extra = str(e)
            return
        self.error_extra = ""

        resultados = algoritmos.comparar_extras(datos, quantum)
        mejores_espera = algoritmos.mejores(resultados, "espera")
        mejores_sistema = algoritmos.mejores(resultados, "sistema")
        max_espera = max(r["espera"] for r in resultados) or 1
        max_sistema = max(r["sistema"] for r in resultados) or 1

        self.comparacion_extra = [
            {
                "algoritmo": r["algoritmo"],
                "espera": f"{r['espera']:.2f}",
                "sistema": f"{r['sistema']:.2f}",
                "ancho_espera": f"{r['espera'] / max_espera * 100:.1f}%",
                "ancho_sistema": f"{r['sistema'] / max_sistema * 100:.1f}%",
                "gana_espera": "si" if r["algoritmo"] in mejores_espera else "",
                "gana_sistema": "si" if r["algoritmo"] in mejores_sistema else "",
                "retraso": f"{i * 0.12}s",
            }
            for i, r in enumerate(resultados)
        ]
        self.mejor_espera_extra = " y ".join(mejores_espera)
        self.mejor_sistema_extra = " y ".join(mejores_sistema)
        self.mejor_espera_valor_extra = f"{min(r['espera'] for r in resultados):.2f}"
        self.mejor_sistema_valor_extra = f"{min(r['sistema'] for r in resultados):.2f}"
        return rx.scroll_to("comparacion-extra")

    def _reconstruir_segmentos_extra(self, filas_dict, nombres_procesos, total):
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
        self.gantt_segmentos_extra = all_segs

    # ---------- Simulación animada ----------
    @rx.event(background=True)
    async def simular_extra(self):
        async with self:
            if self.animando_extra:
                return
            self._limpiar_extra()
            try:
                datos, quantum = self._leer_procesos_extra()
            except ValueError as e:
                self.error_extra = str(e)
                return
            self.animando_extra = True
            algoritmo_nombre = self.algoritmo_extra
            velocidad_factor = VELOCIDADES[self.velocidad_extra]

        bloques = algoritmos.ejecutar(algoritmo_nombre, datos, quantum)
        colores = {p["nombre"]: p["color"] for p in datos}
        total = bloques[-1]["fin"] if bloques else 1

        nombres_procesos = [p["nombre"] for p in datos]
        proc_rows = [{"nombre": p["nombre"], "color": p["color"]} for p in datos]

        async with self:
            self.gantt_procesos_extra = proc_rows

        filas_dict = {}
        for nombre in nombres_procesos:
            filas_dict[nombre] = {"segmentos": []}

        filas_resultado, prom_espera, prom_sistema = algoritmos.calcular_tiempos(datos, bloques)

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
                "inicio": str(inicio),
                "color": color,
                "ancho_pct": f"{(duracion / total) * 100:.2f}%",
                "left_pct": f"{(inicio / total) * 100:.2f}%",
            })

        async with self:
            self._reconstruir_segmentos_extra(filas_dict, nombres_procesos, total)
            self.gantt_marcas_extra = marcas
            self.gantt_clip_path_extra = "inset(0 100% 0 0)"
            self.gantt_progreso_pct_extra = "0%"
            self.gantt_progreso_transition_extra = "none"
            self.tiempo_actual_extra = "0"

        await asyncio.sleep(0.1)

        tiempo_total_real = total * velocidad_factor
        async with self:
            if total > 0:
                self.gantt_progreso_pct_extra = "100%"
                self.gantt_clip_path_extra = "inset(0 0% 0 0)"
                self.gantt_progreso_transition_extra = f"clip-path {tiempo_total_real}s linear, left {tiempo_total_real}s linear, width {tiempo_total_real}s linear"

        for b in bloques:
            nombre = b["nombre"]
            inicio = b["inicio"]
            fin = b["fin"]
            duracion = fin - inicio
            duracion_real = duracion * velocidad_factor

            async with self:
                self.ejecutando_extra = nombre
                self.tiempo_actual_extra = str(inicio)

            await asyncio.sleep(duracion_real)

            async with self:
                self.tiempo_actual_extra = str(fin)

        async with self:
            self.resultados_extra = [
                {
                    "nombre": f["nombre"],
                    "color": f["color"],
                    "llegada": str(f["llegada"]),
                    "rafaga": str(f["rafaga"]),
                    "fin": str(f["fin"]),
                    "sistema": str(f["sistema"]),
                    "espera": str(f["espera"]),
                    "retraso": f"{i * 0.12}s",
                }
                for i, f in enumerate(filas_resultado)
            ]
            self.prom_espera_extra = f"{prom_espera:.2f}"
            self.prom_sistema_extra = f"{prom_sistema:.2f}"
            self.animando_extra = False
            self.terminado_extra = True


# =====================================================================
#  COMPONENTES
# =====================================================================
def encabezado_extras():
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
            rx.badge(rx.icon("flask-conical", size=14), "Algoritmos Extras", variant="soft",
                     radius="full", size="2", color_scheme="cyan"),
            width="100%",
            align="center",
        ),
        rx.heading("Algoritmos Avanzados de Despacho", size="9", weight="bold",
                   class_name="titulo-gradiente-extra", text_align="center"),
        rx.text("Explora SRTF y MLQ: dos algoritmos adicionales para la planificación de procesos en CPU.",
                color_scheme="gray", size="4", text_align="center", max_width="640px"),
        align="center",
        spacing="3",
        class_name="aparecer",
    )


def titulo_seccion_extra(icono, texto, numero):
    return rx.hstack(
        rx.center(rx.text(numero, weight="bold", size="2"), width="28px", height="28px",
                  border_radius="full", background="rgba(6,182,212,0.25)", color="#67e8f9"),
        rx.icon(icono, size=20, color="#22d3ee"),
        rx.heading(texto, size="5"),
        align="center",
        spacing="2",
    )


def info_algoritmo_extra():
    """Sección con la explicación de cada algoritmo extra."""
    return rx.box(
        rx.vstack(
            titulo_seccion_extra("book-open", "¿Qué son estos algoritmos?", "ℹ"),
            rx.grid(
                # SRTF Card
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.center(rx.icon("zap-off", size=22, color="white"),
                                      width="42px", height="42px", border_radius="12px",
                                      background="linear-gradient(135deg, #f59e0b, #f43f5e)"),
                            rx.vstack(
                                rx.text("SRTF", weight="bold", size="4"),
                                rx.text("Shortest Remaining Time First", size="2", color_scheme="gray"),
                                spacing="0",
                            ),
                            align="center",
                        ),
                        rx.separator(size="4"),
                        rx.text(
                            "Versión expropiativa de SJF.",
                            size="2", color_scheme="gray", margin_bottom="2",
                        ),
                        rx.text(
                            "Cada vez que un nuevo proceso llega, se compara su ráfaga con el tiempo restante del proceso en ejecución. ",
                            rx.text.strong("Si el nuevo tiene menos tiempo restante, expulsa al actual.", color_scheme="gray"),
                            size="2", color_scheme="gray", line_height="1.6",
                        ),
                        rx.hstack(
                            rx.badge("Expropiativo", color_scheme="red", radius="full"),
                            rx.badge("Óptimo en espera", color_scheme="green", radius="full"),
                            wrap="wrap",
                        ),
                        spacing="3",
                    ),
                    class_name="tarjeta-info-extra",
                ),
                # MLQ Card
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.center(rx.icon("layers-3", size=22, color="white"),
                                      width="42px", height="42px", border_radius="12px",
                                      background="linear-gradient(135deg, #06b6d4, #8b5cf6)"),
                            rx.vstack(
                                rx.text("MLQ", weight="bold", size="4"),
                                rx.text("Multilevel Queue", size="2", color_scheme="gray"),
                                spacing="0",
                            ),
                            align="center",
                        ),
                        rx.separator(size="4"),
                        rx.text(
                            "Divide los procesos en 3 colas según su prioridad:",
                            size="2", color_scheme="gray", margin_bottom="2",
                        ),
                        rx.vstack(
                            rx.text("• ", rx.text.strong("Cola 1", color_scheme="gray"), " (prioridad 1-2): Round Robin q=2.", size="2", color_scheme="gray"),
                            rx.text("• ", rx.text.strong("Cola 2", color_scheme="gray"), " (prioridad 3-4): Round Robin q=4.", size="2", color_scheme="gray"),
                            rx.text("• ", rx.text.strong("Cola 3", color_scheme="gray"), " (prioridad 5+): FCFS.", size="2", color_scheme="gray"),
                            spacing="1",
                            align_items="start",
                        ),
                        rx.text(
                            "Las colas superiores siempre tienen preferencia sobre las inferiores.",
                            size="2", color_scheme="gray", margin_top="2",
                        ),
                        rx.hstack(
                            rx.badge("Multinivel", color_scheme="violet", radius="full"),
                            rx.badge("Usa prioridad", color_scheme="cyan", radius="full"),
                            rx.badge("Expropiativo entre colas", color_scheme="orange", radius="full"),
                            wrap="wrap",
                        ),
                        spacing="3",
                    ),
                    class_name="tarjeta-info-extra",
                ),
                columns=rx.breakpoints(initial="1", md="2"),
                spacing="4",
                width="100%",
            ),
            spacing="4",
        ),
        class_name="vidrio aparecer",
    )


def tarjeta_algoritmo_extra(a):
    return rx.box(
        rx.vstack(
            rx.center(rx.icon(a["icono"], size=22), class_name="icono-algo-extra"),
            rx.text(a["nombre"], weight="bold", size="4"),
            rx.text(a["desc"], size="2", color_scheme="gray"),
            spacing="2",
        ),
        on_click=ExtrasState.elegir_algoritmo_extra(a["nombre"]),
        class_name=rx.cond(ExtrasState.algoritmo_extra == a["nombre"],
                          "tarjeta-algo-extra activa-extra", "tarjeta-algo-extra"),
    )


def seccion_algoritmo_extra():
    return rx.box(
        rx.vstack(
            titulo_seccion_extra("layers", "Elige el algoritmo", "1"),
            rx.grid(
                *[tarjeta_algoritmo_extra(a) for a in ALGORITMOS_EXTRAS],
                columns=rx.breakpoints(initial="1", md="2"),
                spacing="3",
                width="100%",
            ),
            spacing="4",
        ),
        class_name="vidrio aparecer",
    )


def punto_color_extra(color):
    return rx.box(width="12px", height="12px", border_radius="50%", background=color,
                  flex_shrink="0")


def campo_numero_extra(valor, al_cambiar):
    return rx.input(value=valor, on_change=al_cambiar, type="number", min=0,
                    variant="soft", width="90px", size="2")


def fila_proceso_extra(p, i):
    return rx.table.row(
        rx.table.cell(rx.hstack(punto_color_extra(p["color"]), rx.text(p["nombre"], weight="bold"), align="center")),
        rx.table.cell(campo_numero_extra(p["llegada"], lambda v: ExtrasState.editar_extra(i, "llegada", v))),
        rx.table.cell(campo_numero_extra(p["rafaga"], lambda v: ExtrasState.editar_extra(i, "rafaga", v))),
        rx.table.cell(campo_numero_extra(p["prioridad"], lambda v: ExtrasState.editar_extra(i, "prioridad", v))),
        rx.table.cell(
            rx.icon_button(rx.icon("trash-2", size=16), on_click=ExtrasState.eliminar_extra(i),
                           variant="ghost", color_scheme="red", disabled=ExtrasState.animando_extra),
        ),
        align="center",
        class_name="aparecer",
    )


def seccion_procesos_extra():
    return rx.box(
        rx.vstack(
            rx.hstack(
                titulo_seccion_extra("table", "Tabla de procesos", "2"),
                rx.spacer(),
                rx.button(rx.icon("shuffle", size=16), "Aleatorio", on_click=ExtrasState.aleatorio_extra,
                          variant="soft", color_scheme="gray", disabled=ExtrasState.animando_extra),
                rx.button(rx.icon("plus", size=16), "Agregar", on_click=ExtrasState.agregar_extra,
                          variant="soft", disabled=ExtrasState.animando_extra),
                width="100%",
                align="center",
                wrap="wrap",
            ),
            rx.callout(
                rx.vstack(
                    rx.text(
                        "La columna ", rx.text.strong("Prioridad"), " es obligatoria para ambos algoritmos."
                    ),
                    rx.text("• En ", rx.text.strong("SRTF"), " se usa solo como referencia."),
                    rx.text("• En ", rx.text.strong("MLQ"), " determina la cola a la que pertenece el proceso:"),
                    rx.hstack(
                        rx.badge("1-2 → Cola Alta (RR q=2)", color_scheme="violet"),
                        rx.badge("3-4 → Cola Media (RR q=4)", color_scheme="blue"),
                        rx.badge("5+ → Cola Baja (FCFS)", color_scheme="cyan"),
                        spacing="2",
                        wrap="wrap",
                        margin_top="1"
                    ),
                    spacing="1",
                    align_items="start"
                ),
                icon="info",
                color_scheme="cyan",
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
                rx.table.body(rx.foreach(ExtrasState.procesos_extra, fila_proceso_extra)),
                variant="ghost",
                width="100%",
            ),
            # Controles de simulación
            rx.hstack(
                rx.cond(
                    ExtrasState.algoritmo_extra == "MLQ",
                    rx.hstack(
                        rx.icon("timer", size=18, color="#22d3ee"),
                        rx.text("Quantum base", weight="medium"),
                        rx.input(value=ExtrasState.quantum_extra, on_change=ExtrasState.set_quantum_extra,
                                 type="number", min=1, width="80px", variant="soft"),
                        align="center",
                        class_name="aparecer",
                    ),
                ),
                rx.hstack(
                    rx.icon("gauge", size=18, color="#22d3ee"),
                    rx.text("Velocidad", weight="medium"),
                    rx.segmented_control.root(
                        *[rx.segmented_control.item(v, value=v) for v in VELOCIDADES],
                        value=ExtrasState.velocidad_extra,
                        on_change=ExtrasState.set_velocidad_extra,
                    ),
                    align="center",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("trophy", size=18),
                    "Comparar los 2",
                    on_click=ExtrasState.comparar_extras,
                    disabled=ExtrasState.animando_extra,
                    size="3",
                    variant="outline",
                ),
                rx.button(
                    rx.icon("play", size=18),
                    rx.cond(ExtrasState.animando_extra, "Simulando...", "Simular"),
                    on_click=ExtrasState.simular_extra,
                    loading=ExtrasState.animando_extra,
                    size="3",
                    class_name="boton-simular-extra",
                ),
                width="100%",
                align="center",
                spacing="5",
                wrap="wrap",
            ),
            rx.cond(
                ExtrasState.error_extra != "",
                rx.callout(ExtrasState.error_extra, icon="triangle-alert", color_scheme="red", width="100%"),
            ),
            spacing="4",
        ),
        class_name="vidrio aparecer",
    )


# =====================================================================
#  DIAGRAMA DE GANTT
# =====================================================================
def segmento_gantt_extra(seg):
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


def fila_proceso_gantt_extra(proc):
    return rx.hstack(
        rx.box(
            width="10px", height="10px", border_radius="50%",
            background=proc["color"],
            flex_shrink="0",
        ),
        rx.text(proc["nombre"], weight="bold", size="2", white_space="nowrap"),
        align="center",
        spacing="2",
        height="36px",
    )


def estado_gantt_extra():
    return rx.cond(
        ExtrasState.animando_extra,
        rx.hstack(
            rx.box(class_name="punto-vivo"),
            rx.text("Ejecutando ", rx.text.strong(ExtrasState.ejecutando_extra), size="2"),
            rx.badge("t = ", ExtrasState.tiempo_actual_extra, variant="surface", size="2"),
            align="center",
        ),
        rx.cond(
            ExtrasState.terminado_extra,
            rx.badge(rx.icon("circle-check", size=14), "Completado en t = ", ExtrasState.tiempo_actual_extra,
                     color_scheme="green", size="2", radius="full"),
        ),
    )


def leyenda_velocidad_extra():
    return rx.cond(
        ExtrasState.animando_extra,
        rx.hstack(
            rx.icon("clock", size=14, color="#22d3ee"),
            rx.text(
                "1 u.t. = ",
                rx.cond(ExtrasState.velocidad_extra == "Lenta", "1.0s",
                        rx.cond(ExtrasState.velocidad_extra == "Normal", "0.5s", "0.2s")),
                " real",
                size="1", color_scheme="gray",
            ),
            align="center",
            spacing="1",
        ),
    )


def seccion_gantt_extra():
    return rx.box(
        rx.vstack(
            rx.hstack(
                titulo_seccion_extra("chart-no-axes-gantt", "Diagrama de Gantt", "3"),
                rx.spacer(),
                leyenda_velocidad_extra(),
                estado_gantt_extra(),
                width="100%",
                align="center",
                wrap="wrap",
                gap="3",
            ),
            rx.cond(
                ExtrasState.gantt_procesos_extra.length() > 0,
                rx.vstack(
                    rx.hstack(
                        rx.vstack(
                            rx.foreach(ExtrasState.gantt_procesos_extra, fila_proceso_gantt_extra),
                            spacing="2",
                            min_width="70px",
                        ),
                        rx.box(
                            rx.foreach(ExtrasState.gantt_marcas_extra, lambda m: rx.box(
                                position="absolute",
                                top="0", bottom="0", left=m["left_pct"],
                                border_left="1px dashed rgba(255,255,255,0.15)",
                                z_index="0",
                            )),
                            rx.box(
                                rx.foreach(ExtrasState.gantt_segmentos_extra, segmento_gantt_extra),
                                position="absolute",
                                inset="0",
                                clip_path=ExtrasState.gantt_clip_path_extra,
                                transition=ExtrasState.gantt_progreso_transition_extra,
                                z_index="1",
                            ),
                            rx.box(
                                position="absolute",
                                left=ExtrasState.gantt_progreso_pct_extra,
                                top="0",
                                bottom="0",
                                width="2px",
                                background="#22d3ee",
                                box_shadow="0 0 8px #22d3ee",
                                transition=ExtrasState.gantt_progreso_transition_extra,
                                z_index="10",
                            ),
                            position="relative",
                            width="100%",
                            height=ExtrasState.gantt_altura_extra,
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
                    rx.hstack(
                        rx.box(min_width="70px"),
                        rx.box(
                            rx.box(
                                position="absolute",
                                left="0", top="0", bottom="0",
                                width=ExtrasState.gantt_progreso_pct_extra,
                                background="linear-gradient(90deg, rgba(6,182,212,0.12), rgba(139,92,246,0.08))",
                                transition=ExtrasState.gantt_progreso_transition_extra,
                            ),
                            rx.foreach(ExtrasState.gantt_marcas_extra, lambda m: rx.box(
                                rx.text(m["tiempo"], size="1", color="#a1a1aa", font_family="JetBrains Mono"),
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
                    spacing="2",
                    width="100%",
                    padding="12px 10px 0 6px",
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("chart-no-axes-gantt", size=40, color="#52525b"),
                        rx.text("Presiona ", rx.text.strong("Simular"), " para construir el diagrama",
                                color_scheme="gray"),
                        align="center",
                    ),
                    height="130px",
                    width="100%",
                    border="2px dashed rgba(255,255,255,0.08)",
                    border_radius="16px",
                ),
            ),
            spacing="4",
        ),
        class_name="vidrio aparecer",
        id="gantt-extra",
    )


# =====================================================================
#  RESULTADOS
# =====================================================================
def tarjeta_promedio_extra(titulo, valor, icono, clase, formula):
    return rx.vstack(
        rx.hstack(rx.icon(icono, size=20), rx.text(titulo, weight="medium", size="3"), align="center"),
        rx.hstack(
            rx.text(valor, class_name="numero-grande"),
            rx.text("u. de tiempo", color_scheme="gray", size="2"),
            align="end",
        ),
        rx.text(formula, size="2", color_scheme="gray"),
        spacing="3",
        class_name="stat " + clase,
    )


def celda_calculo_extra(resultado, operacion):
    return rx.table.cell(
        rx.hstack(
            rx.text(operacion, size="1", color_scheme="gray", font_family="JetBrains Mono"),
            rx.text(resultado, weight="bold", size="3"),
            align="center",
            spacing="2",
        )
    )


def fila_resultado_extra(r):
    return rx.table.row(
        rx.table.cell(rx.hstack(punto_color_extra(r["color"]), rx.text(r["nombre"], weight="bold"), align="center")),
        rx.table.cell(r["llegada"]),
        rx.table.cell(r["rafaga"]),
        rx.table.cell(r["fin"]),
        celda_calculo_extra(r["sistema"], r["fin"] + " − " + r["llegada"] + " ="),
        celda_calculo_extra(r["espera"], r["sistema"] + " − " + r["rafaga"] + " ="),
        align="center",
        class_name="aparecer",
        style={"animation_delay": r["retraso"]},
    )


def seccion_resultados_extra():
    return rx.cond(
        ExtrasState.terminado_extra,
        rx.box(
            rx.vstack(
                titulo_seccion_extra("chart-column", "Resultados", "4"),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Proceso"),
                            rx.table.column_header_cell("Llegada"),
                            rx.table.column_header_cell("Ráfaga"),
                            rx.table.column_header_cell("Finaliza"),
                            rx.table.column_header_cell("T. Sistema"),
                            rx.table.column_header_cell("T. Espera"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(ExtrasState.resultados_extra, fila_resultado_extra),
                        rx.table.row(
                            rx.table.cell(rx.text("Promedio", weight="bold")),
                            rx.table.cell(""), rx.table.cell(""), rx.table.cell(""),
                            rx.table.cell(rx.text(ExtrasState.prom_sistema_extra, weight="bold", color="#22d3ee")),
                            rx.table.cell(rx.text(ExtrasState.prom_espera_extra, weight="bold", color="#f59e0b")),
                            background="rgba(255,255,255,0.04)",
                        ),
                    ),
                    variant="ghost",
                    width="100%",
                ),
                rx.grid(
                    tarjeta_promedio_extra("Tiempo de espera promedio", ExtrasState.prom_espera_extra, "hourglass",
                                          "stat-espera", "Espera = T. Sistema − Ráfaga"),
                    tarjeta_promedio_extra("Tiempo de sistema promedio", ExtrasState.prom_sistema_extra, "clock",
                                          "stat-sistema", "Sistema = Finalización − Llegada"),
                    columns=rx.breakpoints(initial="1", sm="2"),
                    spacing="4",
                    width="100%",
                ),
                spacing="5",
            ),
            class_name="vidrio aparecer",
        ),
    )


# =====================================================================
#  COMPARACIÓN DE LOS 2 ALGORITMOS EXTRAS
# =====================================================================
def tarjeta_ganador_extra(titulo, nombre, valor, icono, clase):
    return rx.vstack(
        rx.hstack(rx.icon(icono, size=20), rx.text(titulo, weight="medium", size="3"), align="center"),
        rx.hstack(
            rx.icon("trophy", size=30, color="#facc15"),
            rx.text(nombre, class_name="numero-grande"),
            align="center",
        ),
        rx.text("Promedio: ", rx.text.strong(valor), " u. de tiempo", size="2", color_scheme="gray"),
        spacing="3",
        class_name="stat aparecer " + clase,
    )


def barra_comparacion_extra(etiqueta, valor, ancho, color, gana):
    return rx.vstack(
        rx.hstack(
            rx.text(etiqueta, size="1", color_scheme="gray"),
            rx.spacer(),
            rx.text(valor, weight="bold", size="2", font_family="JetBrains Mono",
                    color=rx.cond(gana == "si", "#facc15", "white")),
            width="100%",
        ),
        rx.box(
            rx.box(class_name="barra-comp", width=ancho, height="100%", background=color),
            width="100%",
            height="10px",
            border_radius="999px",
            background="rgba(255,255,255,0.06)",
            overflow="hidden",
        ),
        spacing="1",
        width="100%",
    )


def fila_comparacion_extra(i, a):
    c = ExtrasState.comparacion_extra[i]
    gana_alguno = (c["gana_espera"] == "si") | (c["gana_sistema"] == "si")
    return rx.grid(
        rx.hstack(
            rx.center(rx.icon(a["icono"], size=18), class_name="icono-algo-extra", width="36px", height="36px"),
            rx.vstack(
                rx.text(a["nombre"], weight="bold", size="3"),
                rx.cond(gana_alguno, rx.badge(rx.icon("trophy", size=12), "Más óptimo",
                                              color_scheme="yellow", radius="full")),
                spacing="1",
            ),
            align="center",
        ),
        barra_comparacion_extra("Tiempo de espera", c["espera"], c["ancho_espera"],
                                "linear-gradient(90deg, #f59e0b, #f43f5e)", c["gana_espera"]),
        barra_comparacion_extra("Tiempo de sistema", c["sistema"], c["ancho_sistema"],
                                "linear-gradient(90deg, #06b6d4, #8b5cf6)", c["gana_sistema"]),
        rx.button(
            rx.icon("play", size=14), "Ver Gantt",
            on_click=[ExtrasState.elegir_algoritmo_extra(a["nombre"]), ExtrasState.simular_extra, rx.scroll_to("gantt-extra")],
            variant="soft", size="2", disabled=ExtrasState.animando_extra,
        ),
        columns=rx.breakpoints(initial="1", md="170px 1fr 1fr auto"),
        spacing="5",
        align="center",
        width="100%",
        class_name=rx.cond(gana_alguno, "fila-comp ganadora aparecer", "fila-comp aparecer"),
        style={"animation_delay": c["retraso"]},
    )


def seccion_comparacion_extra():
    return rx.cond(
        ExtrasState.comparacion_extra.length() > 0,
        rx.box(
            rx.vstack(
                titulo_seccion_extra("trophy", "Comparación de algoritmos extras", "5"),
                rx.grid(
                    tarjeta_ganador_extra("Mejor en tiempo de espera", ExtrasState.mejor_espera_extra,
                                         ExtrasState.mejor_espera_valor_extra, "hourglass", "stat-espera"),
                    tarjeta_ganador_extra("Mejor en tiempo de sistema", ExtrasState.mejor_sistema_extra,
                                         ExtrasState.mejor_sistema_valor_extra, "clock", "stat-sistema"),
                    columns=rx.breakpoints(initial="1", sm="2"),
                    spacing="4",
                    width="100%",
                ),
                rx.vstack(
                    *[fila_comparacion_extra(i, a) for i, a in enumerate(ALGORITMOS_EXTRAS)],
                    spacing="3",
                    width="100%",
                ),
                rx.callout(
                    rx.vstack(
                        rx.text(rx.text.strong("SRTF"), " suele dar el menor tiempo de espera promedio al ser expropiativo."),
                        rx.text(rx.text.strong("MLQ"), " asigna los procesos a colas fijas según su prioridad:"),
                        rx.hstack(
                            rx.badge("Cola 1: Prioridad 1-2 (RR q=2)", color_scheme="violet"),
                            rx.badge("Cola 2: Prioridad 3-4 (RR q=4)", color_scheme="blue"),
                            rx.badge("Cola 3: Prioridad 5+ (FCFS)", color_scheme="cyan"),
                            wrap="wrap",
                            spacing="2",
                        ),
                        rx.text(
                            "Las colas se atienden en orden estricto de mayor a menor prioridad.",
                            size="2", color_scheme="gray",
                        ),
                        spacing="1",
                        align_items="start"
                    ),
                    icon="info",
                    color_scheme="gray",
                    variant="surface",
                    width="100%",
                ),
                spacing="5",
            ),
            class_name="vidrio aparecer",
            id="comparacion-extra",
        ),
    )


# =====================================================================
#  PARTÍCULAS DE FONDO
# =====================================================================
def particulas_fondo_extra():
    return rx.script("""
    (function() {
        if (document.getElementById('bg-particles-canvas-extra')) return;
        const canvas = document.createElement('canvas');
        canvas.id = 'bg-particles-canvas-extra';
        canvas.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:1;pointer-events:none;opacity:0.6;';
        document.body.appendChild(canvas);
        const ctx = canvas.getContext('2d');
        const COLORS = ['#06b6d4','#22d3ee','#8b5cf6','#f59e0b','#10b981','#f43f5e'];
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
                        ctx.strokeStyle = '#06b6d4';
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


# =====================================================================
#  PÁGINA
# =====================================================================
def extras_page():
    return rx.box(
        particulas_fondo_extra(),
        rx.container(
            rx.vstack(
                encabezado_extras(),
                info_algoritmo_extra(),
                seccion_algoritmo_extra(),
                seccion_procesos_extra(),
                seccion_gantt_extra(),
                seccion_resultados_extra(),
                seccion_comparacion_extra(),
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
        class_name="fondo-extra",
    )
