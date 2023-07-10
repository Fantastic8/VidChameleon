import re
import os
import docker
import logging
import subprocess
import shutil
from typing import Optional
from video_processor import VideoProcessor


class VideoCompressor(VideoProcessor):

    # docker 别名
    docker_name = 'ffmpeg_compress'
    # 输出文件名前缀
    output_prefix = 'COMP_'
    # 编码别名
    codex_name = {'libx264': 'H264', 'libx265': 'HEVC'}

    def __init__(self, crf: Optional[int] = 23, mem_limit: Optional[int] = 512,
                 mem_swap_limit: Optional[int] = 10, preset: Optional[str] = 'veryslow',
                 lib: Optional[str] = 'libx264', start_date: str = '',
                 height: str = '', width: str = ''):
        # param init
        self.crf = crf
        self.mem_limit = mem_limit
        self.mem_swap_limit = mem_swap_limit
        self.preset = preset
        self.lib = lib
        self.start_date = start_date
        self.height = height
        self.width = width

        # env init
        self.input_dir_pattern = re.compile(r'\d{8}-.*$', re.I)
        self.input_file_pattern = re.compile(r'SRC\d{4}', re.I)

        self.client = docker.from_env()

    def dir_filter(self, input_dir) -> bool:
        """
        插件自定义文件夹过滤器,True:处理,False:跳过
        只处理 start_date 之后的文件夹
        :param input_dir:
        :return:
        """
        dir_name = os.path.basename(input_dir)
        return self.input_dir_pattern.match(dir_name) is not None \
            and (len(self.start_date) == 0
                 or (len(self.start_date) > 0 and dir_name[:9] >= self.start_date))

    def file_filter(self, input_file) -> bool:
        """
        插件自定义文件名过滤器,True:处理,False:跳过
        :param input_file:
        :return:
        """
        # 获取文件名
        file_name = os.path.basename(input_file)
        # 获取不带扩展名的文件名
        file_name, _ = os.path.splitext(file_name)
        return self.input_file_pattern.match(file_name) is not None

    def process(self, input_file: str, output_dir: str) -> None:
        logging.info(f'Compressing video: {input_file}')
        try:
            self.compress_video(os.path.abspath(input_file), output_dir)
            logging.info(f'Video compressed successfully:{os.path.dirname(os.path.abspath(input_file))}')
        except Exception as e:
            logging.error(f'Error compressing video: {input_file}, error: {e}')

    def configure(self, config: dict) -> None:
        self.crf = config.get('crf', 23)
        self.mem_limit = config.get('mem_limit', 512)
        self.mem_swap_limit = config.get('mem_swap_limit', 10)
        self.preset = config.get('preset', 'veryslow')
        self.lib = config.get('lib', 'libx264')
        self.start_date = config.get('start_date')
        self.height = config.get('height')
        self.width = config.get('width')

    def gen_output_file_name(self, input_file_name: str):
        """
        生成输出文件名(不包含路径)
        :param input_file_name:
        :return:
        """
        input_file_name_no_ext, ext = os.path.splitext(input_file_name)
        # 输出文件名格式: 前缀_原文件名_编码_尺寸
        output_name = f"{self.output_prefix}{input_file_name_no_ext}_{self.codex_name.get(self.lib, self.lib)}"

        if len(self.height) > 0 or len(self.width) > 0:
            output_name = f"{output_name}_{self.width if len(self.width) > 0 else ''}x" \
                          f"{self.height if len(self.height) > 0 else ''}"

        output_name = f"{output_name}{ext}"
        return output_name

    def compress_video(self, abs_input_file: str, output_path: str) -> None:
        """
        执行压缩
        :param abs_input_file: 输入文件(绝对路径)
        :param output_path: 输出地址
        :return:
        """
        # 输入文件名称
        input_file_name = os.path.basename(abs_input_file)
        # 输入文件路径(不含文件名)
        abs_input_path = os.path.dirname(abs_input_file)
        # 输出文件名(不含路径)
        output_file_name = self.gen_output_file_name(input_file_name)
        # 输出绝对路径
        abs_output_path = os.path.join(abs_input_path, output_path)
        if os.path.isabs(output_path):
            # 如果输出地址是绝对路径则使用绝对路径
            abs_output_path = output_path
        # 临时输出文件名(不含路径)
        temp_output_file_name = f"temp_{output_file_name}"

        # 临时输出文件
        temp_output_file = os.path.join(abs_input_path, temp_output_file_name)
        # 目标文件:
        # TODO:output_file = os.path.join(abs_output_path, output_file_name)
        output_src_file = os.path.join(abs_output_path, input_file_name)
        output_compress_file = os.path.join(abs_input_path, output_file_name)

        # 1. 检查文件存在
        # 1.1 检查是否有正在处理的文件
        if os.path.exists(temp_output_file):
            logging.info("[COMPRESS-PROC]output file is processing: " + str(output_file_name))
            return

        # 1.2 检查目标文件是否已存在
        if os.path.exists(output_src_file):
            logging.info("[COMPRESS-PROC]output file exists: " + str(output_file_name))
            return

        # 2. 组装压缩命令
        command = f"sudo docker run --rm --name {self.docker_name} " \
                  f"--memory={self.mem_limit}m --memory-swap={self.mem_swap_limit}g -v " \
                  f"{abs_input_path}:/data -w /data jrottenberg/ffmpeg -stats " \
                  f"-i {input_file_name}"

        # 2.1 分辨率
        if len(self.height) > 0 or len(self.width) > 0:
            command = command + f" -vf \"scale={self.width if len(self.width) > 0 else -1}:" \
                                f"{self.height if len(self.height) > 0 else -1}\""

        command = command + f" -c:v {self.lib} -preset {self.preset} -crf {self.crf}" \
                            f" -c:a copy {temp_output_file_name} -progress -"

        logging.info(f'[Compressor]Start... abs_input_file={abs_input_file},command=\"{command}\"')

        # 3. 执行压缩
        subprocess.run(command, shell=True, check=True, capture_output=True)

        # 4. 压缩完成后置任务 - 将文件名还原并将文件移动到指定目录
        if not os.path.exists(abs_output_path):
            os.mkdir(abs_output_path)

        # 将temp文件重命名为输出文件名
        shutil.move(temp_output_file, output_compress_file)
        # 将SRC文件移动到 src 文件夹中
        shutil.move(abs_input_file, output_src_file)

        """
        cmd = f"-i {input_file_name} -c:v {self.lib} -preset {self.preset} -crf {self.crf} " \
              f"-c:a copy {output_file_name}"
        logging.info(f'[Compressor]Start... abs_input_file={abs_input_file},cmd=\"{cmd}\"')

        container = self.client.containers.run(
            "jrottenberg/ffmpeg",
            name="GoproCompressor",
            command=cmd,
            volumes={
                abs_input_path: {'bind': abs_input_path, 'mode': 'rw'},
            },
            working_dir=abs_input_path,
            # 设置容器内存限制大小（单位：MB）
            mem_limit=f"{self.mem_limit}m",
            # 设置容器内存交换空间大小（单位：GB）
            memswap_limit=f"{self.mem_swap_limit}g",
            remove=True,
            detach=True
        )

        container.wait()
        """
