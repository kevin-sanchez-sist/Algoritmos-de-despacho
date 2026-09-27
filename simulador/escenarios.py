"""Página de Escenarios del Mundo Real: Algoritmos de despacho en la vida cotidiana."""

import asyncio
import random

import reflex as rx

from . import algoritmos

COLORES = [
    "#10b981", "#06b6d4", "#f43f5e", "#f59e0b", "#8b5cf6",
    "#3b82f6", "#ec4899", "#84cc16", "#f97316", "#14b8a6",
]
MAX_PROCESOS = 8
VELOCIDADES = {"Lenta": 1.0, "Normal": 0.5, "Rápida": 0.2}

ESCENARIOS = [
    {
        "id": "banco",
        "nombre": "Banco",
        "icono": "landmark",
        "algoritmo": "FIFO",
        "desc": "Los clientes toman turno y son atendidos por orden de llegada.",
        "clase_icono": "icono-banco",
    },
    {
        "id": "hospital",
        "nombre": "Hospital",
        "icono": "heart-pulse",
        "algoritmo": "Prioridad",
        "desc": "Los pacientes se atienden según la gravedad de su condición.",
        "clase_icono": "icono-hospital",
    },
    {
        "id": "supermercado",
        "nombre": "Supermercado",
        "icono": "shopping-cart",
        "algoritmo": "SJF",
        "desc": "La caja rápida atiende primero a quien tiene menos artículos.",
        "clase_icono": "icono-super",
    },
    {
        "id": "callcenter",
        "nombre": "Call Center",
        "icono": "phone",
        "algoritmo": "Round Robin",
        "desc": "Cada llamada recibe un tiempo fijo antes de rotar a la siguiente.",
        "clase_icono": "icono-call",
    },
]


def crear_proceso_esc(n, llegada, rafaga, prioridad):
    return {
        "nombre": f"P{n}",
        "llegada": str(llegada),
        "rafaga": str(rafaga),
        "prioridad": str(prioridad),
        "color": COLORES[(n - 1) % len(COLORES)],
    }


DATOS_DEFECTO = {
    "banco": [
        crear_proceso_esc(1, 0, 5, 0),
        crear_proceso_esc(2, 2, 3, 0),
        crear_proceso_esc(3, 4, 7, 0),
        crear_proceso_esc(4, 5, 2, 0),
        crear_proceso_esc(5, 7, 4, 0),
    ],
    "hospital": [
        crear_proceso_esc(1, 0, 8, 4),
        crear_proceso_esc(2, 1, 3, 1),
        crear_proceso_esc(3, 3, 5, 2),
        crear_proceso_esc(4, 4, 2, 5),
        crear_proceso_esc(5, 6, 4, 3),
    ],
    "supermercado": [
        crear_proceso_esc(1, 0, 8, 0),
        crear_proceso_esc(2, 1, 2, 0),
        crear_proceso_esc(3, 3, 5, 0),
        crear_proceso_esc(4, 4, 1, 0),
        crear_proceso_esc(5, 5, 3, 0),
    ],
    "callcenter": [
        crear_proceso_esc(1, 0, 6, 0),
        crear_proceso_esc(2, 1, 4, 0),
        crear_proceso_esc(3, 2, 8, 0),
        crear_proceso_esc(4, 3, 3, 0),
        crear_proceso_esc(5, 5, 5, 0),
    ],
}


