from pathlib import Path
from ultralytics import YOLO

RAIZ = Path(__file__).resolve().parent.parent

if __name__ == '__main__':
    model = YOLO('yolo26n.pt')

    model.train(
        data=str(RAIZ / 'datasets' / 'matriculas' / 'data.yaml'),
        epochs=50,
        imgsz=640,
        batch=8,
        name='privacy_shield_plates_v1',
        project=str(RAIZ / 'resultados' / 'entrenamiento_matriculas'),
        device=0,
        patience=15,
        save=True,
        val=True,
        plots=True,
        workers=0,
        cache=False,
        fraction=0.1,
    )

    print('Entrenamiento completado.')