from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import subprocess
import tempfile
import tomllib
import unittest
import zlib
from pathlib import Path

import codex_home  # noqa: F401  (isolates the Codex user config)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTEXTKIT = REPO_ROOT / "bin" / "contextkit"


def png_bytes(red: int = 0x20, width: int = 64, height: int | None = None) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    height = width if height is None else height
    raw = b"".join(b"\x00" + bytes((red, 0x40, 0x80)) * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def stored_name(body: bytes) -> str:
    return f"icon-{hashlib.sha256(body).hexdigest()[:12]}.png"


class IdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "my-agent"
        self.project.mkdir()
        initialized = self.run_cli("init", "--with-layers", "--json")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)

    def run_cli(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(CONTEXTKIT), *args],
            cwd=str(cwd or self.project),
            env=dict(os.environ),
            text=True,
            capture_output=True,
            check=False,
        )

    def identity(self, *args: str, cwd: Path | None = None) -> dict:
        result = self.run_cli("identity", *args, "--json", cwd=cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def config(self) -> dict:
        return tomllib.loads((self.project / ".contextkit" / "config.toml").read_text())

    def display_identity(self) -> dict:
        """The identity table without the project id `init` assigns."""
        return {key: value for key, value in self.config().get("identity", {}).items() if key != "id"}

    def icon_file(self, name: str = "cropped.png", body: bytes | None = None) -> Path:
        path = self.root / name
        path.write_bytes(body if body is not None else png_bytes())
        return path

    def test_show_resolves_the_folder_name_until_a_name_is_configured(self) -> None:
        report = self.identity("show")
        self.assertEqual(report["name"], "my-agent")
        self.assertEqual(report["name_source"], "folder")
        self.assertIsNone(report["description"])
        self.assertIsNone(report["icon"])
        self.assertEqual(report["problems"], [])
        self.assertEqual(report["project"], str(self.project))
        self.assertEqual(report["config"], str(self.project / ".contextkit" / "config.toml"))
        self.assertEqual(self.display_identity(), {})

    def test_show_outside_a_contextkit_project_reports_no_config(self) -> None:
        loose = self.root / "loose-agent"
        loose.mkdir()
        report = self.identity("show", cwd=loose)
        self.assertEqual(report["name"], "loose-agent")
        self.assertEqual(report["name_source"], "folder")
        self.assertIsNone(report["config"])

    def test_set_and_clear_name_and_description(self) -> None:
        written = self.identity("set", "--name", "Agent One", "--description", "One line about this agent.")
        self.assertEqual(written["changed"], ["name", "description"])
        self.assertEqual(written["unchanged"], [])
        self.assertEqual(written["name"], "Agent One")
        self.assertEqual(written["name_source"], "config")
        self.assertEqual(written["description"], "One line about this agent.")
        self.assertEqual(self.config()["identity"]["name"], "Agent One")

        again = self.identity("set", "--name", "Agent One")
        self.assertEqual(again["changed"], [])
        self.assertEqual(again["unchanged"], ["name"])

        cleared = self.identity("clear", "--name")
        self.assertEqual(cleared["changed"], ["name"])
        self.assertEqual(cleared["name"], "my-agent")
        self.assertEqual(cleared["name_source"], "folder")
        self.assertEqual(cleared["description"], "One line about this agent.")
        self.assertNotIn("name", self.config()["identity"])

        cleared_again = self.identity("clear", "--name", "--description")
        self.assertEqual(cleared_again["changed"], ["description"])
        self.assertEqual(cleared_again["unchanged"], ["name"])
        self.assertIsNone(cleared_again["description"])

    def test_set_icon_copies_the_image_into_the_binding_folder(self) -> None:
        source = self.icon_file()
        written = self.identity("set", "--icon", str(source))
        stored = self.project / ".contextkit" / stored_name(png_bytes())
        self.assertEqual(written["changed"], ["icon"])
        self.assertEqual(written["icon"], str(stored))
        self.assertEqual(stored.read_bytes(), source.read_bytes())
        self.assertEqual(self.config()["identity"]["icon"], stored.name)

        source.unlink()
        kept = self.identity("show")
        self.assertEqual(kept["icon"], str(stored))

        again = self.identity("set", "--icon", str(self.icon_file()))
        self.assertEqual(again["changed"], [])
        self.assertEqual(again["unchanged"], ["icon"])
        self.assertEqual(again["removed"], [])

    def test_a_new_icon_gets_a_new_path_and_the_old_file_goes(self) -> None:
        first = self.identity("set", "--icon", str(self.icon_file()))["icon"]
        replacement = png_bytes(red=0x90, width=512)
        written = self.identity("set", "--icon", str(self.icon_file("next.png", replacement)))
        binding = self.project / ".contextkit"
        self.assertEqual(written["changed"], ["icon"])
        self.assertEqual(written["icon"], str(binding / stored_name(replacement)))
        self.assertNotEqual(written["icon"], first)
        self.assertEqual(written["removed"], [f".contextkit/{Path(first).name}"])
        self.assertFalse(Path(first).exists())
        self.assertEqual(sorted(path.name for path in binding.glob("icon-*.png")), [stored_name(replacement)])

    def test_a_failed_config_write_keeps_the_previous_icon(self) -> None:
        previous = self.identity("set", "--icon", str(self.icon_file()))["icon"]
        config = self.project / ".contextkit" / "config.toml"
        original = config.read_text().split("\n[identity]\n")[0] + "\n"
        # An inline `identity` table cannot be rewritten line by line, so the write fails.
        config.write_text(f'identity = {{ icon = "{Path(previous).name}" }}\n' + original)
        failed = self.run_cli("identity", "set", "--icon", str(self.icon_file("next.png", png_bytes(red=0x90))))
        self.assertEqual(failed.returncode, 6, failed.stdout)
        self.assertIn("could not write identity.icon", failed.stderr)
        binding = self.project / ".contextkit"
        self.assertEqual([path.name for path in binding.glob("icon-*.png")], [Path(previous).name])
        self.assertEqual(self.identity("show")["icon"], previous)

    def test_clear_icon_removes_the_reference_and_the_file_contextkit_owns(self) -> None:
        self.identity("set", "--icon", str(self.icon_file()))
        stored = self.project / ".contextkit" / stored_name(png_bytes())
        cleared = self.identity("clear", "--icon")
        self.assertEqual(cleared["changed"], ["icon"])
        self.assertEqual(cleared["removed"], [f".contextkit/{stored.name}"])
        self.assertIsNone(cleared["icon"])
        self.assertFalse(stored.exists())
        self.assertNotIn("icon", self.config()["identity"])

        again = self.identity("clear", "--icon")
        self.assertEqual(again["changed"], [])
        self.assertEqual(again["removed"], [])

    def test_clear_icon_keeps_an_image_contextkit_does_not_own(self) -> None:
        brand = self.project / ".contextkit" / "brand" / "logo.png"
        brand.parent.mkdir(parents=True)
        brand.write_bytes(png_bytes())
        config = self.project / ".contextkit" / "config.toml"
        config.write_text(config.read_text() + 'icon = "brand/logo.png"\n')
        self.assertEqual(self.identity("show")["icon"], str(brand))

        cleared = self.identity("clear", "--icon")
        self.assertEqual(cleared["changed"], ["icon"])
        self.assertEqual(cleared["removed"], [])
        self.assertIsNone(cleared["icon"])
        self.assertTrue(brand.is_file())

    def test_set_rejects_input_that_is_not_a_supported_image(self) -> None:
        text = self.root / "note.png"
        text.write_text("not an image\n")
        rejected = self.run_cli("identity", "set", "--icon", str(text))
        self.assertEqual(rejected.returncode, 2, rejected.stdout)
        self.assertIn("unsupported icon format", rejected.stderr)

        gif = self.icon_file("cropped.gif", b"GIF89a" + bytes(20))
        rejected_gif = self.run_cli("identity", "set", "--icon", str(gif))
        self.assertEqual(rejected_gif.returncode, 2, rejected_gif.stdout)
        self.assertIn("The icon is a PNG image.", rejected_gif.stderr)

        for body in (png_bytes(width=128, height=64), png_bytes(width=32), png_bytes(width=2048)):
            sized = self.run_cli("identity", "set", "--icon", str(self.icon_file("sized.png", body)))
            self.assertEqual(sized.returncode, 2, sized.stdout)
            self.assertIn("unsupported icon size", sized.stderr)

        heavy = self.icon_file("heavy.png", png_bytes() + bytes(1024 * 1024))
        rejected_heavy = self.run_cli("identity", "set", "--icon", str(heavy))
        self.assertEqual(rejected_heavy.returncode, 2, rejected_heavy.stdout)
        self.assertIn("larger than 1024 KiB", rejected_heavy.stderr)
        self.assertEqual(list((self.project / ".contextkit").glob("icon-*.png")), [])

        missing = self.run_cli("identity", "set", "--icon", str(self.root / "absent.png"))
        self.assertEqual(missing.returncode, 2, missing.stdout)
        self.assertIn("icon file not found", missing.stderr)

        empty = self.root / "empty.png"
        empty.write_bytes(b"")
        rejected_empty = self.run_cli("identity", "set", "--icon", str(empty))
        self.assertEqual(rejected_empty.returncode, 2, rejected_empty.stdout)
        self.assertIn("icon file is empty", rejected_empty.stderr)
        self.assertEqual(self.display_identity(), {})

    def test_set_rejects_empty_and_multi_line_values(self) -> None:
        for args, reason in (
            (("--name", "two\nlines"), "expected one line"),
            (("--description", "two\nlines"), "expected one line"),
            (("--name", "   "), "expected a non-empty string"),
            (("--name", "x" * 121), "within 120 characters"),
            (("--description", "x" * 501), "within 500 characters"),
        ):
            rejected = self.run_cli("identity", "set", *args)
            self.assertEqual(rejected.returncode, 2, rejected.stdout)
            self.assertIn(reason, rejected.stderr)
        self.assertEqual(self.display_identity(), {})

    def test_set_rejects_control_and_separator_characters(self) -> None:
        for value, code in (("sep\u2028x", "U+2028"), ("sep\u2029x", "U+2029"), ("a\x01b", "U+0001"), ("a\tb", "U+0009")):
            for flag in ("--name", "--description"):
                rejected = self.run_cli("identity", "set", flag, value)
                self.assertEqual(rejected.returncode, 2, rejected.stdout)
                self.assertIn(f"contains control or line-separator character {code}", rejected.stderr)
        self.assertEqual(self.display_identity(), {})

    def test_a_config_holding_a_line_separator_stays_writable(self) -> None:
        config = self.project / ".contextkit" / "config.toml"
        config.write_text(config.read_text() + 'name = "sep\\u2028x"\ndescription = "kept"\n')
        self.assertEqual(self.identity("show")["name"], "sep\u2028x")

        renamed = self.identity("set", "--name", "Fixed")
        self.assertEqual(renamed["name"], "Fixed")
        config.write_text(config.read_text().replace('name = "Fixed"', 'name = "sep\u2028x"'))
        cleared = self.identity("clear", "--name")
        self.assertEqual(cleared["changed"], ["name"])
        self.assertEqual(cleared["name_source"], "folder")
        self.assertEqual(self.display_identity(), {"description": "kept"})

    def test_a_field_is_required(self) -> None:
        for command in ("set", "clear"):
            empty = self.run_cli("identity", command)
            self.assertEqual(empty.returncode, 2, empty.stdout)
            self.assertIn("pass --name, --description, or --icon", empty.stderr)

    def test_writes_require_a_contextkit_project(self) -> None:
        loose = self.root / "loose-agent"
        loose.mkdir()
        refused = self.run_cli("identity", "set", "--name", "Loose", cwd=loose)
        self.assertEqual(refused.returncode, 3, refused.stdout)
        self.assertIn("not a ContextKit project", refused.stderr)
        self.assertIn("contextkit init", refused.stderr)

    def test_writes_preserve_the_rest_of_the_config(self) -> None:
        rooted = self.root / "rooted-agent"
        rooted.mkdir()
        initialized = self.run_cli("init", "--with-layers", "--body-root", "agent", "--json", cwd=rooted)
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        config = rooted / ".contextkit" / "config.toml"
        before = config.read_text()

        for args in (("--name", "Rooted"), ("--description", "One line."), ("--icon", str(self.icon_file()))):
            written = self.run_cli("identity", "set", *args, "--json", cwd=rooted)
            self.assertEqual(written.returncode, 0, written.stderr)

        parsed = tomllib.loads(config.read_text())
        project_id = parsed["identity"].pop("id")
        self.assertRegex(project_id, r"^prj_[0-9a-f]{12}$")
        self.assertEqual(parsed["body"]["root"], "agent")
        self.assertEqual(parsed["output"]["context"], ".contextkit/generated/context.md")
        self.assertEqual(parsed["version"], 1)
        self.assertEqual(
            parsed["identity"],
            {"name": "Rooted", "description": "One line.", "icon": stored_name(png_bytes())},
        )
        self.assertIn("# Optional shared doctrine outside this project:", config.read_text())

        cleared = self.run_cli("identity", "clear", "--name", "--description", "--icon", "--json", cwd=rooted)
        self.assertEqual(cleared.returncode, 0, cleared.stderr)
        after = tomllib.loads(config.read_text())
        self.assertEqual(after["body"]["root"], "agent")
        self.assertEqual(after["identity"], {"id": project_id})
        self.assertIn("# Optional shared doctrine outside this project:", config.read_text())
        self.assertTrue(before.startswith("version = 1"))

    def test_invalid_identity_config_is_reported_by_every_command(self) -> None:
        config = self.project / ".contextkit" / "config.toml"
        original = config.read_text()
        # A bare `identity` key is a top-level value, so it precedes every table.
        for body, reason in (
            (original + 'name = 5\n', "invalid identity.name"),
            (original + 'description = """two\nlines"""\n', "invalid identity.description"),
            (original + 'icon = "../outside.png"\n', "invalid identity.icon"),
            (original + 'icon = "logo.txt"\n', "The icon is a PNG image."),
            ('identity = "AgentKit"\n' + original.split("\n[identity]\n")[0] + "\n", "invalid [identity]"),
            (re.sub(r'(?m)^id = ".*"$', 'id = "project-7"', original), "invalid identity.id"),
        ):
            config.write_text(body)
            for command in (("identity", "show"), ("build",), ("doctor",)):
                refused = self.run_cli(*command)
                self.assertEqual(refused.returncode, 6, f"{body} {command} {refused.stdout}")
                self.assertIn(reason, refused.stderr)
        config.write_text(original)

    def test_doctor_reports_the_resolved_identity_and_a_missing_icon_file(self) -> None:
        self.identity("set", "--name", "Agent One", "--icon", str(self.icon_file()))
        healthy = self.run_cli("doctor", "--json")
        self.assertEqual(healthy.returncode, 0, healthy.stderr)
        report = json.loads(healthy.stdout)
        self.assertEqual(
            report["identity"],
            {
                "id": self.config()["identity"]["id"],
                "name": "Agent One",
                "name_source": "config",
                "description": None,
                "icon": str(self.project / ".contextkit" / stored_name(png_bytes())),
            },
        )
        self.assertEqual([problem for problem in report["problems"] if "identity" in problem], [])

        (self.project / ".contextkit" / stored_name(png_bytes())).unlink()
        broken = json.loads(self.run_cli("doctor", "--json").stdout)
        self.assertFalse(broken["ok"])
        self.assertIn(
            f"configured identity icon is missing: .contextkit/{stored_name(png_bytes())}; "
            "run `contextkit identity set --icon <file>` or `contextkit identity clear --icon`",
            broken["problems"],
        )
        self.assertIsNone(broken["identity"]["icon"])
        self.assertEqual(self.identity("show")["problems"], broken["problems"][-1:])

        text = self.run_cli("doctor")
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertIn("- Name: `Agent One` (configured)", text.stdout)
        self.assertIn("- Description: not set", text.stdout)
        self.assertIn("- Icon: not set", text.stdout)

    def test_identity_stays_out_of_generated_context(self) -> None:
        self.identity("set", "--name", "Agent One", "--description", "One line about this agent.")
        built = self.run_cli("build", "--json")
        self.assertEqual(built.returncode, 0, built.stderr)
        generated = (self.project / ".contextkit" / "generated" / "context.md").read_text()
        self.assertNotIn("Agent One", generated)
        self.assertNotIn("One line about this agent.", generated)

    def test_help_lists_the_identity_commands(self) -> None:
        help_result = self.run_cli("help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("contextkit identity show [--project DIR] [--json]", help_result.stdout)
        self.assertIn("contextkit routines [--project DIR] [--json]", help_result.stdout)
        self.assertIn("contextkit identity set [--name <text>]", help_result.stdout)
        self.assertIn("contextkit identity clear [--name]", help_result.stdout)

    def test_project_flag_names_the_project_explicitly(self) -> None:
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        written = self.identity("set", "--name", "Remote", "--project", str(self.project), cwd=elsewhere)
        self.assertEqual(written["project"], str(self.project))
        self.assertEqual(self.config()["identity"]["name"], "Remote")
        shown = self.identity("show", "--project", str(self.project), cwd=elsewhere)
        self.assertEqual(shown["name"], "Remote")

        missing = self.run_cli("identity", "show", "--project", str(self.root / "absent"))
        self.assertEqual(missing.returncode, 2, missing.stdout)
        self.assertIn("project directory not found", missing.stderr)


class ProjectIdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name).resolve() / "my-agent"
        self.project.mkdir()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(CONTEXTKIT), *args],
            cwd=str(self.project),
            env=dict(os.environ),
            text=True,
            capture_output=True,
            check=False,
        )

    def json_cli(self, *args: str) -> dict:
        result = self.run_cli(*args, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def config_text(self) -> str:
        return (self.project / ".contextkit" / "config.toml").read_text()

    def envelope(self, project_id: str, layer: str = "capabilities") -> Path:
        path = self.project / layer / "project.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"id": project_id, "schema": "capabilities.project.v1", "slug": "my-agent"}) + "\n")
        return path

    def test_init_assigns_a_stable_id(self) -> None:
        self.json_cli("init")
        shown = self.json_cli("identity", "show")
        self.assertRegex(shown["id"], r"^prj_[0-9a-f]{12}$")
        self.assertEqual(shown["problems"], [])
        self.assertEqual(self.json_cli("doctor")["identity"]["id"], shown["id"])

        self.json_cli("init")
        self.assertEqual(self.json_cli("identity", "show")["id"], shown["id"])
        adopted = self.json_cli("identity", "adopt")
        self.assertEqual(adopted["changed"], [])
        self.assertEqual(adopted["unchanged"], ["id"])
        self.assertEqual(adopted["id"], shown["id"])

        self.json_cli("identity", "set", "--name", "Agent One")
        self.json_cli("identity", "clear", "--name", "--description", "--icon")
        self.assertEqual(self.json_cli("identity", "show")["id"], shown["id"])
        refused = self.run_cli("identity", "set", "--id", "prj_000000000000")
        self.assertEqual(refused.returncode, 2, refused.stdout)

    def test_init_adopts_the_envelope_id_through_the_body_root(self) -> None:
        envelope = self.envelope("prj_031f2dfab24e", layer="agent/capabilities")
        before = envelope.read_bytes()
        self.json_cli("init", "--body-root", "agent")
        self.assertEqual(self.json_cli("identity", "show")["id"], "prj_031f2dfab24e")
        self.assertEqual(envelope.read_bytes(), before)

    def test_adopt_takes_an_existing_envelope_id_including_a_uuid(self) -> None:
        self.json_cli("init")
        config = self.project / ".contextkit" / "config.toml"
        config.write_text(re.sub(r'(?m)^id = ".*"\n', "", self.config_text()))
        missing = self.json_cli("identity", "show")
        self.assertIsNone(missing["id"])
        self.assertEqual(missing["problems"], ["project id is not assigned; run `contextkit identity adopt`"])
        self.assertFalse(self.json_cli("doctor")["ok"])

        uuid = "351bae2a-e256-4181-a9f7-2b292d198066"
        self.envelope(uuid)
        adopted = self.json_cli("identity", "adopt")
        self.assertEqual(adopted["changed"], ["id"])
        self.assertEqual(adopted["id_source"], "capabilities")
        self.assertEqual(adopted["id"], uuid)
        self.assertEqual(adopted["problems"], [])

    def test_adopt_refuses_an_unreadable_envelope_id(self) -> None:
        self.json_cli("init")
        config = self.project / ".contextkit" / "config.toml"
        config.write_text(re.sub(r'(?m)^id = ".*"\n', "", self.config_text()))
        before = self.config_text()
        self.envelope("not-an-id")
        refused = self.run_cli("identity", "adopt")
        self.assertEqual(refused.returncode, 6, refused.stdout)
        self.assertIn("cannot adopt the project id from capabilities/project.json", refused.stderr)
        self.assertEqual(self.config_text(), before)

    def test_a_folder_without_contextkit_has_no_id(self) -> None:
        shown = self.json_cli("identity", "show")
        self.assertIsNone(shown["id"])
        self.assertIsNone(shown["config"])
        self.assertEqual(shown["problems"], [])
        refused = self.run_cli("identity", "adopt")
        self.assertEqual(refused.returncode, 3, refused.stdout)


class RoutinesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / "my-agent"
        self.project.mkdir()
        initialized = self.run_cli("init", "--with-layers", "--json")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)

    def run_cli(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(CONTEXTKIT), *args],
            cwd=str(cwd or self.project),
            env=dict(os.environ),
            text=True,
            capture_output=True,
            check=False,
        )

    def snapshot(self) -> dict[str, bytes]:
        return {str(path): path.read_bytes() for path in self.project.rglob("*") if path.is_file()}

    def test_routines_lists_declared_routines_without_side_effects(self) -> None:
        routines = self.project / "routines"
        (routines / "weekly-review.md").write_text(
            "---\nname: weekly-review\ndescription: Review the week.\n---\n\n# Weekly Review\n"
        )
        (routines / "broken.md").write_text("# No front matter\n")
        before = self.snapshot()

        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        result = self.run_cli("routines", "--project", str(self.project), "--json", cwd=elsewhere)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["project"], str(self.project))
        self.assertEqual(report["count"], 1)
        self.assertEqual(
            report["routines"],
            [{
                "name": "weekly-review",
                "title": "weekly-review",
                "title_source": "name",
                "description": "Review the week.",
                "path": str(routines / "weekly-review.md"),
            }],
        )
        self.assertEqual(report["warnings"], ["routine missing frontmatter name: routines/broken.md"])
        self.assertEqual(self.snapshot(), before)

    def test_set_and_clear_a_routine_title(self) -> None:
        path = self.project / "routines" / "weekly-review.md"
        body = "\n# Weekly Review\n\nSteps stay exactly as written.\n"
        path.write_text("---\nname: weekly-review\ndescription: Review the week.\n---\n" + body)

        result = self.run_cli("routines", "set", "weekly-review", "--title", 'Weekly "review": Fridays', "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        written = json.loads(result.stdout)
        self.assertEqual(written["changed"], ["title"])
        self.assertEqual(written["routine"]["title"], 'Weekly "review": Fridays')
        self.assertEqual(written["routine"]["title_source"], "front_matter")
        self.assertEqual(written["routine"]["description"], "Review the week.")
        text = path.read_text()
        self.assertTrue(text.startswith('---\nname: weekly-review\ntitle: "Weekly \\"review\\": Fridays"\n'))
        self.assertTrue(text.endswith("---\n" + body))

        listed = json.loads(self.run_cli("routines", "--json").stdout)["routines"][0]
        self.assertEqual(listed["title"], 'Weekly "review": Fridays')

        again = json.loads(self.run_cli("routines", "set", "weekly-review", "--title", 'Weekly "review": Fridays', "--json").stdout)
        self.assertEqual(again["changed"], [])

        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        cleared = self.run_cli("routines", "--project", str(self.project), "clear", "weekly-review", "--title", "--json", cwd=elsewhere)
        self.assertEqual(cleared.returncode, 0, cleared.stderr)
        self.assertEqual(json.loads(cleared.stdout)["routine"]["title_source"], "name")
        self.assertEqual(path.read_text(), "---\nname: weekly-review\ndescription: Review the week.\n---\n" + body)

        built = self.run_cli("build")
        self.assertEqual(built.returncode, 0, built.stderr)

    def test_routine_title_writes_are_validated(self) -> None:
        (self.project / "routines" / "weekly-review.md").write_text(
            "---\nname: weekly-review\ndescription: Review the week.\n---\n"
        )
        for args, code, reason in (
            (("set", "absent", "--title", "X"), 3, "routine not found: absent"),
            (("set", "weekly-review", "--title", "two\nlines"), 2, "expected one line"),
            (("set", "weekly-review", "--title", "a\u2028b"), 2, "U+2028"),
            (("set", "weekly-review", "--title", "x" * 121), 2, "within 120 characters"),
            (("set", "weekly-review"), 2, "nothing to set: pass --title"),
            (("clear", "weekly-review"), 2, "nothing to clear: pass --title"),
        ):
            rejected = self.run_cli("routines", *args)
            self.assertEqual(rejected.returncode, code, f"{args} {rejected.stdout}")
            self.assertIn(reason, rejected.stderr)
        help_result = self.run_cli("help")
        self.assertIn("contextkit routines set <name> --title <text>", help_result.stdout)

    def test_routines_without_a_layer_counts_zero(self) -> None:
        (self.project / "routines").rmdir()
        report = json.loads(self.run_cli("routines", "--json").stdout)
        self.assertEqual(report["count"], 0)
        self.assertEqual(report["routines"], [])
        self.assertEqual(len(report["warnings"]), 1)


if __name__ == "__main__":
    unittest.main()
