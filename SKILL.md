---
name: state-machine-docs
description: Create source-grounded architecture maps, module state diagrams, and source-refreshed documentation as standalone HTML for any project. Use when asked for architecture documentation, state-machine maps, or an HTML documentation explorer with grouped and flat views.
license: MIT
disable-model-invocation: true
---

# Architecture and state-machine documentation

Produce one HTML file the user can double-click or share. It contains the
renderer, diagram data, and source excerpts. Viewing it requires no server,
installation, CDN, or internet connection. Supporting project files retain the
recipe for regeneration.

## Map the implementation first

1. Inspect project instructions, entrypoints, dependency declarations, module
   ownership, and existing documentation. Map the current checkout, including
   relevant uncommitted changes. Treat attached examples as design references,
   not authority over the implementation.
2. Trace a representative operation across interfaces, orchestration, domain
   logic, external dependencies, and persistence. Locate the actual graph
   builders, enums, transition tables, reducers, or lifecycle branches.
3. Identify the primary architecture layers and their responsibilities. Build
   an overview with links to deeper module views. Keep the overview as the
   landing page. Focus on application architecture by default; include
   benchmark and reporting maps when requested or part of the requested scope.
4. For each stateful layer, identify states, events, guards, side effects,
   terminal outcomes, and bounded retries from the source. For a stateless
   module, use an ownership or process diagram instead of inventing states.

Finish this step with source references for every behavior described. Mark
unresolved claims as unknown rather than drawing speculative transitions.

## Build diagrams with honest semantics

- Label each view as architecture, extracted graph, persisted state lifecycle,
  derived state, or process. Graph termination, successful execution, answer
  quality, and UI presentation can be separate domains.
- Extract topology from declarative graph builders when practical. Keep that
  extraction in a project-specific collector that updates the section records.
  The bundled renderer accepts records from any language or framework; it does
  not infer transitions from arbitrary source files.
- Use nested groups for ownership boundaries and shared transition rules.
  Model an event leaving a group only when the implementation supports that
  event for its member states. Preserve all nodes and edges in the flat view.
- Include implemented retry guards and failure exits. Distinguish a client
  timeout from server cancellation and a stored terminal outcome from an
  in-memory process step.
- Split a dense diagram into a module overview and smaller views. Labels and
  source excerpts should answer why an edge exists without requiring readers
  to inspect a giant graph.
- When several events return to the same state, use one self-loop caption
  listing those events and explain their separate guards in source notes.
  If an extracted graph needs distinct parallel edges, split that detail into
  smaller views so their captions stay separate.
- Keep edge captions short. Put full guard expressions in the source evidence
  and behavior notes rather than widening a loop to hold a sentence.

## Generate the standalone explorer

Read [the section schema](references/sections.md) before writing the manifest.
Use the bundled [HTML template](assets/template.html) and
[generator](scripts/build_docs.py). Their defaults preserve the requested
design: sidebar module navigation, grouped and flat views, zoom, source
excerpts, and compact oval self-loops with labels beside the arrow. There is
no layer-search control. Explicit user preferences can change these defaults.

Copy the generator to the project's `scripts/build_architecture_docs.py`.
Place the template, Mermaid renderer, and its license under
`docs/architecture`, preserving the `assets` layout used by the generator.
Write `docs/architecture/architecture.json` using the schema. Adjust the
destination if the project already has a documentation convention.

Run from the project root:

```text
python scripts/build_architecture_docs.py
python scripts/build_architecture_docs.py --check
```

The generator writes `index.html`, `index.md`, and `revision.json` beside the
manifest. It reads text source without importing or running the application.
It includes only referenced source files and explicit `watch` patterns in the
freshness inputs. Keep these patterns narrow. Exclude credentials, private
runtime data, dependencies, and generated documentation.

Source fingerprints detect changes that need review. They do not prove that
authored diagrams remain correct. Review changed behavior and update source
line ranges before regenerating. If executable topology extraction is used,
connect its collector to the project's regeneration command rather than
claiming the generic generator performs that extraction.

## Verify the artifact

1. Run generation and `--check`. Generate again and confirm identical output.
2. Open the HTML using a `file:` URL. Copy it to a directory without adjacent
   assets and confirm it still renders.
3. With a browser automation tool, run
   [the browser page function](scripts/verify_browser.js) against the open
   file. It checks grouped/flat topology equality, self-loop dimensions and
   label placement, zoom, source expansion, navigation, and mobile overflow.
   If the environment cannot run that function, perform equivalent checks and
   report the limitation. Inspect at least one rendered self-loop visually.
4. Check a source-change experiment in a temporary copy. A changed watched file
   must fail `--check`; regeneration must restore a passing check. Recheck
   representative transition guards against the implementation.

For changes to the bundled generator, run `python scripts/test_build_docs.py`
from the skill folder or pass its absolute path from a writable working folder.

Keep verification proportional to the documentation change. Do not run
providers, modify application behavior, or create CI jobs merely to view the
documentation. Integrate freshness checking into existing documentation checks
when it fits the requested scope.

Deliver the standalone HTML link, the covered architecture layers, verification
results, and the command to refresh it. Explain that it is a source snapshot;
it does not monitor a running application. Ask about execution monitoring only
when the user requests that distinct capability.
