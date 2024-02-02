import wav_silent from "@/assets/sound/silent.wav";
import class_0 from "@/assets/sound/class_0.wav";
import class_1 from "@/assets/sound/class_1.wav";
import class_2 from "@/assets/sound/class_2.wav";
import class_3 from "@/assets/sound/class_3.wav";

export default function () {
  var audioObj = null;

  function playSound(path) {
    try {
      var playSoundFunc = () => {
        if (audioObj != null) {
          audioObj.play();
        }
      };
      // 既に何らか再生している場合, 再生停止する
      if (audioObj != null) {
        audioObj.pause();
        audioObj.currentTime = 0;
        audioObj.removeEventListener('loadeddata', playSoundFunc);
        audioObj = null;
      }
      // 再生実行
      audioObj = new Audio(path);
      audioObj.addEventListener('loadeddata', playSoundFunc);
      audioObj.load();
    } catch (err) {
      console.error(err);
    }
  }

  // 無音再生実行
  var playSilent = () => {
    playSound(wav_silent);
  }

  // 推定結果音声発話実行
  var playIchigoResult = (class_id) => {
    if (class_id == 0) {
      playSound(class_0);
    } else if (class_id == 1) {
      playSound(class_1);
    } else if (class_id == 2) {
      playSound(class_2);
    } else if (class_id == 3) {
      playSound(class_3);
    }
  };

  return { playSilent, playIchigoResult };
}
