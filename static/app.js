/* =====================================================================
   VieNeu TTS Web — app.js (JavaScript thuần, chú thích tiếng Việt)
   - Gọi API backend FastAPI: /api/health, /api/voices, /api/tts, /api/clone
   - Điều khiển: textarea, chọn giọng, slider tốc độ/cao độ, audio player
===================================================================== */
(function () {
  "use strict";

  // --- 1) Lấy các phần tử HTML theo id ---
  const $ = (id) => document.getElementById(id);
  const textInput = $("textInput"), voiceSelect = $("voiceSelect"),
    speedRange = $("speedRange"), pitchRange = $("pitchRange"),
    tempRange = $("tempRange"), playRate = $("playRate"),
    speedVal = $("speedVal"), pitchVal = $("pitchVal"),
    tempVal = $("tempVal"), playRateVal = $("playRateVal"),
    btnGen = $("btnGen"), btnWav = $("btnDownloadWav"), btnMp3 = $("btnDownloadMp3"),
    btnClone = $("btnClone"), msg = $("msg"), audio = $("audio"),
    playerBox = $("playerBox"), audioMeta = $("audioMeta"),
    charCount = $("charCount"), estTime = $("estTime"),
    modelStatus = $("modelStatus"), modelStatusText = $("modelStatusText"),
    voiceCount = $("voiceCount"), historyBox = $("history");

  // Văn bản mẫu tiếng Việt cho người dùng thử nhanh
  const SAMPLES = {
    tin: "Bản tin sáng nay: Theo Trung tâm Dự báo Khí tượng Thủy văn, hôm nay khu vực Bắc Bộ có nắng nhẹ vào buổi sáng, chiều tối có mưa rào rải rác. Người dân cần mang theo áo mưa khi ra đường.",
    truyen: "Ngày xửa ngày xưa, ở một làng quê yên bình ven sông Hồng, có một cậu bé chăn trâu rất hiếu thảo. Mỗi buổi chiều, tiếng sáo của cậu vang xa khắp cánh đồng, khiến ai nghe cũng thấy lòng bình yên.",
    qc: "Khuyến mãi lớn! Giảm giá tới năm mươi phần trăm cho mọi đơn hàng hôm nay. Nhanh tay đặt hàng để nhận ưu đãi đặc biệt và miễn phí giao hàng toàn quốc!",
    camxuc: "Nghe hay quá đi [cười]. Thật sự mình rất xúc động [thở dài]. Để mình hắng giọng một chút nhé [hắng giọng], rồi kể tiếp câu chuyện này cho các bạn nghe."
  };

  let lastFile = null;   // tên file wav mới nhất để tải xuống
  let lastAudioUrl = null;

  // --- 2) Hàm hiển thị thông báo (xanh/đỏ/xanh dương) ---
  function showMsg(text, type = "info") {
    msg.className = "msg " + type;
    msg.textContent = text;
    msg.classList.remove("hidden");
  }
  function hideMsg() { msg.classList.add("hidden"); }

  // --- 3) Đếm ký tự + ước tính thời gian đọc ---
  function updateCount() {
    const n = textInput.value.length;
    charCount.textContent = n.toLocaleString("vi-VN");
    // Trung bình tiếng Việt ~ 800 ký tự/phút
    const mins = n / 800;
    estTime.textContent = n ? `• ~${mins < 1 ? Math.round(mins * 60) + " giây" : mins.toFixed(1) + " phút"} audio` : "";
  }
  textInput.addEventListener("input", updateCount);

  // --- 4) Cập nhật nhãn slider ---
  speedRange.addEventListener("input", () => speedVal.textContent = Number(speedRange.value).toFixed(2) + "x");
  pitchRange.addEventListener("input", () => pitchVal.textContent = pitchRange.value);
  tempRange.addEventListener("input", () => tempVal.textContent = tempRange.value);
  playRate.addEventListener("input", () => {
    playRateVal.textContent = Number(playRate.value).toFixed(2) + "x";
    audio.playbackRate = Number(playRate.value); // tốc độ nghe thử (không đổi file gốc)
  });

  // --- 5) Nút mẫu + chèn tag cảm xúc vào vị trí con trỏ ---
  document.querySelectorAll("[data-sample]").forEach((b) =>
    b.addEventListener("click", () => { textInput.value = SAMPLES[b.dataset.sample]; updateCount(); }));
  document.querySelectorAll("[data-tag]").forEach((b) =>
    b.addEventListener("click", () => {
      const s = textInput.selectionStart || textInput.value.length;
      const e = textInput.selectionEnd || s;
      textInput.value = textInput.value.slice(0, s) + " " + b.dataset.tag + " " + textInput.value.slice(e);
      updateCount(); textInput.focus();
    }));
  $("btnClear").addEventListener("click", () => { textInput.value = ""; updateCount(); });

  // --- 6) Kiểm tra trạng thái model (đèn xanh/đỏ) ---
  async function checkHealth() {
    try {
      const r = await fetch("/api/health");
      const d = await r.json();
      const dot = modelStatus.querySelector(".dot");
      // Nhan chay: backend tra ve "docker" khi chay container, "local" khi chay python truc tiep
      const where = d.runtime === "docker" ? "🐳 Docker" : "💻 Local";
      if (d.status === "ok") {
        dot.className = "dot ok";
        modelStatusText.textContent = `${where} • Model sẵn sàng • ${d.backend} • ${d.sample_rate}Hz`;
      } else if (d.status === "loading") {
        dot.className = "dot pulse";
        modelStatusText.textContent = `${where} • Đang tải model lần đầu (cần mạng)…`;
        setTimeout(checkHealth, 4000); // hỏi lại sau 4s
      } else {
        dot.className = "dot pulse";
        modelStatusText.textContent = `${where} • Model chưa tải — bấm Chuyển đổi để kích hoạt`;
      }
    } catch {
      modelStatus.querySelector(".dot").className = "dot err";
      modelStatusText.textContent = "Mất kết nối backend";
    }
  }

  // --- 7) Tải danh sách giọng đọc vào <select> ---
  async function loadVoices() {
    try {
      const r = await fetch("/api/voices");
      const d = await r.json();
      const vs = d.voices || [];
      voiceCount.textContent = vs.length;
      voiceSelect.innerHTML = "";
      // Nhóm giọng: tuyển chọn ⭐ lên đầu cho dễ chọn
      const feat = vs.filter((v) => v.featured), rest = vs.filter((v) => !v.featured);
      const mkGroup = (label, arr) => {
        if (!arr.length) return;
        const g = document.createElement("optgroup"); g.label = label;
        arr.forEach((v) => {
          const o = document.createElement("option");
          o.value = v.id; o.textContent = v.label || v.id;
          if (v.id === "Hải Đăng") o.selected = true;
          g.appendChild(o);
        });
        voiceSelect.appendChild(g);
      };
      mkGroup("⭐ Giọng tuyển chọn", feat);
      mkGroup("Tất cả giọng", rest);
    } catch {
      voiceSelect.innerHTML = "<option>Hải Đăng</option>";
    }
  }

  // --- 8) Lưu lịch sử vào localStorage để nghe lại ---
  function getHist() { try { return JSON.parse(localStorage.getItem("vieneu_hist") || "[]"); } catch { return []; } }
  function setHist(h) { localStorage.setItem("vieneu_hist", JSON.stringify(h.slice(0, 20))); }
  function renderHist() {
    const h = getHist();
    if (!h.length) { historyBox.innerHTML = '<p class="empty">Chưa có file nào. File bạn tạo sẽ hiện ở đây.</p>'; return; }
    historyBox.innerHTML = "";
    h.forEach((it) => {
      const div = document.createElement("div"); div.className = "hist-item";
      div.innerHTML = `<div style="flex:1"><b>${it.voice}</b> • ${it.duration}s • ${it.time}<br><span style="color:#64748b">${it.text}</span><audio controls preload="none" src="${it.url}"></audio></div>`;
      const act = document.createElement("div"); act.className = "h-act";
      const dl = document.createElement("button"); dl.textContent = "⬇️";
      dl.title = "Tải xuống"; dl.onclick = () => window.open(it.url, "_blank");
      act.appendChild(dl); div.appendChild(act);
      historyBox.appendChild(div);
    });
  }
  $("btnClearHist").addEventListener("click", () => { setHist([]); renderHist(); });
  function pushHist(entry) { const h = getHist(); h.unshift(entry); setHist(h); renderHist(); }

  // --- 9) Nút CHUYỂN ĐỔI: gửi văn bản → nhận file âm thanh ---
  btnGen.addEventListener("click", async () => {
    const text = textInput.value.trim();
    if (!text) return showMsg("⚠️ Vui lòng nhập văn bản trước.", "err");
    btnGen.disabled = true; btnWav.disabled = btnMp3.disabled = true;
    showMsg("⏳ Đang tổng hợp giọng nói bằng engine VieNeu v3 Turbo…", "info");
    try {
      const res = await fetch("/api/tts", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text, voice: voiceSelect.value,
          temperature: Number(tempRange.value),
          speed: Number(speedRange.value),   // slider tốc độ
          pitch: Number(pitchRange.value),   // slider cao độ
        }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.error || "Lỗi không rõ");
      // Có file → hiện trình phát + cho phép tải
      lastFile = d.file; lastAudioUrl = d.audio_url;
      audio.src = d.audio_url; audio.playbackRate = Number(playRate.value);
      playerBox.classList.remove("hidden");
      audio.play().catch(() => {});
      audioMeta.textContent = `🎙 ${d.voice} • ⏩ ${d.speed}x • 🎵 ${d.pitch} • ⏱ ${d.duration}s • RTF ${d.rtf}`;
      btnWav.disabled = btnMp3.disabled = false;
      showMsg(`✅ Hoàn tất sau ${d.elapsed}s! Bấm play để nghe hoặc tải xuống.`, "ok");
      pushHist({ voice: d.voice, duration: d.duration, url: d.audio_url, text: text.slice(0, 60), time: new Date().toLocaleString("vi-VN") });
      checkHealth();
    } catch (e) {
      showMsg("❌ " + e.message, "err");
    } finally { btnGen.disabled = false; }
  });

  // --- 10) Nút TẢI XUỐNG (WAV luôn có, MP3 cần ffmpeg trên server) ---
  btnWav.addEventListener("click", () => { if (lastFile) window.open(`/api/download/${lastFile}?fmt=wav`, "_blank"); });
  btnMp3.addEventListener("click", async () => {
    if (!lastFile) return;
    showMsg("⏳ Đang chuyển sang MP3…", "info");
    const r = await fetch(`/api/download/${lastFile}?fmt=mp3`);
    if (r.ok) { window.open(`/api/download/${lastFile}?fmt=mp3`, "_blank"); hideMsg(); }
    else {
      const d = await r.json().catch(() => ({}));
      showMsg("⚠️ " + (d.error || "Chưa hỗ trợ MP3") + " — hãy tải WAV.", "err");
      if (d.fallback) window.open(d.fallback, "_blank");
    }
  });

  // --- 11) Nút VOICE CLONING: tải file mẫu + văn bản ---
  btnClone.addEventListener("click", async () => {
    const text = textInput.value.trim();
    const f = $("refAudio").files[0];
    if (!text) return showMsg("⚠️ Nhập văn bản trước khi clone.", "err");
    if (!f) return showMsg("⚠️ Hãy chọn file giọng mẫu 3–8 giây.", "err");
    btnClone.disabled = true;
    showMsg("🧬 Đang nhân bản giọng từ file mẫu…", "info");
    try {
      const fd = new FormData();
      fd.append("text", text); fd.append("file", f);
      fd.append("denoise", $("denoise").checked ? "true" : "false");
      fd.append("voice_name", $("cloneName").value || "");
      fd.append("speed", speedRange.value); fd.append("pitch", pitchRange.value);
      const res = await fetch("/api/clone", { method: "POST", body: fd });
      const d = await res.json();
      if (!res.ok) throw new Error(d.error || "Lỗi clone");
      lastFile = d.file; lastAudioUrl = d.audio_url;
      audio.src = d.audio_url; playerBox.classList.remove("hidden");
      audio.play().catch(() => {});
      audioMeta.textContent = `🧬 Cloned • ⏱ ${d.duration}s`;
      btnWav.disabled = btnMp3.disabled = false;
      showMsg("✅ Clone giọng thành công!", "ok");
      pushHist({ voice: "Cloned", duration: d.duration, url: d.audio_url, text: text.slice(0, 60), time: new Date().toLocaleString("vi-VN") });
    } catch (e) { showMsg("❌ " + e.message, "err"); }
    finally { btnClone.disabled = false; }
  });

  // --- 12) Khởi động trang ---
  updateCount(); checkHealth(); loadVoices(); renderHist();
})();
