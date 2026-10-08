import { AfterViewInit, ApplicationRef, ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { installBench, PRIORITIES, Priority, Task } from '../shared/bench-harness';
import { TaskRow } from './task-row';

/**
 * Angular: structural directives (*ngFor with trackBy, *ngIf) render the
 * list, [(ngModel)] gives two-way binding on the form, and the list is held
 * in a signal. Rows use OnPush, so a change-detection pass only re-checks rows
 * whose `task` input reference changed. The benchmark adapter calls
 * ApplicationRef.tick() to run change detection synchronously.
 */
@Component({
  selector: 'app-root',
  imports: [NgFor, NgIf, FormsModule, TaskRow],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="todo-app">
      <h1>Angular To-Do</h1>
      <form class="add-form" (ngSubmit)="addTask()">
        <input id="new-task-name" name="name" [(ngModel)]="newName" placeholder="Task name" />
        <select id="new-task-priority" name="priority" [(ngModel)]="newPriority">
          <option *ngFor="let p of priorities" [value]="p">{{ p }}</option>
        </select>
        <button class="primary" type="submit">Add task</button>
      </form>
      <p class="count">{{ tasks().length }} {{ tasks().length === 1 ? 'task' : 'tasks' }}</p>
      <ul id="task-list">
        <li app-task-row *ngFor="let t of tasks(); trackBy: trackById"
            [task]="t" (update)="updateTask($event)" (remove)="removeTask($event)"></li>
      </ul>
      <p *ngIf="tasks().length === 0" class="empty">No tasks yet — add one above.</p>
    </main>
  `,
})
export class App implements AfterViewInit {
  private readonly appRef = inject(ApplicationRef);
  protected readonly priorities = PRIORITIES;
  protected readonly tasks = signal<Task[]>([]);
  protected newName = '';
  protected newPriority: Priority = 'medium';
  private nextId = 1;

  protected trackById = (_: number, t: Task) => t.id;

  protected addTask() {
    const name = this.newName.trim();
    if (!name) return;
    this.tasks.update((list) => [...list, { id: this.nextId++, name, priority: this.newPriority }]);
    this.newName = '';
  }

  protected updateTask(c: Task) {
    this.tasks.update((list) => list.map((t) => (t.id === c.id ? { ...t, name: c.name, priority: c.priority } : t)));
  }

  protected removeTask(id: number) {
    this.tasks.update((list) => list.filter((t) => t.id !== id));
  }

  ngAfterViewInit() {
    installBench('Angular', {
      replaceAll: (list) => {
        this.nextId = list.length ? list[list.length - 1].id + 1 : 1;
        this.tasks.set(list);
        this.appRef.tick();
      },
      updateMany: (changes) => {
        const byId = new Map(changes.map((c) => [c.id, c]));
        this.tasks.update((list) => list.map((t) => {
          const c = byId.get(t.id);
          return c ? { ...t, name: c.name, priority: c.priority } : t;
        }));
        this.appRef.tick();
      },
      removeMany: (ids) => {
        const gone = new Set(ids);
        this.tasks.update((list) => list.filter((t) => !gone.has(t.id)));
        this.appRef.tick();
      },
      getTasks: () => this.tasks().map((t) => ({ ...t })),
    });
  }
}
