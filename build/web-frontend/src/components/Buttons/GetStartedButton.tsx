import './css/GetStartedButton.css'

interface GetStartedButtonProps {
    onClick?: () => void;
}

export const GetStartedButton = ({ onClick }: GetStartedButtonProps) => {
    return (
        <button className="getStartedButton" onClick={onClick}>
            <div className="body">
                <p> Get Started </p>
            </div>
        </button>
    );
}