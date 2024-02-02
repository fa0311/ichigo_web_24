# -*- coding: utf-8 -*-

import logging
from logger import Logger
import time
from ichigo_websocket import IchigoWebsocket
from loadcell import LoadCell

if __name__ == "__main__":

    logger = Logger(
        log_dir="/home/user/ichigo_web/ichigo_judge/log/", log_name="judge", log_level=logging.INFO, console=True
    )
    
    # 仮想シリアルポート(/dev/pts/4)経由でデバイスからデータを読み取る
    #loadcell = LoadCell(logger, port="/dev/pts/4")

    # 物理シリアルポート(/dev/ttyUSB0)経由でデバイスからデータを読み取る
    loadcell = LoadCell(logger, port="/dev/ttyUSB0")

    websocket = IchigoWebsocket(logger,
                                url="http://127.0.0.1:8000",
                                params_fname="./data/params.json",
                                weight_corrects_fname="./data/weight_corrects.json")

    while True:
        try:
            # 重量センサ向けパラメータ更新
            loadcell.update_params(params=websocket.parameters, weight_corrects=websocket.weight_corrects)

            # 画像認識結果取得
            class_id = websocket.ichigo_class_id

            # クラスID確認用
            # print(websocket.ichigo_class_id)

            class_values = websocket.ichigo_class_values
            ### class_id:{0:"円錐果", 1:"歪み果", 2:"平らA", 3:"平ら秀"}
            class_names = ["","ドルチェ", "秀品", "A品", "B品","C品"]

            # 重量データ取得
            # weight_raw = loadcell.weight_raw  # 生データ
            weight_mean = loadcell.weight_mean  # スムージング済
            weight = loadcell.weight  # 補正済

            rank_names = ["不明", f"{class_id}"]
            speech = "不明です"

            #  形と重さによる条件分岐部分
            # -------------------------------------------------------------------
            # 秀品
            if (
                # weight >= 20 
                class_id == 2
            ):
                rank_names[0] = f"秀品"

                # S5 (52g以上)
                if 52 <= weight:
                    rank_names[1] = "S5"
                    speech = "しゅうひん、ごこづめ"
                # S6 (43g以上)
                elif 43 <= weight:
                    rank_names[1] = "S6"
                    speech = "しゅうひん、ろくこづめ"
                # S7 (36g以上)
                elif 36 <= weight:
                    rank_names[1] = "S7"
                    speech = "しゅうひん、ななこづめ"
                # S8 (31g以上)
                elif 31 <= weight:
                    rank_names[1] = "S8"
                    speech = "しゅうひん、はちこづめ"
                # S9 (28g以上)
                elif 28 <= weight:
                    rank_names[1] = "S9"
                    speech = "しゅうひん、きゅうこつめ"
                # S10 (25g以上)
                elif 25 <= weight:
                    rank_names[1] = "S10"
                    speech = "しゅうひん、じゅうこづめ"
                # S12 (20g以上)
                elif 20 <= weight:
                    rank_names[1] = "S12"
                    speech = "しゅうひん、じゅうにこづめ"
                # 規格外 S (19g以下)
                else:
                    rank_names[0] = f"規格外:秀"
                    rank_names[1] = "S"
                    speech = "きかくがい、しゅうひん"

            # -------------------------------------------------------------------
            # A品
            elif  class_id == 3 :

                rank_names[0] = f"A品"

                # A5 (52g以上)
                if 52 <= weight:
                    rank_names[1] = "A5"
                    speech = "えいひん、ごこづめ"
                # A6 (43g以上)
                elif 43 <= weight:
                    rank_names[1] = "A6"
                    speech = "えいひん、ろくこづめ"
                # A7 (36g以上)
                elif 36 <= weight:
                    rank_names[1] = "A7"
                    speech = "えいひん、ななこづめ"
                # A8 (31g以上)
                elif 31 <= weight:
                    rank_names[1] = "A8"
                    speech = "えいひん、はちこづめ"
                # A9 (28g以上)
                elif 28 <= weight:
                    rank_names[1] = "A9"
                    speech = "えいひん、きゅうこづめ"
                # A10 (25g以上)
                elif 25 <= weight:
                    rank_names[1] = "A10"
                    speech = "えいひん、じゅうこづめ"
                # A12 (20g以上)
                elif 20 <= weight:
                    rank_names[1] = "A12"
                    speech = "えいひん、じゅうにこづめ"
                # A品 (19g以下)
                else:
                    rank_names[0] = f"規格外:A"
                    rank_names[1] = "A"
                    speech = "きかくがい、えいひん"

            
            # -------------------------------------------------------------------
            # ドルチェ/B品
            elif class_id == 1 :

                # D5 (52g以上)
                if 52 <= weight:
                    rank_names[0] = "ドルチェ"
                    rank_names[1] = "D5"
                    speech = "ドルチェ、ごこづめ"
                # D6 (43g以上)
                elif 43 <= weight:
                    rank_names[0] = "ドルチェ"
                    rank_names[1] = "D6"
                    speech = "ドルチェ、ろくこづめ"
                # D7 (36g以上)
                elif 36 <= weight:
                    rank_names[0] = "ドルチェ"
                    rank_names[1] = "D7"
                    speech = "ドルチェ、ななこづめ"
                # D (35g以下)
                else:
                    rank_names[0] = f"規格外:B"
                    rank_names[1] = "B"
                    speech = "きかくがい、びいひん"


            # -------------------------------------------------------------------
            elif class_id in (4,5) :
               
                rank_names[0] = f"規格外:D"
                rank_names[1] = "D"
                speech = "きかくがい、でいひん"

                                
            
            # -------------------------------------------------------------------

            
            # 最終結果送信
            websocket.pub_final_answer(class_id, class_values, class_names, weight_mean, weight, rank_names, speech)

        except Exception as e:
            logger.error(f"エラー発生（{e}）")
            break
        finally:
            time.sleep(0.1)

    loadcell.stop()
    websocket.stop()
    logger.stop()
