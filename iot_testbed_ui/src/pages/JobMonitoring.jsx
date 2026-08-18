import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Button,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Paper,
  AppBar,
  Toolbar,
  Container,
  Chip,
  Divider,
  CircularProgress,
  IconButton,
  Card,
  CardContent,
  Tooltip,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Visibility as VisibilityIcon,
  Dashboard as DashboardIcon,
  Build as BuildIcon,
  Group as GroupIcon,
  Search as SearchIcon,
  Add as AddIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import API_BASE_URL from '../settings';

const JobMonitoring = () => {
  const [jobGroups, setJobGroups] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchJobGroups = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Please log in to continue');
        setLoading(false);
        return;
      }
      const response = await axios.get(`${API_BASE_URL}/job-groups/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setJobGroups(response.data);
      setError('');
      setLoading(false);
    } catch (err) {
      setError('Failed to load job groups');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobGroups();
  }, []);

  const handleRefresh = () => {
    fetchJobGroups();
  };

  const handleRowClick = (groupId) => {
    navigate(`/job-groups/${groupId}`);
  };

  const getStatusChip = (status) => {
    let color = 'default';
    let icon = null;

    switch (status.toLowerCase()) {
      case 'completed':
        color = 'success';
        break;
      case 'running':
      case 'in_progress':
        color = 'primary';
        break;
      case 'failed':
        color = 'error';
        break;
      case 'pending':
      case 'queued':
        color = 'warning';
        break;
      default:
        color = 'default';
    }

    return (
      <Chip 
        label={status} 
        color={color} 
        size="small" 
        variant="outlined"
        sx={{ fontWeight: 'medium' }}
      />
    );
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString();
  };

  const handleCreateJob = () => {
    navigate('/submit-jobs');
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      {/* Navbar - matching the previous component */}
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
              <DashboardIcon sx={{ mr: 1 }} />
              Job Monitoring
            </Typography>
            
            <Box>
              <Button 
                variant="contained" 
                onClick={handleCreateJob}
                startIcon={<AddIcon />}
                sx={{ 
                  mr: 2,
                  backgroundColor: '#27ae60',
                  '&:hover': {
                    backgroundColor: '#219653',
                  },
                  borderRadius: 2
                }}
              >
                Create Job
              </Button>
              <Button 
                variant="outlined" 
                onClick={handleRefresh}
                startIcon={loading ? <CircularProgress size={20} /> : <RefreshIcon />}
                disabled={loading}
                sx={{ borderRadius: 2 }}
              >
                Refresh
              </Button>
            </Box>
          </Box>
          
          <Divider sx={{ mb: 4 }} />
          
          {loading ? (
            <Box display="flex" justifyContent="center" my={4}>
              <CircularProgress />
            </Box>
          ) : (
            <>
              {jobGroups.length === 0 ? (
                <Card sx={{ borderRadius: 2, background: 'rgba(236, 240, 241, 0.6)', py: 4 }}>
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Typography variant="h6" gutterBottom>No job groups submitted yet</Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Create your first job group to start monitoring
                    </Typography>
                    <Button 
                      variant="contained" 
                      onClick={handleCreateJob}
                      startIcon={<AddIcon />}
                      sx={{ 
                        mt: 2,
                        backgroundColor: '#3498db',
                        '&:hover': {
                          backgroundColor: '#2980b9',
                        },
                        borderRadius: 2
                      }}
                    >
                      Create New Job Group
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <Paper sx={{ width: '100%', overflow: 'hidden', borderRadius: 2 }}>
                  <Table>
                    <TableHead sx={{ backgroundColor: '#f5f5f5' }}>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold' }}>Name</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Created At</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Started At</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Completed At</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }} align="center">Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {jobGroups.map((group) => (
                        <TableRow
                          key={group.id}
                          sx={{ 
                            cursor: 'pointer', 
                            '&:hover': { backgroundColor: 'rgba(52, 152, 219, 0.05)' },
                            transition: 'background-color 0.2s ease-in-out'
                          }}
                        >
                          <TableCell onClick={() => handleRowClick(group.id)}>
                            <Typography variant="body1" sx={{ fontWeight: 'medium' }}>
                              {group.name}
                            </Typography>
                          </TableCell>
                          <TableCell onClick={() => handleRowClick(group.id)}>
                            {getStatusChip(group.status)}
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
                            <Tooltip title="View Details">
                              <IconButton
                                onClick={() => handleRowClick(group.id)}
                                size="small"
                                sx={{ 
                                  color: '#3498db',
                                  '&:hover': {
                                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                                  }
                                }}
                              >
                                <VisibilityIcon />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Paper>
              )}
            </>
          )}
          
          {error && (
            <Box sx={{ mt: 2, p: 2, backgroundColor: '#ffebee', borderRadius: 2 }}>
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

export default JobMonitoring;
