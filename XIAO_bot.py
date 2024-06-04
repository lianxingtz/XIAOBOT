from flask import Flask, render_template, Response
import cv2
import threading
import webbrowser
import tkinter as tk
import queue
import pyautogui
from PIL import Image, ImageTk
import shutil
from tkinter import messagebox, filedialog, ttk
from tkinter.scrolledtext import ScrolledText
import socket
import pickle
import os
import numpy as np
from pynput import keyboard

VERSION = "0.3.0"  # 更新版本号

app = Flask(__name__)

class GameBot:
    def __init__(self, game_url, log_queue, status_label, progress_label):
        self.game_url = game_url
        self.running = False
        self.log_queue = log_queue
        self.status_label = status_label
        self.progress_label = progress_label
        self.display_screen = True
        self.frame = None
        self.operations_log = []
        self.load_operations_log()

    # 启动游戏
    def start_game(self):
        self.log_queue.put(f"打开游戏网址 {self.game_url}")
        webbrowser.open(self.game_url)  # 打开游戏网址
        self.running = True
        self.update_status_label("脚本已控制游戏角色")

    # 捕获屏幕截图
    def capture_screen(self):
        screenshot = pyautogui.screenshot()
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        return screenshot

    # 检测屏幕中的障碍物
    def detect_obstacles(self, screen):
        gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 50 and h > 50:
                return True, (x, y, w, h)
        return False, None

    # 避免障碍物
    def avoid_obstacles(self):
        self.update_status_label("脚本正在游戏并避免障碍物")
        while self.running:
            screen = self.capture_screen()
            obstacle_detected, obstacle_coords = self.detect_obstacles(screen)
            if obstacle_detected:
                self.log_queue.put(f"检测到障碍物在 {obstacle_coords}")
                self.operations_log.append(('press', 'space'))
                pyautogui.press('space')
            if self.display_screen:
                self.log_queue.put(("SCREEN", screen))
            self.frame = screen
            self.update_progress_label("Running...")

    # 停止脚本
    def stop(self):
        self.running = False
        self.update_progress_label("Stopped")
        self.save_operations_log()

    # 更新状态标签
    def update_status_label(self, text):
        self.log_queue.put(("STATUS", text))

    # 更新进度标签
    def update_progress_label(self, text):
        self.log_queue.put(("PROGRESS", text))

    # 保存操作逻辑
    def save_operations_log(self, filename='operations_log.pkl'):
        with open(filename, 'wb') as f:
            pickle.dump(self.operations_log, f)
        self.log_queue.put("操作逻辑已保存到文件")

    # 加载操作逻辑
    def load_operations_log(self, filename='operations_log.pkl'):
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                self.operations_log = pickle.load(f)
            self.log_queue.put("操作逻辑已从文件加载")
        else:
            self.operations_log = []
            self.log_queue.put("没有找到操作逻辑文件，使用空逻辑库")

    # 重放操作逻辑
    def replay_operations(self):
        self.update_status_label("重放操作逻辑")
        for operation in self.operations_log:
            if operation[0] == 'press':
                pyautogui.press(operation[1])
        self.update_status_label("操作逻辑重放完成")

    # 分析视频生成操作逻辑
    def analyze_video(self, video_path):
        cap = cv2.VideoCapture(video_path)
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            obstacle_detected, obstacle_coords = self.detect_obstacles(frame)
            if obstacle_detected:
                self.operations_log.append(('press', 'space'))
        cap.release()
        self.log_queue.put("视频分析完成，操作逻辑已生成")
        self.save_operations_log()

# 记录用户操作
def record_user_operations(game_bot, log_queue):
    def on_press(key):
        try:
            log_queue.put(f'按下: {key.char}')
            game_bot.operations_log.append(('press', key.char))
        except AttributeError:
            log_queue.put(f'按下: {key}')
            game_bot.operations_log.append(('press', str(key)))

    def on_release(key):
        if key == keyboard.Key.esc:
            return False

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

# 运行机器人
def run_bot(game_bot):
    game_bot.start_game()
    game_bot.avoid_obstacles()
    game_bot.stop()  # 停止并保存逻辑

