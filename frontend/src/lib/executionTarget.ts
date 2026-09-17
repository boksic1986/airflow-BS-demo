/** Display the registered target, never the browser/API host. */
export function executionTargetLabel(mode?: string | null, target?: unknown): string {
  if (mode === 'sge' || target === 'sge-default') return 'SGE';
  if (target === 'node-96') return 'node96';
  if (target === 'node-97') return 'node97';
  return 'Local';
}
