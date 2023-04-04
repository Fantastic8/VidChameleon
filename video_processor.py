from abc import ABC, abstractmethod


class VideoProcessor(ABC):
    @abstractmethod
    def process(self, input_path: str, output_path: str) -> None:
        pass

    # 插件配置 (优化9)
    def configure(self, config: dict) -> None:
        pass
