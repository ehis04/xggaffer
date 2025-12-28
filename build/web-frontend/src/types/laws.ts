export interface LawEdition {
  id: number;
  year: string;
  publication_date: string;
  is_current: boolean;
  law_count: number;
}

export interface LawClause {
  id: number;
  clause_id: number;
  heading: string;
  content: string;
  examples: string[];
  notes: string[];
  order: number;
}

export interface Law {
  id: number;
  number: number;
  title: string;
  clauses: LawClause[];
  full_content: any;
  created_at: string;
}

export interface LawListItem {
    id: number;
    number: number;
    title: string;
    clause_count: number;
}

export interface LawChange {
  id: number;
  law_number: number;
  clause_id: string;
  change_type: 'added' | 'modified' | 'removed' | 'clarified';
  description: string;
  old_content: string;
  new_content: string;
}