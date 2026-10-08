<script setup>
import { ref } from 'vue';
import { PRIORITIES } from './shared/bench-harness.js';

const props = defineProps({ task: { type: Object, required: true } });
const emit = defineEmits(['update', 'remove']);

const editing = ref(false);
const draftName = ref('');
const draftPriority = ref('medium');

function startEdit() {
  draftName.value = props.task.name;
  draftPriority.value = props.task.priority;
  editing.value = true;
}
function save() {
  if (draftName.value.trim()) emit('update', props.task.id, draftName.value.trim(), draftPriority.value);
  editing.value = false;
}
</script>

<template>
  <li v-if="editing" class="task" :data-id="task.id">
    <select class="edit-priority" v-model="draftPriority">
      <option v-for="p in PRIORITIES" :key="p" :value="p">{{ p }}</option>
    </select>
    <input class="edit-name" v-model="draftName" @keydown.enter="save" />
    <button class="save" @click="save">Save</button>
    <button class="cancel" @click="editing = false">Cancel</button>
  </li>
  <li v-else class="task" :data-id="task.id">
    <span :class="['badge', `badge-${task.priority}`]">{{ task.priority }}</span>
    <span class="task-name">{{ task.name }}</span>
    <button class="edit" @click="startEdit">Edit</button>
    <button class="delete" @click="emit('remove', task.id)">Delete</button>
  </li>
</template>
