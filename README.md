# Simulador de Algoritmos de Despacho

Este proyecto es una aplicación web interactiva desarrollada en Python utilizando el framework Reflex. Su propósito principal es simular y visualizar el comportamiento de los algoritmos de planificacion de procesos de CPU mas utilizados en los sistemas operativos.

## Características Principales

El simulador se divide en varias secciones para ofrecer una experiencia de aprendizaje teórica, práctica y analítica:

1. **Simulador Base**
   - Implementa los algoritmos clásicos: First In First Out (FIFO), Shortest Job First (SJF), Planificación por Prioridad y Round Robin.
   - Permite la configuración manual de procesos (tiempo de llegada, ráfaga de CPU, prioridad).
   - Genera diagramas de Gantt visuales para seguir la ejecución en el tiempo.
   - Calcula automáticamente métricas clave como el tiempo de espera promedio y el tiempo de retorno (sistema) promedio.

2. **Algoritmos Extras**
   - Incorpora versiones expropiativas y multinivel.
   - Shortest Remaining Time First (SRTF): Versión expropiativa de SJF.
   - Colas Multinivel (MLQ): Implementación con dos colas (Round Robin para procesos de sistema interactivos y FIFO para procesos por lotes en segundo plano).

3. **Escenarios de la Vida Real**
   - Configuraciones predefinidas que simulan situaciones reales (servidores web de alta carga, sistemas de procesamiento por lotes, sistemas embebidos, etc.).
   - Sirve para analizar empíricamente por qué ciertos sistemas eligen ciertos algoritmos por defecto.

4. **Análisis Avanzado**
   - **Barrido de Quantum (Round Robin):** Herramienta que evalúa el mismo conjunto de procesos iterando sobre distintos valores de quantum para encontrar graficamente el punto de equilibrio optimo entre el tiempo de espera y el costo por cambio de contexto.
   - **Simulación Monte Carlo:** Ejecuta miles de escenarios con procesos generados aleatoriamente bajo rangos definidos por el usuario. Presenta graficas estadisticas que muestran la evolucion de victorias de cada algoritmo, comparativas de tiempos de espera, y tablas de distribucion estadistica.

## Requisitos y Tecnologías

- Python 3.10 o superior
- Reflex (Framework web en Python puro)
- Entorno virtual (recomendado)

## Instalación y Ejecución

Siga los siguientes pasos para ejecutar el proyecto en un entorno local:

1. Clonar el repositorio y navegar al directorio del proyecto:
   git clone <url-del-repositorio>
   cd Algoritmos-de-despacho

2. Crear y activar un entorno virtual:
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En macOS/Linux:
   source venv/bin/activate

3. Instalar las dependencias (si existe un archivo requirements.txt) o inicializar Reflex:
   pip install reflex
   reflex init

4. Ejecutar el servidor de desarrollo:
   reflex run

5. Acceder a la aplicación:
   Abra un navegador web y navegue a http://localhost:3000

## Arquitectura del Proyecto

El proyecto sigue una arquitectura desacoplada y orientada a componentes gracias al sistema de estados (State) de Reflex:

- **algoritmos.py**: Contiene exclusivamente la lógica pura de planificación. Las funciones reciben listas de diccionarios y devuelven el historial de ejecución (Gantt) y las métricas numéricas correspondientes. No interactúa con la interfaz.
- **simulador.py**: Punto de entrada de la aplicación y declaración del estado principal (SimuladorState). Contiene los componentes visuales de la página principal (tabla de procesos, controles, diagramas).
- **extras.py**: Página y estado independientes para algoritmos especiales (SRTF y MLQ).
- **escenarios.py**: Página y estado independientes para la carga y evaluación de casos de uso predefinidos.
- **analisis.py**: Página y estado independientes enfocados en la generación masiva de datos (Barrido y Monte Carlo) y renderizado de gráficas interactivas con Recharts.
- **assets/styles.css**: Hoja de estilos globales que define la estética oscura (dark mode), el efecto de cristal (glassmorphism) y las animaciones de la interfaz.

## Contribuciones

Este proyecto está diseñado de forma aditiva. Cualquier nuevo algoritmo de despacho puede ser integrado agregando su respectiva lógica en `algoritmos.py` y llamando a la función desde cualquiera de los estados de la interfaz sin afectar el resto del flujo.
