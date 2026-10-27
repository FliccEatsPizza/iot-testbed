import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormGroup,
  FormControlLabel,
  Checkbox,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Divider,
  AppBar,
  Toolbar
} from '@mui/material';
import {
  School as SchoolIcon,
  PlayArrow as PlayArrowIcon,
  MenuBook as MenuBookIcon,
  Code as CodeIcon,
  ContentCopy as ContentCopyIcon,
  Close as CloseIcon,
  Computer as ComputerIcon,
  Group as GroupIcon,
  Build as BuildIcon,
  ArrowForward as ArrowForwardIcon
} from '@mui/icons-material';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import API_BASE_URL from '../settings';

const EducationalLabs = () => {
  const [presets, setPresets] = useState([]);
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');

  // Modal State
  const [activeModal, setActiveModal] = useState({
    open: false,
    presetId: null,
    tabIndex: 0,
    detailsLoading: false,
    details: null,
    activeCodeFile: null,
    groupName: '',
    selectedDevices: [],
    serverDevice: '',
    clientDevices: [],
    submitting: false,
    submitError: ''
  });

  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchDevices, 4000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Please log in to access Educational Labs');
        setLoading(false);
        return;
      }

      const [presetsRes, devicesRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/presets/`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_BASE_URL}/devices/`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      setPresets(presetsRes.data || []);
      const active = (devicesRes.data || []).filter(d => d.status !== 'offline');
      setDevices(active);
      setLoading(false);
    } catch (err) {
      console.error('Failed to load labs data:', err);
      setError('Failed to load Educational Labs. Please check your backend connection.');
      setLoading(false);
    }
  };

  const fetchDevices = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      const res = await axios.get(`${API_BASE_URL}/devices/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDevices((res.data || []).filter(d => d.status !== 'offline'));
    } catch (err) {
      // Background poll error ignored
    }
  };

  const handleOpenLab = async (presetId, initialTab = 0) => {
    const preset = presets.find(p => p.id === presetId);
    const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const defaultName = `${preset ? preset.title : 'Lab'} - ${nowStr}`;

    setActiveModal({
      open: true,
      presetId,
      tabIndex: initialTab,
      detailsLoading: true,
      details: null,
      activeCodeFile: null,
      groupName: defaultName,
      selectedDevices: devices.length > 0 ? [devices[0].id] : [],
      serverDevice: devices.length > 0 ? devices[0].id : '',
      clientDevices: devices.length > 1 ? [devices[1].id] : [],
      submitting: false,
      submitError: ''
    });

    try {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${API_BASE_URL}/presets/${presetId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = res.data;
      const codeFiles = Object.keys(data.source_code || {});
      setActiveModal(prev => ({
        ...prev,
        detailsLoading: false,
        details: data,
        activeCodeFile: codeFiles.length > 0 ? codeFiles[0] : null
      }));
    } catch (err) {
      setActiveModal(prev => ({
        ...prev,
        detailsLoading: false,
        submitError: 'Failed to load experiment instructions and source code'
      }));
    }
  };

  const handleCloseModal = () => {
    if (!activeModal.submitting) {
      setActiveModal(prev => ({ ...prev, open: false }));
    }
  };

  const handleUniformDeviceToggle = (deviceId) => {
    setActiveModal(prev => {
      const exists = prev.selectedDevices.includes(deviceId);
      const updated = exists
        ? prev.selectedDevices.filter(id => id !== deviceId)
        : [...prev.selectedDevices, deviceId];
      return { ...prev, selectedDevices: updated };
    });
  };

  const handleClientDeviceToggle = (deviceId) => {
    setActiveModal(prev => {
      const exists = prev.clientDevices.includes(deviceId);
      const updated = exists
        ? prev.clientDevices.filter(id => id !== deviceId)
        : [...prev.clientDevices, deviceId];
      return { ...prev, clientDevices: updated };
    });
  };

  const handleLaunchExperiment = async () => {
    if (activeModal.submitting) return; // Prevent double-clicks / concurrent submissions

    const { presetId, groupName, details, selectedDevices, serverDevice, clientDevices } = activeModal;
    if (!details) return;

    let deviceAssignments = [];
    if (details.type === 'uniform') {
      if (selectedDevices.length === 0) {
        setActiveModal(prev => ({ ...prev, submitError: 'Please select at least 1 node to run this lab' }));
        return;
      }
      deviceAssignments = selectedDevices.map(id => ({ device_id: id, role: 'node' }));
    } else if (details.type === 'role_based') {
      if (!serverDevice) {
        setActiveModal(prev => ({ ...prev, submitError: 'Please select 1 node as the Server (RPL Root)' }));
        return;
      }
      if (clientDevices.length === 0) {
        setActiveModal(prev => ({ ...prev, submitError: 'Please select at least 1 client node' }));
        return;
      }
      deviceAssignments = [
        { device_id: Number(serverDevice), role: 'server' },
        ...clientDevices.map(id => ({ device_id: Number(id), role: 'client' }))
      ];
    }

    try {
      setActiveModal(prev => ({ ...prev, submitting: true, submitError: '' }));
      const token = localStorage.getItem('token');
      const payload = {
        name: groupName || `${details.title} - ${new Date().toLocaleTimeString()}`,
        device_assignments: deviceAssignments
      };

      const res = await axios.post(`${API_BASE_URL}/presets/${presetId}/launch`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });

      const newGroup = res.data;
      // Close modal and navigate immediately to the live job group monitoring page
      setActiveModal(prev => ({ ...prev, open: false, submitting: false }));
      navigate(`/job-groups/${newGroup.id}`);
    } catch (err) {
      console.error('Launch failed:', err);
      const msg = err.response?.data?.detail || err.message || 'Failed to launch experiment';
      setActiveModal(prev => ({ ...prev, submitting: false, submitError: msg }));
    }
  };

  const copyCodeToClipboard = (text) => {
    if (text) {
      navigator.clipboard.writeText(text);
      alert('Source code copied to clipboard!');
    }
  };

  const getDifficultyColor = (diff) => {
    switch ((diff || '').toLowerCase()) {
      case 'beginner': return 'success';
      case 'intermediate': return 'primary';
      case 'advanced': return 'secondary';
      default: return 'default';
    }
  };

  const categories = ['All', ...new Set(presets.map(p => p.category))];
  const filteredPresets = selectedCategory === 'All'
    ? presets
    : presets.filter(p => p.category === selectedCategory);

  return (
    <Box sx={{ flexGrow: 1, pb: 8 }}>
      {/* App Bar Navigation */}
      <AppBar position="static" sx={{ backgroundColor: '#2c3e50', mb: 4 }}>
        <Toolbar>
          <SchoolIcon sx={{ mr: 2, color: '#2ecc71' }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
            Educational Labs & One-Click Experiments
          </Typography>
          <Button color="inherit" startIcon={<BuildIcon />} component={Link} to="/submit-jobs" sx={{ mr: 1 }}>
            Submit Custom Code
          </Button>
          <Button color="inherit" startIcon={<GroupIcon />} component={Link} to="/dashboard">
            Dashboard
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg">
        {/* Hero Section */}
        <Paper
          elevation={2}
          sx={{
            p: 4,
            mb: 4,
            borderRadius: 2,
            background: 'linear-gradient(135deg, #2c3e50 0%, #3498db 100%)',
            color: 'white'
          }}
        >
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={8}>
              <Typography variant="h4" fontWeight="bold" gutterBottom>
                Hands-On IoT & Wireless Labs
              </Typography>
              <Typography variant="body1" sx={{ opacity: 0.9, fontSize: '1.05rem', lineHeight: 1.6 }}>
                Explore real Contiki-NG wireless sensor network experiments with a single click.
                Select your physical nodes, follow the guided theory, and watch live communications in action.
              </Typography>
            </Grid>
            <Grid item xs={12} md={4} sx={{ textAlign: { xs: 'left', md: 'right' } }}>
              <Paper
                elevation={1}
                sx={{
                  display: 'inline-block',
                  p: 2,
                  bgcolor: 'rgba(255,255,255,0.15)',
                  backdropFilter: 'blur(10px)',
                  borderRadius: 2,
                  color: 'white'
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <ComputerIcon sx={{ color: devices.length > 0 ? '#2ecc71' : '#e74c3c' }} />
                  <Typography variant="h6" fontWeight="bold">
                    {devices.length} Nodes Online
                  </Typography>
                </Box>
                <Typography variant="caption" sx={{ opacity: 0.85 }}>
                  {devices.length > 0 ? 'Ready for testbed deployment' : 'Connect nodes to Pi gateway to run labs'}
                </Typography>
              </Paper>
            </Grid>
          </Grid>
        </Paper>

        {/* Category Filters */}
        <Box sx={{ mb: 3, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {categories.map(cat => (
            <Chip
              key={cat}
              label={cat}
              clickable
              color={selectedCategory === cat ? 'primary' : 'default'}
              variant={selectedCategory === cat ? 'filled' : 'outlined'}
              onClick={() => setSelectedCategory(cat)}
              sx={{ fontWeight: 'medium' }}
            />
          ))}
        </Box>

        {/* Error message */}
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Loading Spinner */}
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        ) : (
          /* Presets Grid */
          <Grid container spacing={3}>
            {filteredPresets.map(preset => (
              <Grid item xs={12} md={6} lg={4} key={preset.id}>
                <Card
                  elevation={3}
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    borderRadius: 2,
                    transition: 'transform 0.2s ease, box-shadow 0.2s ease',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: '0 8px 24px rgba(0,0,0,0.12)'
                    }
                  }}
                >
                  <CardContent sx={{ flexGrow: 1, pb: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                      <Chip
                        label={preset.category}
                        size="small"
                        sx={{ bgcolor: '#ecf0f1', color: '#2c3e50', fontWeight: 'bold' }}
                      />
                      <Chip
                        label={preset.difficulty}
                        size="small"
                        color={getDifficultyColor(preset.difficulty)}
                        variant="outlined"
                        sx={{ fontWeight: 'bold' }}
                      />
                    </Box>

                    <Typography variant="h6" fontWeight="bold" gutterBottom sx={{ color: '#2c3e50' }}>
                      {preset.title}
                    </Typography>

                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2, lineHeight: 1.5 }}>
                      {preset.overview}
                    </Typography>

                    <Divider sx={{ my: 1.5 }} />

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                      <Typography variant="caption" color="text.secondary">
                        ⏱️ Est. Time: <strong>{preset.duration}</strong>
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        🔌 Requires: <strong>{preset.min_nodes}+ Node(s)</strong>
                      </Typography>
                    </Box>
                  </CardContent>

                  <CardActions sx={{ p: 2, pt: 0, display: 'flex', gap: 1 }}>
                    <Button
                      variant="contained"
                      fullWidth
                      startIcon={<PlayArrowIcon />}
                      onClick={() => handleOpenLab(preset.id, 0)}
                      sx={{
                        bgcolor: '#2ecc71',
                        '&:hover': { bgcolor: '#27ae60' },
                        textTransform: 'none',
                        fontWeight: 'bold'
                      }}
                    >
                      Configure & Launch
                    </Button>
                    <Tooltip title="View Lab Guide & Theory">
                      <IconButton
                        onClick={() => handleOpenLab(preset.id, 1)}
                        sx={{ color: '#3498db', border: '1px solid #d6dbdf' }}
                      >
                        <MenuBookIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Inspect C Source Code">
                      <IconButton
                        onClick={() => handleOpenLab(preset.id, 2)}
                        sx={{ color: '#7f8c8d', border: '1px solid #d6dbdf' }}
                      >
                        <CodeIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </CardActions>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Container>

      {/* Interactive Lab Modal */}
      <Dialog
        open={activeModal.open}
        onClose={handleCloseModal}
        maxWidth="md"
        fullWidth
        PaperProps={{ sx: { borderRadius: 2, minHeight: '65vh' } }}
      >
        <DialogTitle sx={{ backgroundColor: '#2c3e50', color: 'white', py: 1.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SchoolIcon sx={{ color: '#2ecc71' }} />
            <Typography variant="h6" fontWeight="bold">
              {activeModal.details ? activeModal.details.title : 'Loading Lab...'}
            </Typography>
          </Box>
          <IconButton size="small" onClick={handleCloseModal} sx={{ color: 'white' }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>

        <Box sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: '#f8f9fa' }}>
          <Tabs
            value={activeModal.tabIndex}
            onChange={(e, val) => setActiveModal(prev => ({ ...prev, tabIndex: val }))}
          >
            <Tab icon={<PlayArrowIcon fontSize="small" />} iconPosition="start" label="Configure & Launch" />
            <Tab icon={<MenuBookIcon fontSize="small" />} iconPosition="start" label="Lab Guide & Theory" />
            <Tab icon={<CodeIcon fontSize="small" />} iconPosition="start" label="C Source Code" />
          </Tabs>
        </Box>

        <DialogContent sx={{ p: 3 }}>
          {activeModal.detailsLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
              <CircularProgress />
            </Box>
          ) : activeModal.details ? (
            <>
              {/* TAB 0: CONFIGURE & LAUNCH */}
              {activeModal.tabIndex === 0 && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
                  <TextField
                    label="Experiment / Job Group Name"
                    fullWidth
                    size="small"
                    value={activeModal.groupName}
                    onChange={(e) => setActiveModal(prev => ({ ...prev, groupName: e.target.value }))}
                  />

                  {/* UNIFORM NODE SELECTOR */}
                  {activeModal.details.type === 'uniform' && (
                    <Box sx={{ p: 2, bgcolor: '#f8f9fa', borderRadius: 2, border: '1px solid #e9ecef' }}>
                      <Typography variant="subtitle1" fontWeight="bold" gutterBottom sx={{ color: '#2c3e50' }}>
                        Select Target Nodes
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        All selected nodes will compile and execute this standalone experiment.
                      </Typography>

                      {devices.length === 0 ? (
                        <Alert severity="warning">No physical nodes are currently connected or online.</Alert>
                      ) : (
                        <FormGroup row sx={{ gap: 1 }}>
                          {devices.map(device => {
                            const isChecked = activeModal.selectedDevices.includes(device.id);
                            return (
                              <Paper
                                key={device.id}
                                variant="outlined"
                                sx={{
                                  p: 1,
                                  px: 2,
                                  display: 'flex',
                                  alignItems: 'center',
                                  borderRadius: 2,
                                  bgcolor: isChecked ? 'rgba(46, 204, 113, 0.08)' : 'white',
                                  borderColor: isChecked ? '#2ecc71' : '#d6dbdf'
                                }}
                              >
                                <FormControlLabel
                                  control={
                                    <Checkbox
                                      checked={isChecked}
                                      onChange={() => handleUniformDeviceToggle(device.id)}
                                      color="success"
                                    />
                                  }
                                  label={
                                    <Box>
                                      <Typography variant="body2" fontWeight="bold">
                                        Device #{device.id} ({device.name})
                                      </Typography>
                                      <Typography variant="caption" color="text.secondary">
                                        {device.port_number || 'USB CDC ACM'}
                                      </Typography>
                                    </Box>
                                  }
                                />
                              </Paper>
                            );
                          })}
                        </FormGroup>
                      )}
                    </Box>
                  )}

                  {/* ROLE-BASED SELECTOR (e.g. UDP CLIENT-SERVER) */}
                  {activeModal.details.type === 'role_based' && (
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      {/* Server Selection */}
                      <Box sx={{ p: 2, bgcolor: '#f8f9fa', borderRadius: 2, border: '1px solid #e9ecef' }}>
                        <Typography variant="subtitle1" fontWeight="bold" sx={{ color: '#2c3e50', mb: 0.5 }}>
                          1. Select Server Node (RPL DAG Root)
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                          This node will start the 6LoWPAN RPL tree and listen for client UDP requests on port 5678.
                        </Typography>

                        <FormControl fullWidth size="small">
                          <InputLabel>Server Node</InputLabel>
                          <Select
                            value={activeModal.serverDevice}
                            label="Server Node"
                            onChange={(e) => {
                              const sId = e.target.value;
                              setActiveModal(prev => ({
                                ...prev,
                                serverDevice: sId,
                                clientDevices: prev.clientDevices.filter(id => id !== sId)
                              }));
                            }}
                          >
                            {devices.map(d => (
                              <MenuItem key={d.id} value={d.id}>
                                Device #{d.id} ({d.name}) — {d.port_number || 'USB Port'}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Box>

                      {/* Client Selection */}
                      <Box sx={{ p: 2, bgcolor: '#f8f9fa', borderRadius: 2, border: '1px solid #e9ecef' }}>
                        <Typography variant="subtitle1" fontWeight="bold" sx={{ color: '#2c3e50', mb: 0.5 }}>
                          2. Select Client Node(s)
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                          These nodes will search for the DAG root and transmit periodic UDP requests.
                        </Typography>

                        <FormGroup row sx={{ gap: 1 }}>
                          {devices
                            .filter(d => d.id !== activeModal.serverDevice)
                            .map(device => {
                              const isChecked = activeModal.clientDevices.includes(device.id);
                              return (
                                <Paper
                                  key={device.id}
                                  variant="outlined"
                                  sx={{
                                    p: 1,
                                    px: 2,
                                    display: 'flex',
                                    alignItems: 'center',
                                    borderRadius: 2,
                                    bgcolor: isChecked ? 'rgba(52, 152, 219, 0.08)' : 'white',
                                    borderColor: isChecked ? '#3498db' : '#d6dbdf'
                                  }}
                                >
                                  <FormControlLabel
                                    control={
                                      <Checkbox
                                        checked={isChecked}
                                        onChange={() => handleClientDeviceToggle(device.id)}
                                        color="primary"
                                      />
                                    }
                                    label={
                                      <Box>
                                        <Typography variant="body2" fontWeight="bold">
                                          Device #{device.id} ({device.name})
                                        </Typography>
                                        <Typography variant="caption" color="text.secondary">
                                          {device.port_number || 'USB CDC ACM'}
                                        </Typography>
                                      </Box>
                                    }
                                  />
                                </Paper>
                              );
                            })}
                        </FormGroup>
                        {devices.filter(d => d.id !== activeModal.serverDevice).length === 0 && (
                          <Typography variant="caption" color="error">
                            Need at least 1 other device to act as client. Connect another dongle to the gateway.
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  )}

                  {activeModal.submitError && (
                    <Alert severity="error">{activeModal.submitError}</Alert>
                  )}
                </Box>
              )}

              {/* TAB 1: LAB GUIDE & THEORY */}
              {activeModal.tabIndex === 1 && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Paper sx={{ p: 2.5, bgcolor: '#fcfcfc', border: '1px solid #eaeded', borderRadius: 2 }}>
                    <Typography variant="h6" fontWeight="bold" sx={{ color: '#2c3e50', mb: 1 }}>
                      📖 Background & Theory
                    </Typography>
                    <Box
                      sx={{
                        whiteSpace: 'pre-line',
                        lineHeight: 1.7,
                        color: '#34495e',
                        fontSize: '0.95rem'
                      }}
                    >
                      {activeModal.details.theory}
                    </Box>
                  </Paper>

                  <Paper sx={{ p: 2.5, bgcolor: '#fcfcfc', border: '1px solid #eaeded', borderRadius: 2 }}>
                    <Typography variant="h6" fontWeight="bold" sx={{ color: '#2c3e50', mb: 1 }}>
                      📋 Step-by-Step Instructions
                    </Typography>
                    <Box sx={{ whiteSpace: 'pre-line', lineHeight: 1.7, color: '#34495e', fontSize: '0.95rem' }}>
                      {activeModal.details.instructions}
                    </Box>
                  </Paper>

                  <Paper sx={{ p: 2.5, bgcolor: '#0d1117', borderRadius: 2 }}>
                    <Typography variant="subtitle2" sx={{ color: '#58a6ff', mb: 1, fontWeight: 'bold' }}>
                      💻 Expected Serial Log Output
                    </Typography>
                    <Box
                      component="pre"
                      sx={{
                        m: 0,
                        p: 1.5,
                        color: '#7ee787',
                        backgroundColor: '#161b22',
                        borderRadius: 1,
                        fontFamily: 'Consolas, Monaco, monospace',
                        fontSize: '0.85rem',
                        overflowX: 'auto',
                        whiteSpace: 'pre-wrap'
                      }}
                    >
                      {activeModal.details.expected_output}
                    </Box>
                  </Paper>
                </Box>
              )}

              {/* TAB 2: C SOURCE CODE */}
              {activeModal.tabIndex === 2 && (
                <Box>
                  <Box sx={{ mb: 2, display: 'flex', gap: 1 }}>
                    {Object.keys(activeModal.details.source_code || {}).map(fname => (
                      <Chip
                        key={fname}
                        label={fname}
                        clickable
                        color={activeModal.activeCodeFile === fname ? 'primary' : 'default'}
                        onClick={() => setActiveModal(prev => ({ ...prev, activeCodeFile: fname }))}
                        icon={<CodeIcon />}
                      />
                    ))}
                    <Box sx={{ flexGrow: 1 }} />
                    <Button
                      size="small"
                      startIcon={<ContentCopyIcon />}
                      onClick={() => copyCodeToClipboard(activeModal.details.source_code?.[activeModal.activeCodeFile])}
                    >
                      Copy Code
                    </Button>
                  </Box>

                  <Box
                    component="pre"
                    sx={{
                      m: 0,
                      p: 2,
                      color: '#c9d1d9',
                      backgroundColor: '#0d1117',
                      borderRadius: 2,
                      fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                      fontSize: '0.85rem',
                      lineHeight: 1.5,
                      maxHeight: '52vh',
                      overflow: 'auto',
                      border: '1px solid #30363d'
                    }}
                  >
                    {activeModal.details.source_code?.[activeModal.activeCodeFile] || '// Select a file'}
                  </Box>
                </Box>
              )}
            </>
          ) : null}
        </DialogContent>

        <DialogActions sx={{ px: 3, py: 2, bgcolor: '#f8f9fa', borderTop: '1px solid #e9ecef' }}>
          <Button onClick={handleCloseModal} sx={{ color: '#7f8c8d' }}>
            Close
          </Button>

          {activeModal.tabIndex !== 0 ? (
            <Button
              variant="contained"
              onClick={() => setActiveModal(prev => ({ ...prev, tabIndex: 0 }))}
              endIcon={<ArrowForwardIcon />}
              sx={{ bgcolor: '#3498db' }}
            >
              Continue to Launch
            </Button>
          ) : (
            <Button
              variant="contained"
              onClick={handleLaunchExperiment}
              disabled={activeModal.submitting || devices.length === 0}
              startIcon={activeModal.submitting ? <CircularProgress size={20} color="inherit" /> : <PlayArrowIcon />}
              sx={{
                bgcolor: '#2ecc71',
                '&:hover': { bgcolor: '#27ae60' },
                fontWeight: 'bold',
                px: 3
              }}
            >
              {activeModal.submitting ? 'Deploying...' : 'Launch Experiment'}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EducationalLabs;
