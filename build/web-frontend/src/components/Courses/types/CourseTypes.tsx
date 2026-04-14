export type ItemType = 'clause' | 'quiz' | 'scenario' | 'drill';
export type ItemStatus = 'completed' | 'active' | 'locked';

export interface ClauseData {
  n: number;
  txt: string;
}

export interface ScenarioOption {
  id: string;
  t: string;
}

export interface ScenarioData {
  sit: string;
  opts: ScenarioOption[];
  cor: string;
  expl: string;
}

export interface DrillItem {
  s: string;
  a: 'true' | 'false';
}

export interface DrillData {
  desc: string;
  items: DrillItem[];
}

export interface CourseItem {
  id: string;
  type: ItemType;
  title: string;
  status: ItemStatus;
  mins: number;
  clause?: ClauseData;
  scenario?: ScenarioData;
  drill?: DrillData;
  /** Quiz item fields — populated when type === 'quiz' */
  qc?: number;
  qid?: string;
}

export interface CourseSection {
  id: string;
  title: string;
  items: CourseItem[];
}

export interface CoursePageProps {
  lawNumber: number;
  lawTitle: string;
  sections: CourseSection[];
  initialItemId?: string;
}

export interface CourseResultsProps {
  sections: CourseSection[];
  completedIds: Set<string>;
  onNavigate: (id: string) => void;
}

export interface DrillAnswers {
  [index: number]: 'true' | 'false';
}

export interface DrillContentProps {
  item: CourseItem;
  answers: DrillAnswers;
  submitted: boolean;
  onAnswer: (index: number, value: 'true' | 'false') => void;
  onSubmit: () => void;
  onReset?: () => void;
}

export interface ScenarioContentProps {
  item: CourseItem;
  selectedOption: string | undefined;
  revealed: boolean;
  onSelect: (optionId: string) => void;
  onCheck: () => void;
  onReset?: () => void;
}

export interface ClauseContentProps {
  item: CourseItem;
  isRead: boolean;
}

export interface QuizContentProps {
  item: CourseItem;
}

export interface CourseContentProps {
  item: CourseItem;
  completedIds: Set<string>;
  scenarioSelections: Record<string, string>;
  scenarioRevealed: Set<string>;
  onScenarioSelect: (itemId: string, optId: string) => void;
  onScenarioCheck: (itemId: string) => void;
  onScenarioReset: (itemId: string) => void;
  drillAnswers: Record<string, DrillAnswers>;
  drillSubmitted: Set<string>;
  onDrillAnswer: (itemId: string, index: number, value: 'true' | 'false') => void;
  onDrillSubmit: (itemId: string) => void;
  onDrillReset: (itemId: string) => void;
}