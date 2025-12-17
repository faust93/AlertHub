import axios from 'axios';

const isDevMode = import.meta.env.VITE_APP_MODE === 'dev';
const BaseURL = import.meta.env.VITE_BASE_URL;

let request

if(isDevMode) {
    request = axios.create({
        baseURL: BaseURL,
        timeout: 8000,
        withCredentials: true,
        headers: {
            'Content-Type': 'application/json'
        }
    });
} else {
    request = axios.create({
        timeout: 8000,
        withCredentials: true,
        headers: {
            'Content-Type': 'application/json'
        }
    });
}
// config.headers.Authorization = window.localStorage.getItem('token')
request.defaults.withCredentials = false;

request.interceptors.request.use(config => {
    const token = window.localStorage.getItem('token');
    if (token) {
        config.headers['Authorization'] = 'Bearer ' + token;
    }
    return config;
}, error => {
    return Promise.reject(error);
});

// Response interceptor
request.interceptors.response.use(
    response => {
        // Do something with the response data
        return response.data;
    },
    error => {
        if (error.response && error.response.status === 401) {
            console.warn('Unauthorized - Redirecting to login...');
            window.localStorage.removeItem('token');
            window.localStorage.removeItem('user_id');
            window.localStorage.removeItem('user_role');
            window.location.href = '/login';
        }
        console.log(error);
        return error;
        //return Promise.reject(error);
    }
);

export default request;
