// BiliBili Subtitle Downloader — 浏览器 Console 运行
// 用法: 打开 B 站视频页面 → F12 → Console → 粘贴全部代码 → Enter
// 输出: 每个分P下载一个 raw JSON 文件
(async () => {
  const state = window.__INITIAL_STATE__ || {};
  const videoData = state.videoData || {};
  const pages = videoData.pages || [];

  if (!pages.length) {
    console.error("[!] 未检测到分P列表。请在 B 站视频页面运行此脚本。");
    return;
  }

  console.log(`检测到 ${pages.length} 个分P，开始下载...`);

  for (const page of pages) {
    const url = `https://api.bilibili.com/x/player/v2?aid=${videoData.aid}&cid=${page.cid}&fnval=12288`;
    try {
      const resp = await fetch(url, { credentials: "include" });
      const data = await resp.json();
      const subs = data?.data?.subtitle?.subtitles || [];

      if (!subs.length) {
        console.warn(`[!] P${page.page} "${page.part}" 无字幕`);
        continue;
      }

      // 优先中文 AI 字幕
      let selected = subs.find(s => ["zh-CN", "ai-zh", "zh"].includes(s.lan)) || subs[0];
      let subUrl = selected.subtitle_url;
      if (subUrl.startsWith("//")) subUrl = "https:" + subUrl;

      const content = await fetch(subUrl).then(r => r.json());

      // sanitize 文件名（Windows 非法字符）
      const safeName = page.part.replace(/[\/:*?"<>|]/g, "_");
      const filename = `${page.page}_${safeName}.json`;

      const blob = new Blob([JSON.stringify(content, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      console.log(`[OK] P${page.page} "${page.part}" → ${filename} (${content.body?.length || 0} 条字幕)`);

      // 间隔防浏览器拦截批量下载
      await new Promise(r => setTimeout(r, 500));
    } catch (e) {
      console.error(`[!] P${page.page} "${page.part}" 下载失败:`, e);
    }
  }

  console.log("Done! 请将下载的 JSON 文件移动到 bilibili_SubtitlesOutput/<BV号>/raw/ 目录。");
})();
