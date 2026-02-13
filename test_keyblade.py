#!/usr/bin/env python3
"""Tests for keyblade.py — Kingdom Hearts themed statusline."""

import json
import os
import sys
import unittest

# Import from same directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import keyblade


def make_data(**overrides):
    """Build sample statusline JSON data with overrides."""
    data = {
        "context_window": {
            "remaining_percentage": 75,
            "used_percentage": 25,
            "context_window_size": 200000,
            "current_usage": {
                "input_tokens": 50000,
                "output_tokens": 10000,
            },
        },
        "cost": {
            "total_cost_usd": 1.50,
            "total_duration_ms": 180000,
            "total_api_duration_ms": 120000,
            "total_lines_added": 200,
            "total_lines_removed": 30,
        },
        "model": {
            "id": "claude-opus-4-6",
            "display_name": "Opus",
        },
        "workspace": {
            "current_dir": "/Users/ed/projects/myapp",
            "project_dir": "/Users/ed/projects/myapp",
        },
        "session_id": "test-session-123",
        "version": "1.0.0",
    }
    data.update(overrides)
    return data


class TestKeybladeResolution(unittest.TestCase):
    def test_opus(self):
        config = keyblade.DEFAULT_CONFIG
        result = keyblade.resolve_keyblade("claude-opus-4-6", "Opus", config)
        self.assertEqual(result, "Ultima Weapon")

    def test_sonnet(self):
        config = keyblade.DEFAULT_CONFIG
        result = keyblade.resolve_keyblade("claude-sonnet-4-5", "Sonnet", config)
        self.assertEqual(result, "Oathkeeper")

    def test_haiku(self):
        config = keyblade.DEFAULT_CONFIG
        result = keyblade.resolve_keyblade("claude-haiku-4-5", "Haiku", config)
        self.assertEqual(result, "Kingdom Key")

    def test_unknown_model(self):
        config = keyblade.DEFAULT_CONFIG
        result = keyblade.resolve_keyblade("gpt-4o", "GPT-4o", config)
        self.assertEqual(result, "Waypoint (GPT-4o)")

    def test_unknown_empty_display(self):
        config = keyblade.DEFAULT_CONFIG
        result = keyblade.resolve_keyblade("unknown", "", config)
        self.assertEqual(result, "Kingdom Key")

    def test_custom_names(self):
        config = dict(keyblade.DEFAULT_CONFIG)
        config["keyblade_names"] = {"opus": "Oblivion", "sonnet": "Star Seeker", "haiku": "Dream Sword"}
        result = keyblade.resolve_keyblade("claude-opus-4-6", "Opus", config)
        self.assertEqual(result, "Oblivion")


class TestCalculateMP(unittest.TestCase):
    def test_context_remaining(self):
        data = make_data()
        mp = keyblade.calculate_mp(data)
        # remaining_percentage is 75 in test data
        self.assertEqual(mp, 75)

    def test_missing_context(self):
        mp = keyblade.calculate_mp({})
        self.assertEqual(mp, 100)

    def test_null_remaining(self):
        data = make_data()
        data["context_window"]["remaining_percentage"] = None
        mp = keyblade.calculate_mp(data)
        self.assertEqual(mp, 100)


