import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "build_docs", Path(__file__).with_name("build_docs.py")
)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class BuildDocumentationTests(unittest.TestCase):
    def update_manifest(self, change):
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        change(manifest)
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / "docs/architecture"
        (self.directory / "assets").mkdir(parents=True)
        (self.root / "src").mkdir()
        self.source = self.root / "src/jobs.js"
        self.source.write_text(
            'export const states = ["queued", "running", "completed"];\n'
            'export const example = "</script>";\n',
            encoding="utf-8",
        )
        (self.directory / "template.html").write_text(
            "<title>__PROJECT_NAME__</title>"
            '<script type="application/json">__DOCUMENTATION_DATA__</script>'
            "<script>__MERMAID_RENDERER__</script>",
            encoding="utf-8",
        )
        (self.directory / "assets/mermaid.min.js").write_text(
            'window.rendererExample="</script>";', encoding="utf-8"
        )
        (self.directory / "assets/mermaid-LICENSE").write_text(
            "Fixture license", encoding="utf-8"
        )
        self.manifest = self.directory / "architecture.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "project": "Job service",
                    "watch": ["src/**/*.js"],
                    "sections": [
                        {
                            "id": "overview",
                            "title": "Job lifecycle",
                            "kind": "persisted state lifecycle",
                            "summary": "A claimed job becomes running.",
                            "mermaid": "flowchart TB\nsubgraph work[Work]\nqueued --> running\nend",
                            "sources": [
                                {
                                    "path": "src/jobs.js",
                                    "symbol": "states",
                                    "start_line": 1,
                                    "end_line": 2,
                                }
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        def add_detail(manifest):
            detail = dict(manifest["sections"][0], id="worker", title="Worker decisions")
            manifest["sections"].append(detail)
            manifest["coverage"] = [{"path": "src/jobs.js", "symbol": "states", "section": "worker"}]
        self.update_manifest(add_detail)

    def test_non_python_source_embeds_safely_and_build_is_deterministic(self):
        builder.build(self.root, self.manifest)
        self.assertEqual(builder.build(self.root, self.manifest, write=False), [])
        page = (self.directory / "index.html").read_text(encoding="utf-8")
        self.assertIn("<title>Job service</title>", page)
        self.assertIn('window.rendererExample="<\\/script>";', page)
        self.assertIn('"flat": "flowchart TB\\nqueued --> running"', page)
        self.assertIn("\\u003c/script>", page)
        self.assertNotIn("__DOCUMENTATION_DATA__", page)
        self.assertEqual(builder.build(self.root, self.manifest), [])

    def test_source_change_fails_freshness_and_regeneration_restores_it(self):
        builder.build(self.root, self.manifest)
        self.source.write_text(
            self.source.read_text(encoding="utf-8") + "export const version=2;\n",
            encoding="utf-8",
        )
        self.assertIn(
            "index.html", builder.build(self.root, self.manifest, write=False)
        )
        builder.build(self.root, self.manifest)
        self.assertEqual(builder.build(self.root, self.manifest, write=False), [])

    def test_source_outside_project_is_rejected(self):
        outside = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(outside.cleanup)
        source = Path(outside.name) / "outside.js"
        source.write_text("export const secret = 'fixture';\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "existing project file"):
            builder.source_path(self.root, str(source))

    def test_coverage_requires_discovery_and_cited_detail(self):
        self.update_manifest(lambda manifest: manifest.pop("coverage"))
        with self.assertRaisesRegex(ValueError, "record coverage"):
            builder.build(self.root, self.manifest)
        self.update_manifest(lambda manifest: manifest.update(coverage=[
            {"path": "src/jobs.js", "symbol": "states", "section": "overview"}
        ]))
        with self.assertRaisesRegex(ValueError, "module detail"):
            builder.build(self.root, self.manifest)
        self.update_manifest(lambda manifest: manifest["coverage"][0].update(section="worker"))
        self.update_manifest(lambda manifest: manifest["sections"][1].update(sources=[]))
        with self.assertRaisesRegex(ValueError, "cite the covered"):
            builder.build(self.root, self.manifest)

    def test_excluded_component_is_still_fingerprinted(self):
        self.update_manifest(lambda manifest: manifest["coverage"][0].update(
            section=None, reason="Pure display helper without domain decisions"
        ))
        self.update_manifest(lambda manifest: manifest.update(watch=[]))
        self.update_manifest(lambda manifest: [section.update(sources=[]) for section in manifest["sections"]])
        builder.build(self.root, self.manifest)
        revision = json.loads((self.directory / "revision.json").read_text(encoding="utf-8"))
        self.assertIn("src/jobs.js", revision["sources"])
        self.source.write_text("export const changed = true;\n", encoding="utf-8")
        self.assertIn("index.html", builder.build(self.root, self.manifest, write=False))


if __name__ == "__main__":
    unittest.main()
