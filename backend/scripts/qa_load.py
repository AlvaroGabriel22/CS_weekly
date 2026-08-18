"""Gerador de carga do QA (Agente L) — não commitar se não for necessário.

Uso (a partir de backend/, com o venv):
    ./venv/bin/python scripts/qa_load.py --base http://localhost:8001 --scenario read --vus 10 --duration 30

Cenários:
    read    login uma vez por VU e loop de GET /activities + /weekly + /health
    write   loop de POST /activities (título curto, sem anexo)
    mix     70% leitura / 20% escrita / 10% weekly generate (com layout, sem LLM)
    upload  POST multipart de um PNG ~1MB por iteração
    download loop de GET /weekly/{id}/download (primeiro weekly do VU)

Sempre contra servidor DEDICADO de QA (porta 8001, banco qwi_qa_load.db).
Mede p50/p95/p99, taxa de erro e amostra CPU/RAM do host e do processo alvo
via /proc. Saída: JSON em stdout (uma linha por degrau).
"""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import statistics
import time

import httpx

CPU_TICK = os.sysconf("SC_CLK_TCK")


def read_cpu_total() -> float:
    with open("/proc/stat") as f:
        parts = f.readline().split()[1:]
    return sum(int(p) for p in parts)


def read_proc(pid: int) -> tuple[float, int]:
    """(cpu_ticks, rss_bytes) do processo."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            st = f.read().split()
        ticks = int(st[13]) + int(st[14])
        with open(f"/proc/{pid}/statm") as f:
            rss = int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
        return ticks, rss
    except FileNotFoundError:
        return 0.0, 0


def read_mem_available_mb() -> int:
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable"):
                return int(line.split()[1]) // 1024
    return -1


def make_png(size_kb: int = 1024) -> bytes:
    """PNG sintético de ~size_kb (payload aleatório em chunk privado)."""
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0))
    raw = zlib.compress(b"\x00" + b"\x80" * 24 * 8)
    idat = chunk(b"IDAT", raw)
    filler = chunk(b"prVt", os.urandom(size_kb * 1024))
    return b"\x89PNG\r\n\x1a\n" + ihdr + filler + idat + chunk(b"IEND", b"")


class VU:
    def __init__(self, base: str, index: int, client: httpx.AsyncClient):
        self.base = base
        self.index = index
        self.client = client
        self.token: str | None = None
        self.report_id: str | None = None

    async def ensure_user(self):
        email = f"load{self.index}@qwiload.com"
        payload = {
            "name": f"Load VU {self.index}",
            "email": email,
            "password": "senha123",
            "password_confirm": "senha123",
            "employee_id": f"LOAD{self.index:05d}",
            "role": "Analista Jr",
            "sector": "OQC",
        }
        await self.client.post(f"{self.base}/api/auth/register", json=payload)
        # register devolve o usuário (sem token) → login sempre em seguida
        r = await self.client.post(
            f"{self.base}/api/auth/login",
            json={"email": email, "password": "senha123"},
        )
        self.token = r.json()["access_token"]

    @property
    def h(self):
        return {"Authorization": f"Bearer {self.token}"}


LAYOUT = {
    "slides": [
        {"id": "s0", "kind": "cover", "elements": [
            {"id": "t", "type": "text", "x": 0.06, "y": 0.3, "w": 0.8, "h": 0.15,
             "text": "Weekly carga", "font_size": 40, "bold": True, "color": "#0C379C"},
        ]},
        {"id": "s1", "kind": "custom", "elements": [
            {"id": "b", "type": "text", "x": 0.06, "y": 0.1, "w": 0.8, "h": 0.3,
             "text": "Slide de carga", "font_size": 18, "color": "#1F2937"},
        ]},
    ]
}


async def one_request(vu: VU, scenario: str, counter: int) -> tuple[str, float, int]:
    start = time.perf_counter()
    label = scenario
    try:
        if scenario == "read":
            which = counter % 3
            if which == 0:
                r = await vu.client.get(f"{vu.base}/api/activities?page_size=50", headers=vu.h)
                label = "GET activities"
            elif which == 1:
                r = await vu.client.get(f"{vu.base}/api/weekly", headers=vu.h)
                label = "GET weekly"
            else:
                r = await vu.client.get(f"{vu.base}/api/health")
                label = "GET health"
        elif scenario == "write":
            r = await vu.client.post(
                f"{vu.base}/api/activities",
                json={"title": f"Carga {vu.index}-{counter}", "include_in_weekly": False},
                headers=vu.h,
            )
            label = "POST activity"
        elif scenario == "upload":
            png = make_png(1024)
            r = await vu.client.post(
                f"{vu.base}/api/activities",
                json={"title": f"Upload {vu.index}-{counter}", "include_in_weekly": False},
                headers=vu.h,
            )
            if r.status_code in (200, 201):
                act = r.json()["id"]
                r = await vu.client.post(
                    f"{vu.base}/api/activities/{act}/attachments",
                    files={"file": (f"img{counter}.png", io.BytesIO(png), "image/png")},
                    headers=vu.h,
                )
            label = "upload 1MB"
        elif scenario == "generate":
            r = await vu.client.post(
                f"{vu.base}/api/activities",
                json={"title": f"Gen {vu.index}-{counter}", "include_in_weekly": True},
                headers=vu.h,
            )
            act = r.json()["id"]
            r = await vu.client.post(
                f"{vu.base}/api/weekly/generate",
                json={"activity_ids": [act], "week_number": 30, "year": 2026,
                      "layout": LAYOUT, "layout_source": "manual"},
                headers=vu.h, timeout=120,
            )
            if r.status_code == 200:
                vu.report_id = r.json()["id"]
            label = "weekly generate"
        elif scenario == "download":
            if not vu.report_id:
                return await one_request(vu, "generate", counter)
            r = await vu.client.get(
                f"{vu.base}/api/weekly/{vu.report_id}/download", headers=vu.h
            )
            label = "download pptx"
        elif scenario == "mix":
            m = counter % 10
            if m < 7:
                return await one_request(vu, "read", counter)
            if m < 9:
                return await one_request(vu, "write", counter)
            return await one_request(vu, "generate", counter)
        else:
            raise ValueError(scenario)
        return label, time.perf_counter() - start, r.status_code
    except Exception:
        return label, time.perf_counter() - start, 0  # 0 = erro de transporte/timeout


async def vu_loop(vu: VU, scenario: str, stop: float, out: list):
    counter = 0
    while time.perf_counter() < stop:
        result = await one_request(vu, scenario, counter)
        out.append(result)
        counter += 1


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8001")
    ap.add_argument("--scenario", default="read")
    ap.add_argument("--vus", type=int, default=1)
    ap.add_argument("--duration", type=int, default=30)
    ap.add_argument("--server-pid", type=int, default=0)
    args = ap.parse_args()

    limits = httpx.Limits(max_connections=args.vus + 5)
    async with httpx.AsyncClient(timeout=60, limits=limits) as client:
        vus = [VU(args.base, i, client) for i in range(args.vus)]
        await asyncio.gather(*(v.ensure_user() for v in vus))

        cpu0 = read_cpu_total()
        proc0, _ = read_proc(args.server_pid) if args.server_pid else (0, 0)
        t0 = time.perf_counter()
        out: list = []
        stop = t0 + args.duration
        await asyncio.gather(*(vu_loop(v, args.scenario, stop, out) for v in vus))
        elapsed = time.perf_counter() - t0
        cpu1 = read_cpu_total()
        proc1, rss = read_proc(args.server_pid) if args.server_pid else (0, 0)

    lat = sorted(t for _, t, _ in out)
    errors = [s for _, _, s in out if s == 0 or s >= 500]
    codes: dict[int, int] = {}
    for _, _, s in out:
        codes[s] = codes.get(s, 0) + 1

    def pct(p):
        return round(lat[min(len(lat) - 1, int(len(lat) * p))] * 1000) if lat else None

    print(json.dumps({
        "scenario": args.scenario, "vus": args.vus, "duration_s": round(elapsed, 1),
        "requests": len(out), "rps": round(len(out) / elapsed, 1),
        "p50_ms": pct(0.50), "p95_ms": pct(0.95), "p99_ms": pct(0.99),
        "max_ms": round(lat[-1] * 1000) if lat else None,
        "error_rate": round(len(errors) / max(len(out), 1), 4),
        "status_codes": codes,
        "host_cpu_pct": round((cpu1 - cpu0) / CPU_TICK / elapsed / os.cpu_count() * 100, 1),
        "server_cpu_pct": round((proc1 - proc0) / CPU_TICK / elapsed * 100, 1)
        if args.server_pid else None,
        "server_rss_mb": rss // (1024 * 1024) if args.server_pid else None,
        "mem_available_mb": read_mem_available_mb(),
    }, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
