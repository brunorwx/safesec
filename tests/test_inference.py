from camera.capture.models import Frame
from detection.inference.ultralytics import UltralyticsDetector


class FakeImage:
    shape = (100, 100, 3)


class FakeBoxes:
    xyxy = [[10, 20, 50, 80], [0, 0, 5, 5]]
    conf = [0.9, 0.2]
    cls = [0, 0]


class FakeResult:
    boxes = FakeBoxes()
    names = {0: "person"}


class IrrelevantResult:
    boxes = FakeBoxes()
    names = {0: "umbrella"}


class FakeModel:
    def __init__(self, _: str) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, image: object, **kwargs: object) -> list[FakeResult]:
        self.calls.append({"image": image, **kwargs})
        return [FakeResult(), IrrelevantResult()]


def make_frame() -> Frame:
    return Frame.from_image(FakeImage(), camera_id="cam-1", sequence=4, monotonic_time=2.0)


def test_detector_lazily_loads_and_filters_results() -> None:
    model = FakeModel("weights.pt")
    detector = UltralyticsDetector(model_factory=lambda path: model, confidence_threshold=0.5)

    detections = detector.detect(make_frame())

    assert len(detections) == 1
    assert detections[0].label == "person"
    assert detections[0].box.left == 10
    assert len(model.calls) == 1


def test_detector_reuses_loaded_model() -> None:
    models: list[FakeModel] = []

    def factory(path: str) -> FakeModel:
        model = FakeModel(path)
        models.append(model)
        return model

    detector = UltralyticsDetector(model_factory=factory)
    detector.detect(make_frame())
    detector.detect(make_frame())

    assert len(models) == 1
    assert len(models[0].calls) == 2
