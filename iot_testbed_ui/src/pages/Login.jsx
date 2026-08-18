import React, { useState } from 'react';
import { TextField, Button, Typography, Box, Grid, InputAdornment } from '@mui/material';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import EmailIcon from '@mui/icons-material/Email';
import LockIcon from '@mui/icons-material/Lock';
import image from './image.jpg';
import API_BASE_URL from '../settings';

// Create a custom style to override any AppBar that might be in a parent component
const appBarOverrideStyle = `
  .MuiAppBar-root, header, nav, .navigation-bar, .app-bar, .navbar {
    display: none !important;
  }
`;

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const data = new URLSearchParams();
      data.append('username', username);
      data.append('password', password);
      const response = await axios.post(`${API_BASE_URL}/auth/login`, data);
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      navigate('/submit-jobs');
    } catch (err) {
      setError('Invalid credentials');
    }
  };

  return (
    <>
      {/* Add a style tag to hide any app bar */}
      <style>{appBarOverrideStyle}</style>
      
      <Grid 
        container 
        sx={{ 
          maxWidth: 'xl', 
          margin: '0 auto', 
          height: '100vh',
          padding: 0,
          overflow: 'hidden',
          // Make sure this component takes up the full viewport from the very top
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 1300 // This is higher than MUI's AppBar default z-index
        }}
      >
        {/* Left column with image - hidden on small screens */}
        <Grid 
          item 
          xs={0} 
          lg={6} 
          sx={{ 
            display: { xs: 'none', lg: 'flex' },
            justifyContent: 'center',
            alignItems: 'center'
          }}
        >
          <img src={image} alt="Description of the image" style={{ width: '66%' }} />
        </Grid>

        {/* Right column with login form */}
        <Grid 
          item 
          xs={12} 
          lg={6} 
          sx={{ 
            display: 'flex', 
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            padding: { xs: '0 20px', md: '0 40px' }
          }}
        >
          <Box sx={{ width: '100%', maxWidth: '66%' }}>
            <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Image for mobile - hidden on larger screens */}
              <Box sx={{ display: { xs: 'block', lg: 'none' }, mb: 2 }}>
                <img src={image} alt="Description of the image" style={{ width: '96px' }} />
              </Box>

              <Typography variant="h4" fontWeight="800" sx={{ mb: 2 }}>
                Log In.
              </Typography>

              <TextField
                fullWidth
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <EmailIcon />
                    </InputAdornment>
                  ),
                  sx: { 
                    borderRadius: '4px',
                    '& .MuiOutlinedInput-notchedOutline': {
                      borderColor: '#e0e0e0'
                    }
                  }
                }}
                variant="outlined"
              />

              <TextField
                fullWidth
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <LockIcon />
                    </InputAdornment>
                  ),
                  sx: { 
                    borderRadius: '4px',
                    '& .MuiOutlinedInput-notchedOutline': {
                      borderColor: '#e0e0e0'
                    }
                  }
                }}
                variant="outlined"
                sx={{ mb: 1 }}
              />
              
              <Button 
                type="submit" 
                variant="contained" 
                fullWidth 
                sx={{ 
                  borderRadius: '24px',
                  padding: '10px',
                  textTransform: 'none',
                  fontWeight: 500
                }}
              >
                Log In
              </Button>
              
              {error && <Typography color="error">{error}</Typography>}
            </form>

            <Box sx={{ mt: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Typography color="text.secondary" sx={{ fontSize: '1.1rem' }}>
                Don't have an account?
              </Typography>
              <Link to="/register" style={{ textDecoration: 'none', width: '100%' }}>
                <Button 
                  variant="outlined" 
                  fullWidth 
                  sx={{ 
                    borderRadius: '24px',
                    padding: '10px',
                    textTransform: 'none',
                    fontWeight: 500
                  }}
                >
                  Sign Up
                </Button>
              </Link>
            </Box>
          </Box>
        </Grid>
      </Grid>
    </>
  );
};

export default Login;