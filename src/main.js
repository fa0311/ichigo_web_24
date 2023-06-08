import './assets/main.css'
import 'element-plus/theme-chalk/index.css'
import ElementPlus from 'element-plus'
import { createApp } from 'vue'
import App from './App.vue'

const app = createApp(App);
app.use(ElementPlus);
app.mount('#app');
