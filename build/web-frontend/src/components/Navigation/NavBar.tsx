import './css/NavBar.css';

export const NavBar = () => {
    return (
        <div className='navbar-button-container'>
            <button className='navbar-button'>Home</button>
            <button className='navbar-button'>Predictions</button>
            <button className='navbar-button'>Profile</button>
            <button className='navbar-button'>Settings</button>
        </div>
    )
}