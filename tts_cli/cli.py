from __future__ import annotations

import argparse
import asyncio
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="TTS-CLI",
        description="读取本地文本文件并执行语音合成。",
    )
    parser.add_argument("file", nargs="?", help="要读取的本地文本文件，例如 ./notes.md")
    parser.add_argument(
        "--backend",
        choices=["auto", "pyttsx3", "edge"],
        default="auto",
        help="TTS 后端。auto 会优先尝试 pyttsx3，其次 edge。",
    )
    parser.add_argument("--speed", type=int, default=180, help="语速，默认 180。")
    parser.add_argument("--lang", default="zh-CN", help="语言代码，默认 zh-CN。")
    parser.add_argument("--voice", help="指定语音名称或 ID。")
    parser.add_argument("--style", help="语音风格，仅 edge 后端支持。")
    parser.add_argument("--pitch", default="+0Hz", help="音高，仅 edge 后端支持。")
    parser.add_argument(
        "--output",
        help="输出音频文件路径。pyttsx3 常见为 .aiff/.wav，edge 推荐 .mp3。",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="文本文件编码，默认 utf-8。",
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="列出当前后端可用的语音。",
    )
    parser.add_argument(
        "--play",
        action="store_true",
        help="生成后直接播放音频。macOS 默认使用 afplay。",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        backend = resolve_backend(args.backend)
        runner = create_backend(backend)
    except RuntimeError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2

    if args.list_voices:
        voices = runner.list_voices(args.lang)
        if not voices:
            print("未找到匹配的语音。")
            return 1
        print("可用语音：")
        for item in voices:
            print(f"- {item}")
        return 0

    if not args.file:
        parser.print_help()
        return 1

    try:
        text = read_text_file(Path(args.file), args.encoding)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"读取文件失败：{exc}", file=sys.stderr)
        return 1

    temp_output: str | None = None
    output_path = args.output
    if args.play and backend == "edge" and not output_path:
        fd, temp_output = tempfile.mkstemp(prefix="tts-cli-", suffix=".mp3")
        os.close(fd)
        output_path = temp_output

    try:
        runner.run(
            text=text,
            speed=args.speed,
            lang=args.lang,
            voice=args.voice,
            style=args.style,
            pitch=args.pitch,
            output=output_path,
        )
    except RuntimeError as exc:
        print(f"执行失败：{exc}", file=sys.stderr)
        cleanup_temp_file(temp_output)
        return 1

    if args.play and output_path:
        try:
            play_audio(output_path)
        except RuntimeError as exc:
            print(f"播放失败：{exc}", file=sys.stderr)
            cleanup_temp_file(temp_output)
            return 1

    if args.output:
        print(f"已生成音频文件：{args.output}")
    elif output_path and args.play:
        print("已生成临时音频并完成播放。")
    else:
        print("朗读完成。")
    cleanup_temp_file(temp_output)
    return 0


def read_text_file(path: Path, encoding: str) -> str:
    if not path.exists():
        raise ValueError(f"文件不存在：{path}")
    if not path.is_file():
        raise ValueError(f"不是文件：{path}")
    text = path.read_text(encoding=encoding).strip()
    if not text:
        raise ValueError("文件内容为空。")
    return text


def resolve_backend(requested: str) -> str:
    if requested != "auto":
        ensure_dependency(requested)
        return requested
    if has_dependency("pyttsx3"):
        return "pyttsx3"
    if has_dependency("edge_tts"):
        return "edge"
    raise RuntimeError("未安装可用 TTS 后端。请先安装 pyttsx3，或安装 '.[edge]'。")


def create_backend(name: str) -> "BaseBackend":
    if name == "pyttsx3":
        return Pyttsx3Backend()
    if name == "edge":
        return EdgeTTSBackend()
    raise RuntimeError(f"不支持的后端：{name}")


