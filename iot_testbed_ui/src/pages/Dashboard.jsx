import React, { useState, useEffect } from 'react';
import {
  TextField,
  Checkbox,
  FormControlLabel,
  Select,
  MenuItem,
  Button,
  Box,
  Typography,
  FormControl,
  InputLabel,
  Paper,
  AppBar,
  Toolbar,
  Container,
  Grid,
  Chip,
  Avatar,
  Divider,
  CircularProgress,
  Card,
  CardContent,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
} from '@mui/material';
import {
  Build as BuildIcon,
  Dashboard as DashboardIcon,
  CloudUpload as CloudUploadIcon,
  FolderOpen as FolderOpenIcon,
  Router as RouterIcon,
  Assessment as AssessmentIcon,
  ExitToApp as ExitToAppIcon,
  Person as PersonIcon,
  Description as DescriptionIcon,
  Send as SendIcon,
  Group as GroupIcon,
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
  Add as AddIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import axios from 'axios';
import API_BASE_URL from '../settings';

const Dashboard = () => {

  const [username, setUsername] = useState('');
  const [userDescription, setUserDescription] = useState('IoT Researcher');
  const [jobGroups, setJobGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const token = localStorage.getItem('token');

        const response = await axios.get(`${API_BASE_URL}/auth/me`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        setUsername(response.data.username); // <-- Corrected this line

        const dummyJobGroups = []; // Add your dummy job groups here
        setJobGroups(dummyJobGroups);

        setLoading(false);
      } catch (error) {
        console.error("Error fetching data:", error);
        setError('Failed to load user data');
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleNavigation = (path) => {
    window.location.href = `/${path}`;
  };

  const handleRefresh = () => {
    // Re-fetch data
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
    }, 800);
  };

  const handleRowClick = (groupId) => {
    handleNavigation(`job-groups/${groupId}`);
  };

  // Removed getStatusChip as we're handling chip styling directly in the JSX

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString();
  };

  const handleCreateJob = () => {
    handleNavigation('submit-jobs');
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      {/* Navbar */}
      <AppBar position="static" sx={{ backgroundColor: '#2c3e50', marginBottom: 4 }}>
        <Toolbar>
          <BuildIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Job Management System
          </Typography>
          <Button color="inherit" startIcon={<RouterIcon />} onClick={() => handleNavigation('add-gateway')}>
            Add Gateway
          </Button>
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
          <Typography
            variant="h4"
            gutterBottom
            sx={{
              fontWeight: 'bold',
              color: '#2c3e50',
              textAlign: 'center',
              mb: 3
            }}
          >
            <DashboardIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            Dashboard
          </Typography>

          <Divider sx={{ mb: 4 }} />

          {loading ? (
            <Box display="flex" justifyContent="center" my={4}>
              <CircularProgress />
            </Box>
          ) : (
            <>
              {/* User Profile Section */}
              <Card sx={{ mb: 4, borderRadius: 2, background: 'rgba(236, 240, 241, 0.6)' }}>
                <CardContent>
                  <Grid container spacing={3} alignItems="center">
                    {/* User Avatar */}
                    <Grid item xs={12} sm={2} md={2} sx={{ textAlign: { xs: 'center', sm: 'left' } }}>
                      <Avatar 
                        sx={{ 
                          width: 100, 
                          height: 100, 
                          bgcolor: '#3498db',
                          margin: { xs: 'auto', sm: '0' }
                        }}
                      >
                        <PersonIcon sx={{ fontSize: 50 }} />
                      </Avatar>
                    </Grid>
                    
                    {/* User Info */}
                    <Grid item xs={12} sm={6} md={6}>
                      <Typography variant="h5" sx={{ fontWeight: 'bold', color: '#2c3e50', mb: 1 }}>
                        {username}
                      </Typography>
                      <Typography variant="body1" color="text.secondary">
                        {userDescription}
                      </Typography>
                    </Grid>
                    
                    {/* Quick Action Buttons */}
                    <Grid item xs={12} sm={4} md={4}>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        <Button
                          variant="outlined"
                          startIcon={<SendIcon />}
                          sx={{ justifyContent: 'flex-start', borderRadius: 2 }}
                          onClick={() => handleNavigation('submit-jobs')}
                        >
                          Submit Jobs
                        </Button>
                        <Button
                          variant="outlined"
                          startIcon={<FolderOpenIcon />}
                          sx={{ justifyContent: 'flex-start', borderRadius: 2 }}
                          onClick={() => handleNavigation('files')}
                        >
                          Files
                        </Button>
                        <Button
                          variant="outlined"
                          startIcon={<RouterIcon />}
                          sx={{ justifyContent: 'flex-start', borderRadius: 2 }}
                          onClick={() => handleNavigation('add-gateway')}
                        >
                          Add Gateway
                        </Button>
                      </Box>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* Job Monitoring Section - Matching the simplified version from the screenshots */}
              <Box sx={{ mt: 4, mb: 4 }}>
                <Box sx={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center', 
                  mb: 3,
                  pb: 2,
                  borderBottom: '1px solid #e0e0e0'
                }}>
                  <Typography variant="h5" sx={{ 
                    display: 'flex', 
                    alignItems: 'center',
                    fontWeight: 500,
                    color: '#2c3e50'
                  }}>
                    <AssessmentIcon sx={{ mr: 1.5 }} />
                    Job Submission 
                  </Typography>
                  
                  <Box>
                    <Button 
                      variant="contained" 
                      onClick={handleCreateJob}
                      startIcon={<AddIcon />}
                      sx={{ 
                        mr: 2,
                        backgroundColor: '#4CAF50',
                        borderRadius: 2,
                        textTransform: 'uppercase',
                        fontWeight: 500,
                        px: 2,
                        '&:hover': {
                          backgroundColor: '#388E3C',
                        },
                      }}
                    >
                      Create Job
                    </Button>
                    <Button 
                      variant="outlined" 
                      onClick={handleRefresh}
                      startIcon={loading ? <CircularProgress size={20} /> : <RefreshIcon />}
                      disabled={loading}
                      sx={{ 
                        borderRadius: 2,
                        color: '#2196F3',
                        borderColor: '#2196F3',
                        textTransform: 'uppercase',
                        fontWeight: 500,
                        '&:hover': {
                          borderColor: '#1976D2',
                          backgroundColor: 'rgba(33, 150, 243, 0.04)',
                        }
                      }}
                    >
                      Refresh
                    </Button>
                  </Box>
                </Box>

                {loading ? (
                  <Box display="flex" justifyContent="center" my={4}>
                    <CircularProgress />
                  </Box>
                ) : (
                  <Paper sx={{ 
                    width: '100%', 
                    overflow: 'hidden', 
                    boxShadow: 'none', 
                    border: '1px solid #f0f0f0',
                    borderRadius: '8px'
                  }}>
                    <Table sx={{ minWidth: 650 }}>
                      <TableHead sx={{ backgroundColor: '#fafafa' }}>
                        <TableRow>
                          {/* <TableCell sx={{ fontWeight: 500, color: '#333', py: 2 }}>Name</TableCell>
                          <TableCell sx={{ fontWeight: 500, color: '#333', py: 2 }}>Status</TableCell>
                          <TableCell sx={{ fontWeight: 500, color: '#333', py: 2 }}>Created At</TableCell>
                          <TableCell sx={{ fontWeight: 500, color: '#333', py: 2 }}>Started At</TableCell>
                          <TableCell sx={{ fontWeight: 500, color: '#333', py: 2 }}>Completed At</TableCell>
                          <TableCell sx={{ fontWeight: 500, color: '#333', py: 2 }} align="center">Actions</TableCell> */}
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {jobGroups.map((group) => (
                          <TableRow
                            key={group.id}
                            sx={{ 
                              cursor: 'pointer', 
                              '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.01)' },
                              borderBottom: '1px solid #f0f0f0'
                            }}
                          >
                            <TableCell onClick={() => handleRowClick(group.id)}>
                              {group.name}
                            </TableCell>
                            <TableCell onClick={() => handleRowClick(group.id)}>
                              <Chip 
                                label={group.status} 
                                sx={{ 
                                  borderRadius: '16px',
                                  backgroundColor: 
                                    group.status.toLowerCase() === 'completed' ? 'rgba(76, 175, 80, 0.1)' : 
                                    group.status.toLowerCase() === 'running' ? 'rgba(33, 150, 243, 0.1)' : 
                                    group.status.toLowerCase() === 'pending' ? 'rgba(255, 152, 0, 0.1)' : 
                                    'rgba(158, 158, 158, 0.1)',
                                  color: 
                                    group.status.toLowerCase() === 'completed' ? '#388E3C' : 
                                    group.status.toLowerCase() === 'running' ? '#1976D2' : 
                                    group.status.toLowerCase() === 'pending' ? '#F57C00' : 
                                    '#616161',
                                  border: 
                                    group.status.toLowerCase() === 'completed' ? '1px solid #81C784' : 
                                    group.status.toLowerCase() === 'running' ? '1px solid #64B5F6' : 
                                    group.status.toLowerCase() === 'pending' ? '1px solid #FFB74D' : 
                                    '1px solid #E0E0E0',
                                  fontWeight: 500,
                                  fontSize: '0.75rem'
                                }}
                                size="small"
                              />
                            </TableCell>
                            <TableCell onClick={() => handleRowClick(group.id)}>
                              {formatDate(group.created_at)}
                            </TableCell>
                            <TableCell onClick={() => handleRowClick(group.id)}>
                              {formatDate(group.started_at)}
                            </TableCell>
                            <TableCell onClick={() => handleRowClick(group.id)}>
                              {formatDate(group.completed_at)}
                            </TableCell>
                            <TableCell align="center">
                              <IconButton
                                onClick={() => handleRowClick(group.id)}
                                size="small"
                                sx={{ color: '#2196F3' }}
                              >
                                <VisibilityIcon />
                              </IconButton>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Paper>
                )}
                
                {error && (
                  <Box sx={{ mt: 2, p: 2, backgroundColor: '#ffebee', borderRadius: 2 }}>
                    <Typography color="error">
                      {error}
                    </Typography>
                  </Box>
                )}
              </Box>

              <Button
                variant="contained"
                fullWidth
                startIcon={<AddIcon />}
                onClick={() => handleNavigation('submit-jobs')}
                sx={{
                  mt: 4,
                  mb: 2,
                  py: 1.5,
                  backgroundColor: '#2c3e50',
                  borderRadius: 2,
                  '&:hover': {
                    backgroundColor: '#1a2530',
                  }
                }}
              >
                Submit New Job Group
              </Button>
            </>
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

export default Dashboard;