# =====================================================================
#  ESTADO
# =====================================================================
class EscenariosState(rx.State):
    escenario: str = "banco"
    velocidad_esc: str = "Normal"
    quantum_esc: str = "3"

    procesos_esc: list[dict[str, str]] = [
        crear_proceso_esc(1, 0, 5, 0),
        crear_proceso_esc(2, 2, 3, 0),
        crear_proceso_esc(3, 4, 7, 0),
        crear_proceso_esc(4, 5, 2, 0),
        crear_proceso_esc(5, 7, 4, 0),
    ]

    # Gantt
    gantt_segmentos_esc: list[dict[str, str]] = []
    gantt_procesos_esc: list[dict[str, str]] = []
    gantt_progreso_pct_esc: str = "0%"
    gantt_marcas_esc: list[dict[str, str]] = []
    gantt_clip_path_esc: str = "inset(0 100% 0 0)"
    gantt_progreso_transition_esc: str = "none"

    # Resultados
    resultados_esc: list[dict[str, str]] = []
    prom_espera_esc: str = ""
    prom_sistema_esc: str = ""
    ejecutando_esc: str = ""
    tiempo_actual_esc: str = "0"
    animando_esc: bool = False
    terminado_esc: bool = False
    error_esc: str = ""

    # --- Computed vars ---
    @rx.var
    def gantt_altura_esc(self) -> str:
        if not self.procesos_esc:
            return "100px"
        return f"{len(self.procesos_esc) * 44 + 8}px"

    @rx.var
    def muestra_prioridad(self) -> bool:
        return self.escenario == "hospital"

    @rx.var
    def muestra_quantum(self) -> bool:
        return self.escenario == "callcenter"

    @rx.var
    def algoritmo_badge(self) -> str:
        m = {"banco": "FIFO", "hospital": "Prioridad", "supermercado": "SJF", "callcenter": "Round Robin"}
        return m.get(self.escenario, "FIFO")

    @rx.var
    def col_nombre(self) -> str:
        m = {"banco": "Cliente", "hospital": "Paciente", "supermercado": "Cliente", "callcenter": "Llamada"}
        return m.get(self.escenario, "Proceso")

    @rx.var
    def col_llegada(self) -> str:
        m = {"banco": "Hora llegada", "hospital": "Hora ingreso", "supermercado": "Hora llegada", "callcenter": "Hora llamada"}
        return m.get(self.escenario, "Llegada")

    @rx.var
    def col_rafaga(self) -> str:
        m = {"banco": "Tiempo trámite", "hospital": "Tiempo atención", "supermercado": "Artículos", "callcenter": "Duración"}
        return m.get(self.escenario, "Ráfaga")

    @rx.var
    def contexto_titulo(self) -> str:
        m = {
            "banco": "🏦 Fila del Banco",
            "hospital": "🏥 Sala de Urgencias",
            "supermercado": "🛒 Caja Rápida del Supermercado",
            "callcenter": "📞 Línea de Soporte Técnico",
        }
        return m.get(self.escenario, "")

    @rx.var
    def contexto_desc(self) -> str:
        m = {
            "banco": "En un banco, los clientes toman un turno numerado al llegar y son atendidos en estricto orden de llegada. No importa cuánto tiempo tome su trámite — el primero en llegar es el primero en ser atendido. Este es el algoritmo FIFO (First In, First Out).",
            "hospital": "En urgencias, un equipo de triaje clasifica a cada paciente según la gravedad de su condición. Un infarto (prioridad 1) se atiende antes que un resfriado (prioridad 5), sin importar quién llegó primero. Este es el algoritmo de Prioridad.",
            "supermercado": "En la caja rápida, se atiende primero al cliente con menos artículos. Esto minimiza el tiempo de espera promedio para todos. Es exactamente el algoritmo SJF (Shortest Job First): el trabajo más corto va primero.",
            "callcenter": "Cada agente atiende una llamada durante un tiempo fijo (quantum). Si no se resuelve, la llamada vuelve a la cola y se atiende la siguiente. Así nadie espera indefinidamente. Este es el algoritmo Round Robin.",
        }
        return m.get(self.escenario, "")

    @rx.var
    def explicacion_titulo(self) -> str:
        m = {
            "banco": "¿Por qué FIFO en un banco?",
            "hospital": "¿Por qué Prioridad en un hospital?",
            "supermercado": "¿Por qué SJF en un supermercado?",
            "callcenter": "¿Por qué Round Robin en un call center?",
        }
        return m.get(self.escenario, "")

    @rx.var
    def explicacion_texto(self) -> str:
        m = {
            "banco": "El banco usa FIFO porque es el algoritmo más justo y simple: todos los clientes son tratados por igual. Solo se necesita una máquina de turnos. Sin embargo, si un cliente tiene un trámite muy extenso, los demás deben esperar sin importar que sus trámites sean breves.",
            "hospital": "El hospital usa Prioridad porque salvar vidas es más importante que el orden de llegada. El sistema de triaje asigna niveles de urgencia (1 = crítico, 5 = leve). La desventaja es que pacientes con baja prioridad pueden esperar mucho tiempo si siguen llegando casos urgentes (inanición).",
            "supermercado": "La caja rápida aplica SJF: atiende primero al cliente con menos artículos. Matemáticamente, esto produce el menor tiempo de espera promedio posible. Sin embargo, un cliente con muchos artículos podría esperar indefinidamente si siguen llegando clientes con pocos artículos (inanición).",
            "callcenter": "El call center usa Round Robin para garantizar equidad: cada llamada recibe exactamente el mismo tiempo de atención antes de rotar. Ningún cliente queda abandonado (se evita la inanición). La desventaja es que genera más cambios de contexto y puede ser menos eficiente para problemas simples.",
        }
        return m.get(self.escenario, "")

    @rx.var
    def analogia_cpu(self) -> str:
        m = {"banco": "Ventanilla del cajero", "hospital": "Consultorio de urgencias", "supermercado": "Caja registradora", "callcenter": "Agente de soporte"}
        return m.get(self.escenario, "")

    @rx.var
    def analogia_proceso(self) -> str:
        m = {"banco": "Cliente con turno", "hospital": "Paciente ingresado", "supermercado": "Cliente en fila", "callcenter": "Llamada entrante"}
        return m.get(self.escenario, "")

    @rx.var
    def analogia_rafaga(self) -> str:
        m = {"banco": "Duración del trámite", "hospital": "Tiempo de atención médica", "supermercado": "Cantidad de artículos", "callcenter": "Complejidad del problema"}
        return m.get(self.escenario, "")

    @rx.var
    def analogia_cola(self) -> str:
        m = {"banco": "Sala de espera con turnos", "hospital": "Sala de espera de urgencias", "supermercado": "Fila de la caja rápida", "callcenter": "Llamadas en espera"}
        return m.get(self.escenario, "")

    # --- Events ---
    @rx.event
    def elegir_escenario(self, escenario_id: str):
        if not self.animando_esc:
            self.escenario = escenario_id
            self._limpiar_esc()
            if escenario_id in DATOS_DEFECTO:
                self.procesos_esc = [dict(p) for p in DATOS_DEFECTO[escenario_id]]

    @rx.event
    def set_velocidad_esc(self, valor: str | list[str]):
        self.velocidad_esc = str(valor)

    @rx.event
    def set_quantum_esc(self, valor: str):
        self.quantum_esc = valor

    @rx.event
    def editar_esc(self, i: int, campo: str, valor: str):
        procesos = [dict(p) for p in self.procesos_esc]
        procesos[i][campo] = valor
        self.procesos_esc = procesos

    @rx.event
    def agregar_esc(self):
        if len(self.procesos_esc) < MAX_PROCESOS:
            n = len(self.procesos_esc) + 1
            prio = random.randint(1, 5) if self.escenario == "hospital" else 0
            self.procesos_esc = self.procesos_esc + [crear_proceso_esc(n, n - 1, 3, prio)]

    @rx.event
    def eliminar_esc(self, i: int):
        if len(self.procesos_esc) > 1:
            restantes = [p for j, p in enumerate(self.procesos_esc) if j != i]
            self.procesos_esc = [
                crear_proceso_esc(n, p["llegada"], p["rafaga"], p["prioridad"])
                for n, p in enumerate(restantes, start=1)
            ]

    @rx.event
    def aleatorio_esc(self):
        cantidad = random.randint(4, 6)
        if self.escenario == "hospital":
            self.procesos_esc = [
                crear_proceso_esc(n, random.randint(0, 8), random.randint(1, 8), random.randint(1, 5))
                for n in range(1, cantidad + 1)
            ]
        else:
            self.procesos_esc = [
                crear_proceso_esc(n, random.randint(0, 8), random.randint(1, 8), 0)
                for n in range(1, cantidad + 1)
            ]
        self._limpiar_esc()

    def _limpiar_esc(self):
        self.gantt_segmentos_esc = []
        self.gantt_procesos_esc = []
        self.gantt_progreso_pct_esc = "0%"
        self.gantt_marcas_esc = []
        self.gantt_clip_path_esc = "inset(0 100% 0 0)"
        self.gantt_progreso_transition_esc = "none"
        self.resultados_esc = []
        self.ejecutando_esc = ""
        self.tiempo_actual_esc = "0"
        self.terminado_esc = False
        self.error_esc = ""

    def _leer_procesos_esc(self):
        datos = []
        for p in self.procesos_esc:
            try:
                llegada, rafaga = int(p["llegada"]), int(p["rafaga"])
                prioridad = int(p["prioridad"] or 0)
            except ValueError:
                raise ValueError(f"{p['nombre']}: todos los valores deben ser números enteros.")
            if llegada < 0 or rafaga < 1:
                raise ValueError(f"{p['nombre']}: la llegada debe ser ≥ 0 y la ráfaga ≥ 1.")
            datos.append({**p, "llegada": llegada, "rafaga": rafaga, "prioridad": prioridad})

        try:
            quantum = int(self.quantum_esc)
        except ValueError:
            quantum = 0
        if self.escenario == "callcenter" and quantum < 1:
            raise ValueError("El quantum debe ser un número entero ≥ 1.")
        if quantum < 1:
            quantum = 2
        return datos, quantum

    def _reconstruir_segmentos_esc(self, filas_dict, nombres_procesos, total):
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
        self.gantt_segmentos_esc = all_segs

    # ---------- Simulación animada ----------
    @rx.event(background=True)
    async def simular_esc(self):
        async with self:
            if self.animando_esc:
                return
            self._limpiar_esc()
            try:
                datos, quantum = self._leer_procesos_esc()
            except ValueError as e:
                self.error_esc = str(e)
                return
            self.animando_esc = True
            esc = self.escenario
            velocidad_factor = VELOCIDADES[self.velocidad_esc]

        mapping = {"banco": "FIFO", "hospital": "Prioridad", "supermercado": "SJF", "callcenter": "Round Robin"}
        algoritmo_nombre = mapping.get(esc, "FIFO")

        bloques = algoritmos.ejecutar(algoritmo_nombre, datos, quantum)
        colores = {p["nombre"]: p["color"] for p in datos}
        total = bloques[-1]["fin"] if bloques else 1

        nombres_procesos = [p["nombre"] for p in datos]
        proc_rows = [{"nombre": p["nombre"], "color": p["color"]} for p in datos]

        async with self:
            self.gantt_procesos_esc = proc_rows

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
            self._reconstruir_segmentos_esc(filas_dict, nombres_procesos, total)
            self.gantt_marcas_esc = marcas
            self.gantt_clip_path_esc = "inset(0 100% 0 0)"
            self.gantt_progreso_pct_esc = "0%"
            self.gantt_progreso_transition_esc = "none"
            self.tiempo_actual_esc = "0"

        await asyncio.sleep(0.1)

        tiempo_total_real = total * velocidad_factor
        async with self:
            if total > 0:
                self.gantt_progreso_pct_esc = "100%"
                self.gantt_clip_path_esc = "inset(0 0% 0 0)"
                self.gantt_progreso_transition_esc = f"clip-path {tiempo_total_real}s linear, left {tiempo_total_real}s linear, width {tiempo_total_real}s linear"

        for b in bloques:
            nombre = b["nombre"]
            inicio = b["inicio"]
            fin = b["fin"]
            duracion = fin - inicio
            duracion_real = duracion * velocidad_factor

            async with self:
                self.ejecutando_esc = nombre
                self.tiempo_actual_esc = str(inicio)

            await asyncio.sleep(duracion_real)

            async with self:
                self.tiempo_actual_esc = str(fin)

        async with self:
            self.resultados_esc = [
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
            self.prom_espera_esc = f"{prom_espera:.2f}"
            self.prom_sistema_esc = f"{prom_sistema:.2f}"
            self.animando_esc = False
            self.terminado_esc = True


# =====================================================================
#  COMPONENTES
# =====================================================================

def encabezado_escenarios():
    return rx.vstack(
        rx.hstack(
            rx.link(
                rx.button(
                    rx.icon("arrow-left", size=18),
                    "Simulador",
                    variant="soft",
                    color_scheme="gray",
                    size="3",
                ),
                href="/",
                underline="none",
            ),
            rx.link(
                rx.button(
                    rx.icon("flask-conical", size=18),
                    "Extras",
                    variant="soft",
                    color_scheme="gray",
                    size="3",
                ),
                href="/extras",
                underline="none",
            ),
            rx.spacer(),
            rx.badge(rx.icon("globe", size=14), "Vida Real", variant="soft",
                     radius="full", size="2", color_scheme="green"),
            width="100%",
            align="center",
        ),
        rx.heading("Algoritmos en la Vida Real", size="9", weight="bold",
                   class_name="titulo-gradiente-esc", text_align="center"),
        rx.text(
            "Descubre cómo los algoritmos de planificación de CPU se aplican en situaciones cotidianas.",
            color_scheme="gray", size="4", text_align="center", max_width="640px",
        ),
        align="center",
        spacing="3",
        class_name="aparecer",
    )


def titulo_seccion_esc(icono, texto, numero):
    return rx.hstack(
        rx.center(
            rx.text(numero, weight="bold", size="2"), width="28px", height="28px",
            border_radius="full", background="rgba(16,185,129,0.25)", color="#6ee7b7",
        ),
        rx.icon(icono, size=20, color="#34d399"),
        rx.heading(texto, size="5"),
        align="center",
        spacing="2",
    )


def tarjeta_escenario(esc):
    return rx.box(
        rx.vstack(
            rx.center(
                rx.icon(esc["icono"], size=28, color="white"),
                class_name=esc["clase_icono"],
            ),
            rx.text(esc["nombre"], weight="bold", size="5"),
            rx.badge(esc["algoritmo"], variant="surface", radius="full", size="2"),
            rx.text(esc["desc"], size="2", color_scheme="gray", text_align="center"),
            spacing="3",
            align="center",
        ),
        on_click=EscenariosState.elegir_escenario(esc["id"]),
        class_name=rx.cond(
            EscenariosState.escenario == esc["id"],
            "tarjeta-escenario activa-esc",
            "tarjeta-escenario",
        ),
    )


def seccion_escenarios():
    return rx.box(
        rx.vstack(
            titulo_seccion_esc("map-pin", "Elige un escenario", "1"),
            rx.grid(
                *[tarjeta_escenario(e) for e in ESCENARIOS],
                columns=rx.breakpoints(initial="2", md="4"),
                spacing="3",
                width="100%",
            ),
            spacing="4",
        ),
        class_name="vidrio aparecer",
    )


def seccion_contexto():
    """Tarjeta que explica el escenario seleccionado y qué algoritmo usa."""
    return rx.box(
        rx.vstack(
            titulo_seccion_esc("book-open", "Contexto", "2"),
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.text(EscenariosState.contexto_titulo, weight="bold", size="6"),
                        rx.spacer(),
                        rx.badge(
                            "Algoritmo: ",
                            EscenariosState.algoritmo_badge,
                            color_scheme="green",
                            variant="surface",
                            radius="full",
                            size="2",
                        ),
                        width="100%",
                        align="center",
                        wrap="wrap",
                        gap="2",
                    ),
                    rx.text(
                        EscenariosState.contexto_desc,
                        size="3", color_scheme="gray", line_height="1.7",
                    ),
                    spacing="3",
                ),
                class_name="tarjeta-contexto-esc",
            ),
            spacing="4",
        ),
        class_name="vidrio aparecer",
    )


