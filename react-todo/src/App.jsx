import { memo, useCallback, useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { installBench, PRIORITIES } from './shared/bench-harness.js';

/**
 * React: component tree + useState. The list lives in one immutable array;
 * each change produces a new array and React's reconciler diffs the virtual
 * DOM. TaskRow is wrapped in React.memo and receives stable callbacks so that
 * updating 50 of 1000 tasks only re-renders those 50 rows.
 */
export default function App() {
  const [tasks, setTasks] = useState([]);
  const tasksRef = useRef(tasks);
  tasksRef.current = tasks;
  const nextId = useRef(1);

  const addTask = useCallback((name, priority) => {
    setTasks((prev) => [...prev, { id: nextId.current++, name, priority }]);
  }, []);

  const updateTask = useCallback((id, name, priority) => {
    setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, name, priority } : t)));
  }, []);

  const removeTask = useCallback((id) => {
    setTasks((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Benchmark adapter: flushSync forces React to commit to the DOM synchronously.
  useEffect(() => {
    installBench('React', {
      replaceAll(list) {
        nextId.current = list.length ? list[list.length - 1].id + 1 : 1;
        flushSync(() => setTasks(list));
      },
      updateMany(changes) {
        const byId = new Map(changes.map((c) => [c.id, c]));
        flushSync(() =>
          setTasks((prev) => prev.map((t) => {
            const c = byId.get(t.id);
            return c ? { ...t, name: c.name, priority: c.priority } : t;
          })),
        );
      },
      removeMany(ids) {
        const gone = new Set(ids);
        flushSync(() => setTasks((prev) => prev.filter((t) => !gone.has(t.id))));
      },
      getTasks: () => tasksRef.current.map((t) => ({ ...t })),
    });
  }, []);

  return (
    <main className="todo-app">
      <h1>React To-Do</h1>
      <AddTaskForm onAdd={addTask} />
      <p className="count">{tasks.length} {tasks.length === 1 ? 'task' : 'tasks'}</p>
      <ul id="task-list">
        {tasks.map((t) => (
          <TaskRow key={t.id} task={t} onUpdate={updateTask} onRemove={removeTask} />
        ))}
      </ul>
      {tasks.length === 0 && <p className="empty">No tasks yet — add one above.</p>}
    </main>
  );
}

function AddTaskForm({ onAdd }) {
  const [name, setName] = useState('');
  const [priority, setPriority] = useState('medium');
  return (
    <form
      className="add-form"
      onSubmit={(e) => {
        e.preventDefault();
        if (!name.trim()) return;
        onAdd(name.trim(), priority);
        setName('');
      }}
    >
      <input id="new-task-name" placeholder="Task name" value={name} onChange={(e) => setName(e.target.value)} />
      <select id="new-task-priority" value={priority} onChange={(e) => setPriority(e.target.value)}>
        {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
      </select>
      <button className="primary" type="submit">Add task</button>
    </form>
  );
}

const TaskRow = memo(function TaskRow({ task, onUpdate, onRemove }) {
  const [editing, setEditing] = useState(false);
  const [draftName, setDraftName] = useState(task.name);
  const [draftPriority, setDraftPriority] = useState(task.priority);

  const startEdit = () => {
    setDraftName(task.name);
    setDraftPriority(task.priority);
    setEditing(true);
  };
  const save = () => {
    if (draftName.trim()) onUpdate(task.id, draftName.trim(), draftPriority);
    setEditing(false);
  };

  if (editing) {
    return (
      <li className="task" data-id={task.id}>
        <select className="edit-priority" value={draftPriority} onChange={(e) => setDraftPriority(e.target.value)}>
          {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <input className="edit-name" value={draftName} onChange={(e) => setDraftName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && save()} />
        <button className="save" onClick={save}>Save</button>
        <button className="cancel" onClick={() => setEditing(false)}>Cancel</button>
      </li>
    );
  }

  return (
    <li className="task" data-id={task.id}>
      <span className={`badge badge-${task.priority}`}>{task.priority}</span>
      <span className="task-name">{task.name}</span>
      <button className="edit" onClick={startEdit}>Edit</button>
      <button className="delete" onClick={() => onRemove(task.id)}>Delete</button>
    </li>
  );
});
