# -*- coding: utf-8 -*-
"""
=====================================================================
VieNeu TTS Web — Backend FastAPI
---------------------------------------------------------------------
- Engine: VieNeu-TTS v3 Turbo (repo gốc: https://github.com/pnnbao97/VieNeu-TTS)
- Model tự tải từ HuggingFace `pnnbao-ump/VieNeu-TTS-v3-Turbo` ở lần chạy đầu.
- CPU chạy ONNX (nhẹ, không cần torch), có GPU sẽ tự dùng PyTorch nhanh hơn.
- Chạy local:  python app.py  → mở http://127.0.0.1:8000
=====================================================================
"""
import os          # đọc biến môi trường, xử lý file
import sys         # fix encoding tiếng Việt trên Windows
import time        # đo thời gian tổng hợp, đặt tên file
import uuid        # tạo tên file ngẫu nhiên không trùng
import threading   # load model nền để web mở nhanh
import tempfile    # lưu tạm file giọng mẫu khi voice-clone
from pathlib import Path  # xử lý đường dẫn đa nền tảng

# --- Fix lỗi font tiếng Việt trên Windows PowerShell ---
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- Đường dẫn gốc của project ---
BASE_DIR = Path(__file__).resolve().parent          # E:\AI Project\TTS_Viet
OUTPUTS_DIR = BASE_DIR / "outputs"                  # nơi lưu file .wav đã tạo
OUTPUTS_DIR.mkdir(exist_ok=True)                    # tự tạo nếu chưa có
STATIC_DIR = BASE_DIR / "static"                    # nơi chứa frontend (index.html...)

# ---------------------------------------------------------------------------
# 1) Quản lý engine VieNeu (load lười - lazy loading)
# ---------------------------------------------------------------------------
_tts = None              # object Vieneu() sau khi load xong
_tts_error: str | None = None  # lỗi load model (nếu có)
_tts_loading = False     # cờ: đang tải model dở
_tts_lock = threading.Lock()   # chống load 2 lần cùng lúc
BACKEND_NAME = "none"    # "onnx" (CPU) hoặc "pytorch" (GPU)
SAMPLE_RATE = 48000      # v3 Turbo xuất âm 48kHz

