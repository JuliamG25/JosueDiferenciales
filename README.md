# 🔬 Solucionador de Ecuaciones Diferenciales

Una aplicación web moderna y completa para resolver ecuaciones diferenciales paso a paso. Desarrollada con Flask, SymPy y una interfaz web moderna.

## 📋 Características

La aplicación puede resolver los siguientes tipos de ecuaciones diferenciales:

1. **Variables Separables** - Ecuaciones que se pueden separar en términos de x e y
2. **Ecuaciones Homogéneas** - Ecuaciones diferenciales homogéneas
3. **Ecuaciones Exactas** - Ecuaciones diferenciales exactas
4. **Ecuaciones Lineales** - Ecuaciones diferenciales lineales de primer orden
5. **Ecuación de Bernoulli** - Ecuaciones diferenciales de Bernoulli
6. **Reducibles a Primer Orden** - Ecuaciones que se pueden reducir a primer orden
7. **Coeficientes Constantes** - Ecuaciones con coeficientes constantes
8. **Coeficientes Indeterminados** - Método de coeficientes indeterminados para ecuaciones de orden superior
9. **Factor Integrante** - Resolución mediante factores integrantes

## 🚀 Instalación

### Requisitos previos

- Python 3.7 o superior
- pip (gestor de paquetes de Python)

### Pasos de instalación

1. **Clonar o descargar el proyecto**

2. **Crear un entorno virtual (recomendado)**
   ```bash
   python -m venv venv
   ```

3. **Activar el entorno virtual**
   
   En Windows:
   ```bash
   venv\Scripts\activate
   ```
   
   En Linux/Mac:
   ```bash
   source venv/bin/activate
   ```

4. **Instalar las dependencias**
   ```bash
   pip install -r requirements.txt
   ```

## 💻 Uso

1. **Iniciar el servidor**
   ```bash
   python app.py
   ```

2. **Abrir en el navegador**
   - Navega a: `http://localhost:5000`

3. **Usar la aplicación**
   - Ingresa tu ecuación diferencial en el campo de texto
   - Selecciona el método de solución (o deja "Auto-detectado")
   - Haz clic en "Resolver Ecuación"
   - Revisa la solución y los pasos detallados

## 📝 Formatos de Entrada

La aplicación acepta ecuaciones en diferentes formatos:

### Derivadas
- `y'` - Primera derivada
- `y''` - Segunda derivada
- `dy/dx` - Notación de Leibniz para primera derivada

### Operadores
- `+`, `-`, `*`, `/` - Operaciones básicas
- `**` o `^` - Potenciación (usa `**` para mejor compatibilidad)
- `exp(x)` - Función exponencial
- `log(x)` - Logaritmo natural
- `sin(x)`, `cos(x)`, `tan(x)` - Funciones trigonométricas

### Ejemplos de Ecuaciones

```
y' = x*y
dy/dx = x**2 + y**2
y' + 2*y = exp(x)
y'' + 3*y' + 2*y = 0
y' = y*(1-y)
```

## 🎯 Ejemplos Incluidos

La aplicación incluye ejemplos precargados que puedes hacer clic para resolver automáticamente:

- Variables Separables: `y' = x*y`
- Ecuación Homogénea
- Ecuación Lineal: `y' + y/x = x²`
- Ecuación de Bernoulli
- Ecuaciones con Coeficientes Constantes
- Ecuaciones con Exponenciales

## 🛠️ Tecnologías Utilizadas

- **Backend**: Flask (Python web framework)
- **Matemáticas**: SymPy (biblioteca de matemáticas simbólicas)
- **Frontend**: HTML5, CSS3, JavaScript
- **Renderizado Matemático**: MathJax

## 📚 Estructura del Proyecto

```
josue/
├── app.py                 # Aplicación Flask principal
├── requirements.txt       # Dependencias del proyecto
├── README.md             # Este archivo
├── templates/
│   └── index.html        # Plantilla HTML principal
└── static/
    ├── style.css         # Estilos CSS
    └── script.js         # JavaScript del frontend
```

## 🔧 Personalización

Puedes modificar los siguientes aspectos:

- **Puerto del servidor**: Edita `app.py` línea final y cambia `port=5000`
- **Estilos**: Modifica `static/style.css`
- **Funcionalidad**: Edita `static/script.js`

## ⚠️ Notas Importantes

- Asegúrate de escribir las ecuaciones correctamente
- Usa `**` en lugar de `^` para potencias para mejor compatibilidad
- Algunas ecuaciones complejas pueden requerir más tiempo para resolver
- El modo "Auto-detectado" intenta encontrar el mejor método automáticamente

## 🐛 Solución de Problemas

### Error: "ModuleNotFoundError: No module named 'flask'"
- Solución: Instala las dependencias con `pip install -r requirements.txt`

### Error: "Address already in use"
- Solución: Cambia el puerto en `app.py` (línea final) a otro número como 5001

### La ecuación no se resuelve
- Verifica que la ecuación esté escrita correctamente
- Prueba con el formato: `y' = expresión`
- Usa `**` para potencias en lugar de `^`

## 📄 Licencia

Este proyecto es de código abierto y está disponible para uso educativo.

## 👨‍💻 Autor

Desarrollado como herramienta educativa para resolver ecuaciones diferenciales.

---

**¡Disfruta resolviendo ecuaciones diferenciales!** 🎉

