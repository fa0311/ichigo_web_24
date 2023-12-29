<script setup>
import { ref, watch, onMounted, onBeforeMount, onBeforeUnmount } from "vue";
import { io } from "socket.io-client";
import Cookies from "js-cookies";
import moment from "moment";
import PlaySound from "./playSound.js";

const max_class_num = 4;
var sum_class = ref(Array(max_class_num).fill(0));
// ※クラス名リストはサーバ側から配信されるので、ここでは仮設定とする
var class_names = ref(Array("0:円錐果", "1:歪み果", "2:平ら果", "3:平ら秀"));

const audio = PlaySound();
var playdt = moment();
var screen_clicked = false;
var startDialog_visible = ref(true);

const smoothing_rate_def = 0.95;
var smoothing_rate = ref(smoothing_rate_def);

const hold_sec_def = 3.0;
var hold_sec = ref(hold_sec_def);

const judge_th_def = 50;
var judge_th = ref(judge_th_def);

var weight_smoothing_rate = ref(0.0);
var loadcell_weight = ref(0);
var weight_correct_mode = ref(1);
var rank_names = ref(Array("", "？"));

// 重量データ補正関連: 正解重量データ格納用(入力2)
var right_weight_0 = ref(50);
var right_weight_1 = ref(100);

// 各種編集フラグ
var params_edit_flg = ref(false);
var weight_params_edit_flg = ref(false);

// 音声発話再生間隔
const key_speech_limit_sec = "ICHIGO-WEB_speech_limit_sec";
var speech_limit_sec_bk = Cookies.getItem(key_speech_limit_sec);
var speech_limit_sec = ref(
  speech_limit_sec_bk == undefined ? 3.0 : parseFloat(speech_limit_sec_bk)
);

// 音声発話高さ
const key_speech_pitch = "ICHIGO-WEB_speech_pitch";
var speech_pitch_bk = Cookies.getItem(key_speech_pitch);
var speech_pitch = ref(
  speech_pitch_bk == undefined ? 1.0 : parseFloat(speech_pitch_bk)
);

// 音声発話速度
const key_speech_speed = "ICHIGO-WEB_speech_speed";
var speech_speed_bk = Cookies.getItem(key_speech_speed);
var speech_speed = ref(
  speech_speed_bk == undefined ? 1.0 : parseFloat(speech_speed_bk)
);

watch(smoothing_rate, () => {
  changeParameters();
});

watch(hold_sec, () => {
  changeParameters();
});

watch(judge_th, () => {
  changeParameters();
});

watch(weight_smoothing_rate, () => {
  changeParameters();
});

watch(speech_limit_sec, () => {
  Cookies.setItem(key_speech_limit_sec, speech_limit_sec.value);
});

watch(speech_pitch, () => {
  Cookies.setItem(key_speech_pitch, speech_pitch.value);
});

watch(speech_speed, () => {
  Cookies.setItem(key_speech_speed, speech_speed.value);
});

const socket = io({
  path: "/ichigo_websocket",
  transports: ["websocket", "polling"],
});

const setupWebsocketClient = () => {
  // 画像認識結果・重量データなどの各種データ受信
  socket.on("final_answer", (data) => {
    if (data != null) {
      // 認識結果（クラス別信頼度）
      if (data.class_values != undefined) {
        sum_class.value = data.class_values;
      }
      // 認識クラス名称リスト
      if (data.class_names != undefined) {
        class_names.value = data.class_names;
      }
      // 重量データ
      if (data.weight != undefined) {
        loadcell_weight.value = data.weight;
      } else {
        loadcell_weight.value = 0.0;
      }
      // 最終結果
      if (data.rank_names != undefined) {
        rank_names.value = data.rank_names;
      }
      // 音声合成
      if (data.speech != undefined && data.speech != "") {
        if (
          window.speechSynthesis.speaking == false &&
          1000 * speech_limit_sec.value < moment().diff(playdt)
        ) {
          playdt = moment();
          // 音声合成出力
          var utterance = new SpeechSynthesisUtterance(data.speech);
          utterance.lang = "ja-JP";
          utterance.localService = true;
          utterance.pitch = speech_pitch.value;
          utterance.rate = speech_speed.value;
          window.speechSynthesis.speak(utterance);
        }
      }
    }
  });

  // 各種パラメータ受信
  socket.on("change_parameters", (data) => {
    if (params_edit_flg.value == false) {
      smoothing_rate.value = data.smoothing_rate;
      hold_sec.value = data.hold_sec;
      judge_th.value = data.judge_th;
    }
    if (weight_params_edit_flg.value == false) {
      weight_smoothing_rate.value = data.weight_smoothing_rate;
      weight_correct_mode.value = parseInt(data.weight_correct_mode);

      if (data.right_weight_0 != undefined) {
        right_weight_0.value = parseFloat(data.right_weight_0);
      }
      if (data.right_weight_1 != undefined) {
        right_weight_1.value = parseFloat(data.right_weight_1);
      }
    }
  });
};