# Danh sách 25 giọng dự phòng hiển thị ngay cả khi model chưa tải xong.
FALLBACK_VOICES = [
    {"id": "Hải Đăng", "label": "⭐ Hải Đăng — nam Bắc, tin tức (mặc định)", "region": "Bắc", "gender": "Nam", "featured": True},
    {"id": "Mai Anh", "label": "⭐ Mai Anh — nữ Bắc, dịu dàng", "region": "Bắc", "gender": "Nữ", "featured": True},
    {"id": "Trúc Ly", "label": "⭐ Trúc Ly — nữ trẻ, tươi sáng", "region": "Bắc", "gender": "Nữ", "featured": True},
    {"id": "Thiện Minh", "label": "⭐ Thiện Minh — nam trầm ấm", "region": "Bắc", "gender": "Nam", "featured": True},
    {"id": "Adam bựa", "label": "⭐ Adam bựa — nam Nam, hài hước", "region": "Nam", "gender": "Nam", "featured": True},
    {"id": "Thùy Dung", "label": "⭐ Thùy Dung — nữ Nam, truyền cảm", "region": "Nam", "gender": "Nữ", "featured": True},
    {"id": "Thiền Tâm Đức", "label": "⭐ Thiền Tâm Đức — nam, thiền định", "region": "Bắc", "gender": "Nam", "featured": True},
    {"id": "Ngọc Huyền", "label": "⭐ Ngọc Huyền — nữ kể chuyện", "region": "Bắc", "gender": "Nữ", "featured": True},
    {"id": "Quang Sơn", "label": "⭐ Quang Sơn — nam Trung, rắn rỏi", "region": "Trung", "gender": "Nam", "featured": True},
    {"id": "Ngọc Trân", "label": "⭐ Ngọc Trân — nữ Trung, ngọt ngào", "region": "Trung", "gender": "Nữ", "featured": True},
    {"id": "Minh Đức", "label": "Minh Đức — nam Bắc", "region": "Bắc", "gender": "Nam", "featured": False},
    {"id": "Phạm Tuyên", "label": "Phạm Tuyên — nam Bắc, uy tín", "region": "Bắc", "gender": "Nam", "featured": False},
    {"id": "Xuân Vĩnh", "label": "Xuân Vĩnh — nam Bắc", "region": "Bắc", "gender": "Nam", "featured": False},
    {"id": "Thanh Bình", "label": "Thanh Bình — nam Bắc", "region": "Bắc", "gender": "Nam", "featured": False},
    {"id": "Ngọc Linh", "label": "Ngọc Linh — nữ Bắc", "region": "Bắc", "gender": "Nữ", "featured": False},
    {"id": "Đoan Trang", "label": "Đoan Trang — nữ Bắc", "region": "Bắc", "gender": "Nữ", "featured": False},
    {"id": "Quỳnh Anh", "label": "Quỳnh Anh — nữ Bắc", "region": "Bắc", "gender": "Nữ", "featured": False},
    {"id": "Quốc Tuấn", "label": "Quốc Tuấn — nam Bắc", "region": "Bắc", "gender": "Nam", "featured": False},
    {"id": "Adam", "label": "Adam — nam Nam", "region": "Nam", "gender": "Nam", "featured": False},
    {"id": "Thái Sơn", "label": "Thái Sơn — nam Nam", "region": "Nam", "gender": "Nam", "featured": False},
    {"id": "Thục Đoan", "label": "Thục Đoan — nữ Nam", "region": "Nam", "gender": "Nữ", "featured": False},
    {"id": "Minh Triết", "label": "Minh Triết — nam Nam", "region": "Nam", "gender": "Nam", "featured": False},
    {"id": "Mỹ Duyên", "label": "Mỹ Duyên — nữ Nam", "region": "Nam", "gender": "Nữ", "featured": False},
    {"id": "Đức Trí", "label": "Đức Trí — nam Nam", "region": "Nam", "gender": "Nam", "featured": False},
    {"id": "Kim Thanh", "label": "Kim Thanh — nữ Nam", "region": "Nam", "gender": "Nữ", "featured": False},
]


def get_tts():
    """Lấy object engine Vieneu (tự tải model nếu chưa có)."""
    global _tts, _tts_error, _tts_loading, BACKEND_NAME, SAMPLE_RATE
    if _tts is not None:  # đã load rồi → trả ngay
        return _tts, None
    with _tts_lock:
        if _tts is not None:
            return _tts, None
        if _tts_loading:  # luồng khác đang tải → báo frontend chờ
            return None, "loading"
        _tts_loading = True
    try:
        from vieneu import Vieneu  # thư viện engine (pip install vieneu)
        precision = os.environ.get("VIENEU_PRECISION", "fp32")  # fp32 nét nhất, int8 nhanh hơn
        print(f"⏳ Đang tải VieNeu-TTS v3 Turbo (precision={precision})...")
        print("   Lần đầu cần mạng để tải ~1-3GB từ HuggingFace pnnbao-ump/VieNeu-TTS-v3-Turbo")
        t0 = time.time()
        tts = Vieneu(mode="v3turbo", precision=precision)  # tự chọn onnx(CPU)/pytorch(GPU)
        with _tts_lock:
            _tts = tts
            BACKEND_NAME = getattr(tts, "backend", "onnx")
            SAMPLE_RATE = getattr(tts, "sample_rate", 48000)
        print(f"✅ Model sẵn sàng sau {time.time()-t0:.1f}s (backend={BACKEND_NAME}, {SAMPLE_RATE}Hz)")
        return _tts, None
    except Exception as e:  # chưa cài vieneu / mất mạng / hết RAM...
        import traceback
        traceback.print_exc()
        with _tts_lock:
            _tts_error = str(e)
            _tts_loading = False
        return None, str(e)
    finally:
        with _tts_lock:
            if _tts is not None:
                _tts_loading = False


