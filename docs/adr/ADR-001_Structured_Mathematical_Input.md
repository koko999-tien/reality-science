# ADR-001: Structured Mathematical AST Input & Elimination of Arbitrary Code Execution

## Status
**Approved** (Governing Mandate: Approved Decision 1)

## Date
2026-11-13

## Deciders
Technical Steering Committee / Master Project Brief v1.0

## Context & Problem Statement
REALITY SCIENCE is designed to verify mathematical equations, physical dimensional validity, and empirical claims. In traditional academic and scientific web applications, users typically submit mathematical content either as raw LaTeX presentation strings, free-form Python scripts, or Jupyter notebooks.

Accepting arbitrary Python code or raw LaTeX strings poses fatal architectural and security hazards:
1. **Remote Code Execution (RCE)**: Evaluating user-supplied strings using Python's `eval()`, `exec()`, or unconstrained `sympy.parsing.sympy_parser.parse_expr` allows malicious actors to execute arbitrary host commands (e.g., `__import__('os').system(...)`, traversing `__class__.__subclasses__`, or executing bytecode exploits).
2. **Algorithmic Denial of Service (Symbolic Bombs)**: Expressions such as `(x + y + z + w)**100`, deeply nested transcendental equations, or unsolvable non-elementary integrals cause combinatorial explosion in computer algebra systems, exhausting worker CPU and RAM.
3. **Semantic Ambiguity**: Raw LaTeX is visual, not semantic. For example, $E(x)$ could represent a function call or the product $E \cdot x$; the symbol $m$ could represent the physical quantity mass ($m$) or the SI unit meter ($\text{m}$). Without explicit operational definitions and declared units, automated verification is impossible.

### Alternatives Considered
- **Alternative 1: Raw LaTeX Parsing with Regex / Heuristics**: Rejected. LaTeX is presentation-focused; parsing semantics from LaTeX requires fragile heuristic guessing and fails on non-trivial mathematical notations.
- **Alternative 2: Python Script Uploads in Ephemeral Sandboxes**: Rejected for Stage 0/MVP. Arbitrary script execution creates a continuous attack surface (sandbox escapes, kernel exploits) and introduces non-deterministic execution risks.
- **Alternative 3: Python `eval()` with Global Whitelisting**: Rejected. Python's dynamic runtime makes blacklisting or shallow whitelisting fundamentally unsafe against object introspection escapes.
- **Alternative 4: Structured Abstract Syntax Tree (AST) with Pydantic Contracts**: Chosen. Formulas are broken into typed AST nodes (`ExprNode`) referencing explicitly declared variables (`VariableSpec`) and units (`UnitSpec`).

## Decision
1. **Symbol-First Authoring**: Users must declare an explicit table of variables and physical units for each version scope before equations can be authored or validated. Undeclared symbols in equations are rejected at the schema validation boundary.
2. **Dual-Representation Model**:
   - **Display LaTeX (`latex_raw`)**: Stored strictly for KaTeX presentation in the web frontend. Sanitized against Cross-Site Scripting (XSS). Never passed to execution engines.
   - **Canonical AST (`canonical_ast_json`)**: Stored as a typed JSON Abstract Syntax Tree (`ExprNode`) representing the unambiguous semantic structure of the formula.
3. **Absolute Ban on Arbitrary Code**: The platform explicitly rejects `.py` file uploads, `eval()`, `exec()`, dynamic imports, shell commands, and string-based SymPy `parse_expr` execution.
4. **Programmatic SymPy & Pint Construction**: Pinned versions of SymPy and Pint in worker processes traverse the validated AST nodes, instantiating symbolic expressions (`sympy.Symbol`, `sympy.Add`, `sympy.Mul`) and Pint unit quantities programmatically.
5. **Algorithmic Complexity Pre-Flight Limits**:
   - Maximum AST recursion depth: **15**.
   - Maximum AST total node count: **100**.
   - Maximum polynomial power / exponent: **20**.
   - Execution timeout: Hard **10.0 seconds** per symbolic check via OS signal alarm (`SIGALRM`).

### Core Contract Schema
```python
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class NodeType(str, Enum):
    CONSTANT = "constant"
    VARIABLE = "variable"
    BINARY_OP = "binary_op"
    UNARY_OP = "unary_op"
    FUNCTION_CALL = "function_call"

class OperatorType(str, Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    POW = "**"
    NEG = "neg"

class AllowedFunction(str, Enum):
    SQRT = "sqrt"
    SIN = "sin"
    COS = "cos"
    EXP = "exp"
    LOG = "log"

class UnitSpec(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    symbol: str
    dimensionality: str  # e.g., '[length] / [time]'
    scale_factor: float = 1.0

class VariableSpec(BaseModel):
    symbol: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    name: str
    unit: str
    domain: str = "real"  # 'real', 'positive_real', 'integer', 'complex'
    latex_presentation: Optional[str] = None

class ExprNode(BaseModel):
    node_type: NodeType
    value: Optional[Union[float, int, str]] = None
    op: Optional[OperatorType] = None
    func: Optional[AllowedFunction] = None
    left: Optional["ExprNode"] = None
    right: Optional["ExprNode"] = None
    args: Optional[List["ExprNode"]] = None

ExprNode.model_rebuild()
```

## Consequences

### Positive
- **Elimination of RCE Attack Surface**: Code injection is rendered architecturally impossible because no user-supplied string is ever executed as code.
- **Unambiguous Semantic Lineage**: Every equation is machine-interpretable, enabling cross-paper claim checking, automated unit cancellation, and theorem proving.
- **Predictable Compute Resource Usage**: AST pre-flight guardrails eliminate symbolic expansion bombs before expressions reach SymPy.

### Negative / Trade-Offs
- **Frontend Complexity**: The web frontend must translate formula authoring into a structured AST or provide an interactive equation builder rather than a simple LaTeX textarea.
- **Author Friction**: Authors must declare variables and units before entering equations, increasing initial submission time.

### Risks & Mitigations
- **Risk**: Richardson's Theorem proves symbolic equivalence ($E \equiv 0$) is mathematically undecidable for general elementary functions.
  - *Mitigation*: When symbolic simplification is inconclusive, the engine falls back to numerical evaluation across 10 random sample points. If consistent within tolerance $\epsilon = 10^{-12}$, it issues `state: "WARNING"`, `diagnostic_code: "SYMBOLIC_UNPROVEN_NUMERICALLY_CONSISTENT"`. If it times out, it issues `state: "NEEDS_EXPERT_REVIEW"`, never crashing the worker.

## Compliance & Verification Rules
1. **Schema Validation Test**: All mathematical endpoints must reject payloads failing Pydantic AST schema validation with HTTP 422.
2. **Zero-Code Linter**: SAST scanners and unit tests must verify that `eval()`, `exec()`, `compile()`, and `sympy.parsing` are strictly absent from backend and worker codebases.
3. **Symbolic Bomb Resilience**: Unit tests must submit deeply nested ASTs and assert that the worker terminates within 10.0 seconds with a graceful `NEEDS_EXPERT_REVIEW` finding.
