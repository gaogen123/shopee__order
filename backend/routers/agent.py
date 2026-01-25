from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse
from master_agent import run_agent_generator
import subprocess
import socket
import platform

router = APIRouter(prefix="/api/agent", tags=["agent"])

@router.get("/stream")
async def stream_pdd(query: str, session_id: str = None):
    """
    流式返回拼多多 Agent 的执行结果 (SSE 格式)
    """
    return StreamingResponse(run_agent_generator(query, thread_id=session_id), media_type="text/event-stream")

@router.post("/stop")
async def stop_agent(session_id: str):
    """
    停止指定会话的 Agent 任务
    """
    try:
        import os
        stop_dir = "/tmp/agent_stops"
        if not os.path.exists(stop_dir):
            os.makedirs(stop_dir)
        
        # 创建停止标志文件
        with open(f"{stop_dir}/{session_id}", "w") as f:
            f.write("stop")
            
        return {"success": True, "message": f"已发送停止信号给会话 {session_id}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/browser/status")
async def check_browser_status():
    """
    检查调试浏览器是否在运行（端口 9222）
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 9222))
        sock.close()
        is_running = result == 0
        return {"running": is_running, "port": 9222}
    except Exception as e:
        return {"running": False, "error": str(e)}

@router.post("/browser/start")
async def start_debug_browser():
    """
    启动调试模式的 Chrome 浏览器（端口 9222）
    会先关闭已有的 Chrome 进程，确保使用干净快速的浏览器
    """
    try:
        system = platform.system()
        
        # 先杀掉已运行的 Chrome 进程
        if system == "Darwin":  # macOS
            subprocess.run(["pkill", "-f", "Google Chrome"], capture_output=True)
        elif system == "Windows":
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
        else:  # Linux
            subprocess.run(["pkill", "-f", "chrome"], capture_output=True)
        
        # 等待进程完全退出
        import time
        time.sleep(1)
        
        # 根据操作系统启动 Chrome
        if system == "Darwin":  # macOS
            cmd = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "--remote-debugging-port=9222",
                "--user-data-dir=/tmp/chrome_crawler_profile",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-gpu",
                "--disable-background-networking",
                "--disable-sync",
                "--no-first-run"
            ]
        elif system == "Windows":
            cmd = [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "--remote-debugging-port=9222",
                "--user-data-dir=C:\\temp\\chrome_crawler_profile",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-gpu",
                "--no-first-run"
            ]
        else:  # Linux
            cmd = [
                "google-chrome",
                "--remote-debugging-port=9222",
                "--user-data-dir=/tmp/chrome_crawler_profile",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-gpu",
                "--no-first-run"
            ]
        
        # 启动浏览器进程
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return {"success": True, "message": "调试浏览器已启动（已关闭旧浏览器）"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}