def preload_in_background():
    """Load model ở thread nền để trang web mở ngay, model vào sau."""
    def _run():
        tts, err = get_tts()
        if err and err != "loading":
            print(f"⚠️ Không tải được model: {err}")
    threading.Thread(target=_run, daemon=True).start()


# ---------------------------------------------------------------------------
# 2) Hậu kỳ âm thanh: chỉnh Tốc độ (Speed) và Cao độ (Pitch)
#    - Engine gốc không có 2 tham số này → ta xử lý sau khi sinh wav.
# ---------------------------------------------------------------------------
def apply_speed_pitch(audio, sr: int, speed: float = 1.0, pitch: float = 0.0):
    """Chỉnh tốc độ & cao độ cho mảng audio numpy.

    - speed: 0.5 (chậm) → 1.5 (nhanh). Dùng nội suy tuyến tính (không cần lib nặng).
    - pitch: số semitone -12 … +12. Ưu tiên dùng librosa nếu có, không thì resample gần đúng.
    """
    import numpy as np
    y = np.asarray(audio, dtype=np.float32)
    # --- Tốc độ: đổi độ dài mảng (speed>1 → ngắn lại = nhanh hơn) ---
    if speed and abs(speed - 1.0) > 1e-3:
        speed = float(max(0.5, min(1.5, speed)))  # kẹp an toàn
        old_idx = np.arange(len(y))
        new_len = max(1, int(len(y) / speed))
        new_idx = np.linspace(0, len(y) - 1, new_len)
        y = np.interp(new_idx, old_idx, y).astype(np.float32)
    # --- Cao độ (pitch shift, đơn vị semitone) ---
    if pitch and abs(pitch) > 1e-6:
        pitch = float(max(-12, min(12, pitch)))
        try:
            import librosa  # nếu máy đã cài librosa (đi kèm vieneu) thì cho chất lượng tốt
            y = librosa.effects.pitch_shift(y, sr=sr, n_steps=pitch).astype(np.float32)
        except Exception:
            # Dự phòng không có librosa: đổi pitch bằng resample (giọng hơi khác nhưng vẫn dùng được)
            factor = 2.0 ** (pitch / 12.0)
            old_idx = np.arange(len(y))
            new_len = max(1, int(len(y) / factor))
            new_idx = np.linspace(0, len(y) - 1, new_len)
            tmp = np.interp(new_idx, old_idx, y).astype(np.float32)
            # kéo lại độ dài cũ để giữ tốc độ (gần đúng)
            if len(tmp) != len(y):
                oi = np.arange(len(tmp))
                ni = np.linspace(0, len(tmp) - 1, len(y))
                y = np.interp(ni, oi, tmp).astype(np.float32)
            else:
                y = tmp
    return y


def _save_wav(audio, sr: int) -> Path:
    """Lưu mảng float32 thành file .wav trong thư mục outputs/."""
    import numpy as np
    import soundfile as sf
    audio = np.asarray(audio, dtype=np.float32)
    fname = f"vieneu_{int(time.time())}_{uuid.uuid4().hex[:6]}.wav"
    out = OUTPUTS_DIR / fname
    sf.write(str(out), audio, sr)  # 48kHz chuẩn v3 Turbo
    return out


# ---------------------------------------------------------------------------
# 3) FastAPI: khai báo app + các API
# ---------------------------------------------------------------------------
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="VieNeu TTS Web", version="1.0")


@app.on_event("startup")
def _startup_preload():
    """Tự nạp model nền khi server khởi động (quan trọng khi chạy Docker
    bằng `uvicorn app:app`, vì nhánh `__main__` không được thực thi)."""
    preload_in_background()


