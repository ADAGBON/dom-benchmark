import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PRIORITIES, Priority, Task } from '../shared/bench-harness';

/** One row. Attribute selector keeps the DOM as <ul><li class="task">… like the other apps. */
@Component({
  selector: 'li[app-task-row]',
  imports: [NgFor, NgIf, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'task', '[attr.data-id]': 'task.id' },
  template: `
    <ng-container *ngIf="editing; else view">
      <select class="edit-priority" [(ngModel)]="draftPriority">
        <option *ngFor="let p of priorities" [value]="p">{{ p }}</option>
      </select>
      <input class="edit-name" [(ngModel)]="draftName" (keydown.enter)="save()" />
      <button class="save" (click)="save()">Save</button>
      <button class="cancel" (click)="editing = false">Cancel</button>
    </ng-container>
    <ng-template #view>
      <span [class]="'badge badge-' + task.priority">{{ task.priority }}</span>
      <span class="task-name">{{ task.name }}</span>
      <button class="edit" (click)="startEdit()">Edit</button>
      <button class="delete" (click)="remove.emit(task.id)">Delete</button>
    </ng-template>
  `,
})
export class TaskRow {
  @Input({ required: true }) task!: Task;
  @Output() update = new EventEmitter<Task>();
  @Output() remove = new EventEmitter<number>();

  protected readonly priorities = PRIORITIES;
  protected editing = false;
  protected draftName = '';
  protected draftPriority: Priority = 'medium';

  protected startEdit() {
    this.draftName = this.task.name;
    this.draftPriority = this.task.priority;
    this.editing = true;
  }

  protected save() {
    const name = this.draftName.trim();
    if (name) this.update.emit({ id: this.task.id, name, priority: this.draftPriority });
    this.editing = false;
  }
}