# 更新图像
def update_image(log_queue, label):
    while True:
        message = log_queue.get()
        if isinstance(message, tuple) and message[0] == "SCREEN":
            screen = message[1]
            screen = cv2.cvtColor(screen, cv2.COLOR_BGR2RGB)
            screen_pil = Image.fromarray(screen)
            screen_tk = ImageTk.PhotoImage(screen_pil)
            label.after(0, lambda: label.config(image=screen_tk))
            label.image = screen_tk
        elif isinstance(message, tuple) and message[0] == "STATUS":
            text = message[1]
            label.after(0, lambda: label.config(text=text))
        elif isinstance(message, tuple) and message[0] == "PROGRESS":
            text = message[1]
            label.after(0, lambda: label.config(text=text))

# 更新日志
def update_log(log_queue, log_widget):
    while True:
        message = log_queue.get()
        if not isinstance(message, tuple):
            log_widget.after(0, lambda: log_widget.insert(tk.END, message + "\n"))
            log_widget.after(0, lambda: log_widget.see(tk.END))

# 保存日志
def save_log():
    log_filename = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Log files", "*.log"), ("All files", "*.*")])
    if log_filename:
        shutil.copy('game_bot.log', log_filename)
        messagebox.showinfo("日志已保存", f"日志文件已保存到 {log_filename}")

# 查看日志
def view_log(log_widget):
    try:
        log_widget.delete('1.0', tk.END)
        with open('game_bot.log', 'r') as log_file:
            log_widget.insert(tk.END, log_file.read())
        log_widget.see(tk.END)
    except FileNotFoundError:
        log_widget.insert(tk.END, "日志文件不存在\n")
        log_widget.see(tk.END)

# 启动倒计时
def start_countdown(label, duration, progress_bar, callback):
    def update_progress(value):
        progress_bar['value'] = value

    for i in range(duration, 0, -1):
        label.after(0, lambda i=i: label.config(text=f"{i} 秒后开始..."))
        label.after(0, lambda i=i: update_progress((duration - i) * (100 / duration)))
        time.sleep(1)
    callback()

