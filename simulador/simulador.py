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
PAUSAS = {"Lenta": 1.2, "Normal": 0.7, "Rápida": 0.3}


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

    # Resultado de la simulación
    gantt: list[dict[str, str]] = []
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
            # Se vuelven a numerar P1, P2, ... para que no queden huecos
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
        self.gantt = []
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

    # ---------- Simulación animada ----------
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
            algoritmo = self.algoritmo
            pausa = PAUSAS[self.velocidad]

        bloques = algoritmos.ejecutar(algoritmo, datos, quantum)
        colores = {p["nombre"]: p["color"] for p in datos}
        total = bloques[-1]["fin"]  # duración total, para que el Gantt ocupe el 100% del ancho

        # Se agrega un bloque al Gantt cada `pausa` segundos
        for b in bloques:
            async with self:
                self.gantt = self.gantt + [{
                    "nombre": b["nombre"],
                    "fin": str(b["fin"]),
                    "color": colores.get(b["nombre"], COLOR_OCIOSO),
                    "ancho": f"{(b['fin'] - b['inicio']) / total * 100}%",
                }]
                self.ejecutando = b["nombre"]
                self.tiempo_actual = str(b["fin"])
            await asyncio.sleep(pausa)

        filas, prom_espera, prom_sistema = algoritmos.calcular_tiempos(datos, bloques)
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
                for i, f in enumerate(filas)
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
                  box_shadow="0 0 10px " + color, flex_shrink="0")


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
                        *[rx.segmented_control.item(v, value=v) for v in PAUSAS],
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


def bloque_gantt(b, i):
    es_ocioso = b["nombre"] == "Ocioso"
    return rx.box(
        rx.center(
            rx.text(rx.cond(es_ocioso, "—", b["nombre"]), weight="bold", size="3",
                    color=rx.cond(es_ocioso, "#71717a", "white")),
            class_name="barra",
            background=b["color"],
        ),
        rx.cond(i == 0, rx.text("0", class_name="marca marca-cero")),
        rx.text(b["fin"], class_name="marca"),
        class_name=rx.cond(i == 0, "bloque primero", "bloque"),
        width=b["ancho"],
        position="relative",
        padding_bottom="26px",
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


def seccion_gantt():
    return rx.box(
        rx.vstack(
            rx.hstack(
                titulo_seccion("chart-no-axes-gantt", "Diagrama de Gantt", "3"),
                rx.spacer(),
                estado_gantt(),
                width="100%",
                align="center",
                wrap="wrap",
            ),
            rx.cond(
                State.gantt.length() > 0,
                rx.hstack(
                    rx.foreach(State.gantt, bloque_gantt),
                    spacing="0",
                    width="100%",
                    padding="8px 10px 0 6px",
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


def index():
    return rx.box(
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
