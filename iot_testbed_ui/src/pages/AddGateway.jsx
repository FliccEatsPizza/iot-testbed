import React, { useState } from 'react';
import {Link} from 'react-router-dom';
import {
  Button,
  Typography,
  Box,
  Paper,
  TextField,
  AppBar,
  Toolbar,
  Container,
  Divider,
  CircularProgress,
  IconButton,
  Card,
  CardContent,
} from '@mui/material';
import { 
  ContentCopy as CopyIcon, 
  Build as BuildIcon,
  Group as GroupIcon,
  Router as RouterIcon,
  ErrorOutline as ErrorOutlineIcon,
} from '@mui/icons-material';
import axios from 'axios';
import API_BASE_URL from '../settings';

const AddGateway = () => {
  const [gatewayName, setGatewayName] = useState('');
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCreateGateway = async (e) => {
    e.preventDefault();
    if (!gatewayName) {
      setError('Please enter a gateway name');
      return;
    }

    try {
      setLoading(true);
      const tokenAuth = localStorage.getItem('token');
      if (!tokenAuth) {
        setError('Please log in to continue');
        setLoading(false);
        return;
      }

      const response = await axios.post(
        `${API_BASE_URL}/gateways/`,
        { name: gatewayName },
        {
          headers: { Authorization: `Bearer ${tokenAuth}` },
        }
      );
      setToken(response.data.token);
      setGatewayName('');
      setError('');
      setLoading(false);
    } catch (err) {
      setError('Failed to create gateway');
      setLoading(false);
    }
  };

  const handleCopyToken = () => {
    navigator.clipboard.writeText(token);
    alert('Token copied to clipboard!');
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      {/* Navbar - matching the previous components */}
      <AppBar position="static" sx={{ backgroundColor: '#2c3e50', marginBottom: 4 }}>
        <Toolbar>
          <BuildIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Job Management System
          </Typography>
          <Button color="inherit" startIcon={<GroupIcon />} component={Link} to="/dashboard">
            Dashboard
          </Button>
          {/* <Button color="inherit" variant="outlined" sx={{ ml: 2 }}>
            Logout
          </Button> */}
        </Toolbar>
      </AppBar>

      {/* Main content */}
      <Container maxWidth="lg">
        <Paper 
          elevation={3} 
          sx={{ 
            padding: 4, 
            borderRadius: 2,
            background: 'linear-gradient(145deg, #f9f9f9 0%, #f0f0f0 100%)',
          }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography 
              variant="h4" 
              sx={{ 
                fontWeight: 'bold',
                color: '#2c3e50',
                display: 'flex',
                alignItems: 'center' 
              }}
            >
              <RouterIcon sx={{ mr: 1 }} />
              Add Gateway
            </Typography>
          </Box>
          
          <Divider sx={{ mb: 4 }} />

          <Card sx={{ mb: 4, borderRadius: 2, background: 'rgba(236, 240, 241, 0.6)' }}>
            <CardContent>
              <Box component="form" onSubmit={handleCreateGateway}>
                <TextField
                  label="Gateway Name"
                  fullWidth
                  margin="normal"
                  value={gatewayName}
                  onChange={(e) => setGatewayName(e.target.value)}
                  required
                  variant="outlined"
                  sx={{ mb: 2 }}
                />
                <Button 
                  type="submit" 
                  variant="contained"
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <RouterIcon />}
                  sx={{ 
                    mt: 2,
                    backgroundColor: '#27ae60',
                    '&:hover': {
                      backgroundColor: '#219653',
                    },
                    borderRadius: 2
                  }}
                >
                  {loading ? 'Creating...' : 'Create Gateway'}
                </Button>
              </Box>
            </CardContent>
          </Card>

          {token && (
            <Card sx={{ mb: 4, borderRadius: 2, background: 'rgba(236, 240, 241, 0.6)' }}>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', color: '#2c3e50' }}>
                  Registration Token
                </Typography>
                <Box sx={{ 
                  display: 'flex', 
                  alignItems: 'center',
                  p: 2,
                  borderRadius: 1,
                  backgroundColor: 'rgba(39, 174, 96, 0.1)',
                  border: '1px dashed #27ae60',
                  mb: 2
                }}>
                  <Typography 
                    sx={{ 
                      flexGrow: 1, 
                      wordBreak: 'break-all',
                      fontFamily: 'monospace',
                      fontSize: '0.9rem'
                    }}
                  >
                    {token}
                  </Typography>
                  <IconButton 
                    onClick={handleCopyToken}
                    sx={{ 
                      color: '#3498db',
                      ml: 1,
                      '&:hover': {
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                      }
                    }}
                  >
                    <CopyIcon />
                  </IconButton>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Use this token to register your gateway with the system.
                </Typography>
              </CardContent>
            </Card>
          )}
          
          {error && (
            <Box sx={{ mt: 2, p: 2, backgroundColor: '#ffebee', borderRadius: 2, display: 'flex', alignItems: 'center' }}>
              <ErrorOutlineIcon color="error" sx={{ mr: 1 }} />
              <Typography color="error">
                {error}
              </Typography>
            </Box>
          )}
        </Paper>
      </Container>
      <Box
              sx={{
                position: 'fixed',
                bottom: 0,
                left: 0,
                width: '100%',
                bgcolor: 'white',
                pb: 2,
                pt: 1
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'center' }}>
                <Divider sx={{ width: '20%' }} />
              </Box>
              <Box sx={{ mt: -1, py: 2, color: '#2c3e50', textAlign: 'center' }}>
                <Typography variant="body2" sx={{ fontFamily: 'Arial, sans-serif', color: '#d3d3d3' }}>
                  &copy; {new Date().getFullYear()} Job Management System. All rights reserved.
                </Typography>
              </Box>
            </Box>
    </Box>
  );
};

export default AddGateway;