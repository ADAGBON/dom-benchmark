<script>
  import { PRIORITIES } from './shared/bench-harness.js';

  let { task, onupdate, onremove } = $props();

  let editing = $state(false);
  let draftName = $state('');
  let draftPriority = $state('medium');

  function startEdit() {
    draftName = task.name;
    draftPriority = task.priority;
    editing = true;
  }
  function save() {
    if (draftName.trim()) onupdate(task.id, draftName.trim(), draftPriority);
    editing = false;
  }
</script>

{#if editing}
  <li class="task" data-id={task.id}>
    <select class="edit-priority" bind:value={draftPriority}>
      {#each PRIORITIES as p}<option value={p}>{p}</option>{/each}
    </select>
    <input class="edit-name" bind:value={draftName} onkeydown={(e) => e.key === 'Enter' && save()} />
    <button class="save" onclick={save}>Save</button>
    <button class="cancel" onclick={() => (editing = false)}>Cancel</button>
  </li>
{:else}
  <li class="task" data-id={task.id}>
    <span class="badge badge-{task.priority}">{task.priority}</span>
    <span class="task-name">{task.name}</span>
    <button class="edit" onclick={startEdit}>Edit</button>
    <button class="delete" onclick={() => onremove(task.id)}>Delete</button>
  </li>
{/if}
