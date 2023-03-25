# example_plugin.py

from video_framework import VideoProcessor

class ExamplePlugin(VideoProcessor):
    def __init__(self):
        self.option1 = None
        self.option2 = None

    def process(self, input_path: str, output_path: str) -> None:
        # 在这里实现视频处理逻辑
        print(f"处理视频：{input_path}，使用配置：option1={self.option1}, option2={self.option2}")

    def configure(self, config: dict) -> None:
        self.option1 = config.get('option1')
        self.option2 = config.get('option2')