import {useState} from 'react';
import predictions from './predictions.json';
import Popup from 'reactjs-popup';

interface Prediction {
    home_team: string;
    away_team: string;
    prediction: string;
    confidence: number;
    home_win_prob: number;
    draw_prob: number;
    away_win_prob: number;
}

interface ErrorResult {
    error: string;
}

type PredictionResult = Prediction | ErrorResult | null;

export function HandlePredictions () {
    const [homeTeam, setHomeTeam] = useState('');
    const [awayTeam, setAwayTeam] = useState('');
    const [result, setResult] = useState<PredictionResult>(null);

    const handlePredict = () => {
        const match = predictions.predictions.find(p =>
            p.home_team.toLowerCase() === homeTeam.toLowerCase() &&
            p.away_team.toLowerCase() === awayTeam.toLowerCase()
        );
        setResult(match || {error: 'No prediction found'});
    };

    return (
        <div>
            <h1> Football Match Prediction </h1>
            <input value={homeTeam} onChange={(e) => setHomeTeam(e.target.value)} placeholder="Home Team" />
            <input value={awayTeam} onChange={(e) => setAwayTeam(e.target.value)} placeholder="Away Team" />
            <Popup position="center center" modal trigger={<button onClick={handlePredict}>Predict</button>}>
                {result && 'error' in result && (
                    <div>
                        <p>{result.error}</p>
                    </div>
                )}
                {result && 'prediction' in result && (
                    <div>
                    <h2>Prediction: {result.prediction}</h2>
                    <p>Confidence: {(result.confidence * 100).toFixed(1)}%</p>
                    </div>
                )}
            </Popup>
        </div>
    )
}