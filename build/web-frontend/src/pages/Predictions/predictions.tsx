import { NavBar } from "../../components/Navigation/NavBar"
import { HandlePredictions } from "../../components/Tester/handlePredictions"
import './css/predictions.css';

export const Predictions = () => {
    return (
        <div className="predictions-page">
            <NavBar/>
            <HandlePredictions/>
        </div>
    )
}