class TestWorldName(unittest.TestCase):
    def test_normal_dir(self):
        data = make_data()
        # world_name will try git commands which may add branch info
        result = keyblade.world_name(data)
        self.assertTrue(result.startswith("myapp"))

    def test_empty_workspace(self):
        data = make_data(workspace={})
        self.assertEqual(keyblade.world_name(data), "Traverse Town")

    def test_root_dir(self):
        data = make_data(workspace={"current_dir": "/"})
        self.assertEqual(keyblade.world_name(data), "Traverse Town")

    def test_custom_fallback(self):
        data = make_data(workspace={})
        config = dict(keyblade.DEFAULT_CONFIG)
        config["world_fallback"] = "Destiny Islands"
        self.assertEqual(keyblade.world_name(data, config), "Destiny Islands")

    def test_world_map(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        config["world_map"] = {"myapp": "Hollow Bastion"}
        config["show_branch"] = False
        result = keyblade.world_name(data, config)
        self.assertEqual(result, "Hollow Bastion")

    def test_no_branch(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        config["show_branch"] = False
        result = keyblade.world_name(data, config)
        self.assertEqual(result, "myapp")


class TestFormatDuration(unittest.TestCase):
    def test_seconds(self):
        self.assertEqual(keyblade.format_duration(5000), "5s")

    def test_minutes(self):
        self.assertEqual(keyblade.format_duration(180000), "3m00s")

    def test_hours(self):
        self.assertEqual(keyblade.format_duration(3720000), "1h02m")


class TestCalculateLevel(unittest.TestCase):
    def test_zero_lines(self):
        data = make_data()
        data["cost"]["total_lines_added"] = 0
        data["cost"]["total_lines_removed"] = 0
        self.assertEqual(keyblade.calculate_level(data), 1)

    def test_under_100(self):
        data = make_data()
        data["cost"]["total_lines_added"] = 50
        data["cost"]["total_lines_removed"] = 20
        # 70 total modified, still level 1
        self.assertEqual(keyblade.calculate_level(data), 1)

    def test_exactly_100(self):
        data = make_data()
        data["cost"]["total_lines_added"] = 60
        data["cost"]["total_lines_removed"] = 40
        # 100 total modified = level 2
        self.assertEqual(keyblade.calculate_level(data), 2)

    def test_250_lines(self):
        data = make_data()
        data["cost"]["total_lines_added"] = 200
        data["cost"]["total_lines_removed"] = 50
        # 250 total = level 3
        self.assertEqual(keyblade.calculate_level(data), 3)

    def test_1000_lines(self):
        data = make_data()
        data["cost"]["total_lines_added"] = 700
        data["cost"]["total_lines_removed"] = 300
        # 1000 total = level 11
        self.assertEqual(keyblade.calculate_level(data), 11)

    def test_custom_per(self):
        data = make_data()
        data["cost"]["total_lines_added"] = 50
        data["cost"]["total_lines_removed"] = 0
        config = dict(keyblade.DEFAULT_CONFIG)
        config["level_per"] = 50
        # 50 lines / 50 per = level 2
        self.assertEqual(keyblade.calculate_level(data, config), 2)

    def test_exponential_curve(self):
        data = make_data()
        data["cost"]["total_lines_added"] = 300
        data["cost"]["total_lines_removed"] = 0
        config = dict(keyblade.DEFAULT_CONFIG)
        config["level_curve"] = "exponential"
        # Triangular: L = (1 + sqrt(1 + 8*300/100)) / 2 = (1 + sqrt(25)) / 2 = 3
        self.assertEqual(keyblade.calculate_level(data, config), 3)

    def test_max_cap(self):
        data = make_data()
        data["cost"]["total_lines_added"] = 999999
        data["cost"]["total_lines_removed"] = 0
        config = dict(keyblade.DEFAULT_CONFIG)
        config["level_max"] = 10
        self.assertEqual(keyblade.calculate_level(data, config), 10)

    def test_added_only_source(self):
        data = make_data()
        data["cost"]["total_lines_added"] = 100
        data["cost"]["total_lines_removed"] = 500
        config = dict(keyblade.DEFAULT_CONFIG)
        config["level_source"] = "added_only"
        # Only 100 added, ignores 500 removed
        self.assertEqual(keyblade.calculate_level(data, config), 2)


class TestCalculateExp(unittest.TestCase):
    def test_default_data(self):
        data = make_data()
        # 200 added + 30 removed = 230
        self.assertEqual(keyblade.calculate_exp(data), 230)

    def test_zero(self):
        data = make_data()
        data["cost"]["total_lines_added"] = 0
        data["cost"]["total_lines_removed"] = 0
        self.assertEqual(keyblade.calculate_exp(data), 0)

    def test_null_fields(self):
        data = make_data()
        data["cost"]["total_lines_added"] = None
        data["cost"]["total_lines_removed"] = None
        self.assertEqual(keyblade.calculate_exp(data), 0)

    def test_added_only_source(self):
        data = make_data()
        data["cost"]["total_lines_added"] = 100
        data["cost"]["total_lines_removed"] = 50
        config = dict(keyblade.DEFAULT_CONFIG)
        config["level_source"] = "added_only"
        # EXP tied to same source as level
        self.assertEqual(keyblade.calculate_exp(data, config), 100)


class TestBarRendering(unittest.TestCase):
    def test_full_bar(self):
        bar = keyblade.render_bar("HP", 100, 10, "green")
        self.assertIn(keyblade.BAR_FULL, bar)
        self.assertNotIn(keyblade.BAR_EMPTY, bar)
        self.assertIn("100%", bar)

    def test_empty_bar(self):
        bar = keyblade.render_bar("HP", 0, 10, "green")
        self.assertNotIn(keyblade.BAR_FULL, bar)
        self.assertIn(keyblade.BAR_EMPTY, bar)
        self.assertIn("0%", bar)

    def test_half_bar(self):
        bar = keyblade.render_bar("HP", 50, 10, "green")
        self.assertIn("50%", bar)

    def test_no_pct(self):
        bar = keyblade.render_bar("HP", 50, 10, "green", show_pct=False)
        self.assertNotIn("%", bar)

    def test_clamps_over_100(self):
        bar = keyblade.render_bar("HP", 150, 10, "green")
        self.assertIn("100%", bar)

    def test_clamps_under_0(self):
        bar = keyblade.render_bar("HP", -10, 10, "green")
        self.assertIn("0%", bar)


class TestHPColor(unittest.TestCase):
    def test_green_above_50(self):
        self.assertEqual(keyblade.hp_color(75), keyblade.ANSI["green"])

    def test_yellow_20_to_50(self):
        self.assertEqual(keyblade.hp_color(35), keyblade.ANSI["yellow"])

    def test_red_below_20(self):
        self.assertEqual(keyblade.hp_color(10), keyblade.ANSI["red"])


class TestClassicTheme(unittest.TestCase):
    def test_renders_two_lines(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_classic(data, config)
        lines = output.split("\n")
        self.assertEqual(len(lines), 2)

    def test_contains_keyblade_name(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_classic(data, config)
        self.assertIn("Ultima Weapon", output)

    def test_contains_munny(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_classic(data, config)
        self.assertIn("munny", output)

    def test_contains_hp_mp(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_classic(data, config)
        self.assertIn("HP", output)
        self.assertIn("MP", output)


class TestMinimalTheme(unittest.TestCase):
    def test_renders_one_line(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_minimal(data, config)
        lines = output.split("\n")
        self.assertEqual(len(lines), 1)

    def test_contains_keyblade(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_minimal(data, config)
        self.assertIn("Ultima Weapon", output)


class TestFullRPGTheme(unittest.TestCase):
    def test_renders_three_lines(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_full_rpg(data, config)
        lines = output.split("\n")
        self.assertEqual(len(lines), 3)

    def test_contains_level(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_full_rpg(data, config)
        self.assertIn("Lv.", output)

    def test_contains_drive_form(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_full_rpg(data, config)
        self.assertIn("Form", output)

    def test_contains_exp(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_full_rpg(data, config)
        self.assertIn("230 EXP", output)

    def test_agent_party_member(self):
        data = make_data(agent={"name": "security-reviewer"})
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_full_rpg(data, config)
        self.assertIn("security-reviewer", output)

    def test_no_agent(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_full_rpg(data, config)
        self.assertNotIn(keyblade.PARTY_ICON, output)


class TestEdgeCases(unittest.TestCase):
    def test_empty_data(self):
        config = dict(keyblade.DEFAULT_CONFIG)
        # Should not crash with empty data
        for renderer in [keyblade.render_classic, keyblade.render_minimal, keyblade.render_full_rpg]:
            output = renderer({}, config)
            self.assertIsInstance(output, str)
            self.assertTrue(len(output) > 0)

    def test_null_fields(self):
        data = {
            "context_window": {"remaining_percentage": None, "used_percentage": None},
            "cost": {"total_cost_usd": None, "total_lines_added": None},
            "model": {"id": None, "display_name": None},
            "workspace": {"current_dir": None},
        }
        config = dict(keyblade.DEFAULT_CONFIG)
        for renderer in [keyblade.render_classic, keyblade.render_minimal, keyblade.render_full_rpg]:
            output = renderer(data, config)
            self.assertIsInstance(output, str)


class TestConfigLoading(unittest.TestCase):
    def test_defaults_when_no_file(self):
        # With a nonexistent config dir, should return defaults
        os.environ["CLAUDE_CONFIG_DIR"] = "/tmp/nonexistent_keyblade_test"
        config = keyblade.load_config()
        self.assertEqual(config["theme"], "classic")
        self.assertEqual(config["hp_usage_cache_ttl"], 60)
        del os.environ["CLAUDE_CONFIG_DIR"]


class TestResolveDriveForm(unittest.TestCase):
    def setUp(self):
        # Ensure no env var leaks between tests
        self.orig_env = os.environ.get("CLAUDE_CODE_EFFORT_LEVEL")
        self.orig_config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
        # Point config dir to nonexistent path so settings.json isn't read
        os.environ["CLAUDE_CONFIG_DIR"] = "/tmp/nonexistent_keyblade_test"

    def tearDown(self):
        if self.orig_env is not None:
            os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = self.orig_env
        elif "CLAUDE_CODE_EFFORT_LEVEL" in os.environ:
            del os.environ["CLAUDE_CODE_EFFORT_LEVEL"]
        if self.orig_config_dir is not None:
            os.environ["CLAUDE_CONFIG_DIR"] = self.orig_config_dir
        elif "CLAUDE_CONFIG_DIR" in os.environ:
            del os.environ["CLAUDE_CONFIG_DIR"]

    def test_default_is_master_form(self):
        data = make_data()
        result = keyblade.resolve_drive_form(data)
        self.assertEqual(result, "Master Form")

    def test_low_effort_from_env(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "low"
        data = make_data()
        result = keyblade.resolve_drive_form(data)
        self.assertEqual(result, "Valor Form")

    def test_medium_effort_from_env(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "medium"
        data = make_data()
        result = keyblade.resolve_drive_form(data)
        self.assertEqual(result, "Wisdom Form")

    def test_high_effort_from_env(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "high"
        data = make_data()
        result = keyblade.resolve_drive_form(data)
        self.assertEqual(result, "Master Form")

    def test_data_effort_takes_priority(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "high"
        data = make_data()
        data["effort"] = "low"
        result = keyblade.resolve_drive_form(data)
        self.assertEqual(result, "Valor Form")

    def test_data_reasoning_effort_field(self):
        data = make_data()
        data["reasoning_effort"] = "medium"
        result = keyblade.resolve_drive_form(data)
        self.assertEqual(result, "Wisdom Form")

    def test_custom_form_names(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "low"
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        config["drive_form_names"] = {
            "low": "Anti Form",
            "medium": "Limit Form",
            "high": "Final Form",
        }
        result = keyblade.resolve_drive_form(data, config)
        self.assertEqual(result, "Anti Form")

    def test_max_effort_from_env(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "max"
        data = make_data()
        result = keyblade.resolve_drive_form(data)
        self.assertEqual(result, "Final Form")

    def test_unknown_effort_falls_back_to_high(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "turbo"
        data = make_data()
        result = keyblade.resolve_drive_form(data)
        self.assertEqual(result, "Master Form")


class TestDriveFormInThemes(unittest.TestCase):
    def setUp(self):
        self.orig_config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = "/tmp/nonexistent_keyblade_test"
        self.orig_env = os.environ.get("CLAUDE_CODE_EFFORT_LEVEL")
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "low"

    def tearDown(self):
        if self.orig_config_dir is not None:
            os.environ["CLAUDE_CONFIG_DIR"] = self.orig_config_dir
        elif "CLAUDE_CONFIG_DIR" in os.environ:
            del os.environ["CLAUDE_CONFIG_DIR"]
        if self.orig_env is not None:
            os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = self.orig_env
        elif "CLAUDE_CODE_EFFORT_LEVEL" in os.environ:
            del os.environ["CLAUDE_CODE_EFFORT_LEVEL"]

    def test_full_rpg_shows_form_name(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_full_rpg(data, config)
        self.assertIn("Valor Form", output)
        self.assertNotIn("Drive", output.split("Valor Form")[0].split("\n")[-1])

    def test_classic_shows_form_name(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_classic(data, config)
        self.assertIn("Valor Form", output)

    def test_minimal_shows_short_form_name(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_minimal(data, config)
        self.assertIn("Valor", output)
        # Minimal strips " Form" suffix
        self.assertNotIn("Valor Form", output)

    def test_show_drive_form_false_hides_in_classic(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        config["show_drive_form"] = False
        output = keyblade.render_classic(data, config)
        self.assertNotIn("Valor", output)

    def test_show_drive_form_false_hides_in_minimal(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        config["show_drive_form"] = False
        output = keyblade.render_minimal(data, config)
        self.assertNotIn("Valor", output)

    def test_show_drive_form_false_shows_drive_in_full_rpg(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        config["show_drive_form"] = False
        output = keyblade.render_full_rpg(data, config)
        self.assertIn("Drive", output)
        self.assertNotIn("Valor", output)


if __name__ == "__main__":
    unittest.main()
