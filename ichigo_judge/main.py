import logging
from logger import Logger
import time
from ichigo_websocket import IchigoWebsocket
from loadcell import LoadCell

if __name__ == "__main__":

    logger = Logger(
        log_dir="./log/", log_name="judge", log_level=logging.INFO, console=True
    )

    loadcell = LoadCell(logger)

    websocket = IchigoWebsocket(logger,
                                url="http://127.0.0.1:8000",
                                params_fname="./data/params.json",
                                weight_corrects_fname="./data/weight_corrects.json")

    while True:
        try:
            # 重量センサ向けパラメータ更新
            loadcell.update_params(
                params=websocket.parameters, weight_corrects=websocket.weight_corrects)

            # 画像認識結果取得
            class_id = websocket.ichigo_class_id
            class_values = websocket.ichigo_class_values
            class_names = ["円錐果", "歪み果", "平ら果", "平ら秀"]
            class_delay_sec = websocket.ichigo_class_delay_sec  # 最新認識結果受信からの経過時間（3秒以上であれば、データ無しと判断する）

            # 重量データ取得
            # weight_raw = loadcell.weight_raw  # 生データ
            weight_mean = loadcell.weight_mean  # スムージング済
            weight = loadcell.weight  # 補正済
            weight_delay_sec = loadcell.delay_sec  # 最新重量データ受信からの経過時間（3秒以上であれば、データ無しと判断する）

            rank_names = ["", f"？"]
            speech = ""

            # -------------------------------------------------------------------
            # 270g 大玉平PK 秀品：円錐果, 平ら果
            if (
                class_id == 0  # 円錐果
                or class_id == 3  # 平ら秀
            ):
                rank_names[0] = f"秀品：{class_names[class_id]}"

                # S5 (52g以上)
                if 52 <= weight:
                    rank_names[1] = "S5"
                    speech = "えす、ごう"
                # S6 (43g以上)
                elif 43 <= weight:
                    rank_names[1] = "S6"
                    speech = "えす、ろく"
                # S7 (36g以上)
                elif 36 <= weight:
                    rank_names[1] = "S7"
                    speech = "えす、なな"
                # S8 (31g以上)
                elif 31 <= weight:
                    rank_names[1] = "S8"
                    speech = "えす、はち"
                # S9 (28g以上)
                elif 28 <= weight:
                    rank_names[1] = "S9"
                    speech = "えす、きゅう"
                # S10 (25g以上)
                elif 25 <= weight:
                    rank_names[1] = "S10"
                    speech = "えす、じゅう"
                # S12 (20g以上)
                elif 20 <= weight:
                    rank_names[1] = "S12"
                    speech = "えす、じゅうに"
                # 規格外 S (19g以下)
                else:
                    rank_names[0] = f"規格外：{class_names[class_id]}"
                    rank_names[1] = "S"
                    speech = "えす"

            # -------------------------------------------------------------------
            # 270g 大玉平PK A品: 平ら果
            elif class_id == 2:  # 平ら果
                rank_names[0] = f"A品：{class_names[class_id]}"

                # A5 (52g以上)
                if 52 <= weight:
                    rank_names[1] = "A5"
                    speech = "えい、ごう"
                # A6 (43g以上)
                elif 43 <= weight:
                    rank_names[1] = "A6"
                    speech = "えい、ろく"
                # A7 (36g以上)
                elif 36 <= weight:
                    rank_names[1] = "A7"
                    speech = "えい、なな"
                # A8 (31g以上)
                elif 31 <= weight:
                    rank_names[1] = "A8"
                    speech = "えい、はち"
                # A9 (28g以上)
                elif 28 <= weight:
                    rank_names[1] = "A9"
                    speech = "えい、きゅう"
                # A10 (25g以上)
                elif 25 <= weight:
                    rank_names[1] = "A10"
                    speech = "えい、じゅう"
                # A12 (20g以上)
                elif 20 <= weight:
                    rank_names[1] = "A12"
                    speech = "えい、じゅうに"
                # A品 (19g以下)
                else:
                    rank_names[0] = f"A品：{class_names[class_id]}"
                    rank_names[1] = "A"
                    speech = "えい"

            # -------------------------------------------------------------------
            # 歪み果
            elif class_id == 1:  # 歪み果
                # D5 (52g以上)
                if 52 <= weight:
                    rank_names[0] = "ドルチェ"
                    rank_names[1] = "D5"
                    speech = "ドルチェ、でい、ごう"
                # D6 (43g以上)
                elif 43 <= weight:
                    rank_names[0] = "ドルチェ"
                    rank_names[1] = "D6"
                    speech = "ドルチェ、でい、ろく"
                # D7 (36g以上)
                elif 36 <= weight:
                    rank_names[0] = "ドルチェ"
                    rank_names[1] = "D7"
                    speech = "ドルチェ、でい、なな"
                # D (35g以下)
                else:
                    rank_names[0] = f"B品：{class_names[class_id]}"
                    rank_names[1] = "D"
                    speech = "びーひん、でいー"

            # 最終結果送信
            if websocket.pub_final_answer(class_id, class_values, class_names, weight_mean, weight, rank_names, speech) == False:
                logger.warn("main: received restart request")
                break

        except Exception as e:
            logger.error(f"エラー発生（{e}）")
            break
        finally:
            time.sleep(0.1)

    loadcell.stop()
    websocket.stop()
    logger.stop()
