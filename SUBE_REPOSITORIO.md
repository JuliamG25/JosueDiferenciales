# 📤 Instrucciones para Subir el Repositorio a GitHub

## Opción 1: Desde la Interfaz Web de GitHub (Recomendado)

1. **Crear un nuevo repositorio en GitHub:**
   - Ve a https://github.com/new
   - Nombre del repositorio: `solucionador-ecuaciones-diferenciales` (o el nombre que prefieras)
   - Descripción: "Solucionador de Ecuaciones Diferenciales con Flask y SymPy"
   - Selecciona **Público** o **Privado** según prefieras
   - **NO marques** "Initialize this repository with a README" (ya tenemos uno)
   - Haz clic en "Create repository"

2. **Conectar y subir tu código:**
   
   Ejecuta estos comandos en la terminal (estando en el directorio del proyecto):

   ```bash
   git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
   git push -u origin main
   ```

   **Nota:** Reemplaza `TU_USUARIO` con tu nombre de usuario de GitHub y `TU_REPOSITORIO` con el nombre que le diste al repositorio.

## Opción 2: Usando GitHub CLI (si lo tienes instalado)

```bash
gh repo create solucionador-ecuaciones-diferenciales --public --source=. --remote=origin --push
```

## Opción 3: Verificar configuración de Git (si necesitas configurarlo)

Si no has configurado tu nombre y email en Git:

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu.email@ejemplo.com"
```

## Comandos rápidos (después de crear el repositorio en GitHub)

```bash
# Agregar el repositorio remoto
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git

# Subir el código
git push -u origin main
```

## Verificar que todo está bien

Después de subir, puedes verificar con:

```bash
git remote -v
```

Esto debería mostrar tu repositorio remoto.

---

**¡Listo!** Tu código estará disponible en GitHub. 🎉

