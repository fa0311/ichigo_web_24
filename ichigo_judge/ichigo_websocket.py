import socketio
import threading
import time
import json
import os


class IchigoRecog:
    '''画像認識結果処理クラス（スムージング処理などを行う）'''

    def __init__(self):
        self.__max_class_num: int = 4
        self.__sum_class = [0.0] * self.__max_class_num
        self.__class_id: int = -1
        self.__hold_sec: float = 0.0
        self.__updatedt: float = 0.0

    @property
    def class_id(self) -> int:
        if self.__hold_sec < (time.time() - self.__updatedt):
            # 受信データが古い場合, -1を返す
            return -1
        return self.__class_id

    @property
    def class_values(self) -> list:
        return self.__sum_class

    def reset(self):
        self.__class_id = -1
        for idx in range(self.__max_class_num):
            self.__sum_class[idx] = 0.0

    def update(self, result_class, params):
        '''
        いちご画像認識結果を更新する
        '''
        # 推定結果スムージング係数(0.0～0.99)
        smoothing_rate = 0.95
        if 'smoothing_rate' in params:
            smoothing_rate = float(params['smoothing_rate'])

        # 推定結果表示しきい値（0～100）
        judge_th = 50
        if 'judge_th' in params:
            judge_th = float(params['judge_th'])

        # 推定結果保持時間（秒）
        if 'hold_sec' in params:
            self.__hold_sec = float(params['hold_sec'])
        else:
            self.__hold_sec = 3.0

        # 前の受信日時が古い場合, リセットしておく
        if self.__hold_sec < (time.time() - self.__updatedt):
            self.reset()

        self.__updatedt = time.time()

        # 想定外結果の場合
        if result_class < 0 or self.__max_class_num <= result_class:
            # 全ての推定結果積算データを0方向へ縮小させる
            for idx in range(self.__max_class_num):
                self.__sum_class[idx] = smoothing_rate * self.__sum_class[idx]
            return

        # 最頻出の認識クラスIDを求める
        max_val = 0.0
        max_idx = -1
        for idx in range(self.__max_class_num):
            val = 1.0 if idx == result_class else 0.0
            self.__sum_class[idx] = smoothing_rate * \
                self.__sum_class[idx] + (1.0 - smoothing_rate) * val
            if max_val < self.__sum_class[idx]:
                max_val = self.__sum_class[idx]
                max_idx = idx

        # しきい値を上回った場合, 最終認識結果とする
        if judge_th <= 100 * max_val:
            self.__class_id = max_idx
        # 最終しきい値を下回った場合, 結果無しにする
        else:
            self.__class_id = -1


