# Decision Register

Record only meaningful project decisions.

| ID | Date | Decision | Authority/source | Alternatives | Consequences | Status |
|---|---|---|---|---|---|---|
| ADR-000 | 2026-11-15 | Layer 6 definition conflict: Master Project Brief v1.0 §4 and validation architecture §1 specify Reproducibility & Replication; PROJECT.md Feature 26/M10-M11 and Stage 4 handover §2 specify Epistemic Logic & Cross-Claim Graph. No approved superseding ADR found. | Conflicting project documents; requires project owner/steering decision | Treat Layer 6 presentation as unresolved and avoid asserting either taxonomy in new UI; issue an approved ADR superseding the conflicting definition | UI labels, state mappings, historical report compatibility, and acceptance criteria depend on the decision | DECISION REQUIRED |

Never convert an agent suggestion into an approved decision without the required authorization.

## Bounded implementation choices — 2026-11-16

- Under the authorized single-equation canvas assignment and ADR-001, one canvas represents one unambiguous expression: one explicit equation root or one implicit sink, with every node reaching it and every edge/port checked. Shared operands may expand into the canonical AST; expanded nodes count toward the 100-node limit and the visual result root does not. This does not add multi-equation or selected-subgraph validation UX.
- Nodes, edges and declarations share one React state snapshot. AST/LaTeX/local numeric previews are derived; request invalidation runs outside updaters. Cosmetic node position/selection/measurement changes retain scientific findings.
- Follow-up refinement after independent review: all edits pass through one event/effect-only pure transform of the latest canvas snapshot; the ref advances outside render/React updaters and the same value is set as React state. Validation reads that snapshot so earlier edits in the same batch are included. Auto-layout changes only positions and preserves node IDs, edges and shared-operand identity. This closes implementation defects without changing the single-expression contract.
- Maintain Next major 15 using Next/eslint-config-next 15.5.29 and React/ReactDOM 19.0.9, as confirmed by official release/npm metadata; regenerate normal lockfile without force/overrides. Sources and installed versions are recorded in the canvas evidence directory/log.
- These are bounded engineering choices within the existing assignment, not superseding scientific ADRs. Layer 6 decision remains open.
