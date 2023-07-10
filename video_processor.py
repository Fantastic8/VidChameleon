from abc import ABC, abstractmethod


class VideoProcessor(ABC):
    @abstractmethod
    def process(self, input_path: str, output_path: str) -> None:
        pass

    # 插件配置 (优化9)
    def configure(self, config: dict) -> None:
        pass

    # 插件自定义文件名过滤器,True:处理,False:跳过
    def file_filter(self, input_file) -> bool:
        return True

    # 插件自定义文件夹过滤器,True:处理,False:跳过
    def dir_filter(self, input_dir) -> bool:
        return True
