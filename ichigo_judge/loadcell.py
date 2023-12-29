import serial
import threading
import time


class LoadCell:
    def __init__(self, logger, port="/dev/ttyACM0", baud_rate=115200, timeout_sec=1):
        self.__logger = logger
        self.__ser: serial.Serial = None
        self.__port: int = port
        self.__baud_rate: int = baud_rate
        self.__timeout_sec: int = timeout_sec

        self.__weight: float = 0.0
        self.__weight_raw: float = 0.0
        self.__weight_mean: float = 0.0

        self.__smoothing_rate: float = 0.95
        self.__weight_correct_mode: int = 0

        self.__wx: list = [0.0]*2
        self.__wy: list = [0.0]*2

        self.__lock = threading.Lock()

        self.__th_active_flg: bool = False
        self.__th = threading.Thread(target=self.__update_thread, args=())
        self.__th.daemon = True
        self.__th.start()

    def __del__(self):
        self.stop()

    @property
    def weight_raw(self) -> float:
        '''重量データ（生値）（単位：グラム）'''
        with self.__lock:
            return self.__weight_raw

    @property
    def weight_mean(self) -> float:
        '''重量データ（スムージング処理後）（単位：グラム）'''
        with self.__lock:
            return self.__weight_mean

    @property
    def weight(self) -> float:
        '''補正済み重量データ（単位：グラム）'''
        with self.__lock:
            return self.__weight

    def reset(self):
        '''各種変数初期化'''
        with self.__lock:
            self.__weight = 0.0
            self.__weight_raw = 0.0
            self.__weight_mean = 0.0

    def stop(self):
        '''インスタンス停止処理'''
        self.__th_active_flg = False
        if self.__th is not None:
            self.__th.join()
            self.__th = None
        self.__disconnect()

    def update_params(self, params, weight_corrects):
        '''各種パラメータ更新'''
        with self.__lock:
            # スムージング係数 (0.0～0.99)
            if 'weight_smoothing_rate' in params:
                self.__smoothing_rate = float(params['weight_smoothing_rate'])
            # 補正モード（0:補正無し, 1:補正1のみ, 2:補正1&2）
            if 'weight_correct_mode' in params:
                self.__weight_correct_mode = int(params['weight_correct_mode'])

            for index in range(2):
                if f'weight_{index}' in weight_corrects:
                    self.__wx[index] = float(
                        weight_corrects[f'weight_{index}'])
                if f'right_weight_{index}' in weight_corrects:
                    self.__wy[index] = float(
                        weight_corrects[f'right_weight_{index}'])

    def __connect(self):
        '''シリアル接続'''
        try:
            self.__disconnect()
            self.__ser = serial.Serial(
                self.__port, self.__baud_rate, timeout=self.__timeout_sec
            )
            self.__logger.info(
                f"loadcell.connect: 接続しました port=[{self.__port}]")
        except serial.SerialException as e:
            self.__logger.error(f"loadcell.connect: 接続エラー発生 {e}")

    def __disconnect(self):
        '''シリアル切断'''
        try:
            if self.__ser:
                self.__ser.close()
                self.__logger.info(f"loadcell: 切断しました。port=[{self.__port}]")
        except serial.SerialException as e:
            self.__logger.error(f"loadcell.close: 切断時エラー発生 {e}")
        finally:
            self.__ser = None
            self.reset()

    def __parse_weight(self, weight_str) -> float:
        '''重量データ取得（重量データ文字列をfloat型へ変換する）'''
        try:
            return float(weight_str)
        except ValueError:
            # 変換できない場合は0を返す
            return 0.0

    def __weight_hosei(self, input_x) -> float:
        '''重量データ補正処理'''
        # 補正モード1 設定時
        if self.__weight_correct_mode == 1 and 1 <= len(self.__wx) and 1 <= len(self.__wy):
            # (x1,y1)のうち, x1がゼロの場合, (0,y1)の1点のみで補正処理を行う
            if self.__wx[0] == 0:
                output_y = self.__wy[0] + input_x
            else:
                # 原点(0,0)と(x1,y1)の2点での補正処理
                x1 = 0.0
                y1 = 0.0
                x2 = self.__wx[0]
                y2 = self.__wy[0]
                output_y = (y2 - y1) / (x2 - x1) * (input_x - x1) + y1
        # 補正モード2 設定時
        elif self.__weight_correct_mode == 2 and 2 <= len(self.__wx) and 2 <= len(self.__wy):
            if (
                input_x <= self.__wx[0]
                # (x1,y1)と(x2,y2)の２座標のうち, x1とx2が同じ値の場合, 原点(0,0)と(x1,y1)の2点のみで補正処理を行う
                or self.__wx[0] == self.__wx[1]
            ):
                # 原点(0,0)と(x1,y1)の2点での補正処理
                x1 = 0.0
                y1 = 0.0
                x2 = self.__wx[0]
                y2 = self.__wy[0]
                output_y = (y2 - y1) / (x2 - x1) * (input_x - x1) + y1
            else:
                # (x1, y1), (x2, y2)の2座標を用いて補正する
                x1 = self.__wx[0]
                y1 = self.__wy[0]
                x2 = self.__wx[1]
                y2 = self.__wy[1]
                output_y = (y2 - y1) / (x2 - x1) * (input_x - x1) + y1
        # 補正OFF設定時
        else:
            output_y = input_x
        return output_y

    def __update_thread(self):
        '''重量データ取得スレッド（シリアル通信により逐次最新の重量データを取得する）'''
        self.__th_active_flg = True
        rcvdt = 0
        while self.__th_active_flg:
            try:
                if 3 < (time.time() - rcvdt):
                    self.__weight_raw = 0.0
                with self.__lock:
                    # スムージング
                    self.__weight_mean = self.__smoothing_rate * self.__weight_mean + \
                        (1.0 - self.__smoothing_rate) * self.__weight_raw
                    # 補正処理
                    self.__weight = self.__weight_hosei(self.__weight_mean)

                # シリアル通信正常時
                if self.__ser is not None and self.__ser.isOpen():
                    line = self.__ser.readline().decode("utf-8").strip()
                    if line:
                        rcvdt = time.time()
                        data = eval(line)
                        omosa = data.get("Omosa")
                        weight_class = data.get("class")
                        # print(f"omosa={omosa} class={weight_class}")
                        # 重量データ（生値）取得
                        self.__weight_raw = self.__parse_weight(omosa)
                # シリアル通信異常時
                else:
                    # 再接続を行う
                    self.__connect()
                    time.sleep(1)
            except serial.SerialException as e:
                self.__logger.error(f"loadcell: シリアル通信エラー {e}")
                self.__disconnect()
                time.sleep(1)
            except Exception as e:
                self.__logger.error(f"loadcell: 例外発生 {e}")
                self.__disconnect()
                time.sleep(1)
        self.__logger.warn(f"loadcell: stopped update_thread")
