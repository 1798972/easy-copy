import json

from easy_copy import config


def test_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.json")
    assert config.load_config() == config.DEFAULTS


def test_merge_validate_and_save(tmp_path, monkeypatch):
    f = tmp_path / "config.json"
    monkeypatch.setattr(config, "CONFIG_FILE", f)
    f.write_text(json.dumps({"max_items": 3, "auto_paste": "yes", "panel_width": True,
                             "hotkey": "<Control>space", "junk": 1}))
    cfg = config.load_config()
    assert cfg["max_items"] == 3 and cfg["hotkey"] == "<Control>space"
    assert cfg["auto_paste"] is True, "类型不对的项回退默认"
    assert cfg["panel_width"] == config.DEFAULTS["panel_width"], "bool 不能冒充 int"
    assert "junk" not in cfg
    config.save_config(cfg)
    assert set(json.loads(f.read_text())) == set(config.DEFAULTS)
