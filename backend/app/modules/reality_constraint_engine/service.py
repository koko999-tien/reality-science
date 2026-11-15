"""Zone 2 Backend Epistemic Logic Service.

Provides in-memory graph validation (Tarjan's SCC, explicit/interval contradictions,
topological status propagation) strictly adhering to Zone 2 constraints:
- ZERO imports from worker (preserves strict Zone 2 / Zone 3 layer isolation)
- ZERO dependencies on sympy (which is isolated to Zone 3 compute worker)
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple

from shared.models.enums import DiagnosticCode
from shared.schemas.epistemic_logic import (
    ClaimDependency,
    ClaimGraph,
    ClaimGraphValidationResult,
    ClaimSpec,
    ClaimType,
    ContradictionItem,
    ContradictionReport,
    ContradictionType,
    CycleReport,
    DependencyLogic,
    EpistemicFinding,
    RelationType,
)
from shared.schemas.finding_result import FindingState


SEVERITY_ORDER: Dict[FindingState, int] = {
    FindingState.PASS: 0,
    FindingState.NOT_APPLICABLE: 1,
    FindingState.WARNING: 2,
    FindingState.NOT_YET_TESTED: 3,
    FindingState.INSUFFICIENT_DATA: 4,
    FindingState.NEEDS_EXPERT_REVIEW: 5,
    FindingState.FAIL: 6,
}


def _extract_sccs(nodes: List[str], adj: Dict[str, List[str]]) -> List[List[str]]:
    index = 0
    indices: Dict[str, int] = {}
    lowlink: Dict[str, int] = {}
    on_stack: Set[str] = set()
    stack: List[str] = []
    sccs: List[List[str]] = []

    def strongconnect(v: str) -> None:
        nonlocal index
        indices[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)

        for w in adj.get(v, []):
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])

        if lowlink[v] == indices[v]:
            component: List[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                component.append(w)
                if w == v:
                    break
            sccs.append(component)

    for node in nodes:
        if node not in indices:
            strongconnect(node)

    return sccs


def _extract_cycle_path(scc_nodes: Set[str], adj: Dict[str, List[str]]) -> List[str]:
    start = next(iter(scc_nodes))
    if start in adj.get(start, []):
        return [start, start]

    visited: Set[str] = set()
    path: List[str] = [start]

    def dfs(current: str) -> Optional[List[str]]:
        for nxt in adj.get(current, []):
            if nxt not in scc_nodes:
                continue
            if nxt == start and len(path) > 1:
                return path + [start]
            if nxt not in visited:
                visited.add(nxt)
                path.append(nxt)
                res = dfs(nxt)
                if res:
                    return res
                path.pop()
        return None

    visited.add(start)
    res = dfs(start)
    if res:
        return res

    for alternate in scc_nodes:
        if alternate == start:
            continue
        visited.clear()
        path.clear()
        path.append(alternate)
        visited.add(alternate)
        res = dfs(alternate)
        if res:
            return res

    return list(scc_nodes) + [list(scc_nodes)[0]]


def detect_cycles_backend(graph: ClaimGraph) -> CycleReport:
    node_ids = [c.claim_id for c in graph.claims]
    adj: Dict[str, List[str]] = defaultdict(list)
    has_self_loop: Dict[str, bool] = defaultdict(bool)

    inferential_relations = {
        RelationType.DEPENDS_ON,
        RelationType.DERIVED_FROM,
    }

    for dep in graph.dependencies:
        if dep.relation_type in inferential_relations:
            adj[dep.source_claim_id].append(dep.target_claim_id)
            if dep.source_claim_id == dep.target_claim_id:
                has_self_loop[dep.source_claim_id] = True

    sccs = _extract_sccs(node_ids, adj)

    cycle_detected = False
    cycles: List[List[str]] = []
    cyclic_claim_ids: Set[str] = set()

    for scc in sccs:
        if len(scc) > 1:
            cycle_detected = True
            scc_set = set(scc)
            cyclic_claim_ids.update(scc_set)
            path = _extract_cycle_path(scc_set, adj)
            cycles.append(path)
        elif len(scc) == 1:
            node = scc[0]
            if has_self_loop[node]:
                cycle_detected = True
                cyclic_claim_ids.add(node)
                cycles.append([node, node])

    return CycleReport(
        cycle_detected=cycle_detected,
        cycles=cycles,
        cyclic_claim_ids=cyclic_claim_ids,
    )


def detect_contradictions_backend(graph: ClaimGraph) -> ContradictionReport:
    items: List[ContradictionItem] = []
    claims_by_id = {c.claim_id: c for c in graph.claims}

    # 1. Explicit CONTRADICTS links
    for dep in graph.dependencies:
        if dep.relation_type == RelationType.CONTRADICTS:
            c_a = claims_by_id.get(dep.source_claim_id)
            c_b = claims_by_id.get(dep.target_claim_id)
            if c_a and c_b:
                if c_a.local_state == FindingState.PASS and c_b.local_state == FindingState.PASS:
                    items.append(
                        ContradictionItem(
                            contradiction_type=ContradictionType.EXPLICIT_CONTRADICTION,
                            claim_id_a=c_a.claim_id,
                            claim_id_b=c_b.claim_id,
                            description=(
                                f"Explicit CONTRADICTS relation exists between {c_a.claim_code} "
                                f"and {c_b.claim_code}, but both evaluate to PASS locally."
                            ),
                            symbolic_proof="Explicit CONTRADICTS relation declared between two PASS claims",
                            severity=FindingState.FAIL,
                        )
                    )

    # 2. Metadata interval and sign contradictions
    claims_by_target: Dict[str, List[ClaimSpec]] = defaultdict(list)
    for c in graph.claims:
        if c.target_variable:
            claims_by_target[c.target_variable].append(c)

    for target_var, claims_group in claims_by_target.items():
        if len(claims_group) < 2:
            continue
        for i in range(len(claims_group)):
            for j in range(i + 1, len(claims_group)):
                c_i = claims_group[i]
                c_j = claims_group[j]

                # Check intervals
                int_i = c_i.metadata.get("interval")
                int_j = c_j.metadata.get("interval")
                if int_i and int_j and isinstance(int_i, (list, tuple)) and isinstance(int_j, (list, tuple)):
                    l_i, u_i = float(int_i[0]), float(int_i[1])
                    l_j, u_j = float(int_j[0]), float(int_j[1])
                    # Disjoint intervals: u_i < l_j or u_j < l_i
                    if u_i < l_j or u_j < l_i:
                        items.append(
                            ContradictionItem(
                                contradiction_type=ContradictionType.BOUNDARY_CONFLICT,
                                claim_id_a=c_i.claim_id,
                                claim_id_b=c_j.claim_id,
                                conflict_variable=target_var,
                                description=(
                                    f"Claims {c_i.claim_code} and {c_j.claim_code} specify mutually exclusive "
                                    f"intervals for '{target_var}': [{l_i}, {u_i}] and [{l_j}, {u_j}]."
                                ),
                                symbolic_proof=f"Disjoint intervals: [{l_i}, {u_i}] cap [{l_j}, {u_j}] == empty",
                                severity=FindingState.FAIL,
                            )
                        )

                # Check sign
                sign_i = c_i.metadata.get("sign")
                sign_j = c_j.metadata.get("sign")
                if (sign_i == "positive" and sign_j in ("negative", "non_positive")) or (
                    sign_j == "positive" and sign_i in ("negative", "non_positive")
                ):
                    items.append(
                        ContradictionItem(
                            contradiction_type=ContradictionType.SIGN_CONFLICT,
                            claim_id_a=c_i.claim_id,
                            claim_id_b=c_j.claim_id,
                            conflict_variable=target_var,
                            description=(
                                f"Sign conflict for variable '{target_var}': {c_i.claim_code} asserts {sign_i} "
                                f"while {c_j.claim_code} asserts {sign_j}."
                            ),
                            symbolic_proof=f"Sign mismatch: {sign_i} vs {sign_j}",
                            severity=FindingState.FAIL,
                        )
                    )

    return ContradictionReport(
        contradictions_found=len(items) > 0,
        items=items,
    )


def propagate_epistemic_status_backend(
    graph: ClaimGraph,
    cycle_report: CycleReport,
    contradiction_report: ContradictionReport,
) -> Tuple[Dict[str, EpistemicFinding], Optional[List[str]]]:
    claims_by_id = {c.claim_id: c for c in graph.claims}
    findings: Dict[str, EpistemicFinding] = {}

    contradicting_claim_ids: Set[str] = set()
    contradiction_details: Dict[str, List[str]] = defaultdict(list)
    for item in contradiction_report.items:
        if item.severity == FindingState.FAIL:
            contradicting_claim_ids.add(item.claim_id_a)
            contradicting_claim_ids.add(item.claim_id_b)
            contradiction_details[item.claim_id_a].append(item.description)
            contradiction_details[item.claim_id_b].append(item.description)

    # 1. Cyclic nodes
    for cyclic_id in cycle_report.cyclic_claim_ids:
        c = claims_by_id.get(cyclic_id)
        code = c.claim_code if c else cyclic_id
        participating_cycle = next((cyc for cyc in cycle_report.cycles if cyclic_id in cyc), None)
        path_str = " -> ".join(participating_cycle) if participating_cycle else cyclic_id
        findings[cyclic_id] = EpistemicFinding(
            claim_id=cyclic_id,
            state=FindingState.FAIL,
            diagnostic_code=DiagnosticCode.CIRCULAR_DEPENDENCY_DETECTED.value,
            message=f"Circular dependency loop detected: {path_str}. Scientific reasoning must be well-founded (DAG).",
            cycle_membership=participating_cycle,
            diagnostics=[f"Participates in cycle: {path_str}"],
        )

    # 2. Contradiction nodes
    for cont_id in contradicting_claim_ids:
        if cont_id not in findings:
            c = claims_by_id.get(cont_id)
            code = c.claim_code if c else cont_id
            reasons = contradiction_details.get(cont_id, [])
            findings[cont_id] = EpistemicFinding(
                claim_id=cont_id,
                state=FindingState.FAIL,
                diagnostic_code=DiagnosticCode.CROSS_CLAIM_CONTRADICTION.value,
                message=f"Cross-claim contradiction detected for {code}: " + "; ".join(reasons),
                contradictions=reasons,
                diagnostics=reasons,
            )

    inferential_relations = {
        RelationType.DEPENDS_ON,
        RelationType.DERIVED_FROM,
    }
    prereqs_of: Dict[str, List[str]] = defaultdict(list)
    dependents_of: Dict[str, List[str]] = defaultdict(list)
    in_degree: Dict[str, int] = defaultdict(int)

    acyclic_node_ids = [cid for cid in claims_by_id.keys() if cid not in cycle_report.cyclic_claim_ids]

    for dep in graph.dependencies:
        if dep.relation_type in inferential_relations:
            src = dep.source_claim_id
            tgt = dep.target_claim_id
            if src in claims_by_id and tgt in claims_by_id:
                if src in acyclic_node_ids:
                    prereqs_of[src].append(tgt)
                    if tgt in acyclic_node_ids:
                        dependents_of[tgt].append(src)

    for node in acyclic_node_ids:
        in_degree[node] = len([p for p in prereqs_of[node] if p in acyclic_node_ids])

    queue = deque([node for node in acyclic_node_ids if in_degree[node] == 0])
    topo_order: List[str] = []

    while queue:
        curr = queue.popleft()
        topo_order.append(curr)
        for dep_node in dependents_of[curr]:
            in_degree[dep_node] -= 1
            if in_degree[dep_node] == 0:
                queue.append(dep_node)

    for node in acyclic_node_ids:
        if node not in topo_order:
            topo_order.append(node)

    for node in topo_order:
        if node in findings:
            continue

        c = claims_by_id[node]
        prereqs = prereqs_of[node]

        if not prereqs:
            local_st = c.local_state
            findings[node] = EpistemicFinding(
                claim_id=node,
                state=local_st,
                diagnostic_code=(
                    DiagnosticCode.EPISTEMIC_VALIDATION_PASSED.value
                    if local_st == FindingState.PASS
                    else f"LOCAL_{local_st.value}"
                ),
                message=f"Claim {c.claim_code} ({c.claim_type.value}) has state {local_st.value}.",
                diagnostics=[f"Local state: {local_st.value}"],
            )
            continue

        failed_prereqs = [p for p in prereqs if p in findings and findings[p].state == FindingState.FAIL]
        warning_prereqs = [p for p in prereqs if p in findings and findings[p].state == FindingState.WARNING]
        unresolved_prereqs = [
            p
            for p in prereqs
            if p not in findings
            or findings[p].state in (FindingState.INSUFFICIENT_DATA, FindingState.NOT_YET_TESTED, FindingState.NEEDS_EXPERT_REVIEW)
        ]

        if c.dependency_logic == DependencyLogic.ALL:
            if failed_prereqs:
                failed_codes = [claims_by_id[p].claim_code if p in claims_by_id else p for p in failed_prereqs]
                findings[node] = EpistemicFinding(
                    claim_id=node,
                    state=FindingState.FAIL,
                    diagnostic_code=DiagnosticCode.EPISTEMIC_ANTECEDENT_FAILED.value,
                    message=f"Claim {c.claim_code} failed due to epistemic poisoning from antecedent failure in: {', '.join(failed_codes)}.",
                    antecedent_failures=failed_prereqs,
                    diagnostics=[f"Poisoned by failed antecedent(s): {', '.join(failed_codes)}"],
                )
            elif unresolved_prereqs:
                unres_codes = [claims_by_id[p].claim_code if p in claims_by_id else p for p in unresolved_prereqs]
                findings[node] = EpistemicFinding(
                    claim_id=node,
                    state=FindingState.INSUFFICIENT_DATA,
                    diagnostic_code=DiagnosticCode.EPISTEMIC_DEPENDENCY_UNRESOLVED.value,
                    message=f"Claim {c.claim_code} has unresolved antecedent dependencies: {', '.join(unres_codes)}.",
                    diagnostics=[f"Unresolved antecedent(s): {', '.join(unres_codes)}"],
                )
            elif warning_prereqs:
                warn_codes = [claims_by_id[p].claim_code if p in claims_by_id else p for p in warning_prereqs]
                prop_st = FindingState.WARNING if c.local_state == FindingState.PASS else c.local_state
                findings[node] = EpistemicFinding(
                    claim_id=node,
                    state=prop_st,
                    diagnostic_code=DiagnosticCode.EPISTEMIC_ANTECEDENT_WARNING.value,
                    message=f"Claim {c.claim_code} inherited warning from antecedent(s): {', '.join(warn_codes)}.",
                    diagnostics=[f"Antecedent warning from: {', '.join(warn_codes)}"],
                )
            else:
                findings[node] = EpistemicFinding(
                    claim_id=node,
                    state=c.local_state,
                    diagnostic_code=(
                        DiagnosticCode.EPISTEMIC_VALIDATION_PASSED.value
                        if c.local_state == FindingState.PASS
                        else f"LOCAL_{c.local_state.value}"
                    ),
                    message=(
                        f"Claim {c.claim_code} successfully verified. All antecedents passed."
                        if c.local_state == FindingState.PASS
                        else f"All antecedents passed, local state is {c.local_state.value}."
                    ),
                    diagnostics=["All antecedents verified: PASS."],
                )
        elif c.dependency_logic == DependencyLogic.ANY:
            passed_prereqs = [p for p in prereqs if p in findings and findings[p].state == FindingState.PASS]
            if passed_prereqs:
                passed_codes = [claims_by_id[p].claim_code if p in claims_by_id else p for p in passed_prereqs]
                findings[node] = EpistemicFinding(
                    claim_id=node,
                    state=c.local_state,
                    diagnostic_code=(
                        DiagnosticCode.EPISTEMIC_VALIDATION_PASSED.value
                        if c.local_state == FindingState.PASS
                        else f"LOCAL_{c.local_state.value}"
                    ),
                    message=f"Claim {c.claim_code} satisfied via alternative route(s): {', '.join(passed_codes)}.",
                    diagnostics=[f"Satisfied via: {', '.join(passed_codes)}"],
                )
            elif len(failed_prereqs) == len(prereqs):
                findings[node] = EpistemicFinding(
                    claim_id=node,
                    state=FindingState.FAIL,
                    diagnostic_code=DiagnosticCode.EPISTEMIC_ANTECEDENT_FAILED.value,
                    message=f"All disjunctive derivation routes failed for claim {c.claim_code}.",
                    antecedent_failures=failed_prereqs,
                    diagnostics=["Every alternative antecedent route failed."],
                )
            else:
                findings[node] = EpistemicFinding(
                    claim_id=node,
                    state=FindingState.INSUFFICIENT_DATA,
                    diagnostic_code=DiagnosticCode.EPISTEMIC_DEPENDENCY_UNRESOLVED.value,
                    message=f"No verified antecedent route found yet for disjunctive claim {c.claim_code}.",
                    diagnostics=["Awaiting at least one passing prerequisite route."],
                )

    for c in graph.claims:
        if c.claim_id in findings:
            c.propagated_state = findings[c.claim_id].state

    full_topo = [cid for cid in cycle_report.cyclic_claim_ids] + topo_order
    return findings, full_topo


def verify_claim_graph_backend(graph: ClaimGraph) -> ClaimGraphValidationResult:
    cycle_report = detect_cycles_backend(graph)
    contradiction_report = detect_contradictions_backend(graph)
    findings, topo_order = propagate_epistemic_status_backend(graph, cycle_report, contradiction_report)

    worst_state = FindingState.PASS
    worst_rank = 0
    for f in findings.values():
        rank = SEVERITY_ORDER.get(f.state, 0)
        if rank > worst_rank:
            worst_rank = rank
            worst_state = f.state

    diagnostics: List[str] = [
        f"Zone 2 Epistemic Graph Verification: {len(graph.claims)} claims, {len(graph.dependencies)} relations.",
        f"Cycle Detection: {'CYCLES DETECTED' if cycle_report.cycle_detected else 'DAG OK'}.",
        f"Contradictions: {'CONTRADICTIONS FOUND' if contradiction_report.contradictions_found else 'CONSISTENT OK'}.",
        f"Overall Epistemic State: {worst_state.value}.",
    ]

    return ClaimGraphValidationResult(
        graph_id=graph.graph_id,
        version_id=graph.version_id,
        overall_state=worst_state,
        cycle_report=cycle_report,
        contradiction_report=contradiction_report,
        claim_findings=findings,
        topological_order=topo_order,
        diagnostics=diagnostics,
    )