/**
 * 各種パラメータ送信
 */
const changeParameters = () => {
  if (params_edit_flg.value || weight_params_edit_flg.value) {
    var payload = {
      src: "CLIENT",
      smoothing_rate: smoothing_rate.value,
      hold_sec: hold_sec.value,
      judge_th: judge_th.value,
      weight_smoothing_rate: weight_smoothing_rate.value,
      weight_correct_mode: parseInt(weight_correct_mode.value),
    };
    socket.emit("change_parameters", payload);
  }
};

/**
 * 重量センサ補正情報送信
 * @param {*} index 補正値保存領域インデックス(0:補正1, 1:補正2)
 * @param {*} right_weight 正解重量データ(単位:グラム)
 */
const weightCorrection = (index, right_weight) => {
  var payload = {
    index: index,
    right_weight: right_weight,
  };
  socket.emit("weight_correction", payload);
};

const pubSystemCmd = (cmd) => {
  var payload = {
    cmd: cmd,
  };
  socket.emit("system_cmd", payload);
};

/**
 * 画面内をクリックした場合にコールバックされる
 */
var clickedScreen = () => {
  if (screen_clicked == false) {
    screen_clicked = true;
    audio.playSilent();
  }
};

/**
 * 各種パラメータ初期化
 */
var resetParams = () => {
  smoothing_rate.value = smoothing_rate_def;
  hold_sec.value = hold_sec_def;
  judge_th.value = judge_th_def;
};

/**
 * マウント時に呼出
 */
onMounted(() => {
  setupWebsocketClient();
});

/**
 * マウント前に呼出
 */
onBeforeMount(() => {
  window.addEventListener("click", clickedScreen);
});

/**
 * アンマウント前に呼出
 */
onBeforeUnmount(() => {
  window.removeEventListener("click", clickedScreen);
});
</script> 

