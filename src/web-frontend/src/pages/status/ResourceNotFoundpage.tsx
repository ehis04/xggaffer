import { useNavigate } from "react-router-dom";
import { StatusBlock } from "../../common/components/StatusBlock";
import styles from "./css/ResourceNotFoundPage.module.css";

const DEFAULT_BACK_PATH = "/";
const DEFAULT_BACK_LABEL = "Go Back";

interface ResourceNotFoundPageProps {
  backPath?: string;
  backLabel?: string;
}

export function ResourceNotFoundPage({
  backPath = DEFAULT_BACK_PATH,
  backLabel = DEFAULT_BACK_LABEL,
}: ResourceNotFoundPageProps) {
  const navigate = useNavigate();

  const actions = (
    <button type="button" className={styles.backButton} onClick={() => navigate(backPath)}>
      {backLabel}
    </button>
  );

  return (
    <div className={styles.page}>
      <StatusBlock variant="not-found" actions={actions} />
    </div>
  );
}