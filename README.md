# okinawa-hs-exam

沖縄県立高校入試（2027年3月3日）に向けた「理科 一問一答」動画を毎朝つくってYouTubeに上げるための置き場です。

- `tools/setup.sh` … VOICEVOX・Playwright・ffmpeg の準備
- `tools/build_quiz.py` … quiz.json から動画・タイトル・概要欄を作る（形式は冒頭コメント）
- `tools/studio_upload.js` … YouTube Studio のアップロード画面で実行し、`latest` ブランチの動画をセットする
- `rika/curriculum.json` … 単元のローテーション（中1〜中3・28単元）
- `rika/history/YYYY-MM-DD.json` … 出題済みの quiz.json（重複防止と復習問題の選定に使う）
- `latest` ブランチ … 当日の動画1本だけ（毎朝上書き）
