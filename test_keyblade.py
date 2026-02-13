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
    def test_cost_budget_default(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        mp = keyblade.calculate_mp(data, config)
        # $1.50 spent of $5.00 budget = 70% remaining
        self.assertAlmostEqual(mp, 70.0)

    def test_cost_budget_zero_budget(self):
        config = dict(keyblade.DEFAULT_CONFIG)
        config["mp_budget_usd"] = 0
        mp = keyblade.calculate_mp(make_data(), config)
        self.assertEqual(mp, 100.0)

    def test_cost_budget_overspent(self):
        data = make_data()
        data["cost"]["total_cost_usd"] = 10.0
        config = dict(keyblade.DEFAULT_CONFIG)
        mp = keyblade.calculate_mp(data, config)
        self.assertEqual(mp, 0.0)

    def test_context_remaining_source(self):
        config = dict(keyblade.DEFAULT_CONFIG)
        config["mp_source"] = "context_remaining"
        data = make_data()
        mp = keyblade.calculate_mp(data, config)
        self.assertEqual(mp, 75)

    def test_api_efficiency_source(self):
        config = dict(keyblade.DEFAULT_CONFIG)
        config["mp_source"] = "api_efficiency"
        data = make_data()
        mp = keyblade.calculate_mp(data, config)
        # 120000 / 180000 * 100 = 66.67
        self.assertAlmostEqual(mp, 66.67, places=1)


class TestWorldName(unittest.TestCase):
    def test_normal_dir(self):
        data = make_data()
        self.assertEqual(keyblade.world_name(data), "myapp")

    def test_empty_workspace(self):
        data = make_data(workspace={})
        self.assertEqual(keyblade.world_name(data), "Traverse Town")

    def test_root_dir(self):
        data = make_data(workspace={"current_dir": "/"})
        self.assertEqual(keyblade.world_name(data), "Traverse Town")


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
        self.assertEqual(keyblade.calculate_level(data), 1)

    def test_ten_lines(self):
        data = make_data()
        data["cost"]["total_lines_added"] = 10
        self.assertEqual(keyblade.calculate_level(data), 2)

    def test_200_lines(self):
        data = make_data()
        data["cost"]["total_lines_added"] = 200
        level = keyblade.calculate_level(data)
        self.assertEqual(level, 5)

    def test_1000_lines(self):
        data = make_data()
        data["cost"]["total_lines_added"] = 1000
        self.assertEqual(keyblade.calculate_level(data), 11)


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

    def test_contains_drive(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_full_rpg(data, config)
        self.assertIn("Drive", output)

    def test_contains_exp(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_full_rpg(data, config)
        self.assertIn("+200/-30", output)

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
        self.assertEqual(config["mp_budget_usd"], 5.00)
        del os.environ["CLAUDE_CONFIG_DIR"]


if __name__ == "__main__":
    unittest.main()
