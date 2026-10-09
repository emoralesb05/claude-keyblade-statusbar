#!/usr/bin/env python3
"""Tests for keyblade.py — Kingdom Hearts themed statusline.

Run: python3 -m unittest test_keyblade
"""

import contextlib
import io
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
import unittest

# Import from same directory
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import keyblade

SCRIPT = os.path.join(HERE, "keyblade.py")

# Environment that changes keyblade's behavior; cleared for every test.
ISOLATED_ENV = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
    "ANTHROPIC_BASE_URL", "CLAUDE_CODE_EXECPATH", "CLAUDE_CODE_EFFORT_LEVEL",
    "CLAUDE_CONFIG_DIR", "COLUMNS", "NO_COLOR", "CLICOLOR", "COLORTERM",
    "KEYBLADE_STATE_FILE",
)

_ESCAPES = re.compile(r"\x1b\[[0-9;]*m|\x1b\]8;[^\x07\x1b]*(?:\x07|\x1b\\)")


def strip(text):
    """Remove ANSI colors and OSC 8 links."""
    return _ESCAPES.sub("", text)


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
            "current_dir": "/nonexistent/projects/myapp",
            "project_dir": "/nonexistent/projects/myapp",
        },
        "session_id": "test-session-123",
        "version": "1.0.0",
    }
    data.update(overrides)
    return data


