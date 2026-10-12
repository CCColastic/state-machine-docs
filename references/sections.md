# Section records

The manifest is JSON with `project`, `sections`, and optional `watch` fields.
The first section has ID `overview`. IDs are unique URL-fragment-safe strings.

```json
{
  "project": "Example service",
  "watch": ["src/**/*.js"],
  "sections": [
    {
      "id": "overview",
      "title": "Architecture overview",
      "kind": "architecture",
      "summary": "The API admits work and a worker processes queued jobs.",
      "mermaid": "flowchart TB\nsubgraph interface[Interfaces]\napi[API]\nend\nsubgraph execution[Execution]\nqueue[Queue] --> worker[Worker]\nend\napi --> queue",
      "notes": ["This is an ownership view, not a persisted state machine."],
      "sources": [
        {"path": "src/api.js", "symbol": "submitJob", "start_line": 1, "end_line": 12}
      ],
      "tests": ["tests/jobs.test.js"]
    }
  ]
}
```

Paths are relative to the project root. `symbol` is a display label. The generic
generator verifies files and line ranges, but it does not resolve symbols in
every programming language. A project-specific collector can locate symbols
and emit current line ranges before generation.

`sources`, `notes`, and `tests` can be empty arrays. Cite implementation symbols
for behavior and existing tests for relevant checks. Test links do not mean
those tests ran during documentation generation.

Use `flowchart TB` or `flowchart TD` for the bundled flat-view conversion. Put
`subgraph ...` and its closing `end` on their own lines. Keep actual node and
edge declarations outside group-header lines. Removing only the group lines
must leave a valid flat diagram with the same topology. For more complex
group-only layout directives, provide an explicit `flat` diagram and verify
its topology equals the grouped `mermaid` diagram.

For an extracted graph, optional `edges` records drive the transition table:

```json
"edges": [
  ["queued", "running", "claim succeeds"],
  ["running", "running", "lease renewed"],
  ["running", "completed", "result committed"]
]
```

Use source states and router return values for extracted topology. A separate
process diagram can explain internal calls without relabeling them as stored
states. Diagram labels may be readable descriptions when a process has no
named code state.

The bundled self-loop treatment applies to the vendored Mermaid flowchart
renderer. It preserves edge endpoints and places wrapped text beside a compact
oval about 38 by 20 SVG units. Renderer upgrades require checking this geometry
and edge-label association again.

Use one self-loop per node in a view. Combine captions for multiple self-events
without dropping an event or its guard. Use separate detail views when distinct
parallel edges must remain individually visible. Browser verification rejects
overlapping self-loop captions.

`watch` contains project-relative source globs. Referenced source files and
test files are always fingerprinted. Template, renderer, license, manifest, and
generator are also fingerprinted. Text hashes normalize newline conventions.
The generator excludes its own output directory from watched source globs.
Select textual application source; avoid repository-wide patterns that pull
in data, binary assets, installed packages, or credentials.

Generated HTML embeds source excerpts. Review the cited content before sharing
the file. Source-file links remain project-relative and work when the HTML
stays in its generated location. Embedded diagrams and excerpts remain usable
when the single HTML file is copied elsewhere.
