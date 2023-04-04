import os
import mimetypes
import logging
from example_plugin import ExamplePlugin
from video_compressor import VideoCompressor
from configparser import ConfigParser
import argparse

# 错误处理与日志记录 (优化3)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PluginManager:

    def __init__(self):
        self.plugins = {
            'example_plugin': ExamplePlugin(),
            'video_compressor': VideoCompressor(),
        }

    def process_video(self, plugin_name: str, input_path: str, output_path: str) -> None:
        if plugin_name not in self.plugins:
            logger.error("插件未找到: %s", plugin_name)
            return

        plugin = self.plugins[plugin_name]
        try:
            plugin.process(input_path, output_path)
        except Exception as e:
            logger.error("处理视频时出错: %s", str(e))


# 文件类型过滤 (优化5)
def is_video_file(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type is not None and mime_type.startswith('video')


# 命令行参数 (优化7)
def parse_arguments():
    parser = argparse.ArgumentParser(description="视频处理程序")
    parser.add_argument("input_folder", help="输入视频所在文件夹")
    parser.add_argument("output_folder", help="处理后视频的输出文件夹")
    parser.add_argument("plugin_name", help="要使用的处理插件名称")
    return parser.parse_args()


def main():
    args = parse_arguments()
    input_folder = args.input_folder
    output_folder = args.output_folder
    plugin_name = args.plugin_name

    # 配置文件 (优化4)
    config = ConfigParser()
    config.read('config.ini')

    plugin_manager = PluginManager()

    # 为插件应用配置 (优化9)
    if plugin_name in config:
        plugin_manager.plugins[plugin_name].configure(config[plugin_name])

    for video_file in os.listdir(input_folder):
        input_path = os.path.join(input_folder, video_file)
        if not is_video_file(input_path):  # 文件类型过滤 (优化5)
            continue

        output_path = os.path.join(output_folder, video_file)
        plugin_manager.process_video(plugin_name, input_path, output_path)


if __name__ == "__main__":
    main()
