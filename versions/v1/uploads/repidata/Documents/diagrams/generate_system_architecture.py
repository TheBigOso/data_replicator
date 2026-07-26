#!/usr/bin/env python3
"""Generate system architecture diagram assets for repidata documentation."""

from __future__ import annotations

import base64
import subprocess
import sys
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
DRAWIO_PATH = OUT_DIR / "system-architecture.drawio"
SVG_PATH = OUT_DIR / "system-architecture.svg"
PNG_PATH = OUT_DIR / "system-architecture.png"

WIDTH = 1600
HEIGHT = 1100


def build_drawio() -> str:
    """Build draw.io mxGraph XML matching the v1 system architecture spec."""
    cells: list[tuple[str, str, str, str]] = []

    def cell(
        cid: str,
        value: str,
        style: str,
        parent: str = "1",
        *,
        vertex: bool = True,
        edge: bool = False,
        source: str | None = None,
        target: str | None = None,
        x: int | None = None,
        y: int | None = None,
        w: int | None = None,
        h: int | None = None,
    ) -> None:
        attrs = [f'id="{cid}"', f'value="{value}"', f'style="{style}"', f'parent="{parent}"', "vertex=1"]
        if edge:
            attrs = [f'id="{cid}"', f'value="{value}"', f'style="{style}"', f'parent="{parent}"', "edge=1"]
            if source:
                attrs.append(f'source="{source}"')
            if target:
                attrs.append(f'target="{target}"')
        if x is not None:
            attrs.extend([f"x={x}", f"y={y}", f"width={w}", f"height={h}"])
        cells.append(("mxCell", " ".join(attrs), "", ""))

    # Title
    cell(
        "title",
        "Enterprise CDC Replication Platform — System Architecture (v1)",
        "text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontSize=22;fontStyle=1;fontColor=#1a1a2e;",
        x=200,
        y=20,
        w=1200,
        h=40,
    )

    # Swimlanes
    cell(
        "lane-data",
        "Data plane — encrypted change files",
        "swimlane;horizontal=0;startSize=34;fillColor=#e8f0fe;strokeColor=#5c7cfa;fontStyle=1;fontSize=14;",
        x=40,
        y=80,
        w=1520,
        h=430,
    )
    cell(
        "lane-control",
        "Control plane — metadata and orchestration",
        "swimlane;horizontal=0;startSize=34;fillColor=#e6f4ea;strokeColor=#34a853;fontStyle=1;fontSize=14;",
        x=40,
        y=540,
        w=1520,
        h=300,
    )

    # Data plane components
    cell(
        "sources",
        "Source databases&#xa;Oracle (direct redo) · SQL Server&#xa;PostgreSQL · DB2",
        "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=12;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;",
        parent="lane-data",
        x=60,
        y=90,
        w=170,
        h=120,
    )
    cell(
        "capture",
        "Capture agent (replagent)&#xa;Universal Rust binary&#xa;Log-layer filter · zstd · AES-256-GCM",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=11;",
        parent="lane-data",
        x=300,
        y=95,
        w=200,
        h=110,
    )
    cell(
        "hublog",
        "Hub file log / relay&#xa;Durable encrypted change files&#xa;Sequence-ordered · ack-based GC",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontSize=11;",
        parent="lane-data",
        x=580,
        y=95,
        w=220,
        h=110,
    )
    cell(
        "integrate",
        "Integrate agent (replagent)&#xa;Burst or continuous apply&#xa;Target-side state table",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=11;",
        parent="lane-data",
        x=880,
        y=95,
        w=200,
        h=110,
    )
    cell(
        "targets",
        "Targets&#xa;Snowflake · Databricks&#xa;File stores (S3 / ADLS / local)",
        "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=12;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=12;",
        parent="lane-data",
        x=1160,
        y=90,
        w=180,
        h=120,
    )

    # Data flow label
    cell(
        "data-label",
        "encrypted change files (protobuf + zstd + AES-256-GCM)",
        "text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=10;fontColor=#555555;",
        parent="lane-data",
        x=520,
        y=230,
        w=340,
        h=24,
    )

    # Callouts
    callouts = [
        (
            "callout-exactly-once",
            "Exactly-once: state table&#xa;co-transactional with apply",
            60,
            300,
        ),
        (
            "callout-broadcast",
            "Broadcast-ready: ack-based GC&#xa;supports one-to-many fan-out",
            360,
            300,
        ),
        (
            "callout-agent-init",
            "Agent-initiated mode:&#xa;agent dials out to hub",
            660,
            300,
        ),
        (
            "callout-repo-boundary",
            "Repository boundary:&#xa;change data never enters repo",
            960,
            300,
        ),
    ]
    for cid, value, x, y in callouts:
        cell(
            cid,
            value,
            "rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#999999;fontSize=10;dashed=1;dashPattern=4 4;",
            parent="lane-data",
            x=x,
            y=y,
            w=250,
            h=70,
        )

    # Control plane components
    cell(
        "operators",
        "Operators&#xa;Web UI · CLI · automation&#xa;(pure REST API clients)",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;fontSize=11;",
        parent="lane-control",
        x=120,
        y=90,
        w=220,
        h=100,
    )
    cell(
        "api",
        "Hub REST API + scheduler&#xa;Single Rust process&#xa;CDC · refresh · compare jobs",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=11;",
        parent="lane-control",
        x=480,
        y=90,
        w=260,
        h=100,
    )
    cell(
        "repo",
        "Repository&#xa;PostgreSQL (prod) / SQLite (dev)&#xa;Metadata only — no row data",
        "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=12;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=11;",
        parent="lane-control",
        x=900,
        y=85,
        w=220,
        h=110,
    )

    # Legend
    cell(
        "legend-box",
        "",
        "rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#666666;",
        x=1240,
        y=880,
        w=300,
        h=120,
    )
    cell(
        "legend-title",
        "Legend",
        "text;html=1;strokeColor=none;fillColor=none;align=left;fontStyle=1;fontSize=12;",
        x=1250,
        y=890,
        w=80,
        h=20,
    )
    cell(
        "legend-solid",
        "━━ Solid arrow = data movement",
        "text;html=1;strokeColor=none;fillColor=none;align=left;fontSize=11;",
        x=1250,
        y=915,
        w=260,
        h=20,
    )
    cell(
        "legend-dashed",
        "- - Dashed arrow = control / mTLS",
        "text;html=1;strokeColor=none;fillColor=none;align=left;fontSize=11;",
        x=1250,
        y=940,
        w=260,
        h=20,
    )
    cell(
        "legend-encrypt",
        "Encryption at agent (before network) and at rest on hub",
        "text;html=1;strokeColor=none;fillColor=none;align=left;fontSize=10;fontColor=#555555;",
        x=1250,
        y=965,
        w=280,
        h=30,
    )

    # Data flow edges (solid)
    data_edges = [
        ("e1", "", "sources", "capture", "endArrow=classic;html=1;strokeWidth=2;strokeColor=#333333;"),
        ("e2", "", "capture", "hublog", "endArrow=classic;html=1;strokeWidth=2;strokeColor=#333333;"),
        ("e3", "", "hublog", "integrate", "endArrow=classic;html=1;strokeWidth=2;strokeColor=#333333;"),
        ("e4", "", "integrate", "targets", "endArrow=classic;html=1;strokeWidth=2;strokeColor=#333333;"),
    ]
    for cid, value, src, tgt, style in data_edges:
        cell(cid, value, style, edge=True, source=src, target=tgt)

    # Control edges
    cell(
        "e5",
        "",
        "endArrow=classic;html=1;strokeWidth=2;strokeColor=#34a853;",
        edge=True,
        source="operators",
        target="api",
    )
    cell(
        "e6",
        "",
        "endArrow=classic;html=1;strokeWidth=2;strokeColor=#34a853;",
        edge=True,
        source="api",
        target="repo",
    )

    # mTLS dashed edges from API to agents (cross swimlanes)
    cell(
        "e7",
        "mTLS: enrollment, assignments,&#xa;health, checkpoints",
        "endArrow=classic;html=1;strokeWidth=2;strokeColor=#6c8ebf;dashed=1;dashPattern=8 4;rounded=1;exitX=0.5;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;",
        edge=True,
        source="api",
        target="capture",
    )
    cell(
        "e8",
        "mTLS: enrollment, assignments,&#xa;health, checkpoints",
        "endArrow=classic;html=1;strokeWidth=2;strokeColor=#6c8ebf;dashed=1;dashPattern=8 4;rounded=1;exitX=0.75;exitY=0;exitDx=0;exitDy=0;entryX=0.5;entryY=1;entryDx=0;entryDy=0;",
        edge=True,
        source="api",
        target="integrate",
    )

    lines = [
        '<mxfile host="app.diagrams.net" agent="repidata-generator" version="24.0.0">',
        '  <diagram name="System Architecture" id="system-architecture-v1">',
        f'    <mxGraphModel dx="1422" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{WIDTH}" pageHeight="{HEIGHT}" math="0" shadow="0">',
        "      <root>",
        '        <mxCell id="0"/>',
        '        <mxCell id="1" parent="0"/>',
    ]
    for tag, attr_str, _, _ in cells:
        lines.append(f"        <{tag} {attr_str}/>")
    lines.extend(
        [
            "      </root>",
            "    </mxGraphModel>",
            "  </diagram>",
            "</mxfile>",
        ]
    )
    return "\n".join(lines) + "\n"


