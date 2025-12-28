const LoginForm = () => {
    return (
        <div className="login-form">
            {error && <p className="error-message">{error}</p>}
            









            <p> Login Form Component </p>
            <form>
                <label>Username:</label>
                <input type="text" name="username" />
                <br />  
                <label>Password:</label>
                <input type="password" name="password" />
                <br />
                <button type="submit">Login</button>
            </form>
        </div>
    )
}   

export default LoginForm;