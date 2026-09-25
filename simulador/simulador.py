"""Simulador de algoritmos de planificación de CPU hecho con Reflex."""

import asyncio
import random

import reflex as rx

from . import algoritmos

COLORES = [
    "#8b5cf6", "#06b6d4", "#f43f5e", "#f59e0b", "#10b981",
    "#3b82f6", "#ec4899", "#84cc16", "#f97316", "#14b8a6",
]
COLOR_OCIOSO = "repeating-linear-gradient(45deg, #2a2a3a 0 6px, #1c1c28 6px 12px)"
MAX_PROCESOS = 10

ALGORITMOS = [
    {"nombre": "FIFO", "icono": "list-ordered", "desc": "El primero en llegar es el primero en ser atendido"},
    {"nombre": "SJF", "icono": "zap", "desc": "Se atiende primero la ráfaga más corta"},
    {"nombre": "Prioridad", "icono": "crown", "desc": "Menor número = mayor prioridad"},
    {"nombre": "Round Robin", "icono": "refresh-cw", "desc": "Turnos rotativos con un quantum fijo"},
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
#  ESTADO
# =====================================================================
class State(rx.State):
    algoritmo: str = "FIFO"
    quantum: str = "2"
    velocidad: str = "Normal"
    procesos: list[dict[str, str]] = [
        crear_proceso(1, 0, 5, 3),
        crear_proceso(2, 1, 3, 1),
        crear_proceso(3, 2, 8, 4),
        crear_proceso(4, 3, 6, 2),
        crear_proceso(5, 4, 2, 5),
    ]

    # Gantt multi-fila: flat list of segments, each with process info
    # Each segment: {nombre, color, left_pct, ancho_pct}
    gantt_segmentos: list[dict[str, str]] = []
    # Process row info: {nombre, color}
    gantt_procesos: list[dict[str, str]] = []
    # Progreso actual de la animación
    gantt_progreso: float = 0.0
    # Porcentaje de progreso precalculado como string CSS
    gantt_progreso_pct: str = "0%"
    # Marcas de tiempo (líneas verticales)
    gantt_marcas: list[dict[str, str]] = []
    # Máscara clip-path para revelar fluidamente
    gantt_clip_path: str = "inset(0 100% 0 0)"
    # Transición CSS dinámica para el progreso
    gantt_progreso_transition: str = "none"

    @rx.var
    def gantt_altura(self) -> str:
        """Altura dinámica del contenedor de Gantt calculada en base a los procesos."""
        if not self.procesos:
            return "100px"
        return f"{len(self.procesos) * 44 + 8}px"

    resultados: list[dict[str, str]] = []
    prom_espera: str = ""
    prom_sistema: str = ""
    ejecutando: str = ""
    tiempo_actual: str = "0"
    animando: bool = False
    terminado: bool = False
    error: str = ""

    # ---------- Edición de la tabla ----------
    @rx.event
    def elegir_algoritmo(self, nombre: str):
        if not self.animando:
            self.algoritmo = nombre
            self._limpiar()

    @rx.event
    def set_quantum(self, valor: str):
        self.quantum = valor

    @rx.event
    def set_velocidad(self, valor: str | list[str]):
        self.velocidad = str(valor)

    @rx.event
    def editar(self, i: int, campo: str, valor: str):
        procesos = [dict(p) for p in self.procesos]
        procesos[i][campo] = valor
        self.procesos = procesos

    @rx.event
    def agregar(self):
        if len(self.procesos) < MAX_PROCESOS:
            n = len(self.procesos) + 1
            self.procesos = self.procesos + [crear_proceso(n, n - 1, 3, n)]

    @rx.event
    def eliminar(self, i: int):
        if len(self.procesos) > 1:
            restantes = [p for j, p in enumerate(self.procesos) if j != i]
            self.procesos = [
                crear_proceso(n, p["llegada"], p["rafaga"], p["prioridad"])
                for n, p in enumerate(restantes, start=1)
            ]

    @rx.event
    def aleatorio(self):
        cantidad = random.randint(4, 6)
        self.procesos = [
            crear_proceso(n, random.randint(0, 8), random.randint(1, 8), random.randint(1, 5))
            for n in range(1, cantidad + 1)
        ]
        self._limpiar()

    def _limpiar(self):
        self.gantt_segmentos = []
        self.gantt_procesos = []
        self.gantt_progreso = 0.0
        self.gantt_progreso_pct = "0%"
        self.gantt_marcas = []
        self.gantt_clip_path = "inset(0 100% 0 0)"
        self.gantt_progreso_transition = "none"
        self.resultados = []
        self.ejecutando = ""
        self.tiempo_actual = "0"
        self.terminado = False
        self.error = ""

    def _leer_procesos(self):
        """Convierte la tabla (texto) a números y valida."""
        datos = []
        for p in self.procesos:
            try:
                llegada, rafaga = int(p["llegada"]), int(p["rafaga"])
                prioridad = int(p["prioridad"] or 0)
            except ValueError:
                raise ValueError(f"{p['nombre']}: todos los valores deben ser números enteros.")
            if llegada < 0 or rafaga < 1:
                raise ValueError(f"{p['nombre']}: la llegada debe ser ≥ 0 y la ráfaga ≥ 1.")
            datos.append({**p, "llegada": llegada, "rafaga": rafaga, "prioridad": prioridad})

        try:
            quantum = int(self.quantum)
        except ValueError:
            quantum = 0
        if quantum < 1:
            raise ValueError("El quantum debe ser un número entero ≥ 1.")
        return datos, quantum

    def _reconstruir_segmentos(self, filas_dict, nombres_procesos, total):
        """Reconstruct flat segment list from filas_dict for the UI."""
        all_segs = []
        for proc_idx, nombre in enumerate(nombres_procesos):
            # Each row is 36px height + 8px gap = 44px stride
            top_px = f"{proc_idx * 44}px"
            for seg in filas_dict[nombre]["segmentos"]:
                all_segs.append({
                    "nombre": nombre,
                    "color": seg["color"],
                    "left_pct": seg["left_pct"],
                    "ancho_pct": seg["ancho_pct"],
                    "fila_top": top_px,
                })
        self.gantt_segmentos = all_segs

    # ---------- Simulación animada multi-fila ----------
    @rx.event(background=True)
    async def simular(self):
        async with self:
            if self.animando:
                return
            self._limpiar()
            try:
                datos, quantum = self._leer_procesos()
            except ValueError as e:
                self.error = str(e)
                return
            self.animando = True
            algoritmo_nombre = self.algoritmo
            velocidad_factor = VELOCIDADES[self.velocidad]

        bloques = algoritmos.ejecutar(algoritmo_nombre, datos, quantum)
        colores = {p["nombre"]: p["color"] for p in datos}
        total = bloques[-1]["fin"] if bloques else 1

        # Build process rows
        nombres_procesos = [p["nombre"] for p in datos]
        proc_rows = [{"nombre": p["nombre"], "color": p["color"]} for p in datos]

        async with self:
            self.gantt_procesos = proc_rows

        # Track segments per process
        filas_dict = {}
        for nombre in nombres_procesos:
            filas_dict[nombre] = {"segmentos": []}

        # Prepare result data
        filas_resultado, prom_espera, prom_sistema = algoritmos.calcular_tiempos(datos, bloques)

        # 1. Pre-calculate all segments and marks
        marcas = [{"tiempo": "0", "left_pct": "0%"}]
        tiempos_vistos = {"0"}
        
        for b in bloques:
            nombre = b["nombre"]
            inicio = b["inicio"]
            fin = b["fin"]
            duracion = fin - inicio
            
            # Add time mark if not present
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
            
        # Reconstruct exactly once and yield to render the fully constructed (but clipped) DOM
        async with self:
            self._reconstruir_segmentos(filas_dict, nombres_procesos, total)
            self.gantt_marcas = marcas
            self.gantt_clip_path = "inset(0 100% 0 0)"
            self.gantt_progreso_pct = "0%"
            self.gantt_progreso_transition = "none"
            self.tiempo_actual = "0"
            
        # Pequeña pausa para que Reflex renderice el DOM inicial antes de empezar las transiciones CSS
        await asyncio.sleep(0.1)

        # 2. Disparar la animación visual en un solo movimiento fluido de CSS
        tiempo_total_real = total * velocidad_factor
        async with self:
            if total > 0:
                self.gantt_progreso_pct = "100%"
                self.gantt_clip_path = "inset(0 0% 0 0)"
                self.gantt_progreso_transition = f"clip-path {tiempo_total_real}s linear, left {tiempo_total_real}s linear, width {tiempo_total_real}s linear"

        # 3. Bucle ligero solo para actualizar los textos ("Ejecutando Px" y tiempo) en sincronía
        for b in bloques:
            nombre = b["nombre"]
            inicio = b["inicio"]
            fin = b["fin"]
            duracion = fin - inicio
            duracion_real = duracion * velocidad_factor

            async with self:
                self.ejecutando = nombre
                self.tiempo_actual = str(inicio)

            # Wait exactly the real duration of this block
            await asyncio.sleep(duracion_real)
            
            async with self:
                self.tiempo_actual = str(fin)

        async with self:
            self.resultados = [
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
            self.prom_espera = f"{prom_espera:.2f}"
            self.prom_sistema = f"{prom_sistema:.2f}"
            self.animando = False
            self.terminado = True


# =====================================================================
#  COMPONENTES
# =====================================================================
def encabezado():
    return rx.vstack(
        rx.badge(rx.icon("cpu", size=14), "Sistemas Operativos", variant="soft", radius="full", size="2"),
        rx.heading("Simulador de Planificación de CPU", size="9", weight="bold",
                   class_name="titulo-gradiente", text_align="center"),
        rx.text("Configura tus procesos, elige un algoritmo y mira cómo se arma el diagrama de Gantt paso a paso.",
                color_scheme="gray", size="4", text_align="center", max_width="640px"),
        align="center",
        spacing="3",
        class_name="aparecer",
    )


def titulo_seccion(icono, texto, numero):
    return rx.hstack(
        rx.center(rx.text(numero, weight="bold", size="2"), width="28px", height="28px",
                  border_radius="full", background="rgba(139,92,246,0.25)", color="#c4b5fd"),
        rx.icon(icono, size=20, color="#a78bfa"),
        rx.heading(texto, size="5"),
        align="center",
        spacing="2",
    )


def tarjeta_algoritmo(a):
    return rx.box(
        rx.vstack(
            rx.center(rx.icon(a["icono"], size=22), class_name="icono-algo"),
            rx.text(a["nombre"], weight="bold", size="4"),
            rx.text(a["desc"], size="2", color_scheme="gray"),
            spacing="2",
        ),
        on_click=State.elegir_algoritmo(a["nombre"]),
        class_name=rx.cond(State.algoritmo == a["nombre"], "tarjeta-algo activa", "tarjeta-algo"),
    )


def seccion_algoritmo():
    return rx.box(
        rx.vstack(
            titulo_seccion("layers", "Elige el algoritmo", "1"),
            rx.grid(
                *[tarjeta_algoritmo(a) for a in ALGORITMOS],
                columns=rx.breakpoints(initial="2", md="4"),
                spacing="3",
                width="100%",
            ),
            spacing="4",
        ),
        class_name="vidrio aparecer",
    )


def punto_color(color):
    return rx.box(width="12px", height="12px", border_radius="50%", background=color,
                  flex_shrink="0")


def campo_numero(valor, al_cambiar):
    return rx.input(value=valor, on_change=al_cambiar, type="number", min=0,
                    variant="soft", width="90px", size="2")


def fila_proceso(p, i):
    return rx.table.row(
        rx.table.cell(rx.hstack(punto_color(p["color"]), rx.text(p["nombre"], weight="bold"), align="center")),
        rx.table.cell(campo_numero(p["llegada"], lambda v: State.editar(i, "llegada", v))),
        rx.table.cell(campo_numero(p["rafaga"], lambda v: State.editar(i, "rafaga", v))),
        rx.cond(
            State.algoritmo == "Prioridad",
            rx.table.cell(campo_numero(p["prioridad"], lambda v: State.editar(i, "prioridad", v))),
        ),
        rx.table.cell(
            rx.icon_button(rx.icon("trash-2", size=16), on_click=State.eliminar(i),
                           variant="ghost", color_scheme="red", disabled=State.animando),
        ),
        align="center",
        class_name="aparecer",
    )


def seccion_procesos():
    return rx.box(
        rx.vstack(
            rx.hstack(
                titulo_seccion("table", "Tabla de procesos", "2"),
                rx.spacer(),
                rx.button(rx.icon("shuffle", size=16), "Aleatorio", on_click=State.aleatorio,
                          variant="soft", color_scheme="gray", disabled=State.animando),
                rx.button(rx.icon("plus", size=16), "Agregar", on_click=State.agregar,
                          variant="soft", disabled=State.animando),
                width="100%",
                align="center",
                wrap="wrap",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Proceso"),
                        rx.table.column_header_cell("Llegada"),
                        rx.table.column_header_cell("Ráfaga CPU"),
                        rx.cond(State.algoritmo == "Prioridad", rx.table.column_header_cell("Prioridad")),
                        rx.table.column_header_cell(""),
                    )
                ),
                rx.table.body(rx.foreach(State.procesos, fila_proceso)),
                variant="ghost",
                width="100%",
            ),
            # Controles de la simulación
            rx.hstack(
                rx.cond(
                    State.algoritmo == "Round Robin",
                    rx.hstack(
                        rx.icon("timer", size=18, color="#22d3ee"),
                        rx.text("Quantum", weight="medium"),
                        rx.input(value=State.quantum, on_change=State.set_quantum, type="number",
                                 min=1, width="80px", variant="soft"),
                        align="center",
                        class_name="aparecer",
                    ),
                ),
                rx.hstack(
                    rx.icon("gauge", size=18, color="#a78bfa"),
                    rx.text("Velocidad", weight="medium"),
                    rx.segmented_control.root(
                        *[rx.segmented_control.item(v, value=v) for v in VELOCIDADES],
                        value=State.velocidad,
                        on_change=State.set_velocidad,
                    ),
                    align="center",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("play", size=18),
                    rx.cond(State.animando, "Simulando...", "Simular"),
                    on_click=State.simular,
                    loading=State.animando,
                    size="3",
                    class_name="boton-simular",
                ),
                width="100%",
                align="center",
                spacing="5",
                wrap="wrap",
            ),
            rx.cond(
                State.error != "",
                rx.callout(State.error, icon="triangle-alert", color_scheme="red", width="100%"),
            ),
            spacing="4",
        ),
        class_name="vidrio aparecer",
    )


