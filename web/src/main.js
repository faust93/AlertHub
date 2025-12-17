import { createApp } from 'vue'
//import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
//import 'element-plus/theme-chalk/display.css'
import App from './App.vue'
import router from './router.js'

import en from "element-plus/dist/locale/en";
import dayjs from 'dayjs'
dayjs.Ls.en ??= {}
dayjs.Ls.en.weekStart = 1

const app = createApp(App)
app.use({ locale: en })
app.use(router)
app.mount('#app')
