"""Benchmark runner: headless Chromium (Playwright) + Chrome DevTools Protocol.

By default every sample uses a *fresh* browser context that loads the app's production build,
so each measurement is a cold, first-time operation (no JIT warm-up from
earlier runs). Frameworks are interleaved in random order on each iteration to
spread any machine noise evenly.

Scenarios
  render-100 / render-500 / render-1000 : empty list -> N tasks
  update-50  : 1000 tasks rendered, then 50 tasks (spread across the list) get a new name + priority
  delete-50  : 1000 tasks rendered, then 50 tasks (spread across the list) are removed in one action

Memory (CDP): JS heap after forced GC — on an empty app, and with 1000 tasks rendered.
DOM node count and gzipped bundle size are recorded too.

Usage:
  python3 bench/run_benchmarks.py                 # 1x CPU, 25 samples per cell
  python3 bench/run_benchmarks.py --cpu 4 -n 10   # 4x CPU throttling (mid-range phone)
  python3 bench/run_benchmarks.py --warm 5        # steady state: 5 warm-up rounds before measuring
  python3 bench/run_benchmarks.py --traces        # also save DevTools traces of render-1000
"""
import argparse
import gzip
import json
import platform
import random
import statistics as st
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from common import APPS, ROOT, open_app, serve_all

SCENARIOS = ["render-100", "render-500", "render-1000", "update-50", "delete-50"]
RESULTS = ROOT / "results"


def warm_up(page, scenario, rounds):
    """Exercise the same code path a few times so V8 has optimised it (steady-state)."""
    for _ in range(rounds):
        if scenario.startswith("render-"):
            page.evaluate(f"__bench.render({scenario.split('-')[1]})")
        else:
            page.evaluate("__bench.seed(1000)")
            page.evaluate("__bench.update(50)" if scenario == "update-50" else "__bench.remove(50)")
    page.evaluate("__bench.clear()")


def run_scenario(page, scenario):
    if scenario.startswith("render-"):
        n = int(scenario.split("-")[1])
        return page.evaluate(f"__bench.render({n})")
    page.evaluate("__bench.seed(1000)")
    if scenario == "update-50":
        return page.evaluate("__bench.update(50)")
    return page.evaluate("__bench.remove(50)")


def heap_metrics(cdp):
    cdp.send("HeapProfiler.collectGarbage")
    cdp.send("HeapProfiler.collectGarbage")
    m = {x["name"]: x["value"] for x in cdp.send("Performance.getMetrics")["metrics"]}
    return {"heapMB": m["JSHeapUsedSize"] / 1024 / 1024, "domNodes": int(m["Nodes"])}


def new_page(browser, cpu):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    cdp = ctx.new_cdp_session(page)
    cdp.send("Performance.enable")
    if cpu > 1:
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": cpu})
    return ctx, page, cdp


def summarize(samples):
    return {
        "median": st.median(samples),
        "mean": st.fmean(samples),
        "stdev": st.stdev(samples) if len(samples) > 1 else 0.0,
        "min": min(samples),
        "max": max(samples),
        "n": len(samples),
    }


def bundle_sizes():
    out = {}
    for fw, dist in APPS.items():
        js = [p for p in dist.rglob("*.js")]
        raw = sum(p.stat().st_size for p in js)
        gz = sum(len(gzip.compress(p.read_bytes(), 9)) for p in js)
        out[fw] = {"jsKB": raw / 1024, "jsGzipKB": gz / 1024}
    return out


def framework_versions():
    def ver(pkg_json):
        return json.loads(Path(pkg_json).read_text())["version"]
    nm = lambda app, pkg: ROOT / app / "node_modules" / pkg / "package.json"
    return {
        "React": ver(nm("react-todo", "react")),
        "Angular": ver(nm("angular-todo", "@angular/core")),
        "Vue": ver(nm("vue-todo", "vue")),
        "Svelte": ver(nm("svelte-todo", "svelte")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--samples", type=int, default=25)
    ap.add_argument("--cpu", type=int, default=1, help="CPU throttling rate (1 = none)")
    ap.add_argument("--memory-samples", type=int, default=5)
    ap.add_argument("--traces", action="store_true")
    ap.add_argument("--warm", type=int, default=0, help="warm-up rounds on the same page before measuring (0 = cold)")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    random.seed(args.seed)

    urls = serve_all()
    fws = list(urls)
    raw = {fw: {s: [] for s in SCENARIOS} for fw in fws}
    mem = {fw: {"empty": [], "tasks1000": []} for fw in fws}

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--js-flags=--expose-gc"])
        chrome_version = browser.version

        total = args.samples * len(SCENARIOS) * len(fws)
        done = 0
        for i in range(args.samples):
            for scenario in SCENARIOS:
                order = fws[:]
                random.shuffle(order)
                for fw in order:
                    ctx, page, _ = new_page(browser, args.cpu)
                    open_app(page, urls[fw])
                    if args.warm:
                        warm_up(page, scenario, args.warm)
                    r = run_scenario(page, scenario)
                    raw[fw][scenario].append(r)
                    ctx.close()
                    done += 1
            print(f"  iteration {i + 1}/{args.samples} ({done}/{total} samples)", flush=True)

        for _ in range(args.memory_samples):
            for fw in fws:
                ctx, page, cdp = new_page(browser, 1)
                open_app(page, urls[fw])
                mem[fw]["empty"].append(heap_metrics(cdp))
                page.evaluate("__bench.seed(1000)")
                mem[fw]["tasks1000"].append(heap_metrics(cdp))
                ctx.close()

        if args.traces:
            tdir = RESULTS / "traces"
            tdir.mkdir(parents=True, exist_ok=True)
            for fw in fws:
                ctx, page, _ = new_page(browser, args.cpu)
                open_app(page, urls[fw])
                browser.start_tracing(page=page, path=str(tdir / f"{fw.lower()}-render-1000.json"))
                page.evaluate("__bench.render(1000)")
                browser.stop_tracing()
                ctx.close()
        browser.close()

    summary = {}
    for fw in fws:
        summary[fw] = {}
        for s in SCENARIOS:
            summary[fw][s] = {
                metric: summarize([r[metric] for r in raw[fw][s]])
                for metric in ("script", "scriptLayout", "paint")
            }
        summary[fw]["memory"] = {
            "emptyHeapMB": st.median(m["heapMB"] for m in mem[fw]["empty"]),
            "heap1000MB": st.median(m["heapMB"] for m in mem[fw]["tasks1000"]),
            "domNodes1000": st.median(m["domNodes"] for m in mem[fw]["tasks1000"]),
        }
        summary[fw]["memory"]["deltaMB"] = summary[fw]["memory"]["heap1000MB"] - summary[fw]["memory"]["emptyHeapMB"]

    out = {
        "meta": {
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "browser": f"Chromium {chrome_version} (headless, Playwright)",
            "platform": f"{platform.system()} {platform.machine()}",
            "cpuThrottling": args.cpu,
            "mode": f"warm ({args.warm} warm-up rounds)" if args.warm else "cold (fresh page per sample)",
            "samplesPerCell": args.samples,
            "frameworks": framework_versions(),
        },
        "bundles": bundle_sizes(),
        "summary": summary,
        "raw": raw,
    }
    RESULTS.mkdir(exist_ok=True)
    mode = f"warm" if args.warm else "cold"
    path = RESULTS / f"results-{mode}-cpu{args.cpu}x.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