<template>
  <div class="container">
    <el-button
      v-if="!params_edit_flg"
      type="success"
      size="small"
      style="width: 200px"
      @click="params_edit_flg = true"
      >画像認識 パラメータ編集</el-button
    >
    <el-button
      v-if="params_edit_flg"
      type="primary"
      size="small"
      style="width: 200px"
      @click="
        changeParameters();
        params_edit_flg = false;
      "
      >編集終了</el-button
    >
    <el-button
      v-if="params_edit_flg"
      type="warning"
      size="small"
      style="width: 200px"
      @click="resetParams()"
      >パラメータリセット</el-button
    >
    <el-button
      v-if="params_edit_flg"
      type="danger"
      size="small"
      style="width: 200px"
      @click="pubSystemCmd('RESTART_ICHIGO_JUDGE')"
      >いちご判定処理リスタート</el-button
    >

    <!-- 各種パラメータ変更スライダー表示部 -->
    <el-row :gutter="20">
      <el-col :span="8">
        <span>認識結果 スムージング係数：{{ smoothing_rate.toFixed(2) }}</span>
        <el-slider
          class="setting-slider"
          v-model="smoothing_rate"
          :disabled="!params_edit_flg"
          :min="0.0"
          :max="0.99"
          :step="0.01"
          :show-tooltip="true"
        />
      </el-col>
      <el-col :span="8">
        <span>認識結果 保持時間：{{ hold_sec.toFixed(1) }}秒</span>
        <el-slider
          class="setting-slider"
          v-model="hold_sec"
          :disabled="!params_edit_flg"
          :min="1"
          :max="30"
          :step="0.1"
          :show-tooltip="true"
        />
      </el-col>
      <el-col :span="8">
        <span>認識結果 確定しきい値：{{ judge_th }}%</span>
        <el-slider
          class="setting-slider"
          v-model="judge_th"
          :disabled="!params_edit_flg"
          :min="10"
          :max="100"
          :step="1"
          :show-tooltip="true"
        />
      </el-col>
    </el-row>

    <!-- 画像認識結果表示部 -->
    <div class="progress-container">
      <el-progress
        class="progress-class"
        v-for="(val, idx) in class_names"
        :key="idx"
        type="dashboard"
        :percentage="100 * sum_class[idx]"
      >
        <template #default="{ percentage }">
          <span class="progress-value">{{ Math.round(percentage) }}%</span>
          <span class="progress-label">{{ val }}</span>
        </template>
      </el-progress>
    </div>

    <br />

    <!-- 重量データ表示部 -->
    <div class="weight-container">
      <el-row :gutter="20" align="middle">
        <el-col :span="16">
          <h2 class="display-weight">{{ loadcell_weight.toFixed(1) }} g</h2>

          <el-row :gutter="20">
            <el-col :span="6">
              <el-button
                v-if="weight_params_edit_flg"
                type="danger"
                size="small"
                style="width: 100%; height: calc(100% - 20px)"
                @click="
                  changeParameters();
                  weight_params_edit_flg = false;
                "
                >編集終了</el-button
              >
              <el-button
                v-else
                type="success"
                size="small"
                style="
                  width: 100%;
                  height: calc(100% - 20px);
                  line-height: 18px;
                "
                @click="weight_params_edit_flg = true"
                >重量センサ<br />パラメータ編集</el-button
              >
            </el-col>
            <el-col :span="18">
              <span
                >重量データ スムージング係数：{{
                  weight_smoothing_rate.toFixed(2)
                }}</span
              >
              <el-slider
                class="setting-slider"
                v-model="weight_smoothing_rate"
                :disabled="!weight_params_edit_flg"
                :min="0.0"
                :max="0.5"
                :step="0.01"
                :show-tooltip="true"
              />
            </el-col>
          </el-row>
        </el-col>
        <el-col :span="8">
          <div v-if="!weight_params_edit_flg">
            <div v-if="weight_correct_mode == 0">
              <h2 class="weight-correct-modename">補正<br />オフ</h2>
            </div>
            <div v-else-if="weight_correct_mode == 1">
              <h2 class="weight-correct-modename">
                補正オン<br />（タイプ１）
              </h2>
            </div>
            <div v-else>
              <h2 class="weight-correct-modename">
                補正オン<br />（タイプ２）
              </h2>
            </div>
          </div>

          <div v-if="weight_params_edit_flg">
            <el-radio-group
              v-model="weight_correct_mode"
              size="small"
              :disabled="!weight_params_edit_flg"
              style="padding-bottom: 15px"
              @change="changeParameters()"
            >
              <el-radio-button label="0">補正<br />オフ</el-radio-button>
              <el-radio-button label="1"
                >補正オン<br />（タイプ1）</el-radio-button
              >
              <el-radio-button label="2"
                >補正オン<br />（タイプ2）</el-radio-button
              >
            </el-radio-group>

            <br />

            <el-button
              v-if="weight_correct_mode != 0"
              type="success"
              size="small"
              style="width: 100%; margin-bottom: 10px"
              @click="weightCorrection(0, right_weight_0)"
              >補正１データ登録</el-button
            >
            <div v-if="weight_correct_mode != 0">
              <span>正解重量入力１：{{ right_weight_0 }}グラム</span>
              <el-slider
                v-model="right_weight_0"
                style="width: 100%; margin-bottom: 10px"
                :min="1"
                :max="200"
                :step="1"
                show-input
              />
            </div>

            <br />

            <el-button
              type="warning"
              size="small"
              v-if="weight_correct_mode == 2"
              style="width: 100%"
              @click="weightCorrection(1, right_weight_1)"
              >補正２データ登録</el-button
            >
            <br />

            <div v-if="weight_correct_mode == 2">
              <span>正解重量入力２：{{ right_weight_1 }}グラム</span>
              <el-slider
                v-model="right_weight_1"
                style="width: 100%; margin-bottom: 10px"
                :min="1"
                :max="200"
                :step="1"
                show-input
              />
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 最終結果表示部 -->
    <div class="answer-container">
      <el-row :gutter="20" align="middle">
        <el-col :span="16" align="center">
          <div class="answer1">{{ rank_names[0] }}</div>
        </el-col>
        <el-col :span="8" align="left">
          <div class="answer2">{{ rank_names[1] }}</div>
        </el-col>
      </el-row>

      <div class="tts-slider">
        <el-row :gutter="20">
          <el-col :span="8">
            <span>発話間隔：{{ speech_limit_sec.toFixed(1) }}秒</span>
            <el-slider
              class="setting-slider"
              v-model="speech_limit_sec"
              :min="0.1"
              :max="10"
              :step="0.1"
              :show-tooltip="true"
            />
          </el-col>
          <el-col :span="8">
            <span>発話音程：{{ speech_pitch.toFixed(1) }}</span>
            <el-slider
              class="setting-slider"
              v-model="speech_pitch"
              :min="0.1"
              :max="3.0"
              :step="0.1"
              :show-tooltip="true"
            />
          </el-col>
          <el-col :span="8">
            <span>発話速度：{{ speech_speed.toFixed(1) }}</span>
            <el-slider
              class="setting-slider"
              v-model="speech_speed"
              :min="0.1"
              :max="3.0"
              :step="0.1"
              :show-tooltip="true"
            />
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- 初回表示時ダイアログ設定 -->
    <el-dialog v-model="startDialog_visible" title="確認" width="70%">
      <span>実行開始します</span>
      <template #footer>
        <el-button
          type="primary"
          style="width: 100%"
          @click="startDialog_visible = false"
          >OK</el-button
        >
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.container {
  position: relative;
  padding: 20px;
  margin: auto;
  width: 100%;
}

