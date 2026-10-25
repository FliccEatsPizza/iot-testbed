import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import Login from './pages/Login';
import Register from './pages/Register';
import JobSubmission from './pages/JobSubmission';
import FileManagement from './pages/FileManagement';
import AddGateway from './pages/AddGateway';
import JobMonitoring from './pages/JobMonitoring';
import JobGroupDetails from './pages/JobGroupDetails';
import Dashboard from './pages/Dashboard';
import EducationalLabs from './pages/EducationalLabs';

// Navigation component that highlights the current page
function Navigation() {
  const location = useLocation();
  const token = localStorage.getItem('token');
  
  // Define navigation links with their paths and display text
  const navLinks = [
    { path: '/dashboard', text: 'Dashboard' },
    { path: '/experiments', text: 'Educational Labs' },
    { path: '/submit-jobs', text: 'Submit Jobs' },
    { path: '/files', text: 'Files' },
    { path: '/add-gateway', text: 'Add Gateway' },
    { path: '/monitor-jobs', text: 'Monitor Jobs' }
  ];
  
  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
  };
  
  // Only show navigation when user is logged in
  if (!token) return null;
  
  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          IoT Testbed
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          {navLinks.map((link) => (
            <Button
              component={Link}
              to={link.path}
              key={link.path}
              color="inherit"
              sx={{
                position: 'relative',
                '&::after': location.pathname === link.path ? {
                  content: '""',
                  position: 'absolute',
                  bottom: 0,
                  left: 0,
                  width: '100%',
                  height: '3px',
                  backgroundColor: 'white',
                  borderRadius: '3px 3px 0 0'
                } : {}
              }}
            >
              {link.text}
            </Button>
          ))}
          <Button color="inherit" onClick={handleLogout}>Logout</Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
}

function App() {
  return (
    <Router>
      <Navigation />
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Navigate to="/login" replace />} />
        <Route path="/experiments" element={<EducationalLabs />} />
        <Route path="/submit-jobs" element={<JobSubmission />} />
        <Route path="/files" element={<FileManagement />} />
        <Route path="/add-gateway" element={<AddGateway />} />
        <Route path="/monitor-jobs" element={<JobMonitoring />} />
        <Route path="/job-groups/:id" element={<JobGroupDetails />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
      
    </Router>
  );
}

export default App;
