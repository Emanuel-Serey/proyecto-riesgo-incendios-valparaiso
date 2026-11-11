from pathlib import Path

from huggingface_hub import hf_hub_download
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "images"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def cargar_modelo():
    print("Descargando/cargando modelo...")

    pesos = hf_hub_download(
        repo_id="rabahdev/fire-smoke-yolov8n",
        filename="best.pt"
    )

    modelo = YOLO(pesos)

    print("Modelo cargado.")
    print("Clases:", modelo.names)

    return modelo


def probar_imagen(modelo, ruta_imagen):
    print("\n" + "=" * 60)
    print(f"Imagen: {ruta_imagen.name}")

    resultados = modelo.predict(
        source=str(ruta_imagen),
        conf=0.25,
        save=True,
        project=str(OUTPUT_DIR),
        name="detecciones",
        exist_ok=True,
        verbose=False
    )

    resultado = resultados[0]

    if len(resultado.boxes) == 0:
        print("❌ No se detectó fuego ni humo.")
        return

    print(f"✅ Detecciones encontradas: {len(resultado.boxes)}")

    for box in resultado.boxes:
        clase_id = int(box.cls[0])
        confianza = float(box.conf[0])

        clase = modelo.names[clase_id]

        print(
            f"  - {clase}: "
            f"{confianza * 100:.2f}%"
        )


def main():
    modelo = cargar_modelo()

    extensiones = {".jpg", ".jpeg", ".png", ".webp"}

    imagenes = [
        archivo
        for archivo in IMAGES_DIR.rglob("*")
        if archivo.suffix.lower() in extensiones
    ]

    if not imagenes:
        print("No hay imágenes para probar.")
        return

    print(f"\nImágenes encontradas: {len(imagenes)}")

    for imagen in imagenes:
        probar_imagen(modelo, imagen)


if __name__ == "__main__":
    main()