def build_svg() -> str:
    """Publication-quality SVG aligned with the draw.io layout."""
    return textwrap.dedent(
        f"""\
        <svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">
          <title id="title">Enterprise CDC Replication Platform — System Architecture (v1)</title>
          <desc id="desc">Hub-routed CDC platform with data plane (sources, capture agents, hub file log, integrate agents, targets) and control plane (operators, REST API, repository).</desc>
          <defs>
            <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
              <path d="M0,0 L0,6 L9,3 z" fill="#333"/>
            </marker>
            <marker id="arrow-green" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
              <path d="M0,0 L0,6 L9,3 z" fill="#34a853"/>
            </marker>
            <marker id="arrow-blue" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
              <path d="M0,0 L0,6 L9,3 z" fill="#6c8ebf"/>
            </marker>
            <style>
              .title {{ font: 700 22px Segoe UI, Arial, sans-serif; fill: #1a1a2e; }}
              .lane-title {{ font: 700 14px Segoe UI, Arial, sans-serif; }}
              .box {{ font: 11px Segoe UI, Arial, sans-serif; fill: #222; }}
              .cylinder {{ font: 12px Segoe UI, Arial, sans-serif; fill: #222; }}
              .callout {{ font: 10px Segoe UI, Arial, sans-serif; fill: #444; }}
              .label {{ font: 10px Segoe UI, Arial, sans-serif; fill: #555; }}
              .legend {{ font: 11px Segoe UI, Arial, sans-serif; fill: #333; }}
              .edge-label {{ font: 10px Segoe UI, Arial, sans-serif; fill: #6c8ebf; }}
            </style>
          </defs>

          <rect width="100%" height="100%" fill="#ffffff"/>

          <text x="800" y="48" text-anchor="middle" class="title">Enterprise CDC Replication Platform — System Architecture (v1)</text>

          <!-- Data plane swimlane -->
          <rect x="40" y="80" width="1520" height="430" rx="8" fill="#e8f0fe" stroke="#5c7cfa" stroke-width="2"/>
          <text x="60" y="108" class="lane-title" fill="#1a3a8a">Data plane — encrypted change files</text>

          <!-- Source DB cylinder -->
          <ellipse cx="145" cy="175" rx="85" ry="18" fill="#dae8fc" stroke="#6c8ebf" stroke-width="1.5"/>
          <rect x="60" y="175" width="170" height="90" fill="#dae8fc" stroke="#6c8ebf" stroke-width="1.5"/>
          <ellipse cx="145" cy="265" rx="85" ry="18" fill="#dae8fc" stroke="#6c8ebf" stroke-width="1.5"/>
          <text x="145" y="205" text-anchor="middle" class="cylinder">Source databases</text>
          <text x="145" y="225" text-anchor="middle" class="cylinder">Oracle · SQL Server</text>
          <text x="145" y="243" text-anchor="middle" class="cylinder">PostgreSQL · DB2</text>

          <!-- Capture agent -->
          <rect x="300" y="175" width="200" height="110" rx="10" fill="#fff2cc" stroke="#d6b656" stroke-width="1.5"/>
          <text x="400" y="200" text-anchor="middle" class="box">Capture agent (replagent)</text>
          <text x="400" y="220" text-anchor="middle" class="box">Universal Rust binary</text>
          <text x="400" y="240" text-anchor="middle" class="box">Log-layer filter · zstd</text>
          <text x="400" y="258" text-anchor="middle" class="box">AES-256-GCM</text>

          <!-- Hub file log -->
          <rect x="580" y="175" width="220" height="110" rx="10" fill="#f8cecc" stroke="#b85450" stroke-width="1.5"/>
          <text x="690" y="200" text-anchor="middle" class="box">Hub file log / relay</text>
          <text x="690" y="220" text-anchor="middle" class="box">Durable encrypted change files</text>
          <text x="690" y="240" text-anchor="middle" class="box">Sequence-ordered</text>
          <text x="690" y="258" text-anchor="middle" class="box">Ack-based GC</text>

          <!-- Integrate agent -->
          <rect x="880" y="175" width="200" height="110" rx="10" fill="#fff2cc" stroke="#d6b656" stroke-width="1.5"/>
          <text x="980" y="200" text-anchor="middle" class="box">Integrate agent (replagent)</text>
          <text x="980" y="220" text-anchor="middle" class="box">Burst or continuous apply</text>
          <text x="980" y="240" text-anchor="middle" class="box">Target-side state table</text>

          <!-- Targets cylinder -->
          <ellipse cx="1250" cy="170" rx="90" ry="18" fill="#d5e8d4" stroke="#82b366" stroke-width="1.5"/>
          <rect x="1160" y="170" width="180" height="95" fill="#d5e8d4" stroke="#82b366" stroke-width="1.5"/>
          <ellipse cx="1250" cy="265" rx="90" ry="18" fill="#d5e8d4" stroke="#82b366" stroke-width="1.5"/>
          <text x="1250" y="200" text-anchor="middle" class="cylinder">Targets</text>
          <text x="1250" y="220" text-anchor="middle" class="cylinder">Snowflake · Databricks</text>
          <text x="1250" y="240" text-anchor="middle" class="cylinder">S3 / ADLS / local</text>

          <!-- Data flow arrows -->
          <line x1="230" y1="230" x2="300" y2="230" stroke="#333" stroke-width="2.5" marker-end="url(#arrow)"/>
          <line x1="500" y1="230" x2="580" y2="230" stroke="#333" stroke-width="2.5" marker-end="url(#arrow)"/>
          <line x1="800" y1="230" x2="880" y2="230" stroke="#333" stroke-width="2.5" marker-end="url(#arrow)"/>
          <line x1="1080" y1="230" x2="1160" y2="230" stroke="#333" stroke-width="2.5" marker-end="url(#arrow)"/>
          <text x="690" y="320" text-anchor="middle" class="label">encrypted change files (protobuf + zstd + AES-256-GCM)</text>

          <!-- Callouts -->
          <rect x="60" y="350" width="250" height="70" rx="8" fill="#f5f5f5" stroke="#999" stroke-width="1" stroke-dasharray="4 4"/>
          <text x="185" y="378" text-anchor="middle" class="callout">Exactly-once: state table</text>
          <text x="185" y="396" text-anchor="middle" class="callout">co-transactional with apply</text>

          <rect x="360" y="350" width="250" height="70" rx="8" fill="#f5f5f5" stroke="#999" stroke-width="1" stroke-dasharray="4 4"/>
          <text x="485" y="378" text-anchor="middle" class="callout">Broadcast-ready: ack-based GC</text>
          <text x="485" y="396" text-anchor="middle" class="callout">supports one-to-many fan-out</text>

          <rect x="660" y="350" width="250" height="70" rx="8" fill="#f5f5f5" stroke="#999" stroke-width="1" stroke-dasharray="4 4"/>
          <text x="785" y="378" text-anchor="middle" class="callout">Agent-initiated mode:</text>
          <text x="785" y="396" text-anchor="middle" class="callout">agent dials out to hub</text>

          <rect x="960" y="350" width="250" height="70" rx="8" fill="#f5f5f5" stroke="#999" stroke-width="1" stroke-dasharray="4 4"/>
          <text x="1085" y="378" text-anchor="middle" class="callout">Repository boundary:</text>
          <text x="1085" y="396" text-anchor="middle" class="callout">change data never enters repo</text>

          <!-- Control plane swimlane -->
          <rect x="40" y="540" width="1520" height="300" rx="8" fill="#e6f4ea" stroke="#34a853" stroke-width="2"/>
          <text x="60" y="568" class="lane-title" fill="#1b5e20">Control plane — metadata and orchestration</text>

          <rect x="120" y="630" width="220" height="100" rx="10" fill="#e1d5e7" stroke="#9673a6" stroke-width="1.5"/>
          <text x="230" y="658" text-anchor="middle" class="box">Operators</text>
          <text x="230" y="678" text-anchor="middle" class="box">Web UI · CLI · automation</text>
          <text x="230" y="698" text-anchor="middle" class="box">(pure REST API clients)</text>

          <rect x="480" y="630" width="260" height="100" rx="10" fill="#ffe6cc" stroke="#d79b00" stroke-width="1.5"/>
          <text x="610" y="658" text-anchor="middle" class="box">Hub REST API + scheduler</text>
          <text x="610" y="678" text-anchor="middle" class="box">Single Rust process</text>
          <text x="610" y="698" text-anchor="middle" class="box">CDC · refresh · compare jobs</text>

          <ellipse cx="1010" cy="625" rx="110" ry="18" fill="#dae8fc" stroke="#6c8ebf" stroke-width="1.5"/>
          <rect x="900" y="625" width="220" height="95" fill="#dae8fc" stroke="#6c8ebf" stroke-width="1.5"/>
          <ellipse cx="1010" cy="720" rx="110" ry="18" fill="#dae8fc" stroke="#6c8ebf" stroke-width="1.5"/>
          <text x="1010" y="655" text-anchor="middle" class="cylinder">Repository</text>
          <text x="1010" y="675" text-anchor="middle" class="cylinder">PostgreSQL / SQLite</text>
          <text x="1010" y="695" text-anchor="middle" class="cylinder">Metadata only — no row data</text>

          <line x1="340" y1="680" x2="480" y2="680" stroke="#34a853" stroke-width="2.5" marker-end="url(#arrow-green)"/>
          <line x1="740" y1="680" x2="900" y2="680" stroke="#34a853" stroke-width="2.5" marker-end="url(#arrow-green)"/>

          <!-- mTLS dashed control lines -->
          <path d="M 610 630 C 610 560, 400 560, 400 285" fill="none" stroke="#6c8ebf" stroke-width="2" stroke-dasharray="8 4" marker-end="url(#arrow-blue)"/>
          <path d="M 650 630 C 650 560, 980 560, 980 285" fill="none" stroke="#6c8ebf" stroke-width="2" stroke-dasharray="8 4" marker-end="url(#arrow-blue)"/>
          <text x="500" y="545" text-anchor="middle" class="edge-label">mTLS: enrollment, assignments, health, checkpoints</text>

          <!-- Legend -->
          <rect x="1240" y="880" width="300" height="120" rx="8" fill="#ffffff" stroke="#666" stroke-width="1.5"/>
          <text x="1260" y="905" class="legend" font-weight="700">Legend</text>
          <line x1="1260" y1="925" x2="1295" y2="925" stroke="#333" stroke-width="3" marker-end="url(#arrow)"/>
          <text x="1305" y="930" class="legend">Solid arrow = data movement</text>
          <line x1="1260" y1="950" x2="1295" y2="950" stroke="#6c8ebf" stroke-width="2" stroke-dasharray="8 4"/>
          <text x="1305" y="955" class="legend">Dashed arrow = control / mTLS</text>
          <text x="1260" y="980" class="label">Encryption at agent (before network) and at rest on hub</text>
        </svg>
        """
    )


