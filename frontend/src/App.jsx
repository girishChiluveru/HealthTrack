import { useAuth } from './auth/useAuth.js';
import AuthScreen from './components/AuthScreen.jsx';
import DoctorDashboard from './components/DoctorDashboard.jsx';
import SymptomDashboard from './components/SymptomDashboard.jsx';

export default function App() {
  const { user, isCheckingSession, notice, login, register, logout } = useAuth();

  if (isCheckingSession) {
    return (
      <p className="loading-screen" role="status">
        Checking your session…
      </p>
    );
  }
  if (!user) {
    return <AuthScreen notice={notice} onLogin={login} onRegister={register} />;
  }
  return user.role === 'patient' ? (
    <SymptomDashboard user={user} onLogout={logout} />
  ) : (
    <DoctorDashboard user={user} onLogout={logout} />
  );
}