# 启动GUI界面
def start_gui(game_bot, log_queue, server_address):
    root = tk.Tk()
    root.title(f"游戏机器人界面 v{VERSION}")
    root.configure(bg='lightgray')

    status_label = tk.Label(root, text="游戏机器人已就绪", bg='lightgray', fg='lightgreen', font=("Helvetica", 12))
    status_label.pack()

    screen_label = tk.Label(root)
    screen_label.pack()

    log_widget = ScrolledText(root, height=10, width=50, bg='white', fg='lightgreen')
    log_widget.pack()

    countdown_label = tk.Label(root, text="", bg='lightgray', fg='lightgreen', font=("Helvetica", 12))
    countdown_label.pack()

    progress_bar = ttk.Progressbar(root, length=200, mode='determinate')
    progress_bar.pack()

    progress_label = tk.Label(root, text="进度: 等待中", bg='lightgray', fg='lightgreen', font=("Helvetica", 12))
    progress_label.pack()

    button_frame = tk.Frame(root, bg='lightgray')
    button_frame.pack()

    def start_bot():
        status_label.config(text="游戏机器人运行中...")
        threading.Thread(target=run_bot, args=(game_bot,)).start()
        threading.Thread(target=update_image, args=(log_queue, screen_label)).start()
        threading.Thread(target=update_log, args=(log_queue, log_widget)).start()
        start_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.NORMAL)
        show_screen_button.config(state=tk.NORMAL)

    def stop_bot():
        status_label.config(text="游戏机器人已停止")
        game_bot.stop()
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)
        show_screen_button.config(state=tk.DISABLED)

    def toggle_screen():
        game_bot.display_screen = not game_bot.display_screen
        if game_bot.display_screen:
            show_screen_button.config(text="隐藏屏幕")
        else:
            show_screen_button.config(text="显示屏幕")
            screen_label.config(image='')

    start_button = tk.Button(button_frame, text="启动", command=start_bot, bg='green', fg='white')
    start_button.grid(row=0, column=0, padx=5, pady=5)
    start_button.config(state=tk.NORMAL)

    stop_button = tk.Button(button_frame, text="停止", command=stop_bot, bg='red', fg='white')
    stop_button.grid(row=0, column=1, padx=5, pady=5)
    stop_button.config(state=tk.DISABLED)

    show_screen_button = tk.Button(button_frame, text="隐藏屏幕", command=toggle_screen, bg='gray', fg='white')
    show_screen_button.grid(row=0, column=2, padx=5, pady=5)
    show_screen_button.config(state=tk.DISABLED)

    view_log_button = tk.Button(button_frame, text="查看日志", command=lambda: view_log(log_widget), bg='blue', fg='white')
    view_log_button.grid(row=1, column=0, padx=5, pady=5)

    save_log_button = tk.Button(button_frame, text="保存日志", command=save_log, bg='blue', fg='white')
    save_log_button.grid(row=1, column=1, padx=5, pady=5)

    save_operations_button = tk.Button(button_frame, text="保存操作逻辑", command=game_bot.save_operations_log, bg='blue', fg='white')
    save_operations_button.grid(row=1, column=2, padx=5, pady=5)

    load_operations_button = tk.Button(button_frame, text="加载操作逻辑", command=game_bot.load_operations_log, bg='blue', fg='white')
    load_operations_button.grid(row=1, column=3, padx=5, pady=5)

    replay_operations_button = tk.Button(button_frame, text="重放操作逻辑", command=game_bot.replay_operations, bg='blue', fg='white')
    replay_operations_button.grid(row=1, column=4, padx=5, pady=5)

    analyze_video_button = tk.Button(button_frame, text="分析视频生成逻辑", command=lambda: game_bot.analyze_video('游戏逻辑素材A.mp4'), bg='blue', fg='white')
    analyze_video_button.grid(row=1, column=5, padx=5, pady=5)

    def close_gui():
        stop_bot()
        root.destroy()

    close_button = tk.Button(root, text="关闭", command=close_gui, bg='gray', fg='white')
    close_button.pack(pady=10)

    def show_server_info():
        info_label.config(text=f"访问视频流地址: {server_address}")
        copy_button.pack(pady=5)
        root.after(10000, hide_server_info)

    def hide_server_info():
        info_label.config(text="")
        copy_button.pack_forget()

    def copy_to_clipboard():
        pyperclip.copy(server_address)
        messagebox.showinfo("已复制", "服务器地址已复制到剪贴板。")
        hide_server_info()

    info_label = tk.Label(root, text="", bg='lightgray', fg='lightgreen', font=("Helvetica", 12))
    info_label.pack()

    copy_button = tk.Button(root, text="复制地址", command=copy_to_clipboard, bg='gray', fg='white')
    copy_button.pack_forget()

    show_server_info()

    def start_countdown_and_bot():
        threading.Thread(target=start_countdown, args=(countdown_label, 10, progress_bar, start_bot)).start()

    threading.Thread(target=start_countdown_and_bot).start()

    root.mainloop()

# 生成视频流帧
def generate_frame(game_bot):
    while True:
        if game_bot.frame is not None:
            ret, buffer = cv2.imencode('.jpg', game_bot.frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frame(game_bot),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# 打开默认浏览器并打开服务器地址
def open_browser_default(server_address):
    webbrowser.open(server_address)

if __name__ == "__main__":
    # 创建日志文件（如果不存在）
    if not os.path.exists('game_bot.log'):
        open('game_bot.log', 'w').close()

    log_queue = queue.Queue()
    status_label = tk.Label()
    progress_label = tk.Label()
    game_bot = GameBot(game_url="https://game.playpixiz.io/", log_queue=log_queue, status_label=status_label, progress_label=progress_label)
    
    # 获取本地IP地址
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    server_address = f"http://{local_ip}:8000"

    # 启动Flask服务器
    threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 8000}).start()
    
    # 启动GUI
    threading.Thread(target=start_gui, args=(game_bot, log_queue, server_address)).start()

    # 打开默认浏览器并打开服务器地址
    open_browser_default(server_address)

    # 记录用户操作
    threading.Thread(target=record_user_operations, args=(game_bot, log_queue)).start()
