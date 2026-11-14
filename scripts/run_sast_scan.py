#!/usr/bin/env python3
"""REALITY SCIENCE SAST Security Scanner & Secret Detector.

Runs Static Application Security Testing (SAST) and Shannon entropy secret detection
from D:\\AI_Knowledge_Lab\\tools\\secure_coding_scanner against Reality Science codebase.
Excludes virtual environments (.venv), caches (__pycache__, .pytest_cache), and git metadata.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Ensure AI Knowledge Lab scanner tools are importable
AI_KNOWLEDGE_LAB_PATH = Path(r"D:\AI_Knowledge_Lab")
if str(AI_KNOWLEDGE_LAB_PATH) not in sys.path:
    sys.path.insert(0, str(AI_KNOWLEDGE_LAB_PATH))

from tools.secure_coding_scanner.scanner import SecurityScanner, VulnerabilityFinding, ScanReport
from tools.secure_coding_scanner.secret_detector import SecretDetector, SecretFinding


def get_source_files(base_dir: Path) -> List[Path]:
    """Collect source files while strictly ignoring .venv, node_modules, cache dirs."""
    ignore_dirs = {".venv", "venv", ".git", "__pycache__", ".pytest_cache", ".next", "node_modules"}
    collected = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in (".py", ".sql", ".c", ".h", ".cpp"):
                collected.append(p)
    return sorted(collected)


def get_all_scannable_files(base_dir: Path) -> List[Path]:
    """Collect code and config files for secret scanning."""
    ignore_dirs = {".venv", "venv", ".git", "__pycache__", ".pytest_cache", ".next", "node_modules"}
    collected = []
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in (".py", ".sql", ".yml", ".yaml", ".env", ".example", ".toml", ".json", ".conf"):
                collected.append(p)
    return sorted(collected)


def run_sast_scan(project_root: Path) -> Dict[str, Any]:
    scanner = SecurityScanner()
    detector = SecretDetector(entropy_threshold=3.5)

    modules = ["shared", "worker", "backend"]
    results = {
        "modules": {},
        "total_source_files": 0,
        "total_vuln_findings": 0,
        "total_secret_findings": 0,
        "all_vuln_findings": [],
        "all_secret_findings": [],
    }

    for mod in modules:
        mod_dir = project_root / mod
        source_files = get_source_files(mod_dir)
        config_files = get_all_scannable_files(mod_dir)

        vuln_findings: List[VulnerabilityFinding] = []
        for sf in source_files:
            rep = scanner.scan_file(sf)
            if rep.findings:
                vuln_findings.extend(rep.findings)

        secret_findings: List[SecretFinding] = []
        for cf in config_files:
            try:
                s_findings = detector.scan_secrets(cf)
                if s_findings:
                    secret_findings.extend(s_findings)
            except Exception as e:
                pass

        results["modules"][mod] = {
            "source_files_count": len(source_files),
            "config_files_count": len(config_files),
            "vulnerabilities": [f.to_dict() for f in vuln_findings],
            "secrets": [s.to_dict() for s in secret_findings],
        }
        results["total_source_files"] += len(source_files)
        results["total_vuln_findings"] += len(vuln_findings)
        results["total_secret_findings"] += len(secret_findings)
        results["all_vuln_findings"].extend(vuln_findings)
        results["all_secret_findings"].extend(secret_findings)

    return results


if __name__ == "__main__":
    root = Path(r"D:\Reality_Science")
    print("=" * 80)
    print("REALITY SCIENCE — STATIC APPLICATION SECURITY TESTING (SAST) AUDIT")
    print(f"Scanning project root: {root}")
    print("=" * 80)

    results = run_sast_scan(root)

    print(f"Total Source Files Scanned: {results['total_source_files']}")
    print(f"Total SAST Vulnerability Findings: {results['total_vuln_findings']}")
    print(f"Total Secret Detector Findings: {results['total_secret_findings']}")
    print("-" * 80)

    for mod, data in results["modules"].items():
        print(f"\n[Module: {mod}]")
        print(f"  Source files scanned: {data['source_files_count']}")
        print(f"  Vulnerabilities: {len(data['vulnerabilities'])}")
        for v in data["vulnerabilities"]:
            print(f"    - [{v['severity']}] {v['cwe_id']} at {v['file']}:{v['line']}")
            print(f"      Snippet: {v['snippet']}")
            print(f"      Remediation: {v['remediation']}")
        print(f"  Secret Alerts: {len(data['secrets'])}")
        for s in data["secrets"]:
            print(f"    - [{s['secret_type']}] at {s['file']}:{s['line']} (entropy={s['entropy']:.2f})")
            print(f"      Snippet: {s['snippet']}")

    print("\n" + "=" * 80)
    print("SAST AUDIT COMPLETE")
    print("=" * 80)
