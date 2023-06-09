<script setup>
import { ref, watch, onMounted, onBeforeMount, onBeforeUnmount } from "vue";
import { io } from "socket.io-client";
import Cookies from "js-cookies";
import moment from "moment";
import PlaySound from "./playSound.js";

const max_class_num = 4;
var sum_class = ref(Array(max_class_num).fill(0));
var class_name = Array("0:円錐果", "1:歪み果", "2:平ら果", "3:平ら秀");
var timerId = null;
var disp_flg = ref(false);
var disp_result_name = ref("");
var prev_max_idx = null;
const audio = PlaySound();
var result_rcvdt = moment();
var playdt = moment();
var screen_clicked = false;
var startDialog_visible = ref(true);

const limit_sec_def = 3.0;
const key_limit_sec = "ICHIGO-WEB_limit_sec";
var limit_sec_bk = Cookies.getItem(key_limit_sec);
var limit_sec = ref(
  limit_sec_bk == null ? limit_sec_def : parseFloat(limit_sec_bk)
);

const smoothing_rate_def = 0.95;
const key_smoothing_rate = "ICHIGO-WEB_smoothing_rate";
var smoothing_rate_bk = Cookies.getItem(key_smoothing_rate);
var smoothing_rate = ref(
  smoothing_rate_def == null
    ? smoothing_rate_def
    : parseFloat(smoothing_rate_bk)
);

const hold_sec_def = 3.0;
const key_hold_sec = "ICHIGO-WEB_hold_sec";
var hold_sec_bk = Cookies.getItem(key_hold_sec);
var hold_sec = ref(
  hold_sec_bk == null ? hold_sec_def : parseFloat(hold_sec_bk)
);

const judge_th_def = 50;
const key_judge_th = "ICHIGO-WEB_judge_th";
var judge_th_bk = Cookies.getItem(key_judge_th);
var judge_th = ref(
  judge_th_def == null ? judge_th_def : parseFloat(judge_th_bk)
);

watch(limit_sec, () => {
  Cookies.setItem(key_limit_sec, limit_sec.value);
});

watch(smoothing_rate, () => {
  Cookies.setItem(key_smoothing_rate, smoothing_rate.value);
});

watch(hold_sec, () => {
  Cookies.setItem(key_hold_sec, hold_sec.value);
});

watch(judge_th, () => {
  Cookies.setItem(key_judge_th, judge_th.value);
});

const resetSum = () => {
  prev_max_idx = null;
  for (let idx = 0; idx < max_class_num; idx++) {
    sum_class.value[idx] = 0.0;
  }
  disp_result_name.value = "";
};

const judgeFunc = (result_class) => {
  try {
    result_rcvdt = moment();

    // 想定外結果の場合
    if (result_class < 0 || max_class_num <= result_class) {
      disp_result_name.value = "";

      // 全ての推定結果積算データを0方向へ縮小させる
      for (let idx = 0; idx < max_class_num; idx++) {
        sum_class.value[idx] = smoothing_rate.value * sum_class.value[idx];
      }
      return;
    }

    var max_val = 0.0;
    var max_idx = -1;
    for (let idx = 0; idx < max_class_num; idx++) {
      let val = idx == result_class ? 1.0 : 0.0;
      sum_class.value[idx] =
        smoothing_rate.value * sum_class.value[idx] +
        (1.0 - smoothing_rate.value) * val;

      if (max_val < sum_class.value[idx]) {
        max_val = sum_class.value[idx];
        max_idx = idx;
      }
    }

    // 最終しきい値を上回った場合, 音声発話を実行し, 結果を画面表示する
    if (judge_th.value <= 100 * max_val) {
      if (
        prev_max_idx == null || // 新たに結果が到来した場合
        (prev_max_idx != null && prev_max_idx != max_idx) || // 過去と結果が異なる場合, 直ちに発話許可する
        limit_sec.value < moment().diff(playdt) / 1000 // 発話間隔を超えた場合, 発話許可する
      ) {
        // 音声発話実行
        audio.playIchigoResult(max_idx);
        playdt = moment();
      }

      // 認識結果文字列を設定する
      if (0 <= max_idx && max_idx < class_name.length) {
        disp_result_name.value = class_name[max_idx];
      } else {
        disp_result_name.value = `${max_idx}：不明`;
      }

      prev_max_idx = max_idx;
    }
    // 最終しきい値を下回った場合, 結果非表示にする
    else {
      disp_result_name.value = "";
      prev_max_idx = null;
    }
  } catch (err) {
    console.error(err);
  }
};