# =====================================================================
#  DIAGRAMA DE GANTT MULTI-FILA
# =====================================================================

def segmento_gantt(seg):
    """A single segment positioned absolutely within its row."""
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


def fila_proceso_gantt(proc):
    """Label for a process row in the Gantt chart."""
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


def estado_gantt():
    return rx.cond(
        State.animando,
        rx.hstack(
            rx.box(class_name="punto-vivo"),
            rx.text("Ejecutando ", rx.text.strong(State.ejecutando), size="2"),
            rx.badge("t = ", State.tiempo_actual, variant="surface", size="2"),
            align="center",
        ),
        rx.cond(
            State.terminado,
            rx.badge(rx.icon("circle-check", size=14), "Completado en t = ", State.tiempo_actual,
                     color_scheme="green", size="2", radius="full"),
        ),
    )


def leyenda_velocidad():
    """Muestra la escala de tiempo real."""
    return rx.cond(
        State.animando,
        rx.hstack(
            rx.icon("clock", size=14, color="#a78bfa"),
            rx.text(
                "1 u.t. = ",
                rx.cond(State.velocidad == "Lenta", "1.0s",
                        rx.cond(State.velocidad == "Normal", "0.5s", "0.2s")),
                " real",
                size="1", color_scheme="gray",
            ),
            align="center",
            spacing="1",
        ),
    )


