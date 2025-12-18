# -*- coding: utf-8 -*-
"""
Created on Tue Dec 16 14:31:27 2025

@author: Chongrui Xi
"""

import os
import subprocess
import time
from pathlib import Path

# ============ 配置 ============
INPUT_FOLDER = "."          
OUTPUT_FOLDER = "音频输出"
OUTPUT_FORMAT = "mp3"       # 可选: mp3, aac, wav, flac
QUALITY = "high"            # 可选: high, medium, low

# 质量设置
QUALITY_SETTINGS = {
    "mp3": {
        "high": ["-acodec", "libmp3lame", "-q:a", "0"],      # ~245 kbps
        "medium": ["-acodec", "libmp3lame", "-q:a", "4"],    # ~165 kbps
        "low": ["-acodec", "libmp3lame", "-q:a", "7"],       # ~100 kbps
    },
    "aac": {
        "high": ["-acodec", "aac", "-b:a", "256k"],
        "medium": ["-acodec", "aac", "-b:a", "128k"],
        "low": ["-acodec", "aac", "-b:a", "64k"],
    },
    "wav": {
        "high": ["-acodec", "pcm_s16le"],    # 无损
        "medium": ["-acodec", "pcm_s16le"],
        "low": ["-acodec", "pcm_s16le"],
    },
    "flac": {
        "high": ["-acodec", "flac"],         # 无损压缩
        "medium": ["-acodec", "flac"],
        "low": ["-acodec", "flac"],
    }
}

def format_size(bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"

def format_time(seconds):
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        return f"{int(seconds//60)}分{int(seconds%60)}秒"
    else:
        return f"{int(seconds//3600)}时{int((seconds%3600)//60)}分"

def check_ffmpeg():
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            text=True
        )
        return True
    except FileNotFoundError:
        return False

def extract_audio(input_file, output_file, format_type, quality):
    quality_args = QUALITY_SETTINGS[format_type][quality]
    
    cmd = [
        "ffmpeg",
        "-i", str(input_file),
        "-vn",                  
        *quality_args,
        "-y",              
        str(output_file)
    ]
    
    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True
    )
    
    return result.returncode == 0

def main():
    print("=" * 50)
    print("🎵 视频音频批量提取工具")
    print("=" * 50)
    
    # 检查 FFmpeg
    if not check_ffmpeg():
        print("\n 错误：未找到 FFmpeg！")
        print("请先安装 FFmpeg 并添加到系统 PATH")
        print("下载地址：https://www.gyan.dev/ffmpeg/builds/")
        input("\n按回车退出...")
        return
    
    print("FFmpeg 已就绪")
    
    # 设置路径
    input_path = Path(INPUT_FOLDER)
    output_path = input_path / OUTPUT_FOLDER
    output_path.mkdir(exist_ok=True)
    
    # 查找所有视频文件
    video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv']
    video_files = []
    for ext in video_extensions:
        video_files.extend(input_path.glob(f"*{ext}"))
    
    video_files = sorted(video_files)
    total_count = len(video_files)
    
    if total_count == 0:
        print(f"\n 在 {input_path.absolute()} 中没有找到视频文件")
        input("\n按回车退出...")
        return
    
    # 计算总大小
    total_size = sum(f.stat().st_size for f in video_files)
    
    print(f"\n 输入文件夹: {input_path.absolute()}")
    print(f" 输出文件夹: {output_path.absolute()}")
    print(f" 找到视频: {total_count} 个")
    print(f" 总大小: {format_size(total_size)}")
    print(f" 输出格式: {OUTPUT_FORMAT.upper()} ({QUALITY})")
    print()
    
    input("按回车开始处理...")
    print()
    
    # 开始处理
    start_time = time.time()
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for i, video_file in enumerate(video_files, 1):
        output_file = output_path / f"{video_file.stem}.{OUTPUT_FORMAT}"
        
        # 进度显示
        progress = i / total_count * 100
        file_size = format_size(video_file.stat().st_size)
        
        print(f"[{i}/{total_count}] ({progress:.0f}%) 处理: {video_file.name}")
        print(f"         大小: {file_size}")
        
        # 检查是否已存在
        if output_file.exists():
            print(f"           已存在，跳过")
            skip_count += 1
            print()
            continue
        
        # 提取音频
        file_start = time.time()
        success = extract_audio(video_file, output_file, OUTPUT_FORMAT, QUALITY)
        file_time = time.time() - file_start
        
        if success:
            output_size = format_size(output_file.stat().st_size)
            print(f"          完成！耗时: {format_time(file_time)}，输出: {output_size}")
            success_count += 1
        else:
            print(f"          失败！")
            fail_count += 1
        
        print()
    
    # 完成统计
    total_time = time.time() - start_time
    output_total_size = sum(f.stat().st_size for f in output_path.glob(f"*.{OUTPUT_FORMAT}"))
    
    print("=" * 50)
    print(" 处理完成！")
    print("=" * 50)
    print(f" 成功: {success_count} 个")
    print(f"  跳过: {skip_count} 个")
    print(f" 失败: {fail_count} 个")
    print(f"  总耗时: {format_time(total_time)}")
    print(f" 输出总大小: {format_size(output_total_size)}")
    print(f" 输出位置: {output_path.absolute()}")
    print()
    input("按回车退出...")

if __name__ == "__main__":
    main()
    