.setting-slider {
  display: inline-block;
  width: 100%;
  margin: 0;
  padding: 0;
}

.progress-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px 0 20px;
  border-radius: 10px;
  background: rgb(193, 255, 193);
}

.progress-class {
  display: inline-block;
  padding: 0;
  margin: 0;
}

.progress-value {
  display: block;
}
.progress-label {
  display: block;
  margin-top: 10px;
}

.weight-container {
  align-items: center;
  justify-content: space-between;
  padding: 10px 20px 0 20px;
  border-radius: 10px;
  background: rgb(236, 255, 193);
  color: rgb(65, 65, 65);
}

.display-weight {
  font-size: 4vw;
  text-align: right;
  padding-right: 25vw;
  vertical-align: middle;
  width: 100%;
}

.weight-correct-modename {
  text-align: center;
  border-radius: 5px;
  border: 1px solid rgb(168, 168, 168); /* 1pxの太さの実線で、色は黒 */
}

.answer-container {
  align-items: center;
  justify-content: space-between;
  text-align: center;
  vertical-align: middle;
  margin: 20px 0 0 0;
  padding: 20px 20px 0 20px;
  border-radius: 10px;
  background: rgb(255, 246, 193);
  color: rgb(65, 65, 65);
}

.answer1 {
  font-size: 4vw;
  vertical-align: middle;
  line-height: 100px;
}

.answer2 {
  font-size: 5vw;
  text-align: center;
  vertical-align: middle;
  margin: 0;
  padding: 5px 50px 10px 50px;
  border-radius: 5px;
  border: 1px solid rgb(168, 168, 168);
  width: 100%;
  line-height: 100px;
}

.tts-slider {
  text-align: left;
  vertical-align: middle;
  margin: 10px 0 0 0;
  padding: 0;
}
</style>
