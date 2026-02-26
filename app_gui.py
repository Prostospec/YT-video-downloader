import customtkinter as ctk
import yt_dlp
import os
import threading
import sys
import requests
import keyboard
import time
from PIL import Image
from io import BytesIO

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("BG_GAMES Downloader Ultra")
        self.geometry("600x680")
        
        # Фоновый поток для отслеживания Ctrl+V (скан-код 47) на любой раскладке
        threading.Thread(target=self.setup_hotkeys, daemon=True).start()

        # Заголовок
        self.label = ctk.CTkLabel(self, text="Вставьте ссылку на YouTube:", font=("Arial", 16))
        self.label.pack(pady=(20, 5))

        # Поле ввода
        self.url_entry = ctk.CTkEntry(self, width=450, placeholder_text="Нажмите Ctrl + V для вставки...")
        self.url_entry.pack(pady=10)
        self.url_entry.bind("<KeyRelease>", self.on_url_change)

        # Превью видео
        self.preview_label = ctk.CTkLabel(self, text="Ожидание ссылки...", width=320, height=180, fg_color="#2b2b2b", corner_radius=10)
        self.preview_label.pack(pady=10)

        # Выбор качества (скрыт по умолчанию)
        self.quality_label = ctk.CTkLabel(self, text="Выберите качество:", font=("Arial", 12))
        self.quality_menu = ctk.CTkOptionMenu(self, values=["Анализ..."])
        
        # Переключатель Видео/Аудио
        self.mode_var = ctk.StringVar(value="video")
        self.mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.mode_frame.pack(pady=10)
        ctk.CTkRadioButton(self.mode_frame, text="Видео (MP4)", variable=self.mode_var, value="video", command=self.toggle_quality_ui).pack(side="left", padx=20)
        ctk.CTkRadioButton(self.mode_frame, text="Аудио (MP3)", variable=self.mode_var, value="audio", command=self.toggle_quality_ui).pack(side="left", padx=20)

        # Кнопка Скачать
        self.download_btn = ctk.CTkButton(self, text="Скачать", font=("Arial", 14, "bold"), command=self.start_download_thread, height=40, width=200)
        self.download_btn.pack(pady=15)

        # Элементы прогресса
        self.progress_label = ctk.CTkLabel(self, text="")
        self.progress_bar = ctk.CTkProgressBar(self, width=450)
        self.status_label = ctk.CTkLabel(self, text="", text_color="yellow")

    def setup_hotkeys(self):
        """Глобальный слушатель физических клавиш (Ctrl + V/M)"""
        while True:
            try:
                # 29 - Ctrl, 47 - V/М
                if keyboard.is_pressed(29) and keyboard.is_pressed(47):
                    if self.focus_get():
                        self.paste_action()
                        while keyboard.is_pressed(47): # Ждем отпускания
                            time.sleep(0.1)
            except: pass
            time.sleep(0.1)

    def paste_action(self):
        try:
            content = self.clipboard_get().strip()
            self.url_entry.delete(0, 'end')
            self.url_entry.insert(0, content)
            self.on_url_change()
        except: pass

    def toggle_quality_ui(self):
        """Показывает или скрывает выбор качества"""
        if self.mode_var.get() == "audio":
            self.quality_label.pack_forget()
            self.quality_menu.pack_forget()
        else:
            # Возвращаем меню качества на экран, если оно прогружено
            if self.quality_menu.cget("values")[0] != "Анализ...":
                self.quality_label.pack(after=self.preview_label)
                self.quality_menu.pack(after=self.quality_label)

    def on_url_change(self, event=None):
        url = self.url_entry.get().strip()
        if len(url) > 10 and ("youtube.com" in url or "youtu.be" in url):
            self.quality_menu.set("Анализ...")
            threading.Thread(target=self.load_video_info, args=(url,), daemon=True).start()

    def load_video_info(self, url):
        """Получает превью и список доступных разрешений"""
        try:
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Загрузка превью
                thumb_url = info.get('thumbnail')
                if thumb_url:
                    res = requests.get(thumb_url, timeout=5, headers={'User-Agent': ydl_opts['user_agent']})
                    img = Image.open(BytesIO(res.content))
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(320, 180))
                    self.preview_label.configure(image=ctk_img, text="")

                # Получение списка качеств
                formats = set()
                for f in info.get('formats', []):
                    if f.get('height') and f.get('vcodec') != 'none':
                        formats.add(f'{f["height"]}p')
                
                if formats:
                    sorted_res = sorted(list(formats), key=lambda x: int(x[:-1]), reverse=True)
                    self.quality_menu.configure(values=sorted_res)
                    self.quality_menu.set(sorted_res[0])
                    self.toggle_quality_ui()
        except Exception as e:
            self.quality_menu.set("Ошибка анализа")
            print(f"Error: {e}")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%','')
            try:
                val = float(p) / 100
                self.progress_bar.set(val)
                self.progress_label.configure(text=f"Загрузка: {int(float(p))}%")
            except: pass

    def download(self):
        url = self.url_entry.get().strip()
        if not url: return

        self.status_label.pack(pady=5); self.progress_label.pack(); self.progress_bar.pack(pady=10)
        self.download_btn.configure(state="disabled")

        ffmpeg_path = os.path.join(sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(__file__), 'ffmpeg.exe')
        res = self.quality_menu.get().replace("p", "")

        ydl_opts = {
            'outtmpl': os.path.join(os.path.expanduser('~'), 'Downloads', '%(title)s.%(ext)s'),
            'ffmpeg_location': ffmpeg_path if os.path.exists(ffmpeg_path) else None,
            'progress_hooks': [self.progress_hook],
        }

        if self.mode_var.get() == 'audio':
            ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]})
        else:
            ydl_opts.update({
                'format': f'bestvideo[height<={res}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res}][ext=mp4]',
                'merge_output_format': 'mp4'
            })

        try:
            self.status_label.configure(text="Процесс пошел...", text_color="yellow")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.status_label.configure(text="Готово! Файл в Загрузках", text_color="green")
            self.url_entry.delete(0, 'end')
        except:
            self.status_label.configure(text="Ошибка загрузки", text_color="red")
        finally:
            self.download_btn.configure(state="normal")
            self.after(5000, self.hide_status)

    def hide_status(self):
        self.status_label.pack_forget(); self.progress_label.pack_forget(); self.progress_bar.pack_forget()

    def start_download_thread(self):
        threading.Thread(target=self.download, daemon=True).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()