from pathlib import Path

import tts_cli.cli as cli

from tts_cli.cli import build_parser, read_text_file, speed_to_edge_rate


def test_parser_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args(["demo.md"])
    assert args.file == "demo.md"
    assert args.backend == "auto"
    assert args.speed == 180
    assert args.lang == "zh-CN"
    assert args.play is False


def test_read_text_file(tmp_path: Path) -> None:
    sample = tmp_path / "demo.md"
    sample.write_text("# 标题\n\n你好，世界", encoding="utf-8")
    assert "你好，世界" in read_text_file(sample, "utf-8")


def test_read_text_file_empty(tmp_path: Path) -> None:
    sample = tmp_path / "empty.md"
    sample.write_text("   ", encoding="utf-8")
    try:
        read_text_file(sample, "utf-8")
    except ValueError as exc:
        assert "为空" in str(exc)
    else:
        raise AssertionError("应当抛出 ValueError")


def test_speed_to_edge_rate() -> None:
    assert speed_to_edge_rate(180) == "+0%"
    assert speed_to_edge_rate(270) == "+50%"
    assert speed_to_edge_rate(90) == "-50%"


def test_resolve_backend_auto_prefers_pyttsx3(monkeypatch) -> None:
    monkeypatch.setattr(cli, "has_dependency", lambda module_name: module_name == "pyttsx3")
    assert cli.resolve_backend("auto") == "pyttsx3"


def test_cleanup_temp_file(tmp_path: Path) -> None:
    sample = tmp_path / "temp.mp3"
    sample.write_text("x", encoding="utf-8")
    cli.cleanup_temp_file(str(sample))
    assert not sample.exists()