def git(cwd, *args):
    """Run git with a fixed identity and no user hooks/signing."""
    return subprocess.run(
        ["git", "-c", "user.name=Sora", "-c", "user.email=sora@example.com",
         "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    ).stdout


class KeybladeTestCase(unittest.TestCase):
    """Isolates every test from the machine: temp state and git cache, no real
    settings.json, no auth env, no `claude` binary, no terminal width."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = os.path.realpath(self._tmpdir.name)
        self._env = {k: os.environ.get(k) for k in ISOLATED_ENV}
        for k in ISOLATED_ENV:
            os.environ.pop(k, None)
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.tmp, "claude")
        self._originals = {}
        self.patch("STATE_FILE", os.path.join(self.tmp, "state.json"))
        self.patch("GIT_CACHE_DIR", self.tmp)
        self.patch("_claude_executable", lambda: None)
        # Run auth refreshes inline instead of in a detached child
        self.patch("_spawn_auth_refresh", lambda key, ttl: keyblade.refresh_auth(key, ttl))
        self.patch("ANSI", keyblade._resolve_ansi("truecolor"))

    def tearDown(self):
        for name, value in self._originals.items():
            setattr(keyblade, name, value)
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmpdir.cleanup()

    def patch(self, name, value):
        self._originals.setdefault(name, getattr(keyblade, name))
        setattr(keyblade, name, value)

    def config(self, **overrides):
        config = dict(keyblade.DEFAULT_CONFIG)
        config.update(overrides)
        return config

    def make_repo(self, name="destiny-islands", commit=True):
        path = os.path.join(self.tmp, name)
        os.makedirs(path)
        git(path, "init", "-q", "-b", "main")
        # Repo-local identity so the user's global git config can't leak in
        git(path, "config", "user.email", "sora@example.com")
        git(path, "config", "user.name", "Sora")
        if commit:
            self.write(path, "README.md", "line 1\nline 2\nline 3\n")
            git(path, "add", "README.md")
            git(path, "commit", "-q", "-m", "init")
        return path

    def write(self, repo, rel, content, mode="w"):
        path = os.path.join(repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, mode) as f:
            f.write(content)
        return path

    def repo_data(self, path, **overrides):
        return make_data(workspace={"current_dir": path, "project_dir": path}, **overrides)


# ─── Existing behavior ───────────────────────────────────────────

class TestKeybladeResolution(KeybladeTestCase):
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

    def test_fable(self):
        result = keyblade.resolve_keyblade("claude-fable-5-1", "Fable", keyblade.DEFAULT_CONFIG)
        self.assertEqual(result, "Sweet Memories")

    def test_unknown_model(self):
        config = keyblade.DEFAULT_CONFIG
        result = keyblade.resolve_keyblade("gpt-4o", "GPT-4o", config)
        self.assertEqual(result, "Starlight")

    def test_unknown_empty_display(self):
        config = keyblade.DEFAULT_CONFIG
        result = keyblade.resolve_keyblade("unknown", "", config)
        self.assertEqual(result, "Starlight")

    def test_custom_names(self):
        config = dict(keyblade.DEFAULT_CONFIG)
        config["keyblade_names"] = {"opus": "Oblivion", "sonnet": "Star Seeker", "haiku": "Dream Sword"}
        result = keyblade.resolve_keyblade("claude-opus-4-6", "Opus", config)
        self.assertEqual(result, "Oblivion")

    def test_custom_family_key(self):
        config = self.config(keyblade_names={"mythos": "Kingdom Key D"})
        self.assertEqual(keyblade.resolve_keyblade("claude-mythos-1", "", config), "Kingdom Key D")


class TestCalculateMP(KeybladeTestCase):
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

    def test_transcript_is_source_of_truth(self):
        path = os.path.join(self.tmp, "t.jsonl")
        with open(path, "w") as f:
            f.write(json.dumps({"message": {"usage": {"input_tokens": 10, "cache_read_input_tokens": 49990}}}) + "\n")
        data = make_data(transcript_path=path)
        # 50k of 200k used → 75% left, regardless of the payload's stale value
        data["context_window"]["remaining_percentage"] = 10
        self.assertAlmostEqual(keyblade.calculate_mp(data), 75.0)

    def test_transcript_compact_marker_wins(self):
        path = os.path.join(self.tmp, "t.jsonl")
        with open(path, "w") as f:
            f.write(json.dumps({"message": {"usage": {"input_tokens": 180000}}}) + "\n")
            f.write(json.dumps({"isCompactSummary": True, "message": {"content": "x" * 40000}}) + "\n")
        data = make_data(transcript_path=path)
        # 40k chars ≈ 10k tokens of 200k → 95% left
        self.assertAlmostEqual(keyblade.calculate_mp(data), 95.0)


class TestWorldName(KeybladeTestCase):
    def test_normal_dir(self):
        data = make_data()
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

    def test_branch_from_repo(self):
        repo = self.make_repo()
        self.assertEqual(keyblade.world_name(self.repo_data(repo)), "destiny-islands ∙ main")

    def test_trailing_slash(self):
        data = make_data(workspace={"current_dir": "/nonexistent/myapp/"})
        self.assertEqual(keyblade.world_name(data), "myapp")


class TestFormatDuration(KeybladeTestCase):
    def test_seconds(self):
        self.assertEqual(keyblade.format_duration(5000), "5s")

    def test_minutes(self):
        self.assertEqual(keyblade.format_duration(180000), "3m00s")

    def test_hours(self):
        self.assertEqual(keyblade.format_duration(3720000), "1h02m")


class TestCalculateLevel(KeybladeTestCase):
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


class TestCalculateExp(KeybladeTestCase):
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


class TestBarRendering(KeybladeTestCase):
    def test_full_bar(self):
        bar = keyblade.render_bar(100, 10, "green")
        self.assertIn(keyblade.BAR_FULL, bar)
        self.assertIn("100%", bar)

    def test_empty_bar(self):
        bar = keyblade.render_bar(0, 10, "green")
        self.assertNotIn(keyblade.BAR_FULL, bar)
        self.assertIn("0%", bar)

    def test_smooth_partial_block(self):
        # 45% of 10 = 4.5 chars → 4 full + ▌ (4/8) partial block
        bar = keyblade.render_bar(45, 10, "green")
        self.assertIn(keyblade.BAR_FULL, bar)
        self.assertIn("45%", bar)
        # Should contain a partial block character (3/8 or thicker)
        partial_blocks = set(keyblade.BAR_BLOCKS[3:8])  # ▍▌▋▊▉
        has_partial = any(ch in bar for ch in partial_blocks)
        self.assertTrue(has_partial, "Bar at 45% should contain a partial block character")

    def test_half_bar(self):
        bar = keyblade.render_bar(50, 10, "green")
        self.assertIn("50%", bar)

    def test_no_pct(self):
        bar = keyblade.render_bar(50, 10, "green", show_pct=False)
        self.assertNotIn("%", bar)

    def test_clamps_over_100(self):
        bar = keyblade.render_bar(150, 10, "green")
        self.assertIn("100%", bar)

    def test_clamps_under_0(self):
        bar = keyblade.render_bar(-10, 10, "green")
        self.assertIn("0%", bar)

    def test_bar_is_exactly_width_columns(self):
        for pct in (0, 7, 33, 45, 50, 99, 100):
            bar = strip(keyblade.render_bar(pct, 12, "green", show_pct=False))
            self.assertEqual(keyblade.visible_width(bar), 12, pct)


class TestBasicColorBars(KeybladeTestCase):
    """16-color terminals: the empty track must not share the fill's color."""

    def test_basic_mode_uses_shaded_track(self):
        self.patch("ANSI", keyblade._resolve_ansi("basic"))
        bar = keyblade.render_bar(30, 10, "green")
        self.assertIn(keyblade.BAR_EMPTY, bar)
        self.assertNotIn("\033[42m", bar)

    def test_basic_mode_has_no_track_backgrounds(self):
        self.assertFalse([k for k in keyblade.ANSI_BASIC if k.startswith("bg_")])

    def test_truecolor_track_for_every_form_color(self):
        for color in keyblade.DEFAULT_CONFIG["drive_form_colors"].values():
            self.assertIn(f"bg_{color}", keyblade.ANSI_TRUECOLOR, color)


class TestHPColor(KeybladeTestCase):
    def test_green_above_50(self):
        self.assertEqual(keyblade.hp_color(75), keyblade.ANSI["green"])

    def test_orange_20_to_50(self):
        self.assertEqual(keyblade.hp_color(35), keyblade.ANSI["bright_orange"])

    def test_red_below_20(self):
        self.assertEqual(keyblade.hp_color(10), keyblade.ANSI["red"])

    def test_custom_hp_color_when_healthy(self):
        self.assertEqual(keyblade.hp_bar_color(80, {"hp": "cyan"}), "cyan")
        self.assertEqual(keyblade.hp_bar_color(30, {"hp": "cyan"}), "bright_orange")

    def test_classic_uses_colors_hp(self):
        out = keyblade.render_classic(make_data(), self.config(colors=dict(keyblade.DEFAULT_CONFIG["colors"], hp="cyan")))
        self.assertIn(keyblade.ANSI["cyan"] + keyblade.ANSI["bold"] + keyblade.BAR_FULL, out.split("\n")[1])


class TestClassicTheme(KeybladeTestCase):
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
        self.assertIn(keyblade.MUNNY_ICON, output)

    def test_contains_hp_mp_icons(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_classic(data, config)
        self.assertIn(keyblade.HEART_ICON, output)
        self.assertIn(keyblade.MP_ICON, output)

    def test_party_member_shown(self):
        out = keyblade.render_classic(make_data(agent={"name": "security-reviewer"}), self.config())
        self.assertIn("security-reviewer", out)


class TestMinimalTheme(KeybladeTestCase):
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


class TestFullRPGTheme(KeybladeTestCase):
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
        self.assertIn("LV ", output)

    def test_contains_drive_form(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_full_rpg(data, config)
        self.assertIn("Form", output)

    def test_contains_exp(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_full_rpg(data, config)
        # EXP is on line 2 next to Level: "LV 3 (♛ 230)"
        self.assertIn("230)", output)

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

    def test_show_drive_false_keeps_form_and_indent(self):
        out = keyblade.render_full_rpg(make_data(), self.config(show_drive=False))
        line3 = out.split("\n")[2]
        self.assertTrue(line3.startswith("  "))
        self.assertNotIn(keyblade.DRIVE_ICON, line3)
        self.assertIn("Form", line3)


class TestEdgeCases(KeybladeTestCase):
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
            "rate_limits": None,
            "pr": None,
            "prompt_cache": None,
            "effort": None,
        }
        config = dict(keyblade.DEFAULT_CONFIG)
        for renderer in [keyblade.render_classic, keyblade.render_minimal, keyblade.render_full_rpg]:
            output = renderer(data, config)
            self.assertIsInstance(output, str)

    def test_malformed_rate_limits(self):
        data = make_data(rate_limits={"five_hour": "lots", "seven_day": {"used_percentage": None}})
        for renderer in keyblade.RENDERERS.values():
            self.assertIsInstance(renderer(data, self.config()), str)


class TestConfigLoading(KeybladeTestCase):
    def write_config(self, cfg):
        path = os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "hooks", "keyblade", "config.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(cfg, f)

    def test_defaults_when_no_file(self):
        config = keyblade.load_config()
        self.assertEqual(config["theme"], "classic")
        self.assertEqual(config["hp_source"], "auto")
        self.assertEqual(config["drive_max_lines"], 1000)

    def test_nested_dicts_deep_merge(self):
        self.write_config({"keyblade_names": {"opus": "Oblivion"}, "colors": {"hp": "cyan"}})
        config = keyblade.load_config()
        self.assertEqual(config["keyblade_names"]["opus"], "Oblivion")
        self.assertEqual(config["keyblade_names"]["fable"], "Sweet Memories")
        self.assertEqual(config["colors"]["mp"], "blue")

    def test_shipped_config_matches_defaults(self):
        with open(os.path.join(HERE, "config.json")) as f:
            shipped = json.load(f)
        self.assertEqual(set(shipped), set(keyblade.DEFAULT_CONFIG))
        for key, value in shipped.items():
            self.assertEqual(value, keyblade.DEFAULT_CONFIG[key], key)


class TestResolveDriveForm(KeybladeTestCase):
    def test_default_is_limit_form(self):
        data = make_data()
        result = keyblade.resolve_drive_form(data)
        self.assertEqual(result, "Limit Form")

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
        self.assertEqual(result, "Limit Form")

    def test_xhigh_effort_from_env(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "xhigh"
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
        self.assertEqual(result, "Limit Form")


class TestDriveFormInThemes(KeybladeTestCase):
    def setUp(self):
        super().setUp()
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "low"

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

    def test_drive_bar_uses_colors_drive_without_form(self):
        config = self.config(show_drive_form=False)
        out = keyblade.render_full_rpg(make_data(), config)
        self.assertIn(keyblade.ANSI["magenta"] + keyblade.FORM_ICON + " Drive", out)


class TestResolveEffortLevel(KeybladeTestCase):
    def test_default_is_high(self):
        data = make_data()
        self.assertEqual(keyblade.resolve_effort_level(data), "high")

    def test_from_env(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "low"
        data = make_data()
        self.assertEqual(keyblade.resolve_effort_level(data), "low")

    def test_data_overrides_env(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "high"
        data = make_data()
        data["effort"] = "max"
        self.assertEqual(keyblade.resolve_effort_level(data), "max")

    def test_from_settings_json(self):
        os.makedirs(os.environ["CLAUDE_CONFIG_DIR"])
        with open(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"), "w") as f:
            json.dump({"effortLevel": "medium"}, f)
        self.assertEqual(keyblade.resolve_effort_level(make_data()), "medium")


class TestEffortFromPayload(KeybladeTestCase):
    """Claude Code v2.1+ sends effort.level, and omits it for models without effort."""

    def test_dict_level(self):
        data = make_data(version="2.1.295", effort={"level": "xhigh"})
        self.assertEqual(keyblade.resolve_drive_form(data), "Master Form")

    def test_absent_on_modern_version_means_no_form(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "max"  # must not leak in
        data = make_data(version="2.1.295")
        self.assertIsNone(keyblade.resolve_effort_level(data))
        self.assertIsNone(keyblade.resolve_drive_form(data))

    def test_null_level_means_no_form(self):
        data = make_data(version="2.1.295", effort={"level": None})
        self.assertIsNone(keyblade.resolve_effort_level(data))

    def test_old_version_still_falls_back(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "max"
        self.assertEqual(keyblade.resolve_effort_level(make_data(version="2.0.9")), "max")

    def test_themes_without_effort(self):
        data = make_data(version="2.1.295", model={"id": "claude-haiku-5-5", "display_name": "Haiku"})
        self.assertNotIn(keyblade.FORM_ICON, keyblade.render_classic(data, self.config()))
        self.assertNotIn(keyblade.FORM_ICON, keyblade.render_minimal(data, self.config()))
        self.assertIn(f"{keyblade.FORM_ICON} Drive", strip(keyblade.render_full_rpg(data, self.config())))

    def test_anti_form_still_shows_without_effort(self):
        data = make_data(version="2.1.295")
        data["context_window"]["remaining_percentage"] = 3
        self.assertIn("Anti Form", keyblade.render_classic(data, self.config()))


class TestDriveFormColorName(KeybladeTestCase):
    def test_low_is_red(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "low"
        data = make_data()
        self.assertEqual(keyblade.resolve_drive_form_color_name(data), "red")

    def test_medium_is_blue(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "medium"
        data = make_data()
        self.assertEqual(keyblade.resolve_drive_form_color_name(data), "blue")

    def test_high_is_bright_cyan(self):
        data = make_data()
        self.assertEqual(keyblade.resolve_drive_form_color_name(data), "bright_cyan")

    def test_xhigh_is_bright_yellow(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "xhigh"
        data = make_data()
        self.assertEqual(keyblade.resolve_drive_form_color_name(data), "bright_yellow")

    def test_max_is_bright_white(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "max"
        data = make_data()
        self.assertEqual(keyblade.resolve_drive_form_color_name(data), "bright_white")

    def test_custom_form_colors(self):
        os.environ["CLAUDE_CODE_EFFORT_LEVEL"] = "low"
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        config["drive_form_colors"] = {"low": "cyan", "high": "magenta"}
        self.assertEqual(keyblade.resolve_drive_form_color_name(data, config), "cyan")

    def test_no_effort_uses_colors_drive(self):
        data = make_data(version="2.1.0")
        self.assertEqual(keyblade.resolve_drive_form_color_name(data), "magenta")


class TestHPDangerMarker(KeybladeTestCase):
    def test_healthy_no_marker(self):
        self.assertEqual(keyblade.hp_danger_marker(75), "")

    def test_warning_marker(self):
        marker = keyblade.hp_danger_marker(35)
        self.assertIn("⚠", marker)

    def test_danger_marker(self):
        marker = keyblade.hp_danger_marker(10)
        self.assertIn("DANGER", marker)

    def test_boundary_50_shows_warning(self):
        marker = keyblade.hp_danger_marker(50)
        self.assertIn("⚠", marker)

    def test_boundary_20_shows_warning(self):
        marker = keyblade.hp_danger_marker(20)
        self.assertIn("⚠", marker)

    def test_boundary_19_shows_danger(self):
        marker = keyblade.hp_danger_marker(19)
        self.assertIn("DANGER", marker)


class TestColorMode(KeybladeTestCase):
    def test_no_color_returns_none(self):
        os.environ["NO_COLOR"] = "1"
        self.assertEqual(keyblade._detect_color_mode(), "none")

    def test_default_is_basic(self):
        self.assertEqual(keyblade._detect_color_mode(), "basic")

    def test_clicolor_zero_returns_none(self):
        os.environ["CLICOLOR"] = "0"
        self.assertEqual(keyblade._detect_color_mode(), "none")

    def test_truecolor_detected(self):
        os.environ["COLORTERM"] = "truecolor"
        self.assertEqual(keyblade._detect_color_mode(), "truecolor")

    def test_resolve_ansi_none_blanks_all(self):
        ansi = keyblade._resolve_ansi("none")
        self.assertEqual(ansi["green"], "")
        self.assertEqual(ansi["bold"], "")

    def test_resolve_ansi_truecolor_uses_rgb(self):
        ansi = keyblade._resolve_ansi("truecolor")
        # True color codes use 38;2;R;G;B format
        self.assertIn("38;2;", ansi["green"])

    def test_no_color_renders_without_escapes(self):
        self.patch("ANSI", keyblade._resolve_ansi("none"))
        out = keyblade.render_full_rpg(make_data(), self.config(hyperlinks=False))
        self.assertNotIn("\033", out.replace("\033[7m", "").replace("\033[27m", ""))


class TestMPChargeState(KeybladeTestCase):
    def test_charge_below_10(self):
        self.assertTrue(keyblade.mp_charge_state(5))

    def test_no_charge_at_10(self):
        self.assertFalse(keyblade.mp_charge_state(10))

    def test_no_charge_at_75(self):
        self.assertFalse(keyblade.mp_charge_state(75))

    def test_charge_label_and_color(self):
        lbl, clr = keyblade.mp_label_and_color(5, {"mp": "blue"})
        self.assertIn("MP", lbl)
        self.assertEqual(clr, "magenta")

    def test_charge_marker(self):
        marker = keyblade.mp_charge_marker(5)
        self.assertIn("CHARGE", marker)

    def test_no_charge_marker(self):
        marker = keyblade.mp_charge_marker(75)
        self.assertEqual(marker, "")

    def test_normal_label_and_color(self):
        lbl, clr = keyblade.mp_label_and_color(75, {"mp": "blue"})
        self.assertIn("MP", lbl)
        self.assertNotIn("CHARGE", lbl)
        self.assertEqual(clr, "blue")

    def test_classic_shows_charge(self):
        data = make_data()
        data["context_window"]["remaining_percentage"] = 5
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_classic(data, config)
        self.assertIn("CHARGE", output)

    def test_minimal_shows_charge(self):
        data = make_data()
        data["context_window"]["remaining_percentage"] = 5
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_minimal(data, config)
        self.assertIn("CHARGE", output)

    def test_full_rpg_shows_charge(self):
        data = make_data()
        data["context_window"]["remaining_percentage"] = 5
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_full_rpg(data, config)
        self.assertIn("CHARGE", output)


class TestCriticalHPReverseVideo(KeybladeTestCase):
    def test_reverse_video_below_15(self):
        marker = keyblade.hp_danger_marker(10)
        self.assertIn("DANGER", marker)
        # Reverse video escape: \033[7m
        self.assertIn("\033[7m", marker)

    def test_no_reverse_at_18(self):
        marker = keyblade.hp_danger_marker(18)
        self.assertIn("DANGER", marker)
        self.assertNotIn("\033[7m", marker)


class TestLevelUp(KeybladeTestCase):
    def test_first_level_triggers_notification(self):
        result = keyblade.check_level_up(1)
        self.assertTrue(result)

    def test_same_level_no_notification_after_duration(self):
        # Set state with expired timestamp
        keyblade._write_level_state({}, 5, 0)
        result = keyblade.check_level_up(5)
        self.assertFalse(result)

    def test_level_increase_triggers_notification(self):
        keyblade._write_level_state({}, 3, 0)
        result = keyblade.check_level_up(4)
        self.assertTrue(result)

    def test_level_up_marker_text(self):
        marker = keyblade.level_up_marker(1)
        self.assertIn("LEVEL UP!", marker)


class TestWorldAndBranch(KeybladeTestCase):
    def test_world_branch_split(self):
        data = make_data()
        config = dict(keyblade.DEFAULT_CONFIG)
        config["show_branch"] = False
        name, branch = keyblade.world_and_branch(data, config)
        self.assertEqual(name, "myapp")
        self.assertEqual(branch, "")


class TestAntiForm(KeybladeTestCase):
    def test_anti_form_low_hp_high_drive(self):
        self.assertTrue(keyblade.is_anti_form(3, 50, 95))

    def test_anti_form_low_mp(self):
        self.assertTrue(keyblade.is_anti_form(80, 4, 10))

    def test_no_anti_form_normal(self):
        self.assertFalse(keyblade.is_anti_form(75, 75, 50))

    def test_no_anti_form_low_hp_low_drive(self):
        # HP is low but drive isn't high enough
        self.assertFalse(keyblade.is_anti_form(3, 50, 50))

    def test_anti_form_in_classic(self):
        data = make_data()
        data["context_window"]["remaining_percentage"] = 3
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_classic(data, config)
        self.assertIn("Anti Form", output)

    def test_anti_form_in_minimal(self):
        data = make_data()
        data["context_window"]["remaining_percentage"] = 3
        config = dict(keyblade.DEFAULT_CONFIG)
        output = keyblade.render_minimal(data, config)
        self.assertIn("Anti", output)
        # Minimal strips " Form" suffix
        self.assertNotIn("Anti Form", output)


class TestSavePoint(KeybladeTestCase):
    def test_clean_tree_triggers_save_point(self):
        result = keyblade.check_save_point(0, 0)
        self.assertTrue(result)

    def test_dirty_tree_no_save_point(self):
        result = keyblade.check_save_point(5, 100)
        self.assertFalse(result)

    def test_save_point_marker_text(self):
        marker = keyblade.save_point_marker(0, 0)
        self.assertIn("SAVE POINT", marker)

    def test_no_save_point_marker_when_dirty(self):
        marker = keyblade.save_point_marker(5, 100)
        self.assertEqual(marker, "")

    def test_save_point_expires(self):
        # Simulate an old save point
        keyblade._write_project_state({}, {"save_point": {"clean": True, "ts": 0}})
        result = keyblade.check_save_point(0, 0)
        self.assertFalse(result)

    def test_no_save_point_outside_git(self):
        # A non-repo looks "clean" (0 files, 0 lines) but isn't a save point
        out = keyblade.render_classic(make_data(), self.config())
        self.assertNotIn("SAVE POINT", out)

    def test_save_point_in_clean_repo(self):
        repo = self.make_repo()
        self.assertIn("SAVE POINT", keyblade.render_classic(self.repo_data(repo), self.config()))


# ─── Text & layout helpers ───────────────────────────────────────

class TestVisibleWidth(KeybladeTestCase):
    def test_plain(self):
        self.assertEqual(keyblade.visible_width("Sora"), 4)

    def test_ansi_and_links_are_free(self):
        text = "\033[1m\033[38;2;1;2;3m" + keyblade.hyperlink("Kairi", "https://example.com") + "\033[0m"
        self.assertEqual(keyblade.visible_width(text), 5)

    def test_wide_chars(self):
        self.assertEqual(keyblade.visible_width("「DANGER」"), 10)
        self.assertEqual(keyblade.visible_width(keyblade.HASTE_ICON), 2)

    def test_truncate(self):
        self.assertEqual(keyblade.truncate("Riku", 10), "Riku")
        cut = keyblade.truncate("The World That Never Was", 10)
        self.assertTrue(cut.endswith("…"))
        self.assertEqual(keyblade.visible_width(cut), 10)

    def test_clean_text_strips_control_chars(self):
        self.assertEqual(keyblade.clean_text("a\x1b[31mb\nc\x07"), "a[31mbc")


class TestFitSegments(KeybladeTestCase):
    def test_no_width_joins_everything(self):
        self.assertEqual(keyblade.fit_segments([(0, "A"), (3, "B"), (1, "C", " ")], None), "  A  B C")

    def test_drops_least_important_first(self):
        segs = [(0, "AAAA"), (1, "BBBB"), (2, "CCCC")]
        self.assertEqual(keyblade.fit_segments(segs, 14), "  AAAA  BBBB")

    def test_ties_drop_rightmost(self):
        segs = [(0, "AAAA"), (2, "BBBB"), (2, "CCCC")]
        self.assertEqual(keyblade.fit_segments(segs, 14), "  AAAA  BBBB")

    def test_priority_zero_never_drops(self):
        segs = [(0, "A" * 30), (1, "B")]
        self.assertEqual(keyblade.fit_segments(segs, 10), "  " + "A" * 30)

    def test_empty_segments_skipped(self):
        self.assertEqual(keyblade.fit_segments([(0, "A"), (1, ""), (2, "B")], None), "  A  B")

    def test_custom_prefix(self):
        self.assertEqual(keyblade.fit_segments([(0, "A"), (1, "B")], None, prefix=""), "A  B")


class TestLineBudget(KeybladeTestCase):
    def test_unset_is_unbounded(self):
        self.assertIsNone(keyblade.line_budget(self.config()))

    def test_zero_or_garbage_is_unbounded(self):
        for value in ("0", "-5", "wide"):
            os.environ["COLUMNS"] = value
            self.assertIsNone(keyblade.line_budget(self.config()), value)

    def test_margin(self):
        os.environ["COLUMNS"] = "100"
        self.assertEqual(keyblade.line_budget(self.config()), 100 - keyblade.RIGHT_MARGIN)

    def test_responsive_off(self):
        os.environ["COLUMNS"] = "40"
        self.assertIsNone(keyblade.line_budget(self.config(responsive=False)))

    def test_bar_widths_shrink(self):
        self.assertEqual(keyblade.bar_widths(None), (16, 24))
        self.assertEqual(keyblade.bar_widths(80), (12, 16))
        self.assertEqual(keyblade.bar_widths(50), (8, 10))


class TestResponsiveLayout(KeybladeTestCase):
    def rich_data(self):
        now = time.time()
        return make_data(
            version="2.1.295", effort={"level": "xhigh"}, session_name="a long session name for testing",
            agent={"name": "security-reviewer"},
            rate_limits={"five_hour": {"used_percentage": 40, "resets_at": now + 3600}},
            pr={"number": 1234, "url": "https://github.com/o/r/pull/1234", "review_state": "approved"},
            prompt_cache={"warm": True, "caching_observed": True, "hit_ratio": 0.9, "expires_at": now + 600},
            workspace={"current_dir": "/nonexistent/a-really-long-project-directory-name"},
        )

    def test_lines_fit_narrow_terminals(self):
        for cols in (100, 80, 60, 40):
            os.environ["COLUMNS"] = str(cols)
            budget = cols - keyblade.RIGHT_MARGIN
            for name, renderer in keyblade.RENDERERS.items():
                for line in renderer(self.rich_data(), self.config()).split("\n"):
                    width = keyblade.visible_width(line)
                    self.assertLessEqual(width, max(budget, 40), f"{name} @ {cols}: {strip(line)!r}")

    def test_wide_terminal_keeps_everything(self):
        os.environ["COLUMNS"] = "300"
        out = strip(keyblade.render_full_rpg(self.rich_data(), self.config()))
        for piece in ("#1234", "a-really-long-project-directory-name",
                      "a long session name", "security-reviewer", keyblade.FOCUS_ICON, keyblade.CURE_ICON):
            self.assertIn(piece, out)

    def test_narrow_keeps_core_hud(self):
        os.environ["COLUMNS"] = "50"
        out = strip(keyblade.render_classic(self.rich_data(), self.config()))
        self.assertIn(keyblade.MP_ICON, out)
        self.assertIn(keyblade.HEART_ICON, out)
        self.assertIn("Ultima Weapon", out)

    def test_long_world_is_shortened_not_dropped(self):
        os.environ["COLUMNS"] = "70"
        line1 = strip(keyblade.render_full_rpg(self.rich_data(), self.config()).split("\n")[0])
        self.assertIn("a-really-long", line1)
        self.assertIn("…", line1)


class TestHyperlinksAndCountdown(KeybladeTestCase):
    def test_hyperlink(self):
        self.assertEqual(keyblade.hyperlink("x", "https://a.b"), "\033]8;;https://a.b\ax\033]8;;\a")

    def test_hyperlink_disabled(self):
        self.assertEqual(keyblade.hyperlink("x", "https://a.b", {"hyperlinks": False}), "x")

    def test_hyperlink_strips_control_chars_from_url(self):
        self.assertNotIn("\x1b[", keyblade.hyperlink("x", "https://a.b/\x1b[31m"))

    def test_no_url_no_link(self):
        self.assertEqual(keyblade.hyperlink("x", ""), "x")

    def test_countdown(self):
        self.assertEqual(keyblade.format_countdown(30), "<1m")
        self.assertEqual(keyblade.format_countdown(600), "10m")
        self.assertEqual(keyblade.format_countdown(7500), "2h05m")
        self.assertEqual(keyblade.format_countdown(3 * 86400 + 4 * 3600 + 59), "3d4h")
        self.assertEqual(keyblade.format_countdown(-5), "<1m")


# ─── HP from plan rate limits ────────────────────────────────────

class TestPlanUsageHP(KeybladeTestCase):
    def limits(self, five=None, seven=None, resets_in=3600):
        rl = {}
        if five is not None:
            rl["five_hour"] = {"used_percentage": five, "resets_at": time.time() + resets_in}
        if seven is not None:
            rl["seven_day"] = {"used_percentage": seven, "resets_at": time.time() + 7 * resets_in}
        return rl

    def test_auto_uses_payload_rate_limits(self):
        hp = keyblade.resolve_hp(make_data(rate_limits=self.limits(five=30)), self.config())
        self.assertAlmostEqual(hp["pct"], 70.0)
        self.assertEqual(hp["source"], "five_hour")
        self.assertIsNotNone(hp["resets_at"])

    def test_auto_picks_window_closest_to_cap(self):
        hp = keyblade.resolve_hp(make_data(rate_limits=self.limits(five=20, seven=70)), self.config())
        self.assertAlmostEqual(hp["pct"], 30.0)
        self.assertEqual(hp["source"], "seven_day")

    def test_explicit_windows(self):
        data = make_data(rate_limits=self.limits(five=20, seven=70))
        self.assertAlmostEqual(keyblade.calculate_hp(data, self.config(hp_source="5_hour")), 80.0)
        self.assertAlmostEqual(keyblade.calculate_hp(data, self.config(hp_source="7_day")), 30.0)

    def test_last_known_values_before_first_response(self):
        # Session start / after /clear: no rate_limits yet → no flash to 100%
        keyblade.resolve_hp(make_data(rate_limits=self.limits(five=60)), self.config())
        subscriber = {"method": "claude.ai", "provider": "firstParty", "plan": "max"}
        hp = keyblade.resolve_hp(make_data(), self.config(), auth=subscriber)
        self.assertAlmostEqual(hp["pct"], 40.0)
        self.assertAlmostEqual(keyblade.calculate_hp(make_data(), self.config(hp_source="5_hour")), 40.0)

    def test_rolled_over_window_is_ignored(self):
        keyblade._write_state({"usage_cache": {"five_hour": {"used": 90.0, "resets_at": time.time() - 10}}})
        self.assertEqual(keyblade.calculate_hp(make_data(), self.config(hp_source="5_hour")), 100.0)

    def test_legacy_cache_format_is_ignored(self):
        keyblade._write_state({"usage_cache": {"ts": time.time(), "five_hour": 90.0, "seven_day": 10.0}})
        self.assertEqual(keyblade.get_plan_usage(make_data()), {})

    def test_api_key_session_uses_cost_budget(self):
        # Even with a subscription's cached usage around, an API-key session
        # isn't billed against it
        keyblade._write_state({"usage_cache": {"five_hour": {"used": 90.0, "resets_at": None}}})
        api = {"method": "api_key", "provider": "firstParty", "plan": None}
        hp = keyblade.resolve_hp(make_data(), self.config(hp_budget_usd=5.0), auth=api)
        self.assertEqual(hp["source"], "cost_budget")
        self.assertAlmostEqual(hp["pct"], 70.0)  # $1.50 of $5

    def test_unknown_auth_uses_cost_budget(self):
        self.assertEqual(keyblade.resolve_hp(make_data(), self.config())["source"], "cost_budget")

    def test_subscriber_without_plan_data_uses_cost_budget(self):
        # Team/Enterprise never get rate_limits; Pro/Max before any data exists
        for plan in ("team", "enterprise", "pro"):
            subscriber = {"method": "claude.ai", "provider": "firstParty", "plan": plan}
            hp = keyblade.resolve_hp(make_data(), self.config(hp_budget_usd=5.0), auth=subscriber)
            self.assertEqual((hp["source"], round(hp["pct"])), ("cost_budget", 70), plan)

    def test_spend_limit(self):
        data = make_data(rate_limits={"spend_limit": {
            "used_percentage": 62.8, "resets_at": time.time() + 86400, "used_usd": 314.12, "limit_usd": 500}})
        hp = keyblade.resolve_hp(data, self.config())
        self.assertAlmostEqual(hp["pct"], 37.2)
        self.assertEqual(hp["spend"], (314.12, 500))
        self.assertIn("$314/$500", strip(keyblade.render_classic(data, self.config())))

    def test_spend_limit_without_dollars(self):
        data = make_data(rate_limits={"spend_limit": {"used_percentage": 10, "resets_at": time.time() + 60}})
        hp = keyblade.resolve_hp(data, self.config(hp_source="spend_limit"))
        self.assertEqual((hp["pct"], hp["spend"]), (90.0, None))

    def test_cost_budget(self):
        self.assertAlmostEqual(keyblade.calculate_hp(make_data(), self.config(hp_source="cost_budget")), 70.0)
        self.assertEqual(keyblade.calculate_hp(make_data(), self.config(hp_source="cost_budget", hp_budget_usd=0)), 100.0)

    def test_cure_countdown_rendered(self):
        data = make_data(rate_limits=self.limits(five=30, resets_in=7500))
        line2 = strip(keyblade.render_classic(data, self.config()).split("\n")[1])
        self.assertIn(f"{keyblade.CURE_ICON} 2h0", line2)
        hidden = strip(keyblade.render_classic(data, self.config(show_hp_reset=False)))
        self.assertNotIn(keyblade.CURE_ICON, hidden)


# ─── Auth ────────────────────────────────────────────────────────

class TestAuth(KeybladeTestCase):
    MAX = {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty",
           "subscriptionType": "max", "email": "sora@destiny.islands", "orgName": "Destiny Islands"}

    def fake_claude(self, payload, exit_code=0):
        """Install a fake `claude` that prints `payload` and counts its calls."""
        path = os.path.join(self.tmp, "bin", "claude")
        self.calls_file = os.path.join(self.tmp, "claude_calls")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        body = payload if isinstance(payload, str) else json.dumps(payload)
        with open(path, "w") as f:
            f.write(f"#!/bin/sh\necho \"$@\" >> {shlex.quote(self.calls_file)}\n"
                    f"cat <<'EOF'\n{body}\nEOF\nexit {exit_code}\n")
        os.chmod(path, 0o755)
        os.environ["CLAUDE_CODE_EXECPATH"] = path
        self.patch("_claude_executable", self._originals["_claude_executable"])
        return path

    def calls(self):
        try:
            with open(self.calls_file) as f:
                return f.read().splitlines()
        except FileNotFoundError:
            return []

    def test_run_auth_status_keeps_no_identity(self):
        self.fake_claude(self.MAX)
        status = keyblade._run_auth_status()
        self.assertEqual(status["authMethod"], "claude.ai")
        self.assertEqual(status["subscriptionType"], "max")
        self.assertNotIn("email", status)
        self.assertNotIn("orgName", status)
        self.assertEqual(self.calls(), ["auth status --json"])

    def test_resolve_caches_per_auth_environment(self):
        self.fake_claude(self.MAX)
        auth = keyblade.resolve_auth(make_data(), self.config())
        self.assertEqual(auth, {"method": "claude.ai", "provider": "firstParty", "plan": "max"})
        keyblade.resolve_auth(make_data(session_id="after-clear"), self.config())
        self.assertEqual(len(self.calls()), 1)
        with open(keyblade.STATE_FILE) as f:
            self.assertNotIn("sora@", f.read())

    def test_expired_cache_refreshes(self):
        self.fake_claude(self.MAX)
        keyblade.resolve_auth(make_data(), self.config(auth_cache_ttl=600))
        state = keyblade._read_state()
        for entry in state["auth_cache"].values():
            entry["ts"] = 0
        keyblade._write_state(state)
        keyblade.resolve_auth(make_data(), self.config(auth_cache_ttl=600))
        self.assertEqual(len(self.calls()), 2)

    def test_failed_refresh_keeps_last_status(self):
        self.fake_claude(self.MAX)
        keyblade.resolve_auth(make_data(), self.config())
        self.fake_claude("not json", exit_code=1)
        key = keyblade._auth_fingerprint()
        entry = keyblade.refresh_auth(key, 600)
        self.assertEqual(entry["status"]["subscriptionType"], "max")
        self.assertLess(entry["ts"], time.time() - 500)  # retries within about a minute

    def test_refresh_backoff_avoids_stampede(self):
        calls = []
        self.patch("_claude_executable", lambda: "/fake/claude")
        self.patch("_spawn_auth_refresh", lambda key, ttl: calls.append(key))
        keyblade.resolve_auth(make_data(), self.config())
        keyblade.resolve_auth(make_data(), self.config())
        self.assertEqual(len(calls), 1)

    def test_api_key_badge(self):
        self.fake_claude({"loggedIn": True, "authMethod": "api_key", "apiProvider": "firstParty",
                          "apiKeySource": "ANTHROPIC_API_KEY"})
        out = strip(keyblade.render_classic(make_data(), self.config()))
        self.assertIn(f"{keyblade.AUTH_ICON} API", out)

    def test_payload_rate_limits_prove_subscription(self):
        self.fake_claude({"loggedIn": True, "authMethod": "api_key", "apiProvider": "firstParty"})
        data = make_data(rate_limits={"five_hour": {"used_percentage": 5, "resets_at": time.time() + 60}})
        self.assertEqual(keyblade.resolve_auth(data, self.config())["method"], "claude.ai")

    def test_env_fallback(self):
        cases = [
            ({"ANTHROPIC_API_KEY": "sk-test"}, {"authMethod": "api_key", "apiProvider": "firstParty"}),
            ({"CLAUDE_CODE_USE_BEDROCK": "1"}, {"apiProvider": "bedrock"}),
            ({"CLAUDE_CODE_USE_VERTEX": "true"}, {"apiProvider": "vertex"}),
            ({"CLAUDE_CODE_USE_BEDROCK": "0"}, None),
            ({"CLAUDE_CODE_OAUTH_TOKEN": "tok"}, {"authMethod": "oauth_token", "apiProvider": "firstParty"}),
            ({}, None),
        ]
        for env, expected in cases:
            for var in keyblade.AUTH_ENV_VARS:
                os.environ.pop(var, None)
            os.environ.update(env)
            self.assertEqual(keyblade._auth_from_env(), expected, env)

    def test_api_key_helper_from_settings(self):
        os.makedirs(os.environ["CLAUDE_CONFIG_DIR"])
        with open(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"), "w") as f:
            json.dump({"apiKeyHelper": "~/bin/get-key"}, f)
        self.assertEqual(keyblade._auth_from_env()["authMethod"], "api_key_helper")

    def test_fingerprint_tracks_auth_env_not_values(self):
        base = keyblade._auth_fingerprint()
        os.environ["ANTHROPIC_API_KEY"] = "sk-one"
        with_key = keyblade._auth_fingerprint()
        os.environ["ANTHROPIC_API_KEY"] = "sk-two"
        self.assertNotEqual(base, with_key)
        self.assertEqual(with_key, keyblade._auth_fingerprint())

    def test_executable_resolution(self):
        self.patch("_claude_executable", self._originals["_claude_executable"])
        fake = self.fake_claude(self.MAX)
        self.assertEqual(keyblade._claude_executable(), fake)
        os.environ["CLAUDE_CODE_EXECPATH"] = "/usr/bin/node"
        self.assertNotEqual(keyblade._claude_executable(), "/usr/bin/node")

    def test_badges(self):
        cases = [
            ({"method": "claude.ai", "provider": "firstParty", "plan": "max"}, ("Max", "bright_cyan")),
            ({"method": "claude.ai", "provider": "firstParty", "plan": "claude_enterprise"}, ("Enterprise", "bright_cyan")),
            ({"method": "claude.ai", "provider": "firstParty", "plan": None}, ("Claude.ai", "bright_cyan")),
            ({"method": "api_key", "provider": "firstParty"}, ("API", "bright_orange")),
            ({"method": "api_key_helper", "provider": "firstParty"}, ("API", "bright_orange")),
            ({"method": "oauth_token", "provider": "firstParty"}, ("OAuth", "bright_cyan")),
            ({"method": None, "provider": "bedrock"}, ("Bedrock", "white")),
            ({"method": None, "provider": "gateway"}, ("Gateway", "white")),
            ({"method": None, "provider": None}, (None, None)),
            (None, (None, None)),
        ]
        for auth, expected in cases:
            self.assertEqual(keyblade.auth_badge(auth), expected, auth)

    def test_show_auth_false(self):
        os.environ["ANTHROPIC_API_KEY"] = "sk-test"
        out = keyblade.render_classic(make_data(), self.config(show_auth=False))
        self.assertNotIn(keyblade.AUTH_ICON, out)

    def test_subscription_detection(self):
        self.assertTrue(keyblade.is_subscription({"method": "claude.ai", "provider": "firstParty"}))
        self.assertTrue(keyblade.is_subscription({"method": "oauth_token", "provider": None}))
        self.assertFalse(keyblade.is_subscription({"method": "api_key", "provider": "firstParty"}))
        self.assertFalse(keyblade.is_subscription({"method": "claude.ai", "provider": "bedrock"}))
        self.assertFalse(keyblade.is_subscription(None))


# ─── Git ─────────────────────────────────────────────────────────

class TestGitInfo(KeybladeTestCase):
    def info(self, path, **config):
        return keyblade.git_info(self.repo_data(path), self.config(git_cache_ttl=0, **config))

    def test_clean_repo(self):
        info = self.info(self.make_repo())
        self.assertEqual((info["branch"], info["files"], info["lines"]), ("main", 0, 0))
        self.assertEqual(len(info["head"]), 40)

    def test_modified_tracked_file(self):
        repo = self.make_repo()
        self.write(repo, "README.md", "line 1\nchanged\nline 3\nline 4\n")
        info = self.info(repo)
        self.assertEqual(info["files"], 1)
        self.assertEqual(info["lines"], 3)  # +2 -1

    def test_staged_and_unstaged_counted_against_head(self):
        repo = self.make_repo()
        self.write(repo, "README.md", "line 1\nline 2\nline 3\nstaged\n")
        git(repo, "add", "README.md")
        self.write(repo, "README.md", "line 1\nline 2\nline 3\nstaged\nunstaged\n")
        self.assertEqual(self.info(repo)["lines"], 2)

    def test_untracked_files_from_a_subdirectory(self):
        repo = self.make_repo()
        os.makedirs(os.path.join(repo, "src", "deep"))
        self.write(repo, "src/deep/new.py", "a\nb\nc\n")
        self.write(repo, "top.txt", "x\n")
        info = keyblade.git_info(self.repo_data(os.path.join(repo, "src")), self.config(git_cache_ttl=0))
        self.assertEqual((info["files"], info["lines"], info["untracked"]), (2, 4, 2))

    def test_exclude_untracked(self):
        repo = self.make_repo()
        self.write(repo, "new.txt", "a\nb\n")
        info = self.info(repo, drive_include_untracked=False)
        self.assertEqual((info["files"], info["lines"]), (0, 0))

    def test_binary_untracked_counts_no_lines(self):
        repo = self.make_repo()
        self.write(repo, "blob.bin", b"\x00\x01\n\n\n", mode="wb")
        info = self.info(repo)
        self.assertEqual((info["files"], info["lines"]), (1, 0))

    def test_rename_parsed_once(self):
        repo = self.make_repo()
        git(repo, "mv", "README.md", "GUIDE.md")
        self.write(repo, "other.txt", "1\n")
        info = self.info(repo)
        self.assertEqual(info["files"], 2)

    def test_detached_head_shows_short_sha(self):
        repo = self.make_repo()
        sha = git(repo, "rev-parse", "HEAD").strip()
        git(repo, "checkout", "-q", "--detach")
        self.assertEqual(self.info(repo)["branch"], sha[:7])

    def test_repo_without_commits(self):
        repo = self.make_repo(commit=False)
        self.write(repo, "a.txt", "1\n2\n")
        git(repo, "add", "a.txt")
        info = self.info(repo)
        self.assertEqual((info["branch"], info["head"], info["lines"]), ("main", "", 2))

    def test_ahead_of_upstream(self):
        origin = self.make_repo("origin")
        clone = os.path.join(self.tmp, "clone")
        git(self.tmp, "clone", "-q", origin, clone)
        self.write(clone, "new.txt", "1\n")
        git(clone, "add", "new.txt")
        git(clone, "commit", "-q", "-m", "ahead")
        info = self.info(clone)
        self.assertEqual((info["ahead"], info["behind"]), (1, 0))
        line1 = strip(keyblade.render_classic(self.repo_data(clone), self.config()).split("\n")[0])
        self.assertIn("↑1", line1)

    def test_not_a_repo(self):
        plain = os.path.join(self.tmp, "plain")
        os.makedirs(plain)
        self.assertIsNone(self.info(plain))
        self.assertEqual(keyblade.calculate_drive(self.repo_data(plain)), (0, 0))

    def test_cache_ttl(self):
        repo = self.make_repo()
        data, cfg = self.repo_data(repo), self.config(git_cache_ttl=60)
        self.assertEqual(keyblade.git_info(data, cfg)["files"], 0)
        self.write(repo, "new.txt", "1\n")
        self.assertEqual(keyblade.git_info(data, cfg)["files"], 0)  # cached
        self.assertEqual(keyblade.git_info(data, self.config(git_cache_ttl=0))["files"], 1)

    def test_calculate_drive(self):
        repo = self.make_repo()
        self.write(repo, "new.txt", "1\n2\n")
        self.assertEqual(keyblade.calculate_drive(self.repo_data(repo), self.config(git_cache_ttl=0)), (1, 2))

    def test_status_does_not_take_index_lock(self):
        # A held index.lock (e.g. Claude mid-commit) must not break the statusline
        repo = self.make_repo()
        open(os.path.join(repo, ".git", "index.lock"), "w").close()
        self.write(repo, "README.md", "changed\n")
        info = self.info(repo)
        self.assertEqual(info["files"], 1)


class TestLevelSources(KeybladeTestCase):
    def commit(self, repo, name):
        self.write(repo, name, "x\n")
        git(repo, "add", name)
        git(repo, "commit", "-q", "-m", name)

    def test_commits_since_session_start(self):
        repo = self.make_repo()
        data, cfg = self.repo_data(repo), self.config(level_source="commits", level_per=1, git_cache_ttl=0)
        self.assertEqual(keyblade.calculate_exp(data, cfg), 0)  # anchors HEAD
        self.commit(repo, "a.txt")
        self.commit(repo, "b.txt")
        self.assertEqual(keyblade.calculate_exp(data, cfg), 2)
        self.assertEqual(keyblade.calculate_level(data, cfg), 3)

    def test_files_touched_since_session_start(self):
        repo = self.make_repo()
        data, cfg = self.repo_data(repo), self.config(level_source="files", git_cache_ttl=0)
        self.assertEqual(keyblade.calculate_exp(data, cfg), 0)
        self.commit(repo, "a.txt")                         # committed this session
        self.write(repo, "README.md", "edited\n")          # modified
        self.write(repo, "new.txt", "1\n")                 # untracked
        self.assertEqual(keyblade.calculate_exp(data, cfg), 3)

    def test_new_session_starts_over(self):
        repo = self.make_repo()
        cfg = self.config(level_source="commits", git_cache_ttl=0)
        keyblade.calculate_exp(self.repo_data(repo), cfg)
        self.commit(repo, "a.txt")
        self.assertEqual(keyblade.calculate_exp(self.repo_data(repo, session_id="new"), cfg), 0)

    def test_outside_git(self):
        self.assertEqual(keyblade.calculate_exp(make_data(), self.config(level_source="commits")), 0)


class TestWorldSegments(KeybladeTestCase):
    def line1(self, data, **cfg):
        return keyblade.render_classic(data, self.config(**cfg)).split("\n")[0]

    def test_repo_link_with_branch(self):
        repo = self.make_repo()
        data = self.repo_data(repo)
        data["workspace"]["repo"] = {"host": "github.com", "owner": "sora", "name": "destiny"}
        self.assertIn("\033]8;;https://github.com/sora/destiny/tree/main\a", self.line1(data))

    def test_repo_url_hosts(self):
        data = {"workspace": {"repo": {"host": "gitlab.com", "owner": "group/sub", "name": "r"}}}
        self.assertEqual(keyblade.repo_url(data, "feat/x"), "https://gitlab.com/group/sub/r/-/tree/feat/x")
        data["workspace"]["repo"]["host"] = "git.example.com"
        self.assertEqual(keyblade.repo_url(data, "main"), "https://git.example.com/group/sub/r")
        self.assertEqual(keyblade.repo_url({}, "main"), "")

    def test_worktree_marker(self):
        data = make_data(worktree={"name": "my-feature", "path": "/x"})
        self.assertIn(f"{keyblade.WORKTREE_ICON} my-feature", strip(self.line1(data)))
        data = make_data(workspace={"current_dir": "/nonexistent/wt", "git_worktree": "feature-xyz"})
        self.assertIn("feature-xyz", strip(self.line1(data)))
        self.assertNotIn("feature-xyz", strip(self.line1(data, show_worktree=False)))

    def test_added_dirs(self):
        data = make_data()
        data["workspace"]["added_dirs"] = ["/a", "/b"]
        self.assertIn("myapp +2", strip(self.line1(data)))

    def test_show_world_false(self):
        self.assertNotIn(keyblade.WORLD_ICON, self.line1(make_data(), show_world=False))


class TestPRBadge(KeybladeTestCase):
    def line1(self, pr, **cfg):
        return keyblade.render_classic(make_data(pr=pr), self.config(**cfg)).split("\n")[0]

    def test_states(self):
        for state, glyph in (("approved", "✓"), ("changes_requested", "✗"),
                             ("pending", "○"), ("draft", "◌")):
            self.assertIn(f"#7 {glyph}", strip(self.line1({"number": 7, "review_state": state})), state)

    def test_no_state(self):
        self.assertIn("#7", strip(self.line1({"number": 7})))

    def test_link(self):
        out = self.line1({"number": 7, "url": "https://github.com/o/r/pull/7"})
        self.assertIn("\033]8;;https://github.com/o/r/pull/7\a#7", out)
        self.assertNotIn("\033]8;;https://github.com/o/r/pull/7", self.line1(
            {"number": 7, "url": "https://github.com/o/r/pull/7"}, hyperlinks=False))

    def test_gitlab_merge_request(self):
        self.assertIn("!42", strip(self.line1({"number": 42, "kind": "mr"})))

    def test_hidden(self):
        self.assertNotIn("#7", strip(self.line1({"number": 7}, show_pr=False)))
        self.assertNotIn("#", strip(self.line1({})))


class TestSegments(KeybladeTestCase):
    def test_fast_mode(self):
        out = keyblade.render_classic(make_data(fast_mode=True), self.config())
        self.assertIn(keyblade.HASTE_ICON, out)
        self.assertNotIn(keyblade.HASTE_ICON, keyblade.render_classic(
            make_data(fast_mode=True), self.config(show_fast_mode=False)))

    def test_session_name_sanitized(self):
        out = keyblade.render_full_rpg(make_data(session_name="evil\x1b]0;pwned\x07name"), self.config())
        self.assertIn("evil]0;pwnedname", strip(out))
        self.assertNotIn("\x1b]0;", out)

    def test_session_name_truncated(self):
        out = strip(keyblade.render_full_rpg(make_data(session_name="x" * 80), self.config()))
        self.assertIn("x" * 27 + "…", out)

    def test_focus_gauge(self):
        warm = {"warm": True, "caching_observed": True, "hit_ratio": 0.914, "expires_at": time.time() + 600}
        out = strip(keyblade.render_full_rpg(make_data(prompt_cache=warm), self.config()))
        self.assertIn(f"{keyblade.FOCUS_ICON} 91% 9m", out)
        cold = dict(warm, warm=False, expires_at=None)
        self.assertIn(f"{keyblade.FOCUS_ICON} 91% cold",
                      strip(keyblade.render_full_rpg(make_data(prompt_cache=cold), self.config())))
        off = dict(warm, caching_observed=False)
        self.assertNotIn(keyblade.FOCUS_ICON, keyblade.render_full_rpg(make_data(prompt_cache=off), self.config()))
        self.assertNotIn(keyblade.FOCUS_ICON, keyblade.render_full_rpg(
            make_data(prompt_cache=warm), self.config(show_focus=False)))

    def test_vim_mode_opt_in(self):
        data = make_data(vim={"mode": "NORMAL"})
        self.assertNotIn("NORMAL", keyblade.render_classic(data, self.config()))
        self.assertIn("-- NORMAL --", strip(keyblade.render_classic(data, self.config(show_vim_mode=True))))

    def test_party_hidden_by_config(self):
        data = make_data(agent={"name": "security-reviewer"})
        self.assertNotIn("security-reviewer", keyblade.render_classic(data, self.config(show_party=False)))


# ─── Party panel ─────────────────────────────────────────────────

class TestPartyPanel(KeybladeTestCase):
    NOW = 1_800_000_000.0

    def task(self, tid="t1", **overrides):
        task = {"id": tid, "type": "local_agent", "agentType": "Explore", "status": "running",
                "description": "Find the bug", "label": "Searching keyblade.py for payload handling",
                "startTime": self.NOW * 1000 - 65_000, "model": "claude-haiku-5-5", "effort": "low",
                "contextWindowSize": 200_000, "tokenCount": 50_000, "tokenSamples": [1, 2], "cwd": "/x"}
        task.update(overrides)
        return task

    def rows(self, tasks, columns=100, now=None, **cfg):
        payload = {"columns": columns, "tasks": tasks}
        out = keyblade.render_party(payload, self.config(**cfg), now=self.NOW if now is None else now)
        return [json.loads(r) for r in out]

    def content(self, tasks, **kw):
        return [strip(r["content"]) for r in self.rows(tasks, **kw)]

    def test_running_row_is_party_chatter(self):
        (row,) = self.content([self.task()])
        self.assertTrue(row.startswith(("✦ Aladdin", "✧ Aladdin")), row)
        self.assertIn('"Searching keyblade.py for payload handling…"', row)
        self.assertTrue(row.rstrip().endswith("1m05s"), row)

    def test_no_keyblades_forms_or_bars(self):
        (row,) = self.content([self.task()])
        for piece in (keyblade.KEYBLADE_ICON, keyblade.FORM_ICON, keyblade.MP_ICON, keyblade.BAR_FULL, "Valor"):
            self.assertNotIn(piece, row)

    def test_roles_map_to_party_members(self):
        cases = {
            "code-reviewer": "Riku", "security-reviewer": "Donald", "test-writer": "Goofy",
            "Explore": "Aladdin", "Plan": "Mulan", "debugger": "Tron", "docs-writer": "Beast",
            "pr-creator": "Jack Sparrow", "releaseManager": "Jack Sparrow",
        }
        for agent_type, member in cases.items():
            got = keyblade.party_role_member({"agentType": agent_type}, self.config())
            self.assertEqual(got, member, agent_type)

    def test_short_keys_need_whole_words(self):
        for agent_type in ("prompt-engineer", "docker-expert", "general-purpose", "qualifier"):
            self.assertIsNone(keyblade.party_role_member({"agentType": agent_type}, self.config()), agent_type)

    def test_name_counts_as_role(self):
        task = {"agentType": "general-purpose", "name": "security-reviewer"}
        self.assertEqual(keyblade.party_role_member(task, self.config()), "Donald")

    def test_only_real_party_members(self):
        cast = {m for _, m in keyblade.PARTY_ROLES} | set(keyblade.PARTY_GUESTS)
        self.assertEqual(cast, set(keyblade.PARTY_COLORS))
        for not_a_fighter in ("Jiminy", "Naminé", "Chip", "Dale", "Yen Sid", "Moogle"):
            self.assertNotIn(not_a_fighter, cast)

    def test_unknown_roles_get_world_guests(self):
        tasks = [self.task(f"g{i}", agentType="general-purpose") for i in range(3)]
        members = [r.split()[1] for r in self.content(tasks)]
        self.assertEqual(members, ["Simba", "Auron", "Ariel"])

    def test_no_two_visible_members_alike(self):
        tasks = [self.task("e1"), self.task("e2"), self.task("e3", agentType="general-purpose")]
        members = [r.split()[1] for r in self.content(tasks)]
        self.assertEqual(members[0], "Aladdin")
        self.assertEqual(len(set(members)), 3)

    def test_member_is_stable_for_a_subagent(self):
        first = self.content([self.task("e1"), self.task("e2")])
        second = self.content([self.task("e2")])  # e1 left the panel
        self.assertEqual(first[1].split()[1], second[0].split()[1])

    def test_config_override(self):
        cfg = {"party_members": {"Explore": "Tarzan", "my-agent": "Ariel"}}
        self.assertTrue(self.content([self.task()], **cfg)[0][2:].startswith("Tarzan"))
        self.assertIn("Ariel", self.content([self.task("t2", agentType="my-agent")], **cfg)[0])

    def test_twinkles_while_running(self):
        a = self.content([self.task()], now=self.NOW)[0][0]
        b = self.content([self.task()], now=self.NOW + 1)[0][0]
        self.assertEqual({a, b}, {"✦", "✧"})

    def test_completed_shows_check_and_total_time(self):
        self.rows([self.task()], now=self.NOW)                          # seen running
        (row,) = self.content([self.task(status="completed", label="Found it")], now=self.NOW + 30)
        self.assertTrue(row.startswith("✓ Aladdin"), row)
        self.assertIn('"Found it"', row)
        self.assertTrue(row.rstrip().endswith("1m35s"), row)            # 65s + 30s, then frozen
        (later,) = self.content([self.task(status="completed", label="Found it")], now=self.NOW + 999)
        self.assertTrue(later.rstrip().endswith("1m35s"), later)

    def test_knocked_out(self):
        for status, color in (("failed", "red"), ("killed", "dim")):
            (raw,) = self.rows([self.task(f"k-{status}", status=status, label="Ran out of context")])
            row = strip(raw["content"])
            self.assertTrue(row.startswith("✗"), row)
            self.assertIn('KO — "Ran out of context"', row)
            self.assertTrue(raw["content"].startswith(keyblade.ANSI[color]), status)

    def test_hp_only_when_low(self):
        (healthy,) = self.content([self.task(tokenCount=100_000)])
        self.assertNotIn(keyblade.HEART_ICON, healthy)
        (low,) = self.content([self.task(tokenCount=176_000)])
        self.assertIn(f"{keyblade.HEART_ICON} 12% low", low)

    def test_fits_columns_and_right_aligns_time(self):
        for columns in (100, 60, 40, 24):
            (row,) = self.content([self.task(label="L" * 200)], columns=columns)
            self.assertLessEqual(keyblade.visible_width(row), columns, columns)
        (row,) = self.content([self.task(label="short")], columns=80)
        self.assertEqual(keyblade.visible_width(row), 79)
        self.assertTrue(row.endswith("1m05s"))

    def test_names_padded_to_align_quotes(self):
        rows = self.content([self.task("a"), self.task("b", agentType="pr-creator")])
        self.assertEqual(rows[0].index('"'), rows[1].index('"'))

    def test_tasks_without_id_skipped(self):
        self.assertEqual(len(self.rows([self.task(), {"name": "no id"}, "junk"])), 1)

    def test_disabled(self):
        self.assertEqual(self.rows([self.task()], party_panel=False), [])

    def test_label_sanitized(self):
        (raw,) = self.rows([self.task(label="evil\x1b[2Jlabel")])
        self.assertNotIn("\x1b[2J", raw["content"])

    def test_assignments_pruned(self):
        for i in range(120):
            self.rows([self.task(f"p{i}")], now=self.NOW + i)
        self.assertEqual(len(keyblade._read_state()["party"]), 100)


# ─── State & settings ────────────────────────────────────────────

class TestStateFile(KeybladeTestCase):
    def test_round_trip_without_leftovers(self):
        keyblade._write_state({"a": 1})
        self.assertEqual(keyblade._read_state(), {"a": 1})
        self.assertEqual([f for f in os.listdir(self.tmp) if f.startswith(".keyblade.")], [])

    def test_corrupt_state_reads_empty(self):
        with open(keyblade.STATE_FILE, "w") as f:
            f.write("{not json")
        self.assertEqual(keyblade._read_state(), {})

    def test_projects_keyed_by_full_path(self):
        a = make_data(workspace={"current_dir": "/work/a/app"})
        b = make_data(workspace={"current_dir": "/work/b/app"})
        keyblade._write_project_state(a, {"level_up": {"level": 9, "ts": 0}})
        self.assertEqual(keyblade._read_project_state(b), {})

    def test_prune_keeps_newest(self):
        entries = {str(i): {"ts": i} for i in range(30)}
        kept = keyblade._prune(entries, keep=5)
        self.assertEqual(sorted(kept, key=int), ["25", "26", "27", "28", "29"])


class TestSettingsRegistration(KeybladeTestCase):
    def setUp(self):
        super().setUp()
        self.settings = os.path.join(self.tmp, "settings.json")

    def read(self):
        with open(self.settings) as f:
            return json.load(f)

    def save(self, obj):
        with open(self.settings, "w") as f:
            json.dump(obj, f)

    def test_fresh_install(self):
        keyblade.register_settings(self.settings, "/opt/keyblade/keyblade.py")
        s = self.read()
        self.assertEqual(s["statusLine"], {"type": "command", "command": "python3 /opt/keyblade/keyblade.py",
                                           "padding": 0, "refreshInterval": 30})
        self.assertEqual(s["subagentStatusLine"], {"type": "command",
                                                   "command": "python3 /opt/keyblade/keyblade.py --party"})

    def test_path_with_spaces_is_quoted(self):
        keyblade.register_settings(self.settings, "/Users/a b/keyblade.py")
        self.assertEqual(self.read()["statusLine"]["command"], "python3 '/Users/a b/keyblade.py'")

    def test_backs_up_and_restores_other_entries(self):
        self.save({"model": "opus", "statusLine": {"type": "command", "command": "~/mine.sh"},
                   "subagentStatusLine": {"type": "command", "command": "~/agents.sh"}})
        keyblade.register_settings(self.settings, "/k/keyblade.py")
        s = self.read()
        self.assertEqual(s["_statusLine_backup"]["command"], "~/mine.sh")
        self.assertEqual(s["_subagentStatusLine_backup"]["command"], "~/agents.sh")
        keyblade.unregister_settings(self.settings)
        self.assertEqual(self.read(), {"model": "opus", "statusLine": {"type": "command", "command": "~/mine.sh"},
                                       "subagentStatusLine": {"type": "command", "command": "~/agents.sh"}})

    def test_reinstall_keeps_user_tweaks(self):
        self.save({"statusLine": {"type": "command", "command": "python3 /old/keyblade.py",
                                  "padding": 2, "refreshInterval": 10, "hideVimModeIndicator": True}})
        keyblade.register_settings(self.settings, "/new/keyblade.py")
        sl = self.read()["statusLine"]
        self.assertEqual(sl["command"], "python3 /new/keyblade.py")
        self.assertEqual((sl["padding"], sl["refreshInterval"], sl["hideVimModeIndicator"]), (2, 10, True))
        self.assertNotIn("_statusLine_backup", self.read())

    def test_upgrade_adds_refresh_interval(self):
        self.save({"statusLine": {"type": "command", "command": "python3 /k/keyblade.py", "padding": 0}})
        keyblade.register_settings(self.settings, "/k/keyblade.py")
        self.assertEqual(self.read()["statusLine"]["refreshInterval"], 30)

    def test_unregister_leaves_foreign_entries(self):
        self.save({"statusLine": {"type": "command", "command": "~/mine.sh"}})
        keyblade.unregister_settings(self.settings)
        self.assertEqual(self.read()["statusLine"]["command"], "~/mine.sh")

    def test_invalid_json_is_never_clobbered(self):
        with open(self.settings, "w") as f:
            f.write("{oops")
        with self.assertRaises(ValueError):
            keyblade.register_settings(self.settings, "/k/keyblade.py")
        with open(self.settings) as f:
            self.assertEqual(f.read(), "{oops")

    def test_cli(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(keyblade.main(["--register-settings", self.settings, "/k/keyblade.py"]), 0)
            self.assertIn("keyblade", self.read()["statusLine"]["command"])
            self.assertEqual(keyblade.main(["--unregister-settings", self.settings]), 0)
            self.assertEqual(self.read(), {})
            self.assertEqual(keyblade.main(["--register-settings"]), 2)
        self.assertIn("statusLine registered.", out.getvalue())
        self.assertIn("--register-settings", err.getvalue())


# ─── Review regressions ──────────────────────────────────────────

class TestConfigRobustness(KeybladeTestCase):
    """A hand-edited config.json (the config skill has an LLM edit it) must
    never take the statusline down."""

    def write_config(self, raw):
        path = os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "hooks", "keyblade", "config.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(raw if isinstance(raw, bytes) else raw.encode())

    def test_wrong_types_fall_back_to_defaults(self):
        self.write_config(json.dumps({"colors": None, "drive_form_names": None, "keyblade_names": "x",
                                      "world_map": None, "drive_max_lines": "lots", "show_munny": "no",
                                      "hp_budget_usd": 25, "theme": "full_rpg"}))
        config = keyblade.load_config()
        self.assertEqual(config["colors"], keyblade.DEFAULT_CONFIG["colors"])
        self.assertEqual(config["keyblade_names"], keyblade.DEFAULT_CONFIG["keyblade_names"])
        self.assertEqual(config["world_map"], {})
        self.assertEqual(config["drive_max_lines"], 1000)
        self.assertIs(config["show_munny"], True)
        self.assertEqual((config["hp_budget_usd"], config["theme"]), (25, "full_rpg"))
        self.assertEqual(len(keyblade.render_full_rpg(make_data(), config).split("\n")), 3)

    def test_non_object_and_undecodable_configs(self):
        for raw in ("[1]", "null", "\"classic\"", b"{\"theme\": \"caf\xe9\"}"):
            self.write_config(raw)
            self.assertEqual(keyblade.load_config()["theme"], "classic", raw)


class TestSettingsSafety(KeybladeTestCase):
    def setUp(self):
        super().setUp()
        self.settings = os.path.join(self.tmp, "settings.json")
        with open(self.settings, "w", encoding="utf-8") as f:
            json.dump({"env": {"GREETING": "café ✨"}, "permissions": {"allow": ["Bash(ls)"]}}, f)

    def test_failed_write_leaves_original_intact(self):
        with open(self.settings, "rb") as f:
            before = f.read()
        with self.assertRaises(TypeError):
            keyblade._write_settings(self.settings, {"unserializable": {1, 2}})
        with open(self.settings, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertEqual([n for n in os.listdir(self.tmp) if n.startswith(".settings.keyblade.")], [])

    def test_symlink_and_mode_preserved(self):
        real = os.path.join(self.tmp, "dotfiles-settings.json")
        os.rename(self.settings, real)
        os.symlink(real, self.settings)
        os.chmod(real, 0o640)
        keyblade.register_settings(self.settings, "/k/keyblade.py")
        self.assertTrue(os.path.islink(self.settings))
        self.assertEqual(os.stat(real).st_mode & 0o777, 0o640)
        with open(real, encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["env"]["GREETING"], "café ✨")
        self.assertIn("statusLine", saved)

    def test_keyblade_wrapper_scripts_are_not_ours(self):
        with open(self.settings, "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "~/bin/statusline-with-keyblade.sh"}}, f)
        keyblade.register_settings(self.settings, "/k/keyblade.py")
        with open(self.settings) as f:
            self.assertEqual(json.load(f)["_statusLine_backup"]["command"], "~/bin/statusline-with-keyblade.sh")
        keyblade.unregister_settings(self.settings)
        with open(self.settings) as f:
            self.assertEqual(json.load(f)["statusLine"]["command"], "~/bin/statusline-with-keyblade.sh")

    def test_command_matching(self):
        self.assertTrue(keyblade._is_keyblade_command({"command": "python3 /x/hooks/keyblade/keyblade.py"}))
        self.assertTrue(keyblade._is_keyblade_command("python3 '/a b/keyblade.py' --party"))
        self.assertFalse(keyblade._is_keyblade_command({"command": "~/bin/keyblade-wrapper.sh"}))
        self.assertFalse(keyblade._is_keyblade_command({"command": None}))


class TestReviewRegressions(KeybladeTestCase):
    def test_mp_zero_remaining_is_empty_not_full(self):
        data = make_data()
        data["context_window"]["remaining_percentage"] = 0
        self.assertEqual(keyblade.calculate_mp(data), 0)
        self.assertIn("Anti Form", keyblade.render_classic(data, self.config()))

    def test_file_named_head_does_not_break_line_count(self):
        repo = self.make_repo()
        self.write(repo, "README.md", "line 1\nchanged\nline 3\nline 4\n")
        self.write(repo, "web/HEAD", "")
        info = keyblade.git_info(self.repo_data(os.path.join(repo, "web")), self.config(git_cache_ttl=0))
        self.assertEqual(info["lines"], 3)

    def test_untracked_fifo_symlink_does_not_hang(self):
        repo = self.make_repo()
        fifo = os.path.join(self.tmp, "pipe")
        os.mkfifo(fifo)
        os.symlink(fifo, os.path.join(repo, "link-to-pipe"))
        outside = self.write(self.tmp, "outside.txt", "1\n" * 500)
        os.symlink(outside, os.path.join(repo, "link-to-outside"))
        info = keyblade.git_info(self.repo_data(repo), self.config(git_cache_ttl=0))
        self.assertEqual((info["untracked"], info["lines"]), (2, 0))

    def test_level_up_is_per_session(self):
        a = make_data(session_id="A")
        b = make_data(session_id="B")
        a["cost"].update(total_lines_added=500, total_lines_removed=0)
        b["cost"].update(total_lines_added=10, total_lines_removed=0)
        keyblade._write_level_state(a, 6, 0)
        keyblade._write_level_state(b, 1, 0)
        cfg = self.config(theme="full_rpg")
        for data in (a, b, a, b):
            self.assertNotIn("LEVEL UP", keyblade.render_full_rpg(data, cfg), data["session_id"])

    def test_projects_map_is_pruned(self):
        for i in range(60):
            keyblade._write_project_state(make_data(workspace={"current_dir": f"/w/p{i}"}), {"save_point": {}})
        projects = keyblade._read_state()["projects"]
        self.assertEqual(len(projects), 50)
        self.assertIn("/w/p59", projects)
        self.assertNotIn("/w/p0", projects)

    def test_party_name_truncated_to_columns(self):
        task = {"id": "t", "name": "a-very-long-custom-agent-name-for-testing", "status": "running"}
        (row,) = keyblade.render_party({"columns": 30, "tasks": [task]}, self.config())
        self.assertLessEqual(keyblade.visible_width(json.loads(row)["content"]), 30)


class TestSessionProgressAccuracy(KeybladeTestCase):
    def commit(self, repo, name, email="sora@example.com"):
        self.write(repo, name, "x\n")
        git(repo, "add", name)
        subprocess.run(["git", "-c", "user.name=X", "-c", f"user.email={email}", "-c", "commit.gpgsign=false",
                        "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", name],
                       cwd=repo, check=True, capture_output=True)

    def setUp(self):
        super().setUp()
        self.repo = self.make_repo()
        git(self.repo, "config", "user.email", "sora@example.com")
        self.cfg = self.config(level_source="commits", git_cache_ttl=0)

    def exp(self, source="commits", cwd=None):
        return keyblade.calculate_exp(self.repo_data(cwd or self.repo), dict(self.cfg, level_source=source))

    def test_branch_switch_does_not_count_existing_commits(self):
        git(self.repo, "checkout", "-q", "-b", "feature")
        for i in range(5):
            self.commit(self.repo, f"f{i}.txt")
        git(self.repo, "checkout", "-q", "main")
        time.sleep(1.1)  # session starts after those commits
        self.assertEqual(self.exp(), 0)
        git(self.repo, "checkout", "-q", "feature")
        self.assertEqual(self.exp(), 0)

    def test_other_authors_do_not_count(self):
        self.assertEqual(self.exp(), 0)
        self.commit(self.repo, "mine.txt")
        self.commit(self.repo, "theirs.txt", email="riku@example.com")
        self.assertEqual(self.exp(), 1)

    def test_cwd_changes_keep_progress(self):
        os.makedirs(os.path.join(self.repo, "sub"))
        self.assertEqual(self.exp(), 0)
        self.commit(self.repo, "a.txt")
        self.assertEqual(self.exp(cwd=os.path.join(self.repo, "sub")), 1)
        self.assertEqual(self.exp(), 1)

    def test_preexisting_dirty_files_are_not_progress(self):
        self.write(self.repo, "README.md", "already dirty\n")
        self.write(self.repo, "old-untracked.txt", "1\n")
        self.assertEqual(self.exp("files"), 0)
        self.write(self.repo, "new.txt", "1\n")
        self.commit(self.repo, "committed.txt")
        self.assertEqual(self.exp("files"), 2)


class TestInstallScripts(KeybladeTestCase):
    """install.sh / uninstall.sh end to end in a sandbox config dir."""

    def setUp(self):
        super().setUp()
        self.base = os.path.join(self.tmp, "claude-home")
        os.makedirs(self.base)
        self.settings = os.path.join(self.base, "settings.json")
        with open(self.settings, "w") as f:
            json.dump({"model": "opus", "statusLine": {"type": "command", "command": "~/mine.sh"}}, f)
        self.hooks = os.path.join(self.base, "hooks", "keyblade")

    def sh(self, script, *args):
        env = {k: v for k, v in os.environ.items() if k not in ISOLATED_ENV}
        env.update(CLAUDE_CONFIG_DIR=self.base, TMPDIR=self.tmp + "/")
        return subprocess.run(["bash", script, *args], capture_output=True, text=True, env=env, timeout=60)

    def read_settings(self):
        with open(self.settings) as f:
            return json.load(f)

    def test_install_update_uninstall(self):
        r = self.sh(os.path.join(HERE, "install.sh"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("keyblade.py", self.read_settings()["statusLine"]["command"])
        # Customize, then update: config survives
        with open(os.path.join(self.hooks, "config.json"), "w") as f:
            json.dump({"theme": "minimal", "hp_budget_usd": 42}, f)
        self.assertEqual(self.sh(os.path.join(HERE, "install.sh")).returncode, 0)
        with open(os.path.join(self.hooks, "config.json")) as f:
            self.assertEqual(json.load(f), {"theme": "minimal", "hp_budget_usd": 42})
        # Uninstall restores the previous statusLine and clears runtime state
        for name in ("keyblade_state.json", "keyblade_git_abc.json", "keyblade_anchor_abc.json"):
            open(os.path.join(self.tmp, name), "w").close()
        r = self.sh(os.path.join(self.hooks, "uninstall.sh"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.read_settings(), {"model": "opus", "statusLine": {"type": "command", "command": "~/mine.sh"}})
        self.assertFalse(os.path.exists(self.hooks))
        self.assertFalse([n for n in os.listdir(self.tmp) if n.startswith("keyblade_")])

    def test_dangling_symlinks_from_homebrew_keep_config(self):
        os.makedirs(self.hooks)
        os.symlink("/nonexistent/Cellar/1.0/keyblade.py", os.path.join(self.hooks, "keyblade.py"))
        with open(os.path.join(self.hooks, "config.json"), "w") as f:
            json.dump({"theme": "minimal"}, f)
        r = self.sh(os.path.join(HERE, "install.sh"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.islink(os.path.join(self.hooks, "keyblade.py")))
        with open(os.path.join(self.hooks, "config.json")) as f:
            self.assertEqual(json.load(f), {"theme": "minimal"})

    def test_install_does_not_write_through_symlinks(self):
        os.makedirs(self.hooks)
        cellar = self.write(self.tmp, "cellar/keyblade.py", "# brew-owned\n")
        os.symlink(cellar, os.path.join(self.hooks, "keyblade.py"))
        self.assertEqual(self.sh(os.path.join(HERE, "install.sh")).returncode, 0)
        with open(cellar) as f:
            self.assertEqual(f.read(), "# brew-owned\n")

    def test_theme_argument(self):
        r = self.sh(os.path.join(HERE, "install.sh"), "full_rpg")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.hooks, "config.json")) as f:
            self.assertEqual(json.load(f)["theme"], "full_rpg")

    def test_unknown_theme_rejected_before_any_change(self):
        r = self.sh(os.path.join(HERE, "install.sh"), "full_rpgg'; import os #")
        self.assertEqual(r.returncode, 1)
        self.assertIn("unknown theme", r.stdout)
        self.assertFalse(os.path.exists(self.hooks))
        self.assertEqual(self.read_settings()["statusLine"]["command"], "~/mine.sh")


# ─── End to end (subprocess, like Claude Code runs it) ───────────

class TestCommandLine(KeybladeTestCase):
    def run_script(self, args=(), stdin="", **env):
        fake = os.path.join(self.tmp, "bin", "claude")
        os.makedirs(os.path.dirname(fake), exist_ok=True)
        with open(fake, "w") as f:
            f.write('#!/bin/sh\necho \'{"loggedIn": true, "authMethod": "claude.ai", '
                    '"apiProvider": "firstParty", "subscriptionType": "pro"}\'\n')
        os.chmod(fake, 0o755)
        full_env = {k: v for k, v in os.environ.items() if k not in ISOLATED_ENV}
        full_env.update({
            "CLAUDE_CONFIG_DIR": os.path.join(self.tmp, "claude"),
            "KEYBLADE_STATE_FILE": os.path.join(self.tmp, "cli_state.json"),
            "CLAUDE_CODE_EXECPATH": fake,
            "TMPDIR": self.tmp,
            "COLORTERM": "truecolor",
        })
        full_env.update(env)
        return subprocess.run([sys.executable, SCRIPT, *args], input=stdin, capture_output=True,
                              text=True, env=full_env, timeout=30)

    def test_statusline(self):
        r = self.run_script(stdin=json.dumps(make_data(version="2.1.295", effort={"level": "max"})))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = strip(r.stdout)
        self.assertEqual(len(out.rstrip("\n").split("\n")), 2)
        self.assertIn("Ultima Weapon", out)
        self.assertIn("Final Form", out)

    def test_theme_from_config(self):
        cfg = os.path.join(self.tmp, "claude", "hooks", "keyblade", "config.json")
        os.makedirs(os.path.dirname(cfg))
        with open(cfg, "w") as f:
            json.dump({"theme": "full_rpg"}, f)
        r = self.run_script(stdin=json.dumps(make_data()))
        self.assertEqual(len(r.stdout.rstrip("\n").split("\n")), 3)

    def test_respects_columns(self):
        r = self.run_script(stdin=json.dumps(make_data(session_name="x" * 50)), COLUMNS="50")
        for line in r.stdout.rstrip("\n").split("\n"):
            self.assertLessEqual(keyblade.visible_width(line), 46)

    def test_bad_json_prints_fallback(self):
        r = self.run_script(stdin="{nope")
        self.assertEqual((r.returncode, strip(r.stdout).strip()), (0, f"{keyblade.KEYBLADE_ICON}  Keyblade"))

    def test_empty_stdin(self):
        r = self.run_script(stdin="")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Starlight", r.stdout)

    def test_party_mode(self):
        payload = {"columns": 80, "tasks": [{"id": "abc", "name": "Explore", "status": "running"}]}
        r = self.run_script(["--party"], stdin=json.dumps(payload))
        rows = [json.loads(l) for l in r.stdout.splitlines()]
        self.assertEqual([row["id"] for row in rows], ["abc"])

    def test_party_mode_bad_input_prints_nothing(self):
        r = self.run_script(["--party"], stdin="garbage")
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_refresh_auth_writes_cache(self):
        r = self.run_script(["--refresh-auth", "k1", "600"])
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.tmp, "cli_state.json")) as f:
            self.assertEqual(json.load(f)["auth_cache"]["k1"]["status"]["subscriptionType"], "pro")

    def test_bad_config_prints_fallback_not_blank(self):
        cfg = os.path.join(self.tmp, "claude", "hooks", "keyblade", "config.json")
        os.makedirs(os.path.dirname(cfg))
        with open(cfg, "w") as f:
            f.write('{"colors": null, "keyblade_names": "x", "world_map": null}')
        r = self.run_script(stdin=json.dumps(make_data()))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Ultima Weapon", r.stdout)

    def test_non_utf8_locale_and_lone_surrogate(self):
        payload = json.dumps(make_data())[:-1] + ', "session_name": "abc\\ud83d"}'
        r = self.run_script(stdin=payload, LC_ALL="en_US.ISO8859-1", LANG="en_US.ISO8859-1",
                            PYTHONIOENCODING="")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Ultima Weapon", r.stdout)

    def test_preview(self):
        r = self.run_script(["--preview", "--width", "100"])
        self.assertEqual(r.returncode, 0, r.stderr)
        out = strip(r.stdout)
        for header in ("classic", "minimal", "full_rpg", "party panel"):
            self.assertIn(f"═══ {header}", out)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "cli_state.json")))


if __name__ == "__main__":
    unittest.main()
