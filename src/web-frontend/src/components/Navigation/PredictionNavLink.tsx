import { NavLink } from 'react-router-dom';

export default function PredictionNavLink() {
  return (
    <NavLink
      to="/predictions"
      className={({ isActive }) =>
        [
          'inline-flex items-center rounded-lg px-3 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'bg-emerald-600 text-white'
            : 'text-slate-300 hover:bg-slate-800 hover:text-white',
        ].join(' ')
      }
    >
      Predictions
    </NavLink>
  );
}