def seccion_gantt():
    return rx.box(
        rx.vstack(
            rx.hstack(
                titulo_seccion("chart-no-axes-gantt", "Diagrama de Gantt", "3"),
                rx.spacer(),
                leyenda_velocidad(),
                estado_gantt(),
                width="100%",
                align="center",
                wrap="wrap",
                gap="3",
            ),
            rx.cond(
                State.gantt_procesos.length() > 0,
                rx.vstack(
                    rx.hstack(
                        # Left column: process labels
                        rx.vstack(
                            rx.foreach(State.gantt_procesos, fila_proceso_gantt),
                            spacing="2",
                            min_width="70px",
                        ),
                        # Right column: Gantt bars area
                        rx.box(
                            # Marcas de tiempo (Líneas divisorias verticales)
                            rx.foreach(State.gantt_marcas, lambda m: rx.box(
                                position="absolute",
                                top="0", bottom="0", left=m["left_pct"],
                                border_left="1px dashed rgba(255,255,255,0.15)",
                                z_index="0",
                            )),
                            # Container con clip-path mask para revelar los segmentos
                            rx.box(
                                rx.foreach(State.gantt_segmentos, segmento_gantt),
                                position="absolute",
                                inset="0",
                                clip_path=State.gantt_clip_path,
                                transition=State.gantt_progreso_transition,
                                z_index="1",
                            ),
                            # Progress line
                            rx.box(
                                position="absolute",
                                left=State.gantt_progreso_pct,
                                top="0",
                                bottom="0",
                                width="2px",
                                background="#22d3ee",
                                box_shadow="0 0 8px #22d3ee",
                                transition=State.gantt_progreso_transition,
                                z_index="10",
                            ),
                            position="relative",
                            width="100%",
                            height=State.gantt_altura,
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
                    # Time axis
                    rx.hstack(
                        rx.box(min_width="70px"),
                        rx.box(
                            # Contenedor relativo para el eje de tiempo
                            rx.box(
                                position="absolute",
                                left="0", top="0", bottom="0",
                                width=State.gantt_progreso_pct,
                                background="linear-gradient(90deg, rgba(139,92,246,0.12), rgba(34,211,238,0.08))",
                                transition=State.gantt_progreso_transition,
                            ),
                            # Números de las marcas
                            rx.foreach(State.gantt_marcas, lambda m: rx.box(
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
    )


def tarjeta_promedio(titulo, valor, icono, clase, formula):
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


def celda_calculo(resultado, operacion):
    return rx.table.cell(
        rx.hstack(
            rx.text(operacion, size="1", color_scheme="gray", font_family="JetBrains Mono"),
            rx.text(resultado, weight="bold", size="3"),
            align="center",
            spacing="2",
        )
    )


def fila_resultado(r):
    return rx.table.row(
        rx.table.cell(rx.hstack(punto_color(r["color"]), rx.text(r["nombre"], weight="bold"), align="center")),
        rx.table.cell(r["llegada"]),
        rx.table.cell(r["rafaga"]),
        rx.table.cell(r["fin"]),
        celda_calculo(r["sistema"], r["fin"] + " − " + r["llegada"] + " ="),
        celda_calculo(r["espera"], r["sistema"] + " − " + r["rafaga"] + " ="),
        align="center",
        class_name="aparecer",
        style={"animation_delay": r["retraso"]},
    )


def seccion_resultados():
    return rx.cond(
        State.terminado,
        rx.box(
            rx.vstack(
                titulo_seccion("chart-column", "Resultados", "4"),
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
                        rx.foreach(State.resultados, fila_resultado),
                        rx.table.row(
                            rx.table.cell(rx.text("Promedio", weight="bold")),
                            rx.table.cell(""), rx.table.cell(""), rx.table.cell(""),
                            rx.table.cell(rx.text(State.prom_sistema, weight="bold", color="#22d3ee")),
                            rx.table.cell(rx.text(State.prom_espera, weight="bold", color="#f59e0b")),
                            background="rgba(255,255,255,0.04)",
                        ),
                    ),
                    variant="ghost",
                    width="100%",
                ),
                rx.grid(
                    tarjeta_promedio("Tiempo de espera promedio", State.prom_espera, "hourglass",
                                     "stat-espera", "Espera = T. Sistema − Ráfaga"),
                    tarjeta_promedio("Tiempo de sistema promedio", State.prom_sistema, "clock",
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
#  PARTÍCULAS DE FONDO (vía rx.script)
# =====================================================================
def particulas_fondo():
    return rx.script("""
    (function() {
        if (document.getElementById('bg-particles-canvas')) return;
        const canvas = document.createElement('canvas');
        canvas.id = 'bg-particles-canvas';
        // z-index: 1 and appendChild ensures it renders over the background gradient but behind the UI cards
        canvas.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:1;pointer-events:none;opacity:0.6;';
        document.body.appendChild(canvas);
        const ctx = canvas.getContext('2d');
        const COLORS = ['#8b5cf6','#06b6d4','#f43f5e','#22d3ee','#c4b5fd','#10b981'];
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
                        ctx.strokeStyle = '#8b5cf6';
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


def index():
    return rx.box(
        particulas_fondo(),
        rx.container(
            rx.vstack(
                encabezado(),
                seccion_algoritmo(),
                seccion_procesos(),
                seccion_gantt(),
                seccion_resultados(),
                rx.text("Hecho con Python + Reflex", size="1", color_scheme="gray",
                        align_self="center"),
                spacing="6",
                padding_y="48px",
            ),
            size="4",
            position="relative",
            z_index="1",
        ),
        class_name="fondo",
    )


app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;700;800&family=JetBrains+Mono&display=swap",
        "/styles.css",
    ],
)
app.add_page(index, title="Simulador de Planificación de CPU")
