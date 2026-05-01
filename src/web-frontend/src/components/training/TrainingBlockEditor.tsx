import { useState } from 'react';
import type {
  CreateTrainingBlockPayload,
  TrainingBlock,
  TrainingBlockType,
} from '../../types/training';
import styles from './css/TrainingComponents.module.css';

interface Props {
  blocks: TrainingBlock[];
  disabled?: boolean;
  onCreate: (payload: CreateTrainingBlockPayload) => Promise<void>;
  onDelete: (blockId: number) => Promise<void>;
}

const blockTypes: { value: TrainingBlockType; label: string }[] = [
  { value: 'warm_up', label: 'Warm-up' },
  { value: 'technical', label: 'Technical' },
  { value: 'tactical', label: 'Tactical' },
  { value: 'conditioned_game', label: 'Conditioned game' },
  { value: 'set_pieces', label: 'Set pieces' },
  { value: 'fitness', label: 'Fitness' },
  { value: 'recovery', label: 'Recovery' },
  { value: 'cool_down', label: 'Cool-down' },
  { value: 'review', label: 'Review' },
  { value: 'other', label: 'Other' },
];

const initialForm = (order: number): CreateTrainingBlockPayload => ({
  order,
  title: '',
  block_type: 'tactical',
  duration_minutes: 15,
  description: '',
  coaching_points: '',
  equipment: '',
  player_group: '',
});

export const TrainingBlockEditor = ({ blocks, disabled = false, onCreate, onDelete }: Props) => {
  const [form, setForm] = useState<CreateTrainingBlockPayload>(() => initialForm(blocks.length + 1));
  const [saving, setSaving] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      await onCreate({ ...form, title: form.title.trim() });
      setForm(initialForm(blocks.length + 2));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.blockList}>
      {blocks.map((block) => (
        <div key={block.id} className={styles.blockRow}>
          <div className={styles.blockHeader}>
            <div>
              <div className={styles.blockTitle}>{block.order}. {block.title}</div>
              <div className={styles.blockMeta}>{block.block_type.replaceAll('_', ' ')} · {block.duration_minutes} min</div>
            </div>
            {!disabled && (
              <button type="button" className={styles.dangerBtn} onClick={() => onDelete(block.id)}>
                Delete
              </button>
            )}
          </div>
          {block.description && <p className={styles.blockText}>{block.description}</p>}
          {block.coaching_points && <p className={styles.blockText}>{block.coaching_points}</p>}
        </div>
      ))}

      {!disabled && (
        <form className={styles.inlineForm} onSubmit={submit}>
          <input
            className={styles.input}
            type="number"
            min={1}
            value={form.order}
            onChange={(e) => setForm((prev) => ({ ...prev, order: Number(e.target.value) }))}
            aria-label="Block order"
          />
          <input
            className={styles.input}
            value={form.title}
            onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
            placeholder="Block title"
          />
          <select
            className={styles.select}
            value={form.block_type}
            onChange={(e) => setForm((prev) => ({ ...prev, block_type: e.target.value as TrainingBlockType }))}
          >
            {blockTypes.map((type) => <option key={type.value} value={type.value}>{type.label}</option>)}
          </select>
          <input
            className={styles.input}
            type="number"
            min={1}
            value={form.duration_minutes}
            onChange={(e) => setForm((prev) => ({ ...prev, duration_minutes: Number(e.target.value) }))}
            aria-label="Duration minutes"
          />
          <textarea
            className={`${styles.textarea} ${styles.inlineFormWide}`}
            value={form.description}
            onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
            placeholder="Instructions"
          />
          <textarea
            className={`${styles.textarea} ${styles.inlineFormWide}`}
            value={form.coaching_points}
            onChange={(e) => setForm((prev) => ({ ...prev, coaching_points: e.target.value }))}
            placeholder="Coaching points"
          />
          <div className={styles.blockActions}>
            <button type="submit" className={styles.primaryBtn} disabled={saving || !form.title.trim()}>
              Add block
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

export default TrainingBlockEditor;
