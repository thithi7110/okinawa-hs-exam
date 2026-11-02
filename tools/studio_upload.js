// YouTube Studio のアップロード画面（.../videos/upload?d=ud）で javascript_tool から実行する。
// latest ブランチの video.mp4 をファイル欄にセットし、タイトルと概要欄を入れる。
(async () => {
  const base = 'https://raw.githubusercontent.com/thithi7110/okinawa-hs-exam/latest/';
  const get = p => fetch(base + p, {cache: 'no-store'});
  const blob = await (await get('video.mp4')).blob();
  const date = (await (await get('DATE')).text()).trim();
  const inp = document.querySelector('input[type=file][name=Filedata]');
  if (!inp) return 'NO_FILE_INPUT';
  const dt = new DataTransfer(); dt.items.add(new File([blob], `rika-ichimon-${date}.mp4`, {type: 'video/mp4'}));
  inp.files = dt.files; inp.dispatchEvent(new Event('change', {bubbles: true}));
  for (let i = 0; i < 40; i++) {           // ダイアログの入力欄が出るまで待つ
    await new Promise(r => setTimeout(r, 500));
    const boxes = [...document.querySelectorAll('ytcp-uploads-dialog #textbox[contenteditable=true]')];
    if (boxes.length >= 2) {
      const [title, desc] = await Promise.all(['title.txt', 'desc.txt'].map(p => get(p).then(r => r.text())));
      const set = (el, t) => { el.focus(); document.execCommand('selectAll'); document.execCommand('insertText', false, t.trim()); el.blur(); };
      set(boxes[0], title); set(boxes[1], desc);
      return `OK size=${blob.size} title=${boxes[0].innerText.length} desc=${boxes[1].innerText.length}`;
    }
  }
  return 'DIALOG_TIMEOUT';
})()