def has_dependency(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def ensure_dependency(backend: str) -> None:
    module_name = "pyttsx3" if backend == "pyttsx3" else "edge_tts"
    if not has_dependency(module_name):
        if backend == "pyttsx3":
            raise RuntimeError("缺少 pyttsx3。请执行: python3 -m pip install -e .")
        raise RuntimeError("缺少 edge-tts。请执行: python3 -m pip install -e '.[edge]'")


def play_audio(path: str) -> None:
    player = shutil.which("afplay")
    if player is None:
        raise RuntimeError("当前系统未找到 afplay，暂不支持直接播放。")
    print(f"正在播放：{path}")
    try:
        subprocess.run([player, path], check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"播放器退出码异常：{exc.returncode}") from exc


def cleanup_temp_file(path: str | None) -> None:
    if not path:
        return
    temp_path = Path(path)
    if temp_path.exists():
        temp_path.unlink()


class BaseBackend:
    def list_voices(self, lang: str) -> list[str]:
        raise NotImplementedError

    def run(
        self,
        *,
        text: str,
        speed: int,
        lang: str,
        voice: str | None,
        style: str | None,
        pitch: str,
        output: str | None,
    ) -> None:
        raise NotImplementedError


class Pyttsx3Backend(BaseBackend):
    def __init__(self) -> None:
        import pyttsx3

        self.engine = pyttsx3.init()

    def list_voices(self, lang: str) -> list[str]:
        voices: list[str] = []
        for voice in self.engine.getProperty("voices"):
            if matches_lang(voice, lang):
                voices.append(f"{voice.id} ({voice.name})")
        return voices

    def run(
        self,
        *,
        text: str,
        speed: int,
        lang: str,
        voice: str | None,
        style: str | None,
        pitch: str,
        output: str | None,
    ) -> None:
        selected = self._pick_voice(lang, voice)
        if selected is not None:
            self.engine.setProperty("voice", selected.id)
        self.engine.setProperty("rate", speed)
        if style:
            print("提示：pyttsx3 后端暂不支持 style，已忽略。")
        if pitch != "+0Hz":
            print("提示：pyttsx3 后端暂不支持 pitch，已忽略。")
        if output:
            self.engine.save_to_file(text, output)
        else:
            self.engine.say(text)
        self.engine.runAndWait()

    def _pick_voice(self, lang: str, voice_name: str | None) -> Any | None:
        voices = self.engine.getProperty("voices")
        if voice_name:
            for voice in voices:
                if voice_name in {voice.id, voice.name}:
                    return voice
            raise RuntimeError(f"未找到指定语音：{voice_name}")
        for voice in voices:
            if matches_lang(voice, lang):
                return voice
        return voices[0] if voices else None


class EdgeTTSBackend(BaseBackend):
    def __init__(self) -> None:
        import edge_tts

        self.edge_tts = edge_tts

    def list_voices(self, lang: str) -> list[str]:
        async def _load() -> list[str]:
            items = await self.edge_tts.list_voices()
            return [
                f"{item['ShortName']} ({item['Gender']}, {item['Locale']})"
                for item in items
                if item["Locale"].lower().startswith(lang.lower())
            ]

        return asyncio.run(_load())

    def run(
        self,
        *,
        text: str,
        speed: int,
        lang: str,
        voice: str | None,
        style: str | None,
        pitch: str,
        output: str | None,
    ) -> None:
        if not output:
            raise RuntimeError("edge 后端当前要求提供 --output，例如 out.mp3")
        selected_voice = voice or guess_edge_voice(lang)
        rate = speed_to_edge_rate(speed)

        async def _save() -> None:
            communicate = self.edge_tts.Communicate(
                text=text,
                voice=selected_voice,
                rate=rate,
                pitch=pitch,
            )
            if style:
                communicate = self.edge_tts.Communicate(
                    text=apply_style(text, style),
                    voice=selected_voice,
                    rate=rate,
                    pitch=pitch,
                )
            await communicate.save(output)

        asyncio.run(_save())


def matches_lang(voice: Any, lang: str) -> bool:
    target = lang.lower().replace("_", "-")
    voice_id = getattr(voice, "id", "").lower()
    voice_name = getattr(voice, "name", "").lower()
    languages = [str(item).lower() for item in getattr(voice, "languages", [])]
    return any(target in item for item in languages) or target in voice_id or target in voice_name


def speed_to_edge_rate(speed: int) -> str:
    delta = int(((speed - 180) / 180) * 100)
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta}%"


def guess_edge_voice(lang: str) -> str:
    mapping = {
        "zh-cn": "zh-CN-XiaoxiaoNeural",
        "zh-tw": "zh-TW-HsiaoChenNeural",
        "en-us": "en-US-AriaNeural",
        "ja-jp": "ja-JP-NanamiNeural",
    }
    return mapping.get(lang.lower(), "zh-CN-XiaoxiaoNeural")


def apply_style(text: str, style: str) -> str:
    print(f"提示：当前 edge 后端暂未直接应用 style='{style}'，已按默认风格合成。")
    return text


if __name__ == "__main__":
    raise SystemExit(main())
