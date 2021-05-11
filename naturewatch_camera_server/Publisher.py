from telegram.ext import Updater, CommandHandler
from subprocess import check_call
import logging
import threading
import os
import os.path

class Publisher():

    def __init__(self, config, logger=None):
        self.config = config

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging

        # The semaphore number sets how many publishing tasks to do at the same time.
        # Since FFmpeg is multi-threaded, there's no benefit in running more than one at the same time.
        # Also the high load can make the detection logic fail.
        # Increase it at your own risk.
        self.ffmpegSemaphore = threading.Semaphore(1)

        self.updater = Updater(self.config["telegram_api_key"])
        # dp = updater.dispatcher
        self.logger.info("Starting Telegram publisher")
        # dp.add_handler(CommandHandler('bop',bop))
        self.updater.start_polling()
        self.logger.info("Telegram publisher started")

    def doPublish(self, video_file_name, thumb_file_name):
        with self.ffmpegSemaphore:
            # The original video is 17-18MB big, too heavy to be easily shared.
            self.logger.info("Shrinking video for publishing: " + video_file_name)
            
            shrunk_file_name = video_file_name.replace(".mp4", "_shrunk.mp4")
            try:
                check_call(["ffmpeg", 
                    "-hide_banner",
                    "-nostats",
                    "-i", video_file_name, 
                    "-vf", "scale=960:540", 
                    "-crf" , "25", 
                    shrunk_file_name])

                with open(shrunk_file_name, 'rb') as video_file:
                    with open(thumb_file_name, 'rb') as thumbnail_file:
                        self.logger.info("sending video file")
                        self.updater.bot.send_video(
                            chat_id=self.config['telegram_chat_id'],
                            video=video_file,
                            thumb=thumbnail_file,
                            width=960,
                            height=540,
                            supports_streaming=True)
                        self.logger.info("send completed")
            finally:
                if os.path.isfile(shrunk_file_name):      
                    os.remove(shrunk_file_name)

    def publish_image(self, file_name):
        pass

    def publish_video(self, video_file_name, thumb_file_name):
        thread = threading.Thread(target=self.doPublish, args=(video_file_name, thumb_file_name))
        self.logger.info("Will publish using thread " + str(thread))
        thread.start()
