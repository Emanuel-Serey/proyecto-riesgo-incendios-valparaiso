from pathlib import Path
from transformers import pipeline


BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "images"

MODEL_NAME = "dima806/wildfire_types_image_detection"


def main():
    print("Cargando modelo contextual liviano...")

    clasificador = pipeline(
        "image-classification",
        model=MODEL_NAME
    )

    print("Modelo cargado.\n")

    extensiones = {".jpg", ".jpeg", ".png", ".webp"}

    imagenes = [
        archivo
        for archivo in IMAGES_DIR.rglob("*")
        if archivo.suffix.lower() in extensiones
    ]

    print(f"Imágenes encontradas: {len(imagenes)}")

    for imagen in imagenes:

        print("\n" + "=" * 60)
        print(f"Imagen: {imagen.name}")

        resultados = clasificador(
            str(imagen),
            top_k=5
        )

        for resultado in resultados:
            print(
                f"- {resultado['label']}: "
                f"{resultado['score'] * 100:.2f}%"
            )


if __name__ == "__main__":
    main()