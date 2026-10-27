// Automatically determine the backend IP/host from current browser location
// This ensures that when accessing via http://172.28.8.13:5173, API calls go to http://172.28.8.13:8000
const SERVER_IP = (typeof window !== 'undefined' && window.location.hostname)
  ? window.location.hostname
  : 'localhost';

const API_BASE_URL = `http://${SERVER_IP}:8000/api/v1`;

export default API_BASE_URL;