class TTSRequest(BaseModel):
    """Body JSON cho POST /api/tts."""
    text: str                    # văn bản tiếng Việt (tối đa 20.000 ký tự)
    voice: str = "Hải Đăng"      # tên giọng trong danh sách preset
    temperature: float = 0.8     # độ tự nhiên 0.3–1.2
    speed: float = 1.0           # tốc độ đọc 0.5–1.5
    pitch: float = 0.0           # cao độ -12…+12 semitone


@app.get("/api/health")
def health():
    """Kiểm tra trạng thái model để frontend hiển thị đèn xanh/đỏ."""
    with _tts_lock:
        loaded, loading, err = _tts is not None, _tts_loading, _tts_error
    return {
        "status": "ok" if loaded else ("loading" if loading else "not_loaded"),
        "model": "pnnbao-ump/VieNeu-TTS-v3-Turbo",
        "backend": BACKEND_NAME, "sample_rate": SAMPLE_RATE,
        "error": err, "engine_repo": "https://github.com/pnnbao97/VieNeu-TTS",
    }


@app.get("/api/voices")
def voices():
    """Trả danh sách giọng đọc cho <select> ở frontend."""
    if _tts is not None:  # model đã load → hỏi engine danh sách thật
        try:
            raw = _tts.list_preset_voices()
            out = []
            for item in raw:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    label, vid = item[0], item[1]
                else:
                    label, vid = str(item), str(item)
                out.append({"id": vid, "label": label, "region": "", "gender": "", "featured": str(label).startswith("⭐")})
            return {"voices": out, "source": "model", "count": len(out)}
        except Exception as e:
            return {"voices": FALLBACK_VOICES, "source": f"fallback ({e})", "count": len(FALLBACK_VOICES)}
    return {"voices": FALLBACK_VOICES, "source": "fallback", "count": len(FALLBACK_VOICES)}


@app.post("/api/tts")
def tts_infer(req: TTSRequest):
    """Chuyển văn bản → file .wav (API chính, nút 'Chuyển đổi' gọi vào đây)."""
    text = (req.text or "").strip()
    if not text:
        return JSONResponse({"error": "Vui lòng nhập văn bản."}, status_code=400)
    if len(text) > 20000:
        return JSONResponse({"error": "Văn bản quá dài (tối đa 20.000 ký tự)."}, status_code=400)
    tts, err = get_tts()
    if tts is None:
        msg = "Model đang tải, vui lòng thử lại sau ít giây." if err == "loading" else f"Chưa tải được model: {err}"
        return JSONResponse({"error": msg, "hint": "Chạy: pip install vieneu. Lần đầu cần mạng để tải model."}, status_code=503)
    try:
        t0 = time.time()
        # 1) Sinh giọng gốc bằng engine VieNeu
        audio = tts.infer(text, voice=req.voice or None, temperature=float(req.temperature or 0.8))
        sr = getattr(tts, "sample_rate", 48000)
        # 2) Hậu kỳ tốc độ + cao độ theo slider của người dùng
        audio = apply_speed_pitch(audio, sr, speed=req.speed, pitch=req.pitch)
        elapsed = time.time() - t0
        out = _save_wav(audio, sr)  # 3) Lưu wav để phát + tải
        import numpy as np
        dur = float(len(np.asarray(audio)) / sr) if len(audio) else 0
        return {
            "audio_url": f"/outputs/{out.name}", "file": out.name,
            "sample_rate": sr, "duration": round(dur, 2),
            "elapsed": round(elapsed, 2), "rtf": round(elapsed / dur, 4) if dur else 0,
            "voice": req.voice, "speed": req.speed, "pitch": req.pitch,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"Lỗi tổng hợp: {e}"}, status_code=500)


