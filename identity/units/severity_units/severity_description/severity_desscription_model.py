class SeverityDescriptionModel:
    description : str
    guidance : str

    def __init__(
        self,
        *,
        des: str,
        guid: str,
    ):
        self.description = des
        self.guidance = guid