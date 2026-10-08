<script>
  /**
   * Svelte 5: the compiler turns this template into direct DOM instructions
   * plus fine-grained signal subscriptions ($state runes). There is no
   * virtual DOM — changing `task.name` updates exactly one text node.
   * The benchmark adapter calls flushSync() to apply pending effects at once.
   */
  import { flushSync, onMount } from 'svelte';
  import { installBench, PRIORITIES } from './shared/bench-harness.js';
  import TaskRow from './TaskRow.svelte';

  let tasks = $state([]);
  let newName = $state('');
  let newPriority = $state('medium');
  let nextId = 1;

  function addTask(e) {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    tasks.push({ id: nextId++, name, priority: newPriority });
    newName = '';
  }

  function updateTask(id, name, priority) {
    const t = tasks.find((x) => x.id === id);
    if (t) { t.name = name; t.priority = priority; }
  }

  function removeTask(id) {
    const i = tasks.findIndex((x) => x.id === id);
    if (i !== -1) tasks.splice(i, 1);
  }

  onMount(() => {
    installBench('Svelte', {
      replaceAll(list) {
        nextId = list.length ? list[list.length - 1].id + 1 : 1;
        tasks = list;
        flushSync();
      },
      updateMany(changes) {
        const byId = new Map(changes.map((c) => [c.id, c]));
        for (const t of tasks) {
          const c = byId.get(t.id);
          if (c) { t.name = c.name; t.priority = c.priority; }
        }
        flushSync();
      },
      removeMany(ids) {
        const gone = new Set(ids);
        tasks = tasks.filter((t) => !gone.has(t.id));
        flushSync();
      },
      getTasks: () => tasks.map((t) => ({ id: t.id, name: t.name, priority: t.priority })),
    });
  });
</script>

<main class="todo-app">
  <h1>Svelte To-Do</h1>
  <form class="add-form" onsubmit={addTask}>
    <input id="new-task-name" bind:value={newName} placeholder="Task name" />
    <select id="new-task-priority" bind:value={newPriority}>
      {#each PRIORITIES as p}<option value={p}>{p}</option>{/each}
    </select>
    <button class="primary" type="submit">Add task</button>
  </form>
  <p class="count">{tasks.length} {tasks.length === 1 ? 'task' : 'tasks'}</p>
  <ul id="task-list">
    {#each tasks as task (task.id)}
      <TaskRow {task} onupdate={updateTask} onremove={removeTask} />
    {/each}
  </ul>
  {#if tasks.length === 0}<p class="empty">No tasks yet — add one above.</p>{/if}
</main>
