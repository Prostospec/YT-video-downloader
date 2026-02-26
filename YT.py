import customtkinter as ctk
import yt_dlp
import os
import threading
import sys
import requests
from PIL import Image
from io import BytesIO

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("BG_GAMES Downloader Ultra")
        self.geometry("600x650")
        
        # Фикс вставки
        self.bind_all("<Control-v>", self.paste_event)
        self.bind_all("<Control-V>", self.paste_event)
        self.bind_all("<Control-Key-86>", self.paste_event) 

        # UI элементы
        self.label = ctk.CTkLabel(self, text="Вставьте ссылку на YouTube:", font=("Arial", 16))
        self.label.pack(pady=(20, 5))

        self.url_entry = ctk.CTkEntry(self, width=450)
        self.url_entry.pack(pady=10)
        self.url_entry.bind("<KeyRelease>", self.on_url_change)

        # Превью
        self.preview_label = ctk.CTkLabel(self, text="Ожидание ссылки...", width=320, height=180, fg_color="#2b2b2b", corner_radius=10)
        self.preview_label.pack(pady=10)

        # Выбор качества (появляется после анализа)
        self.quality_label = ctk.CTkLabel(self, text="Выберите качество:", font=("Arial", 12))
        self.quality_menu = ctk.CTkOptionMenu(self, values=["Сначала вставьте ссылку"])
        self.quality_menu.set("Ожидание...")
        
        # Фрейм выбора режима
        self.mode_var = ctk.StringVar(value="video")
        self.mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.mode_frame.pack(pady=10)
        ctk.CTkRadioButton(self.mode_frame, text="Видео (MP4)", variable=self.mode_var, value="video", command=self.toggle_quality_ui).pack(side="left", padx=20)
        ctk.CTkRadioButton(self.mode_frame, text="Аудио (MP3)", variable=self.mode_var, value="audio", command=self.toggle_quality_ui).pack(side="left", padx=20)

        self.download_btn = ctk.CTkButton(self, text="Скачать", font=("Arial", 14, "bold"), command=self.start_download_thread, height=40, width=200)
        self.download_btn.pack(pady=15)

        # Скрытые элементы статуса
        self.progress_label = ctk.CTkLabel(self, text="0%")
        self.progress_bar = ctk.CTkProgressBar(self, width=450)
        self.status_label = ctk.CTkLabel(self, text="", text_color="yellow")

    def toggle_quality_ui(self):
        if self.mode_var.get() == "audio":
            self.quality_label.pack_forget()
            self.quality_menu.pack_forget()
        else:
            self.quality_label.pack(after=self.preview_label)
            self.quality_menu.pack(after=self.quality_label)

    def paste_event(self, event):
        try:
            content = self.clipboard_get()
            self.url_entry.insert("insert", content)
            self.on_url_change()
        except: pass
        return "break"

    def on_url_change(self, event=None):
        url = self.url_entry.get().strip()
        if len(url) > 15 and ("youtube.com" in url or "youtu.be" in url):
            self.quality_menu.set("Анализ видео...")
            threading.Thread(target=self.load_video_info, args=(url,), daemon=True).start()

    def load_video_info(self, url):
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                # Загрузка превью
                thumb_url = info.get('thumbnail')
                if thumb_url:
                    res = requests.get(thumb_url, timeout=5)
                    img = Image.open(BytesIO(res.content))
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(320, 180))
                    self.preview_label.configure(image=ctk_img, text="")

                # Получение разрешений
                formats = set()
                for f in info.get('formats', []):
                    if f.get('height') and f.get('vcodec') != 'none':
                        formats.add(f'{f["height"]}p')
                
                sorted_res = sorted(list(formats), key=lambda x: int(x[:-1]), reverse=True)
                self.quality_menu.configure(values=sorted_res)
                self.quality_menu.set(sorted_res[0])
                self.toggle_quality_ui()
        except:
            self.quality_menu.set("Ошибка ссылки")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%','')
            try:
                self.progress_bar.set(float(p) / 100)
                self.progress_label.configure(text=f"Загрузка: {int(float(p))}%")
            except: pass

    def download(self):
        url = self.url_entry.get().strip()
        if not url: return

        self.status_label.pack(pady=5)
        self.progress_label.pack()
        self.progress_bar.pack(pady=10)
        self.download_btn.configure(state="disabled")

        ffmpeg_bin = os.path.join(sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(__file__), 'ffmpeg.exe')
        res = self.quality_menu.get().replace("p", "")

        ydl_opts = {
            'outtmpl': os.path.join(os.path.expanduser('~'), 'Downloads', '%(title)s.%(ext)s'),
            'ffmpeg_location': ffmpeg_bin if os.path.exists(ffmpeg_bin) else None,
            'progress_hooks': [self.progress_hook],
        }

        if self.mode_var.get() == 'audio':
            ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]})
        else:
            # Качаем выбранное качество (MP4 совместимое)
            ydl_opts.update({
                'format': f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res}][ext=mp4]',
                'merge_output_format': 'mp4'
            })

        try:
            self.status_label.configure(text="Загрузка началась...", text_color="yellow")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.status_label.configure(text="Успешно сохранено!", text_color="green")
        except:
            self.status_label.configure(text="Ошибка загрузки", text_color="red")
        finally:
            self.download_btn.configure(state="normal")
            self.after(5000, self.hide_status)

    def hide_status(self):
        self.status_label.pack_forget()
        self.progress_label.pack_forget()
        self.progress_bar.pack_forget()

    def start_download_thread(self):
        threading.Thread(target=self.download, daemon=True).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()