def punto_color_esc(color):
    return rx.box(width="12px", height="12px", border_radius="50%", background=color, flex_shrink="0")


def campo_numero_esc(valor, al_cambiar):
    return rx.input(value=valor, on_change=al_cambiar, type="number", min=0,
                    variant="soft", width="90px", size="2")


def fila_proceso_esc(p, i):
    return rx.table.row(
        rx.table.cell(rx.hstack(punto_color_esc(p["color"]), rx.text(p["nombre"], weight="bold"), align="center")),
        rx.table.cell(campo_numero_esc(p["llegada"], lambda v: EscenariosState.editar_esc(i, "llegada", v))),
        rx.table.cell(campo_numero_esc(p["rafaga"], lambda v: EscenariosState.editar_esc(i, "rafaga", v))),
        rx.cond(
            EscenariosState.muestra_prioridad,
            rx.table.cell(campo_numero_esc(p["prioridad"], lambda v: EscenariosState.editar_esc(i, "prioridad", v))),
        ),
        rx.table.cell(
            rx.icon_button(rx.icon("trash-2", size=16), on_click=EscenariosState.eliminar_esc(i),
                           variant="ghost", color_scheme="red", disabled=EscenariosState.animando_esc),
        ),
        align="center",
        class_name="aparecer",
    )