@app.post("/api/clone")
async def tts_clone(
    text: str = Form(...),                 # văn bản cần đọc
    denoise: bool = Form(True),            # có khử nhiễu file mẫu không
    voice_name: str = Form(""),            # tên để lưu giọng (tùy chọn)
    speed: float = Form(1.0),              # tốc độ đọc
    pitch: float = Form(0.0),              # cao độ
    file: UploadFile = File(...),          # file giọng mẫu 3–8s
):
    """Nhân bản giọng từ file mẫu (voice cloning tức thì của VieNeu)."""
    text = (text or "").strip()
    if not text:
        return JSONResponse({"error": "Vui lòng nhập văn bản."}, status_code=400)
    if file is None or not file.filename:
        return JSONResponse({"error": "Vui lòng tải file giọng mẫu (3–8 giây)."}, status_code=400)
    data = await file.read()  # đọc bytes upload
    if len(data) > 20 * 1024 * 1024:
        return JSONResponse({"error": "File quá lớn (tối đa 20MB)."}, status_code=413)
    ext = os.path.splitext(file.filename or "")[1].lower() or ".wav"
    if ext not in (".wav", ".mp3", ".flac", ".ogg", ".m4a"):
        ext = ".wav"
    tts, err = get_tts()
    if tts is None:
        msg = "Model đang tải, vui lòng thử lại sau ít giây." if err == "loading" else f"Chưa tải được model: {err}"
        return JSONResponse({"error": msg}, status_code=503)
    fd, tmp = tempfile.mkstemp(suffix=ext)  # lưu tạm file mẫu
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        t0 = time.time()
        if voice_name.strip():  # có đặt tên → lưu giọng để dùng lại
            try:
                tts.add_voice(voice_name.strip(), tmp, denoise=bool(denoise))
                audio = tts.infer(text, voice=voice_name.strip())
            except Exception:
                audio = tts.infer(text, ref_audio=tmp, denoise=bool(denoise))
        else:
            audio = tts.infer(text, ref_audio=tmp, denoise=bool(denoise))
        sr = getattr(tts, "sample_rate", 48000)
        audio = apply_speed_pitch(audio, sr, speed=speed, pitch=pitch)
        out = _save_wav(audio, sr)
        import numpy as np
        dur = float(len(np.asarray(audio)) / sr) if len(audio) else 0
        return {"audio_url": f"/outputs/{out.name}", "file": out.name,
                "duration": round(dur, 2), "elapsed": round(time.time() - t0, 2), "sample_rate": sr}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"Lỗi voice cloning: {e}"}, status_code=500)
    finally:
        try:
            os.unlink(tmp)  # xóa file tạm
        except Exception:
            pass


@app.get("/api/download/{fname}")
def download_file(fname: str, fmt: str = "wav"):
    """Tải file về máy: /api/download/xxx.wav?fmt=wav|mp3."""
    safe = Path(fname).name  # chống path-traversal
    src = OUTPUTS_DIR / safe
    if not src.exists():
        return JSONResponse({"error": "File không tồn tại."}, status_code=404)
    if fmt.lower() == "mp3":  # thử convert sang mp3 nếu có ffmpeg/pydub
        try:
            from pydub import AudioSegment
            mp3_path = src.with_suffix(".mp3")
            if not mp3_path.exists():
                AudioSegment.from_wav(str(src)).export(str(mp3_path), format="mp3")
            return FileResponse(str(mp3_path), media_type="audio/mpeg", filename=mp3_path.name)
        except Exception as e:
            return JSONResponse({"error": f"Server chưa hỗ trợ MP3 ({e}). Hãy tải WAV.", "fallback": f"/outputs/{safe}"}, status_code=501)
    return FileResponse(str(src), media_type="audio/wav", filename=src.name)


# --- Phục vụ frontend tĩnh + file âm thanh đã tạo ---
if STATIC_DIR.exists():
    app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
else:
    @app.get("/")
    def root():
        return {"message": "Thiếu thư mục static/. Hãy tạo frontend trước."}


# --- Chạy server local ---
if __name__ == "__main__":
    import uvicorn
    preload_in_background()  # tải model nền
    print("🦜 VieNeu TTS Web — http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, workers=1)
