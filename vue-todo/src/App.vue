<script setup>
/**
 * Vue 3: the list is a deep-reactive ref. Vue's proxies track which
 * component read which property, so mutating `task.name` re-renders only the
 * TaskRow that owns that task. DOM patches are batched and flushed on the
 * next microtask — the benchmark adapter awaits nextTick() for that flush.
 */
import { nextTick, onMounted, ref } from 'vue';
import { installBench, PRIORITIES } from './shared/bench-harness.js';
import TaskRow from './TaskRow.vue';

const tasks = ref([]);
const newName = ref('');
const newPriority = ref('medium');
let nextId = 1;

function addTask() {
  const name = newName.value.trim();
  if (!name) return;
  tasks.value.push({ id: nextId++, name, priority: newPriority.value });
  newName.value = '';
}

function updateTask(id, name, priority) {
  const t = tasks.value.find((x) => x.id === id);
  if (t) { t.name = name; t.priority = priority; }
}

function removeTask(id) {
  const i = tasks.value.findIndex((x) => x.id === id);
  if (i !== -1) tasks.value.splice(i, 1);
}

onMounted(() => {
  installBench('Vue', {
    async replaceAll(list) {
      nextId = list.length ? list[list.length - 1].id + 1 : 1;
      tasks.value = list;
      await nextTick();
    },
    async updateMany(changes) {
      const byId = new Map(changes.map((c) => [c.id, c]));
      for (const t of tasks.value) {
        const c = byId.get(t.id);
        if (c) { t.name = c.name; t.priority = c.priority; }
      }
      await nextTick();
    },
    async removeMany(ids) {
      const gone = new Set(ids);
      tasks.value = tasks.value.filter((t) => !gone.has(t.id));
      await nextTick();
    },
    getTasks: () => tasks.value.map((t) => ({ id: t.id, name: t.name, priority: t.priority })),
  });
});
</script>

<template>
  <main class="todo-app">
    <h1>Vue To-Do</h1>
    <form class="add-form" @submit.prevent="addTask">
      <input id="new-task-name" v-model="newName" placeholder="Task name" />
      <select id="new-task-priority" v-model="newPriority">
        <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
      </select>
      <button class="primary" type="submit">Add task</button>
    </form>
    <p class="count">{{ tasks.length }} {{ tasks.length === 1 ? 'task' : 'tasks' }}</p>
    <ul id="task-list">
      <TaskRow v-for="t in tasks" :key="t.id" :task="t" @update="updateTask" @remove="removeTask" />
    </ul>
    <p v-if="tasks.length === 0" class="empty">No tasks yet — add one above.</p>
  </main>
</template>
