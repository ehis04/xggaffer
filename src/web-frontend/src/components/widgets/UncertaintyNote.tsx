import styles from './css/UncertaintyNote.module.css';

interface UncertaintyNoteProps {
  message: string;
}

export default function UncertaintyNote({ message }: UncertaintyNoteProps) {
  return <p className={styles.note}>{message}</p>;
}