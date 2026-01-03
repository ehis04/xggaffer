import { Link } from 'react-router-dom';

const RefBase = () => {
    return (
        <>
        
        <div className="intro-text">
            <p> Intro Text explaining what the section is about </p>
        </div>

        <div className="section-cards">

            <p>These will be cards explaining each area within the referee section</p>

            <Link to ="/quizBase" className="card">
                <h3>Laws of The Game Quizzes</h3>
                <p>Quizzes based on the laws of football.</p>
            </Link>

            <Link to ="/fitnessBase" className="card">
                <h3>Fitness Drills</h3>
                <p>Exercises and advice for improving fitness.</p>
            </Link>

            <Link to ="/controlBase" className="card">
                <h3>Control Training</h3>
                <p>Explaning the importance of social connection and offering resources to improve</p>
            </Link>

            <Link to ="/situationBase" className="card">
                <h3>Situational Videos</h3>
                <p>Videos including controversial or specific actions that refs must make a decision on.</p>
            </Link>

            <Link to ="/articleBase" className="card">
                <h3>Articles</h3>
                <p>Relevant articles.</p>
            </Link>

        </div>
        </>
    )
}

export default RefBase;