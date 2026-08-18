import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
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
  Grid,
  Tooltip,
  Breadcrumbs,
  Snackbar,
  Alert,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  ArrowBack as ArrowBackIcon,
  Dashboard as DashboardIcon,
  Build as BuildIcon,
  Group as GroupIcon,
  List as ListIcon,
  Info as InfoIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import axios from 'axios';
import API_BASE_URL from '../settings';

const JobGroupDetails = () => {
  const { id } = useParams();
  const [jobGroup, setJobGroup] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [jobLogs, setJobLogs] = useState({});
  const [checkingLogs, setCheckingLogs] = useState({});
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const navigate = useNavigate();

  const fetchJobGroupDetails = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Please log in to continue');
        setLoading(false);
        return;
      }
      const response = await axios.get(`${API_BASE_URL}/job-groups/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setJobGroup(response.data);
      setError('');
      setLoading(false);
      
      // Check log availability for each job
      if (response.data && response.data.jobs) {
        response.data.jobs.forEach(job => {
          checkJobLogExists(job.id);
        });
      }
    } catch (err) {
      setError(`Failed to load job group details: ${err.message}`);
      setLoading(false);
    }
  };

  const checkJobLogExists = async (jobId) => {
    try {
      setCheckingLogs(prev => ({ ...prev, [jobId]: true }));
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_BASE_URL}/jobs/${jobId}/log`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      setJobLogs(prev => ({ 
        ...prev, 
        [jobId]: response.data.exists 
      }));
      setCheckingLogs(prev => ({ ...prev, [jobId]: false }));
    } catch (err) {
      console.error(`Error checking log for job ${jobId}:`, err);
      setCheckingLogs(prev => ({ ...prev, [jobId]: false }));
    }
  };

  const downloadJobLog = async (jobId) => {
    try {
      const token = localStorage.getItem('token');
      
      // Using fetch for direct download handling
      const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/log/download`, {
        headers: { 
          Authorization: `Bearer ${token}` 
        }
      });
      
      if (!response.ok) {
        throw new Error(`Failed to download log: ${response.statusText}`);
      }
      
      // Get filename from header or create one
      const contentDisposition = response.headers.get('content-disposition');
      let filename = `job-${jobId}-log.txt`;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      // Create blob and download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      setSnackbar({
        open: true,
        message: 'Log downloaded successfully',
        severity: 'success'
      });
    } catch (err) {
      console.error('Error downloading log:', err);
      setSnackbar({
        open: true,
        message: `Failed to download log: ${err.message}`,
        severity: 'error'
      });
    }
  };

  useEffect(() => {
    fetchJobGroupDetails();
  }, [id]);

  const handleRefresh = () => {
    fetchJobGroupDetails();
  };

  const handleBackToList = () => {
    navigate('/monitor-jobs');
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const getStatusChip = (status) => {
    let color = 'default';

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
      case 'preparing':
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

  return (
    <Box sx={{ flexGrow: 1 }}>
      {/* Navbar - matching the JobMonitoring component */}
      <AppBar position="static" sx={{ backgroundColor: '#2c3e50', marginBottom: 4 }}>
        <Toolbar>
          <BuildIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Job Management System
          </Typography>
          <Button color="inherit" startIcon={<GroupIcon />} component={Link} to="/dashboard">
            Dashboard
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
          {/* Breadcrumb Navigation */}
          <Breadcrumbs sx={{ mb: 3 }}>
            <Link to="/dashboard" style={{ textDecoration: 'none', color: '#3498db' }}>
              <Typography sx={{ display: 'flex', alignItems: 'center' }}>
                <DashboardIcon sx={{ mr: 0.5, fontSize: 16 }} />
                Dashboard
              </Typography>
            </Link>
            <Link to="/monitor-jobs" style={{ textDecoration: 'none', color: '#3498db' }}>
              <Typography sx={{ display: 'flex', alignItems: 'center' }}>
                <ListIcon sx={{ mr: 0.5, fontSize: 16 }} />
                Job Monitoring
              </Typography>
            </Link>
            <Typography color="text.primary" sx={{ display: 'flex', alignItems: 'center' }}>
              <InfoIcon sx={{ mr: 0.5, fontSize: 16 }} />
              Job Group Details
            </Typography>
          </Breadcrumbs>

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Button 
                variant="outlined" 
                startIcon={<ArrowBackIcon />}
                onClick={handleBackToList}
                sx={{ mr: 2, borderRadius: 2 }}
              >
                Back to List
              </Button>
              <Typography 
                variant="h4" 
                sx={{ 
                  fontWeight: 'bold',
                  color: '#2c3e50',
                }}
              >
                Job Group Details
              </Typography>
            </Box>
            
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
          
          <Divider sx={{ mb: 4 }} />
          
          {loading ? (
            <Box display="flex" justifyContent="center" my={4}>
              <CircularProgress />
            </Box>
          ) : error ? (
            <Box sx={{ mt: 2, p: 2, backgroundColor: '#ffebee', borderRadius: 2 }}>
              <Typography color="error">
                {error}
              </Typography>
            </Box>
          ) : jobGroup ? (
            <>
              {/* Job Group Summary Card */}
              <Card sx={{ mb: 4, borderRadius: 2, boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
                <CardContent>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <Typography variant="h5" sx={{ mb: 2, fontWeight: 'bold', color: '#2c3e50' }}>
                        {jobGroup.name}
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Typography variant="body2" sx={{ fontWeight: 'bold', width: 120 }}>
                            Status:
                          </Typography>
                          {getStatusChip(jobGroup.status)}
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Typography variant="body2" sx={{ fontWeight: 'bold', width: 120 }}>
                            ID:
                          </Typography>
                          <Typography variant="body2">{jobGroup.id}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Typography variant="body2" sx={{ fontWeight: 'bold', width: 120 }}>
                            User ID:
                          </Typography>
                          <Typography variant="body2">{jobGroup.user_id}</Typography>
                        </Box>
                      </Box>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Typography variant="body2" sx={{ fontWeight: 'bold', width: 120 }}>
                            Created:
                          </Typography>
                          <Typography variant="body2">{formatDate(jobGroup.created_at)}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Typography variant="body2" sx={{ fontWeight: 'bold', width: 120 }}>
                            Started:
                          </Typography>
                          <Typography variant="body2">{formatDate(jobGroup.started_at)}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Typography variant="body2" sx={{ fontWeight: 'bold', width: 120 }}>
                            Completed:
                          </Typography>
                          <Typography variant="body2">{formatDate(jobGroup.completed_at)}</Typography>
                        </Box>
                      </Box>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* Jobs Table */}
              <Typography variant="h5" sx={{ mb: 2, fontWeight: 'bold', color: '#2c3e50' }}>
                Jobs ({jobGroup.jobs.length})
              </Typography>
              
              {jobGroup.jobs.length === 0 ? (
                <Card sx={{ borderRadius: 2, background: 'rgba(236, 240, 241, 0.6)', py: 4 }}>
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Typography variant="h6" gutterBottom>No jobs found in this group</Typography>
                  </CardContent>
                </Card>
              ) : (
                <Paper sx={{ width: '100%', overflow: 'hidden', borderRadius: 2 }}>
                  <Table>
                    <TableHead sx={{ backgroundColor: '#f5f5f5' }}>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold' }}>Job ID</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Device ID</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Created At</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Started At</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Completed At</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }} align="center">Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {jobGroup.jobs.map((job) => (
                        <TableRow
                          key={job.id}
                          sx={{ 
                            '&:hover': { backgroundColor: 'rgba(52, 152, 219, 0.05)' },
                            transition: 'background-color 0.2s ease-in-out'
                          }}
                        >
                          <TableCell>
                            <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                              {job.id}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {job.device_id}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            {getStatusChip(job.status)}
                          </TableCell>
                          <TableCell>
                            {formatDate(job.created_at)}
                          </TableCell>
                          <TableCell>
                            {formatDate(job.started_at)}
                          </TableCell>
                          <TableCell>
                            {formatDate(job.completed_at)}
                          </TableCell>
                          <TableCell align="center">
                            {/* Show download button for logs if logs exist */}
                            {checkingLogs[job.id] ? (
                              <CircularProgress size={20} />
                            ) : jobLogs[job.id] ? (
                              <Tooltip title="Download Log">
                                <IconButton
                                  size="small"
                                  onClick={() => downloadJobLog(job.id)}
                                  sx={{ 
                                    color: '#3498db',
                                    '&:hover': {
                                      backgroundColor: 'rgba(52, 152, 219, 0.1)',
                                    }
                                  }}
                                >
                                  <DownloadIcon />
                                </IconButton>
                              </Tooltip>
                            ) : null}
                            
                            {/* Original download button for output files */}
                            {job.output_file_id && (
                              <Tooltip title="Download Output">
                                <IconButton
                                  size="small"
                                  sx={{ 
                                    color: '#3498db',
                                    '&:hover': {
                                      backgroundColor: 'rgba(52, 152, 219, 0.1)',
                                    },
                                    ml: jobLogs[job.id] ? 1 : 0
                                  }}
                                >
                                  <DownloadIcon />
                                </IconButton>
                              </Tooltip>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Paper>
              )}
            </>
          ) : (
            <Box sx={{ mt: 2, p: 2, backgroundColor: '#fffde7', borderRadius: 2 }}>
              <Typography color="textSecondary">
                Job group not found
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

      {/* Notification Snackbar */}
      <Snackbar 
        open={snackbar.open} 
        autoHideDuration={6000} 
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert 
          onClose={handleCloseSnackbar} 
          severity={snackbar.severity} 
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default JobGroupDetails;
