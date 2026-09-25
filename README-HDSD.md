# 🦜 VieNeu TTS Web — Chuyển văn bản thành giọng nói tiếng Việt

Web TTS dùng **engine VieNeu-TTS v3 Turbo** (repo gốc: https://github.com/pnnbao97/VieNeu-TTS).
- 25 giọng preset 3 miền Bắc/Trung/Nam, 48kHz, voice-cloning tức thì từ file 3–8s.
- Backend **Python FastAPI + thư viện `vieneu`**, Frontend **HTML + TailwindCSS + JS thuần**.

## 📁 Cấu trúc thư mục

```
TTS_Viet/
├── app.py                  # Backend FastAPI (API /api/tts, /api/voices, /api/clone...)
├── requirements.txt        # Thư viện cần cài
├── start.bat               # Chạy nhanh trên Windows (double-click)
├── static/                 # Frontend
│   ├── index.html          # Giao diện: textarea, chọn giọng, slider tốc độ/cao độ...
│   ├── style.css           # CSS riêng (kết hợp Tailwind CDN)
│   └── app.js              # JS gọi API, audio player, lịch sử
├── outputs/                # File .wav đã tạo (tự sinh)
├── Dockerfile              # Đóng gói chạy Docker (Python 3.12 + ffmpeg)
├── docker-compose.yml      # Chạy 1 lệnh: docker compose up -d
├── .dockerignore           # Loại file nặng khỏi image
├── VieNeu-TTS-source/      # Source engine gốc đã clone từ GitHub (tham khảo)
└── README-HDSD.md          # File này
```

## ⚙️ API backend

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/` | Giao diện web |
| GET | `/api/health` | Trạng thái model |
| GET | `/api/voices` | Danh sách giọng đọc |
| POST | `/api/tts` | `{text, voice, speed, pitch, temperature}` → `{audio_url,...}` |
| POST | `/api/clone` | Form `text + file + denoise` → nhân bản giọng |
| GET | `/api/download/{file}?fmt=wav\|mp3` | Tải file về máy |
| GET | `/outputs/{file}` | Nghe trực tiếp |

## 🚀 Cài đặt từng bước trên máy cá nhân (Windows)

### Bước 1 — Cài Python 3.10+
Tải tại https://www.python.org/downloads/ — **tick chọn "Add python to PATH"** khi cài.
Kiểm tra:
```bat
python --version
pip --version
```

### Bước 2 — Tải project + mở thư mục
```bat
cd "E:\AI Project\TTS_Viet"
```

### Bước 3 — (Khuyên dùng) Tạo môi trường ảo
```bat
python -m venv .venv
.venv\Scripts\activate
```

### Bước 4 — Cài thư viện
```bat
pip install --upgrade pip
pip install -r requirements.txt
```
Lệnh này cài: `fastapi, uvicorn, python-multipart, soundfile, numpy, soxr` và **`vieneu`** (engine).
> Mạng yếu? Cài tối thiểu rồi chạy vẫn được (web báo rõ nếu thiếu):
> ```bat
> pip install fastapi "uvicorn[standard]" python-multipart soundfile numpy
> pip install vieneu
> ```

### Bước 5 — Chạy web
Cách A (nhanh):
```bat
start.bat
```
Cách B (thủ công):
```bat
python app.py
```
Mở trình duyệt: **http://127.0.0.1:8000**

> Lần đầu chạy cần mạng để **tự tải model `pnnbao-ump/VieNeu-TTS-v3-Turbo` (~1–3GB)** từ HuggingFace.
> Muốn bản nhẹ nhanh hơn (CPU yếu): `set VIENEU_PRECISION=int8` trước khi chạy.

## 🖱️ Cách dùng

1. Nhập/dán văn bản tiếng Việt vào ô lớn (tối đa 20.000 ký tự).
2. Chọn **giọng đọc** (⭐ là giọng tuyển chọn), kéo **Tốc độ (0.5–1.5x)** và **Cao độ (-6…+6)**.
3. Bấm **🎤 Chuyển đổi** → nghe ngay ở **Audio player**.
4. Bấm **⬇️ Tải WAV / MP3** để lưu file (MP3 cần `ffmpeg`, nếu chưa có hãy tải WAV).
5. Muốn clone giọng: mở mục **🧬 Voice cloning**, chọn file mẫu 3–8s → bấm tạo.

Mẹo cảm xúc (thử nghiệm): chèn `[cười]`, `[thở dài]`, `[hắng giọng]` vào câu.

## ❓ Lỗi thường gặp

| Lỗi | Cách sửa |
|---|---|
| `No module named 'vieneu'` | Chạy `pip install vieneu` (hoặc `pip install -r requirements.txt`) |
| Web báo "Model đang tải" lâu | Lần đầu tải model lớn, chờ 5–15 phút tùy mạng; đèn trạng thái sẽ xanh khi xong |
| Không tải được MP3 | Cài ffmpeg hoặc dùng WAV: `pip install pydub`, tải ffmpeg tại https://www.gyan.dev/ffmpeg/builds/ |
| `kaldi-native-fbank` build lỗi trên Windows | Dùng Python 3.10–3.12 ổn định hơn 3.14; hoặc `pip install vieneu --no-deps` + cài tay `onnxruntime soundfile soxr tokenizers huggingface_hub` |
| Cổng 8000 bận | Đổi port: `uvicorn app:app --port 8001` |

## 🐳 Chạy bằng Docker (khuyên dùng — đủ voice cloning + MP3)

Yêu cầu: đã cài **Docker Desktop**. Trong thư mục project:

```bat
docker compose up -d --build
```

- Mở **http://localhost:8000** để dùng.
- Lần đầu container tự nạp model (dùng chung cache `~/.cache/huggingface` trên máy nên nhanh).
- Xem log: `docker compose logs -f` • Dừng: `docker compose down` • Chạy lại: `docker compose up -d`
- File wav tạo ra nằm ở `./outputs` trên máy host.
- Bản Docker dùng Python 3.12 nên có đủ `kaldi-native-fbank` (voice cloning) và `ffmpeg` (xuất MP3).

## 📜 Bản quyền
Engine © Phạm Nguyễn Ngọc Bảo — Apache-2.0. Web này là giao diện minh họa gọi SDK `vieneu`.
