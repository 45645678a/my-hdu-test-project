import os
import time
from pathlib import Path
from google import genai
from google.genai import types

# ============ 配置 ============
API_KEY = "   "
MODEL = "gemini-2.5-pro"

# 脚本所在目录
SCRIPT_DIR = Path(__file__).parent


INPUT_FOLDER = SCRIPT_DIR / "音频输出"      
OUTPUT_FOLDER = SCRIPT_DIR / "文字总结"     
client = genai.Client(api_key=API_KEY)
stats = {"success": 0, "failed": 0, "total_tokens": 0}


def cleanup_uploaded_files():
    print(" 检查残留的上传文件...")
    try:
        files = list(client.files.list())
        if not files:
            print("   没有残留文件")
            return
        
        print(f"   发现 {len(files)} 个残留文件，正在清理...")
        for f in files:
            try:
                client.files.delete(name=f.name)
                print(f"   ✓ 删除: {f.display_name or f.name}")
            except Exception as e:
                print(f"   ✗ 删除失败 {f.name}: {e}")
        print("    清理完成")
    except Exception as e:
        print(f"    清理时出错: {e}")
    print()


def process_audio(audio_path: Path, index: int, total: int) -> dict:
    """处理单个音频文件"""
    
    print(f"[{index}/{total}] {audio_path.name} - 开始处理...")
    
    output_file = OUTPUT_FOLDER / f"{audio_path.stem}.md"
    
    if output_file.exists():
        print(f"[{index}/{total}] {audio_path.name} -  已存在，跳过")
        stats["success"] += 1
        return {"status": "skipped", "file": audio_path.name}
    
    uploaded_file = None
    
    try:
        print(f"[{index}/{total}] {audio_path.name} - 上传中...")
        uploaded_file = client.files.upload(file=audio_path)
        
        while uploaded_file.state == "PROCESSING":
            time.sleep(2)
            uploaded_file = client.files.get(name=uploaded_file.name)
        
        if uploaded_file.state == "FAILED":
            raise Exception("文件处理失败")
        
        print(f"[{index}/{total}] {audio_path.name} - 分析中...")
        
        prompt = """      """
        
        # 生成内容
        response = client.models.generate_content(
            model=MODEL,
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_uri(
                            file_uri=uploaded_file.uri,
                            mime_type=uploaded_file.mime_type
                        ),
                        types.Part.from_text(text=prompt)
                    ]
                )
            ]
        )
        
        # 清理上传文件
        try:
            client.files.delete(name=uploaded_file.name)
        except:
            pass
        
        # 保存结果
        tokens = response.usage_metadata.total_token_count if response.usage_metadata else 0
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# {audio_path.stem}\n\n")
            f.write(response.text)
        
        print(f"[{index}/{total}] {audio_path.name} -  完成！Token: {tokens}")
        
        stats["success"] += 1
        stats["total_tokens"] += tokens
        
        return {"status": "success", "file": audio_path.name, "tokens": tokens}
        
    except Exception as e:
        print(f"[{index}/{total}] {audio_path.name} -  失败: {e}")
        stats["failed"] += 1
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except:
                pass
        
        return {"status": "failed", "file": audio_path.name, "error": str(e)}


def generate_exam_summary():
    """汇总所有课程的考试重点"""
    
    print(" 正在生成考试重点汇总...")
    
    # 读取所有已生成的笔记
    all_notes = []
    for md_file in sorted(OUTPUT_FOLDER.glob("*.md")):
        if md_file.name == "【期末复习汇总】.md":
            continue
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
            all_notes.append(f"### {md_file.stem}\n\n{content}")
    
    if not all_notes:
        print("  没有找到课程笔记")
        return
    
    combined_notes = "\n\n---\n\n".join(all_notes)
    
    prompt = """   """
            
    
    response = client.models.generate_content(
        model=MODEL,
        contents=[prompt]
    )
    
    # 保存汇总文件
    summary_file = OUTPUT_FOLDER / "【期末复习汇总】.md"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("#  期末考试复习汇总\n\n")
        f.write(f"生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        f.write(response.text)
    
    print(f"   已生成: {summary_file.name}")


def main():
    # 重置统计
    stats["success"] = 0
    stats["failed"] = 0
    stats["total_tokens"] = 0
    
    print("=" * 50)
    print("考试重点提取")
    print("=" * 50)
    
    # 检查输入文件夹是否存在
    if not INPUT_FOLDER.exists():
        print(f" 找不到音频文件夹: {INPUT_FOLDER}")
        print("请确保 '音频输出' 文件夹存在且包含音频文件")
        input("\n按回车退出...")
        return
    
    # 创建输出目录
    OUTPUT_FOLDER.mkdir(exist_ok=True)
    
    cleanup_uploaded_files()
    
    audio_files = []
    for ext in ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']:
        audio_files.extend(INPUT_FOLDER.glob(f"*{ext}"))
    
    audio_files = sorted(audio_files)
    total = len(audio_files)
    
    if total == 0:
        print(f" 在 {INPUT_FOLDER} 中没有找到音频文件")
        input("\n按回车退出...")
        return
    
    print(f" 音频目录: {INPUT_FOLDER}")
    print(f" 输出目录: {OUTPUT_FOLDER}")
    print(f" 找到音频: {total} 个")
    print()
    
    for i, f in enumerate(audio_files, 1):
        if i <= 10 or i > total - 3:
            print(f"   {i:2d}. {f.name}")
        elif i == 11:
            print(f"   ... 省略 {total - 13} 个 ...")
    print()
    
    # 选择从第几个开始
    start_from = input(f"从第几个开始？(1-{total}，直接回车从第1个开始): ").strip()
    if start_from == "":
        start_index = 1
    else:
        try:
            start_index = int(start_from)
            if start_index < 1 or start_index > total:
                print(f" 输入无效，从第1个开始")
                start_index = 1
        except ValueError:
            print(f" 输入无效，从第1个开始")
            start_index = 1
    
    print(f"\n 从第 {start_index} 个开始处理（{audio_files[start_index-1].name}）\n")
    
    start_time = time.time()
    
    # 顺序处理所有音频（从指定位置开始）
    for i, audio_file in enumerate(audio_files, 1):
        if i < start_index:
            continue
        process_audio(audio_file, i, total)
        print()  # 空行分隔
    
    elapsed_time = time.time() - start_time
    
    # 生成汇总文档
    if stats["success"] > 0:
        print()
        try:
            generate_exam_summary()
        except Exception as e:
            print(f"   汇总生成失败: {e}")
    
    print()
    print("=" * 50)
    print(f" 完成！成功 {stats['success']} / 失败 {stats['failed']}")
    print(f" 总 Token: {stats['total_tokens']}")
    print(f" 总耗时: {elapsed_time:.1f} 秒")
    print(f" 结果在: {OUTPUT_FOLDER}")
    print()
    print(" 生成的文件：")
    print("   - 每节课的笔记: xxx.md")
    print("   - 期末复习汇总: 【期末复习汇总】.md")
    input("\n按回车退出...")


if __name__ == "__main__":
    main()