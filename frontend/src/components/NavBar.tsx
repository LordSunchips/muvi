import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function NavBar() {
  const { user, logout } = useAuth();
  if (!user) return null;

  return (
    <nav className="navbar">
      <div className="navbar-brand">🎬 muvi</div>
      <div className="navbar-links">
        <NavLink to="/" end>
          Rankings
        </NavLink>
        <NavLink to="/search">Search</NavLink>
        <NavLink to="/want-to-watch">Watchlist</NavLink>
        <NavLink to="/feed">Feed</NavLink>
        <NavLink to="/friends">Friends</NavLink>
        <NavLink to={`/profile/${user.id}`}>{user.display_name}</NavLink>
      </div>
      <button className="link-button" onClick={logout}>
        Log out
      </button>
    </nav>
  );
}
