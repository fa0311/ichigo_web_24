import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime


class Logger:
    def __del__(self):
        self.stop()

    def __init__(self, log_dir, log_name, log_level: int = logging.INFO, console=True):
        log_fname = "%s/%s_%s.log" % (
            log_dir,
            log_name,
            # datetime.now().strftime("%Y%m%d_%H%M%S"),
            datetime.now().strftime("%Y%m%d"),
        )
        self.logger = logging.getLogger(log_name)

        if log_level is None:
            log_level = logging.INFO
        self.logger.setLevel(log_level)

        if console:
            handler1 = logging.StreamHandler()
            handler1.setLevel(log_level)
            handler1.setFormatter(
                logging.Formatter(
                    "%(asctime)s.%(msecs)03d %(levelname)s %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            self.logger.addHandler(handler1)

        handler2 = TimedRotatingFileHandler(
            filename=log_fname,
            when="D",  # 日単位
            interval=30,  # 30日ごと
            backupCount=12,  # 保存するログファイルの数
            encoding="UTF-8",
        )
        handler2.setLevel(log_level)
        handler2.setFormatter(
            logging.Formatter(
                "%(asctime)s.%(msecs)03d,%(levelname)s,%(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        self.logger.addHandler(handler2)
        self.logger.propagate = False

    def stop(self):
        if self.logger is not None:
            self.warn("logger: stopped")
            handlers = self.logger.handlers[:]
            for handler in handlers:
                try:
                    self.logger.removeHandler(handler)
                    handler.close()
                except:
                    pass
            logging.shutdown()
            self.logger = None

    def debug(self, msg):
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.info(msg)

    def warn(self, msg):
        self.logger.warn(msg)

    def error(self, msg):
        self.logger.error(msg)
