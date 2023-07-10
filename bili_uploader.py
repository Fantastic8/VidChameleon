import os
import re
import time
import shutil
import logging
from video_processor import VideoProcessor
from biliup.plugins.bili_webup import BiliBili, Data


class BiliUploader(VideoProcessor):

    # constants
    TAGS = 'tags'
    COVER = 'cover'

    # 预设 文件夹名出现的 标签
    preset = {
        '东赞': {
            TAGS: ['东赞', '杭州排球', '杭州'],
        },
        '新青牛': {
            TAGS: ['新青牛', '杭州排球', '杭州'],
        },
        '北宸': {
            TAGS: ['北宸', '杭州排球', '杭州'],
        },
        '青英': {
            TAGS: ['青英', '南京排球', '南京'],
        },
        '星辰': {
            TAGS: ['星辰', '上海排球', '上海'],
        },
        'uvcc': {
            TAGS: ['uvcc', '上海排球', '上海'],
        },
    }

    default_tags = ['排球', '野生排球', '日常训练']
    default_cover = '/var/services/video/volleyball/bilicover/default.jpg'

    def __init__(self, start_date: str = ''):
        # 指定输入文件夹格式
        self.input_dir_pattern = re.compile(r'\d{8}-.*$', re.I)
        #self.input_dir_pattern = re.compile(r'^1080$', re.I)
        # 指定输入文件格式
        self.input_file_pattern = re.compile(r'^COMP_SRC\d{4}', re.I)
        # 主目录格式检查
        self.main_dir_pattern = re.compile(r'\d{8}-.*$', re.I)

        self.start_date = start_date

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

    def configure(self, config: dict) -> None:
        self.start_date = config.get('start_date')

    def process(self, input_file: str, _output_dir: str) -> None:
        logging.info(f'[biliup] process video: {input_file}')
        input_dir_path = os.path.dirname(input_file)
        main_dir_name = os.path.basename(input_dir_path)
        """
        1. 拼接投稿文件名
        """
        if self.main_dir_pattern.match(main_dir_name) is None:
            # 如果不是 yyyymmdd-xxx 文件夹的话，默认开头为当天日期
            main_dir_name = time.strftime("%Y%m%d")
        # 文件名
        input_file_name = os.path.basename(input_file)
        input_file_name_no_ext, ext = os.path.splitext(input_file_name)
        # 获取文件编号
        input_file_suffix = input_file_name[8:12]

        if len(input_file_suffix) <= 0:
            # 默认文件名
            input_file_suffix = input_file_name

        # 拼接投稿文件名 - 文件夹名 + 文件编号
        output_file_name = main_dir_name + "-" + input_file_suffix
        output_file_path = os.path.join(input_dir_path, output_file_name) + ext

        """
        2. 构造标签，图像等其他属性
        """
        # 获取预设
        preset = self.get_preset_from_dir_name(main_dir_name)
        # 视频标签
        tags = self.gen_tags_from_preset(preset)
        # 视频封面
        cover = self.gen_cover_from_preset(preset)

        logging.info(f'[biliup] uploading video... src: {input_file}, '
                     f'dest: {output_file_path}, tags: {tags}, cover: {cover}')
        try:
            video = Data()
            video.title = output_file_name
            video.desc = '[AUTO_UPLOAD] ' + output_file_name
            #video.source = 'fantasticMark原创'
            # 1 为原创 2 为转载
            video.copyright = 1
            # 设置视频分区,21 日常
            video.tid = 21
            video.set_tag(tags)
            #video.dynamic = '动态内容'
            lines = 'AUTO'
            tasks = 3
            #dtime = 7200  # 延后时间，单位秒
            with BiliBili(video) as bili:
                # TODO:
                bili.login("bili.cookie", {
                    'cookies': {
                        'SESSDATA': 'c272c056%2C1703948970%2Ce5bc3a72',
                        'bili_jct': 'f6c39386983bc442616845c38a19789a',
                        'DedeUserID__ckMd5': '0ec07315c3a0fbd3',
                        'DedeUserID': '2055481360'
                    }, 'access_token': 'a250a607e47ef43599d154c56cbb0072'})
                video_part = bili.upload_file(input_file, lines=lines, tasks=tasks)  # 上传视频，默认线路AUTO自动选择，线程数量3。
                video.append(video_part)  # 添加已经上传的视频
                # video.delay_time(dtime)  # 设置延后发布（2小时~15天）
                video.cover = bili.cover_up(cover).replace('http:', '')
                ret = bili.submit()  # 提交视频
            # 4. 完成后置任务 - 修改文件名
            shutil.move(input_file, output_file_path)
            logging.info(f'[biliup] Video upload successfully... src: {input_file}, dest: {output_file_path}')
        except Exception as e:
            logging.error(f'[biliup] Error uploading video: {input_file}, error: {e}')

    def get_preset_from_dir_name(self, dir_name: str):
        """
        从文件夹名中获取预设配置
        :param dir_name:
        :return:
        """
        # 如果文件夹名满足 yyyymmdd-xxx 就把 xxx 加到 tag 里
        if self.main_dir_pattern.match(dir_name) is not None:
            for key in self.preset.keys():
                if dir_name.lower().find(key) != -1:
                    return self.preset[key]
        return None

    def gen_tags_from_preset(self, preset: dict):
        """
        从预设中获取标签
        :param preset:
        :return:
        """
        tags = set()

        # 如果 xxx 在预设 tags 里就把预设 tags 加进去
        if preset is not None:
            for tag in preset[self.TAGS]:
                tags.add(tag)

        # 添加默认 tag
        for tag in self.default_tags:
            tags.add(tag)

        return list(tags)

    def gen_cover_from_preset(self, preset: dict):
        """
        TODO: AI
        从预设中获取封面
        :param preset:
        :return:
        """
        if preset is not None and preset.__contains__(self.COVER):
            return preset[self.COVER]
        return self.default_cover
