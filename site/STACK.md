# Stack Recommendation (static, spec-first)

## Recommendation
**Astro + Starlight**
- Naturally "spec/doc" feeling
- Fast static output, simple hosting
- Easy to keep `/spec/` as MD/MDX while shipping `/machine/` JSON artifacts

If you want even more austere: Astro without Starlight + custom layout.

## Proposed file tree
```text
/
├─ public/
│  ├─ .well-known/
│  │  ├─ manifest.json
│  │  └─ llms.txt
│  ├─ machine/
│  │  └─ index.json
│  ├─ schemas/
│  │  └─ v1/
│  │     ├─ capsule.manifest.schema.json
│  │     ├─ redaction.report.schema.json
│  │     └─ restore.report.schema.json
│  ├─ examples/
│  │  ├─ minimal.json
│  │  └─ typical.json
│  ├─ conformance/
│  │  └─ levels.json
│  └─ fonts/
│     └─ .gitkeep
├─ src/
│  ├─ content/docs/
│  │  ├─ index.mdx
│  │  ├─ changelog.mdx
│  │  ├─ spec/
│  │  │  ├─ index.mdx
│  │  │  ├─ contract.mdx
│  │  │  ├─ protocol.mdx
│  │  │  ├─ schemas.mdx
│  │  │  └─ anchors.mdx
│  │  ├─ machine/
│  │  │  ├─ index.mdx
│  │  │  ├─ artifacts.mdx
│  │  │  └─ llm-instructions.mdx
│  │  ├─ meditations/
│  │  │  ├─ index.mdx
│  │  │  └─ ship-of-theseus.mdx
│  │  ├─ examples/
│  │  │  └─ index.mdx
│  │  └─ conformance/
│  │     ├─ index.mdx
│  │     ├─ levels.mdx
│  │     └─ tests.mdx
│  ├─ components/
│  │  ├─ MachineLayerPanel.astro
│  │  ├─ AnchorGutter.astro
│  │  ├─ NormativeBlock.astro
│  │  ├─ CopyButton.astro
│  │  ├─ LogLine.astro
│  │  ├─ SigilMark.astro
│  │  └─ MeditationQuote.astro
│  ├─ layouts/
│  │  ├─ BaseLayout.astro
│  │  ├─ SpecLayout.astro
│  │  └─ MeditationsLayout.astro
│  └─ styles/
│     ├─ tokens.css
│     ├─ theme.css
│     ├─ typography.css
│     ├─ components.css
│     ├─ fonts.css
│     └─ meditations.css
├─ astro.config.mjs
├─ package.json
└─ tsconfig.json
```

## Implementation notes
- Explicit heading IDs in MDX (no auto slugs drifting)
- Anchor registry page (`/spec/anchors/`) is part of the public API
- A build step can compute sha256 and generate manifest/index deterministically
- Schema filenames follow `v1/` versioned directory structure
