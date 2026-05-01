import logo from '../../images/logos/appLogo.png';
import './css/TitleLogo.css';

export const TitleLogo = () => {
    return (
        <div className="titleLogo">
            <div className="Logo">
                <img src={logo} alt='Logo' className="titleNavLogo" />
            </div>
            <div className="Title">
                <h3> iFoot </h3>
            </div>
        </div>
    )
}