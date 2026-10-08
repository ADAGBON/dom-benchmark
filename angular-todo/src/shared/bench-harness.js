/**
 * Framework-agnostic benchmark harness.
 *
 * The SAME file is copied into every app (run `node scripts/sync-shared.mjs`),
 * so React, Angular, Vue and Svelte are measured by identical code.
 *
 * Each app registers an adapter that drives its *own* state-management code:
 *
 *   installBench('React', {
 *     replaceAll(tasks)   // replace the whole list            (render N)
 *     updateMany(changes) // [{ id, name, priority }]          (update K)
 *     removeMany(ids)     // remove the given ids              (delete K)
 *     getTasks()          // plain snapshot [{ id, name, priority }]
 *   })
 *
 * Every adapter method must have committed its DOM changes by the time it
 * returns (or by the time its returned promise resolves): React uses
 * flushSync, Vue awaits nextTick, Svelte calls flushSync, Angular calls
 * ApplicationRef.tick(). That lets us time "state change -> DOM committed".
 *
 * Three timings are taken per operation:
 *   script : state change -> DOM mutated (framework JS + DOM API calls)
 *   layout : forced synchronous style + layout of the new DOM
 *   paint  : state change -> after the next animation frame (includes paint
 *            and frame-alignment jitter, so it is reported as secondary)
 */

export const PRIORITIES = ['low', 'medium', 'high'];

const ADJECTIVES = ['quick', 'urgent', 'small', 'weekly', 'quarterly', 'tricky', 'pending', 'shared', 'optional', 'critical'];
const VERBS = ['review', 'draft', 'deploy', 'refactor', 'test', 'document', 'reconcile', 'plan', 'email', 'benchmark'];
const NOUNS = ['report', 'invoice', 'release', 'dashboard', 'budget', 'API', 'slides', 'backlog', 'contract', 'dataset'];

// Deterministic PRNG (mulberry32) so every framework renders identical data.
function rng(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function makeTasks(n, startId = 1, seed = 42) {
  const r = rng(seed);
  const pick = (arr) => arr[Math.floor(r() * arr.length)];
  const tasks = new Array(n);
  for (let i = 0; i < n; i++) {
    tasks[i] = {
      id: startId + i,
      name: `${pick(VERBS)} ${pick(ADJECTIVES)} ${pick(NOUNS)} #${startId + i}`,
      priority: pick(PRIORITIES),
    };
  }
  return tasks;
}

/** Evenly spread `count` indices across a list of length `len`. */
function spreadIndices(len, count) {
  const step = Math.max(1, Math.floor(len / count));
  const out = [];
  for (let i = 0; i < len && out.length < count; i += step) out.push(i);
  return out;
}

const nextFrame = () => new Promise((r) => requestAnimationFrame(() => setTimeout(r, 0)));
const rows = () => document.querySelectorAll('#task-list > li.task');

async function measure(op) {
  await nextFrame(); // start from an idle, painted state
  const t0 = performance.now();
  await op();
  const t1 = performance.now();
  void document.body.offsetHeight; // force style recalc + layout
  const t2 = performance.now();
  await nextFrame();
  const t3 = performance.now();
  return { script: t1 - t0, layout: t2 - t1, scriptLayout: t2 - t0, paint: t3 - t0 };
}

function assert(cond, msg) {
  if (!cond) throw new Error(`[bench] verification failed: ${msg}`);
}

export function installBench(framework, adapter) {
  const bench = {
    framework,

    async clear() {
      await adapter.replaceAll([]);
      await nextFrame();
      assert(rows().length === 0, 'list should be empty after clear');
    },

    /** Prepare a list without timing it (used before update/delete runs). */
    async seed(n) {
      await adapter.replaceAll(makeTasks(n));
      await nextFrame();
      assert(rows().length === n, `expected ${n} rows after seed, got ${rows().length}`);
    },

    /** Initial rendering: empty list -> n tasks. */
    async render(n) {
      await bench.clear();
      const tasks = makeTasks(n);
      const t = await measure(() => adapter.replaceAll(tasks));
      assert(rows().length === n, `expected ${n} rows, got ${rows().length}`);
      assert(rows()[n - 1].querySelector('.task-name').textContent === tasks[n - 1].name, 'last row text mismatch');
      return { op: `render-${n}`, ...t };
    },

    /** Update `count` tasks spread across the current list (name + priority). */
    async update(count = 50) {
      const current = adapter.getTasks();
      const idx = spreadIndices(current.length, count);
      const changes = idx.map((i) => {
        const t = current[i];
        const p = PRIORITIES[(PRIORITIES.indexOf(t.priority) + 1) % PRIORITIES.length];
        return { id: t.id, name: `${t.name} (edited)`, priority: p };
      });
      const t = await measure(() => adapter.updateMany(changes));
      const r = rows();
      for (let k = 0; k < idx.length; k++) {
        const row = r[idx[k]];
        assert(row.querySelector('.task-name').textContent === changes[k].name, `row ${idx[k]} name not updated`);
        assert(row.querySelector('.badge').textContent.trim() === changes[k].priority, `row ${idx[k]} priority not updated`);
      }
      return { op: `update-${changes.length}`, ...t };
    },

    /** Delete `count` tasks spread across the current list. */
    async remove(count = 50) {
      const current = adapter.getTasks();
      const ids = spreadIndices(current.length, count).map((i) => current[i].id);
      const t = await measure(() => adapter.removeMany(ids));
      assert(rows().length === current.length - ids.length, `expected ${current.length - ids.length} rows after delete, got ${rows().length}`);
      const remaining = new Set([...rows()].map((li) => Number(li.dataset.id)));
      assert(ids.every((id) => !remaining.has(id)), 'a deleted id is still in the DOM');
      return { op: `delete-${ids.length}`, ...t };
    },

    rowCount: () => rows().length,
  };

  window.__bench = bench;
  mountPanel(bench);
  return bench;
}

/** Small vanilla-DOM toolbar (outside the framework root) for manual runs. */
function mountPanel(bench) {
  const host = document.getElementById('bench-panel');
  if (!host) return;
  host.innerHTML = `
    <strong>${bench.framework} · benchmark</strong>
    <button data-op="render" data-n="100">Render 100</button>
    <button data-op="render" data-n="500">Render 500</button>
    <button data-op="render" data-n="1000">Render 1000</button>
    <button data-op="update">Update 50</button>
    <button data-op="remove">Delete 50</button>
    <button data-op="clear">Clear</button>
    <output id="bench-output">Results appear here (also logged to the console).</output>`;
  const out = host.querySelector('#bench-output');
  host.addEventListener('click', async (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    try {
      const op = b.dataset.op;
      const res = op === 'render' ? await bench.render(Number(b.dataset.n))
        : op === 'update' ? await bench.update(50)
        : op === 'remove' ? await bench.remove(50)
        : (await bench.clear(), null);
      if (!res) { out.textContent = 'Cleared.'; return; }
      out.textContent = `${res.op}: script ${res.script.toFixed(2)} ms · script+layout ${res.scriptLayout.toFixed(2)} ms · to next frame ${res.paint.toFixed(2)} ms`;
      console.table([res]);
    } catch (err) {
      out.textContent = String(err.message || err);
    }
  });
}