class IchigoWebsocket:
    def __init__(self, logger, url="http://127.0.0.1:8000", path="/ichigo_websocket", params_fname="./data/params.json", weight_corrects_fname="./data/weight_corrects.json"):
        self.__logger = logger
        self.__ws_url = url
        self.__ws_path = path
        self.__params_fname = params_fname
        self.__weight_corrects_fname = weight_corrects_fname
        self.__restart_reqdt: int = 0

        self.__params = dict()
        self.__load_params()

        self.__weight_corrects = dict()
        self.__load_weight_corrects()

        self.__current_weight: float = 0.0

        self.__ichigo_recog = IchigoRecog()

        # websocket関係
        self.__connected: bool = False
        self.__connect_retrydt: float = 0.0
        self.__sio = socketio.Client(logger=False, engineio_logger=False)
        self.__register_handlers()
        self.__connect()

        # 接続状態監視用スレッド生成
        self.__th_active_flg: bool = False
        self.__th = threading.Thread(target=self.__check_thread)
        self.__th.daemon = True
        self.__th.start()

    def __del__(self):
        self.stop()

    def stop(self):
        self.__th_active_flg = False
        if self.__th is not None:
            self.__th.join()
            self.__th = None

    @property
    def connected(self) -> bool:
        '''websocket接続状態'''
        return self.__connected

    @property
    def ichigo_class_id(self) -> int:
        '''画像認識結果(BestクラスID)'''
        if self.__connected == False:
            return -1
        return self.__ichigo_recog.class_id

    @property
    def ichigo_class_values(self) -> list:
        '''画像認識結果(クラス別認識結果)'''
        if self.__connected == False:
            return -1
        return self.__ichigo_recog.class_values

    @property
    def weight_corrects(self) -> dict:
        '''重量センサ補正情報'''
        return self.__weight_corrects

    @property
    def parameters(self) -> bool:
        return self.__params

    def pub_final_answer(self, class_id: int, class_values: list, class_names: list, weight_mean: float, weight: float, rank_names: list, speech: str) -> bool:
        '''最終結果配信'''
        try:
            payload = {
                "class_id": class_id,
                "class_values": class_values,
                "class_names": class_names,
                "weight": weight,
                "rank_names": rank_names,
                "speech": speech
            }
            self.__current_weight = weight_mean
            self.__sio.emit("final_answer", payload)
        except Exception as e:
            self.__logger.error(f"websocket.pub_final_answer: exception {e}")
        finally:
            if time.time() - self.__restart_reqdt < 5:
                # 再起動要求ありの場合, Falseを返す
                return False
            return True

    def __pub_params(self):
        '''各種パラメータ配信'''
        try:
            if self.__connected:
                params = self.__params.copy()
                params['src'] = "SERVER"
                for index in range(2):
                    params[f'right_weight_{index}'] = self.weight_corrects[f'right_weight_{index}']
                self.__sio.emit("change_parameters", params)
        except Exception as e:
            self.__logger.error(f"websocket.pub_params: exception {e}")

    def __reset_values(self):
        self.__connected = False

    def __register_handlers(self):
        @self.__sio.event
        def connect():
            '''websocket接続確立時'''
            self.__websocket_connected = True
            self.__logger.info("websocket.event: connected")
            self.__pub_params()

        @self.__sio.event
        def disconnect():
            '''websocket切断時'''
            self.__reset_values()
            self.__logger.info("websocket.event: disconnected")

        @self.__sio.event
        def play_request(data):
            '''画像認識結果到来時'''
            try:
                if data is not None and 'class_id' in data:
                    self.__ichigo_recog.update(
                        int(data['class_id']), self.__params)
            except Exception as e:
                self.__logger.error(
                    f"websocket.event: exception @ play_request: {e}")

        @self.__sio.event
        def change_parameters(data):
            '''各種パラメータ変更時'''
            try:
                # サーバ以外からのパラメータ配信データの場合のみ保存処理を行う
                if 'src' in data and data['src'] != "SERVER":
                    self.__params = data
                    self.__save_params()
            except Exception as e:
                self.__logger.error(
                    f"websocket.event: exception @ change_parameters: {e}")

        @self.__sio.event
        def weight_correction(data):
            '''重量データ補正値入力時'''
            try:
                self.__logger.info(
                    f"websocket.event: weight_correction received: {data}")
                correct_index = int(data['index'])  # 0:補正1(ゼロ補正), 1:補正2データ
                right_weight = float(data['right_weight'])

                self.__weight_corrects[f'weight_{correct_index}'] = self.__current_weight
                self.__weight_corrects[f'right_weight_{correct_index}'] = right_weight

                self.__save_weight_corrects()

            except Exception as e:
                self.__logger.error(
                    f"websocket.event: exception @ weight_correction: {e}")

        @self.__sio.event
        def system_cmd(data):
            '''システムコマンド受信'''
            try:
                if 'cmd' in data and data['cmd'] == "RESTART_ICHIGO_JUDGE":
                    self.__restart_reqdt = time.time()
            except Exception as e:
                self.__logger.error(
                    f"websocket.event: exception @ system_cmd: {e}")

    def __check_thread(self):
        '''websocket接続監視 & 各種パラメータ定期配信処理'''
        self.__th_active_flg = True
        while self.__th_active_flg:
            try:
                if self.__connected == False:
                    # 切断状態の場合, 再接続する (3秒間隔でリトライする)
                    if 3 < time.time() - self.__connect_retrydt:
                        self.__connect_retrydt = time.time()
                        self.__connect()
                else:
                    self.__pub_params()
            except Exception as e:
                self.__logger.error(f"exception @ loop: {e}")
            finally:
                time.sleep(0.5)

    def __connect(self):
        '''websocket接続'''
        try:
            self.__disconnect()
            self.__sio.connect(
                self.__ws_url,
                transports=["websocket", "polling"],
                socketio_path=self.__ws_path,
            )
            self.__connected = True
        except Exception as e:
            self.__logger.error(f"websocket.connect: exception {e}")
            self.__connected = False

    def __disconnect(self):
        '''websocket切断'''
        try:
            self.__sio.disconnect()
        except Exception as e:
            self.__logger.error(f"websocket.connect: exception {e}")
        finally:
            self.__reset_values()

    def __save_params(self):
        '''各種パラメータ保存（jsonファイル形式）'''
        try:
            with open(self.__params_fname, 'w') as file:
                json.dump(self.__params, file)
        except Exception as e:
            self.__logger.error(f"websocket.save_params: exception {e}")

    def __load_params(self):
        '''各種パラメータ取出（jsonファイルから）'''
        try:
            if os.path.exists(self.__params_fname):
                with open(self.__params_fname, 'r') as file:
                    self.__params = json.load(file)
            else:
                self.__params['smoothing_rate'] = 0.95
                self.__params['judge_th'] = 0.5
                self.__params['hold_sec'] = 3.0
                self.__params['limit_sec'] = 3.0
                self.__params['weight_smoothing_rate'] = 0.50
                self.__params['weight_correct_mode'] = 0
                self.__save_params()
        except Exception as e:
            self.__logger.error(f"websocket.load_params: exception {e}")

    def __save_weight_corrects(self):
        '''重量データ補正情報保存（jsonファイル形式）'''
        try:
            with open(self.__weight_corrects_fname, 'w') as file:
                json.dump(self.__weight_corrects, file)
        except Exception as e:
            self.__logger.error(
                f"websocket.save_weight_corrects: exception {e}")

    def __load_weight_corrects(self):
        '''重量データ補正情報取出（jsonファイルから）'''
        try:
            if os.path.exists(self.__weight_corrects_fname):
                with open(self.__weight_corrects_fname, 'r') as file:
                    self.__weight_corrects = json.load(file)
            else:
                for index in range(2):
                    self.__weight_corrects[f'weight_{index}'] = 0.0
                    self.__weight_corrects[f'right_weight_{index}'] = 0.0
                self.__save_weight_corrects()
        except Exception as e:
            self.__logger.error(
                f"websocket.load_weight_corrects: exception {e}")
