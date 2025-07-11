# Proyecto de Preprocesamiento y Análisis de Imágenes

Este proyecto contiene scripts y notebooks para el preprocesamiento de imágenes, análisis de datos de imágenes y clustering.

## Estructura del Proyecto

- `requirements.txt`: Lista de dependencias de Python necesarias para ejecutar el proyecto.
- `Image_data.py`: Script para el manejo y preprocesamiento de datos de imágenes.
- `clustering.py`: Script que contiene la lógica para algoritmos de clustering.
- `main.py`: El punto de entrada principal para ejecutar las operaciones del proyecto.
- `clustering_simulation.ipynb`: Un Jupyter Notebook para simular y visualizar resultados de clustering.
- `testing_notebook.ipynb`: Un Jupyter Notebook para pruebas y experimentación.
- `.gitignore`: Archivo para especificar archivos y directorios que Git debe ignorar.

## Configuración del Entorno

Para configurar el entorno de desarrollo y ejecutar el proyecto, sigue estos pasos:

1.  **Clonar el repositorio** (si aún no lo has hecho):

    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd image_preprocessing
    ```

2.  **Crear un entorno virtual** (recomendado):

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instalar las dependencias**:

    ```bash
    pip install -r requirements.txt
    ```

## Uso

### Ejecutar el script principal

Para ejecutar el script principal del proyecto, que probablemente orquesta las tareas de preprocesamiento y clustering:

```bash
python main.py