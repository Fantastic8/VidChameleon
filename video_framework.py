import os
import mimetypes
import logging
from example_plugin import ExamplePlugin
from video_compressor import VideoCompressor
from video_processor import VideoProcessor
from bili_uploader import BiliUploader
from configparser import ConfigParser
import argparse
import json

# 错误处理与日志记录 (优化3)
# logger 配置
logger_file = '/var/services/homes/fantasticmark/scripts/VidChameleon/logger.log'
logging.basicConfig(filename=logger_file, level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# pid 文件名
pid_file_name = 'vid.pid'


class PluginManager:

    def __init__(self):
        self.plugins = {
            'example_plugin': ExamplePlugin(),
            'video_compressor': VideoCompressor(),
            'biliup': BiliUploader(),
        }

    def run(self, plugin_name: str, input_folder: str, output_folder: str) -> None:
        if plugin_name not in self.plugins:
            logger.error("插件未找到: %s", plugin_name)
            return

        plugin: VideoProcessor = self.plugins[plugin_name]

        for root, dirs, files in os.walk(input_folder):
            # 逆序,最新文件夹开始
            dirs.sort(reverse=True)
            '''
            遍历文件夹
            '''
            if plugin.dir_filter(root):
                logging.info('[Vid]开始处理目标文件夹: ' + root)
                try:
                    for file in files:
                        input_path = os.path.join(root, file)
                        if not is_video_file(input_path):
                            continue

                        self.process_video(plugin, input_path, output_folder)
                except Exception as e:
                    logging.error('[Vid]异常', e)
                    logging.info('[Vid]结束处理目标文件夹:' + root)
        logging.info('[Vid]结束运行')

    def process_video(self, plugin: VideoProcessor, input_path: str, output_dir: str) -> None:
        try:
            if plugin.file_filter(input_path):
                plugin.process(input_path, output_dir)
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


def idempotent_check(plugin_name: str):
    """
    程序pid检查,防止程序多开
    根据plugin name进行检查
    :return:
    """
    pids = {}
    if os.path.exists(pid_file_name):
        with open(pid_file_name, 'r') as pid_file:
            lines = pid_file.read()
        try:
            pids = json.loads(lines)
            pid = pids[plugin_name]
            os.kill(int(pid), 0)
            logging.error(f"插件 {plugin_name} 已在运行,pid=" + pid)
            return False
        except Exception as e:
            pass

    with open(pid_file_name, 'w') as pid_file:
        pids[plugin_name] = str(os.getpid())
        pid_file.writelines(json.dumps(pids))

    return True


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

    if idempotent_check(plugin_name):
        plugin_manager.run(plugin_name, input_folder, output_folder)


if __name__ == "__main__":
    main()
