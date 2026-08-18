import React, { useState, useEffect } from 'react';
import {Link } from 'react-router-dom';
import {
  Button,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  IconButton,
  Paper,
  AppBar,
  Toolbar,
  Container,
  Divider,
  CircularProgress,
  Tooltip,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { 
  Download as DownloadIcon, 
  Delete as DeleteIcon, 
  CloudUpload as CloudUploadIcon,
  FilePresent as FileIcon,
  Build as BuildIcon,
  Group as GroupIcon,
  Backup as BackupIcon,
  InsertDriveFile as InsertDriveFileIcon,
  ErrorOutline as ErrorOutlineIcon,
} from '@mui/icons-material';
import axios from 'axios';
import API_BASE_URL from '../settings';

const FileManagement = () => {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);
  const fileInputRef = React.useRef(null);

  const fetchFiles = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      if (!token) {
        setError('Please log in to continue');
        setLoading(false);
        return;
      }
      const response = await axios.get(`${API_BASE_URL}/files/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setFiles(response.data);
      setError('');
      setLoading(false);
    } catch (err) {
      setError('Failed to load files');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select a file to upload');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      setUploading(true);
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API_BASE_URL}/files/upload`, formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      });
      setFiles([...files, response.data]);
      setSelectedFile(null);
      setError('');
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      setError('Failed to upload file');
      setUploading(false);
    }
  };

  const handleDownload = async (fileId, filename) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_BASE_URL}/files/${fileId}/download`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setError('Failed to download file');
    }
  };

  const handleDeleteClick = (file) => {
    setFileToDelete(file);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!fileToDelete) return;
    
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_BASE_URL}/files/${fileToDelete.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setFiles(files.filter((file) => file.id !== fileToDelete.id));
      setError('');
    } catch (err) {
      setError('Failed to delete file');
    } finally {
      setDeleteDialogOpen(false);
      setFileToDelete(null);
    }
  };

  const handleRefresh = () => {
    fetchFiles();
  };

  const getFileIcon = (filename) => {
    const extension = filename.split('.').pop().toLowerCase();
    let color = '#3498db'; // Default blue
    
    switch(extension) {
      case 'pdf':
        color = '#e74c3c'; // Red
        break;
      case 'doc':
      case 'docx':
        color = '#2980b9'; // Dark blue
        break;
      case 'xls':
      case 'xlsx':
        color = '#27ae60'; // Green
        break;
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
        color = '#f39c12'; // Orange
        break;
      case 'zip':
      case 'rar':
        color = '#8e44ad'; // Purple
        break;
      default:
        color = '#3498db'; // Default blue
    }
    
    return <InsertDriveFileIcon sx={{ color }} />;
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown';
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 Byte';
    const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
    return Math.round(bytes / Math.pow(1024, i), 2) + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleString();
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
              <FileIcon sx={{ mr: 1 }} />
              File Management
            </Typography>
            
            <Button 
              variant="outlined" 
              onClick={handleRefresh}
              startIcon={loading ? <CircularProgress size={20} /> : <BackupIcon />}
              disabled={loading}
              sx={{ borderRadius: 2 }}
            >
              Refresh
            </Button>
          </Box>
          
          <Divider sx={{ mb: 4 }} />

          <Card sx={{ mb: 4, borderRadius: 2, background: 'rgba(236, 240, 241, 0.6)' }}>
            <CardContent>
              <Box component="form" onSubmit={handleUpload} sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap' }}>
                <input
                  type="file"
                  onChange={(e) => setSelectedFile(e.target.files[0])}
                  style={{ display: 'none' }}
                  id="file-upload"
                  ref={fileInputRef}
                />
                <label htmlFor="file-upload">
                  <Button 
                    variant="contained" 
                    component="span"
                    startIcon={<CloudUploadIcon />}
                    sx={{ 
                      backgroundColor: '#3498db',
                      '&:hover': {
                        backgroundColor: '#2980b9',
                      },
                      borderRadius: 2
                    }}
                  >
                    Choose File
                  </Button>
                </label>
                
                <Box sx={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  ml: 2, 
                  px: 2, 
                  py: 1, 
                  borderRadius: 1, 
                  backgroundColor: selectedFile ? 'rgba(39, 174, 96, 0.1)' : 'transparent',
                  border: selectedFile ? '1px dashed #27ae60' : 'none',
                  flexGrow: 1,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  maxWidth: '40%'
                }}>
                  {selectedFile ? (
                    <>
                      <InsertDriveFileIcon sx={{ mr: 1, color: '#3498db' }} />
                      <Typography noWrap>{selectedFile.name}</Typography>
                    </>
                  ) : (
                    <Typography sx={{ color: 'text.secondary' }}>No file selected</Typography>
                  )}
                </Box>
                
                <Button 
                  type="submit" 
                  variant="contained"
                  disabled={!selectedFile || uploading}
                  startIcon={uploading ? <CircularProgress size={20} color="inherit" /> : <CloudUploadIcon />}
                  sx={{ 
                    ml: 2,
                    backgroundColor: '#27ae60',
                    '&:hover': {
                      backgroundColor: '#219653',
                    },
                    borderRadius: 2
                  }}
                >
                  {uploading ? 'Uploading...' : 'Upload'}
                </Button>
              </Box>
            </CardContent>
          </Card>
          
          {loading ? (
            <Box display="flex" justifyContent="center" my={4}>
              <CircularProgress />
            </Box>
          ) : (
            <>
              {files.length === 0 ? (
                <Card sx={{ borderRadius: 2, background: 'rgba(236, 240, 241, 0.6)', py: 4 }}>
                  <CardContent sx={{ textAlign: 'center' }}>
                    <CloudUploadIcon sx={{ fontSize: 60, color: '#bdc3c7', mb: 2 }} />
                    <Typography variant="h6" gutterBottom>No files uploaded yet</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Upload your first file using the form above
                    </Typography>
                  </CardContent>
                </Card>
              ) : (
                <Paper sx={{ width: '100%', overflow: 'hidden', borderRadius: 2 }}>
                  <Table>
                    <TableHead sx={{ backgroundColor: '#f5f5f5' }}>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold' }}>File Name</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Uploaded At</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }} align="center">Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {files.map((file) => (
                        <TableRow 
                          key={file.id}
                          sx={{ 
                            '&:hover': { backgroundColor: 'rgba(52, 152, 219, 0.05)' },
                            transition: 'background-color 0.2s ease-in-out'
                          }}
                        >
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              {getFileIcon(file.filename)}
                              <Typography sx={{ ml: 1 }}>{file.filename}</Typography>
                            </Box>
                          </TableCell>
                          <TableCell>{formatDate(file.created_at)}</TableCell>
                          <TableCell align="center">
                            <Tooltip title="Download">
                              <IconButton 
                                onClick={() => handleDownload(file.id, file.filename)}
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
                            <Tooltip title="Delete">
                              <IconButton 
                                onClick={() => handleDeleteClick(file)}
                                sx={{ 
                                  color: '#e74c3c',
                                  '&:hover': {
                                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                                  }
                                }}
                              >
                                <DeleteIcon />
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
            <Box sx={{ mt: 2, p: 2, backgroundColor: '#ffebee', borderRadius: 2, display: 'flex', alignItems: 'center' }}>
              <ErrorOutlineIcon color="error" sx={{ mr: 1 }} />
              <Typography color="error">
                {error}
              </Typography>
            </Box>
          )}
        </Paper>
      </Container>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        PaperProps={{
          sx: { borderRadius: 2 }
        }}
      >
        <DialogTitle sx={{ fontWeight: 'bold' }}>
          Confirm Delete
        </DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete <strong>{fileToDelete?.filename}</strong>? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button 
            onClick={() => setDeleteDialogOpen(false)}
            sx={{ borderRadius: 2 }}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleDeleteConfirm} 
            variant="contained" 
            color="error"
            sx={{ borderRadius: 2 }}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
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

export default FileManagement;