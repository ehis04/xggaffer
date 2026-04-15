import ChatInterface from '../../components/predictions/chat/ChatInterface';
import styles from './css/PredictionPage.module.css';

export default function PredictionPage() {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>xgGaffer</h1>
        <p className={styles.subtitle}>
          Ask anything about match predictions, team strength, tactics, lineups,
          and player availability across Europe's top 5 leagues.
        </p>
      </header>
      <div className={styles.chatContainer}>
        <ChatInterface />
      </div>
    </div>
  );
}