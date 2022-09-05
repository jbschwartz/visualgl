class Scene:
    def __init__(self, **kwargs) -> None:
        self.camera: Camera = kwargs.get("camera", Camera())
