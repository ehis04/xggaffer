import type { QuizContentProps } from './types/CourseTypes';

export const QuizContent = ({ item }: QuizContentProps) => {
  return (
    <div className="quiz-content">
      <div
        className="course-type-title"
        style={{
          background: 'var(--bg-quiz-colour)',
          border: '1px solid rgba(232,184,75,0.2)',
          color: 'var(--quiz-colour)',
        }}
      >
        Quiz
      </div>
      <h2 className="ct-title">{item.title}</h2>
      <div className="qc-divider" />
      <div className="qc-placeholder">
        <div className="qc-icon">📝</div>
        <h3>{item.qc} Questions</h3>
        <p>
          Wire in your{' '}
          <code>
            {'<'}Quiz quizId="{item.qid}" {'/'}{'>'} 
          </code>{' '}
          component here.
        </p>
        <button className="qc-start-btn">Start Quiz</button>
      </div>
    </div>
  );
};