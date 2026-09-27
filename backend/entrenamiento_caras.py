from pathlib import Path
from ultralytics import YOLO

RAIZ = Path(__file__).resolve().parent.parent

if __name__ == '__main__':
    model = YOLO('yolo26n.pt')

    model.train(
        data=str(RAIZ / 'datasets' / 'wider_face' / 'data.yaml'),
        epochs=50,
        imgsz=640,
        batch=8,
        name='privacy_shield_faces_v2',
        project=str(RAIZ / 'resultados' / 'entrenamiento_caras'),
        device=0,
        patience=15,
        save=True,
        val=True,
        plots=True,
        workers=2,
        cache=False,
        fraction=0.3,
    )

    print('Entrenamiento completado')