def seccion_procesos_esc():
    return rx.box(
        rx.vstack(
            rx.hstack(
                titulo_seccion_esc("table", "Datos del escenario", "3"),
                rx.spacer(),
                rx.button(rx.icon("shuffle", size=16), "Aleatorio", on_click=EscenariosState.aleatorio_esc,
                          variant="soft", color_scheme="gray", disabled=EscenariosState.animando_esc),
                rx.button(rx.icon("plus", size=16), "Agregar", on_click=EscenariosState.agregar_esc,
                          variant="soft", disabled=EscenariosState.animando_esc),
                width="100%",
                align="center",
                wrap="wrap",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(EscenariosState.col_nombre),
                        rx.table.column_header_cell(EscenariosState.col_llegada),
                        rx.table.column_header_cell(EscenariosState.col_rafaga),
                        rx.cond(EscenariosState.muestra_prioridad, rx.table.column_header_cell("Urgencia")),
                        rx.table.column_header_cell(""),
                    ),
                ),
                rx.table.body(rx.foreach(EscenariosState.procesos_esc, fila_proceso_esc)),
                variant="ghost",
                width="100%",
            ),
            # Controles de simulación
            rx.hstack(
                rx.cond(
                    EscenariosState.muestra_quantum,
                    rx.hstack(
                        rx.icon("timer", size=18, color="#34d399"),
                        rx.text("Quantum", weight="medium"),
                        rx.input(
                            value=EscenariosState.quantum_esc,
                            on_change=EscenariosState.set_quantum_esc,
                            type="number", min=1, width="80px", variant="soft",
                        ),
                        align="center",
                        class_name="aparecer",
                    ),
                ),
                rx.hstack(
                    rx.icon("gauge", size=18, color="#34d399"),
                    rx.text("Velocidad", weight="medium"),
                    rx.segmented_control.root(
                        *[rx.segmented_control.item(v, value=v) for v in VELOCIDADES],
                        value=EscenariosState.velocidad_esc,
                        on_change=EscenariosState.set_velocidad_esc,
                    ),
                    align="center",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("play", size=18),
                    rx.cond(EscenariosState.animando_esc, "Simulando...", "Simular"),
                    on_click=EscenariosState.simular_esc,
                    loading=EscenariosState.animando_esc,
                    size="3",
                    class_name="boton-simular-esc",
                ),
                width="100%",
                align="center",
                spacing="5",
                wrap="wrap",
            ),
            rx.cond(
                EscenariosState.error_esc != "",
                rx.callout(EscenariosState.error_esc, icon="triangle-alert", color_scheme="red", width="100%"),
            ),
            spacing="4",
        ),
        class_name="vidrio aparecer",
    )


