from pathlib import Path


def test_health_check_adds_project_root_before_config_import():
    script = Path("scripts/health_check.py").read_text(encoding="utf-8")

    project_root_line = "sys.path.insert(0, str(_project_root))"
    config_import_line = "from config.bootstrap_env import bootstrap_env"

    assert project_root_line in script
    assert config_import_line in script
    assert script.index(project_root_line) < script.index(config_import_line)
