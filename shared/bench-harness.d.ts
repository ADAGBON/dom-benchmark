// Type declarations for bench-harness.js (used by the Angular/TypeScript app).
export type Priority = 'low' | 'medium' | 'high';
export interface Task { id: number; name: string; priority: Priority; }
export interface TaskChange { id: number; name: string; priority: Priority; }

export interface BenchAdapter {
  replaceAll(tasks: Task[]): void | Promise<void>;
  updateMany(changes: TaskChange[]): void | Promise<void>;
  removeMany(ids: number[]): void | Promise<void>;
  getTasks(): Task[];
}

export const PRIORITIES: Priority[];
export function makeTasks(n: number, startId?: number, seed?: number): Task[];
export function installBench(framework: string, adapter: BenchAdapter): unknown;