# =====================================================================
#  DIAGRAMA DE GANTT
# =====================================================================

def segmento_gantt_esc(seg):
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


def fila_proceso_gantt_esc(proc):
    return rx.hstack(
        rx.box(
            width="10px", height="10px", border_radius="50%",
            background=proc["color"], flex_shrink="0",
        ),
        rx.text(proc["nombre"], weight="bold", size="2", white_space="nowrap"),
        align="center",
        spacing="2",
        height="36px",
    )


def estado_gantt_esc():
    return rx.cond(
        EscenariosState.animando_esc,
        rx.hstack(
            rx.box(class_name="punto-vivo-esc"),
            rx.text("Atendiendo ", rx.text.strong(EscenariosState.ejecutando_esc), size="2"),
            rx.badge("t = ", EscenariosState.tiempo_actual_esc, variant="surface", size="2"),
            align="center",
        ),
        rx.cond(
            EscenariosState.terminado_esc,
            rx.badge(rx.icon("circle-check", size=14), "Completado en t = ", EscenariosState.tiempo_actual_esc,
                     color_scheme="green", size="2", radius="full"),
        ),
    )


def leyenda_velocidad_esc():
    return rx.cond(
        EscenariosState.animando_esc,
        rx.hstack(
            rx.icon("clock", size=14, color="#34d399"),
            rx.text(
                "1 u.t. = ",
                rx.cond(EscenariosState.velocidad_esc == "Lenta", "1.0s",
                        rx.cond(EscenariosState.velocidad_esc == "Normal", "0.5s", "0.2s")),
                " real",
                size="1", color_scheme="gray",
            ),
            align="center",
            spacing="1",
        ),
    )


