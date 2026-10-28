"""Observable scope-checker behavior using isolated Git repositories."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_scope.py"
SPEC = importlib.util.spec_from_file_location("check_scope", SCRIPT)
assert SPEC and SPEC.loader
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


@unittest.skipUnless(shutil.which("git"), "Git is required for inventory tests")
class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="orb scope ")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.git("init", "-q", "-b", "main")
        self.write(".gitignore", "ignored/\n")
        self.write("README.md", "baseline\n")
        self.write("src/orb/providers/oci/base.py", "baseline\n" * 20)
        self.write("src/orb/application/shared.py", "shared\n" * 20)
        self.git("add", ".")
        self.commit("baseline")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args, check=True):
        result = subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "-c",
                "user.name=Scope Test",
                "-c",
                "user.email=scope@example.invalid",
                *args,
            ],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        if check and result.returncode:
            self.fail(f"Test Git setup failed: {args!r}: {result.stderr}")
        return result.stdout

    def write(self, path, content=None):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            content if content is not None else f"new content for {path}\n", encoding="utf-8"
        )

    def commit(self, message):
        self.git("commit", "-qm", message)

    def check_scope(self, *extra, profile="oci-234", base=None, expected=0):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(self.repo),
                "--base-ref",
                base or self.base,
                "--profile",
                profile,
                *extra,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_clean_repository_and_deterministic_evidence(self):
        first = self.check_scope()
        self.assertEqual(first, self.check_scope())
        self.assertEqual(first["head_commit"], self.base)
        self.assertEqual(first["base_commit"], self.base)
        self.assertEqual(first["merge_base"], self.base)
        self.assertFalse(first["dirty"])
        self.assertEqual(first["paths"], [])

    def test_union_keeps_all_four_change_origins(self):
        self.write("src/orb/providers/oci/committed.py")
        self.git("add", ".")
        self.commit("OCI committed work")
        self.write("src/orb/providers/oci/staged.py")
        self.git("add", ".")
        self.write("src/orb/providers/oci/base.py", "unstaged edit\n")
        self.write("src/orb/providers/oci/untracked.py")
        report = self.check_scope()
        origins = {p["path"]: p["origins"] for p in report["paths"]}
        self.assertEqual(origins["src/orb/providers/oci/committed.py"], ["committed"])
        self.assertEqual(origins["src/orb/providers/oci/staged.py"], ["staged"])
        self.assertEqual(origins["src/orb/providers/oci/base.py"], ["unstaged"])
        self.assertEqual(origins["src/orb/providers/oci/untracked.py"], ["untracked"])
        self.assertTrue(report["dirty"])

    def test_each_origin_catches_shared_code(self):
        self.write("src/orb/application/shared.py", "staged\n")
        self.git("add", ".")
        self.assertIn("src/orb/application/shared.py", self.check_scope(expected=1)["violations"])
        self.commit("shared edit")
        report = self.check_scope(expected=1)
        self.assertEqual(report["paths"][0]["origins"], ["committed"])
        self.write("src/orb/application/shared.py", "unstaged\n")
        self.write("src/orb/application/new.py")
        report = self.check_scope(expected=1)
        origins = {p["path"]: p["origins"] for p in report["paths"]}
        self.assertEqual(origins["src/orb/application/shared.py"], ["committed", "unstaged"])
        self.assertEqual(origins["src/orb/application/new.py"], ["untracked"])

    def test_rename_out_of_provider_rejects_new_path(self):
        self.git("mv", "src/orb/providers/oci/base.py", "src/orb/application/moved.py")
        report = self.check_scope(expected=1)
        self.assertEqual(report["violations"], ["src/orb/application/moved.py"])
        self.assertEqual(report["inventory"]["staged"][0]["status"], "R100")
        self.assertEqual(len(report["inventory"]["staged"][0]["paths"]), 2)

    def test_rename_into_provider_still_rejects_old_path(self):
        self.git("mv", "src/orb/application/shared.py", "src/orb/providers/oci/moved.py")
        self.commit("rename into OCI")
        report = self.check_scope(expected=1)
        self.assertEqual(report["violations"], ["src/orb/application/shared.py"])

    def test_staged_rename_then_unstaged_edit_keeps_both_records(self):
        self.git("mv", "src/orb/providers/oci/base.py", "src/orb/providers/oci/renamed.py")
        self.write("src/orb/providers/oci/renamed.py", "later edit\n")
        report = self.check_scope()
        origins = {p["path"]: p["origins"] for p in report["paths"]}
        self.assertEqual(origins["src/orb/providers/oci/renamed.py"], ["staged", "unstaged"])
        self.assertIn("src/orb/providers/oci/base.py", origins)

    def test_staged_copy_of_unchanged_shared_source_checks_both_paths(self):
        source = "src/orb/application/shared.py"
        destination = "src/orb/providers/oci/copied.py"
        shutil.copyfile(self.repo / source, self.repo / destination)
        self.git("add", destination)
        report = self.check_scope(expected=1)
        self.assertEqual(report["violations"], [source])
        self.assertEqual(
            report["inventory"]["staged"], [{"status": "C100", "paths": [source, destination]}]
        )
        self.assertEqual((self.repo / source).read_text(), "shared\n" * 20)

    def test_committed_copy_of_unchanged_shared_source_checks_both_paths(self):
        source = "src/orb/application/shared.py"
        destination = "src/orb/providers/oci/copied.py"
        shutil.copyfile(self.repo / source, self.repo / destination)
        self.git("add", destination)
        self.commit("copy shared code into OCI")
        report = self.check_scope(expected=1)
        self.assertEqual(report["violations"], [source])
        self.assertEqual(
            report["inventory"]["committed"], [{"status": "C100", "paths": [source, destination]}]
        )

    def assert_hidden_edit_fails(self, set_flag, clear_flag, detail_key):
        path = "src/orb/providers/oci/base.py"
        original = (self.repo / path).read_text()
        self.git("update-index", set_flag, path)
        self.write(path, "hidden working-tree edit\n")
        # Establish that ordinary diff really hides this edit in this Git fixture.
        self.assertEqual(self.git("diff", "--name-only", "--", path).strip(), "")
        before = self.git("ls-files", "-v", "--", path)
        report = self.check_scope(expected=1)
        self.assertFalse(report["inventory_complete"])
        self.assertIsNone(report["dirty"])
        self.assertEqual(report["index_flags"][0]["path"], path)
        self.assertTrue(report["index_flags"][0][detail_key])
        self.assertEqual(report["violations"], [])
        self.assertEqual(self.git("ls-files", "-v", "--", path), before)
        # The fixture, not the read-only audit, restores normal tracking.
        self.git("update-index", clear_flag, path)
        visible = self.check_scope()
        self.assertTrue(visible["inventory_complete"])
        self.assertTrue(visible["dirty"])
        self.assertEqual(visible["index_flags"], [])
        self.write(path, original)
        self.assertFalse(self.check_scope()["dirty"])

    def test_assume_unchanged_hidden_edit_fails_without_changing_index_flags(self):
        self.assert_hidden_edit_fails(
            "--assume-unchanged", "--no-assume-unchanged", "assume_unchanged"
        )

    def test_skip_worktree_hidden_edit_fails_without_changing_index_flags(self):
        self.assert_hidden_edit_fails("--skip-worktree", "--no-skip-worktree", "skip_worktree")

    def test_deletion_does_not_hide_outside_path(self):
        (self.repo / "src/orb/application/shared.py").unlink()
        report = self.check_scope(expected=1)
        self.assertEqual(report["inventory"]["unstaged"][0]["status"], "D")
        self.assertEqual(report["violations"], ["src/orb/application/shared.py"])

    def test_spaces_and_unicode_survive_inventory(self):
        path = "src/orb/providers/oci/space café.py"
        self.write(path)
        self.assertEqual(self.check_scope()["paths"][0]["path"], path)

    @unittest.skipIf(os.name == "nt", "Windows does not allow newlines in filenames")
    def test_newline_filename_is_not_split(self):
        path = "src/orb/providers/oci/line\nbreak.py"
        self.write(path)
        self.assertEqual(self.check_scope()["paths"][0]["path"], path)

    def test_prefix_boundaries_and_case_are_exact(self):
        self.write("src/orb/providers/oci_other/not_oci.py")
        # A case-insensitive filesystem cannot create a second OCI directory;
        # check the exact prospective path before any filesystem normalization.
        report = self.check_scope(
            "--planned-path", "src/orb/providers/OCI/not_exact.py", expected=1
        )
        self.assertEqual(len(report["violations"]), 2)

    def test_ignored_private_evidence_is_not_a_pr_input(self):
        self.write("ignored/config.json", "private local evidence\n")
        self.assertEqual(self.check_scope()["paths"], [])

    def test_missing_reference_and_unknown_profile_fail_closed(self):
        self.assertEqual(self.check_scope(base="missing-ref", expected=2)["result"], "error")
        self.assertEqual(self.check_scope(profile="missing-profile", expected=2)["result"], "error")

    def test_required_arguments_are_not_inferred(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.repo)], capture_output=True
        )
        self.assertEqual(result.returncode, 2)

    def test_upstream_changes_are_excluded_using_merge_base(self):
        self.git("checkout", "-qb", "feature")
        self.write("src/orb/providers/oci/feature.py")
        self.git("add", ".")
        self.commit("OCI feature")
        self.git("checkout", "-q", "main")
        self.write("src/orb/application/upstream.py")
        self.git("add", ".")
        self.commit("unrelated upstream work")
        self.git("checkout", "-q", "feature")
        report = self.check_scope(base="main")
        self.assertEqual(report["merge_base"], self.base)
        self.assertNotEqual(report["base_commit"], self.base)
        self.assertEqual(report["paths"][0]["path"], "src/orb/providers/oci/feature.py")

    def test_inherited_git_overrides_cannot_hide_target_changes(self):
        self.write("src/orb/application/outside.py")
        with patch.dict(
            os.environ,
            {
                "GIT_DIR": str(self.repo / "missing-git"),
                "GIT_WORK_TREE": str(self.repo / "missing-tree"),
                "GIT_INDEX_FILE": str(self.repo / "missing-index"),
            },
        ):
            report = self.check_scope(expected=1)
        self.assertEqual(report["violations"], ["src/orb/application/outside.py"])

    def test_planned_path_checked_without_editing_target(self):
        report = self.check_scope("--planned-path", "src/orb/application/planned.py", expected=1)
        self.assertEqual(report["paths"][0]["origins"], ["planned"])
        self.assertFalse((self.repo / "src/orb/application/planned.py").exists())

    def test_exception_is_exact_and_recorded_with_reason(self):
        self.write("src/orb/application/one.py")
        report = self.check_scope(
            "--allow-path",
            "src/orb/application/one.py",
            "--reason",
            "User selected one compatibility fix",
        )
        self.assertEqual(report["paths"][0]["scope"], "exception")
        self.assertEqual(report["declared_exceptions"]["paths"], ["src/orb/application/one.py"])
        self.write("src/orb/application/two.py")
        report = self.check_scope(
            "--allow-path",
            "src/orb/application/one.py",
            "--reason",
            "User selected one compatibility fix",
            expected=1,
        )
        self.assertEqual(report["violations"], ["src/orb/application/two.py"])

    def test_exception_requires_reason_and_cannot_be_directory(self):
        self.check_scope("--allow-path", "README.md", expected=2)
        self.check_scope("--reason", "No exception path", expected=2)
        self.check_scope(
            "--allow-path", "src/orb/application/", "--reason", "Too broad", expected=2
        )

    def test_traversal_absolute_and_option_refs_are_rejected(self):
        for path in ("../outside.py", "/outside.py", "C:/outside.py", "src/../outside.py"):
            with self.subTest(path=path):
                self.check_scope("--planned-path", path, expected=2)
        self.check_scope("--base-ref=-bad-ref", expected=2)

    def test_profiles_are_separate(self):
        self.write("AGENTS.md")
        self.check_scope(profile="fork-tooling")
        self.check_scope(profile="oci-234", expected=1)
        (self.repo / "AGENTS.md").unlink()
        self.write("Dockerfile")
        self.check_scope(profile="packaging-589")
        self.check_scope(profile="oci-234", expected=1)
        (self.repo / "Dockerfile").unlink()
        self.write(
            "src/orb/providers/azure/infrastructure/services/spot_placement_score_adapter.py"
        )
        self.check_scope(profile="azure-588")
        self.check_scope(profile="oci-234", expected=1)

    def test_capacity_profile_does_not_admit_shared_metadata(self):
        self.write("README.md", "changed shared doc\n")
        self.check_scope(profile="oci-234")
        self.check_scope(profile="oci-capacity", expected=1)

    def test_conflicts_fail_even_when_path_is_allowed(self):
        self.git("checkout", "-qb", "other")
        self.write("src/orb/providers/oci/base.py", "other branch\n")
        self.git("add", ".")
        self.commit("other branch")
        self.git("checkout", "-q", "main")
        self.write("src/orb/providers/oci/base.py", "main branch\n")
        self.git("add", ".")
        self.commit("main branch")
        self.git("merge", "other", check=False)
        report = self.check_scope(expected=1)
        self.assertEqual(report["conflicts"], ["src/orb/providers/oci/base.py"])
        self.assertEqual(report["violations"], [])


class NulParserTests(unittest.TestCase):
    def test_copy_keeps_both_endpoints_and_unusual_names(self):
        changes = CHECKER.parse_changes(b"C100\0outside\nname.py\0src/orb/providers/oci/copy.py\0")
        self.assertEqual(changes[0]["paths"], ["outside\nname.py", "src/orb/providers/oci/copy.py"])

    def test_malformed_or_unsupported_records_fail_closed(self):
        for value in (
            b"M\0missing-terminator",
            b"R100\0only-one-path\0",
            b"Q\0some.py\0",
            b"Rno\0one\0two\0",
        ):
            with self.subTest(value=value):
                with self.assertRaises(CHECKER.ScopeError):
                    CHECKER.parse_changes(value)


if __name__ == "__main__":
    unittest.main()