def export_png_from_svg() -> bool:
    """Render PNG from the SVG using resvg-js (cross-platform, no Cairo dependency)."""
    svg = str(SVG_PATH)
    png = str(PNG_PATH)
    commands: list[list[str] | str] = [
        [
            "npx",
            "--yes",
            "@resvg/resvg-js-cli",
            svg,
            png,
            "--fit-width",
            "3200",
        ],
        ["magick", "convert", "-density", "192", svg, png],
        ["inkscape", svg, "--export-type=png", f"--export-filename={png}"],
        f'npx --yes @resvg/resvg-js-cli "{svg}" "{png}" --fit-width 3200',
    ]
    for cmd in commands:
        try:
            use_shell = isinstance(cmd, str)
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                shell=use_shell,
            )
            if PNG_PATH.exists():
                return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    return False


def main() -> int:
    drawio = build_drawio()
    svg = build_svg()

    DRAWIO_PATH.write_text(drawio, encoding="utf-8")
    SVG_PATH.write_text(svg, encoding="utf-8")

    if not export_png_from_svg():
        print("Warning: PNG export failed; SVG and draw.io source were written.", file=sys.stderr)
        return 1

    print(f"Wrote {DRAWIO_PATH}")
    print(f"Wrote {SVG_PATH}")
    print(f"Wrote {PNG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
