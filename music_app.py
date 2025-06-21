import os
import time
from tkinter import *
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageFont
from io import BytesIO
import pygame.mixer as mixer
import audio_metadata

# Gradient background with slow color shift (basic simulation)
class AnimatedGradient(Label):
    def __init__(self, parent, width, height, colors, delay=100):
        super().__init__(parent)
        self.width = width
        self.height = height
        self.colors = colors
        self.delay = delay
        self.idx = 0
        self.img = None
        self.animate()

    def create_gradient_img(self, c1, c2):
        base = Image.new('RGB', (self.width, self.height), c1)
        top = Image.new('RGB', (self.width, self.height), c2)
        mask = Image.new('L', (self.width, self.height))
        mask_data = []
        for y in range(self.height):
            mask_data.extend([int(255 * (y / self.height))] * self.width)
        mask.putdata(mask_data)
        base.paste(top, (0, 0), mask)
        return ImageTk.PhotoImage(base)

    def animate(self):
        c1 = self.colors[self.idx % len(self.colors)]
        c2 = self.colors[(self.idx + 1) % len(self.colors)]
        self.img = self.create_gradient_img(c1, c2)
        self.config(image=self.img)
        self.idx += 1
        self.after(self.delay, self.animate)

# Pill-shaped glowing button with hover scale
class GlowButton(Button):
    def __init__(self, master, bg, accent, shape, cmd, **kwargs):
        self.bg = bg
        self.accent = accent
        self.shape = shape
        self.icon_normal = self.make_icon(bg, accent, shape)
        self.icon_hover = self.make_icon(accent, bg, shape)
        super().__init__(master, image=self.icon_normal, bd=0, bg=bg, activebackground=bg,
                         command=cmd, cursor='hand2', **kwargs)
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.scale = 1.0

    def make_icon(self, bg, fg, shape, size=70):
        img = Image.new('RGBA', (size, size), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((0, 0, size, size), radius=size//2, fill=bg)
        # Icon shapes
        if shape == 'play' or shape == 'resume':
            draw.polygon([(size*0.38, size*0.28), (size*0.38, size*0.72), (size*0.72, size*0.5)], fill=fg)
        elif shape == 'pause':
            draw.rounded_rectangle((size*0.33, size*0.28, size*0.42, size*0.72), radius=6, fill=fg)
            draw.rounded_rectangle((size*0.58, size*0.28, size*0.67, size*0.72), radius=6, fill=fg)
        elif shape == 'stop':
            draw.rounded_rectangle((size*0.36, size*0.36, size*0.64, size*0.64), radius=10, fill=fg)
        elif shape == 'folder':
            draw.rectangle((size*0.22, size*0.52, size*0.78, size*0.72), fill=fg)
            draw.rectangle((size*0.32, size*0.44, size*0.46, size*0.52), fill=fg)
        return ImageTk.PhotoImage(img)

    def on_enter(self, e):
        self.config(image=self.icon_hover)
        self.scale = 1.1
        self._resize()

    def on_leave(self, e):
        self.config(image=self.icon_normal)
        self.scale = 1.0
        self._resize()

    def _resize(self):
        # Tkinter buttons don't support scaling directly, so skip or implement if needed
        pass

def make_glow_album_art(img_bytes=None):
    size = 220
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    if img_bytes:
        img = Image.open(BytesIO(img_bytes)).resize((size, size), Image.LANCZOS).convert("RGBA")
    else:
        img = Image.new('RGBA', (size, size), '#232526')
        d = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        text = "No Art"
        w, h = d.textsize(text, font=font)
        d.text(((size - w) / 2, (size - h) / 2), text, fill='#bbb', font=font)
    img.putalpha(mask)
    glow = img.filter(ImageFilter.GaussianBlur(12))
    combined = Image.new('RGBA', (size+40, size+40), (0,0,0,0))
    combined.paste(glow, (20,20), glow)
    combined.paste(img, (0,0), img)
    return ImageTk.PhotoImage(combined)

class MusicPlayer:
    def __init__(self, root):
        self.root = root
        self.root.geometry('540x740')
        self.root.title('🎵 Music Player')
        self.root.resizable(False, False)
        mixer.init()

        # Animated gradient background
        colors = ["#18122B", "#43e97b", "#232526", "#21d4fd"]
        self.bg_label = AnimatedGradient(self.root, 540, 740, colors, delay=150)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # Album art
        self.album_art_label = Label(self.root, bd=0, bg='#18122B')
        self.album_art_label.place(relx=0.5, y=60, anchor="n")
        self.album_art = make_glow_album_art()
        self.album_art_label.config(image=self.album_art)
        self.album_art_label.image = self.album_art

        # Song title
        self.current_song = StringVar(value='No song selected')
        self.song_label = Label(self.root, textvariable=self.current_song, font=('Montserrat', 20, 'bold'), fg='#fff', bg='#18122B')
        self.song_label.place(relx=0.5, y=320, anchor='center')

        # Song status
        self.song_status = StringVar(value='Welcome! Load a directory to start.')
        self.status_label = Label(self.root, textvariable=self.song_status, font=('Montserrat', 11, 'italic'), fg='#43e97b', bg='#18122B')
        self.status_label.place(relx=0.5, y=355, anchor='center')

        # Neon control buttons with hover effect
        btn_y = 400
        btns_info = [
            ('#232526', '#43e97b', 'play', self.play_song, 70),
            ('#232526', '#f7971e', 'pause', self.pause_song, 160),
            ('#232526', '#fd1d1d', 'stop', self.stop_song, 250),
            ('#232526', '#21d4fd', 'resume', self.resume_song, 340),
            ('#232526', '#b721ff', 'folder', self.load_directory, 430)
        ]
        self.btns = []
        for bg, accent, shape, cmd, x in btns_info:
            btn = GlowButton(self.root, bg, accent, shape, cmd)
            btn.place(x=x, y=btn_y)
            self.btns.append(btn)
        self.btns[3].config(state=DISABLED)  # resume initially disabled

        # Volume slider
        self.volume_slider = Scale(self.root, from_=100, to=0, orient=VERTICAL, command=self.set_volume,
                                   length=120, bg='#18122B', fg='#43e97b', troughcolor='#b2fefa',
                                   highlightthickness=0, bd=0, sliderrelief=FLAT)
        self.volume_slider.set(30)
        self.volume_slider.place(x=470, y=90)

        # Playlist card with shadow
        self.playlist_card = Frame(self.root, bg='#232526', bd=0, highlightbackground='#43e97b', highlightthickness=2)
        self.playlist_card.place(relx=0.5, y=540, anchor='center', width=440, height=150)
        self.playlist = Listbox(self.playlist_card, font=('Montserrat', 12), selectbackground='#43e97b',
                                bg='#232526', fg='#fff', bd=0, highlightthickness=0,
                                activestyle='none', height=5, relief=FLAT)
        self.playlist.pack(side=LEFT, fill=BOTH, expand=True, padx=(12,0), pady=12)
        self.scroll_bar = Scrollbar(self.playlist_card, orient=VERTICAL, command=self.playlist.yview)
        self.scroll_bar.pack(side=RIGHT, fill=Y, pady=12)
        self.playlist.config(yscrollcommand=self.scroll_bar.set)

        # Time elapsed label
        self.duration = "00:00"
        self.duration_label = Label(self.root, text='Time Elapsed: 00:00 / 00:00', font=('Montserrat', 12), fg='#fff', bg='#18122B')
        self.duration_label.place(relx=0.5, y=710, anchor='center')

        self.metadata = None
        self.playing_file = None

        self.update_time()

    # All other methods same as before (load_directory, play_song, stop_song, pause_song, resume_song, set_volume, update_time, show_artwork)
    # For brevity, reuse the previous implementations here.

    def load_directory(self):
        directory = filedialog.askdirectory(title="Select Music Directory")
        if not directory:
            return
        self.playlist.delete(0, END)
        for file in os.listdir(directory):
            if file.lower().endswith('.mp3'):
                self.playlist.insert(END, os.path.join(directory, file))
        self.song_status.set("Directory loaded. Select a song to play.")
        self.current_song.set("No song selected")
        self.duration = "00:00"
        self.duration_label.config(text='Time Elapsed: 00:00 / 00:00')
        self.album_art = make_glow_album_art()
        self.album_art_label.config(image=self.album_art)
        self.album_art_label.image = self.album_art

    def play_song(self):
        try:
            selected = self.playlist.curselection()
            if not selected:
                self.song_status.set("Please select a song!")
                return
            song_path = self.playlist.get(selected[0])
            self.playing_file = song_path
            song_name = os.path.basename(song_path)
            if len(song_name) > 40:
                song_name = song_name[:35] + '...'
            self.current_song.set(song_name)
            mixer.music.load(song_path)
            mixer.music.play()
            try:
                self.metadata = audio_metadata.load(song_path)
                song_len = self.metadata.streaminfo['duration']
            except Exception:
                song_len = 0
            self.duration = time.strftime('%M:%S', time.gmtime(song_len))
            self.song_status.set("Playing")
            self.btns[3].config(state=NORMAL)
            self.show_artwork()
        except Exception as e:
            messagebox.showerror("Error", f"Could not play song:\n{e}")

    def stop_song(self):
        mixer.music.stop()
        self.song_status.set("Stopped")
        self.btns[3].config(state=DISABLED)
        self.duration_label.config(text=f"Time Elapsed: 00:00 / {self.duration}")

    def pause_song(self):
        mixer.music.pause()
        self.song_status.set("Paused")

    def resume_song(self):
        mixer.music.unpause()
        if self.song_status.get() in ("Stopped", "No song selected", "Please select a song!"):
            self.song_status.set("Please Select a song!")
        else:
            self.song_status.set("Playing")

    def set_volume(self, x):
        value = self.volume_slider.get()
        mixer.music.set_volume(value / 100)

    def update_time(self):
        if mixer.music.get_busy():
            current_time = mixer.music.get_pos() / 1000
            converted_current_time = time.strftime('%M:%S', time.gmtime(current_time))
            self.duration_label.config(text=f"Time Elapsed: {converted_current_time} / {self.duration}")
        else:
            if self.song_status.get() == "Stopped":
                self.duration_label.config(text=f"Time Elapsed: 00:00 / {self.duration}")
        self.root.after(1000, self.update_time)

    def show_artwork(self):
        try:
            if self.metadata and getattr(self.metadata, 'pictures', []):
                artwork = self.metadata.pictures[0].data
                art_img = make_glow_album_art(artwork)
                self.album_art_label.config(image=art_img)
                self.album_art_label.image = art_img
            else:
                self.album_art = make_glow_album_art()
                self.album_art_label.config(image=self.album_art)
                self.album_art_label.image = self.album_art
        except Exception:
            self.album_art = make_glow_album_art()
            self.album_art_label.config(image=self.album_art)
            self.album_art_label.image = self.album_art

if __name__ == "__main__":
    root = Tk()
    app = MusicPlayer(root)
    root.mainloop()
