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
} from '@mui/material';
import {
  Computer as ComputerIcon,
  CloudUpload as CloudUploadIcon,
  Send as SendIcon,
  Build as BuildIcon,
  Group as GroupIcon,
} from '@mui/icons-material';
import axios from 'axios';
import { Link } from 'react-router-dom';
import API_BASE_URL from '../settings';

const JobSubmission = () => {
  const [jobGroupName, setJobGroupName] = useState('');
  const [devices, setDevices] = useState([]);
  const [files, setFiles] = useState([]);
  const [selectedDevices, setSelectedDevices] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitLoading, setSubmitLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const token = localStorage.getItem('token');
        if (!token) {
          setError('Please log in to continue');
          setLoading(false);
          return;
        }

        const devicesResponse = await axios.get(`${API_BASE_URL}/devices/`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setDevices(devicesResponse.data);

        const filesResponse = await axios.get(`${API_BASE_URL}/files/`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setFiles(filesResponse.data);
        setLoading(false);
      } catch (err) {
        setError('Failed to load devices or files');
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleDeviceToggle = (deviceId) => {
    const isSelected = selectedDevices.some((d) => d.device_id === deviceId);
    if (isSelected) {
      setSelectedDevices(selectedDevices.filter((d) => d.device_id !== deviceId));
    } else {
      setSelectedDevices([...selectedDevices, { device_id: deviceId, file_id: '' }]);
    }
  };

  const handleFileChange = (deviceId, fileId) => {
    setSelectedDevices(
      selectedDevices.map((d) =>
        d.device_id === deviceId ? { ...d, file_id: fileId } : d
      )
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!jobGroupName || selectedDevices.length === 0 || selectedDevices.some((d) => !d.file_id)) {
      setError('Please fill all fields: job group name, devices, and a file for each device');
      return;
    }

    try {
      setSubmitLoading(true);
      const token = localStorage.getItem('token');
      const payload = {
        name: jobGroupName,
        jobs: selectedDevices.map((d) => ({
          device_id: d.device_id,
          source_file_id: d.file_id,
        })),
      };
      await axios.post(`${API_BASE_URL}/job-groups/`, payload, {
        headers: { Authorization: `Bearer ${token}` },
      });

      // Success notification
      setSubmitLoading(false);
      alert('Job group submitted successfully');
      setJobGroupName('');
      setSelectedDevices([]);
      setError('');
    } catch (err) {
      setSubmitLoading(false);
      setError('Failed to submit job group');
    }
  };

  const getDeviceName = (deviceId) => {
    const device = devices.find((d) => d.id === deviceId);
    return device ? device.name : 'Unknown Device';
  };

  const getFileName = (fileId) => {
    const file = files.find((f) => f.id === fileId);
    return file ? file.filename : 'No file selected';
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

          <Button color="inherit" startIcon={<GroupIcon />} component={Link} to="/dashboard">
            Dashboard
          </Button>
          
          {/* <Button color="inherit" variant="outlined" sx={{ ml: 2 }}>
            Logout
          </Button> */}
        </Toolbar>
      </AppBar>

      {/* Main content */}
      <Container maxWidth="md">
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
            <SendIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            Submit New Job Group
          </Typography>

          <Divider sx={{ mb: 4 }} />

          {loading ? (
            <Box display="flex" justifyContent="center" my={4}>
              <CircularProgress />
            </Box>
          ) : (
            <form onSubmit={handleSubmit}>
              <TextField
                label="Job Group Name"
                fullWidth
                margin="normal"
                value={jobGroupName}
                onChange={(e) => setJobGroupName(e.target.value)}
                required
                variant="outlined"
                InputProps={{
                  sx: { borderRadius: 2 }
                }}
              />

              <Card sx={{ mt: 4, mb: 4, borderRadius: 2, background: 'rgba(236, 240, 241, 0.6)' }}>
                <CardContent>
                  <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <ComputerIcon sx={{ mr: 1 }} />
                    Available Devices
                  </Typography>

                  {devices.length === 0 ? (
                    <Typography>No devices available</Typography>
                  ) : (
                    <Grid container spacing={2}>
                      {devices.map((device) => (
                        <Grid item xs={12} sm={6} md={4} key={device.id}>
                          <Paper
                            elevation={selectedDevices.some(d => d.device_id === device.id) ? 3 : 1}
                            sx={{
                              p: 2,
                              borderRadius: 2,
                              border: selectedDevices.some(d => d.device_id === device.id)
                                ? '2px solid #3498db'
                                : '1px solid #e0e0e0',
                              transition: 'all 0.3s ease',
                              '&:hover': {
                                boxShadow: '0 4px 8px rgba(0,0,0,0.1)'
                              }
                            }}
                          >
                            <FormControlLabel
                              control={
                                <Checkbox
                                  checked={selectedDevices.some((d) => d.device_id === device.id)}
                                  onChange={() => handleDeviceToggle(device.id)}
                                  color="primary"
                                />
                              }
                              label={
                                <Typography
                                  sx={{
                                    fontWeight: selectedDevices.some(d => d.device_id === device.id)
                                      ? 'bold'
                                      : 'normal'
                                  }}
                                >
                                  {device.name}
                                </Typography>
                              }
                            />
                          </Paper>
                        </Grid>
                      ))}
                    </Grid>
                  )}
                </CardContent>
              </Card>

              {selectedDevices.length > 0 && (
                <Card sx={{ mt: 4, mb: 4, borderRadius: 2, background: 'rgba(236, 240, 241, 0.6)' }}>
                  <CardContent>
                    <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                      <CloudUploadIcon sx={{ mr: 1 }} />
                      Assign Files to Selected Devices
                    </Typography>

                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        Selected devices: {selectedDevices.length}
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                        {selectedDevices.map((selection) => (
                          <Chip
                            key={selection.device_id}
                            label={getDeviceName(selection.device_id)}
                            icon={<ComputerIcon />}
                            variant="outlined"
                            color={selection.file_id ? "success" : "default"}
                          />
                        ))}
                      </Box>
                    </Box>

                    <Grid container spacing={3}>
                      {selectedDevices.map((selection) => (
                        <Grid item xs={12} sm={6} key={selection.device_id}>
                          <FormControl fullWidth variant="outlined">
                            <InputLabel>{`File for ${getDeviceName(selection.device_id)}`}</InputLabel>
                            <Select
                              value={selection.file_id}
                              onChange={(e) => handleFileChange(selection.device_id, e.target.value)}
                              label={`File for ${getDeviceName(selection.device_id)}`}
                              sx={{ borderRadius: 2 }}
                            >
                              <MenuItem value="" disabled>
                                Select a file
                              </MenuItem>
                              {files.length === 0 ? (
                                <MenuItem disabled>No files uploaded yet</MenuItem>
                              ) : (
                                files.map((file) => (
                                  <MenuItem key={file.id} value={file.id}>
                                    {file.filename}
                                  </MenuItem>
                                ))
                              )}
                            </Select>
                          </FormControl>
                        </Grid>
                      ))}
                    </Grid>
                  </CardContent>
                </Card>
              )}

              {selectedDevices.length > 0 && (
                <Box sx={{ mt: 4, p: 2, backgroundColor: '#f5f5f5', borderRadius: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Job Summary
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={12}>
                      <Typography variant="body2">
                        <strong>Job Group Name:</strong> {jobGroupName || "Not specified"}
                      </Typography>
                    </Grid>
                    {selectedDevices.map((selection) => (
                      <Grid item xs={12} sm={6} key={selection.device_id}>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <ComputerIcon sx={{ mr: 1, color: '#3498db' }} />
                          <Box>
                            <Typography variant="body2">
                              <strong>{getDeviceName(selection.device_id)}</strong>
                            </Typography>
                            <Typography variant="caption" color={selection.file_id ? "success.main" : "error.main"}>
                              {selection.file_id ? getFileName(selection.file_id) : "No file selected"}
                            </Typography>
                          </Box>
                        </Box>
                      </Grid>
                    ))}
                  </Grid>
                </Box>
              )}

              {error && (
                <Box sx={{ mt: 2, p: 2, backgroundColor: '#ffebee', borderRadius: 2 }}>
                  <Typography color="error">
                    {error}
                  </Typography>
                </Box>
              )}

              <Button
                type="submit"
                variant="contained"
                fullWidth
                disabled={submitLoading}
                startIcon={submitLoading ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
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
                {submitLoading ? 'Submitting...' : 'Submit Job Group'}
              </Button>
            </form>
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

export default JobSubmission;