def seccion_gantt_esc():
    return rx.box(
        rx.vstack(
            rx.hstack(
                titulo_seccion_esc("chart-no-axes-gantt", "Diagrama de Gantt", "4"),
                rx.spacer(),
                leyenda_velocidad_esc(),
                estado_gantt_esc(),
                width="100%",
                align="center",
                wrap="wrap",
                gap="3",
            ),
            rx.cond(
                EscenariosState.gantt_procesos_esc.length() > 0,
                rx.vstack(
                    rx.hstack(
                        rx.vstack(
                            rx.foreach(EscenariosState.gantt_procesos_esc, fila_proceso_gantt_esc),
                            spacing="2",
                            min_width="70px",
                        ),
                        rx.box(
                            # Marcas de tiempo
                            rx.foreach(EscenariosState.gantt_marcas_esc, lambda m: rx.box(
                                position="absolute",
                                top="0", bottom="0", left=m["left_pct"],
                                border_left="1px dashed rgba(255,255,255,0.15)",
                                z_index="0",
                            )),
                            # Segmentos con clip-path
                            rx.box(
                                rx.foreach(EscenariosState.gantt_segmentos_esc, segmento_gantt_esc),
                                position="absolute",
                                inset="0",
                                clip_path=EscenariosState.gantt_clip_path_esc,
                                transition=EscenariosState.gantt_progreso_transition_esc,
                                z_index="1",
                            ),
                            # Línea de progreso
                            rx.box(
                                position="absolute",
                                left=EscenariosState.gantt_progreso_pct_esc,
                                top="0", bottom="0",
                                width="2px",
                                background="#34d399",
                                box_shadow="0 0 8px #34d399",
                                transition=EscenariosState.gantt_progreso_transition_esc,
                                z_index="10",
                            ),
                            position="relative",
                            width="100%",
                            height=EscenariosState.gantt_altura_esc,
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
                    # Eje de tiempo
                    rx.hstack(
                        rx.box(min_width="70px"),
                        rx.box(
                            rx.box(
                                position="absolute",
                                left="0", top="0", bottom="0",
                                width=EscenariosState.gantt_progreso_pct_esc,
                                background="linear-gradient(90deg, rgba(16,185,129,0.12), rgba(52,211,153,0.08))",
                                transition=EscenariosState.gantt_progreso_transition_esc,
                            ),
                            rx.foreach(EscenariosState.gantt_marcas_esc, lambda m: rx.box(
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
                        rx.text("Presiona ", rx.text.strong("Simular"), " para ver la simulación",
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
        id="gantt-esc",
    )


# =====================================================================
#  RESULTADOS
# =====================================================================

def tarjeta_promedio_esc(titulo, valor, icono, clase, formula):
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


def celda_calculo_esc(resultado, operacion):
    return rx.table.cell(
        rx.hstack(
            rx.text(operacion, size="1", color_scheme="gray", font_family="JetBrains Mono"),
            rx.text(resultado, weight="bold", size="3"),
            align="center",
            spacing="2",
        )
    )


def fila_resultado_esc(r):
    return rx.table.row(
        rx.table.cell(rx.hstack(punto_color_esc(r["color"]), rx.text(r["nombre"], weight="bold"), align="center")),
        rx.table.cell(r["llegada"]),
        rx.table.cell(r["rafaga"]),
        rx.table.cell(r["fin"]),
        celda_calculo_esc(r["sistema"], r["fin"] + " − " + r["llegada"] + " ="),
        celda_calculo_esc(r["espera"], r["sistema"] + " − " + r["rafaga"] + " ="),
        align="center",
        class_name="aparecer",
        style={"animation_delay": r["retraso"]},
    )


def seccion_resultados_esc():
    return rx.cond(
        EscenariosState.terminado_esc,
        rx.box(
            rx.vstack(
                titulo_seccion_esc("chart-column", "Resultados", "5"),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(EscenariosState.col_nombre),
                            rx.table.column_header_cell("Llegada"),
                            rx.table.column_header_cell("Ráfaga"),
                            rx.table.column_header_cell("Finaliza"),
                            rx.table.column_header_cell("T. Sistema"),
                            rx.table.column_header_cell("T. Espera"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(EscenariosState.resultados_esc, fila_resultado_esc),
                        rx.table.row(
                            rx.table.cell(rx.text("Promedio", weight="bold")),
                            rx.table.cell(""), rx.table.cell(""), rx.table.cell(""),
                            rx.table.cell(rx.text(EscenariosState.prom_sistema_esc, weight="bold", color="#34d399")),
                            rx.table.cell(rx.text(EscenariosState.prom_espera_esc, weight="bold", color="#f59e0b")),
                            background="rgba(255,255,255,0.04)",
                        ),
                    ),
                    variant="ghost",
                    width="100%",
                ),
                rx.grid(
                    tarjeta_promedio_esc("Tiempo de espera promedio", EscenariosState.prom_espera_esc, "hourglass",
                                        "stat-espera", "Espera = T. Sistema − Ráfaga"),
                    tarjeta_promedio_esc("Tiempo de sistema promedio", EscenariosState.prom_sistema_esc, "clock",
                                        "stat-sistema-esc", "Sistema = Finalización − Llegada"),
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
#  EXPLICACIÓN DEL ALGORITMO
# =====================================================================

def seccion_explicacion():
    return rx.cond(
        EscenariosState.terminado_esc,
        rx.box(
            rx.vstack(
                titulo_seccion_esc("lightbulb", "¿Por qué este algoritmo?", "6"),
                rx.box(
                    rx.vstack(
                        rx.heading(EscenariosState.explicacion_titulo, size="5", weight="bold"),
                        rx.text(
                            EscenariosState.explicacion_texto,
                            size="3", color_scheme="gray", line_height="1.8",
                        ),
                        rx.separator(size="4"),
                        rx.heading("Analogía con la CPU", size="4", weight="bold"),
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Concepto de CPU"),
                                    rx.table.column_header_cell("En este escenario"),
                                )
                            ),
                            rx.table.body(
                                rx.table.row(
                                    rx.table.cell(rx.hstack(
                                        rx.icon("cpu", size=14, color="#34d399"),
                                        rx.text("CPU", weight="bold"), align="center",
                                    )),
                                    rx.table.cell(EscenariosState.analogia_cpu),
                                ),
                                rx.table.row(
                                    rx.table.cell(rx.hstack(
                                        rx.icon("box", size=14, color="#34d399"),
                                        rx.text("Proceso", weight="bold"), align="center",
                                    )),
                                    rx.table.cell(EscenariosState.analogia_proceso),
                                ),
                                rx.table.row(
                                    rx.table.cell(rx.hstack(
                                        rx.icon("zap", size=14, color="#34d399"),
                                        rx.text("Ráfaga de CPU", weight="bold"), align="center",
                                    )),
                                    rx.table.cell(EscenariosState.analogia_rafaga),
                                ),
                                rx.table.row(
                                    rx.table.cell(rx.hstack(
                                        rx.icon("users", size=14, color="#34d399"),
                                        rx.text("Cola de listos", weight="bold"), align="center",
                                    )),
                                    rx.table.cell(EscenariosState.analogia_cola),
                                ),
                            ),
                            variant="ghost",
                            width="100%",
                        ),
                        rx.separator(size="4"),
                        rx.hstack(
                            rx.cond(
                                EscenariosState.escenario == "callcenter",
                                rx.badge("Expropiativo", color_scheme="red", radius="full"),
                                rx.badge("No expropiativo", color_scheme="green", radius="full"),
                            ),
                            rx.cond(
                                EscenariosState.escenario == "banco",
                                rx.badge("Justo y simple", color_scheme="blue", radius="full"),
                            ),
                            rx.cond(
                                (EscenariosState.escenario == "hospital") | (EscenariosState.escenario == "supermercado"),
                                rx.badge("Riesgo de inanición", color_scheme="orange", radius="full"),
                            ),
                            rx.cond(
                                EscenariosState.escenario == "supermercado",
                                rx.badge("Óptimo en espera", color_scheme="green", radius="full"),
                            ),
                            rx.cond(
                                EscenariosState.escenario == "callcenter",
                                rx.badge("Equitativo", color_scheme="blue", radius="full"),
                            ),
                            rx.cond(
                                EscenariosState.escenario == "hospital",
                                rx.badge("Basado en triaje", color_scheme="red", radius="full"),
                            ),
                            wrap="wrap",
                            spacing="2",
                        ),
                        spacing="4",
                    ),
                    class_name="tarjeta-explicacion-esc",
                ),
                spacing="4",
            ),
            class_name="vidrio aparecer",
        ),
    )


# =====================================================================
#  PARTÍCULAS DE FONDO
# =====================================================================

def particulas_fondo_esc():
    return rx.script("""
    (function() {
        if (document.getElementById('bg-particles-canvas-esc')) return;
        const canvas = document.createElement('canvas');
        canvas.id = 'bg-particles-canvas-esc';
        canvas.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:1;pointer-events:none;opacity:0.6;';
        document.body.appendChild(canvas);
        const ctx = canvas.getContext('2d');
        const COLORS = ['#10b981','#34d399','#06b6d4','#22d3ee','#6ee7b7','#a78bfa'];
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
                        ctx.strokeStyle = '#10b981';
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

def escenarios_page():
    return rx.box(
        particulas_fondo_esc(),
        rx.container(
            rx.vstack(
                encabezado_escenarios(),
                seccion_escenarios(),
                seccion_contexto(),
                seccion_procesos_esc(),
                seccion_gantt_esc(),
                seccion_resultados_esc(),
                seccion_explicacion(),
                rx.text("Desarrollado por: ", size="1", color_scheme="gray", align_self="center"),
                rx.text("Kevin Esteban Sánchez Torres ", size="1", color_scheme="gray", align_self="center"),
                rx.text("Yeison Orozco Vasco ", size="1", color_scheme="gray", align_self="center"),
                spacing="6",
                padding_y="48px",
            ),
            size="4",
            position="relative",
            z_index="1",
        ),
        class_name="fondo-esc",
    )
