import os
import logging
import docker
from typing import Optional
from video_processor import VideoProcessor


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class VideoCompressor(VideoProcessor):

    def __init__(self, delete_source: Optional[bool] = False, crf_value: Optional[int] = 23):
        self.delete_source = delete_source
        self.crf_value = crf_value
        self.client = docker.from_env()

    def filter(self, input_path) -> bool:
        file_name = os.path.basename(input_path)
        return True

    def process(self, input_path: str, output_path: str) -> None:
        logging.info(f'Compressing video: {input_path}')

        try:
            self.compress_video(input_path, output_path)
            logging.info(f'Video compressed successfully: {output_path}, self.delete_source={self.delete_source}')

            '''
            if self.delete_source:
                os.remove(input_path)
                logging.info(f'Source video deleted: {input_path}')
            '''

        except Exception as e:
            logging.error(f'Error compressing video: {input_path}, error: {e}')

    def configure(self, config: dict) -> None:
        self.delete_source = config.get('delete_source', False)
        self.crf_value = config.get('crf_value', 23)

    def compress_video(self, input_path: str, output_path: str) -> None:
        # 使用CRF值进行压缩，越小画质越好，范围0-51
        output_name = 'OUT_' + os.path.basename(output_path)

        cmd = f"-i {input_path} -c:v libx265 -preset veryslow -crf {self.crf_value} -c:a copy {output_name}"

        logging.info(f'input_path={input_path}, output_path={output_path}, '
                     f'crf_value={self.crf_value}, delete_source={self.delete_source},'
                     f'dir_input_path={os.path.dirname(input_path)}, cmd={cmd}')

        container = self.client.containers.run(
            "jrottenberg/ffmpeg",
            command=cmd,
            volumes={
                os.path.dirname(input_path): {'bind': os.path.dirname(input_path), 'mode': 'rw'},
            },
            working_dir=os.path.dirname(input_path),
            remove=True,
            detach=True
        )

        container.wait()
