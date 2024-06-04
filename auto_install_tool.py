import os
import subprocess
import sys
import shutil
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
from tkinter import ttk
from threading import Thread
import socket
import pyperclip

# 自动运行安装工具版本号
TOOL_VERSION = "0.3.6"

# 运行命令并返回输出
def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = process.communicate()
    return out.decode('utf-8', errors='ignore'), err.decode('utf-8', errors='ignore')

# 检查并安装所需的Python包
def check_and_install_package(pip_path, package):
    try:
        out, err = run_command(f"{pip_path} show {package}")
        if "Name: " not in out:
            log_message(f"{package} 未安装。正在安装...")
            out, err = run_command(f"{pip_path} install {package}")
            if err:
                log_message(f"安装 {package} 时出错: {err}")
                return False
            else:
                log_message(f"{package} 安装成功。")
        else:
            log_message(f"{package} 已安装。")
        return True
    except Exception as e:
        log_message(f"检查/安装 {package} 时发生异常: {str(e)}")
        return False

# 安装所有依赖包
def install_dependencies(env_path):
    pip_path = os.path.join(env_path, 'Scripts', 'pip') if os.name == 'nt' else os.path.join(env_path, 'bin', 'pip')
    packages = ['Flask', 'opencv-python', 'pyautogui', 'pillow', 'pyperclip', 'pynput']
    for package in packages:
        success = check_and_install_package(pip_path, package)
        if not success:
            log_message(f"重试安装 {package}...")
            check_and_install_package(pip_path, package)

# 创建虚拟环境
def create_virtual_environment(path):
    run_command(f"{sys.executable} -m venv {path}")

# 复制脚本文件
def copy_script(script_path, target_path):
    shutil.copy(script_path, target_path)

# 启动游戏机器人
def start_game_bot(env_path, target_path):
    python_path = os.path.join(env_path, 'Scripts', 'python') if os.name == 'nt' else os.path.join(env_path, 'bin', 'python')
    script_path = os.path.join(target_path, 'XIAO_bot.py')
    run_command(f"{python_path} {script_path}")

# 启动服务器线程
def start_server_thread(env_path, target_path):
    thread = Thread(target=start_game_bot, args=(env_path, target_path))
    thread.start()

# 日志消息
def log_message(message):
    log_text.insert(tk.END, message + "\n")
    log_text.see(tk.END)

# 部署过程
def deploy():
    log_message("开始部署...")

    try:
        # 检查并安装虚拟环境包
        try:
            import venv
        except ImportError:
            log_message("venv 未安装。正在安装...")
            run_command(f"{sys.executable} -m pip install virtualenv")
            log_message("venv 安装成功。")

        # 创建虚拟环境
        env_path = os.path.join(os.getcwd(), 'venv')
        log_message("正在创建虚拟环境...")
        create_virtual_environment(env_path)
        log_message("虚拟环境已创建。")

        # 安装依赖
        log_message("正在安装依赖包...")
        install_dependencies(env_path)
        log_message("依赖包已安装。")

        # 复制脚本
        script_path = os.path.join(os.getcwd(), 'XIAO_bot.py')
        target_path = os.path.join(os.getcwd(), 'deployment_directory')
        os.makedirs(target_path, exist_ok=True)
        log_message(f"正在将脚本复制到 {target_path}...")
        copy_script(script_path, target_path)
        log_message("脚本已复制。")

        # 启动服务器
        log_message("正在启动游戏机器人...")
        start_server_thread(env_path, target_path)
        log_message("游戏机器人已启动。")

        # 获取本地IP地址
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        server_address = f"http://{local_ip}:8000"
        log_message(f"访问视频流地址: {server_address}")

        def copy_to_clipboard():
            pyperclip.copy(server_address)
            messagebox.showinfo("已复制", "服务器地址已复制到剪贴板。")

        copy_button = tk.Button(frame, text="复制地址", command=copy_to_clipboard, bg='gray', fg='white')
        copy_button.pack(pady=5)

        # 自动启动机器人服务
        log_message("启动机器人服务中...")
        run_command(f"start {server_address}")

        # 自动运行 XIAO_bot.py 脚本
        log_message("正在运行 XIAO_bot.py 脚本...")
        start_game_bot(env_path, target_path)

    except Exception as e:
        log_message(f"部署失败: {str(e)}")
        messagebox.showerror("部署错误", f"部署失败: {str(e)}")

# 主函数，启动GUI
def main():
    global log_text, frame

    root = tk.Tk()
    root.title(f"自动运行安装工具 v{TOOL_VERSION}")

    frame = tk.Frame(root, padx=10, pady=10)
    frame.pack(padx=10, pady=10)

    log_text = tk.Text(frame, height=15, width=60)
    log_text.pack()

    deploy_button = tk.Button(frame, text="部署", command=deploy, bg='green', fg='white')
    deploy_button.pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()