const setupWebsocketClient = () => {
  const socket = io({
    path: "/ichigo_websocket",
  });
  socket.on("play_request", (data) => {
    if (startDialog_visible.value == false) {
      judgeFunc(data.class_id);
    }
  });
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
  limit_sec.value = limit_sec_def;
  smoothing_rate.value = smoothing_rate_def;
  hold_sec.value = hold_sec_def;
  judge_th.value = judge_th_def;
};

/**
 * マウント時に呼出
 */
onMounted(() => {
  setupWebsocketClient();

  timerId = setInterval(() => {
    let prev_disp_flg = disp_flg.value;

    // 推定結果受信からhold_sec秒未満の場合, 最新データが到来していると判断し, 推定結果を表示する
    if (moment().diff(result_rcvdt) < hold_sec.value * 1000) {
      disp_flg.value = true;
    }
    // 推定結果受信からhold_sec秒を超えた場合, 古いデータと判断し, 推定結果非表示とする
    else {
      disp_flg.value = false;

      // 非表示へと変化した場合, 積算データ配列を初期化する
      if (prev_disp_flg) {
        resetSum();
      }
    }
  }, 500);
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

  if (timerId != null) {
    clearInterval(timerId);
    timerId = null;
  }
});
</script> 

<template>
  <div class="container">
    <!-- パラメータリセットボタン表示 -->
    <el-button type="primary" size="small" @click="resetParams()"
      >パラメータリセット</el-button
    >

    <!-- 各種パラメータ変更スライダー表示部 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <span>発話間隔：{{ limit_sec.toFixed(1) }}秒</span>
        <el-slider
          class="setting-slider"
          v-model="limit_sec"
          :min="1"
          :max="10"
          :step="0.1"
          :show-tooltip="true"
        />
      </el-col>
      <el-col :span="12">
        <span>推定結果スムージング係数：{{ smoothing_rate.toFixed(2) }}</span>
        <el-slider
          class="setting-slider"
          v-model="smoothing_rate"
          :min="0.0"
          :max="1.0"
          :step="0.01"
          :show-tooltip="true"
        />
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col :span="12">
        <span>推定結果 保持時間：{{ hold_sec.toFixed(1) }}秒</span>
        <el-slider
          class="setting-slider"
          v-model="hold_sec"
          :min="1"
          :max="30"
          :step="0.1"
          :show-tooltip="true"
        />
      </el-col>
      <el-col :span="12">
        <span>推定結果表示しきい値：{{ judge_th }}%</span>
        <el-slider
          class="setting-slider"
          v-model="judge_th"
          :min="10"
          :max="100"
          :step="1"
          :show-tooltip="true"
        />
      </el-col>
    </el-row>

    <!-- 受信結果表示部 -->
    <div class="progress-container">
      <el-progress
        class="progress-class"
        v-for="(val, idx) in class_name"
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

    <!-- 最終結果表示部 -->
    <h1 v-if="disp_flg" class="display-result">{{ disp_result_name }}</h1>

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

.display-result {
  font-size: 120px;
  text-align: center;
  vertical-align: middle;
  width: 100%;
  height: 50vh;
  line-height: 50vh;
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
  /* font-size: 2vw; */
}
.progress-label {
  display: block;
  margin-top: 10px;
  /* font-size: 2vw; */
}
</style>
